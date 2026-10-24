"""Checks for bulk SGP4 propagation used by the live radar."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from satlink.core.propagator import OrbitPropagator
from satlink.core.radar import propagate_radar


class RadarPropagationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snapshot = Path(__file__).resolve().parents[1] / "src/satlink/core/assets/tle/stations.json"
        cls.iss = json.loads(snapshot.read_text(encoding="utf-8"))["satellites"][0]
        cls.at = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

    def test_bulk_position_matches_existing_single_satellite_model(self):
        bulk = propagate_radar([("stations", [self.iss])], self.at)["satellites"][0]
        single = OrbitPropagator(self.iss["name"], self.iss["line1"], self.iss["line2"]).get_current_state(self.at)
        self.assertAlmostEqual(bulk["latitude"], single["latitude"], delta=0.02)
        longitude_difference = (bulk["longitude"] - single["longitude"] + 180) % 360 - 180
        self.assertAlmostEqual(longitude_difference, 0, delta=0.02)
        self.assertAlmostEqual(bulk["altitude_km"], single["altitude_km"], delta=1)
        self.assertAlmostEqual(bulk["speed_km_s"], single["speed_km_s"], delta=0.03)

    def test_object_in_multiple_groups_is_only_drawn_once(self):
        result = propagate_radar([("stations", [self.iss]), ("active", [self.iss])], self.at)
        self.assertEqual(result["total_cataloged"], 1)
        self.assertEqual(len(result["satellites"]), 1)
        self.assertEqual(result["satellites"][0]["group"], "stations")


if __name__ == "__main__":
    unittest.main()
