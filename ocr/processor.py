import ast
import operator
import re
from dataclasses import dataclass, field

from ocr.summarizer import summarize

BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
MAX_POWER = 64
MAX_LENGTH = 120
ALLOWED = re.compile(r"[\d\s+\-*/().]+")
HAS_OPERATOR = re.compile(r"\d\s*(?:\*\*|//|[+\-*/])\s*[\d(]")
MULTIPLY = re.compile(r"(?<=[\d)])\s*[xXхХ]\s*(?=[\d(])")
FAILURES = (ValueError, ZeroDivisionError, OverflowError, SyntaxError, RecursionError)


@dataclass
class ProcessedResult:
    text: str
    calculations: list = field(default_factory=list)
    summary: str = ""


def _normalize(line):
    expr = line.strip().rstrip("=").strip()
    expr = expr.replace("×", "*").replace("÷", "/")
    expr = expr.replace("−", "-").replace("–", "-")
    expr = MULTIPLY.sub("*", expr)
    return expr.replace("^", "**").replace(",", ".")


def _evaluate(node):
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("constant")
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_POWER:
            raise ValueError("power")
        return BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](_evaluate(node.operand))
    raise ValueError("unsupported")


def _format(value):
    if isinstance(value, float):
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.10g}"
    return str(value)


class TextProcessor:
    def process(self, text: str) -> ProcessedResult:
        found = []
        for line in text.splitlines():
            item = self._calculate(line)
            if item:
                found.append(item)
        return ProcessedResult(text=text, calculations=found, summary=summarize(text))

    @staticmethod
    def _calculate(line):
        raw = line.strip()
        if not raw or len(raw) > MAX_LENGTH:
            return None
        expr = _normalize(raw)
        if not ALLOWED.fullmatch(expr) or not HAS_OPERATOR.search(expr):
            return None
        try:
            value = _evaluate(ast.parse(expr, mode="eval"))
        except FAILURES:
            return None
        return raw.rstrip("= ").strip(), _format(value)
