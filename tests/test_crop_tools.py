"""Offline tests for the crop tools (no API key, no internet). Run: python -m unittest discover tests"""
import json
import os
import tempfile
import unittest
from unittest import mock

import pandas as pd

from tools import crop_tools

TOMATO = {"Date": pd.date_range("2026-10-01", periods=8), "Soil_Moisture": [31, 29, 28, 27, 26, 24, 23, 22],
          "Nitrogen": [40] * 8, "P": [20] * 8, "K": [30] * 8}
KAGGLE = {"N": [90, 85, 60], "P": [42, 40, 30], "K": [43, 41, 35], "temperature": [20, 21, 25],
          "humidity": [80, 82, 70], "ph": [6.5, 6.4, 6.0], "rainfall": [200, 210, 100], "label": ["rice", "rice", "maize"]}
REQ = {"tomato": {"source": "test", "ideal": {"N": 70, "P": 30, "K": 40, "moisture": 60},
                  "stages": {"flowering": {"moisture": 65}}},
       "rice": {"source": "test", "ideal": {"N": 80, "P": 40, "K": 40}}}


class CropToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("AGENTX_DATA_DIR")
        os.environ["AGENTX_DATA_DIR"] = self.tmp.name
        req = os.path.join(self.tmp.name, "req.json")
        with open(req, "w") as f:
            json.dump(REQ, f)
        patcher = mock.patch.object(crop_tools, "KNOWLEDGE", req)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        if self.old is None:
            os.environ.pop("AGENTX_DATA_DIR", None)
        else:
            os.environ["AGENTX_DATA_DIR"] = self.old
        self.tmp.cleanup()

    def write(self, data):
        pd.DataFrame(data).to_csv(os.path.join(self.tmp.name, "soil_telemetry.csv"), index=False)

    def run_tool(self, cls, **kw):
        out = cls().execute(**kw)
        self.assertIsInstance(out, str)
        return json.loads(out)                      # every tool must return valid JSON

    def test_column_aliases_and_readings(self):
        self.write(TOMATO)
        r = self.run_tool(crop_tools.GetSoilReadings, days="7")
        self.assertTrue({"moisture", "N", "P", "K"} <= set(r["columns"]))
        self.assertEqual(r["latest"]["moisture"], 22)

    def test_trend_falling(self):
        self.write(TOMATO)
        r = self.run_tool(crop_tools.AnalyzeTrend, column="moisture")
        self.assertEqual(r["status"], "falling")

    def test_trend_needs_three_readings(self):
        self.write({k: v[:2] for k, v in TOMATO.items()})
        self.assertIn("error", self.run_tool(crop_tools.AnalyzeTrend, column="moisture"))

    def test_kaggle_shape_without_time_column(self):
        self.write(KAGGLE)
        r = self.run_tool(crop_tools.GetSoilReadings)
        self.assertFalse(r["has_time_column"])
        self.assertIn("rice", r["crops_in_data"])
        e = self.run_tool(crop_tools.AnalyzeTrend, column="moisture")
        self.assertIn("Available", e["error"])

    def test_empty_and_missing_files_do_not_crash(self):
        with open(os.path.join(self.tmp.name, "soil_telemetry.csv"), "w") as f:
            f.write("")
        for cls in (crop_tools.GetSoilReadings, crop_tools.AnalyzeTrend, crop_tools.CalculateDosage):
            self.assertIn("error", self.run_tool(cls))
        os.remove(os.path.join(self.tmp.name, "soil_telemetry.csv"))
        self.assertIn("error", self.run_tool(crop_tools.GetSoilReadings))

    def test_requirements_stage_and_unknown_crop(self):
        r = self.run_tool(crop_tools.CropRequirements, crop="Tomato", stage="flowering")
        self.assertEqual(r["ideal"]["moisture"], 65)
        self.assertEqual(r["ideal"]["N"], 70)
        e = self.run_tool(crop_tools.CropRequirements, crop="banana")
        self.assertIn("tomato", e["known_crops"])

    def test_dosage_values_and_assumptions(self):
        self.write(TOMATO)
        r = self.run_tool(crop_tools.CalculateDosage, crop="tomato", area_acres="2", stage="flowering")
        self.assertAlmostEqual(r["dosage"]["N"]["deficit"], 30.0)
        self.assertGreater(r["dosage"]["N"]["dose_kg"], 0)
        self.assertGreater(r["dosage"]["water"]["litres"], 0)
        self.assertIn("agriculture officer", r["assumptions"])

    def test_dosage_is_capped(self):
        big = dict(TOMATO, Nitrogen=[0] * 8)
        req = os.path.join(self.tmp.name, "req.json")
        with open(req, "w") as f:
            json.dump({"tomato": {"source": "t", "ideal": {"N": 5000}}}, f)
        self.write(big)
        r = self.run_tool(crop_tools.CalculateDosage, crop="tomato", area_acres=1)
        self.assertLessEqual(r["dosage"]["N"]["dose_kg"], crop_tools.MAX_NUTRIENT_KG_PER_ACRE)
        self.assertTrue(r["notes"])

    def test_dosage_refuses_bad_input(self):
        self.write({k: v[:2] for k, v in TOMATO.items()})
        self.assertIn("error", self.run_tool(crop_tools.CalculateDosage, crop="tomato"))
        self.write(TOMATO)
        self.assertIn("error", self.run_tool(crop_tools.CalculateDosage, crop="tomato", area_acres=0))
        self.assertIn("error", self.run_tool(crop_tools.CalculateDosage, crop="banana"))

    def test_weather_failure_and_success(self):
        with mock.patch.object(crop_tools.requests, "get", side_effect=TimeoutError), \
                mock.patch.object(crop_tools.time, "sleep"):
            e = self.run_tool(crop_tools.WeatherForecast)
        self.assertIn("unavailable", e["error"])
        fake = mock.Mock()
        fake.json.return_value = {"daily": {"precipitation_probability_max": [70, 20, 10],
                                            "precipitation_sum": [8.0, 0.0, 0.0]}}
        with mock.patch.object(crop_tools.requests, "get", return_value=fake):
            r = self.run_tool(crop_tools.WeatherForecast, lat="10.79", lon="78.7")
        self.assertEqual(r["rain_probability_pct"][0], 70)

    def test_unexpected_arguments_are_ignored(self):
        self.write(TOMATO)
        self.assertNotIn("error", self.run_tool(crop_tools.GetSoilReadings, days=7, bogus="x"))


if __name__ == "__main__":
    unittest.main()