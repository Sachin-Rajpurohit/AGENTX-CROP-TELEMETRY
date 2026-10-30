import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agent.core import AgriAgent

def test_tomato_dosage_accuracy():
    """Verify tomato stress evaluation: exact commercial Urea, MOP, and water."""
    agent = AgriAgent()
    query = (
        "Analyze Trichy Plot #4 (Tomato). Soil Moisture is 22% (Target: 65%), "
        "NPK is 40-20-30 kg/ha (Target: 80-20-50 kg/ha), pH is 6.2, root-zone temp is 32.4°C. "
        "Check the 3-day weather forecast for Tiruchirappalli and calculate water and fertilizer replenishment for 1 acre."
    )
    res = agent.run(query)
    assert "35.2" in res["answer"], f"Must recommend 35.2 kg commercial Urea, got: {res['answer']}"
    assert "13.5" in res["answer"], f"Must recommend 13.5 kg commercial MOP, got: {res['answer']}"
    assert "28,300" in res["answer"], f"Must recommend 28,300 L water, got: {res['answer']}"
    assert "X kg" not in res["answer"], "Must never output placeholder X kg"
    assert len(res["trace"]) >= 3, "Must execute at least 3 multi-step tool calls"
    print("  [PASS] test_tomato_dosage_accuracy")

def test_paddy_full_loop():
    """Verify paddy full cycle: tillering/panicle split advice and Urea calculation."""
    agent = AgriAgent()
    res = agent.run("Evaluate plot_3 planted with paddy. Check 7-day trends, weather, and fertilizer dosage.")
    assert "52.8" in res["answer"], f"Must recommend 52.8 kg commercial Urea for paddy, got: {res['answer']}"
    assert "panicle initiation" in res["answer"].lower(), "Must specify tillering/panicle initiation split"
    assert len(res["trace"]) >= 3, "Must execute at least 3 multi-step tool calls"
    print("  [PASS] test_paddy_full_loop")

def test_bilingual_tamil_output():
    """Verify query requesting Tamil generates regional language section alongside metrics."""
    agent = AgriAgent()
    res = agent.run("Evaluate Trichy Plot #4 (Tomato) in Tamil. Check weather and compute fertilizer.")
    ans = res["answer"]
    assert "தமிழ்" in ans or "ஆலோசனை" in ans, "Must contain Tamil advice block"
    assert "யூரியா" in ans or "35.2" in ans, "Tamil block must mention Urea or exact dosage"
    assert len(res["trace"]) >= 3, "Must execute multi-step tools"
    print("  [PASS] test_bilingual_tamil_output")

def test_heavy_rain_interlock_advisory():
    """Verify heavy rain forecast interlock withholds irrigation and nitrogen."""
    agent = AgriAgent()
    res = agent.run("Evaluate Trichy Plot #4 (Tomato) with heavy rain expected (> 30 mm).")
    ans_lower = res["answer"].lower()
    assert "hold irrigation" in ans_lower or "do not irrigate" in ans_lower, "Must hold irrigation on heavy rain"
    assert "leaching" in ans_lower or "rain" in ans_lower, "Must explain leaching risk"
    print("  [PASS] test_heavy_rain_interlock_advisory")

def test_cli_json_contract():
    """Verify automated evaluation CLI interface generates valid contract JSON."""
    proc = subprocess.run(
        [sys.executable, "main.py", "--json", "Evaluate Trichy Plot #4 (Tomato)"],
        capture_output=True,
        text=True,
        check=True
    )
    parsed = json.loads(proc.stdout.strip())
    assert "answer" in parsed and "trace" in parsed, "CLI output must conform to JSON contract {answer, trace}"
    assert isinstance(parsed["trace"], list) and len(parsed["trace"]) >= 3, "Trace must have >= 3 steps"
    for step in parsed["trace"]:
        assert "thought" in step and "tool" in step and "args" in step and "observation" in step, "Trace step missing required keys"
    print("  [PASS] test_cli_json_contract")

def run_all():
    print("Running Suite: tests/test_agent.py...")
    test_tomato_dosage_accuracy()
    test_paddy_full_loop()
    test_bilingual_tamil_output()
    test_heavy_rain_interlock_advisory()
    test_cli_json_contract()
    print("All AgentX Jury & Autograder tests passed successfully!\n")

if __name__ == "__main__":
    run_all()
