"""Tests for MousePro quick system actions."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from core.system_actions import (
    ActionResult,
    pointer_size_settings_uri,
    POINTER_SIZE_URI_WIN10,
    POINTER_SIZE_URI_WIN11,
    WIN11_BUILD_THRESHOLD,
)


class PointerSettingsUriTests(unittest.TestCase):
    def test_build_split(self):
        self.assertEqual(
            pointer_size_settings_uri(WIN11_BUILD_THRESHOLD),
            POINTER_SIZE_URI_WIN11,
        )
        self.assertEqual(
            pointer_size_settings_uri(WIN11_BUILD_THRESHOLD + 1234),
            POINTER_SIZE_URI_WIN11,
        )
        self.assertEqual(
            pointer_size_settings_uri(WIN11_BUILD_THRESHOLD - 1),
            POINTER_SIZE_URI_WIN10,
        )
        self.assertEqual(
            pointer_size_settings_uri(19045), POINTER_SIZE_URI_WIN10
        )


@unittest.skipUnless(os.name == "nt", "system actions are Windows-only")
class SystemActionsWindowsTests(unittest.TestCase):
    def setUp(self):
        from core import system_actions

        system_actions._shared_actions = None
        self.module = system_actions

    def test_calculator_success(self):
        actions = self.module.SystemActions()
        with patch.object(self.module.os, "startfile") as start:
            result = actions.open_calculator()
        self.assertTrue(result.success)
        start.assert_called_once_with("calc.exe")

    def test_launch_failure_is_reported(self):
        actions = self.module.SystemActions()
        with patch.object(
            self.module.os, "startfile", side_effect=OSError("boom")
        ):
            result = actions.open_calculator()
        self.assertFalse(result.success)
        self.assertIn("boom", result.detail)

    def test_media_player_falls_back_to_wmplayer(self):
        actions = self.module.SystemActions()
        calls = []

        def fake_startfile(target):
            calls.append(target)
            if target == "mswindowsmusic:":
                raise OSError("no protocol handler")

        with patch.object(self.module.os, "startfile", side_effect=fake_startfile):
            result = actions.open_media_player()
        self.assertTrue(result.success)
        self.assertEqual(calls, ["mswindowsmusic:", "wmplayer.exe"])

    def test_browser_uses_default_browser(self):
        actions = self.module.SystemActions()
        with patch.object(self.module.webbrowser, "open", return_value=True):
            result = actions.open_browser()
        self.assertTrue(result.success)

    def test_enhanced_paste_rejected_outside_explorer(self):
        actions = self.module.SystemActions()
        with patch.object(
            self.module, "get_active_explorer_directory", return_value=None
        ):
            result = actions.create_folder_and_paste_clipboard()
        self.assertFalse(result.success)

    def test_enhanced_paste_creates_folder_and_pastes_in_explorer(self):
        actions = self.module.SystemActions()
        sent = []
        actions._send_keys = lambda keys, name, shortcut: (
            sent.append((tuple(keys), name)) or ActionResult(True, "ok")
        )
        with patch.object(
            self.module,
            "get_active_explorer_directory",
            return_value=Path(r"C:\Users\Tester\Downloads"),
        ), patch.object(self.module.time, "sleep"):
            result = actions.create_folder_and_paste_clipboard()
        self.assertTrue(result.success, msg=result.detail)
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[0][0], (0x11, 0x10, ord("N")))
        self.assertEqual(sent[1][0], (0x11, ord("V")))

    def test_facade_unknown_action(self):
        result = self.module.execute_quick_action("does_not_exist")
        self.assertFalse(result.success)

    def test_facade_routes_brightness(self):
        actions = self.module.SystemActions()
        actions._display = _FakeDisplay()
        with patch.object(
            self.module, "_get_system_actions", return_value=actions
        ):
            up = self.module.execute_quick_action("brightness_up")
            down = self.module.execute_quick_action("contrast_down")
        self.assertTrue(up.success)
        self.assertIn("60", up.message)
        self.assertTrue(down.success)
        self.assertIn("40", down.message)


class _FakeDisplay:
    def adjust_brightness(self, direction):
        from core.display_controls import DisplayAdjustment

        return DisplayAdjustment(True, 60 if direction > 0 else 50, "stub")

    def adjust_contrast(self, direction):
        from core.display_controls import DisplayAdjustment

        return DisplayAdjustment(True, 55 if direction > 0 else 40, "stub")


if __name__ == "__main__":
    unittest.main()
