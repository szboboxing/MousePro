"""
Display brightness/contrast controls (Windows only).

Two backends are tried in order:

1. WMI ``WmiMonitorBrightness`` for built-in (laptop/tablet) panels;
2. Dxva2 DDC/CI physical monitor APIs for external monitors.

The Win32 implementation is imported only on Windows so the module stays
import-safe (and unit-testable for the pure helpers) on other platforms.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

PHYSICAL_MONITOR_DESCRIPTION_SIZE = 128


@dataclass(frozen=True)
class DisplayAdjustment:
    success: bool
    value: int | None
    detail: str


def _normalize_direction(direction: int) -> int:
    if direction not in {-1, 1}:
        raise ValueError("adjustment direction must be -1 or 1")
    return direction


def _step_value(
    current: int,
    minimum: int,
    maximum: int,
    direction: int,
) -> int:
    direction = _normalize_direction(direction)
    if maximum <= minimum:
        raise ValueError("monitor returned an invalid adjustment range")
    step = max(1, round((maximum - minimum) * 0.05))
    return max(minimum, min(maximum, current + direction * step))


_UNSUPPORTED_DETAIL = "Display controls are only available on Windows."


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    import pythoncom
    import win32com.client

    class PhysicalMonitor(ctypes.Structure):
        _fields_ = (
            ("handle", wintypes.HANDLE),
            (
                "description",
                wintypes.WCHAR * PHYSICAL_MONITOR_DESCRIPTION_SIZE,
            ),
        )

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HANDLE,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    class DisplayController:
        """Adjust brightness/contrast through WMI then DDC/CI."""

        def __init__(self) -> None:
            self._user32 = ctypes.windll.user32
            self._dxva2 = ctypes.WinDLL("Dxva2.dll", use_last_error=True)
            self._configure_winapi()

        def adjust_brightness(self, direction: int) -> DisplayAdjustment:
            direction = _normalize_direction(direction)
            try:
                value, count = self._adjust_wmi_brightness(direction)
                return DisplayAdjustment(
                    True,
                    value,
                    f"Adjusted {count} built-in display(s)",
                )
            except (AttributeError, OSError, pythoncom.com_error):
                pass

            try:
                value, count = self._adjust_physical_monitors(
                    "brightness", direction
                )
                return DisplayAdjustment(
                    True,
                    value,
                    f"Adjusted {count} monitor(s) via DDC/CI",
                )
            except OSError as exc:
                return DisplayAdjustment(
                    False,
                    None,
                    f"This display does not support software brightness "
                    f"adjustment: {exc}",
                )

        def adjust_contrast(self, direction: int) -> DisplayAdjustment:
            direction = _normalize_direction(direction)
            try:
                value, count = self._adjust_physical_monitors(
                    "contrast", direction
                )
                return DisplayAdjustment(
                    True,
                    value,
                    f"Adjusted {count} monitor(s) via DDC/CI",
                )
            except OSError as exc:
                return DisplayAdjustment(
                    False,
                    None,
                    f"This display does not support software contrast "
                    f"adjustment: {exc}",
                )

        def _configure_winapi(self) -> None:
            physical_pointer = ctypes.POINTER(PhysicalMonitor)
            self._user32.EnumDisplayMonitors.argtypes = (
                wintypes.HDC,
                ctypes.POINTER(wintypes.RECT),
                MonitorEnumProc,
                wintypes.LPARAM,
            )
            self._user32.EnumDisplayMonitors.restype = wintypes.BOOL

            self._dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = (
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            )
            self._dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.restype = (
                wintypes.BOOL
            )
            self._dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = (
                wintypes.HANDLE,
                wintypes.DWORD,
                physical_pointer,
            )
            self._dxva2.GetPhysicalMonitorsFromHMONITOR.restype = wintypes.BOOL
            self._dxva2.DestroyPhysicalMonitors.argtypes = (
                wintypes.DWORD,
                physical_pointer,
            )
            self._dxva2.DestroyPhysicalMonitors.restype = wintypes.BOOL

            for name in ("Brightness", "Contrast"):
                getter = getattr(self._dxva2, f"GetMonitor{name}")
                getter.argtypes = (
                    wintypes.HANDLE,
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD),
                    ctypes.POINTER(wintypes.DWORD),
                )
                getter.restype = wintypes.BOOL
                setter = getattr(self._dxva2, f"SetMonitor{name}")
                setter.argtypes = (wintypes.HANDLE, wintypes.DWORD)
                setter.restype = wintypes.BOOL

        def _adjust_wmi_brightness(self, direction: int) -> tuple[int, int]:
            pythoncom.CoInitialize()
            try:
                service = win32com.client.GetObject(
                    r"winmgmts:\\.\root\WMI"
                )
                levels = list(
                    service.ExecQuery(
                        "SELECT CurrentBrightness "
                        "FROM WmiMonitorBrightness WHERE Active=TRUE"
                    )
                )
                methods = list(
                    service.ExecQuery(
                        "SELECT * FROM WmiMonitorBrightnessMethods "
                        "WHERE Active=TRUE"
                    )
                )
                if not levels or not methods:
                    raise OSError("no adjustable built-in display found")

                targets: list[int] = []
                for index, method in enumerate(methods):
                    current = int(
                        levels[
                            min(index, len(levels) - 1)
                        ].CurrentBrightness
                    )
                    target = _step_value(current, 0, 100, direction)
                    method.WmiSetBrightness(0, target)
                    targets.append(target)
                return targets[0], len(targets)
            finally:
                pythoncom.CoUninitialize()

        def _adjust_physical_monitors(
            self,
            control: str,
            direction: int,
        ) -> tuple[int, int]:
            monitor_handles: list[int] = []

            @MonitorEnumProc
            def collect_monitor(
                monitor: int,
                _device_context: int,
                _rect: ctypes.POINTER(wintypes.RECT),
                _data: int,
            ) -> bool:
                monitor_handles.append(monitor)
                return True

            if not self._user32.EnumDisplayMonitors(
                None, None, collect_monitor, 0
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            getter = getattr(
                self._dxva2,
                f"GetMonitor{control.capitalize()}",
            )
            setter = getattr(
                self._dxva2,
                f"SetMonitor{control.capitalize()}",
            )
            targets: list[int] = []

            for monitor_handle in monitor_handles:
                count = wintypes.DWORD()
                if not self._dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(
                    monitor_handle, ctypes.byref(count)
                ):
                    continue
                if count.value == 0:
                    continue

                monitors = (PhysicalMonitor * count.value)()
                if not self._dxva2.GetPhysicalMonitorsFromHMONITOR(
                    monitor_handle, count.value, monitors
                ):
                    continue
                try:
                    for monitor in monitors:
                        minimum = wintypes.DWORD()
                        current = wintypes.DWORD()
                        maximum = wintypes.DWORD()
                        if not getter(
                            monitor.handle,
                            ctypes.byref(minimum),
                            ctypes.byref(current),
                            ctypes.byref(maximum),
                        ):
                            continue
                        target = _step_value(
                            current.value,
                            minimum.value,
                            maximum.value,
                            direction,
                        )
                        if setter(monitor.handle, target):
                            targets.append(target)
                finally:
                    self._dxva2.DestroyPhysicalMonitors(
                        count.value, monitors
                    )

            if not targets:
                raise OSError(
                    "make sure the monitor supports and has DDC/CI enabled"
                )
            return targets[0], len(targets)

else:  # non-Windows: safe no-op controller

    class DisplayController:  # type: ignore[no-redef]
        """Placeholder used on platforms without display control APIs."""

        def __init__(self) -> None:
            return

        def adjust_brightness(self, direction: int) -> DisplayAdjustment:
            _normalize_direction(direction)
            return DisplayAdjustment(False, None, _UNSUPPORTED_DETAIL)

        def adjust_contrast(self, direction: int) -> DisplayAdjustment:
            _normalize_direction(direction)
            return DisplayAdjustment(False, None, _UNSUPPORTED_DETAIL)
