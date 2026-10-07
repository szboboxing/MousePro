"""
Windows mouse hook implementation.
"""

import ctypes
import ctypes.wintypes as wintypes
import queue
import sys
import threading
import time
import traceback
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    byref,
    c_int,
    c_uint,
    c_ulong,
    c_ushort,
    c_void_p,
    create_string_buffer,
    sizeof,
    windll,
)

from core.key_simulator import MOUSEEVENTF_HWHEEL, MOUSEEVENTF_WHEEL
from core.key_simulator import inject_scroll as _inject_scroll_impl
from core.mouse_hook_base import BaseMouseHook, HidGestureListener
from core.mouse_hook_types import MouseEvent
from core.right_hold_gesture import RightHoldGestureState

WH_MOUSE_LL = 14
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MOUSEHWHEEL = 0x020E
WM_MOUSEWHEEL = 0x020A
WM_POWERBROADCAST = 0x0218

HC_ACTION = 0
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002

MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

mouse_event = windll.user32.mouse_event
mouse_event.restype = ctypes.c_void_p
mouse_event.argtypes = [
    c_ulong,
    c_ulong,
    c_ulong,
    c_ulong,
    ctypes.c_size_t,
]


class MSLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


HOOKPROC = CFUNCTYPE(
    ctypes.c_long,
    c_int,
    wintypes.WPARAM,
    ctypes.POINTER(MSLLHOOKSTRUCT),
)

SetWindowsHookExW = windll.user32.SetWindowsHookExW
SetWindowsHookExW.restype = wintypes.HHOOK
SetWindowsHookExW.argtypes = [c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]

CallNextHookEx = windll.user32.CallNextHookEx
CallNextHookEx.restype = ctypes.c_long
CallNextHookEx.argtypes = [
    wintypes.HHOOK,
    c_int,
    wintypes.WPARAM,
    ctypes.POINTER(MSLLHOOKSTRUCT),
]

UnhookWindowsHookEx = windll.user32.UnhookWindowsHookEx
UnhookWindowsHookEx.restype = wintypes.BOOL
UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]

GetModuleHandleW = windll.kernel32.GetModuleHandleW
GetModuleHandleW.restype = wintypes.HMODULE
GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

GetMessageW = windll.user32.GetMessageW
PostThreadMessageW = windll.user32.PostThreadMessageW

WM_QUIT = 0x0012
INJECTED_FLAG = 0x00000001

WM_INPUT = 0x00FF
RIDEV_INPUTSINK = 0x00000100
RID_INPUT = 0x10000003
RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1
RIM_TYPEHID = 2
RIDI_DEVICENAME = 0x20000007
SW_HIDE = 0
STANDARD_BUTTON_MASK = 0x1F
RI_MOUSE_BUTTON_4_DOWN = 0x0040
RI_MOUSE_BUTTON_4_UP = 0x0080
RI_MOUSE_BUTTON_5_DOWN = 0x0100
RI_MOUSE_BUTTON_5_UP = 0x0200
RAW_XBUTTON_FLAGS = {
    RI_MOUSE_BUTTON_4_DOWN: "XBUTTON1_DOWN",
    RI_MOUSE_BUTTON_4_UP: "XBUTTON1_UP",
    RI_MOUSE_BUTTON_5_DOWN: "XBUTTON2_DOWN",
    RI_MOUSE_BUTTON_5_UP: "XBUTTON2_UP",
}


class RAWINPUTDEVICE(Structure):
    _fields_ = [
        ("usUsagePage", c_ushort),
        ("usUsage", c_ushort),
        ("dwFlags", c_ulong),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(Structure):
    _fields_ = [
        ("dwType", c_ulong),
        ("dwSize", c_ulong),
        ("hDevice", c_void_p),
        ("wParam", POINTER(c_ulong)),
    ]


class RAWMOUSE(Structure):
    _fields_ = [
        ("usFlags", c_ushort),
        ("usButtonFlags", c_ushort),
        ("usButtonData", c_ushort),
        ("ulRawButtons", c_ulong),
        ("lLastX", c_int),
        ("lLastY", c_int),
        ("ulExtraInformation", c_ulong),
    ]


class RAWHID(Structure):
    _fields_ = [
        ("dwSizeHid", c_ulong),
        ("dwCount", c_ulong),
    ]


WNDPROC_TYPE = CFUNCTYPE(
    ctypes.c_longlong,
    wintypes.HWND,
    c_uint,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASSEXW(Structure):
    _fields_ = [
        ("cbSize", c_uint),
        ("style", c_uint),
        ("lpfnWndProc", WNDPROC_TYPE),
        ("cbClsExtra", c_int),
        ("cbWndExtra", c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


RegisterRawInputDevices = windll.user32.RegisterRawInputDevices
GetRawInputData = windll.user32.GetRawInputData
GetRawInputData.argtypes = [c_void_p, c_uint, c_void_p, POINTER(c_uint), c_uint]
GetRawInputData.restype = c_uint
GetRawInputDeviceInfoW = windll.user32.GetRawInputDeviceInfoW
RegisterClassExW = windll.user32.RegisterClassExW

CreateWindowExW = windll.user32.CreateWindowExW
CreateWindowExW.restype = wintypes.HWND
CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    c_int,
    c_int,
    c_int,
    c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]

ShowWindow = windll.user32.ShowWindow
DefWindowProcW = windll.user32.DefWindowProcW
DefWindowProcW.restype = ctypes.c_longlong
DefWindowProcW.argtypes = [
    wintypes.HWND,
    c_uint,
    wintypes.WPARAM,
    wintypes.LPARAM,
]

TranslateMessage = windll.user32.TranslateMessage
DispatchMessageW = windll.user32.DispatchMessageW
DestroyWindow = windll.user32.DestroyWindow


def hiword(dword):
    value = (dword >> 16) & 0xFFFF
    if value >= 0x8000:
        value -= 0x10000
    return value


WM_APP = 0x8000
WM_APP_INJECT_VSCROLL = WM_APP + 1
WM_APP_INJECT_HSCROLL = WM_APP + 2

WM_DEVICECHANGE = 0x0219
DBT_DEVNODES_CHANGED = 0x0007
PBT_APMRESUMECRITICAL = 0x0006
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012
POWER_RESUME_EVENTS = {
    PBT_APMRESUMECRITICAL,
    PBT_APMRESUMESUSPEND,
    PBT_APMRESUMEAUTOMATIC,
}
SILENT_HOOK_RAW_DIVERGENCE_S = 1.0

PostMessageW = windll.user32.PostMessageW
PostMessageW.argtypes = [wintypes.HWND, c_uint, wintypes.WPARAM, wintypes.LPARAM]
PostMessageW.restype = wintypes.BOOL


class MouseHook(BaseMouseHook):
    """
    Installs a low-level mouse hook on Windows to intercept side-button clicks
    and horizontal scroll events.
    """

    _READING_BUTTON_EDGES = {
        0x0201: (1, True), 0x0202: (1, False),
        0x0204: (2, True), 0x0205: (2, False),
        WM_MBUTTONDOWN: (4, True), WM_MBUTTONUP: (4, False),
    }

    def set_reading_hide_key(self, key):
        with self._reading_claim_lock:
            self._reading_hide_key = key

    def _claim_reading_button(self, key, down, source):
        # Keep ownership until release even if reading is disabled mid-hold.
        identity = (source, key)
        with self._reading_claim_lock:
            if down:
                return self._reading_claims.setdefault(identity, key == self._reading_hide_key)
            return self._reading_claims.pop(identity, False)

    def _clear_logi_xbutton_pressed(self, reason):
        super()._clear_logi_xbutton_pressed(reason)
        with self._reading_claim_lock:
            for identity in list(self._reading_claims):
                if identity[0] in ("hid", "injected"):
                    del self._reading_claims[identity]

    def set_reading_button_observer(self, observer):
        self._reading_button_observer = observer

    def _side_button_release_requires_confirmation(self, cid, hold_identity):
        with self._logi_windows_hold_lock:
            return (hold_identity is not None
                    and self._logi_windows_holds.get(cid) == hold_identity)

    def _on_reading_hid_button(self, key, down):
        observer = getattr(self, "_reading_button_observer", None)
        if observer is not None:
            observer(key, down)

    def set_reading_wheel_handler(self, handler):
        self._reading_wheel_handler = handler

    def __init__(self):
        self._reading_claim_lock = threading.Lock()
        self._reading_hide_key = 0
        self._reading_claims = {}
        super().__init__()
        self._hook = None
        self._hook_thread = None
        self._thread_id = None
        self._running = False
        self._hook_proc = None
        self._hook_generation = 0
        self._retired_hooks = []
        self._pending_vscroll = 0
        self._pending_hscroll = 0
        self._vscroll_posted = False
        self._hscroll_posted = False
        # RegisterClassExW retains this function pointer after the window is
        # destroyed.  Keep one callback and class for this hook object's full
        # lifetime so a stop/start cycle cannot leave Windows with a pointer to
        # a garbage-collected replacement callback.
        self._ri_wndproc_ref = WNDPROC_TYPE(self._ri_wndproc)
        self._ri_class_name = (
            f"MouseProRawInput_{id(self):X}_{time.monotonic_ns():X}"
        )
        self._ri_class_registered = False
        self._ri_hwnd = None
        self._device_name_cache = {}
        self._startup_event = threading.Event()
        self._startup_ok = False
        self._stop_requested = True
        self._recovery_required = False
        self._raw_input_active = False
        self._last_hook_event_at = None
        self._last_raw_input_at = None
        self._last_dispatch_event_at = None
        self._prev_raw_buttons = {}
        self._last_rehook_time = 0
        self._init_dispatch_queue(maxsize=512)
        self._dispatch_worker_thread = None

        # ── MousePro right-hold chord / raw observer / button test ──
        self._mp_gesture = RightHoldGestureState()
        self._mp_pending_side_release = set()
        self._mp_enabled_cb = None
        self._mp_buttons_cb = None
        self._mp_fire_cb = None
        self._mp_active_test_cb = None
        self._mp_raw_observer = None
        self._mp_test_mode = False

    # ------------------------------------------------------------------
    # MousePro enhancement wiring (only used by the Windows backend)
    # ------------------------------------------------------------------

    def set_right_hold_config(self, enabled_cb, buttons_cb, fire_cb,
                              active_test_cb):
        """Install live callbacks for the right-hold gesture chord.

        enabled_cb()      -> bool, feature enabled;
        buttons_cb()      -> list[str] subset of xbutton1/xbutton2;
        fire_cb(action)   -> dispatched off the hook thread by the engine;
        active_test_cb()  -> bool, UI capture mode (test/confirm) active.
        """
        self._mp_enabled_cb = enabled_cb
        self._mp_buttons_cb = buttons_cb
        self._mp_fire_cb = fire_cb
        self._mp_active_test_cb = active_test_cb

    def set_raw_observer(self, callback):
        """Receive a dict for every physical (never injected) event."""
        self._mp_raw_observer = callback

    def set_test_mode(self, enabled):
        """Button test mode: observe only, never swallow or run the chord."""
        self._mp_test_mode = bool(enabled)
        if self._mp_test_mode:
            self._mp_gesture.cancel()
            self._mp_pending_side_release.clear()

    def _mp_chord_allowed(self):
        if self._mp_test_mode:
            return False
        try:
            if self._mp_active_test_cb is not None and self._mp_active_test_cb():
                return False
        except Exception:
            pass
        try:
            return bool(
                self._mp_enabled_cb is not None and self._mp_enabled_cb()
            )
        except Exception:
            return False

    def _mp_configured_side_buttons(self):
        try:
            buttons = self._mp_buttons_cb() if self._mp_buttons_cb else None
        except Exception:
            buttons = None
        if not isinstance(buttons, (list, tuple, set, frozenset)):
            return set()
        result = set()
        for name in buttons:
            if name == "xbutton1":
                result.add(XBUTTON1)
            elif name == "xbutton2":
                result.add(XBUTTON2)
        return result

    def _mp_fire(self, action_id):
        fire_cb = self._mp_fire_cb
        if fire_cb is None:
            return
        try:
            fire_cb(action_id)
        except Exception as exc:
            self._emit_debug(f"Right-hold gesture fire failed: {exc}")

    def _mp_replay_right_click(self):
        try:
            mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        except OSError as exc:
            self._emit_debug(f"Right-click replay failed: {exc}")

    _MP_RAW_CONTROLS = {
        WM_LBUTTONDOWN: ("left", True),
        WM_LBUTTONUP: ("left", False),
        WM_RBUTTONDOWN: ("right", True),
        WM_RBUTTONUP: ("right", False),
        WM_MBUTTONDOWN: ("middle", True),
        WM_MBUTTONUP: ("middle", False),
    }

    def _mp_emit_raw(self, w_param, point, mouse_data):
        """Forward one physical event to the raw observer (best effort)."""
        observer = self._mp_raw_observer
        if observer is None:
            return
        payload = None
        if w_param == WM_MOUSEMOVE:
            payload = {
                "control": "move",
                "pressed": None,
                "x": int(point.x),
                "y": int(point.y),
                "ts": time.time(),
            }
        elif w_param == WM_MOUSEWHEEL:
            delta = hiword(mouse_data)
            if delta:
                payload = {
                    "control": "wheel_up" if delta > 0 else "wheel_down",
                    "pressed": None,
                    "delta": abs(delta),
                    "ts": time.time(),
                }
        elif w_param in (WM_XBUTTONDOWN, WM_XBUTTONUP):
            button = hiword(mouse_data)
            if button in (XBUTTON1, XBUTTON2):
                payload = {
                    "control": "xbutton1" if button == XBUTTON1 else "xbutton2",
                    "pressed": w_param == WM_XBUTTONDOWN,
                    "ts": time.time(),
                }
        else:
            mapped = self._MP_RAW_CONTROLS.get(w_param)
            if mapped is not None:
                payload = {
                    "control": mapped[0],
                    "pressed": mapped[1],
                    "ts": time.time(),
                }
        if payload is None:
            return
        try:
            observer(payload)
        except Exception as exc:
            self._emit_debug(f"Raw observer failed: {exc}")

    def _log_backend_exception(self, exc, phase):
        message = self._record_backend_exception(exc, phase)
        print(
            "[MouseHook] BACKEND_EXCEPTION "
            f"backend=windows phase={phase} error={message}"
        )
        traceback.print_exc(file=sys.stdout)

    def _log_backend_error(self, phase, detail):
        exc = RuntimeError(detail)
        message = self._record_backend_exception(exc, phase)
        print(
            "[MouseHook] BACKEND_EXCEPTION "
            f"backend=windows phase={phase} error={message}"
        )

    def _make_hook_proc(self, generation):
        def _generation_handler(nCode, wParam, lParam):
            if generation != self._hook_generation:
                return CallNextHookEx(None, nCode, wParam, lParam)
            return self._low_level_handler(nCode, wParam, lParam)

        return HOOKPROC(_generation_handler)

    def health_snapshot(self):
        base = super().health_snapshot()
        hook_thread_alive = bool(
            self._hook_thread and self._hook_thread.is_alive()
        )
        dispatch_worker_alive = bool(
            self._dispatch_worker_thread
            and self._dispatch_worker_thread.is_alive()
        )
        listener = self._hid_gesture
        listener_expected = bool(listener and getattr(listener, "_running", False))
        listener_thread = getattr(listener, "_thread", None) if listener else None
        listener_alive = bool(listener_thread and listener_thread.is_alive())
        listener_required = self._hid_listener_required()
        listener_ready = listener_expected and listener_alive
        running = bool(self._running)
        silent_unhook_suspected = bool(
            self._last_raw_input_at is not None
            and (
                self._last_hook_event_at is None
                or self._last_raw_input_at - self._last_hook_event_at
                > SILENT_HOOK_RAW_DIVERGENCE_S
            )
        )
        recovery_required = bool(
            self._recovery_required
            or (
                not self._stop_requested
                and (
                    not running
                    or not self._hook
                    or not hook_thread_alive
                    or not self._raw_input_active
                    or not dispatch_worker_alive
                    or (listener_required and not listener_ready)
                    or bool(self._retired_hooks)
                    or silent_unhook_suspected
                )
            )
        )
        return type(base)(
            **{
                **base.__dict__,
                "backend": "windows",
                "running": running,
                "hook_registered": bool(self._hook),
                "hook_thread_alive": hook_thread_alive,
                "raw_input_active": bool(self._raw_input_active),
                "dispatch_worker_alive": dispatch_worker_alive,
                "listener_alive": listener_alive,
                "device_available": bool(self._device_connected),
                "last_input_event_at": base.last_input_event_at,
                "last_hook_event_at": self._last_hook_event_at,
                "last_raw_input_at": self._last_raw_input_at,
                "last_dispatch_event_at": self._last_dispatch_event_at,
                "recovery_required": recovery_required,
                "healthy": running and not recovery_required,
            }
        )

    def _hid_listener_required(self):
        return bool(
            self._hid_listener_required_by_config
            or self._gesture_direction_enabled
            or self._build_extra_diverts()
        )

    def _accumulate_gesture_delta(self, delta_x, delta_y, source):
        if not (self._gesture_direction_enabled and self._gesture_active):
            return
        if self._gesture_cooldown_active():
            self._emit_debug(
                f"Gesture cooldown active source={source} dx={delta_x} dy={delta_y}"
            )
            self._emit_gesture_event(
                {
                    "type": "cooldown_active",
                    "source": source,
                    "dx": delta_x,
                    "dy": delta_y,
                }
            )
            return
        if not self._gesture_tracking:
            self._emit_debug(f"Gesture tracking started source={source}")
            self._emit_gesture_event(
                {
                    "type": "tracking_started",
                    "source": source,
                }
            )
            self._start_gesture_tracking()

        now = time.monotonic()
        idle_ms = (now - self._gesture_last_move_at) * 1000.0
        if idle_ms > self._gesture_timeout_ms:
            self._emit_debug(
                f"Gesture segment reset timeout source={source} "
                f"accum_x={self._gesture_delta_x} accum_y={self._gesture_delta_y}"
            )
            self._start_gesture_tracking()

        if self._gesture_input_source not in (None, source):
            self._emit_debug(
                f"Gesture source locked to {self._gesture_input_source}; "
                f"ignoring {source} dx={delta_x} dy={delta_y}"
            )
            return
        self._gesture_input_source = source

        self._gesture_delta_x += delta_x
        self._gesture_delta_y += delta_y
        self._gesture_last_move_at = now
        self._emit_debug(
            f"Gesture segment source={source} "
            f"accum_x={self._gesture_delta_x} accum_y={self._gesture_delta_y}"
        )
        self._emit_gesture_event(
            {
                "type": "segment",
                "source": source,
                "dx": self._gesture_delta_x,
                "dy": self._gesture_delta_y,
            }
        )

        gesture_event = self._detect_gesture_event()
        if not gesture_event:
            return

        self._gesture_triggered = True
        self._emit_debug(
            "Gesture detected "
            f"{gesture_event} source={source} "
            f"delta_x={self._gesture_delta_x} delta_y={self._gesture_delta_y}"
        )
        self._emit_gesture_event(
            {
                "type": "detected",
                "event_name": gesture_event,
                "source": source,
                "dx": self._gesture_delta_x,
                "dy": self._gesture_delta_y,
            }
        )
        self._dispatch(
            MouseEvent(
                gesture_event,
                {
                    "delta_x": self._gesture_delta_x,
                    "delta_y": self._gesture_delta_y,
                    "source": source,
                },
            )
        )
        self._gesture_cooldown_until = (
            time.monotonic() + self._gesture_cooldown_ms / 1000.0
        )
        self._emit_debug(
            f"Gesture cooldown started source={source} "
            f"for_ms={self._gesture_cooldown_ms}"
        )
        self._emit_gesture_event(
            {
                "type": "cooldown_started",
                "source": source,
                "for_ms": self._gesture_cooldown_ms,
            }
        )
        self._finish_gesture_tracking()

    _WM_NAMES = {
        0x0200: "WM_MOUSEMOVE",
        0x0201: "WM_LBUTTONDOWN",
        0x0202: "WM_LBUTTONUP",
        0x0204: "WM_RBUTTONDOWN",
        0x0205: "WM_RBUTTONUP",
        0x0207: "WM_MBUTTONDOWN",
        0x0208: "WM_MBUTTONUP",
        0x020A: "WM_MOUSEWHEEL",
        0x020B: "WM_XBUTTONDOWN",
        0x020C: "WM_XBUTTONUP",
        0x020E: "WM_MOUSEHWHEEL",
    }

    def _low_level_handler(self, nCode, wParam, lParam):
        try:
            return self._low_level_handler_inner(nCode, wParam, lParam)
        except Exception as exc:
            try:
                self._log_backend_exception(exc, "low-level-callback")
            except Exception:
                pass
            return CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _low_level_handler_inner(self, nCode, wParam, lParam):
        if nCode == HC_ACTION:
            self._last_hook_event_at = time.time()
            data = lParam.contents
            mouse_data = data.mouseData
            flags = data.flags
            binding_snapshot = self.capture_binding_snapshot()
            event = None
            should_block = False

            if self.debug_mode and self._debug_callback:
                wm_name = self._WM_NAMES.get(wParam, f"0x{wParam:04X}")
                if wParam != 0x0200:
                    extra = data.dwExtraInfo.contents.value if data.dwExtraInfo else 0
                    info = (
                        f"{wm_name}  mouseData=0x{mouse_data:08X}  "
                        f"hiword={hiword(mouse_data)}  flags=0x{flags:04X}  "
                        f"extraInfo=0x{extra:X}"
                    )
                    try:
                        self._debug_callback(info)
                    except Exception:
                        pass

            windows_xbutton_event = None
            if wParam == WM_XBUTTONDOWN:
                xbutton = hiword(mouse_data)
                if xbutton == XBUTTON1:
                    windows_xbutton_event = MouseEvent.XBUTTON1_DOWN
                elif xbutton == XBUTTON2:
                    windows_xbutton_event = MouseEvent.XBUTTON2_DOWN
            elif wParam == WM_XBUTTONUP:
                xbutton = hiword(mouse_data)
                if xbutton == XBUTTON1:
                    windows_xbutton_event = MouseEvent.XBUTTON1_UP
                elif xbutton == XBUTTON2:
                    windows_xbutton_event = MouseEvent.XBUTTON2_UP
            if windows_xbutton_event:
                self._observe_windows_xbutton_event(
                    windows_xbutton_event,
                    bool(flags & INJECTED_FLAG),
                    flags,
                )

            if flags & INJECTED_FLAG:
                if windows_xbutton_event and self._claim_reading_button(
                    4 + hiword(mouse_data), wParam == WM_XBUTTONDOWN, "injected"
                ):
                    return 1
                injected_xbutton_event = windows_xbutton_event
                if (
                    injected_xbutton_event
                    and self._consume_logi_xbutton_suppression(injected_xbutton_event)
                ):
                    self._emit_debug(
                        "Suppressed duplicate Logitech native event "
                        f"button={injected_xbutton_event}"
                    )
                    return 1
                return CallNextHookEx(self._hook, nCode, wParam, lParam)

            # Physical event only (injected events returned above):
            # feed the raw observer used by usage stats / button test UI.
            self._mp_emit_raw(wParam, data.pt, mouse_data)

            edge = self._READING_BUTTON_EDGES.get(wParam)
            if wParam in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                button = hiword(mouse_data)
                if button in (XBUTTON1, XBUTTON2):
                    edge = (4 + button, wParam == WM_XBUTTONDOWN)
            observer = getattr(self, "_reading_button_observer", None)
            if observer is not None:
                if edge:
                    try:
                        observer(*edge)
                    except Exception as exc:
                        self._emit_debug(f"Reader button observer failed: {exc}")

            if edge and self._claim_reading_button(*edge, "physical"):
                return 1

            # ── MousePro right-hold gesture chord ──────────────────
            # Reading mode claims are settled above; they take priority.
            if wParam == WM_RBUTTONDOWN and self._mp_chord_allowed():
                self._mp_gesture.press_right()
                return 1

            if wParam == WM_RBUTTONUP and self._mp_gesture.active:
                decision = self._mp_gesture.release_right()
                if decision.replay_right_click:
                    self._mp_replay_right_click()
                return 1

            if wParam == WM_XBUTTONUP:
                side_button = hiword(mouse_data)
                if side_button in self._mp_pending_side_release:
                    # Swallow the matching release edge of a screenshot chord.
                    self._mp_pending_side_release.discard(side_button)
                    return 1

            if (
                wParam == WM_XBUTTONDOWN
                and self._mp_gesture.active
                and self._mp_chord_allowed()
            ):
                side_button = hiword(mouse_data)
                if side_button in self._mp_configured_side_buttons():
                    decision = self._mp_gesture.press_side_button()
                    if decision.action:
                        self._mp_fire(decision.action)
                        self._mp_pending_side_release.add(side_button)
                        return 1

            if wParam == WM_XBUTTONDOWN:
                xbutton = hiword(mouse_data)
                if xbutton == XBUTTON1:
                    event = MouseEvent(MouseEvent.XBUTTON1_DOWN)
                elif xbutton == XBUTTON2:
                    event = MouseEvent(MouseEvent.XBUTTON2_DOWN)

            elif wParam == WM_XBUTTONUP:
                xbutton = hiword(mouse_data)
                if xbutton == XBUTTON1:
                    event = MouseEvent(MouseEvent.XBUTTON1_UP)
                elif xbutton == XBUTTON2:
                    event = MouseEvent(MouseEvent.XBUTTON2_UP)

            elif wParam == WM_MBUTTONDOWN:
                event = MouseEvent(MouseEvent.MIDDLE_DOWN)

            elif wParam == WM_MBUTTONUP:
                event = MouseEvent(MouseEvent.MIDDLE_UP)

            elif wParam == WM_MOUSEWHEEL:
                # Feature ownership is independent of the mapping snapshot/profile.
                reader = getattr(self, "_reading_wheel_handler", None)
                if reader is not None and reader(hiword(mouse_data)):
                    return 1
                if self._mp_gesture.active:
                    # Right button is held: wheel drives the gesture chord
                    # (up -> copy, down -> enhanced paste); skip reverse scroll.
                    wheel_delta = hiword(mouse_data)
                    decision = None
                    if wheel_delta > 0:
                        decision = self._mp_gesture.scroll_up()
                    elif wheel_delta < 0:
                        decision = self._mp_gesture.scroll_down()
                    if decision is not None and decision.action:
                        self._mp_fire(decision.action)
                    return 1
                if self.invert_vscroll:
                    delta = hiword(mouse_data)
                    if delta != 0 and self._ri_hwnd:
                        self._pending_vscroll += -delta
                        if self._vscroll_posted:
                            return 1
                        if PostMessageW(self._ri_hwnd, WM_APP_INJECT_VSCROLL, 0, 0):
                            self._vscroll_posted = True
                            return 1
                        self._pending_vscroll -= -delta
                    elif delta != 0:
                        self._emit_debug(
                            "Invert vertical scroll skipped: raw input window unavailable"
                        )

            elif wParam == WM_MOUSEHWHEEL:
                delta = hiword(mouse_data)
                if delta > 0:
                    event = MouseEvent(MouseEvent.HSCROLL_LEFT, abs(delta))
                elif delta < 0:
                    event = MouseEvent(MouseEvent.HSCROLL_RIGHT, abs(delta))

                if event:
                    should_block = event.event_type in binding_snapshot.blocked_events

                if self.invert_hscroll:
                    if delta != 0 and self._ri_hwnd and not should_block:
                        self._pending_hscroll += -delta
                        if self._hscroll_posted:
                            return 1
                        if PostMessageW(self._ri_hwnd, WM_APP_INJECT_HSCROLL, 0, 0):
                            self._hscroll_posted = True
                            return 1
                        self._pending_hscroll -= -delta
                    elif delta != 0 and not should_block:
                        self._emit_debug(
                            "Invert horizontal scroll skipped: raw input window unavailable"
                        )

            if event:
                self.bind_event(event, binding_snapshot)
                should_block = event.binding_suppressed
                self._emit_debug(
                    "Windows hook event "
                    f"message={self._WM_NAMES.get(wParam, f'0x{wParam:04X}')} "
                    f"button={event.event_type} device=unavailable(WH_MOUSE_LL) "
                    f"blocked={should_block} "
                    f"generation={event.binding_generation} "
                    f"route={event.binding_route or 'native'} "
                    f"callbacks={len(event.binding_callbacks)}"
                )
                self._enqueue_dispatch_event(event)
                if should_block:
                    return 1

        return CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _get_device_name(self, hDevice):
        if hDevice in self._device_name_cache:
            return self._device_name_cache[hDevice]
        try:
            size = c_uint(0)
            GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, None, byref(size))
            if size.value > 0:
                buffer = ctypes.create_unicode_buffer(size.value + 1)
                GetRawInputDeviceInfoW(hDevice, RIDI_DEVICENAME, buffer, byref(size))
                name = buffer.value
            else:
                name = ""
        except Exception:
            name = ""
        self._device_name_cache[hDevice] = name
        return name

    def _is_logitech(self, hDevice):
        return "046d" in self._get_device_name(hDevice).lower()

    def _ri_wndproc(self, hwnd, msg, wParam, lParam):
        try:
            return self._ri_wndproc_inner(hwnd, msg, wParam, lParam)
        except Exception as exc:
            self._log_backend_exception(exc, "raw-input-window")
            return DefWindowProcW(hwnd, msg, wParam, lParam)

    def _ri_wndproc_inner(self, hwnd, msg, wParam, lParam):
        if msg == WM_INPUT:
            try:
                self._process_raw_input(lParam)
            except Exception as exc:
                self._log_backend_exception(exc, "raw-input")
            return 0

        if msg == WM_APP_INJECT_VSCROLL:
            delta = self._pending_vscroll
            self._pending_vscroll = 0
            self._vscroll_posted = False
            if delta != 0:
                _inject_scroll_impl(MOUSEEVENTF_WHEEL, delta)
            return 0

        if msg == WM_APP_INJECT_HSCROLL:
            delta = self._pending_hscroll
            self._pending_hscroll = 0
            self._hscroll_posted = False
            if delta != 0:
                _inject_scroll_impl(MOUSEEVENTF_HWHEEL, delta)
            return 0

        if msg == WM_DEVICECHANGE:
            if wParam == DBT_DEVNODES_CHANGED:
                self._on_device_change()
            return 0

        if msg == WM_POWERBROADCAST and wParam in POWER_RESUME_EVENTS:
            self._on_power_resume(wParam)
            return 1

        return DefWindowProcW(hwnd, msg, wParam, lParam)

    def _process_raw_input(self, lParam):
        size = c_uint(0)
        GetRawInputData(lParam, RID_INPUT, None, byref(size), sizeof(RAWINPUTHEADER))
        if size.value == 0:
            return
        buffer = create_string_buffer(size.value)
        ret = GetRawInputData(
            lParam,
            RID_INPUT,
            buffer,
            byref(size),
            sizeof(RAWINPUTHEADER),
        )
        if ret == 0xFFFFFFFF:
            return
        header = RAWINPUTHEADER.from_buffer_copy(buffer)
        if header.dwType == RIM_TYPEMOUSE:
            self._last_raw_input_at = time.time()
            # Raw Input has useful device identity for diagnostics, but its
            # asynchronous messages cannot be correlated reliably with the
            # synchronous WH_MOUSE_LL event used for suppression and routing.
            mouse = RAWMOUSE.from_buffer_copy(buffer, sizeof(RAWINPUTHEADER))
            xbutton_flags = [
                name
                for flag, name in RAW_XBUTTON_FLAGS.items()
                if mouse.usButtonFlags & flag
            ]
            if xbutton_flags:
                device_name = self._get_device_name(header.hDevice)
                self._emit_debug(
                    "Raw input event "
                    f"buttons={','.join(xbutton_flags)} "
                    f"device_handle={int(header.hDevice or 0)} "
                    f"device={device_name or 'unknown'} "
                    f"logitech={self._is_logitech(header.hDevice)}"
                )
            if not self._is_logitech(header.hDevice):
                return
            self._check_raw_mouse_gesture(header.hDevice, buffer)

    def _check_raw_mouse_gesture(self, hDevice, buffer):
        if self._hid_gesture_available():
            return
        mouse = RAWMOUSE.from_buffer_copy(buffer, sizeof(RAWINPUTHEADER))
        raw_buttons = mouse.ulRawButtons
        prev_buttons = self._prev_raw_buttons.get(hDevice, 0)
        self._prev_raw_buttons[hDevice] = raw_buttons

        extra_now = raw_buttons & ~STANDARD_BUTTON_MASK
        extra_prev = prev_buttons & ~STANDARD_BUTTON_MASK

        if extra_now == extra_prev:
            return
        if extra_now and not extra_prev:
            if not self._gesture_active:
                self._gesture_active = True
                self._gesture_triggered = False
                print(f"[MouseHook] Gesture DOWN (rawBtns extra: 0x{extra_now:X})")
        elif not extra_now and extra_prev:
            if self._gesture_active:
                self._gesture_active = False
                print("[MouseHook] Gesture UP")
                self._dispatch(MouseEvent(MouseEvent.GESTURE_CLICK))

    def _setup_raw_input(self):
        self._raw_input_active = False
        instance = GetModuleHandleW(None)
        if not self._ri_class_registered:
            window_class = WNDCLASSEXW()
            window_class.cbSize = sizeof(WNDCLASSEXW)
            window_class.lpfnWndProc = self._ri_wndproc_ref
            window_class.hInstance = instance
            window_class.lpszClassName = self._ri_class_name
            if not RegisterClassExW(byref(window_class)):
                self._log_backend_error(
                    "raw-input-class-registration",
                    "RegisterClassExW failed "
                    f"winerror={ctypes.get_last_error()}",
                )
                return False
            self._ri_class_registered = True

        self._ri_hwnd = CreateWindowExW(
            0,
            self._ri_class_name,
            "MousePro RI",
            0,
            0,
            0,
            1,
            1,
            None,
            None,
            instance,
            None,
        )
        if not self._ri_hwnd:
            print("[MouseHook] CreateWindowExW failed — gesture detection unavailable")
            self._log_backend_error("raw-input-window", "CreateWindowExW failed")
            return False

        ShowWindow(self._ri_hwnd, SW_HIDE)
        return self._register_raw_input_devices()

    def _register_raw_input_devices(self):
        if not self._ri_hwnd:
            self._raw_input_active = False
            return False
        devices = (RAWINPUTDEVICE * 4)()
        devices[0].usUsagePage = 0x01
        devices[0].usUsage = 0x02
        devices[0].dwFlags = RIDEV_INPUTSINK
        devices[0].hwndTarget = self._ri_hwnd
        devices[1].usUsagePage = 0xFF43
        devices[1].usUsage = 0x0202
        devices[1].dwFlags = RIDEV_INPUTSINK
        devices[1].hwndTarget = self._ri_hwnd
        devices[2].usUsagePage = 0xFF43
        devices[2].usUsage = 0x0204
        devices[2].dwFlags = RIDEV_INPUTSINK
        devices[2].hwndTarget = self._ri_hwnd
        devices[3].usUsagePage = 0x0C
        devices[3].usUsage = 0x01
        devices[3].dwFlags = RIDEV_INPUTSINK
        devices[3].hwndTarget = self._ri_hwnd

        if RegisterRawInputDevices(devices, 4, sizeof(RAWINPUTDEVICE)):
            print("[MouseHook] Raw Input: mice + Logitech HID + consumer")
            self._raw_input_active = True
            return True
        if RegisterRawInputDevices(devices, 2, sizeof(RAWINPUTDEVICE)):
            print("[MouseHook] Raw Input: mice + Logitech HID short")
            self._raw_input_active = True
            return True
        if RegisterRawInputDevices(devices, 1, sizeof(RAWINPUTDEVICE)):
            print("[MouseHook] Raw Input: mice only")
            self._raw_input_active = True
            return True
        print("[MouseHook] Raw Input registration failed")
        self._raw_input_active = False
        self._log_backend_error(
            "raw-input-registration",
            f"RegisterRawInputDevices failed winerror={ctypes.get_last_error()}",
        )
        return False

    def _dispatch_worker(self):
        try:
            while self._running:
                try:
                    event = self._dispatch_queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    self._dispatch(event)
                    self._last_dispatch_event_at = time.time()
                except Exception as exc:
                    self._log_backend_exception(exc, "dispatch-worker-event")
        except Exception as exc:
            if not self._stop_requested:
                self._recovery_required = True
            self._log_backend_exception(exc, "dispatch-worker")

    def _run_hook(self):
        hook_thread_id = windll.kernel32.GetCurrentThreadId()
        self._thread_id = hook_thread_id
        try:
            generation = self._hook_generation + 1
            hook_proc = self._make_hook_proc(generation)
            hook = SetWindowsHookExW(
                WH_MOUSE_LL,
                hook_proc,
                GetModuleHandleW(None),
                0,
            )
            if not hook:
                self._startup_ok = False
                self._log_backend_error(
                    "hook-registration",
                    f"SetWindowsHookExW failed winerror={ctypes.get_last_error()}",
                )
                print("[MouseHook] Failed to install hook!")
                return
            self._hook_generation = generation
            self._hook_proc = hook_proc
            self._hook = hook
            print("[MouseHook] Hook installed successfully")
            self._setup_raw_input()
            self._running = True
            self._startup_ok = True
            self._startup_event.set()

            message = wintypes.MSG()
            while self._running:
                result = GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == 0:
                    if self._running:
                        self._log_backend_error(
                            "message-loop", "GetMessageW received unexpected WM_QUIT"
                        )
                    break
                if result == -1:
                    self._log_backend_error(
                        "message-loop",
                        f"GetMessageW failed winerror={ctypes.get_last_error()}",
                    )
                    break
                TranslateMessage(ctypes.byref(message))
                DispatchMessageW(ctypes.byref(message))
        except Exception as exc:
            self._startup_ok = False
            self._log_backend_exception(exc, "hook-thread")
        finally:
            try:
                if not self._stop_requested:
                    self._recovery_required = True
                self._startup_event.set()
                self._running = False
                self._raw_input_active = False
                if self._ri_hwnd:
                    DestroyWindow(self._ri_hwnd)
                    self._ri_hwnd = None
                self._hook_generation += 1
                self._cleanup_retired_hooks()
                hook = self._hook
                hook_proc = self._hook_proc
                self._hook = None
                self._hook_proc = None
                if hook and not UnhookWindowsHookEx(hook):
                    self._retired_hooks.append((hook, hook_proc))
                    self._recovery_required = True
                    self._log_backend_error(
                        "hook-unregister",
                        "UnhookWindowsHookEx failed during hook-thread exit "
                        f"winerror={ctypes.get_last_error()}",
                    )
                    print(
                        "[MouseHook] HOOK_FAILURE phase=final-unhook "
                        "callback=retained"
                    )
                print("[MouseHook] Hook removed")
            finally:
                if self._thread_id == hook_thread_id:
                    self._thread_id = None

    def _on_device_change(self):
        now = time.time()
        if now - self._last_rehook_time < 2.0:
            return
        self._last_rehook_time = now
        print("[MouseHook] Device change detected — refreshing hook")
        self._device_name_cache.clear()
        self._prev_raw_buttons.clear()
        self._reinstall_hook(reason="device-change")
        # DBT_DEVNODES_CHANGED identifies no particular device. Keep the HID
        # transport intact; its read/health checks handle actual device loss.

    def _on_power_resume(self, resume_event):
        self._last_rehook_time = time.time()
        self._last_hook_event_at = None
        self._last_raw_input_at = None
        self._last_dispatch_event_at = None
        self._raw_input_active = False
        self._device_name_cache.clear()
        self._prev_raw_buttons.clear()
        self._clear_logi_xbutton_suppression("power resume")
        self._clear_logi_xbutton_pressed("power resume")
        print(
            "[MouseHook] POWER_RESUME "
            f"event=0x{int(resume_event):04X} action=refresh-backends"
        )
        hook_refreshed = self._reinstall_hook(reason="power-resume")
        raw_input_refreshed = self._register_raw_input_devices()
        if not hook_refreshed or not raw_input_refreshed:
            self._recovery_required = True
        listener = self._hid_gesture
        if listener is not None and hasattr(listener, "force_reconnect"):
            listener.force_reconnect()

    def _cleanup_retired_hooks(self):
        remaining = []
        for hook, hook_proc in self._retired_hooks:
            try:
                removed = bool(UnhookWindowsHookEx(hook))
            except Exception as exc:
                removed = False
                self._log_backend_exception(exc, "retired-hook-unregister")
            if not removed:
                remaining.append((hook, hook_proc))
        self._retired_hooks = remaining
        return not remaining

    def _reinstall_hook(self, reason="manual"):
        old_hook = self._hook
        old_hook_proc = self._hook_proc
        generation = self._hook_generation + 1
        hook_proc = self._make_hook_proc(generation)
        hook = SetWindowsHookExW(
            WH_MOUSE_LL,
            hook_proc,
            GetModuleHandleW(None),
            0,
        )
        if not hook:
            self._recovery_required = True
            self._log_backend_error(
                "hook-reinstall",
                f"SetWindowsHookExW failed reason={reason} "
                f"winerror={ctypes.get_last_error()}",
            )
            print(
                "[MouseHook] HOOK_FAILURE "
                f"phase=reinstall reason={reason} retained_old={bool(old_hook)}"
            )
            print("[MouseHook] Failed to reinstall hook!")
            return False

        self._hook_generation = generation
        self._hook_proc = hook_proc
        self._hook = hook
        self._recovery_required = False
        if old_hook and not UnhookWindowsHookEx(old_hook):
            # The old callback is generation-gated and cannot dispatch or block,
            # but retain its Python callback object until Windows releases it.
            self._retired_hooks.append((old_hook, old_hook_proc))
            self._log_backend_error(
                "hook-unregister",
                f"UnhookWindowsHookEx failed reason={reason} "
                f"winerror={ctypes.get_last_error()}",
            )
        if not self._cleanup_retired_hooks():
            self._recovery_required = True
        print(f"[MouseHook] Hook reinstalled successfully reason={reason}")
        return True

    def _on_hid_gesture_down(self):
        if not self._gesture_active:
            self._gesture_active = True
            self._gesture_triggered = False
            self._emit_debug("HID gesture button down")
            self._emit_gesture_event({"type": "button_down"})
            if self._gesture_direction_enabled and not self._gesture_cooldown_active():
                self._start_gesture_tracking()
            else:
                self._gesture_tracking = False
                self._gesture_triggered = False

    def _on_hid_gesture_up(self):
        if self._gesture_active:
            should_click = not self._gesture_triggered
            self._gesture_active = False
            self._finish_gesture_tracking()
            self._gesture_triggered = False
            self._emit_debug(
                f"HID gesture button up click_candidate={str(should_click).lower()}"
            )
            self._emit_gesture_event(
                {
                    "type": "button_up",
                    "click_candidate": should_click,
                }
            )
            if should_click:
                self._dispatch(MouseEvent(MouseEvent.GESTURE_CLICK))

    def _on_hid_mode_shift_down(self):
        print("[MouseHook] HID mode shift button down")
        self._emit_debug("HID mode shift button down")
        self._dispatch(MouseEvent(MouseEvent.MODE_SHIFT_DOWN))

    def _on_hid_mode_shift_up(self):
        print("[MouseHook] HID mode shift button up")
        self._emit_debug("HID mode shift button up")
        self._dispatch(MouseEvent(MouseEvent.MODE_SHIFT_UP))

    def _on_hid_dpi_switch_down(self):
        self._emit_debug("HID DPI switch button down")
        self._dispatch(MouseEvent(MouseEvent.DPI_SWITCH_DOWN))

    def _on_hid_dpi_switch_up(self):
        self._emit_debug("HID DPI switch button up")
        self._dispatch(MouseEvent(MouseEvent.DPI_SWITCH_UP))

    def _on_hid_gesture_move(self, delta_x, delta_y):
        self._emit_debug(f"HID rawxy move dx={delta_x} dy={delta_y}")
        self._emit_gesture_event(
            {
                "type": "move",
                "source": "hid_rawxy",
                "dx": delta_x,
                "dy": delta_y,
            }
        )
        self._accumulate_gesture_delta(delta_x, delta_y, "hid_rawxy")

    def start(self):
        if self._hook_thread and self._hook_thread.is_alive():
            return self.health_snapshot().healthy
        if self._retired_hooks and not self._cleanup_retired_hooks():
            self._recovery_required = True
            print(
                "[MouseHook] HOOK_FAILURE phase=start "
                "reason=retired-hook-still-registered"
            )
            return False
        if self._hid_gesture is not None and not self._stop_hid_listener():
            self._recovery_required = True
            print(
                "[MouseHook] HOOK_FAILURE phase=start "
                "reason=previous-hid-listener-still-running"
            )
            return False
        self._stop_requested = False
        self._recovery_required = False
        self._last_hook_event_at = None
        self._last_raw_input_at = None
        self._last_dispatch_event_at = None
        self._pending_vscroll = 0
        self._pending_hscroll = 0
        self._vscroll_posted = False
        self._hscroll_posted = False
        self._prev_raw_buttons.clear()
        self._device_name_cache.clear()
        self._startup_ok = False
        self._startup_event.clear()
        self._hook_thread = threading.Thread(
            target=self._run_hook,
            daemon=True,
            name="WindowsMouseHook",
        )
        self._hook_thread.start()
        if not self._startup_event.wait(2):
            print("[MouseHook] Hook startup timed out")
            self.stop()
            return False
        if not self._startup_ok:
            return False
        listener = self._start_hid_listener()
        if listener is None:
            required = self._hid_listener_required()
            print(
                "[MouseHook] HOOK_FAILURE phase=hid-listener-start "
                f"required={str(required).lower()}"
            )
            if required:
                self._recovery_required = True
                self.stop()
                return False
        self._dispatch_worker_thread = threading.Thread(
            target=self._dispatch_worker,
            daemon=True,
            name="HookDispatch",
        )
        self._dispatch_worker_thread.start()
        return self.health_snapshot().healthy

    def stop(self):
        with self._reading_claim_lock:
            self._reading_claims.clear()
        observer = getattr(self, "_reading_button_observer", None)
        if observer is not None:
            observer(0, False)
        self._stop_requested = True
        self._recovery_required = False
        self._running = False
        listener_stopped = self._stop_hid_listener()
        stopped = listener_stopped
        if self._dispatch_worker_thread:
            if self._dispatch_worker_thread is threading.current_thread():
                stopped = False
            else:
                self._dispatch_worker_thread.join(timeout=1)
                if self._dispatch_worker_thread.is_alive():
                    stopped = False
                else:
                    self._dispatch_worker_thread = None
        if self._thread_id:
            PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._hook_thread:
            if self._hook_thread is threading.current_thread():
                stopped = False
            else:
                self._hook_thread.join(timeout=2)
                if self._hook_thread.is_alive():
                    stopped = False
                else:
                    self._hook_thread = None
        if not self._cleanup_retired_hooks():
            stopped = False
        if stopped:
            self._hook = None
            self._ri_hwnd = None
            self._thread_id = None
            self._startup_ok = False
            self._connected_device = None
            self._device_connected = False
        else:
            self._recovery_required = True
        self._startup_event.clear()
        return stopped


MouseHook._platform_module = sys.modules[__name__]


__all__ = [
    "MouseHook",
    "HidGestureListener",
    "MSLLHOOKSTRUCT",
    "WM_XBUTTONDOWN",
    "WM_XBUTTONUP",
    "WM_MBUTTONDOWN",
    "WM_MBUTTONUP",
    "WM_MOUSEHWHEEL",
    "WM_MOUSEWHEEL",
]
