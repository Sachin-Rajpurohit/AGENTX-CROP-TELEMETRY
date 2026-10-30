"""Offline tests (no API key). Run: python -m unittest discover tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

# Fixture data folder. Set BEFORE importing tools so any module that reads the env at import time sees it.
_FIXTURE = tempfile.mkdtemp()
with open(os.path.join(_FIXTURE, "soil_telemetry.csv"), "w", encoding="utf-8") as f:
    f.write("timestamp,moisture,N,P,K,pH\n")
    for i, m in enumerate([31, 29, 28, 27, 26, 24, 23, 22]):
        f.write(f"2026-10-0{i+1} 08:00,{m},40,20,30,6.4\n")
os.environ["AGENTX_DATA_DIR"] = _FIXTURE

from agent.core import AgentExecutor, parse_json
from tools import build_tools


class Scripted:
    def __init__(self, replies):
        self.replies = list(replies)

    def generate(self, system, messages):
        return self.replies.pop(0) if self.replies else '{"final_answer": "done"}'


class AgentTests(unittest.TestCase):
    def test_parse_json_handles_fences(self):
        self.assertEqual(parse_json('text ```json\n{"a": 1}\n``` more'), {"a": 1})

    def test_tool_call_then_final(self):
        llm = Scripted(['{"thought":"t","action":"get_soil_readings","args":{"days":7}}',
                        '{"thought":"t","final_answer":"moisture is low"}'])
        answer, trace = AgentExecutor(llm, build_tools()).run("q")
        self.assertEqual(answer, "moisture is low")
        self.assertEqual(trace[0]["tool"], "get_soil_readings")
        self.assertIn("moisture", trace[0]["observation"])

    def test_crop_tools_in_the_loop(self):
        llm = Scripted(['{"thought":"t","action":"analyze_trend","args":{"column":"moisture"}}',
                        '{"thought":"t","final_answer":"YELLOW"}'])
        _, trace = AgentExecutor(llm, build_tools()).run("q")
        self.assertIn("falling", trace[0]["observation"])

    def test_tool_error_becomes_observation(self):
        llm = Scripted(['{"action":"read_file","args":{"filename":"nope.csv"}}', '{"final_answer":"x"}'])
        _, trace = AgentExecutor(llm, build_tools()).run("q")
        self.assertTrue(trace[0]["observation"].startswith("ERROR"))

    def test_iteration_cap(self):
        llm = Scripted(['{"action":"list_files","args":{}}'] * 20)
        answer, trace = AgentExecutor(llm, build_tools(), max_iterations=3).run("q")
        self.assertLessEqual(len(trace), 3)

    def test_sql_and_calculator(self):
        t = build_tools()
        self.assertIn("23", str(t["sql_query"].execute(filename="soil_telemetry.csv",
                                                        sql="SELECT moisture FROM data WHERE moisture < 25")))
        self.assertEqual(t["calculator"].execute(expression="2+2*10"), 22)

    def test_calculate_dosage_uses_shared_pipeline(self):
        d = json.loads(build_tools()["calculate_dosage"].execute(crop="tomato", area_acres=1, stage="flowering"))
        self.assertEqual(d["decision"], "IRRIGATE_THEN_FERTILIZE")
        self.assertEqual(d["urgency"], "RED")
        self.assertEqual(d["moisture_thresholds"]["trigger"], 25.2)
        self.assertAlmostEqual(d["fertilizer_kg_for_area"]["dap"], 120.88, delta=0.02)
        self.assertIn("error", json.loads(build_tools()["calculate_dosage"].execute(crop="dragonfruit")))
        rice = json.loads(build_tools()["calculate_dosage"].execute(crop="paddy", stage="tillering"))
        self.assertEqual((rice["crop"], rice["water"]["method"]), ("rice", "flood"))

    def test_crop_suitability_tool(self):
        d = json.loads(build_tools()["check_crop_suitability"].execute(crop="rice"))
        self.assertTrue(d["available"])
        self.assertEqual(d["selected_crop"]["crop"], "rice")

    def test_final_answer_is_pipeline_draft_verbatim(self):
        llm = Scripted(['{"thought":"t","action":"calculate_dosage","args":{"crop":"tomato","stage":"flowering"}}',
                        '{"thought":"t","final_answer":"URGENCY: GREEN. ADVICE: made-up numbers"}'])
        answer, _ = AgentExecutor(llm, build_tools()).run("should I irrigate my tomato?")
        self.assertTrue(answer.startswith("URGENCY: RED\nADVICE: Soil is dry."))
        self.assertIn("வறண்டுள்ளது", answer)

    def test_cli_contract(self):
        out = subprocess.run([sys.executable, "main.py", "--json", "--dry-run", "hi"], capture_output=True, text=True)
        d = json.loads(out.stdout.strip().splitlines()[-1])
        self.assertTrue(d["answer"] and len(d["trace"]) >= 2)


if __name__ == "__main__":
    unittest.main()
