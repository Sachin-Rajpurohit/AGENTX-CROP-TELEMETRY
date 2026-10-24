"""Safe mathematical calculator tool."""
import re
from tools import Tool


class Calculator(Tool):
    name = "calculator"
    description = "Safely evaluate simple arithmetic expressions like '2 + 2 * 10' or '(100 - 40) / 2.471'."
    args_doc = '{"expression": "2 + 2 * 10"}'

    def execute(self, expression="0", **kw):
        sanitized = re.sub(r"[^0-9+\-*/().\s]", "", str(expression))
        if not sanitized.strip():
            return "ERROR: invalid expression"
        try:
            # Evaluate safely with empty builtins
            return eval(sanitized, {"__builtins__": None}, {})
        except Exception as e:
            return f"ERROR: calculator failed: {e}"
