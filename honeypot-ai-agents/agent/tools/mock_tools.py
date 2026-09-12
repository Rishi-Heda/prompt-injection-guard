import ast
import operator
from pathlib import Path
from typing import Any


MOCK_FILES = {
    "clean-doc": "The project ships a weekly report every Friday. The owner reviews metrics and open risks before release.",
}
MOCK_DATABASE = {
    "project_status": {"status": "green", "open_tasks": 2},
}
MOCK_WRITTEN_FILES: dict[str, str] = {}

TOOL_INDEX_MAP = {
    "READ_FILE": 1,
    "SUMMARIZE": 2,
    "QUERY_DB": 3,
    "SEND_EMAIL": 4,
    "SEARCH_WEB": 5,
    "CALCULATE_MATH": 6,
    "WRITE_FILE": 7,
}

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "READ_FILE", "description": "Read a document from the local mock file store.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "SUMMARIZE", "description": "Create a short summary of supplied text.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "QUERY_DB", "description": "Query the local mock database by key.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "SEND_EMAIL", "description": "Simulate sending an email. No email is sent.", "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {"name": "SEARCH_WEB", "description": "Search the local mock web index.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "CALCULATE_MATH", "description": "Evaluate a basic arithmetic expression.", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "WRITE_FILE", "description": "Simulate writing a file to an in-memory store.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
]


def _calculate(expression: str) -> int | float:
    operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in operators:
            return operators[type(node.op)](evaluate(node.left), evaluate(node.right))
        raise ValueError("Only basic arithmetic is supported.")

    return evaluate(ast.parse(expression, mode="eval"))


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    if name == "READ_FILE":
        path = arguments["path"]
        if path in MOCK_FILES:
            return MOCK_FILES[path]
        fixture = (Path(__file__).parents[2] / path).resolve()
        pages_root = (Path(__file__).parents[2] / "demo_pages").resolve()
        if fixture.is_relative_to(pages_root) and fixture.is_file():
            return fixture.read_text(encoding="utf-8")
        return "File not found."
    if name == "SUMMARIZE":
        text = arguments["text"].strip()
        return text if len(text) <= 240 else f"{text[:237]}..."
    if name == "QUERY_DB":
        return repr(MOCK_DATABASE.get(arguments["query"], {"result": "No matching record."}))
    if name == "SEND_EMAIL":
        return f"SIMULATED ONLY: would send email to {arguments['to']!r}: {arguments['subject']!r}"
    if name == "SEARCH_WEB":
        return "No mock web result found."
    if name == "CALCULATE_MATH":
        try:
            return str(_calculate(arguments.get("expression", "0")))
        except Exception as e:
            return f"Math execution error: {e}"
    if name == "WRITE_FILE":
        MOCK_WRITTEN_FILES[arguments["path"]] = arguments["content"]
        return f"SIMULATED ONLY: stored {arguments['path']!r} in memory."
    raise ValueError(f"Unknown tool: {name}")
