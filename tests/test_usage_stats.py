"""Tests for the thread-safe mouse usage stats tracker."""

import threading
import unittest

from core.usage_stats import UsageStatsTracker


class UsageStatsTests(unittest.TestCase):
    def test_click_and_wheel_counts(self):
        stats = UsageStatsTracker()
        stats.record_click("left")
        stats.record_click("left")
        stats.record_click("right")
        stats.record_click("middle")
        stats.record_click("xbutton1")
        stats.record_click("xbutton2")
        stats.record_click("not_a_button")
        stats.record_wheel("wheel_up")
        stats.record_wheel("wheel_down")
        stats.record_wheel("sideways")
        snap = stats.snapshot()
        self.assertEqual(snap["left_clicks"], 2)
        self.assertEqual(snap["right_clicks"], 1)
        self.assertEqual(snap["middle_clicks"], 1)
        self.assertEqual(snap["xbutton1_clicks"], 1)
        self.assertEqual(snap["xbutton2_clicks"], 1)
        self.assertEqual(snap["wheel_up"], 1)
        self.assertEqual(snap["wheel_down"], 1)

    def test_move_distance_is_euclidean(self):
        stats = UsageStatsTracker()
        stats.record_move(0, 0)
        stats.record_move(3, 4)
        stats.record_move(6, 8)
        self.assertEqual(stats.snapshot()["distance_pixels"], 10.0)

    def test_feature_recording(self):
        stats = UsageStatsTracker()
        stats.record_feature("copy")
        stats.record_feature("copy")
        stats.record_feature("enhanced_paste")
        stats.record_feature("screenshot")
        stats.record_feature("unknown_feature")
        snap = stats.snapshot()
        self.assertEqual(snap["feature_copy"], 2)
        self.assertEqual(snap["feature_enhanced_paste"], 1)
        self.assertEqual(snap["feature_screenshot"], 1)

    def test_reset_clears_everything(self):
        stats = UsageStatsTracker()
        stats.record_click("left")
        stats.record_move(0, 0)
        stats.record_move(10, 0)
        stats.record_feature("copy")
        stats.reset()
        snap = stats.snapshot()
        self.assertEqual(snap["left_clicks"], 0)
        self.assertEqual(snap["distance_pixels"], 0.0)
        self.assertEqual(snap["feature_copy"], 0)
        # First move after reset establishes the origin again.
        stats.record_move(5, 5)
        stats.record_move(8, 9)
        self.assertEqual(stats.snapshot()["distance_pixels"], 5.0)

    def test_concurrent_increments_are_consistent(self):
        stats = UsageStatsTracker()

        def worker():
            for _ in range(1000):
                stats.record_click("left")
                stats.record_wheel("wheel_up")
                stats.record_feature("screenshot")

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        snap = stats.snapshot()
        self.assertEqual(snap["left_clicks"], 8000)
        self.assertEqual(snap["wheel_up"], 8000)
        self.assertEqual(snap["feature_screenshot"], 8000)


if __name__ == "__main__":
    unittest.main()
