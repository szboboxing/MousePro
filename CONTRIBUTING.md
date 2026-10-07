# Contributing to MousePro

Thanks for helping improve MousePro. MousePro is an independently designed and maintained input-customization application, with Multi-Action support for compatible mouse buttons.

## What Makes a Good Contribution?

Good contributions are focused, testable, and easy to review.

Useful areas include:

- Bug fixes with a clear reproduction case.
- Tests for existing behavior.
- Device support data and device layout improvements.
- Documentation polish.
- Small UI improvements that match the existing design.
- Multi-Action support for additional buttons through the generic framework.

## Before You Start

Check the existing issues and pull requests first. If your change affects device behavior, include the mouse model, connection type, operating system, and device info JSON from the Mouse page.

Avoid unrelated refactors in the same pull request. They make HID++ and input-hook changes much harder to review.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run from source:

```powershell
.\.venv\Scripts\python.exe main_qml.py
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for architecture and platform details.

## Multi-Action Button Changes

Future supported buttons should use the generic Multi-Action framework instead of adding separate timing logic.

When adding a supported button:

1. Add the button to the Multi-Action configuration.
2. Ensure the button has separate down and up events.
3. Add a default Long Press mapping.
4. Expose capability data through the backend.
5. Add focused tests for config migration, dispatch behavior, and UI/backend exposure.
6. Document the supported button if it is user-visible.

## Device Support

For new Logitech mice, start with [CONTRIBUTING_DEVICES.md](CONTRIBUTING_DEVICES.md). A device info JSON dump is usually the most useful artifact because it shows product ID, discovered HID++ features, reprogrammable controls, flags, and supported buttons.

## Pull Request Checklist

- The change is focused and does not mix unrelated work.
- Tests pass with `python -m unittest discover -s tests`.
- User-visible behavior is documented.
- Device changes include device info JSON or hardware test notes.
- Screenshots are included for visible UI changes.
- Existing config formats are preserved unless a migration is included.

## Behavior Compatibility

MousePro remaps physical input. Small changes can have large user-visible effects, so compatibility matters:

- Do not break Gesture behavior.
- Do not break Horizontal Scroll.
- Do not break Middle Button behavior.
- Preserve existing mappings and config migrations.
- Prefer adding support through configuration and shared dispatch paths.

## Code Style

Follow the style already used in the touched files. Keep comments short and useful, prefer focused helpers over broad rewrites, and add tests near the behavior you changed.

## Releases

This project uses Semantic Versioning. Release artifacts are versioned as:

```text
MousePro-vX.Y.Z-Windows.zip
```

Do not overwrite previous release artifacts.
