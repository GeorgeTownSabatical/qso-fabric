from context_engine.context_loader import load_context
from context_engine.context_registry import ContextObject


def test_single_cluster_load():
    ctx = load_context("QSO")
    assert isinstance(ctx, ContextObject)
    assert ctx.id == "QSO"


def test_multi_cluster_merge():
    out = load_context(["QSO", "SOLIS"])
    assert "merged" in out and "clusters" in out
    merged = out["merged"]
    assert merged.id == "MERGED"
    assert out["clusters"]["QSO"].id == "QSO"
    assert out["clusters"]["SOLIS"].id == "SOLIS"
