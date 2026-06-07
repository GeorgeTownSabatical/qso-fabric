from __future__ import annotations

from services.oracle import SettlementOracle
from services.qcc import ProviderScoringEngine, QCCTokenModel, QCUMeter


def test_qcu_and_provider_scoring_and_settlement() -> None:
    meter = QCUMeter()
    estimate = meter.estimate({"qubit_count": 32, "depth": 100, "shots": 2048})
    assert estimate["qcu"] > 0

    scoring = ProviderScoringEngine().score({"uptime": 0.99, "error_rate": 0.01, "latency_ms": 100})
    assert scoring["tier"] in {"gold", "silver", "bronze"}

    payload = QCCTokenModel().mint_payload(wallet="0xabc", qcu=estimate["qcu"], nonce="n1")
    assert payload["token_type"] == "QCC"

    settlement = SettlementOracle().settle(
        settlement_id="s1",
        qcu_consumed=estimate["qcu"],
        unit_price=0.5,
        provider_id="provider-1",
    )
    assert settlement["gross"] >= 0
    assert len(settlement["record_hash"]) == 64
