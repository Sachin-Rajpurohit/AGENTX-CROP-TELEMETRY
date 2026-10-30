from tools.data_query import analyze_soil_telemetry, load_crop_requirements
from tools.web_search import get_weather_forecast
from tools.crop_tools import calculate_fertilizer_water_dosage
from tools.calculator import evaluate_expression

TOOL_REGISTRY = {
    "analyze_soil_telemetry": analyze_soil_telemetry,
    "get_weather_forecast": get_weather_forecast,
    "calculate_fertilizer_water_dosage": calculate_fertilizer_water_dosage,
    "evaluate_expression": evaluate_expression,
}

TOOL_SCHEMAS = [
    {
        "name": "analyze_soil_telemetry",
        "description": "Analyze 7 days of soil moisture, NPK (kg/ha), pH, and root-zone temperature trends from soil_telemetry.csv.",
        "parameters": {
            "type": "object",
            "properties": {
                "plot_id": {"type": "string", "description": "Field/Plot identifier (e.g., 'Trichy Plot #4', 'plot_3')"},
                "days": {"type": "integer", "description": "Number of days of trend history to analyze (default 7)"}
            },
            "required": ["plot_id"]
        }
    },
    {
        "name": "get_weather_forecast",
        "description": "Check rainfall probability (%) and expected precipitation (mm) for the field location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "District or city name (e.g., 'Tiruchirappalli')"},
                "days": {"type": "integer", "description": "Forecast horizon in days (default 3)"}
            },
            "required": ["location"]
        }
    },
    {
        "name": "calculate_fertilizer_water_dosage",
        "description": "Compute exact commercial fertilizer weights (Urea, SSP/DAP, MOP in kg/acre) and irrigation water volume (Liters/acre).",
        "parameters": {
            "type": "object",
            "properties": {
                "crop": {"type": "string", "description": "Crop name (e.g., 'tomato', 'paddy', 'rice', 'groundnut')"},
                "current_moisture_pct": {"type": "number"},
                "target_moisture_pct": {"type": "number"},
                "current_npk_kg_ha": {"type": "array", "items": {"type": "number"}},
                "target_npk_kg_ha": {"type": "array", "items": {"type": "number"}},
                "field_area_acres": {"type": "number"},
                "heavy_rain_expected": {"type": "boolean"}
            },
            "required": ["crop", "current_moisture_pct", "target_moisture_pct", "current_npk_kg_ha", "target_npk_kg_ha"]
        }
    }
]