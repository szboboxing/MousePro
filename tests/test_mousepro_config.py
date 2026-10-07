"""Tests for the MousePro config section, sanitizer and migration."""

import json
import os
import tempfile
import unittest

from core import config as core_config
from core.config import (
    DEFAULT_CONFIG,
    _migrate,
    load_config,
    sanitize_mousepro_section,
    save_config,
)


class MouseProDefaultsTests(unittest.TestCase):
    def test_defaults_present(self):
        section = DEFAULT_CONFIG["mousepro"]
        self.assertIs(section["right_hold_gesture_enabled"], True)
        self.assertEqual(
            section["screenshot_side_buttons"], ["xbutton1", "xbutton2"]
        )
        self.assertGreaterEqual(DEFAULT_CONFIG["version"], 12)


class SanitizeTests(unittest.TestCase):
    def test_unknown_buttons_filtered_and_order_preserved(self):
        cfg = {"mousepro": {
            "right_hold_gesture_enabled": False,
            "screenshot_side_buttons": ["xbutton2", "junk", "xbutton1", 3],
        }}
        sanitize_mousepro_section(cfg)
        self.assertEqual(
            cfg["mousepro"]["screenshot_side_buttons"],
            ["xbutton2", "xbutton1"],
        )
        self.assertIs(cfg["mousepro"]["right_hold_gesture_enabled"], False)

    def test_empty_list_falls_back_to_both_buttons(self):
        cfg = {"mousepro": {"screenshot_side_buttons": []}}
        sanitize_mousepro_section(cfg)
        self.assertEqual(
            cfg["mousepro"]["screenshot_side_buttons"],
            ["xbutton1", "xbutton2"],
        )

    def test_invalid_types_fall_back_to_defaults(self):
        cfg = {"mousepro": {
            "right_hold_gesture_enabled": "yes",
            "screenshot_side_buttons": "xbutton1",
        }}
        sanitize_mousepro_section(cfg)
        self.assertIs(cfg["mousepro"]["right_hold_gesture_enabled"], True)
        self.assertEqual(
            cfg["mousepro"]["screenshot_side_buttons"],
            ["xbutton1", "xbutton2"],
        )

    def test_missing_or_non_dict_section_is_rebuilt(self):
        cfg = {}
        sanitize_mousepro_section(cfg)
        self.assertIn("mousepro", cfg)
        self.assertEqual(
            cfg["mousepro"]["screenshot_side_buttons"],
            ["xbutton1", "xbutton2"],
        )

        cfg = {"mousepro": "broken"}
        sanitize_mousepro_section(cfg)
        self.assertIsInstance(cfg["mousepro"], dict)


class MigrationTests(unittest.TestCase):
    def test_v11_config_gains_mousepro_section(self):
        cfg = {"version": 11, "profiles": {}, "settings": {}}
        migrated = _migrate(cfg)
        self.assertEqual(migrated["version"], 12)
        self.assertIn("mousepro", migrated)
        self.assertTrue(
            migrated["mousepro"]["right_hold_gesture_enabled"]
        )


class MouseProConfigPersistenceTests(unittest.TestCase):
    def setUp(self):
        self._sandbox = tempfile.TemporaryDirectory(
            prefix="mousepro-config-tests-"
        )
        self._prev_dir = core_config.CONFIG_DIR
        self._prev_file = core_config.CONFIG_FILE
        core_config.CONFIG_DIR = os.path.join(self._sandbox.name, "MousePro")
        core_config.CONFIG_FILE = os.path.join(
            core_config.CONFIG_DIR, "config.json"
        )

    def tearDown(self):
        core_config.CONFIG_DIR = self._prev_dir
        core_config.CONFIG_FILE = self._prev_file
        self._sandbox.cleanup()

    def test_garbage_section_on_disk_is_repaired_on_load(self):
        os.makedirs(core_config.CONFIG_DIR, exist_ok=True)
        with open(core_config.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"mousepro": {"screenshot_side_buttons": []}}, f)
        cfg = load_config()
        self.assertEqual(
            cfg["mousepro"]["screenshot_side_buttons"],
            ["xbutton1", "xbutton2"],
        )

    def test_settings_round_trip(self):
        cfg = load_config()
        cfg["mousepro"]["right_hold_gesture_enabled"] = False
        cfg["mousepro"]["screenshot_side_buttons"] = ["xbutton2"]
        save_config(cfg)
        reloaded = load_config()
        self.assertFalse(reloaded["mousepro"]["right_hold_gesture_enabled"])
        self.assertEqual(
            reloaded["mousepro"]["screenshot_side_buttons"], ["xbutton2"]
        )


if __name__ == "__main__":
    unittest.main()
