from __future__ import annotations

from mapl.executor import run
from router.context_router import route
from execution_graph.graph_builder import build
from execution_graph.dag_executor import execute
from outputs.report_builder import build as build_report


def main(command: str) -> dict[str, object]:
    parsed = run(command)
    plan = route(parsed["context"], parsed["modules"])
    dag = build(command)
    result = execute(dag)
    report = build_report({"plan": str(plan), "result": str(result)})
    return {
        "parsed": parsed,
        "plan": plan,
        "dag": dag,
        "result": result,
        "report": report,
    }
