"""
Mouse usage statistics.

Pure, thread-safe counters populated from the physical mouse event
observer (never from injected events):

* per-button click counts (left / right / middle / xbutton1 / xbutton2);
* wheel notch counts (up / down);
* accumulated pointer travel distance in pixels (euclidean);
* successful feature invocations (copy / enhanced_paste / screenshot).

``shared_stats`` is the process-wide singleton consumed by the engine
and the QML backend.
"""

from __future__ import annotations

import math
import threading

LEFT = "left"
RIGHT = "right"
MIDDLE = "middle"
XBUTTON1 = "xbutton1"
XBUTTON2 = "xbutton2"
WHEEL_UP = "wheel_up"
WHEEL_DOWN = "wheel_down"

_CLICK_CONTROLS = frozenset({LEFT, RIGHT, MIDDLE, XBUTTON1, XBUTTON2})
_WHEEL_CONTROLS = frozenset({WHEEL_UP, WHEEL_DOWN})

FEATURE_COPY = "copy"
FEATURE_ENHANCED_PASTE = "enhanced_paste"
FEATURE_SCREENSHOT = "screenshot"
_FEATURES = (FEATURE_COPY, FEATURE_ENHANCED_PASTE, FEATURE_SCREENSHOT)

_CLICK_FIELDS = {
    LEFT: "_left_clicks",
    RIGHT: "_right_clicks",
    MIDDLE: "_middle_clicks",
    XBUTTON1: "_xbutton1_clicks",
    XBUTTON2: "_xbutton2_clicks",
}


class UsageStatsTracker:
    """Thread-safe aggregate of physical mouse usage."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._left_clicks = 0
        self._right_clicks = 0
        self._middle_clicks = 0
        self._xbutton1_clicks = 0
        self._xbutton2_clicks = 0
        self._wheel_up = 0
        self._wheel_down = 0
        self._distance_pixels = 0.0
        self._last_x: float | None = None
        self._last_y: float | None = None
        self._features = {name: 0 for name in _FEATURES}

    def record_click(self, control: str) -> None:
        field = _CLICK_FIELDS.get(control)
        if field is None:
            return
        with self._lock:
            setattr(self, field, getattr(self, field) + 1)

    def record_wheel(self, control: str) -> None:
        with self._lock:
            if control == WHEEL_UP:
                self._wheel_up += 1
            elif control == WHEEL_DOWN:
                self._wheel_down += 1

    def record_move(self, x: float, y: float) -> None:
        with self._lock:
            if self._last_x is not None and self._last_y is not None:
                self._distance_pixels += math.hypot(
                    x - self._last_x, y - self._last_y
                )
            self._last_x = float(x)
            self._last_y = float(y)

    def record_feature(self, name: str) -> None:
        """Record one successful feature invocation."""
        if name not in _FEATURES:
            return
        with self._lock:
            self._features[name] += 1

    def reset(self) -> None:
        with self._lock:
            self._left_clicks = 0
            self._right_clicks = 0
            self._middle_clicks = 0
            self._xbutton1_clicks = 0
            self._xbutton2_clicks = 0
            self._wheel_up = 0
            self._wheel_down = 0
            self._distance_pixels = 0.0
            self._last_x = None
            self._last_y = None
            for name in _FEATURES:
                self._features[name] = 0

    def snapshot(self) -> dict:
        """Return a plain-dict copy of every counter (thread-safe)."""
        with self._lock:
            return {
                "left_clicks": self._left_clicks,
                "right_clicks": self._right_clicks,
                "middle_clicks": self._middle_clicks,
                "xbutton1_clicks": self._xbutton1_clicks,
                "xbutton2_clicks": self._xbutton2_clicks,
                "wheel_up": self._wheel_up,
                "wheel_down": self._wheel_down,
                "distance_pixels": round(self._distance_pixels, 2),
                "feature_copy": self._features[FEATURE_COPY],
                "feature_enhanced_paste": self._features[
                    FEATURE_ENHANCED_PASTE
                ],
                "feature_screenshot": self._features[FEATURE_SCREENSHOT],
            }


# Process-wide singleton; safe to record to from the low-level hook thread.
shared_stats = UsageStatsTracker()
