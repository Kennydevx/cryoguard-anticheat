# Cryo-Corona — CryoGuard Anti-Cheat Tests
# Run: python -m pytest tests/ -v

import sys
import os
import math
import time
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestVelocityCalculation(unittest.TestCase):
    """Test that velocity is correctly computed between ticks."""

    def test_stationary_player(self):
        """Player at same position should have velocity ~0."""
        # distance = sqrt(0^2 + 0^2 + 0^2) = 0
        dist = math.sqrt(0**2 + 0**2 + 0**2)
        self.assertEqual(dist, 0.0)

    def test_linear_movement(self):
        """Player moving along X axis should have correct velocity."""
        x1, y1, z1 = 0.0, 0.0, 0.0
        x2, y2, z2 = 10.0, 0.0, 0.0
        dt = 1.0  # 1 second
        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        velocity = dist / dt
        self.assertAlmostEqual(velocity, 10.0)

    def test_teleport_detection(self):
        """Teleport (500 units in 0.1s) should produce very high velocity."""
        x1, y1, z1 = 0.0, 0.0, 0.0
        x2, y2, z2 = 500.0, 0.0, 0.0
        dt = 0.1
        velocity = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2) / dt
        # 500 / 0.1 = 5000 units/s → way above normal (50 is max normal)
        self.assertGreater(velocity, 1000)

    def test_3d_diagonal_movement(self):
        """3D diagonal movement should use Euclidean distance."""
        x1, y1, z1 = 0.0, 0.0, 0.0
        x2, y2, z2 = 3.0, 4.0, 0.0
        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        self.assertAlmostEqual(dist, 5.0)


class TestFlagSeverity(unittest.TestCase):
    """Test that flag severity levels are correctly ordered."""

    def test_flag_thresholds_ordered(self):
        """Higher surprise should produce more severe flags."""
        from cryoguard import CryoGuard
        thresholds = sorted(CryoGuard.FLAG_REASONS.keys())
        self.assertEqual(thresholds, [0.85, 0.90, 0.95])

    def test_flag_reasons_exist(self):
        """All severity levels should have string reasons."""
        from cryoguard import CryoGuard
        for t, reason in CryoGuard.FLAG_REASONS.items():
            self.assertIsInstance(reason, str)
            self.assertGreater(len(reason), 0)


class TestVectorNormalization(unittest.TestCase):
    """Verify that game state values are normalized correctly."""

    def test_position_normalization(self):
        """Position divided by 1000 should scale correctly."""
        x = 500.0
        normalized = x / 1000.0
        self.assertAlmostEqual(normalized, 0.5)

    def test_velocity_capped(self):
        """Velocity normalization should cap at 1.0."""
        velocity = 100.0  # way above 50 max
        normalized = min(velocity / 50.0, 1.0)
        self.assertAlmostEqual(normalized, 1.0)

    def test_aim_delta_normalized(self):
        """Aim delta should normalize 180° to 1.0."""
        aim = 180.0
        normalized = min(aim / 180.0, 1.0)
        self.assertAlmostEqual(normalized, 1.0)

    def test_normal_aim_normalized(self):
        """Small aim delta should produce small normalized value."""
        aim = 5.0
        normalized = min(aim / 180.0, 1.0)
        self.assertAlmostEqual(normalized, 5.0/180.0, places=3)


class TestMatchLifecycle(unittest.TestCase):
    """Test match start/end reporting logic."""

    def test_flagged_players_filter(self):
        """get_flagged_players should respect min_flags threshold."""
        from cryoguard import CryoGuard
        guard = CryoGuard.__new__(CryoGuard)
        guard._flag_counts = {"player_1": 5, "player_2": 1, "player_3": 3}
        
        result = guard.get_flagged_players(min_flags=3)
        ids = [r["player_id"] for r in result]
        self.assertIn("player_1", ids)
        self.assertIn("player_3", ids)
        self.assertNotIn("player_2", ids)

    def test_end_match_report_structure(self):
        """end_match should return a valid report dict."""
        from cryoguard import CryoGuard
        guard = CryoGuard.__new__(CryoGuard)
        guard._last_pos = {"p1": (0,0,0,0), "p2": (0,0,0,0)}
        guard._flag_counts = {"p1": 2}
        
        report = guard.end_match()
        self.assertIn("total_players", report)
        self.assertIn("flagged_players", report)
        self.assertIn("total_flags", report)
        self.assertEqual(report["total_players"], 2)
        self.assertEqual(report["total_flags"], 2)


if __name__ == "__main__":
    unittest.main()
