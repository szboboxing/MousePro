"""
Engine — wires the mouse hook to the key simulator using the
current configuration.  Sits between the hook layer and the UI.
Supports per-application auto-switching of profiles.
"""

from dataclasses import replace
import sys
import threading
import time
from core.mouse_hook import MouseHook, MouseEvent
from core.key_simulator import (
    ACTIONS, execute_action, is_mouse_button_action,
    inject_mouse_down, inject_mouse_up,
)
from core.config import (
    load_config, get_active_mappings, get_profile_for_app,
    ConfigLoadError, config_is_verified, mark_config_verified_writable,
    BUTTON_TO_EVENTS, DEFAULT_LONG_PRESS_THRESHOLD_MS,
    GENERIC_MOUSE_BUTTONS,
    GESTURE_DIRECTION_BUTTONS, save_config,
    long_press_mapping_key, supports_multi_action,
    resolve_windows_xbutton_mapping_key, WINDOWS_XBUTTON_KEYS,
)
from core.app_detector import AppDetector
from core.mouse_hook_types import HidRuntimeState, HookHealth
from core.linux_permissions import (
    linux_permission_log_message,
    linux_permission_report,
    linux_permission_status_message,
)
from core.logi_devices import clamp_dpi, get_reprogrammable_buttons

HSCROLL_ACTION_COOLDOWN_S = 0.35
HSCROLL_VOLUME_COOLDOWN_S = 0.06
BACKEND_HEALTH_INTERVAL_S = 2.0
BACKEND_RECOVERY_BACKOFF_S = (0.0, 1.0, 3.0)
_VOLUME_ACTIONS = {"volume_up", "volume_down"}
_LOGI_XBUTTON_CIDS = {"xbutton1": 0x0053, "xbutton2": 0x0056}
_LOGI_XBUTTON_EVENTS = {
    "xbutton1": (MouseEvent.LOGI_XBUTTON1_DOWN, MouseEvent.LOGI_XBUTTON1_UP),
    "xbutton2": (MouseEvent.LOGI_XBUTTON2_DOWN, MouseEvent.LOGI_XBUTTON2_UP),
}
class Engine:
    """
    Core logic: reads config, installs the mouse hook,
    dispatches actions when mapped buttons are pressed,
    and auto-switches profiles when the foreground app changes.
    """

    def __init__(self, initial_config=None):
        self.hook = MouseHook()
        self.cfg = initial_config if initial_config is not None else load_config()
        self._enabled = True
        self._hscroll_state = {
            MouseEvent.HSCROLL_LEFT: {"accum": 0.0, "last_fire_at": 0.0},
            MouseEvent.HSCROLL_RIGHT: {"accum": 0.0, "last_fire_at": 0.0},
        }
        self._current_profile: str = self.cfg.get("active_profile", "default")
        self._app_detector = AppDetector(self._on_app_change)
        self._profile_change_cb = None       # UI callback
        self._connection_change_cb = None   # UI callback for device status
        self._status_cb = None             # UI callback for status messages
        self._battery_read_cb = None        # UI callback for battery level
        self._dpi_read_cb = None            # UI callback for current DPI
        self._smart_shift_read_cb = None   # UI callback for Smart Shift mode
        self._debug_cb = None               # UI callback for debug messages
        self._gesture_event_cb = None       # UI callback for structured gesture events
        self._debug_events_enabled = bool(
            self.cfg.get("settings", {}).get("debug_mode", False)
        )
        self._battery_poll_stop = threading.Event()
        self._battery_poll_thread = None          # track the poller thread
        self._last_connection_state = bool(self._hid_runtime_state().input_ready)
        self._last_hid_features_ready = bool(self.hid_features_ready)
        self._last_binding_route_identity = self._binding_route_identity()
        self._hid_replay_requested_this_launch = False
        self._replay_inflight = False
        self._replay_pending_rerun = False
        self._replay_lock = threading.Lock()
        self._mouse_release_timers = {}   # action_id → Timer for safety auto-release
        self._multi_action_down_at = {}
        self._binding_state_lock = threading.Lock()
        self._lock = threading.RLock()
        self._backend_watchdog_stop = threading.Event()
        self._backend_watchdog_thread = None
        self._backend_recovery_lock = threading.Lock()
        self._backend_recovery_attempts = 0
        self._backend_recovery_exhausted = False
        self.hook.set_debug_callback(self._emit_debug)
        self.hook.set_gesture_callback(self._emit_gesture_event)
        self.hook.set_status_callback(self._emit_status)
        self._replace_bindings("startup")
        self.hook.set_connection_change_callback(self._on_connection_change)
        # Apply persisted DPI setting
        dpi = self.cfg.get("settings", {}).get("dpi", 1000)
        try:
            if hasattr(self.hook, "set_dpi"):
                self.hook.set_dpi(dpi)
        except Exception as e:
            print(f"[Engine] Failed to set DPI: {e}")

        # ── MousePro enhancements (right-hold chord / usage stats) ──
        self._mp_test_listeners = []
        self._mp_confirm_listeners = []
        self._mp_test_listeners_lock = threading.Lock()
        self._mp_button_test_active = False
        self._mp_confirm_active = False
        self._setup_mousepro_enhancements()

    # ------------------------------------------------------------------
    # MousePro enhancements
    # ------------------------------------------------------------------

    def _setup_mousepro_enhancements(self):
        """Wire the right-hold gesture chord and raw observer into the hook.

        Callbacks read ``self.cfg`` live, so settings changes only need a
        config save/reload — the hook itself is never reconfigured.
        """
        if not (sys.platform == "win32"
                and hasattr(self.hook, "set_right_hold_config")):
            return
        from core.usage_stats import shared_stats

        self._mp_shared_stats = shared_stats
        self.hook.set_right_hold_config(
            enabled_cb=self._mp_gesture_enabled,
            buttons_cb=self._mp_screenshot_buttons,
            fire_cb=self._mp_dispatch_gesture,
            active_test_cb=self._mp_capture_active,
        )
        self.hook.set_raw_observer(self._mp_on_raw_event)

    def _mp_gesture_enabled(self):
        return bool(
            self.cfg.get("mousepro", {}).get(
                "right_hold_gesture_enabled", True
            )
        )

    def _mp_screenshot_buttons(self):
        return list(
            self.cfg.get("mousepro", {}).get(
                "screenshot_side_buttons", ["xbutton1", "xbutton2"]
            )
        )

    def _mp_capture_active(self):
        return bool(self._mp_button_test_active or self._mp_confirm_active)

    def _mp_on_raw_event(self, payload):
        # Physical events only: record usage stats and fan out to any
        # button-test / side-button-confirm UI listeners.
        try:
            stats = getattr(self, "_mp_shared_stats", None)
            if stats is not None:
                control = payload.get("control")
                if control in {"left", "right", "middle",
                               "xbutton1", "xbutton2"}:
                    if payload.get("pressed"):
                        stats.record_click(control)
                elif control in {"wheel_up", "wheel_down"}:
                    stats.record_wheel(control)
                elif control == "move":
                    stats.record_move(payload.get("x", 0), payload.get("y", 0))
        except Exception:
            pass
        with self._mp_test_listeners_lock:
            listeners = list(self._mp_test_listeners)
        for listener in listeners:
            try:
                listener(payload)
            except Exception:
                pass

    def _mp_dispatch_gesture(self, action_id):
        """Run a committed gesture action off the low-level hook thread."""
        def _run():
            try:
                if action_id == "enhanced_paste":
                    from core import system_actions

                    result = system_actions.execute_quick_action(
                        "enhanced_paste"
                    )
                    if result.success:
                        stats = getattr(self, "_mp_shared_stats", None)
                        if stats is not None:
                            stats.record_feature("enhanced_paste")
                    print(
                        "[Engine] gesture action=enhanced_paste "
                        f"ok={result.success} detail={result.detail}"
                    )
                    return
                execute_action(action_id)
                stats = getattr(self, "_mp_shared_stats", None)
                if stats is not None:
                    if action_id == "copy":
                        stats.record_feature("copy")
                    elif action_id == "system_screenshot":
                        stats.record_feature("screenshot")
            except Exception as exc:
                print(f"[Engine] gesture action failed id={action_id}: {exc}")

        threading.Thread(
            target=_run, daemon=True, name="MouseProGesture"
        ).start()

    def set_right_hold_gesture_enabled(self, enabled):
        self.cfg.setdefault("mousepro", {})
        self.cfg["mousepro"]["right_hold_gesture_enabled"] = bool(enabled)
        save_config(self.cfg)

    def set_screenshot_side_buttons(self, buttons):
        from core.config import sanitize_mousepro_section

        cleaned = []
        for name in buttons or []:
            if name in ("xbutton1", "xbutton2") and name not in cleaned:
                cleaned.append(name)
        self.cfg.setdefault("mousepro", {})
        if cleaned:
            self.cfg["mousepro"]["screenshot_side_buttons"] = cleaned
        sanitize_mousepro_section(self.cfg)
        save_config(self.cfg)
        return list(self.cfg["mousepro"]["screenshot_side_buttons"])

    def get_mousepro_settings(self):
        section = self.cfg.get("mousepro", {})
        return {
            "right_hold_gesture_enabled": bool(
                section.get("right_hold_gesture_enabled", True)
            ),
            "screenshot_side_buttons": list(
                section.get(
                    "screenshot_side_buttons", ["xbutton1", "xbutton2"]
                )
            ),
        }

    # -- button test / side-button confirm (raw-event capture) ---------

    def set_button_test_active(self, active):
        self._mp_button_test_active = bool(active)
        if hasattr(self.hook, "set_test_mode"):
            self.hook.set_test_mode(self._mp_capture_active())
        if not active:
            with self._mp_test_listeners_lock:
                self._mp_test_listeners = list(self._mp_confirm_listeners)

    def add_test_event_listener(self, callback):
        with self._mp_test_listeners_lock:
            if callback not in self._mp_test_listeners:
                self._mp_test_listeners.append(callback)

    def remove_test_event_listener(self, callback):
        with self._mp_test_listeners_lock:
            self._mp_test_listeners = [
                cb for cb in self._mp_test_listeners if cb != callback
            ]
            self._mp_confirm_listeners = [
                cb for cb in self._mp_confirm_listeners if cb != callback
            ]

    def start_side_button_confirm(self, listener):
        """Capture the next physical side button(s) for the settings UI."""
        self._mp_confirm_active = True
        with self._mp_test_listeners_lock:
            if listener not in self._mp_confirm_listeners:
                self._mp_confirm_listeners.append(listener)
            if listener not in self._mp_test_listeners:
                self._mp_test_listeners.append(listener)
        if hasattr(self.hook, "set_test_mode"):
            self.hook.set_test_mode(self._mp_capture_active())

    def cancel_side_button_confirm(self):
        self._mp_confirm_active = False
        with self._mp_test_listeners_lock:
            confirmers = list(self._mp_confirm_listeners)
            self._mp_confirm_listeners = []
            self._mp_test_listeners = [
                cb for cb in self._mp_test_listeners if cb not in confirmers
            ]
        if hasattr(self.hook, "set_test_mode"):
            self.hook.set_test_mode(self._mp_capture_active())

    def save_confirmed_side_buttons(self, buttons):
        self._mp_confirm_active = False
        with self._mp_test_listeners_lock:
            self._mp_confirm_listeners = []
        if hasattr(self.hook, "set_test_mode"):
            self.hook.set_test_mode(self._mp_capture_active())
        return self.set_screenshot_side_buttons(buttons)

    # -- quick actions / usage stats ------------------------------------

    def run_quick_action(self, action_id):
        """Execute a MousePro quick action; returns ok/detail, never raises."""
        if sys.platform != "win32":
            return {"ok": False, "detail": "MousePro actions require Windows."}
        from core import system_actions

        try:
            result = system_actions.execute_quick_action(action_id)
            return {"ok": result.success, "detail": result.detail}
        except Exception as exc:
            return {"ok": False, "detail": str(exc)}

    def get_usage_stats(self):
        stats = getattr(self, "_mp_shared_stats", None)
        if stats is None:
            return {}
        return stats.snapshot()

    def reset_usage_stats(self):
        stats = getattr(self, "_mp_shared_stats", None)
        if stats is not None:
            stats.reset()


    def _hid_runtime_state(self):
        state = getattr(self.hook, "hid_runtime_state", None)
        if state is not None:
            return state
        hg = getattr(self.hook, "_hid_gesture", None)
        hid_device = getattr(hg, "connected_device", None) if hg else None
        return HidRuntimeState(
            input_ready=bool(getattr(self.hook, "device_connected", False)),
            hid_ready=hid_device is not None,
            connected_device=getattr(self.hook, "connected_device", None),
        )

    def _binding_route_identity(self):
        device = self._hid_runtime_state().connected_device
        if device is None:
            return None
        return tuple(
            getattr(device, field, None)
            for field in ("key", "product_id", "transport", "source")
        )

    def _reset_backend_identity_tracking(self):
        """Forget stopped-backend identity without publishing new bindings."""
        self._last_connection_state = False
        self._last_hid_features_ready = False
        self._last_binding_route_identity = None
        self._battery_poll_stop.set()
        if self._battery_poll_thread is not None:
            self._battery_poll_thread.join(timeout=5)
            self._battery_poll_thread = None

    # ------------------------------------------------------------------
    # Hook wiring
    # ------------------------------------------------------------------
    def _setup_hooks(self, bindings):
        """Register callbacks and block events for all mapped buttons."""
        mappings = get_active_mappings(self.cfg)
        bindings.set_lifecycle_invalidator(self._invalidate_press_lifecycle)
        generic_mouse_enabled = self._generic_mouse_enabled()
        hid_route_keys = {
            "gesture",
            *GESTURE_DIRECTION_BUTTONS,
            "mode_shift",
            long_press_mapping_key("mode_shift"),
            "dpi_switch",
        }
        if not generic_mouse_enabled:
            for button in WINDOWS_XBUTTON_KEYS:
                hid_route_keys.add(button)
                hid_route_keys.add(long_press_mapping_key(button))
        configured_hid_required = bool(
            sys.platform == "win32"
            and any(
                profile.get("mappings", {}).get(key, "none") != "none"
                for profile in self.cfg.get("profiles", {}).values()
                for key in hid_route_keys
            )
        )
        if hasattr(self.hook, "set_hid_listener_required"):
            self.hook.set_hid_listener_required(configured_hid_required)

        # Apply scroll inversion settings to the hook
        settings = self.cfg.get("settings", {})
        self.hook.invert_vscroll = settings.get("invert_vscroll", False)
        self.hook.invert_hscroll = settings.get("invert_hscroll", False)
        if hasattr(self.hook, "ignore_trackpad"):
            self.hook.ignore_trackpad = settings.get("ignore_trackpad", True)
        self.hook.debug_mode = self._debug_events_enabled
        device = getattr(self, "connected_device", None)
        device_supports_gesture = self._device_supports_gesture_button(device)
        self.hook.configure_gestures(
            enabled=(
                device_supports_gesture
                and any(
                    mappings.get(key, "none") != "none"
                    for key in GESTURE_DIRECTION_BUTTONS
                )
            ),
            threshold=settings.get("gesture_threshold", 50),
            deadzone=settings.get("gesture_deadzone", 40),
            timeout_ms=settings.get("gesture_timeout_ms", 3000),
            cooldown_ms=settings.get("gesture_cooldown_ms", 500),
        )
        # Divert mode shift CID only when the device has the button and
        # at least one profile maps it to an action.  When no device is
        # connected yet, assume the button exists (safe: if the device
        # turns out not to have it, the divert simply has no effect).
        device_buttons = get_reprogrammable_buttons(device)
        inventory = getattr(device, "capability_inventory", None)
        control_cids = set(getattr(inventory, "control_cids", ()) or ())
        has_runtime_controls = bool(
            getattr(inventory, "has_reprog_controls", False)
        )
        logi_xbutton_routes = {}
        if (
            sys.platform == "win32"
            and not generic_mouse_enabled
            and has_runtime_controls
        ):
            for button, cid in _LOGI_XBUTTON_CIDS.items():
                if button in (device_buttons or ()) and cid in control_cids:
                    logi_xbutton_routes[button] = button
        xbutton_routes = {
            button: resolve_windows_xbutton_mapping_key(
                button,
                generic_mouse_enabled=generic_mouse_enabled,
                platform_name=sys.platform,
            )
            for button in WINDOWS_XBUTTON_KEYS
        }
        if self._debug_events_enabled and sys.platform == "win32":
            device_key = getattr(device, "key", "") or "unresolved"
            transport = getattr(device, "transport", "") or "unknown"
            for physical_key in sorted(WINDOWS_XBUTTON_KEYS):
                mapping_key = xbutton_routes[physical_key]
                action_id = mappings.get(mapping_key, "none") if mapping_key else "none"
                long_action_id = (
                    mappings.get(long_press_mapping_key(mapping_key), "none")
                    if mapping_key
                    else "none"
                )
                self._emit_debug(
                    "XBUTTON route "
                    f"profile={self._current_profile} device={device_key} "
                    f"transport={transport} physical={physical_key} "
                    f"logical={mapping_key or 'native'} action={action_id} "
                    f"long_action={long_action_id}"
                )
        for mapping_key in xbutton_routes.values():
            if not mapping_key:
                continue
            for event_type in BUTTON_TO_EVENTS.get(mapping_key, ()):
                bindings.set_route(event_type, mapping_key)
        has_mode_shift = device_buttons is None or "mode_shift" in device_buttons
        self.hook.divert_mode_shift = (
            has_mode_shift
            and any(
                pdata.get("mappings", {}).get("mode_shift", "none") != "none"
                or pdata.get("mappings", {}).get(long_press_mapping_key("mode_shift"), "none") != "none"
                for pdata in self.cfg.get("profiles", {}).values()
            )
        )

        # Divert DPI switch CID (0x00FD) on MX Vertical when mapped.
        has_dpi_switch = device_buttons is None or "dpi_switch" in device_buttons
        self.hook.divert_dpi_switch = (
            has_dpi_switch
            and any(
                pdata.get("mappings", {}).get("dpi_switch", "none") != "none"
                for pdata in self.cfg.get("profiles", {}).values()
            )
        )
        for button in WINDOWS_XBUTTON_KEYS:
            should_divert = (
                logi_xbutton_routes.get(button) == button
                and any(
                    pdata.get("mappings", {}).get(button, "none") != "none"
                    or pdata.get("mappings", {}).get(
                        long_press_mapping_key(button), "none"
                    ) != "none"
                    for pdata in self.cfg.get("profiles", {}).values()
                )
            )
            setattr(self.hook, f"divert_logi_{button}", should_divert)
            if should_divert and self._debug_events_enabled:
                cid = _LOGI_XBUTTON_CIDS[button]
                device_key = getattr(device, "key", "") or "unresolved"
                self._emit_debug(
                    "Logitech binding route "
                    f"device={device_key} cid=0x{cid:04X} detected={button} "
                    f"profile={self._current_profile} logical={button} "
                    f"action={mappings.get(button, 'none')}"
                )
        if hasattr(self.hook, "sync_hid_extra_diverts"):
            self.hook.sync_hid_extra_diverts()

        self._emit_mapping_snapshot("Hook mappings refreshed", mappings)

        for btn_key, action_id in mappings.items():
            if btn_key.endswith("_long"):
                continue
            if btn_key in GENERIC_MOUSE_BUTTONS:
                physical_key = btn_key.removeprefix("generic_")
                if xbutton_routes.get(physical_key) != btn_key:
                    continue
            elif btn_key in WINDOWS_XBUTTON_KEYS:
                if (
                    xbutton_routes.get(btn_key) != btn_key
                    and logi_xbutton_routes.get(btn_key) != btn_key
                ):
                    continue
            elif not self._should_bind_middle_button(
                btn_key,
                generic_mouse_enabled,
                device_buttons,
            ):
                continue
            if btn_key.startswith("gesture") and not device_supports_gesture:
                continue
            events = list(BUTTON_TO_EVENTS.get(btn_key, ()))
            if logi_xbutton_routes.get(btn_key) == btn_key:
                events = list(_LOGI_XBUTTON_EVENTS[btn_key])
            for event_type in events:
                bindings.set_route(event_type, btn_key)
            long_action_id = mappings.get(long_press_mapping_key(btn_key), "none")
            has_multi_action = (
                supports_multi_action(btn_key)
                and long_action_id != "none"
                and any(e.endswith("_down") for e in events)
                and any(e.endswith("_up") for e in events)
            )
            if has_multi_action:
                for evt_type in events:
                    bindings.block(evt_type)
                    if evt_type.endswith("_down"):
                        bindings.register(
                            evt_type,
                            self._make_multi_action_down_handler(
                                btn_key,
                                action_id,
                                long_action_id,
                            ),
                        )
                    elif evt_type.endswith("_up"):
                        bindings.register(
                            evt_type,
                            self._make_multi_action_up_handler(
                                btn_key,
                                action_id,
                                long_action_id,
                            ),
                        )
                continue

            has_paired_down = any(e.endswith("_down") for e in events)
            has_up = any(e.endswith("_up") for e in events)

            for evt_type in events:
                if has_paired_down and evt_type.endswith("_up"):
                    if action_id != "none":
                        bindings.block(evt_type)
                        if is_mouse_button_action(action_id):
                            bindings.register(evt_type, self._make_mouse_up_handler(action_id))
                    continue

                if action_id != "none":
                    bindings.block(evt_type)

                    if "hscroll" in evt_type:
                        bindings.register(evt_type, self._make_hscroll_handler(action_id))
                    elif is_mouse_button_action(action_id):
                        if has_up:
                            # Button has a matching _up event → split press/release
                            bindings.register(evt_type, self._make_mouse_down_handler(action_id))
                        else:
                            # Single-fire event (gesture, swipe) → full click
                            bindings.register(evt_type, self._make_handler(action_id))
                    else:
                        bindings.register(evt_type, self._make_handler(action_id))

    def _replace_bindings(self, reason):
        """Build and publish one generation, then remove only retired state.

        Publication drains admitted callbacks before returning.  The engine
        state lock is acquired afterward, so mapped actions never run under it.
        """
        bindings = self.hook.new_binding_builder()
        self._setup_hooks(bindings)
        snapshot = self.hook.publish_bindings(bindings)
        with self._binding_state_lock:
            self._multi_action_down_at = {
                key: value
                for key, value in self._multi_action_down_at.items()
                if key[0] == snapshot.generation
            }
        self._emit_debug(
            f"Bindings replaced generation={snapshot.generation} reason={reason}"
        )
        health = self.input_health()
        print(
            "[InputRuntime] HOOK_REBUILD "
            f"reason={reason} generation={snapshot.generation}"
        )
        print(
            "[InputRuntime] MAPPING_CONFIGURED_COUNT "
            f"count={health.configured_mapping_count} profile={self._current_profile}"
        )
        print(
            "[InputRuntime] MAPPING_BOUND_COUNT "
            f"count={health.bound_mapping_count} profile={self._current_profile}"
        )
        return snapshot

    def _reload_config_in_place(self, *, strict=True):
        """Refresh the shared config object without breaking Backend authority."""
        current = load_config(strict=strict)
        self.cfg.clear()
        self.cfg.update(current)
        mark_config_verified_writable(self.cfg)
        self._current_profile = self.cfg.get("active_profile", "default")

    def input_health(self):
        """Return explicit configuration, binding, and backend health state."""
        health_getter = getattr(self.hook, "health_snapshot", None)
        if health_getter is None:
            health = HookHealth(backend=sys.platform, healthy=True)
        else:
            health = health_getter()
        mappings = get_active_mappings(self.cfg)
        configured = {
            key for key, action in mappings.items() if action != "none"
        }
        snapshot = self.hook.capture_binding_snapshot()
        bound_routes = {
            snapshot.routes.get(event_type)
            for event_type, callbacks in snapshot.callbacks.items()
            if callbacks and snapshot.routes.get(event_type)
        }
        bound = sum(
            1
            for key in configured
            if (key[:-5] if key.endswith("_long") else key) in bound_routes
        )
        return replace(
            health,
            configured_mapping_count=len(configured),
            bound_mapping_count=bound,
        )

    def _recover_backend_once(self, reason):
        """Stop and rebuild only the input backend from authoritative config."""
        with self._backend_recovery_lock:
            print(f"[InputRuntime] HOOK_RECOVERY phase=start reason={reason}")
            stopped = self.hook.stop()
            if stopped is False:
                print(
                    "[InputRuntime] HOOK_FAILURE phase=stop "
                    f"reason={reason} error=backend-did-not-stop"
                )
                return False
            self._reset_backend_identity_tracking()
            self._release_active_mouse_holds("hook-recovery")
            with self._lock:
                # Engine.cfg is shared with Backend and is the current
                # authoritative document. Recovery is runtime-only: it must
                # neither replace that object nor write config.json.
                self.hook.reset_bindings(wait_timeout=1.0)
                with self._binding_state_lock:
                    self._multi_action_down_at.clear()
                self._replace_bindings("hook-recovery")
            recovered = False
            try:
                started = self.hook.start()
                health = self.input_health()
                recovered = started is not False and health.healthy
            except Exception as exc:
                import traceback

                print(
                    "[InputRuntime] BACKEND_EXCEPTION "
                    f"context=recovery-start reason={reason} error={exc!r} "
                    f"traceback={traceback.format_exc().strip()}"
                )
            finally:
                if not recovered:
                    try:
                        cleanup_stopped = self.hook.stop()
                    except Exception as exc:
                        import traceback

                        cleanup_stopped = False
                        print(
                            "[InputRuntime] BACKEND_EXCEPTION "
                            f"context=recovery-cleanup reason={reason} "
                            f"error={exc!r} "
                            f"traceback={traceback.format_exc().strip()}"
                        )
                    if cleanup_stopped is False:
                        print(
                            "[InputRuntime] HOOK_FAILURE phase=recovery-cleanup "
                            f"reason={reason} error=backend-did-not-stop"
                        )
                    else:
                        self._reset_backend_identity_tracking()
            print(
                "[InputRuntime] HOOK_RECOVERY "
                f"phase=complete reason={reason} healthy={recovered}"
            )
            return recovered

    def _release_active_mouse_holds(self, reason):
        timers = list(self._mouse_release_timers.items())
        self._mouse_release_timers.clear()
        for action_id, timer in timers:
            timer.cancel()
            try:
                inject_mouse_up(action_id)
            except Exception as exc:
                import traceback

                print(
                    "[InputRuntime] BACKEND_EXCEPTION "
                    f"context=mouse-hold-release reason={reason} "
                    f"action={action_id} error={exc!r} "
                    f"traceback={traceback.format_exc().strip()}"
                )

    def _check_backend_health_once(self):
        """Check once and perform at most one bounded recovery attempt."""
        health = self.input_health()
        if health.healthy:
            self._backend_recovery_attempts = 0
            self._backend_recovery_exhausted = False
            return True
        if self._backend_recovery_exhausted:
            return False
        self._backend_recovery_attempts += 1
        attempt = self._backend_recovery_attempts
        reason = health.last_backend_exception or "backend-unhealthy"
        print(
            "[InputRuntime] HOOK_FAILURE "
            f"attempt={attempt} reason={reason} backend={health.backend}"
        )
        if self._recover_backend_once(reason):
            self._backend_recovery_attempts = 0
            return True
        if attempt >= len(BACKEND_RECOVERY_BACKOFF_S):
            self._backend_recovery_exhausted = True
            print(
                "[InputRuntime] HOOK_FAILURE phase=hard-failure "
                f"attempts={attempt} backend={health.backend}"
            )
        return False

    def _backend_watchdog_loop(self):
        while not self._backend_watchdog_stop.wait(BACKEND_HEALTH_INTERVAL_S):
            if self._backend_recovery_attempts:
                delay = BACKEND_RECOVERY_BACKOFF_S[
                    min(
                        self._backend_recovery_attempts,
                        len(BACKEND_RECOVERY_BACKOFF_S) - 1,
                    )
                ]
                if delay and self._backend_watchdog_stop.wait(delay):
                    return
            try:
                self._check_backend_health_once()
            except Exception as exc:
                import traceback

                print(
                    "[InputRuntime] BACKEND_EXCEPTION context=health-watchdog "
                    f"error={exc!r} traceback={traceback.format_exc().strip()}"
                )

    def _start_backend_watchdog(self):
        if self._backend_watchdog_thread and self._backend_watchdog_thread.is_alive():
            return
        self._backend_watchdog_stop.clear()
        self._backend_watchdog_thread = threading.Thread(
            target=self._backend_watchdog_loop,
            daemon=True,
            name="InputHealthWatchdog",
        )
        self._backend_watchdog_thread.start()

    def _stop_backend_watchdog(self):
        self._backend_watchdog_stop.set()
        thread = self._backend_watchdog_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=10)
        if thread and thread.is_alive():
            print(
                "[InputRuntime] HOOK_FAILURE phase=watchdog-stop "
                "error=watchdog-did-not-stop"
            )
            return False
        self._backend_watchdog_thread = None
        return True

    def _invalidate_press_lifecycle(self, generation, route):
        with self._binding_state_lock:
            self._multi_action_down_at.pop((generation, route), None)

    def _generic_mouse_enabled(self):
        if sys.platform != "win32":
            return False
        return bool(self.cfg.get("settings", {}).get("generic_mouse_enabled", False))

    def _should_bind_middle_button(self, button_key, generic_mouse_enabled, device_buttons):
        if button_key != "middle":
            return True
        if sys.platform != "win32":
            return True
        if generic_mouse_enabled:
            return True
        return device_buttons is not None and "middle" in device_buttons

    def _execute_mapped_action(self, action_id, event_type=None):
        if action_id == "none":
            return
        if action_id == "toggle_smart_shift":
            self._toggle_smart_shift()
        elif action_id == "switch_scroll_mode":
            self._switch_scroll_mode()
        elif action_id == "cycle_dpi":
            self._cycle_dpi()
        else:
            if event_type:
                print(f"[Engine] Dispatch {event_type} -> {action_id}")
            execute_action(action_id)

    def _make_handler(self, action_id):
        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped logical={getattr(event, 'binding_route', None) or 'unknown'} "
                        f"event={event.event_type} action={action_id} "
                        f"({self._action_label(action_id)})"
                    )
                    if event.event_type.startswith("gesture_"):
                        self._emit_gesture_event({
                            "type": "mapped",
                            "event_name": event.event_type,
                            "action_id": action_id,
                            "action_label": self._action_label(action_id),
                        })
                    self._execute_mapped_action(action_id, event.event_type)
            except Exception as exc:
                print(f"[Engine] _make_handler EXCEPTION for {action_id}: {exc}")
                raise
        return handler

    def _multi_action_threshold_s(self):
        value = self.cfg.get("settings", {}).get(
            "multi_action_long_press_threshold_ms",
            DEFAULT_LONG_PRESS_THRESHOLD_MS,
        )
        try:
            return max(1, int(value)) / 1000.0
        except (TypeError, ValueError):
            return DEFAULT_LONG_PRESS_THRESHOLD_MS / 1000.0

    def _make_multi_action_down_handler(self, button_key, click_action_id, long_action_id):
        def handler(event):
            try:
                if self._enabled:
                    event_generation = getattr(
                        event,
                        "binding_generation",
                        self.hook.capture_binding_snapshot().generation,
                    )
                    with self._binding_state_lock:
                        state_key = (event_generation, button_key)
                        self._multi_action_down_at[state_key] = time.monotonic()
                    self._emit_debug(
                        f"{button_key} down generation={event_generation} "
                        f"-> armed click={click_action_id} "
                        f"long={long_action_id}"
                    )
            except Exception as exc:
                print(f"[Engine] multi_action_down_handler EXCEPTION for {button_key}: {exc}")
                raise
        return handler

    def _make_multi_action_up_handler(self, button_key, click_action_id, long_action_id):
        def handler(event):
            try:
                if not self._enabled:
                    return
                now = time.monotonic()
                event_generation = getattr(
                    event,
                    "binding_generation",
                    self.hook.capture_binding_snapshot().generation,
                )
                with self._binding_state_lock:
                    state_key = (event_generation, button_key)
                    down_at = self._multi_action_down_at.pop(state_key, None)
                if down_at is None:
                    self._emit_debug(
                        f"Ignored unmatched {button_key} up "
                        f"generation={event_generation}"
                    )
                    return
                held_s = max(0.0, now - down_at)
                held_ms = int(round(held_s * 1000))
                if held_s >= self._multi_action_threshold_s():
                    print(f"[Engine] {button_key} long press ({held_ms}ms) -> {long_action_id}")
                    self._emit_debug(
                        f"{button_key} long press ({held_ms}ms) -> {long_action_id}"
                    )
                    self._execute_mapped_action(long_action_id, event.event_type)
                else:
                    print(f"[Engine] {button_key} click ({held_ms}ms) -> {click_action_id}")
                    self._emit_debug(
                        f"{button_key} click ({held_ms}ms) -> {click_action_id} "
                        f"({self._action_label(click_action_id)})"
                    )
                    self._execute_mapped_action(click_action_id, event.event_type)
            except Exception as exc:
                print(f"[Engine] multi_action_up_handler EXCEPTION for {button_key}: {exc}")
                raise
        return handler

    def _make_mouse_down_handler(self, action_id):
        def _safety_release():
            """Auto-release if the UP event never fires."""
            try:
                print(f"[Engine] SAFETY RELEASE fired for {action_id} (UP never received)")
                self._mouse_release_timers.pop(action_id, None)
                inject_mouse_up(action_id)
            except Exception as exc:
                import traceback

                print(
                    "[InputRuntime] BACKEND_EXCEPTION "
                    f"context=safety-release action={action_id} error={exc!r} "
                    f"traceback={traceback.format_exc().strip()}"
                )

        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped logical={getattr(event, 'binding_route', None) or 'unknown'} "
                        f"event={event.event_type} action={action_id} (mouse down)"
                    )
                    inject_mouse_down(action_id)
                    # Safety: auto-release after 20s if UP event is never received
                    old = self._mouse_release_timers.pop(action_id, None)
                    if old is not None:
                        old.cancel()
                    t = threading.Timer(20.0, _safety_release)
                    t.daemon = True
                    self._mouse_release_timers[action_id] = t
                    t.start()
            except Exception as exc:
                print(f"[Engine] mouse_down_handler EXCEPTION for {action_id}: {exc}")
                raise
        return handler

    def _make_mouse_up_handler(self, action_id):
        def handler(event):
            try:
                if self._enabled:
                    self._emit_debug(
                        f"Mapped logical={getattr(event, 'binding_route', None) or 'unknown'} "
                        f"event={event.event_type} action={action_id} (mouse up)"
                    )
                    # Cancel safety timer
                    old = self._mouse_release_timers.pop(action_id, None)
                    if old is not None:
                        old.cancel()
                    inject_mouse_up(action_id)
            except Exception as exc:
                print(f"[Engine] mouse_up_handler EXCEPTION for {action_id}: {exc}")
                raise
        return handler

    def _toggle_smart_shift(self):
        """Toggle SmartShift auto-switching on/off.

        IMPORTANT: this is called from a HID event callback which runs on the HID
        loop thread.  Calling hg.set_smart_shift() directly would block waiting for
        the same loop to process the pending request — a deadlock that causes the
        3-second timeout seen in the logs.  Config and UI are updated synchronously;
        the device write is dispatched to a separate thread.
        """
        with self._lock:
            settings = self.cfg.get("settings", {})
            new_enabled = not settings.get("smart_shift_enabled", False)
            mode = settings.get("smart_shift_mode", "ratchet")
            threshold = settings.get("smart_shift_threshold", 25)
            print(f"[Engine] toggle_smart_shift -> enabled={new_enabled}")
            settings["smart_shift_enabled"] = new_enabled
            save_config(self.cfg)
        if self._smart_shift_read_cb:
            try:
                self._smart_shift_read_cb({"mode": mode, "enabled": new_enabled, "threshold": threshold})
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                if self._device_supports_smart_shift(
                    getattr(hg, "connected_device", None)
                ):
                    ok = hg.set_smart_shift(mode, new_enabled, threshold)
                    print(f"[Engine] toggle_smart_shift device write -> {'OK' if ok else 'FAILED'}")
            threading.Thread(target=_write, daemon=True, name="ToggleSmartShift").start()

    def _switch_scroll_mode(self):
        """Switch between ratchet and free-spin using the device's mode control.

        SmartShift auto-switching is disabled so the chosen fixed mode takes effect.
        Same deadlock caveat as _toggle_smart_shift — device write runs off-thread.
        """
        with self._lock:
            settings = self.cfg.get("settings", {})
            current_mode = settings.get("smart_shift_mode", "ratchet")
            new_mode = "freespin" if current_mode == "ratchet" else "ratchet"
            threshold = settings.get("smart_shift_threshold", 25)
            print(f"[Engine] switch_scroll_mode -> {new_mode}")
            settings["smart_shift_mode"] = new_mode
            settings["smart_shift_enabled"] = False
            save_config(self.cfg)
        if self._smart_shift_read_cb:
            try:
                self._smart_shift_read_cb({"mode": new_mode, "enabled": False, "threshold": threshold})
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                if self._device_supports_smart_shift(
                    getattr(hg, "connected_device", None)
                ):
                    ok = hg.set_smart_shift(new_mode, False, threshold)
                    print(f"[Engine] switch_scroll_mode device write -> {'OK' if ok else 'FAILED'}")
            threading.Thread(target=_write, daemon=True, name="SwitchScrollMode").start()

    _DEFAULT_DPI_PRESETS = [800, 1200, 1600, 2400]

    def _cycle_dpi(self):
        """Cycle through user-configured DPI presets.

        Advances to the next preset in the list.  If the current DPI doesn't
        match any preset, jumps to the first one.  Updates config, notifies
        the UI, and writes to the device off-thread.
        """
        with self._lock:
            settings = self.cfg.setdefault("settings", {})
            presets = settings.get("dpi_presets") or list(self._DEFAULT_DPI_PRESETS)
            if not presets:
                return
            current_dpi = settings.get("dpi", 1000)
            try:
                idx = presets.index(current_dpi)
                next_idx = (idx + 1) % len(presets)
            except ValueError:
                next_idx = 0
            new_dpi = clamp_dpi(presets[next_idx], self.connected_device)
            print(f"[Engine] cycle_dpi {current_dpi} -> {new_dpi} (preset {next_idx + 1}/{len(presets)})")
            settings["dpi"] = new_dpi
            save_config(self.cfg)
        if self._dpi_read_cb:
            try:
                self._dpi_read_cb(new_dpi)
            except Exception:
                pass
        hg = self.hook._hid_gesture
        if hg:
            def _write():
                if self._device_supports_adjustable_dpi(
                    getattr(hg, "connected_device", None)
                ):
                    hg.set_dpi(new_dpi)
            threading.Thread(target=_write, daemon=True, name="CycleDPI").start()

    def _make_hscroll_handler(self, action_id):
        def handler(event):
            if not self._enabled:
                return
            state = self._hscroll_state.setdefault(
                event.event_type,
                {"accum": 0.0, "last_fire_at": 0.0},
            )
            step = self._hscroll_step(event.raw_data)
            threshold = self._hscroll_threshold()
            now = getattr(event, "timestamp", None) or time.time()

            cooldown = HSCROLL_VOLUME_COOLDOWN_S if action_id in _VOLUME_ACTIONS else HSCROLL_ACTION_COOLDOWN_S
            if now - state["last_fire_at"] < cooldown:
                state["accum"] = 0.0
                return

            state["accum"] += step
            if state["accum"] < threshold:
                return

            state["accum"] = 0.0
            state["last_fire_at"] = now
            self._emit_debug(
                f"Mapped {event.event_type} -> {action_id} "
                f"({self._action_label(action_id)})"
            )
            execute_action(action_id)
        return handler

    def _hscroll_step(self, raw_value):
        if not isinstance(raw_value, (int, float)):
            return 1.0

        # Treat large wheel deltas as a single logical step while preserving
        # sub-step deltas from macOS event tap scrolling.
        return min(abs(float(raw_value)), 1.0)

    def _hscroll_threshold(self):
        return max(
            0.1,
            float(self.cfg.get("settings", {}).get("hscroll_threshold", 1)),
        )

    # ------------------------------------------------------------------
    # Per-app auto-switching
    # ------------------------------------------------------------------
    def _on_app_change(self, exe_name: str):
        """Called by AppDetector when foreground window changes."""
        target = get_profile_for_app(self.cfg, exe_name)
        if target == self._current_profile:
            return
        print(f"[Engine] App changed to {exe_name} -> profile '{target}'")
        self._switch_profile(target)

    def _switch_profile(self, profile_name: str):
        with self._lock:
            self.cfg["active_profile"] = profile_name
            self._current_profile = profile_name
            # Lightweight: just re-wire callbacks, keep hook + HID++ alive
            self._replace_bindings(f"profile:{profile_name}")
            self._emit_debug(f"Active profile -> {profile_name}")
        # Notify UI (if connected)
        if self._profile_change_cb:
            try:
                self._profile_change_cb(profile_name)
            except Exception:
                pass

    def set_profile_change_callback(self, cb):
        """Register a callback ``cb(profile_name)`` invoked on auto-switch."""
        self._profile_change_cb = cb

    def set_debug_callback(self, cb):
        """Register ``cb(message: str)`` invoked for debug events."""
        self._debug_cb = cb

    def set_status_callback(self, cb):
        """Register ``cb(message: str)`` invoked for status messages."""
        self._status_cb = cb

    def set_gesture_event_callback(self, cb):
        """Register ``cb(event: dict)`` invoked for structured gesture debug events."""
        self._gesture_event_cb = cb

    def set_debug_enabled(self, enabled):
        enabled = bool(enabled)
        self.cfg.setdefault("settings", {})["debug_mode"] = enabled
        self._debug_events_enabled = enabled
        self.hook.debug_mode = enabled
        if enabled:
            self._emit_debug(f"Debug enabled on profile {self._current_profile}")
            self._emit_mapping_snapshot(
                "Current mappings", get_active_mappings(self.cfg)
            )

    def set_debug_events_enabled(self, enabled):
        self._debug_events_enabled = bool(enabled)
        self.hook.debug_mode = self._debug_events_enabled

    def _action_label(self, action_id):
        return ACTIONS.get(action_id, {}).get("label", action_id)

    def _emit_debug(self, message):
        if not self._debug_events_enabled:
            return
        if self._debug_cb:
            try:
                self._debug_cb(message)
            except Exception:
                pass

    def _emit_status(self, message):
        if self._status_cb:
            try:
                self._status_cb(message)
            except Exception:
                pass

    def _emit_gesture_event(self, event):
        if not self._debug_events_enabled:
            return
        if self._gesture_event_cb:
            try:
                self._gesture_event_cb(event)
            except Exception:
                pass

    def _emit_mapping_snapshot(self, prefix, mappings):
        if not self._debug_events_enabled:
            return
        interesting = [
            "gesture",
            "gesture_left",
            "gesture_right",
            "gesture_up",
            "gesture_down",
            "xbutton1",
            "xbutton2",
        ]
        summary = ", ".join(f"{key}={mappings.get(key, 'none')}" for key in interesting)
        self._emit_debug(f"{prefix}: {summary}")

    def _saved_smart_shift_state(self):
        settings = self.cfg.get("settings", {})
        return {
            "mode": settings.get("smart_shift_mode", "ratchet"),
            "enabled": settings.get("smart_shift_enabled", False),
            "threshold": settings.get("smart_shift_threshold", 25),
        }

    def _run_saved_settings_replay(self):
        hg = self.hook._hid_gesture
        if hg is None:
            return False
        if hasattr(hg, "connected_device") and hg.connected_device is None:
            return False

        replay_ok = True
        retry_dpi = False
        retry_smart_shift = False
        saved_dpi = self.cfg.get("settings", {}).get("dpi")

        saved_ss_state = self._saved_smart_shift_state()
        saved_ss = saved_ss_state["mode"]
        ss_enabled = saved_ss_state["enabled"]
        ss_threshold = saved_ss_state["threshold"]

        # Phase A: apply Smart Shift immediately so the physical wheel mode
        # converges before the settled replay.
        if (
            saved_ss
            and getattr(hg, "smart_shift_supported", False)
            and self._device_supports_smart_shift(
                getattr(hg, "connected_device", None)
            )
        ):
            if not hasattr(hg, "set_smart_shift"):
                replay_ok = False
            else:
                if not hg.set_smart_shift(saved_ss, ss_enabled, ss_threshold):
                    replay_ok = False
                if self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass

        time.sleep(3)
        hg = self.hook._hid_gesture
        if hg is None or getattr(hg, "connected_device", None) is None:
            return False

        if saved_dpi is not None:
            if not self._device_supports_adjustable_dpi(hg.connected_device):
                replay_ok = False
            elif not hasattr(hg, "set_dpi"):
                replay_ok = False
            elif hg.set_dpi(saved_dpi):
                if self._dpi_read_cb:
                    try:
                        self._dpi_read_cb(saved_dpi)
                    except Exception:
                        pass
            else:
                replay_ok = False
                retry_dpi = True

        if (
            saved_ss
            and getattr(hg, "smart_shift_supported", False)
            and self._device_supports_smart_shift(hg.connected_device)
        ):
            if not hasattr(hg, "set_smart_shift"):
                replay_ok = False
            elif hg.set_smart_shift(saved_ss, ss_enabled, ss_threshold):
                if self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass
            else:
                replay_ok = False
                retry_smart_shift = True

        if retry_dpi or retry_smart_shift:
            time.sleep(5)
            hg = self.hook._hid_gesture
            if hg is None or getattr(hg, "connected_device", None) is None:
                return False
            if retry_dpi:
                if (
                    not self._device_supports_adjustable_dpi(hg.connected_device)
                    or not hasattr(hg, "set_dpi")
                    or not hg.set_dpi(saved_dpi)
                ):
                    replay_ok = False
                elif self._dpi_read_cb:
                    try:
                        self._dpi_read_cb(saved_dpi)
                    except Exception:
                        pass
            if (
                retry_smart_shift
                and getattr(hg, "smart_shift_supported", False)
                and self._device_supports_smart_shift(hg.connected_device)
            ):
                if not hasattr(hg, "set_smart_shift") or not hg.set_smart_shift(
                    saved_ss, ss_enabled, ss_threshold
                ):
                    replay_ok = False
                elif self._smart_shift_read_cb:
                    try:
                        self._smart_shift_read_cb(saved_ss_state)
                    except Exception:
                        pass

        return replay_ok

    def _replay_saved_settings_worker(self):
        while True:
            with self._replay_lock:
                self._replay_pending_rerun = False
            replay_ok = self._run_saved_settings_replay()
            should_emit_failure = False
            with self._replay_lock:
                if self._replay_pending_rerun:
                    continue
                self._replay_inflight = False
                should_emit_failure = not replay_ok
            if should_emit_failure:
                self._emit_status(
                    "Mouse reconnected, but saved device settings could not be restored yet."
                )
            return

    def _request_saved_settings_replay(self, *, startup_fallback=False):
        with self._replay_lock:
            if startup_fallback and self._hid_replay_requested_this_launch:
                return
            if self._replay_inflight:
                self._replay_pending_rerun = True
                return
            self._hid_replay_requested_this_launch = True
            self._replay_inflight = True
        if startup_fallback:
            self._emit_status("Using startup fallback to replay saved device settings")
        threading.Thread(
            target=self._replay_saved_settings_worker,
            daemon=True,
            name="SavedSettingsReplay",
        ).start()

    def _on_connection_change(self, connected):
        connection_changed = connected != self._last_connection_state
        hid_features_ready = self.hid_features_ready
        hid_features_changed = hid_features_ready != self._last_hid_features_ready
        route_identity = self._binding_route_identity()
        route_changed = route_identity != self._last_binding_route_identity
        if connection_changed:
            self._last_connection_state = connected
            self._battery_poll_stop.set()
            if self._battery_poll_thread is not None:
                self._battery_poll_thread.join(timeout=5)
                self._battery_poll_thread = None
        self._last_hid_features_ready = hid_features_ready
        self._last_binding_route_identity = route_identity
        if connection_changed or hid_features_changed or route_changed:
            with self._lock:
                self._replace_bindings(
                    "connection"
                    if connection_changed
                    else "hid-readiness"
                    if hid_features_changed
                    else "device-route"
                )
        if self._connection_change_cb:
            try:
                self._connection_change_cb(connected)
            except Exception:
                pass
        if connected and connection_changed:
            self._battery_poll_stop = threading.Event()
            self._battery_poll_thread = threading.Thread(
                target=self._battery_poll_loop,
                args=(self._battery_poll_stop,),
                daemon=True,
                name="BatteryPoll",
            )
            self._battery_poll_thread.start()
        if hid_features_ready and hid_features_changed:
            self._request_saved_settings_replay()

    def _battery_poll_loop(self, stop_event):
        """Read battery and smart shift mode periodically until disconnected."""
        _battery_poll_interval = 300   # seconds between battery reads
        _ss_poll_interval = 15         # seconds between scroll-mode reads
        _last_battery = time.time() - _battery_poll_interval  # fire immediately
        _last_ss = time.time() - _ss_poll_interval            # fire immediately
        _last_ss_mode = None

        while not stop_event.is_set():
            now = time.time()
            hg = self.hook._hid_gesture
            if hg and hg.connected_device is not None:
                if now - _last_battery >= _battery_poll_interval:
                    _last_battery = now
                    if self._device_supports_battery_status(hg.connected_device):
                        level = hg.read_battery()
                        if stop_event.is_set():
                            return
                        if level is not None and self._battery_read_cb:
                            try:
                                self._battery_read_cb(level)
                            except Exception:
                                pass

                if (
                    not self._replay_inflight
                    and now - _last_ss >= _ss_poll_interval
                    and hg.smart_shift_supported
                    and self._device_supports_smart_shift(hg.connected_device)
                ):
                    _last_ss = now
                    ss_mode = hg.read_smart_shift()
                    if stop_event.is_set():
                        return
                    if ss_mode is not None:
                        if ss_mode != _last_ss_mode:
                            print(f"[Engine] Scroll mode: {ss_mode}"
                                  + (" (changed)" if _last_ss_mode is not None else ""))
                            _last_ss_mode = ss_mode
                        if self._smart_shift_read_cb:
                            try:
                                self._smart_shift_read_cb(ss_mode)
                            except Exception:
                                pass

            if stop_event.wait(5):
                return

    @staticmethod
    def _device_supports_battery_status(device):
        capabilities = getattr(device, "capabilities", None)
        if capabilities is None:
            return True
        if not hasattr(capabilities, "battery_status"):
            return True
        if capabilities.battery_status:
            return True
        inventory = getattr(device, "capability_inventory", None)
        if inventory is None:
            return True
        return not (
            bool(getattr(inventory, "raw_features", ()))
            or bool(getattr(inventory, "has_reprog_controls", False))
        )

    @staticmethod
    def _device_supports_adjustable_dpi(device):
        capabilities = getattr(device, "capabilities", None)
        if capabilities is None:
            return True
        if not hasattr(capabilities, "adjustable_dpi"):
            return True
        if capabilities.adjustable_dpi:
            return True
        inventory = getattr(device, "capability_inventory", None)
        if inventory is None:
            return True
        return not bool(getattr(inventory, "raw_features", ()))

    @staticmethod
    def _device_supports_smart_shift(device):
        capabilities = getattr(device, "capabilities", None)
        if capabilities is None:
            return True
        if not hasattr(capabilities, "smart_shift"):
            return True
        if capabilities.smart_shift:
            return True
        inventory = getattr(device, "capability_inventory", None)
        if inventory is None:
            return True
        return not bool(getattr(inventory, "raw_features", ()))

    @staticmethod
    def _device_supports_gesture_button(device):
        capabilities = getattr(device, "capabilities", None)
        if capabilities is None:
            return True
        if not hasattr(capabilities, "gesture_button"):
            return True
        if capabilities.gesture_button:
            return True
        inventory = getattr(device, "capability_inventory", None)
        if inventory is None:
            return True
        return not bool(getattr(inventory, "has_reprog_controls", False))

    def set_battery_callback(self, cb):
        """Register ``cb(level: int)`` invoked when battery level is read (0-100)."""
        self._battery_read_cb = cb

    def set_connection_change_callback(self, cb):
        """Register ``cb(connected: bool)`` invoked on device connect/disconnect."""
        self._connection_change_cb = cb
        if cb:
            try:
                cb(bool(self._hid_runtime_state().input_ready))
            except Exception:
                pass

    @property
    def device_connected(self):
        return self._hid_runtime_state().input_ready

    @property
    def connected_device(self):
        return self._hid_runtime_state().connected_device

    def dump_device_info(self):
        return getattr(self.hook, "dump_device_info", lambda: None)()

    @property
    def hid_features_ready(self):
        return self._hid_runtime_state().hid_ready

    @property
    def enabled(self):
        return self._enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_dpi(self, dpi_value):
        """Send DPI change to the mouse via HID++."""
        dpi = clamp_dpi(dpi_value, self.connected_device)
        with self._lock:
            self.cfg.setdefault("settings", {})["dpi"] = dpi
            save_config(self.cfg)
        # Try via the hook's HidGestureListener
        hg = self.hook._hid_gesture
        if hg:
            if not self._device_supports_adjustable_dpi(
                getattr(hg, "connected_device", None)
            ):
                return False
            return hg.set_dpi(dpi)
        print("[Engine] No HID++ connection — DPI not applied")
        return False

    def set_smart_shift(self, mode, smart_shift_enabled=False, threshold=25):
        """Send Smart Shift settings to device.
        mode: 'ratchet' or 'freespin' (fixed mode when smart_shift_enabled=False)
        smart_shift_enabled: True to enable auto SmartShift
        threshold: 1-50 sensitivity when SmartShift is enabled"""
        print(f"[Engine] set_smart_shift({mode}, enabled={smart_shift_enabled}, threshold={threshold}) called")
        with self._lock:
            settings = self.cfg.setdefault("settings", {})
            settings["smart_shift_mode"] = mode
            settings["smart_shift_enabled"] = smart_shift_enabled
            settings["smart_shift_threshold"] = threshold
            save_config(self.cfg)
        hg = self.hook._hid_gesture
        if hg:
            if not self._device_supports_smart_shift(
                getattr(hg, "connected_device", None)
            ):
                return False
            result = hg.set_smart_shift(mode, smart_shift_enabled, threshold)
            print(f"[Engine] set_smart_shift -> {'OK' if result else 'FAILED'}")
            return result
        print("[Engine] set_smart_shift: No HID++ connection — not applied")
        return False

    @property
    def smart_shift_supported(self):
        hg = self.hook._hid_gesture
        return bool(
            hg
            and hg.smart_shift_supported
            and self._device_supports_smart_shift(
                getattr(hg, "connected_device", None)
            )
        )

    def reload_mappings(self):
        """
        Called by the UI when the user changes a mapping.
        Re-wire callbacks without tearing down the hook or HID++.
        """
        with self._lock:
            try:
                self._reload_config_in_place()
            except ConfigLoadError as exc:
                print(
                    "[InputRuntime] HOOK_FAILURE phase=mapping-reload "
                    f"error={exc!r} action=preserve-current-config"
                )
            snapshot = self._replace_bindings("mapping-reload")
            self._emit_debug(f"reload_mappings profile={self._current_profile}")
            return snapshot

    def set_enabled(self, enabled):
        enabled = bool(enabled)
        if enabled != self._enabled:
            with self._binding_state_lock:
                self._multi_action_down_at.clear()
        self._enabled = enabled

    def set_ui_passthrough(self, enabled):
        if hasattr(self.hook, "set_ui_passthrough"):
            self.hook.set_ui_passthrough(enabled)

    def _emit_linux_permission_warning(self):
        report = linux_permission_report()
        log_message = linux_permission_log_message(report)
        if log_message:
            print(log_message)
        status_message = linux_permission_status_message(report)
        if status_message:
            self._emit_status(status_message)

    def start(self):
        self._emit_linux_permission_warning()
        with self._lock:
            try:
                self._reload_config_in_place()
            except ConfigLoadError as exc:
                if not config_is_verified(self.cfg):
                    print(
                        "[InputRuntime] HOOK_FAILURE phase=engine-start-config "
                        f"error={exc!r} action=abort-unverified-config"
                    )
                    self._emit_status("Configuration unavailable; input remapping was not started")
                    return False
                print(
                    "[InputRuntime] HOOK_FAILURE phase=engine-start-config "
                    f"error={exc!r} action=preserve-current-config"
                )
            self._replace_bindings("engine-start")
        start_error = None
        try:
            started = self.hook.start()
        except Exception as exc:
            import traceback

            start_error = f"{type(exc).__name__}: {exc}"
            print(
                "[InputRuntime] BACKEND_EXCEPTION context=engine-start "
                f"error={start_error} traceback={traceback.format_exc().strip()}"
            )
            started = False
        if started is False:
            try:
                cleanup_stopped = self.hook.stop()
            except Exception as exc:
                import traceback

                cleanup_stopped = False
                print(
                    "[InputRuntime] BACKEND_EXCEPTION context=engine-start-cleanup "
                    f"error={type(exc).__name__}: {exc} "
                    f"traceback={traceback.format_exc().strip()}"
            )
            if cleanup_stopped is not False:
                self._reset_backend_identity_tracking()
            print(
                "[InputRuntime] HOOK_FAILURE phase=start "
                f"error={start_error or 'registration-failed'}"
            )
            return False
        print("[InputRuntime] HOOK_START healthy=true")
        self._start_backend_watchdog()
        self._app_detector.start()
        # Temporary safety-net: keep the old delayed replay path until the
        # hid-ready transition path has proven out in the field.
        def _startup_replay_fallback():
            time.sleep(3)
            if not self.hid_features_ready:
                return
            self._request_saved_settings_replay(startup_fallback=True)
        threading.Thread(target=_startup_replay_fallback, daemon=True).start()
        return True

    def set_dpi_read_callback(self, cb):
        """Register a callback ``cb(dpi_value)`` invoked when DPI is read from device."""
        self._dpi_read_cb = cb

    def set_smart_shift_read_callback(self, cb):
        """Register a callback ``cb(state)`` invoked when Smart Shift is read."""
        self._smart_shift_read_cb = cb

    def stop(self):
        if self._stop_backend_watchdog() is False:
            return False
        with self._backend_recovery_lock:
            self._battery_poll_stop.set()
            if self._battery_poll_thread is not None:
                self._battery_poll_thread.join(timeout=5)
                self._battery_poll_thread = None
            self._app_detector.stop()
            self.hook.reset_bindings(wait_timeout=1.0)
            with self._binding_state_lock:
                self._multi_action_down_at.clear()
            stopped = self.hook.stop()
            if stopped is not False:
                self._reset_backend_identity_tracking()
                self._release_active_mouse_holds("engine-stop")
            print(f"[InputRuntime] HOOK_STOP stopped={stopped is not False}")
            return stopped
