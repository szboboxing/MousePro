"""Native Windows screenshot actions for MousePro.

The mouse hook can invoke actions from a non-Qt thread.  This module exposes a
Qt controller whose public request method only emits a queued signal; all
capture, clipboard, file, and overlay work then runs on the GUI thread.
"""
from __future__ import annotations

import ctypes
import io
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Callable, Sequence

from PIL import Image, ImageGrab
from PySide6.QtCore import QObject, QRect, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QGuiApplication

from ui.screenshot_common import (
    SCREENSHOT_ACTIONS,
    SCREENSHOT_FULL_CLIP,
    SCREENSHOT_FULL_FILE,
    SCREENSHOT_REGION_CLIP,
    SCREENSHOT_REGION_FILE,
    pil_image_to_qimage,
    save_image_to_file,
)
from ui.screenshot_overlay import (
    IntRect,
    RegionSelectionOverlay,
    rect_from_qrect as _rect_from_qrect,
    union_rect as _union_rect,
)


CF_DIB = 8
GMEM_MOVEABLE = 0x0002


class NativeClipboardError(RuntimeError):
    def __init__(self, stage: str, error_code: int):
        self.stage = stage
        self.error_code = int(error_code)
        super().__init__(f"{stage} failed (WinError {self.error_code})")


def image_to_cf_dib(image: Image.Image) -> bytes:
    """Return a Paint-compatible CF_DIB payload (BMP without file header)."""
    output = io.BytesIO()
    image.convert("RGB").save(output, format="BMP")
    bitmap = output.getvalue()
    if len(bitmap) < 14 or bitmap[:2] != b"BM":
        raise RuntimeError("DIB conversion produced an invalid BMP payload")
    dib = bitmap[14:]
    if len(dib) < 40:
        raise RuntimeError("DIB conversion produced an incomplete BITMAPINFOHEADER")
    return dib


class _Win32ClipboardApi:
    def __init__(self):
        import ctypes.wintypes as wintypes

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32.OpenClipboard.argtypes = [wintypes.HWND]
        self.user32.OpenClipboard.restype = wintypes.BOOL
        self.user32.EmptyClipboard.argtypes = []
        self.user32.EmptyClipboard.restype = wintypes.BOOL
        self.user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        self.user32.SetClipboardData.restype = wintypes.HANDLE
        self.user32.CloseClipboard.argtypes = []
        self.user32.CloseClipboard.restype = wintypes.BOOL
        self.user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        self.user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        self.user32.GetClipboardSequenceNumber.argtypes = []
        self.user32.GetClipboardSequenceNumber.restype = wintypes.DWORD
        self.user32.GetClipboardOwner.argtypes = []
        self.user32.GetClipboardOwner.restype = wintypes.HWND
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        self.kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        self.kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalLock.restype = ctypes.c_void_p
        self.kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalUnlock.restype = wintypes.BOOL
        self.kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
        self.kernel32.GlobalFree.restype = wintypes.HGLOBAL

    def last_error(self):
        return ctypes.get_last_error()


def windows_clipboard_snapshot(api=None):
    api = api or _Win32ClipboardApi()
    sequence = int(api.user32.GetClipboardSequenceNumber())
    owner = api.user32.GetClipboardOwner()
    owner_value = int(owner or 0)
    owner_pid = ctypes.c_ulong(0)
    owner_title = ""
    if owner_value:
        api.user32.GetWindowThreadProcessId(owner, ctypes.byref(owner_pid))
        title = ctypes.create_unicode_buffer(512)
        api.user32.GetWindowTextW(owner, title, len(title))
        owner_title = title.value
    return {
        "sequence": sequence,
        "owner_handle": owner_value,
        "owner_pid": int(owner_pid.value),
        "owner_title": owner_title,
        "cf_dib": bool(api.user32.IsClipboardFormatAvailable(CF_DIB)),
    }


def _log_clipboard_snapshot(label, api=None):
    snapshot = windows_clipboard_snapshot(api)
    print(
        f"[Screenshot] clipboard checkpoint {label}: "
        f"sequence={snapshot['sequence']} cf_dib={snapshot['cf_dib']} "
        f"owner=0x{snapshot['owner_handle']:X} pid={snapshot['owner_pid']} "
        f"title={snapshot['owner_title']!r}"
    )
    return snapshot


def write_cf_dib_to_windows_clipboard(
    image: Image.Image,
    *,
    api=None,
    retry_delays=(0.0, 0.01, 0.025, 0.05),
    sleep=time.sleep,
) -> tuple[int, int]:
    """Publish an image as CF_DIB and transfer memory ownership to Windows."""
    if sys.platform != "win32" and api is None:
        raise RuntimeError("native Windows clipboard is unavailable")
    api = api or _Win32ClipboardApi()
    before = _log_clipboard_snapshot("before OpenClipboard", api)
    dib = image_to_cf_dib(image)
    print(f"[Screenshot] DIB conversion completed: bytes={len(dib)} format=CF_DIB")

    opened = False
    for attempt, delay in enumerate(retry_delays, start=1):
        if delay:
            sleep(delay)
        print(f"[Screenshot] native clipboard open attempt: attempt={attempt}")
        if api.user32.OpenClipboard(None):
            opened = True
            print(f"[Screenshot] native clipboard opened: attempt={attempt}")
            break
        error_code = api.last_error()
        print(
            "[Screenshot] native clipboard open contention: "
            f"attempt={attempt} WinError={error_code}"
        )
    if not opened:
        raise NativeClipboardError("OpenClipboard", api.last_error())

    memory = None
    ownership_transferred = False
    try:
        if not api.user32.EmptyClipboard():
            raise NativeClipboardError("EmptyClipboard", api.last_error())
        memory = api.kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib))
        if not memory:
            raise NativeClipboardError("GlobalAlloc", api.last_error())
        print(f"[Screenshot] allocated HGLOBAL=0x{int(memory):X} bytes={len(dib)}")
        pointer = api.kernel32.GlobalLock(memory)
        if not pointer:
            raise NativeClipboardError("GlobalLock", api.last_error())
        print(f"[Screenshot] GlobalLock succeeded: HGLOBAL=0x{int(memory):X}")
        try:
            ctypes.memmove(pointer, dib, len(dib))
        finally:
            api.kernel32.GlobalUnlock(memory)
        returned_handle = api.user32.SetClipboardData(CF_DIB, memory)
        if not returned_handle:
            raise NativeClipboardError("SetClipboardData", api.last_error())
        ownership_transferred = True
        print(
            "[Screenshot] SetClipboardData succeeded: "
            f"format=CF_DIB returned=0x{int(returned_handle):X}"
        )
        print(
            "[Screenshot] ownership transferred to Windows: "
            f"HGLOBAL=0x{int(memory):X}"
        )
        _log_clipboard_snapshot("after SetClipboardData", api)
    finally:
        api.user32.CloseClipboard()
        if memory and not ownership_transferred:
            api.kernel32.GlobalFree(memory)
        elif memory:
            print(
                "[Screenshot] local cleanup skipped after successful transfer: "
                f"HGLOBAL=0x{int(memory):X}"
            )

    after_close = _log_clipboard_snapshot("after CloseClipboard", api)
    if not after_close["cf_dib"]:
        raise NativeClipboardError("CF_DIB verification", api.last_error())
    print("[Screenshot] external Windows clipboard format confirmed: CF_DIB")
    return image.width, image.height, before["sequence"], after_close["sequence"]


@dataclass(frozen=True)
class MonitorMap:
    logical: IntRect
    physical: IntRect


@dataclass(frozen=True)
class VirtualCapture:
    image: Image.Image
    physical_rect: IntRect
    monitor_maps: tuple[MonitorMap, ...]


def _sort_rects_spatially(rects: Sequence[IntRect]) -> list[IntRect]:
    return sorted(rects, key=lambda r: (r.left, r.top, r.width, r.height))


def build_monitor_maps(
    logical_rects: Sequence[IntRect],
    physical_rects: Sequence[IntRect],
) -> tuple[MonitorMap, ...]:
    """Pair Qt logical screen rectangles with Win32 physical monitor rectangles."""
    logical = [r for r in logical_rects if not r.is_empty]
    physical = [r for r in physical_rects if not r.is_empty]
    if not logical or not physical:
        raise ValueError("monitor mapping requires at least one logical and physical rect")
    if len(logical) != len(physical):
        physical_union = _union_rect(physical)
        return (MonitorMap(physical_union, physical_union),)
    return tuple(
        MonitorMap(logical_rect, physical_rect)
        for logical_rect, physical_rect in zip(
            _sort_rects_spatially(logical),
            _sort_rects_spatially(physical),
        )
    )


def _enum_windows_monitor_rects() -> tuple[IntRect, ...]:
    if sys.platform != "win32":
        raise RuntimeError("Win32 monitor enumeration is only available on Windows")

    import ctypes.wintypes as wintypes

    user32 = ctypes.windll.user32

    monitors: list[IntRect] = []
    monitor_enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    def _callback(_monitor, _dc, rect_ptr, _data):
        rect = rect_ptr.contents
        monitors.append(IntRect(rect.left, rect.top, rect.right, rect.bottom))
        return 1

    if not user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(_callback), 0):
        raise RuntimeError("EnumDisplayMonitors failed")
    return tuple(monitors)


def _system_monitor_maps() -> tuple[MonitorMap, ...]:
    physical_rects = _enum_windows_monitor_rects()
    app = QGuiApplication.instance()
    screens = app.screens() if app is not None else []
    logical_rects = [_rect_from_qrect(screen.geometry()) for screen in screens]
    return build_monitor_maps(logical_rects, physical_rects)


def logical_to_physical_rect(monitor: MonitorMap, logical_rect: IntRect) -> IntRect:
    if monitor.logical.is_empty:
        raise ValueError("logical monitor rectangle is empty")
    scale_x = monitor.physical.width / float(monitor.logical.width)
    scale_y = monitor.physical.height / float(monitor.logical.height)
    return IntRect(
        monitor.physical.left + int(round((logical_rect.left - monitor.logical.left) * scale_x)),
        monitor.physical.top + int(round((logical_rect.top - monitor.logical.top) * scale_y)),
        monitor.physical.left + int(round((logical_rect.right - monitor.logical.left) * scale_x)),
        monitor.physical.top + int(round((logical_rect.bottom - monitor.logical.top) * scale_y)),
    )


def capture_virtual_desktop(
    monitor_maps: Sequence[MonitorMap] | None = None,
    grab: Callable[..., Image.Image] | None = None,
) -> VirtualCapture:
    maps = tuple(monitor_maps or _system_monitor_maps())
    physical_bounds = _union_rect(m.physical for m in maps)
    grab_screen = grab or ImageGrab.grab
    canvas = Image.new("RGB", (physical_bounds.width, physical_bounds.height), (0, 0, 0))
    for monitor in maps:
        bbox = (
            monitor.physical.left,
            monitor.physical.top,
            monitor.physical.right,
            monitor.physical.bottom,
        )
        image = grab_screen(
            bbox=bbox,
            all_screens=True,
            include_layered_windows=True,
        ).convert("RGB")
        canvas.paste(
            image,
            (
                monitor.physical.left - physical_bounds.left,
                monitor.physical.top - physical_bounds.top,
            ),
        )
    return VirtualCapture(canvas, physical_bounds, maps)


def crop_logical_region(capture: VirtualCapture, logical_rect: IntRect) -> Image.Image:
    segments: list[IntRect] = []
    for monitor in capture.monitor_maps:
        logical_part = logical_rect.intersected(monitor.logical)
        if logical_part is not None:
            segments.append(logical_to_physical_rect(monitor, logical_part))
    if not segments:
        raise ValueError("selected region does not intersect any screen")

    output_rect = _union_rect(segments)
    result = Image.new(capture.image.mode, (output_rect.width, output_rect.height), (0, 0, 0))
    for segment in segments:
        source = segment.translated(-capture.physical_rect.left, -capture.physical_rect.top)
        patch = capture.image.crop((source.left, source.top, source.right, source.bottom))
        result.paste(patch, (segment.left - output_rect.left, segment.top - output_rect.top))
    return result


class WindowsScreenshotController(QObject):
    _requestAction = Signal(str, int)
    _CLIPBOARD_VERIFY_DELAYS_MS = (0, 50, 200)

    def __init__(
        self,
        status_callback: Callable[[str], None] | None = None,
        path_factory: Callable[[], object] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._status_callback = status_callback
        self._path_factory = path_factory
        self._overlay: RegionSelectionOverlay | None = None
        self._pending_capture: VirtualCapture | None = None
        self._pending_action = ""
        self._pending_request_id = 0
        self._clipboard_image = None
        self._clipboard_delivery_token = 0
        self._request_lock = threading.Lock()
        self._request_in_progress = False
        self._active_request_id = 0
        self._next_request_id = 0
        self._requestAction.connect(self._handle_request, Qt.ConnectionType.QueuedConnection)

    def request_action(self, action_id: str) -> bool:
        with self._request_lock:
            if self._request_in_progress:
                print(
                    "[Screenshot] screenshot request ignored while active: "
                    f"action={action_id}"
                )
                return False
            self._next_request_id += 1
            request_id = self._next_request_id
            self._request_in_progress = True
            self._active_request_id = request_id
        print(
            "[Screenshot] screenshot request id created: "
            f"id={request_id} action={action_id}"
        )
        print(f"[Screenshot] screenshot request queued: id={request_id} action={action_id}")
        self._requestAction.emit(action_id, request_id)
        return True

    @Slot(str, int)
    def _handle_request(self, action_id: str, request_id: int = 0) -> None:
        on_gui_thread = QThread.currentThread() is self.thread()
        print(
            "[Screenshot] GUI screenshot handler entered: "
            f"id={request_id} action={action_id} gui_thread={on_gui_thread}"
        )
        if action_id not in SCREENSHOT_ACTIONS:
            self._finish_request(request_id, False, "invalid action")
            return
        if self._overlay is not None:
            self._emit_status("Finish the current screenshot selection first")
            self._finish_request(request_id, False, "selection already active")
            return
        try:
            monitor_maps = _system_monitor_maps()
            physical_bounds = _union_rect(m.physical for m in monitor_maps)
            print(
                "[Screenshot] target screen selected: "
                f"monitors={len(monitor_maps)} bounds="
                f"{physical_bounds.left},{physical_bounds.top},"
                f"{physical_bounds.width}x{physical_bounds.height}"
            )
            capture = capture_virtual_desktop(monitor_maps)
            print(
                "[Screenshot] screen capture completed: "
                f"dimensions={capture.image.width}x{capture.image.height} "
                f"format={capture.image.mode}"
            )
        except Exception as exc:
            self._emit_status(f"Screenshot failed: {exc}")
            print(f"[Screenshot] screenshot request failed: id={request_id} stage=capture error={exc}")
            traceback.print_exc()
            self._finish_request(request_id, False)
            return

        if action_id in (SCREENSHOT_FULL_CLIP, SCREENSHOT_FULL_FILE):
            self._deliver_image(capture.image, action_id, request_id)
            return

        self._pending_capture = capture
        self._pending_action = action_id
        self._pending_request_id = request_id
        self._overlay = RegionSelectionOverlay(_union_rect(m.logical for m in capture.monitor_maps))
        self._overlay.selected.connect(self._finish_region)
        self._overlay.cancelled.connect(self._cancel_region)
        self._overlay.show()

    @Slot(QRect)
    def _finish_region(self, rect: QRect) -> None:
        overlay = self._overlay
        self._overlay = None
        if overlay is not None:
            overlay.deleteLater()
        capture = self._pending_capture
        action_id = self._pending_action
        request_id = self._pending_request_id
        self._pending_capture = None
        self._pending_action = ""
        self._pending_request_id = 0
        if capture is None:
            return
        try:
            image = crop_logical_region(capture, _rect_from_qrect(rect))
            self._deliver_image(image, action_id, request_id)
        except Exception as exc:
            self._emit_status(f"Screenshot failed: {exc}")
            print(f"[Screenshot] screenshot delivery failed: region: {exc}")
            traceback.print_exc()
            self._finish_request(request_id, False)

    @Slot()
    def _cancel_region(self) -> None:
        overlay = self._overlay
        self._overlay = None
        self._pending_capture = None
        self._pending_action = ""
        request_id = self._pending_request_id
        self._pending_request_id = 0
        if overlay is not None:
            overlay.deleteLater()
        self._emit_status("Screenshot cancelled")
        self._finish_request(request_id, False, "cancelled")

    def _deliver_image(self, image: Image.Image, action_id: str, request_id: int = 0) -> None:
        try:
            if action_id in (SCREENSHOT_REGION_CLIP, SCREENSHOT_FULL_CLIP):
                if sys.platform == "win32":
                    width, height, _before_sequence, after_sequence = (
                        write_cf_dib_to_windows_clipboard(image)
                    )
                    for delay_ms in (100, 500, 2000):
                        QTimer.singleShot(
                            delay_ms,
                            lambda delay_ms=delay_ms: self._log_native_clipboard_checkpoint(
                                request_id,
                                after_sequence,
                                delay_ms,
                            ),
                        )
                    print(
                        "[Screenshot] screenshot request completed: "
                        f"id={request_id} action={action_id} dimensions={width}x{height}"
                    )
                    self._emit_status("Screenshot copied to clipboard")
                    self._finish_request(request_id, True)
                    return
                clipboard = QGuiApplication.clipboard()
                if clipboard is None:
                    raise RuntimeError("clipboard unavailable")
                qimage = pil_image_to_qimage(image)
                if qimage.isNull():
                    raise RuntimeError("image conversion produced an empty QImage")
                self._clipboard_image = qimage
                self._clipboard_delivery_token += 1
                token = self._clipboard_delivery_token
                print(
                    "[Screenshot] image dimensions and format: "
                    f"{qimage.width()}x{qimage.height()} format={qimage.format()}"
                )
                print(f"[Screenshot] clipboard write requested: action={action_id}")
                clipboard.setImage(qimage)
                self._verify_clipboard_image(
                    clipboard,
                    action_id,
                    token,
                    qimage.width(),
                    qimage.height(),
                    attempt=0,
                    request_id=request_id,
                )
            else:
                target = self._path_factory() if self._path_factory is not None else None
                path = save_image_to_file(image, target)
                self._emit_status(f"Screenshot saved to {path}")
                print(
                    "[Screenshot] screenshot request completed: "
                    f"id={request_id} action={action_id} path={path}"
                )
                self._finish_request(request_id, True)
        except Exception as exc:
            self._emit_status(f"Screenshot failed: {exc}")
            print(
                "[Screenshot] screenshot request failed: "
                f"id={request_id} stage=clipboard delivery error={exc}"
            )
            traceback.print_exc()
            self._finish_request(request_id, False)

    def _log_native_clipboard_checkpoint(
        self,
        request_id: int,
        expected_sequence: int,
        delay_ms: int,
    ) -> None:
        try:
            snapshot = _log_clipboard_snapshot(f"after {delay_ms} ms")
            if snapshot["sequence"] != expected_sequence:
                print(
                    "[Screenshot] clipboard sequence changed after delivery: "
                    f"id={request_id} expected={expected_sequence} "
                    f"actual={snapshot['sequence']} delay_ms={delay_ms} "
                    f"owner_pid={snapshot['owner_pid']}"
                )
        except Exception as exc:
            print(
                "[Screenshot] clipboard checkpoint failed: "
                f"id={request_id} delay_ms={delay_ms} error={exc}"
            )
            traceback.print_exc()

    def _verify_clipboard_image(
        self,
        clipboard,
        action_id: str,
        token: int,
        expected_width: int,
        expected_height: int,
        attempt: int,
        request_id: int = 0,
    ) -> None:
        if token != self._clipboard_delivery_token:
            return
        try:
            image = clipboard.image()
            if (
                image is not None
                and not image.isNull()
                and image.width() == expected_width
                and image.height() == expected_height
            ):
                print(
                    "[Screenshot] clipboard image confirmed: "
                    f"action={action_id} dimensions={image.width()}x{image.height()}"
                )
                self._emit_status("Screenshot copied to clipboard")
                print(
                    "[Screenshot] screenshot request completed: "
                    f"id={request_id} action={action_id}"
                )
                self._finish_request(request_id, True)
                return
        except Exception as exc:
            self._emit_status(f"Screenshot failed: {exc}")
            print(f"[Screenshot] screenshot delivery failed: clipboard verification: {exc}")
            traceback.print_exc()
            self._finish_request(request_id, False)
            return

        if attempt < len(self._CLIPBOARD_VERIFY_DELAYS_MS):
            delay = self._CLIPBOARD_VERIFY_DELAYS_MS[attempt]
            QTimer.singleShot(
                delay,
                lambda: self._verify_clipboard_image(
                    clipboard,
                    action_id,
                    token,
                    expected_width,
                    expected_height,
                    attempt + 1,
                    request_id,
                ),
            )
            return

        try:
            raise RuntimeError(
                "clipboard did not contain the requested image after bounded verification"
            )
        except RuntimeError as exc:
            self._emit_status(f"Screenshot failed: {exc}")
            print(f"[Screenshot] screenshot delivery failed: {exc}")
            traceback.print_exc()
            self._finish_request(request_id, False)

    def _finish_request(
        self,
        request_id: int,
        _success: bool,
        reason: str = "",
    ) -> None:
        if request_id:
            with self._request_lock:
                if request_id != self._active_request_id:
                    print(
                        "[Screenshot] stale screenshot completion ignored: "
                        f"id={request_id} active={self._active_request_id}"
                    )
                    return
                self._request_in_progress = False
                self._active_request_id = 0
        if reason:
            print(f"[Screenshot] screenshot request ended: id={request_id} reason={reason}")

    def _emit_status(self, message: str) -> None:
        if self._status_callback is not None:
            self._status_callback(message)
