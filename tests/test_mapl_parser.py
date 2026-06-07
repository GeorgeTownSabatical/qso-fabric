from mapl.parser import parse
from mapl.executor import run


def test_parse_example():
    ast = parse("@physics >expand_theory +sheaf,avalanche ->equations,simulation")
    assert ast.context == "physics"
    assert ast.task == "expand_theory"
    assert ast.modules == ("sheaf", "avalanche")
    assert ast.output == ("equations", "simulation")


def test_executor_output():
    out = run("@physics >expand_theory +sheaf,avalanche ->equations,simulation")
    assert out["context"] == "physics"
    assert out["task"] == "expand_theory"
    assert out["modules"] == ["sheaf", "avalanche"]
    assert out["output"] == ["equations", "simulation"]
