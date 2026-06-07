from __future__ import annotations

from solis import (
    AlpacaCredentials,
    AlpacaExecutionAdapter,
    RBACAuthorizer,
    RBACPolicy,
    SheafProjection,
    build_sheaf_projection,
    compile_strategy_ast,
    compile_strategy_dsl,
    parse_strategy_dsl,
)
from solis.physics.fixed_math import Fixed64


def test_solis_top_level_boundary_exports_are_import_clean() -> None:
    assert AlpacaExecutionAdapter is not None
    assert AlpacaCredentials is not None
    assert RBACPolicy is not None
    assert RBACAuthorizer is not None
    assert SheafProjection is not None
    assert parse_strategy_dsl is not None
    assert compile_strategy_dsl is not None
    assert compile_strategy_ast is not None


def test_strategy_dsl_boundary_compiles_to_execution_graph() -> None:
    dsl = """
agent alpha
version v1
assets:
BTC
ETH
allocation:
BTC 60%
ETH 40%
rebalance interval 1d
risk:
max_drawdown 3%
collapse_threshold 0.7
no_margin true
""".strip()
    ast = parse_strategy_dsl(dsl)
    graph_from_ast, graph_hash_from_ast = compile_strategy_ast(ast)
    graph_from_text, graph_hash_from_text = compile_strategy_dsl(dsl)

    assert ast.name == "alpha"
    assert graph_hash_from_ast == graph_hash_from_text
    assert graph_from_ast.nodes == graph_from_text.nodes
    assert graph_from_ast.edges == graph_from_text.edges


def test_sheaf_boundary_builds_deterministic_projection() -> None:
    projection = build_sheaf_projection(
        layer_fields={
            "low_vol": {"signal": Fixed64.from_str("0.2")},
            "high_vol": {"signal": Fixed64.from_str("0.9")},
        },
        constellation_state={
            "qso://solis.star.alpha": {
                "entropy_index": Fixed64.from_str("0.2"),
                "previous_entropy_index": Fixed64.from_str("0.1"),
                "magnetic_field": Fixed64.from_str("0.95"),
                "fusion_rate": Fixed64.from_str("0.15"),
            }
        },
        steps=2,
    )

    assert isinstance(projection, SheafProjection)
    assert len(projection.state.layers) == 2
    assert len(projection.propagated.layers) == 2
    assert projection.stability.systemic_risk_index >= Fixed64.zero()
