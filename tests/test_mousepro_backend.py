"""Contract tests for the MousePro QML backend surface."""

import copy
import os
import sys
import tempfile
import unittest
import unittest.mock

from core import config as core_config
from core.config import DEFAULT_CONFIG

_CONFIG_SANDBOX = tempfile.TemporaryDirectory(prefix="mousepro-mp-backend-")
core_config.CONFIG_DIR = os.path.join(_CONFIG_SANDBOX.name, "MousePro")
core_config.CONFIG_FILE = os.path.join(core_config.CONFIG_DIR, "config.json")

try:
    from PySide6.QtCore import QCoreApplication
    from ui import backend as ui_backend
    from ui.backend import Backend
    from ui.locale_manager import LocaleManager
except ModuleNotFoundError:
    Backend = None
    LocaleManager = None
    QCoreApplication = None


def _ensure_qapp():
    app = QCoreApplication.instance()
    if app is None:
        return QCoreApplication(sys.argv)
    return app


class _FakeMpEngine:
    def __init__(self, cfg=None):
        self.cfg = copy.deepcopy(cfg or DEFAULT_CONFIG)
        self.device_connected = False
        self.hid_features_ready = False
        self.connected_device = None
        self.gesture_enabled_calls = []
        self.side_buttons_calls = []
        self.test_active_calls = []
        self.listeners = []
        self.confirm_started = 0
        self.confirm_cancelled = 0
        self.saved_confirm_buttons = None
        self.quick_action_requests = []
        self.stats_reset = 0
        self.next_quick_result = {"ok": True, "detail": "done"}

    # Backend.__init__ wiring
    def set_profile_change_callback(self, cb): pass
    def set_dpi_read_callback(self, cb): pass
    def set_connection_change_callback(self, cb): pass
    def set_status_callback(self, cb): pass

    # MousePro surface
    def set_right_hold_gesture_enabled(self, enabled):
        self.gesture_enabled_calls.append(enabled)
        self.cfg["mousepro"]["right_hold_gesture_enabled"] = enabled

    def set_screenshot_side_buttons(self, buttons):
        self.side_buttons_calls.append(list(buttons))
        self.cfg["mousepro"]["screenshot_side_buttons"] = list(buttons)
        return list(buttons)

    def run_quick_action(self, action_id):
        self.quick_action_requests.append(action_id)
        return copy.deepcopy(self.next_quick_result)

    def get_usage_stats(self):
        return {"left_clicks": 7, "distance_pixels": 12.5}

    def reset_usage_stats(self):
        self.stats_reset += 1

    def add_test_event_listener(self, cb):
        self.listeners.append(cb)

    def remove_test_event_listener(self, cb):
        self.listeners = [item for item in self.listeners if item != cb]

    def set_button_test_active(self, active):
        self.test_active_calls.append(active)

    def start_side_button_confirm(self, listener):
        self.confirm_started += 1
        self.listeners.append(listener)

    def cancel_side_button_confirm(self):
        self.confirm_cancelled += 1

    def save_confirmed_side_buttons(self, buttons):
        self.saved_confirm_buttons = list(buttons)
        self.cfg["mousepro"]["screenshot_side_buttons"] = list(buttons)
        return list(buttons)


@unittest.skipIf(Backend is None, "PySide6 unavailable")
class MouseProBackendTests(unittest.TestCase):
    def setUp(self):
        _ensure_qapp()
        self.engine = _FakeMpEngine()
        self.backend = Backend(
            engine=self.engine,
            locale_manager=LocaleManager("en"),
        )

    def test_supported_flag_and_defaults(self):
        self.assertIs(self.backend.enhancementsSupported, os.name == "nt")
        self.assertTrue(self.backend.rightHoldGestureEnabled)
        self.assertEqual(
            self.backend.screenshotSideButtons, ["xbutton1", "xbutton2"]
        )

    def test_right_hold_gesture_persists(self):
        self.backend.setRightHoldGestureEnabled(False)
        self.assertFalse(self.backend.rightHoldGestureEnabled)
        self.assertEqual(self.engine.gesture_enabled_calls, [False])

    def test_side_buttons_are_filtered(self):
        self.backend.setScreenshotSideButtons(
            ["xbutton2", "xbutton1", "middle"]
        )
        self.assertEqual(
            self.engine.side_buttons_calls[-1], ["xbutton2", "xbutton1"]
        )
        self.assertEqual(
            self.backend.screenshotSideButtons, ["xbutton2", "xbutton1"]
        )

    def test_side_buttons_accept_qjsvalue_arrays(self):
        # QML passes JavaScript arrays into QVariant slots as QJSValue,
        # which is not iterable from Python before normalization.
        class _QJSValueLike:
            def __init__(self, value):
                self._value = value

            def toVariant(self):
                return self._value

        self.backend.setScreenshotSideButtons(
            _QJSValueLike(["xbutton2", "xbutton1"])
        )
        self.assertEqual(
            self.engine.side_buttons_calls[-1], ["xbutton2", "xbutton1"]
        )
        saved = self.backend.saveConfirmedSideButtons(
            _QJSValueLike(["xbutton1"])
        )
        self.assertEqual(saved, ["xbutton1"])

    def test_run_quick_action_returns_contract(self):
        result = self.backend.runQuickAction("calculator")
        self.assertEqual(set(result.keys()), {"ok", "title", "detail"})
        self.assertTrue(result["ok"])
        self.assertEqual(result["title"], "Calculator")
        self.assertEqual(self.engine.quick_action_requests, ["calculator"])

    def test_run_quick_action_title_localized(self):
        backend = Backend(
            engine=self.engine,
            locale_manager=LocaleManager("zh_CN"),
        )
        result = backend.runQuickAction("calculator")
        self.assertEqual(result["title"], "计算器")

    def test_run_quick_action_unsupported_on_non_windows(self):
        with unittest.mock.patch.object(
            ui_backend.sys, "platform", "linux"
        ):
            result = self.backend.runQuickAction("calculator")
        self.assertFalse(result["ok"])
        self.assertIn("Windows", result["detail"])
        self.assertEqual(self.engine.quick_action_requests, [])

    def test_usage_stats_and_reset(self):
        stats = self.backend.usageStats
        self.assertEqual(stats["left_clicks"], 7)
        self.backend.resetUsageStats()
        self.assertEqual(self.engine.stats_reset, 1)

    def test_test_mode_switches_hook_capture_and_counts_events(self):
        # Signal spelling is part of the QML contract: testEventOccurred
        # (the historical "Occerved" typo must never come back).
        self.assertTrue(hasattr(self.backend, "testEventOccurred"))
        self.assertFalse(hasattr(self.backend, "testEventOccerved"))
        received = []
        self.backend.testEventOccurred.connect(lambda event: received.append(event))

        self.backend.setButtonTestActive(True)
        self.assertIn(self.backend._onMpTestEvent, self.engine.listeners)
        self.assertEqual(self.engine.test_active_calls, [True])

        self.backend._onMpTestEvent(
            {"control": "left", "pressed": True, "ts": 1}
        )
        self.backend._onMpTestEvent(
            {"control": "wheel_up", "pressed": None, "delta": 120, "ts": 2}
        )
        self.backend._onMpTestEvent(
            {"control": "move", "pressed": None, "x": 1, "y": 1, "ts": 3}
        )
        counts = self.backend.testCounts
        self.assertEqual(counts["left"], 1)
        self.assertEqual(counts["wheel_up"], 1)
        self.assertEqual(counts["wheel_down"], 0)
        self.assertEqual(self.backend.lastTestEvent["control"], "move")

        self.backend.resetTestCounts()
        self.assertEqual(sum(self.backend.testCounts.values()), 0)
        # Starting a session and resetting both emit an empty "clear" event;
        # the physical payloads arrive in between.
        self.assertEqual(received[0], {})
        self.assertEqual(received[-1], {})
        self.assertEqual(
            [event.get("control") for event in received if event],
            ["left", "wheel_up", "move"],
        )

        self.backend.setButtonTestActive(False)
        self.assertEqual(self.engine.test_active_calls[-1], False)
        self.assertNotIn(self.backend._onMpTestEvent, self.engine.listeners)

    def test_side_button_confirm_capture_and_save(self):
        # Start with only XBUTTON1 configured.
        self.engine.cfg["mousepro"]["screenshot_side_buttons"] = ["xbutton1"]
        self.backend.screenshotSideButtonsChanged  # touch property
        self.backend.startSideButtonConfirm()
        self.assertTrue(self.backend.sideButtonConfirmActive)
        self.assertEqual(self.engine.confirm_started, 1)

        self.backend._onMpTestEvent(
            {"control": "xbutton2", "pressed": True, "ts": 9}
        )
        saved = self.backend.saveConfirmedSideButtons([])
        self.assertFalse(self.backend.sideButtonConfirmActive)
        self.assertIn("xbutton2", saved)
        self.assertEqual(
            self.engine.saved_confirm_buttons, saved
        )

    def test_side_button_confirm_cancel(self):
        self.backend.startSideButtonConfirm()
        self.backend.cancelSideButtonConfirm()
        self.assertFalse(self.backend.sideButtonConfirmActive)
        self.assertEqual(self.engine.confirm_cancelled, 1)

    def test_action_categories_include_mousepro_group(self):
        categories = {
            group["category"]: group["actions"]
            for group in self.backend.actionCategories
        }
        self.assertIn("MousePro", categories)
        ids = {item["id"] for item in categories["MousePro"]}
        self.assertIn("calculator", ids)
        self.assertIn("enhanced_paste", ids)
        self.assertIn("system_screenshot", ids)


if __name__ == "__main__":
    unittest.main()
