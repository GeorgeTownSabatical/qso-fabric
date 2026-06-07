from __future__ import annotations

from solis.agent.dsl.compiler import compile_dsl
from solis.agent.marketplace.revenue_model import split_revenue
from solis.agent.marketplace.template_registry import TemplateRecord, TemplateRegistry
from solis.agent.marketplace.versioning import bump_version
from solis.agent.runtime.capital_router import route_capital
from solis.agent.sandbox.replay_engine import replay_events
from solis.physics.fixed_math import Fixed64


DSL_TEXT = """
agent MyStrategy {
version 1.0
assets:
stable_usdc
eth
allocation:
stable_usdc 50%
eth 50%
rebalance interval 12h
risk:
max_drawdown 15%
collapse_threshold 35%
no_margin true
}
"""


def test_dsl_compile_deterministic() -> None:
    g1, h1 = compile_dsl(DSL_TEXT)
    g2, h2 = compile_dsl(DSL_TEXT)
    assert g1 == g2
    assert h1 == h2


def test_runtime_capital_and_replay() -> None:
    allocations = {
        "stable": Fixed64.from_str("0.6"),
        "growth": Fixed64.from_str("0.4"),
    }
    routed = route_capital(Fixed64.from_int(100), allocations)
    assert routed["stable"] + routed["growth"] == Fixed64.from_int(100)

    def reducer(state: dict, event: dict) -> dict:
        out = dict(state)
        out["v"] = out.get("v", 0) + int(event["delta"])
        return out

    state, h = replay_events({"v": 0}, [{"delta": 2}, {"delta": 3}], reducer)
    assert state["v"] == 5
    assert isinstance(h, str) and len(h) == 64


def test_marketplace_versioning_and_revenue() -> None:
    assert bump_version("1.0.9") == "1.0.10"

    split = split_revenue(
        total=Fixed64.from_int(100),
        ratio_creator=Fixed64.from_str("0.5"),
        ratio_operator=Fixed64.from_str("0.3"),
        ratio_protocol=Fixed64.from_str("0.2"),
    )
    assert split.creator + split.operator + split.protocol == Fixed64.from_int(100)

    registry = TemplateRegistry()
    registry.register(TemplateRecord(template_id="t", version="1.0.0", graph_hash="abc", owner_uri="qso://identity.iris.x"))
    assert registry.get("t", "1.0.0").graph_hash == "abc"
