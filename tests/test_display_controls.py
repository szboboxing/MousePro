"""Tests for display brightness/contrast helpers and controller fallback."""

import os
import unittest

from core.display_controls import (
    DisplayAdjustment,
    _normalize_direction,
    _step_value,
)


class StepValueTests(unittest.TestCase):
    def test_normalize_direction_accepts_only_pm_one(self):
        self.assertEqual(_normalize_direction(1), 1)
        self.assertEqual(_normalize_direction(-1), -1)
        for bad in (0, 2, -2, "up", None):
            with self.assertRaises(ValueError):
                _normalize_direction(bad)

    def test_step_is_roughly_five_percent(self):
        self.assertEqual(_step_value(50, 0, 100, 1), 55)
        self.assertEqual(_step_value(50, 0, 100, -1), 45)

    def test_step_clamps_to_range(self):
        self.assertEqual(_step_value(98, 0, 100, 1), 100)
        self.assertEqual(_step_value(2, 0, 100, -1), 0)
        self.assertEqual(_step_value(0, 0, 10, 1), 1)

    def test_invalid_range_rejected(self):
        with self.assertRaises(ValueError):
            _step_value(5, 100, 0, 1)


@unittest.skipUnless(os.name == "nt", "DDC/CI controller is Windows-only")
class DisplayControllerFallbackTests(unittest.TestCase):
    def setUp(self):
        from core.display_controls import DisplayController

        self.controller = DisplayController()

    def test_wmi_failure_falls_back_to_ddc(self):
        def raise_wmi(direction):
            raise OSError("no WMI brightness")

        self.controller._adjust_wmi_brightness = raise_wmi
        self.controller._adjust_physical_monitors = (
            lambda control, direction: (60, 2)
        )
        result = self.controller.adjust_brightness(1)
        self.assertIsInstance(result, DisplayAdjustment)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 60)
        self.assertIn("DDC/CI", result.detail)

    def test_all_backends_failing_returns_failed_result(self):
        def raise_wmi(direction):
            raise OSError("no WMI brightness")

        def raise_ddc(control, direction):
            raise OSError("monitor does not support DDC/CI")

        self.controller._adjust_wmi_brightness = raise_wmi
        self.controller._adjust_physical_monitors = raise_ddc
        result = self.controller.adjust_brightness(-1)
        self.assertFalse(result.success)
        self.assertIsNone(result.value)

    def test_contrast_uses_physical_monitors(self):
        self.controller._adjust_physical_monitors = (
            lambda control, direction: (70, 1) if control == "contrast"
            else self.fail("contrast must not touch WMI")
        )
        result = self.controller.adjust_contrast(1)
        self.assertTrue(result.success)
        self.assertEqual(result.value, 70)

    def test_contrast_unsupported_monitor(self):
        def raise_ddc(control, direction):
            raise OSError("no DDC/CI")

        self.controller._adjust_physical_monitors = raise_ddc
        result = self.controller.adjust_contrast(1)
        self.assertFalse(result.success)


if __name__ == "__main__":
    unittest.main()
