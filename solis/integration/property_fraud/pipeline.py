from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

from solis.integration.property_fraud.features import FeatureState, build_features
from solis.integration.property_fraud.models import DeedTransferEvent, ScoredTransfer
from solis.integration.property_fraud.scoring import score_features
from solis.integration.property_fraud.tokenization import tokenize_transfer


def _event_sort_key(event: DeedTransferEvent) -> tuple[str, str, str, str]:
    return (
        event.recording_date.isoformat(),
        event.county_fips,
        event.document_number,
        event.apn,
    )


class PropertyFraudPipeline:
    def __init__(self) -> None:
        self.state = FeatureState()

    def prime(self, events: Iterable[DeedTransferEvent]) -> None:
        ordered = sorted(list(events), key=_event_sort_key)
        for event in ordered:
            tokens = tokenize_transfer(event)
            self.state.property_history.setdefault(tokens.property_token_id, []).append(event)
            self.state.grantee_activity.setdefault(tokens.grantee_token_id, []).append(event.recording_date)

    def run(self, events: Iterable[DeedTransferEvent]) -> list[ScoredTransfer]:
        ordered = sorted(list(events), key=_event_sort_key)
        output: list[ScoredTransfer] = []

        for event in ordered:
            tokens = tokenize_transfer(event)
            features = build_features(event, tokens, self.state)
            risk = score_features(features)
            scored = ScoredTransfer(
                event=event,
                tokens=tokens,
                features=features,
                risk=risk,
            )
            output.append(scored)

            self.state.property_history.setdefault(tokens.property_token_id, []).append(event)
            self.state.grantee_activity.setdefault(tokens.grantee_token_id, []).append(event.recording_date)

        return output


def parse_events(records: Iterable[Mapping[str, object]]) -> list[DeedTransferEvent]:
    return [DeedTransferEvent.from_mapping(record) for record in records]


def load_events(path: Path) -> list[DeedTransferEvent]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        return parse_events(records)

    loaded = json.loads(text)
    if isinstance(loaded, list):
        return parse_events(loaded)
    if isinstance(loaded, dict) and isinstance(loaded.get("events"), list):
        return parse_events(loaded["events"])
    raise ValueError("input must be JSON array, {\"events\": [...]}, or JSONL")


def write_scored_transfers(path: Path, rows: Iterable[ScoredTransfer]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")


def summarize_scored_transfers(rows: Iterable[ScoredTransfer]) -> dict[str, object]:
    scored_rows = list(rows)
    by_tier: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    max_score = 0
    high_risk_count = 0

    for row in scored_rows:
        by_tier[row.risk.risk_tier] = by_tier.get(row.risk.risk_tier, 0) + 1
        max_score = max(max_score, row.risk.score)
        if row.risk.risk_tier in {"high", "critical"}:
            high_risk_count += 1

    return {
        "total_transfers": len(scored_rows),
        "tier_counts": by_tier,
        "high_or_critical_count": high_risk_count,
        "max_score": max_score,
    }
