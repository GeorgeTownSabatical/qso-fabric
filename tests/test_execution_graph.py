from execution_graph.graph_builder import build
from execution_graph.dag_executor import execute
from execution_graph.task_scheduler import schedule


def test_execution_graph_flow():
    dag = build("@physics >expand_theory +sheaf,avalanche ->simulation")
    sched = schedule(dag)
    result = execute(dag)
    assert sched.ordered_steps[0] == "LoadContext"
    assert result.status == "ok"
