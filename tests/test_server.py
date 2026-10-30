import pytest
from fastapi.testclient import TestClient

import server
from core.schema import WeatherRisk


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr("agent.advisor.get_weather_risk",
                        lambda lat, lon: WeatherRisk(0.0, 10.0, 33.0, "live"))
    return TestClient(server.app)


def test_sample(client):
    r = client.get("/api/sample")
    assert r.status_code == 200
    assert r.json()["csv"].startswith("timestamp,moisture")


def test_advice_defaults_to_sample(client):
    r = client.post("/api/advice", data={})
    assert r.status_code == 200
    body = r.json()
    assert body["input_source"] == "sample"
    assert body["decision"] == "IRRIGATE_THEN_FERTILIZE"


def test_advice_from_uploaded_csv(client):
    csv = "timestamp,moisture,N,P,K\n" + "".join(
        f"2026-10-0{d} 08:00,{60 - d},90,45,55\n" for d in range(1, 8))
    r = client.post("/api/advice", data={"days_after_transplanting": "30"},
                    files={"csv": ("t.csv", csv, "text/csv")})
    assert r.status_code == 200
    assert r.json()["input_source"] == "upload"
    assert r.json()["readings"]["moisture"] == 53


def test_advice_from_manual_readings(client):
    r = client.post("/api/advice", data={"moisture": "30", "n": "40", "p": "20", "k": "30", "area_acres": "2"})
    assert r.status_code == 200
    body = r.json()
    assert body["input_source"] == "manual"
    assert body["doses"]["fertilizer"]["area_acres"] == 2


@pytest.mark.parametrize("data, files", [
    ({"irrigation": "sprinkler"}, None),
    ({"area_acres": "-1"}, None),
    ({"soil": "peat"}, None),
    ({"crop": "banana"}, None),
    ({}, {"csv": ("t.csv", "a,b\n1,2\n", "text/csv")}),  # no moisture column
    ({}, {"csv": ("t.csv", "", "text/csv")}),
])
def test_advice_rejects_bad_input(client, data, files):
    assert client.post("/api/advice", data=data, files=files).status_code == 400


def test_advice_for_another_crop(client):
    r = client.post("/api/advice", data={"crop": "rice", "days_after_transplanting": "30"})
    assert r.status_code == 200
    assert r.json()["crop"] == "rice" and r.json()["stage"] == "tillering"


def test_crops(client):
    crops = client.get("/api/crops").json()
    assert set(crops) == {"tomato", "maize", "cotton", "rice"}
    assert crops["rice"]["flooded"] is True and crops["maize"]["stages"] == []


def test_crop_fit(client):
    r = client.get("/api/crop-fit", params={"N": 90, "P": 42, "K": 43, "temperature": 20.9, "humidity": 82, "ph": 6.5})
    assert r.status_code == 200 and r.json()["best_matches"][0]["crop"] == "rice"
    assert client.get("/api/crop-fit", params={"N": 90}).status_code == 400


def test_voice_validates_language(client):
    assert client.get("/api/voice", params={"text": "hi", "lang": "fr"}).status_code == 422
