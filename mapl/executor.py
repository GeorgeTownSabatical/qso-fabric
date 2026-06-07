from __future__ import annotations

from .parser import MAPLAst, parse


def run(command: str) -> dict[str, object]:
    ast = parse(command)
    return {
        "context": ast.context,
        "task": ast.task,
        "modules": list(ast.modules),
        "output": list(ast.output),
    }
