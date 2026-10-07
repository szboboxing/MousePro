"""Tests for the pure right-hold gesture state machine and the Windows hook wiring."""

import ctypes
import os
import unittest
from unittest.mock import Mock, patch

from core.right_hold_gesture import (
    GESTURE_COPY,
    GESTURE_ENHANCED_PASTE,
    GESTURE_SYSTEM_SCREENSHOT,
    RightHoldGestureState,
)


class RightHoldGestureStateTests(unittest.TestCase):
    def test_wheel_up_commits_copy_once(self):
        state = RightHoldGestureState()
        state.press_right()
        first = state.scroll_up()
        second = state.scroll_up()
        self.assertEqual(first.action, GESTURE_COPY)
        self.assertIsNone(second.action)

    def test_wheel_down_commits_enhanced_paste(self):
        state = RightHoldGestureState()
        state.press_right()
        self.assertEqual(state.scroll_down().action, GESTURE_ENHANCED_PASTE)

    def test_side_button_commits_screenshot(self):
        state = RightHoldGestureState()
        state.press_right()
        self.assertEqual(
            state.press_side_button().action, GESTURE_SYSTEM_SCREENSHOT
        )
        # Only one action per hold.
        self.assertIsNone(state.scroll_up().action)

    def test_release_without_commit_replays_right_click(self):
        state = RightHoldGestureState()
        state.press_right()
        decision = state.release_right()
        self.assertTrue(decision.replay_right_click)
        self.assertFalse(state.active)

    def test_release_after_commit_does_not_replay(self):
        state = RightHoldGestureState()
        state.press_right()
        state.scroll_up()
        decision = state.release_right()
        self.assertFalse(decision.replay_right_click)
        self.assertFalse(state.active)

    def test_events_without_press_are_ignored(self):
        state = RightHoldGestureState()
        self.assertIsNone(state.scroll_up().action)
        self.assertIsNone(state.scroll_down().action)
        self.assertIsNone(state.press_side_button().action)
        self.assertFalse(state.release_right().replay_right_click)

    def test_cancel_resets_the_hold(self):
        state = RightHoldGestureState()
        state.press_right()
        state.cancel()
        self.assertFalse(state.active)
        self.assertIsNone(state.scroll_up().action)
        self.assertFalse(state.release_right().replay_right_click)


@unittest.skipUnless(os.name == "nt", "Windows low-level hook only")
class RightHoldHookWiringTests(unittest.TestCase):
    def setUp(self):
        from core import mouse_hook_windows as win

        self.win = win
        self.hook = win.MouseHook()
        self.fire = Mock()
        self.hook.set_right_hold_config(
            enabled_cb=lambda: True,
            buttons_cb=lambda: ["xbutton1"],
            fire_cb=self.fire,
            active_test_cb=lambda: False,
        )
        self.observed = []
        self.hook.set_raw_observer(self.observed.append)

    def send(self, message, mouse_data=0, flags=0, x=0, y=0):
        data = self.win.MSLLHOOKSTRUCT()
        data.mouseData = mouse_data
        data.flags = flags
        data.pt.x = x
        data.pt.y = y
        with patch.object(self.win, "CallNextHookEx", return_value=123):
            return self.hook._low_level_handler_inner(
                self.win.HC_ACTION, message, ctypes.pointer(data)
            )

    def test_hold_and_release_without_commit_replays_native_click(self):
        self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 1)
        with patch.object(self.win, "mouse_event") as mouse_event:
            self.assertEqual(self.send(self.win.WM_RBUTTONUP), 1)
        self.assertEqual(
            [call.args[0] for call in mouse_event.call_args_list],
            [
                self.win.MOUSEEVENTF_RIGHTDOWN,
                self.win.MOUSEEVENTF_RIGHTUP,
            ],
        )
        self.fire.assert_not_called()

    def test_wheel_up_fires_copy_and_is_swallowed(self):
        self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 1)
        self.assertEqual(self.send(self.win.WM_MOUSEWHEEL, 120 << 16), 1)
        # Only one action per hold.
        self.assertEqual(self.send(self.win.WM_MOUSEWHEEL, 120 << 16), 1)
        self.assertEqual(self.send(self.win.WM_RBUTTONUP), 1)
        self.fire.assert_called_once_with(GESTURE_COPY)

    def test_wheel_down_fires_enhanced_paste(self):
        self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 1)
        self.assertEqual(self.send(self.win.WM_MOUSEWHEEL, 0xFF880000), 1)
        self.assertEqual(self.send(self.win.WM_RBUTTONUP), 1)
        self.fire.assert_called_once_with(GESTURE_ENHANCED_PASTE)

    def test_configured_side_button_fires_screenshot_and_up_is_held(self):
        self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 1)
        self.assertEqual(
            self.send(self.win.WM_XBUTTONDOWN, 1 << 16), 1
        )
        self.fire.assert_called_once_with(GESTURE_SYSTEM_SCREENSHOT)
        # Matching release edge must stay swallowed.
        self.assertEqual(self.send(self.win.WM_XBUTTONUP, 1 << 16), 1)
        self.assertEqual(self.send(self.win.WM_RBUTTONUP), 1)

    def test_unconfigured_side_button_passes_through(self):
        self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 1)
        # XBUTTON2 is not in the configured subset.
        self.assertEqual(self.send(self.win.WM_XBUTTONDOWN, 2 << 16), 123)

    def test_disabled_feature_passes_right_button_through(self):
        self.hook.set_right_hold_config(
            enabled_cb=lambda: False,
            buttons_cb=lambda: [],
            fire_cb=self.fire,
            active_test_cb=lambda: False,
        )
        with patch.object(self.win, "mouse_event") as mouse_event:
            self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 123)
            self.assertEqual(self.send(self.win.WM_MOUSEWHEEL, 120 << 16), 123)
            self.assertEqual(self.send(self.win.WM_RBUTTONUP), 123)
        mouse_event.assert_not_called()
        self.fire.assert_not_called()

    def test_test_mode_observes_but_does_not_swallow_or_fire(self):
        self.hook.set_test_mode(True)
        try:
            self.assertEqual(self.send(self.win.WM_RBUTTONDOWN), 123)
            self.assertEqual(self.send(self.win.WM_MOUSEWHEEL, 120 << 16), 123)
            self.assertEqual(
                self.send(self.win.WM_XBUTTONDOWN, 1 << 16), 123
            )
        finally:
            self.hook.set_test_mode(False)
        self.fire.assert_not_called()
        controls = {item["control"] for item in self.observed}
        self.assertIn("right", controls)
        self.assertIn("wheel_up", controls)
        self.assertIn("xbutton1", controls)

    def test_observer_sees_physical_but_not_injected_events(self):
        self.send(self.win.WM_LBUTTONDOWN)
        self.send(
            self.win.WM_LBUTTONDOWN, flags=self.win.INJECTED_FLAG
        )
        self.send(self.win.WM_MOUSEMOVE, x=30, y=40)
        physical_clicks = [
            item
            for item in self.observed
            if item["control"] == "left" and item.get("pressed")
        ]
        self.assertEqual(len(physical_clicks), 1)
        move = next(item for item in self.observed if item["control"] == "move")
        self.assertEqual((move["x"], move["y"]), (30, 40))
        self.assertIn("ts", physical_clicks[0])


if __name__ == "__main__":
    unittest.main()
