from router.context_router import route


def test_route_plan():
    plan = route("physics", ["sheaf", "avalanche"])
    assert "SYMBOLIC_PHYSICS" in plan.contexts
    assert plan.modules == ("sheaf", "avalanche")
    assert "LoadContext" in plan.execution_graph
