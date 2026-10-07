# MousePro Event Flow

This reference follows events through the current implementation. Component ownership is summarized in [ARCHITECTURE.md](ARCHITECTURE.md), while persistent and transient data are separated in [STATE_MANAGEMENT.md](STATE_MANAGEMENT.md).

## Contents

- [Application startup](#application-startup)
- [Mouse event flow](#mouse-event-flow)
- [UI event flow](#ui-event-flow)
- [Signal and callback relationships](#signal-and-callback-relationships)
- [Profile switching](#profile-switching)
- [Settings updates](#settings-updates)
- [Generic Mouse Mode](#generic-mouse-mode)
- [Save operations](#save-operations)
- [Shutdown](#shutdown)
- [Known constraints](#known-constraints)

## Application startup

```mermaid
sequenceDiagram
    actor User
    participant Main as main_qml.py
    participant Config as core/config.py
    participant Qt as QApplication and QML
    participant Engine
    participant Backend
    participant Hook
    participant Detector as AppDetector

    User->>Main: start process
    Main->>Main: logging, CLI, update-helper check
    Main->>Config: load_config()
    Config-->>Main: migrated schema 11 config
    Main->>Main: single-instance acquisition
    Main->>Qt: create QApplication and UiState
    Main->>Engine: Engine()
    Engine->>Config: load_config()
    Engine->>Engine: configure hook bindings
    Main->>Backend: Backend(engine, locale)
    Backend->>Config: load_config()
    Backend->>Engine: register callbacks
    Main->>Qt: expose context and load Main.qml
    Main->>Qt: create tray and screenshot controller
    Main-->>Engine: deferred start
    Engine->>Hook: start()
    Engine->>Detector: start()
    Main->>Qt: app.exec()
```

If QML produces no root object, startup exits with failure. On macOS, the engine is not scheduled to start unless the Accessibility check succeeds. A second instance sends an activation message to the existing instance instead of creating another window.

## Mouse event flow

```mermaid
sequenceDiagram
    participant Mouse
    participant OS
    participant Hook as Platform MouseHook
    participant Base as BaseMouseHook
    participant Engine
    participant Action as key_simulator or device action

    Mouse->>OS: physical input
    OS->>Hook: native event
    Hook->>Hook: normalize to MouseEvent
    Hook->>Base: dispatch(event)
    Base->>Engine: registered callback
    alt event is blocked and engine enabled
        Engine->>Action: execute mapped action
        Action->>OS: synthetic keyboard/mouse/system input
    else event is not managed
        Hook-->>OS: pass through native event
    end
```

The engine wires callbacks and block flags together. A mapping of `none`, an unsupported device control, or a disabled Generic Mouse Mode normally leaves the native event unblocked. Synthetic input is marked or otherwise separated by platform code to avoid immediate recapture.

For paired mouse actions, down and up are injected separately. A 20-second safety timer releases an injected mouse button if the corresponding physical up event never arrives. For Multi-Action buttons, the down timestamp is recorded and the selected click or long-press action runs only on release.

## UI event flow

```mermaid
sequenceDiagram
    actor User
    participant QML
    participant Backend
    participant Config
    participant Engine
    participant Hook

    User->>QML: change mapping
    QML->>Backend: setProfileMapping(profile, button, action)
    Backend->>Config: set_mapping() and atomic save
    Backend->>Engine: reload_mappings()
    Engine->>Config: load_config()
    Engine->>Hook: reset_bindings()
    Engine->>Hook: register and block current mappings
    Backend-->>QML: profilesChanged and mappingsChanged
    Backend-->>QML: statusMessage("Saved")
```

QML property bindings update in response to backend notify signals. Dialog visibility, selected editing profile, selected button, search text, and pending deletion are local QML state and do not travel through Python unless the user confirms an operation.

## Signal and callback relationships

The engine exposes ordinary Python callbacks for profile, connection, battery, DPI, SmartShift, debug, gesture, and status changes. The backend callback methods may run off the Qt thread, so they emit internal signals such as `_profileSwitchRequest` and `_connectionChangeRequest`. Those signals are connected with `Qt.QueuedConnection` to handlers that update backend fields and emit public QML notify signals.

```mermaid
flowchart LR
    Worker[Hook, HID, detector, or worker thread] --> Callback[Backend _onEngine... callback]
    Callback --> Internal[Internal queued Qt signal]
    Internal --> Handler[Qt-main-thread _handle... slot]
    Handler --> Public[Public notify signal]
    Public --> QML[QML binding or Connections handler]
```

SmartShift is a special case: the callback stages a value and queues `_handleSmartShiftRead` with `QMetaObject.invokeMethod` because the Windows low-level hook thread is not a reliable signal-emission context.

## Profile switching

```mermaid
sequenceDiagram
    participant Detector as AppDetector
    participant Catalog as app_catalog/config matcher
    participant Engine
    participant Hook
    participant Backend
    participant QML

    Detector->>Detector: poll foreground app every 300 ms
    Detector->>Engine: on_change(app identity)
    Engine->>Catalog: get_profile_for_app(config, identity)
    Catalog-->>Engine: first matching profile or default
    alt profile changed
        Engine->>Engine: update active runtime profile
        Engine->>Hook: reset bindings and configure new mappings
        Engine->>Backend: profile callback
        Backend-->>Backend: queued Qt-thread handoff
        Backend-->>QML: activeProfileChanged, mappingsChanged, profilesChanged
    end
```

Switching profiles does not restart the hook or HID listener. Selecting a profile row in `MousePage.qml` changes the editing target only; foreground-app detection remains the owner of the active runtime profile. See [PROFILE_SYSTEM.md](PROFILE_SYSTEM.md).

## Settings updates

Settings follow one of four paths:

1. **Persist and notify only:** start minimized, update checks, appearance, screenshot directory.
2. **Persist and rewire:** scroll inversion, trackpad filtering, gesture threshold, Generic Mouse Mode.
3. **Persist and write to a device:** DPI and SmartShift settings.
4. **External state then persist:** start at login; failure triggers rollback or an explicit inconsistency message.

Language differs: QML calls `LocaleManager.setLanguage()`, QML bindings and tray text react to `languageChanged`, and `main_qml.py` reloads and saves the language preference.

## Generic Mouse Mode

```mermaid
sequenceDiagram
    actor User
    participant QML as Settings UI
    participant Backend
    participant Config
    participant Engine
    participant Hook as Windows hook

    User->>QML: toggle Generic Mouse Mode
    QML->>Backend: setGenericMouseEnabled(value)
    Backend->>Config: save generic_mouse_enabled
    Backend->>Engine: reload_mappings()
    Engine->>Engine: build complete callback/suppression snapshot
    alt enabled
        Engine->>Hook: bind middle and generic side mappings
    else disabled
        Engine->>Engine: leave standard side events native
    end
    Engine->>Hook: atomically publish new binding generation
    Backend-->>QML: settings, mappings, layout/status signals
```

The mode is forced off by engine logic on non-Windows platforms. When enabled, the UI exposes middle plus two generic side buttons and Generic Mouse Mode owns the standard side events. Detected-device identity and catalog capabilities never authorize a Logitech-specific low-level XBUTTON route because they cannot identify the event source. Disabled or unmapped events pass through natively.

Windows `WH_MOUSE_LL` XBUTTON messages do not include a physical device handle. Raw Input can report a device handle for diagnostics, but it cannot be correlated safely with the synchronous low-level suppression decision. The engine therefore treats standard XBUTTONs as device-ambiguous and routes them only through explicitly enabled Generic Mouse Mode.

## Save operations

All configuration saves use the same atomic sequence:

```mermaid
sequenceDiagram
    participant Caller
    participant Config
    participant Disk

    Caller->>Config: save_config(cfg)
    Config->>Disk: create temporary file in config directory
    Config->>Disk: JSON write, flush, fsync
    Config->>Disk: apply restrictive POSIX permissions
    Config->>Disk: os.replace(temp, config.json)
    alt failure
        Config->>Disk: remove temporary file if possible
        Config-->>Caller: re-raise error
    end
```

Profile and mapping helpers save internally. Most backend setting slots mutate their local configuration and call `save_config()` directly. Hardware reads may update backend display state without saving; for example, `_handleDpiRead` updates the UI copy, while a user DPI change is persisted.

## Shutdown

```mermaid
sequenceDiagram
    actor User
    participant Tray
    participant Main
    participant Engine
    participant Detector
    participant Hook
    participant Qt

    User->>Tray: Quit
    Tray->>Engine: stop()
    Engine->>Detector: stop and join
    Engine->>Hook: stop()
    Tray->>Qt: quit()
    Qt-->>Main: app.exec() returns
    Main->>Engine: stop() in finally
```

Closing the main window hides it rather than ending the process. Update installation is another controlled shutdown path: the backend stops the engine, launches the Windows helper, and asks `QCoreApplication` to quit. If helper launch fails, it attempts to restart the engine.

## Known constraints

- The callback bridge is explicit rather than generated; adding a new runtime state normally requires an engine callback, an internal backend signal/handler, and a public notify signal.
- Profile polling deliberately retains the last profile when the foreground application cannot be resolved because `AppDetector` does not call the change callback for falsey results.
- Settings saves are synchronous on the caller thread; update work and selected device operations use worker threads where implemented.
- Native event interception details differ by platform even though the normalized event path is shared.
