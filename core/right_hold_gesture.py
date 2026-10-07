"""
Pure state machine for the right-button-hold gesture chord.

The state machine is platform neutral and contains no ctypes or Windows
imports so it can be unit tested on every platform.  The Windows hook
(core/mouse_hook_windows.py) owns the actual event swallowing/replay
policy on top of this state.

Gesture semantics (ported from the legacy mouse-gesture-actions project):

* press and hold the right button;
* wheel up   -> copy;
* wheel down -> enhanced paste (new folder + paste);
* side button -> system screenshot;
* release without committing anything -> replay a native right click.

At most one action is committed per right-button hold.
"""

from __future__ import annotations

from dataclasses import dataclass

# Action ids shared with key_simulator / engine / config.
GESTURE_COPY = "copy"
GESTURE_ENHANCED_PASTE = "enhanced_paste"
GESTURE_SYSTEM_SCREENSHOT = "system_screenshot"


@dataclass(frozen=True)
class StateDecision:
    """Result of a state-machine transition."""

    action: str | None = None
    replay_right_click: bool = False


class RightHoldGestureState:
    """Pure state machine for actions performed while right is held."""

    def __init__(self) -> None:
        self._active = False
        self._action_committed = False

    @property
    def active(self) -> bool:
        return self._active

    def press_right(self) -> None:
        self._active = True
        self._action_committed = False

    def scroll_up(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=GESTURE_COPY)

    def scroll_down(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=GESTURE_ENHANCED_PASTE)

    def press_side_button(self) -> StateDecision:
        if not self._active or self._action_committed:
            return StateDecision()
        self._action_committed = True
        return StateDecision(action=GESTURE_SYSTEM_SCREENSHOT)

    def release_right(self) -> StateDecision:
        if not self._active:
            return StateDecision()

        if not self._action_committed:
            decision = StateDecision(replay_right_click=True)
        else:
            decision = StateDecision()
        self.cancel()
        return decision

    def cancel(self) -> None:
        self._active = False
        self._action_committed = False
