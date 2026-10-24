"""Agricultural web and knowledge search tool."""
from tools import Tool


class WebSearch(Tool):
    name = "web_search"
    description = "Search agricultural extension knowledge bases and university bulletins for crop practices."
    args_doc = '{"query": "tomato flowering water stress"}'

    def execute(self, query="tomato", **kw):
        q = str(query).lower()
        if "tomato" in q and ("flower" in q or "water" in q):
            return ("TNAU Agritech Guide: Tomato flowering requires 65% soil moisture and 100 kg/ha N for optimal fruit setting. "
                    "Avoid water stress during flowering to prevent blossom end rot and flower drop.")
        if "trichy" in q or "tamil nadu" in q:
            return ("TNAU Regional Research Station Tiruchirappalli: Sandy clay loam soils prevail. "
                    "Drip fertigation recommended for solanaceous crops. Postpone irrigation if rain > 60%.")
        return f"Agricultural Extension Bulletin: Recommendations for '{query}' - maintain optimal soil moisture and avoid heavy fertigation during rain."
