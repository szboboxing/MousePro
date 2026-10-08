<p align="center">
  <img src="images/logo.png" alt="MousePro" width="140">
</p>

# MousePro

### Your mouse. Your controls.

**English** · [简体中文](README_CN.md)

**MousePro is a mouse customization app.** Make supported mouse buttons perform the actions you need: copying, pasting, switching tabs, taking screenshots, running keyboard shortcuts, and more. Give a click and a long press different actions, then create application profiles that switch automatically as you work.

[**Download for Windows · v1.0.1**](https://github.com/szboboxing/MousePro/releases/download/v1.0.1/MousePro-v1.0.1-Windows.zip) · [Release notes](https://github.com/szboboxing/MousePro/releases/tag/v1.0.1) · [Full feature gallery](docs/FEATURES.md)

![Mouse controls and application profiles in MousePro v1.0.1](images/screenshots-v1.4.3/mouse-en.png)

*Current v1.0.1 interface, rendered with sample profiles and device capabilities. Screenshots illustrate controls; available hardware features depend on your mouse and firmware.*

## Put everyday actions on your mouse

Choose a supported button directly on the mouse diagram. Assign browser navigation, editing commands, media controls, desktop navigation, or a custom keyboard shortcut. Screenshot actions can capture the whole screen or a selected region, to the clipboard or a file.

**One button can do two jobs.** For example, click the middle button to capture a region and hold it to copy. Configure Click and Long Press independently where supported.

![Actions, screenshots, custom shortcuts, and long-press mapping](images/screenshots-v1.4.3/actions-en.png)

[See all action categories and the custom shortcut editor →](docs/FEATURES.md#buttons-and-shortcuts)

## Different applications, different controls

Keep a default profile for everyday use and add profiles for your browser, editor, or other apps. MousePro changes the active mappings with the focused application. The same side button can go back in your browser and run a shortcut elsewhere.

![Application profile selection](images/screenshots-v1.4.3/profiles-en.png)

## Standard buttons and MX enhancements, together

**Generic Mouse Mode** maps the standard Windows middle button and two side buttons, including on ordinary mice such as ZOWIE. While enabled, Generic owns these inputs completely: a “none” mapping performs no action and does not fall back to a saved MX mapping. Switching it off restores device-specific routing without deleting those mappings.

![Generic Mouse Mode enabled](images/screenshots-v1.4.3/generic-en.png)

Supported **MX Master HID++ enhancements** remain available for non-overlapping controls: gestures, horizontal scrolling, Mode Shift, SmartShift, and DPI. You can assign directional gestures and adjust their threshold, configure horizontal scroll actions, and choose the supported wheel behavior. Device and firmware support varies.

![DPI, SmartShift sensitivity, appearance, and language settings](images/screenshots-v1.4.3/settings-1-en.png)

[Explore gestures, horizontal scrolling, wheel modes, and every settings section →](docs/FEATURES.md#mx-controls)

## Make the app fit your workflow

Choose light, dark, or system appearance and English or Simplified Chinese. Configure startup behavior, update checks, screenshot destination, and vertical/horizontal scroll direction. Mouse mappings and reader data stay in separate local stores.

## Reading Mode: mouse control for a specific activity

Mouse customization is MousePro's core. Reading Mode extends that idea: beyond deciding what a button does, a mouse can adapt to the activity you are doing. It is an example of bringing mouse control into a complete workflow, while keeping your everyday mappings intact.

### Read local books in a floating panel

Import **TXT or EPUB** and use the wheel to move through the text, or start **smooth automatic scrolling** with adjustable speed and pause/resume. The panel keeps its size and font size; overflow continues as you read. It stays on top without taking keyboard focus.

![Reading controls, automatic scrolling, and chapter navigation](images/screenshots-v1.4.3/reading-en.png)

### Find your place with chapters

EPUB contents and recognized TXT headings appear in the chapter selector. When explicit headings are absent, MousePro can suggest titles from line spacing and short standalone lines. Suggestions are labeled and require confirmation; they may be incomplete or incorrect. A jump starts at the chapter title on its own line. Older imports may need reimporting for accurate contents.

### A panel you can adjust and hide

Drag the book-and-leaf handle to move the panel, or the lower-right grip to resize it. Set the font size, text color, opacity, and fully transparent background. Choose **Normal**, **Minimal**, or **Ghost**; Minimal and Ghost let clicks pass through the text area.

![Normal floating reading panel with a chapter title](images/screenshots-v1.4.3/overlay-en.png)

**Press once to hide; press again to show.** Releasing the key keeps the panel hidden. Automatic reading pauses while hidden and resumes when shown. Reading stays enabled, the position is retained, and the wheel still belongs to Reading Mode. The selected mouse hide button is exclusive while reading; keyboard keys retain their usual keyboard action.

Reading OFF restores ordinary wheel scrolling. Reading ON temporarily claims the vertical wheel above Generic/MX routing. Switching mouse profiles or Generic mode does not reset the book. Reopening restores your position with automatic scrolling paused.

[All reading controls and the three panel modes →](docs/FEATURES.md#reading) · [Reading guide](docs/READING_MODE.md)

## Get started on Windows

[**Download MousePro v1.0.1 for Windows**](https://github.com/szboboxing/MousePro/releases/download/v1.0.1/MousePro-v1.0.1-Windows.zip)

Prefer a single portable exe? Grab [MousePro-v1.0.1-Windows-OneFile.exe](https://github.com/szboboxing/MousePro/releases/download/v1.0.1/MousePro-v1.0.1-Windows-OneFile.exe) — one standalone file with no `_internal` folder, copy it anywhere and run. The first launch takes a few extra seconds while it unpacks.

1. Extract the **entire ZIP** to a short path, such as `F:\Apps`. Do not run the app inside the ZIP or skip files if extraction fails.
2. Quit any older MousePro instance from its **system tray menu**. Closing the settings window only hides it.
3. Open `MousePro/MousePro.exe`. No separate Python installation is needed.
4. To customize buttons, open the mouse page and select a button.
5. Add application profiles and enable Generic Mouse Mode if you want to customize standard middle and side buttons.

The Windows executable is unsigned. Downloads include a SHA-256 checksum and an update manifest on the [release page](https://github.com/szboboxing/MousePro/releases/tag/v1.0.1). If your antivirus flags the unsigned app, whitelist the MousePro folder. Windows 10 or later is required, and the folder build's `MousePro.exe` must stay next to its `_internal` folder (the single-file build has no such constraint).

## Device and platform notes

**Windows hardware validation:** MX Master 4 and a ZOWIE mouse were used to validate reading, wheel ownership, and panel-hiding workflows. Earlier testing also covered MX Master 3 controls. This does not mean every feature is available on every model or firmware.

Generic Mouse Mode currently maps the middle button and two side buttons. It cannot distinguish multiple standard mice by physical device, and it does not offer general left/right-button or vertical-wheel remapping. Reading's wheel override is a separate feature.

Other Logitech models may work when they expose the required HID++ controls. If a device is detected but a control is missing, include the device information exported from the mouse page in a [device support request](https://github.com/szboboxing/MousePro/issues).

### macOS edition

The macOS release is **v1.0.1**. The Windows reading and automatic scrolling features shown above are not included in that release.

[Apple Silicon download](https://github.com/szboboxing/MousePro/releases/download/v1.0.1/MousePro-macOS.zip) · [Intel download](https://github.com/szboboxing/MousePro/releases/download/v1.0.1/MousePro-macOS-intel.zip) · [macOS release notes](https://github.com/szboboxing/MousePro/releases/tag/v1.0.1)

Extract the matching package, open `MousePro.app`, and grant Accessibility permission when prompted. This build is unsigned and unnotarized. Intel hardware testing used a MacBook Air and MX Master 3; Apple Silicon has build validation only. Generic Mouse Mode is Windows-only. Linux remains validation-only.

## Quick help

**A button performs an unexpected action?** Check the active application profile, Generic Mouse Mode, and whether that button is selected as the reader's hide button.

**Extraction reports “path too long”?** Cancel and extract to a shorter path. Do not skip the failed files.

**The app seems not to open?** Check the system tray for an already running copy. Quit it before opening another version.

## Development and contribution

Start with the [development guide](DEVELOPMENT.md), [architecture overview](docs/ARCHITECTURE.md), and [Reading Mode notes](docs/READING_MODE.md). For contributions, see [CONTRIBUTING.md](CONTRIBUTING.md) and [device support guidance](CONTRIBUTING_DEVICES.md).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main_qml.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Maintained by **szboboxing**. MousePro is forked from [pour-soi/PourInput](https://github.com/pour-soi/PourInput) (MIT); early upstream development used work from [Mouser](https://github.com/TomBadash/Mouser). MousePro is independently maintained and does not require Mouser to run.

[MIT license](LICENSE) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/szboboxing/MousePro/issues)
