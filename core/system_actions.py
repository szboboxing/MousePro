"""
MousePro quick system actions (Windows only).

Ports the non-gesture ``SystemActions`` from the legacy
mouse-gesture-actions project:

* open calculator / browser / media player;
* open the mouse pointer size settings page (Win10/Win11 aware);
* enhanced paste (new folder in the active Explorer window + paste);
* display brightness / contrast adjustments.

``execute_quick_action`` is the platform-guarded facade used by
key_simulator and the QML backend.  Win32-only dependencies (pywin32)
are imported exclusively inside the ``sys.platform == "win32"`` branch
so the module imports cleanly on macOS/Linux.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

IS_WINDOWS = sys.platform == "win32"

POINTER_SIZE_URI_WIN11 = "ms-settings:easeofaccess-mousepointer"
POINTER_SIZE_URI_WIN10 = "ms-settings:easeofaccess-cursorandpointersize"
WIN11_BUILD_THRESHOLD = 22000

QUICK_ACTION_IDS = frozenset(
    {
        "calculator",
        "browser",
        "media_player",
        "pointer_size",
        "brightness_up",
        "brightness_down",
        "contrast_up",
        "contrast_down",
        "enhanced_paste",
    }
)


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str
    detail: str = ""


UNSUPPORTED_RESULT = ActionResult(
    False,
    "Unsupported platform",
    "MousePro quick actions are only available on Windows.",
)


def pointer_size_settings_uri(build: int) -> str:
    """Pick the mouse pointer settings URI for the given OS build.

    Build >= 22000 is Windows 11 (Accessibility -> Mouse pointer and
    touch); older builds use the Windows 10 Ease of Access page.
    Pure/static so the split is unit-testable on every platform.
    """
    if int(build) >= WIN11_BUILD_THRESHOLD:
        return POINTER_SIZE_URI_WIN11
    return POINTER_SIZE_URI_WIN10


if IS_WINDOWS:
    import ctypes
    import os
    import time
    import webbrowser

    import pythoncom
    import win32com.client
    import win32gui
    from win32com.shell import shell, shellcon

    from core.display_controls import DisplayController

    KEYEVENTF_KEYUP = 0x0002
    GA_ROOT = 2
    VK_CONTROL = 0x11
    VK_SHIFT = 0x10
    VK_N = ord("N")
    VK_V = ord("V")
    ENHANCED_PASTE_DELAY_SECONDS = 0.20

    def get_active_explorer_directory():
        """Return the folder shown by the foreground Explorer window.

        Returns the desktop path when the desktop is foreground, and
        ``None`` when the foreground window is neither Explorer nor the
        desktop.
        """
        foreground = win32gui.GetForegroundWindow()
        root_window = win32gui.GetAncestor(foreground, GA_ROOT)
        class_name = win32gui.GetClassName(root_window)

        if class_name in {"Progman", "WorkerW"}:
            from pathlib import Path

            desktop = shell.SHGetFolderPath(
                0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0
            )
            return Path(desktop)

        if class_name not in {"CabinetWClass", "ExploreWClass"}:
            return None

        from pathlib import Path

        shell_application = win32com.client.Dispatch("Shell.Application")
        for window in shell_application.Windows():
            try:
                if int(window.HWND) != root_window:
                    continue
                path_text = str(window.Document.Folder.Self.Path)
                path = Path(path_text)
                return path if path.is_dir() else None
            except (AttributeError, TypeError, pythoncom.com_error):
                continue
        return None

    class SystemActions:
        """Launchers and helpers that interact with the Windows shell."""

        def __init__(self) -> None:
            self._user32 = ctypes.windll.user32
            self._display = DisplayController()
            self._user32.keybd_event.argtypes = (
                ctypes.c_ubyte,
                ctypes.c_ubyte,
                ctypes.c_ulong,
                ctypes.c_size_t,
            )

        pointer_size_settings_uri = staticmethod(pointer_size_settings_uri)

        def _send_keys(self, keys, action_name, shortcut_text):
            try:
                for virtual_key in keys:
                    self._user32.keybd_event(virtual_key, 0, 0, 0)
                for virtual_key in reversed(keys):
                    self._user32.keybd_event(
                        virtual_key, 0, KEYEVENTF_KEYUP, 0
                    )
                return ActionResult(
                    True,
                    f"{action_name} executed",
                    shortcut_text,
                )
            except OSError as exc:
                return ActionResult(
                    False, f"{action_name} failed", str(exc)
                )

        def create_folder_and_paste_clipboard(self) -> ActionResult:
            """Create a new folder in the active Explorer dir, then paste."""
            pythoncom.CoInitialize()
            try:
                directory = get_active_explorer_directory()
                if directory is None:
                    return ActionResult(
                        False,
                        "Enhanced paste not executed",
                        "Activate File Explorer or the desktop first.",
                    )

                create_result = self._send_keys(
                    (VK_CONTROL, VK_SHIFT, VK_N),
                    "New folder",
                    "Ctrl+Shift+N",
                )
                if not create_result.success:
                    return create_result

                time.sleep(ENHANCED_PASTE_DELAY_SECONDS)
                paste_result = self._send_keys(
                    (VK_CONTROL, VK_V),
                    "Paste clipboard content",
                    "Ctrl+V",
                )
                if not paste_result.success:
                    return ActionResult(
                        False,
                        "Folder created, but clipboard paste failed",
                        paste_result.detail,
                    )
                return ActionResult(
                    True,
                    "Enhanced paste executed",
                    f"Created a new folder in {directory} and pasted the "
                    f"clipboard content",
                )
            except (OSError, pythoncom.com_error) as exc:
                return ActionResult(
                    False, "Enhanced paste failed", str(exc)
                )
            finally:
                pythoncom.CoUninitialize()

        def open_calculator(self) -> ActionResult:
            return self._open_target("calc.exe", "Calculator")

        def open_browser(self) -> ActionResult:
            try:
                if not webbrowser.open(
                    "https://www.bing.com", new=2
                ):
                    return ActionResult(
                        False,
                        "Browser failed to start",
                        "No default browser found",
                    )
                return ActionResult(
                    True,
                    "Browser started",
                    "Using the system default browser",
                )
            except (OSError, webbrowser.Error) as exc:
                return ActionResult(
                    False, "Browser failed to start", str(exc)
                )

        def open_media_player(self) -> ActionResult:
            errors: list[str] = []
            for target in ("mswindowsmusic:", "wmplayer.exe"):
                result = self._open_target(target, "Media player")
                if result.success:
                    return result
                errors.append(result.detail)
            return ActionResult(
                False,
                "Media player failed to start",
                "; ".join(item for item in errors if item),
            )

        def open_mouse_pointer_size_settings(self) -> ActionResult:
            """Open the pointer-size settings page, split by Windows build."""
            build = sys.getwindowsversion().build
            target = self.pointer_size_settings_uri(build)
            if build >= WIN11_BUILD_THRESHOLD:
                detail = (
                    "Opened Settings -> Accessibility -> "
                    "Mouse pointer and touch"
                )
            else:
                detail = (
                    "Opened Settings -> Ease of Access -> "
                    "Mouse pointer size"
                )
            try:
                os.startfile(target)  # type: ignore[attr-defined]
                return ActionResult(
                    True, "Mouse pointer size settings opened", detail
                )
            except OSError as exc:
                return ActionResult(
                    False,
                    "Mouse pointer size settings failed to open",
                    str(exc),
                )

        def adjust_brightness(self, direction: int) -> ActionResult:
            result = self._display.adjust_brightness(direction)
            if not result.success:
                return ActionResult(
                    False, "Brightness adjustment failed", result.detail
                )
            direction_text = "increased" if direction > 0 else "decreased"
            return ActionResult(
                True,
                f"Brightness {direction_text} to {result.value}%",
                result.detail,
            )

        def adjust_contrast(self, direction: int) -> ActionResult:
            result = self._display.adjust_contrast(direction)
            if not result.success:
                return ActionResult(
                    False, "Contrast adjustment failed", result.detail
                )
            direction_text = "increased" if direction > 0 else "decreased"
            return ActionResult(
                True,
                f"Contrast {direction_text} to {result.value}%",
                result.detail,
            )

        @staticmethod
        def _open_target(target: str, action_name: str) -> ActionResult:
            try:
                os.startfile(target)  # type: ignore[attr-defined]
                return ActionResult(True, f"{action_name} started", target)
            except OSError as exc:
                return ActionResult(
                    False, f"{action_name} failed to start", str(exc)
                )

    def get_active_explorer_directory_safe():
        try:
            return get_active_explorer_directory()
        except (OSError, pythoncom.com_error):
            return None

else:  # macOS / Linux / unknown: graceful "unsupported" results

    def get_active_explorer_directory():
        return None

    def get_active_explorer_directory_safe():
        return None

    class SystemActions:  # type: ignore[no-redef]
        """No-op placeholder; every action reports unsupported."""

        pointer_size_settings_uri = staticmethod(pointer_size_settings_uri)

        def _unsupported(self) -> ActionResult:
            return UNSUPPORTED_RESULT

        def create_folder_and_paste_clipboard(self) -> ActionResult:
            return self._unsupported()

        def open_calculator(self) -> ActionResult:
            return self._unsupported()

        def open_browser(self) -> ActionResult:
            return self._unsupported()

        def open_media_player(self) -> ActionResult:
            return self._unsupported()

        def open_mouse_pointer_size_settings(self) -> ActionResult:
            return self._unsupported()

        def adjust_brightness(self, direction: int) -> ActionResult:
            return self._unsupported()

        def adjust_contrast(self, direction: int) -> ActionResult:
            return self._unsupported()


_shared_actions: SystemActions | None = None


def _get_system_actions() -> SystemActions:
    global _shared_actions
    if _shared_actions is None:
        _shared_actions = SystemActions()
    return _shared_actions


def execute_quick_action(action_id: str) -> ActionResult:
    """Facade mapping a quick-action id to a SystemActions method.

    Unknown ids and non-Windows platforms return a failed ActionResult
    instead of raising.
    """
    if not IS_WINDOWS:
        return UNSUPPORTED_RESULT
    try:
        actions = _get_system_actions()
        if action_id == "calculator":
            return actions.open_calculator()
        if action_id == "browser":
            return actions.open_browser()
        if action_id == "media_player":
            return actions.open_media_player()
        if action_id == "pointer_size":
            return actions.open_mouse_pointer_size_settings()
        if action_id == "brightness_up":
            return actions.adjust_brightness(1)
        if action_id == "brightness_down":
            return actions.adjust_brightness(-1)
        if action_id == "contrast_up":
            return actions.adjust_contrast(1)
        if action_id == "contrast_down":
            return actions.adjust_contrast(-1)
        if action_id == "enhanced_paste":
            return actions.create_folder_and_paste_clipboard()
    except Exception as exc:  # pragma: no cover - defensive shell guard
        return ActionResult(False, f"Action failed: {action_id}", str(exc))
    return ActionResult(
        False, "Unknown action", f"No such quick action: {action_id}"
    )
