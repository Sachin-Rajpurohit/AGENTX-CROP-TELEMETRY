"""AgriAgent package."""
# Advisor tools (append-only)

from agent.prompt_builder import TOOL_DESCRIPTIONS

# Now your existing code that uses TOOL_DESCRIPTIONS will work:
# {"name": "tool_quality", "description": TOOL_DESCRIPTIONS["tool_quality"]},

TOOL_DESCRIPTIONS = [
    {"name": "tool_quality", "description": TOOL_DESCRIPTIONS["tool_quality"]},
    {"name": "tool_trends", "description": TOOL_DESCRIPTIONS["tool_trends"]},
    {"name": "tool_weather", "description": TOOL_DESCRIPTIONS["tool_weather"]},
    {"name": "tool_dosage", "description": TOOL_DESCRIPTIONS["tool_dosage"]},
    {"name": "tool_irrigation", "description": TOOL_DESCRIPTIONS["tool_irrigation"]},
    {"name": "tool_rules", "description": TOOL_DESCRIPTIONS["tool_rules"]},
    {"name": "tool_confidence", "description": TOOL_DESCRIPTIONS["tool_confidence"]},
]
