import json

import pytest
from fastapi.testclient import TestClient

import farm_store
import server
from core.schema import WeatherRisk
from tools import build_tools
from tools.farm_context import FARM

SALEM = {"name": "Salem, Tamil Nadu, India", "lat": 11.66, "lon": 78.15}
MAIZE = {"name": "North field", "crop": "maize", "area_acres": 2, "irrigation": "drip", "soil": "red_soil",
         "location": SALEM}
CSV = "timestamp,moisture,N,P,K,pH\n" + "".join(f"2026-10-0{d} 08:00,{30 - d},40,20,30,6.4\n" for d in range(1, 8))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(farm_store, "FARM_DIR", tmp_path / "farms")
    seen = {}

    def weather(lat, lon):
        seen["latlon"] = (lat, lon)
        return WeatherRisk(0.0, 10.0, 33.0, "live")

    monkeypatch.setattr("agent.advisor.get_weather_risk", weather)
    c = TestClient(server.app)
    c.weather_seen = seen
    return c


def test_first_run_creates_demo_farm_with_data(client):
    farms = client.get("/api/farms").json()
    assert len(farms) == 1 and farms[0]["has_telemetry"] is True
    assert len(client.get(f"/api/farms/{farms[0]['id']}/telemetry").json()["rows"]) == 8


def test_create_update_delete(client):
    farm = client.post("/api/farms", json=MAIZE).json()
    assert farm["crop"] == "maize" and farm["has_telemetry"] is False
    assert len(client.get("/api/farms").json()) == 2
    updated = client.put(f"/api/farms/{farm['id']}", json={**MAIZE, "name": "South field", "area_acres": 3}).json()
    assert (updated["name"], updated["area_acres"]) == ("South field", 3)
    assert client.delete(f"/api/farms/{farm['id']}").status_code == 204
    assert client.get(f"/api/farms/{farm['id']}").status_code == 404


@pytest.mark.parametrize("patch, status", [
    ({"crop": "banana"}, 400),
    ({"crop": "rice", "stage": "fruiting"}, 400),
    ({"soil": "peat"}, 400),
    ({"area_acres": 0}, 422),
    ({"location": {**SALEM, "lat": 120}}, 422),
    ({"name": ""}, 422),
])
def test_farm_validation(client, patch, status):
    assert client.post("/api/farms", json={**MAIZE, **patch}).status_code == status


def test_rice_farm_is_always_flooded(client):
    farm = client.post("/api/farms", json={**MAIZE, "crop": "paddy", "irrigation": "drip"}).json()
    assert (farm["crop"], farm["irrigation"]) == ("rice", "flood")


def test_upload_and_advise_with_farm_settings(client):
    farm = client.post("/api/farms", json=MAIZE).json()
    assert client.post(f"/api/farms/{farm['id']}/advice").status_code == 400  # no sensor data yet
    bad = client.post(f"/api/farms/{farm['id']}/telemetry", files={"csv": ("x.csv", "a,b\n1,2\n", "text/csv")})
    assert bad.status_code == 400
    ok = client.post(f"/api/farms/{farm['id']}/telemetry", files={"csv": ("t.csv", CSV, "text/csv")}).json()
    assert ok["rows"] == 7 and ok["farm"]["has_telemetry"] is True

    advice = client.post(f"/api/farms/{farm['id']}/advice").json()
    assert advice["crop"] == "maize" and advice["readings"]["moisture"] == 23
    assert advice["moisture_thresholds"]["soil"] == "red_soil"
    assert advice["doses"]["fertilizer"]["area_acres"] == 2
    assert client.weather_seen["latlon"] == (11.66, 78.15)


def test_chat_runs_with_the_farm_selected(client, monkeypatch):
    farm = client.post("/api/farms", json=MAIZE).json()
    assert client.post("/api/chat", json={"message": "hi", "farm_id": farm["id"]}).status_code == 400
    client.post(f"/api/farms/{farm['id']}/telemetry", files={"csv": ("t.csv", CSV, "text/csv")})
    captured = {}

    def fake_agent(message, role=None):
        captured.update(farm=FARM.get(), role=role)
        return "URGENCY: GREEN\nADVICE: ok", []

    monkeypatch.setattr(server, "run_agent", fake_agent)
    assert client.post("/api/chat", json={"message": "hi", "farm_id": farm["id"]}).status_code == 200
    assert captured["farm"]["crop"] == "maize" and captured["farm"]["lat"] == 11.66
    assert "North field" in captured["role"]
    assert FARM.get() is None  # context is reset after the request
    assert client.post("/api/chat", json={"message": "hi", "farm_id": "nope"}).status_code == 404


def test_agent_tools_use_the_selected_farm(tmp_path, monkeypatch):
    monkeypatch.setattr("agent.advisor.get_weather_risk", lambda lat, lon: WeatherRisk(0, 10, 33, "live"))
    csv = tmp_path / "soil_telemetry.csv"
    csv.write_text(CSV)
    token = FARM.set({"name": "North field", "crop": "maize", "stage": None, "area_acres": 3, "irrigation": "drip",
                      "soil": "red_soil", "lat": 11.66, "lon": 78.15, "telemetry_path": str(csv)})
    try:
        tools = build_tools()
        d = json.loads(tools["calculate_dosage"].execute())
        assert (d["crop"], d["area_acres"], d["moisture_now_pct"]) == ("maize", 3, 23)
        assert d["moisture_thresholds"]["soil"] == "red_soil"
        assert json.loads(tools["get_soil_readings"].execute())["latest"]["moisture"] == 23
        assert json.loads(tools["analyze_trend"].execute(column="moisture"))["thresholds"]["crop"] == "maize"
        rice = json.loads(tools["calculate_dosage"].execute(crop="rice"))
        assert rice["stage"] == "tillering"  # the maize farm's stage does not leak into another crop
    finally:
        FARM.reset(token)


def test_geocode(client, monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [{"name": "Kumbakonam", "admin2": "Thanjavur", "admin1": "Tamil Nadu",
                                 "country": "India", "latitude": 10.96, "longitude": 79.39}]}

    monkeypatch.setattr(server.requests, "get", lambda *a, **k: Resp())
    assert client.get("/api/geocode", params={"q": "Kumbakonam"}).json() == [
        {"name": "Kumbakonam, Thanjavur, Tamil Nadu, India", "lat": 10.96, "lon": 79.39}]
    assert client.get("/api/geocode", params={"q": "K"}).status_code == 422


def test_dose_calculator_can_use_a_farms_data(client):
    farm = client.post("/api/farms", json=MAIZE).json()
    client.post(f"/api/farms/{farm['id']}/telemetry", files={"csv": ("t.csv", CSV, "text/csv")})
    r = client.post("/api/advice", data={"farm_id": farm["id"], "crop": "cotton", "area_acres": "5"}).json()
    assert (r["input_source"], r["crop"], r["readings"]["moisture"]) == ("farm", "cotton", 23)
    assert client.weather_seen["latlon"] == (11.66, 78.15)
