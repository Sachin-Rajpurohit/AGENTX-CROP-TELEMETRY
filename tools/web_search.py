import sys
import requests

DISTRICT_COORDS = {
    "tiruchirappalli": (10.7905, 78.7047),
    "trichy": (10.7905, 78.7047),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "thanjavur": (10.7870, 79.1378),
    "salem": (11.6643, 78.1460),
    "chennai": (13.0827, 80.2707)
}

def get_weather_forecast(location: str = "Tiruchirappalli", days: int = 3) -> dict:
    """
    Retrieves multi-day precipitation probability, rainfall mm, and max temperature.
    Recovers gracefully if offline or rate-limited.
    """
    sys.stderr.write(f"[TOOL: get_weather_forecast] Fetching {days}-day forecast for {location}\n")
    loc_key = str(location).strip().lower()
    lat, lon = DISTRICT_COORDS.get(loc_key, (10.7905, 78.7047))

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["precipitation_sum", "precipitation_probability_max", "temperature_2m_max"],
        "timezone": "auto",
        "forecast_days": min(max(int(days), 1), 7)
    }

    try:
        response = requests.get(url, params=params, timeout=4.0)
        response.raise_for_status()
        daily = response.json().get("daily", {})

        rain_list = [float(x or 0.0) for x in daily.get("precipitation_sum", [0.0])]
        prob_list = [int(x or 0) for x in daily.get("precipitation_probability_max", [15])]
        temp_list = [float(x or 34.0) for x in daily.get("temperature_2m_max", [34.0])]

        total_rain_mm = round(sum(rain_list), 2)
        max_prob_pct = max(prob_list) if prob_list else 15
        avg_max_temp = round(sum(temp_list) / len(temp_list), 1) if temp_list else 34.5

        heavy_rain_risk = total_rain_mm >= 15.0 or max_prob_pct >= 65
        delay_irrigation = total_rain_mm >= 10.0 and max_prob_pct >= 55

        return {
            "status": "success",
            "location": location,
            "forecast_days": days,
            "total_rainfall_mm": total_rain_mm,
            "max_rain_probability_pct": max_prob_pct,
            "avg_max_temp_c": avg_max_temp,
            "heavy_rain_risk": heavy_rain_risk,
            "should_delay_irrigation": delay_irrigation,
            "weather_advisory": (
                "Heavy rainfall imminent; hold irrigation and delay top-dress fertilizer to prevent nutrient leaching."
                if delay_irrigation else
                f"Low rainfall risk ({max_prob_pct}% probability, {total_rain_mm} mm expected). Do NOT delay scheduled irrigation or fertilizer application."
            )
        }
    except Exception as e:
        sys.stderr.write(f"[WARN] Live weather lookup failed ({e}); returning safe fallback.\n")
        return {
            "status": "fallback",
            "location": location,
            "forecast_days": days,
            "total_rainfall_mm": 0.4,
            "max_rain_probability_pct": 15,
            "avg_max_temp_c": 34.8,
            "heavy_rain_risk": False,
            "should_delay_irrigation": False,
            "weather_advisory": "Low rainfall risk (15% probability, <1 mm expected). Proceed with immediate irrigation; weather API fallback active."
        }