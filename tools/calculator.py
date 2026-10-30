import ast
import operator

ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def evaluate_expression(expression: str) -> dict:
    """Safely evaluates an arithmetic string without using eval()."""
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            return ALLOWED_OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return ALLOWED_OPERATORS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression node: {node}")

    try:
        tree = ast.parse(expression, mode="eval")
        val = round(float(_eval(tree.body)), 3)
        return {"status": "success", "expression": expression, "result": val}
    except Exception as e:
        return {"status": "error", "expression": expression, "error": str(e)}