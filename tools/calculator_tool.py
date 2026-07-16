#!/usr/bin/env python3
"""Calculator Tool - Basic math operations."""

import operator
import json
from tools.registry import registry


def calculator(expression: str) -> str:
    """
    Calculates basic math operations.
    Supported operators: +, -, *, /
    Input format: 'number operator number' (e.g., '2 + 2' or '15 * 3')
    """
    try:
        parts = expression.strip().split()
        
        if len(parts) != 3:
            return json.dumps({
                "error": "Invalid format. Please use 'number operator number' (e.g., '5 * 4')."
            })
        
        num1_str, op, num2_str = parts
        num1 = float(num1_str)
        num2 = float(num2_str)
        
        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv
        }
        
        if op not in ops:
            return json.dumps({
                "error": f"Unsupported operator '{op}'. Use +, -, *, or /."
            })
        
        if op == '/' and num2 == 0:
            return json.dumps({"error": "Division by zero is undefined."})
        
        result = ops[op](num1, num2)
        
        if result.is_integer():
            result = int(result)
        
        return json.dumps({"result": result})
        
    except ValueError:
        return json.dumps({"error": "Invalid numbers provided. Ensure inputs are integers or floats."})
    except Exception as e:
        return json.dumps({"error": str(e)})


CALCULATOR_SCHEMA = {
    "name": "calculator",
    "description": "Calculate basic math operations. Supports +, -, *, / with format 'number operator number' (e.g., '2 + 2').",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression in format 'number operator number' (e.g., '5 * 4')",
            }
        },
        "required": ["expression"],
    },
}

registry.register(
    name="calculator",
    toolset="system",
    schema=CALCULATOR_SCHEMA,
    handler=lambda args, **kw: calculator(expression=args.get("expression", "")),
    check_fn=None,
    emoji="🧮",
)
