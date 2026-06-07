from __future__ import annotations

import json
from pathlib import Path

from solis.integration.property_fraud import DeedTransferEvent, PropertyFraudPipeline, tokenize_transfer
from tools import solis_property_fraud


def _event(**overrides: object) -> DeedTransferEvent:
    base: dict[str, object] = {
        "state_fips": "06",
        "county_fips": "059",
        "apn": "123-456-10",
        "situs_address": "100 Main St, Santa Ana, CA",
        "recording_date": "2024-01-03",
        "instrument_type": "Grant Deed",
        "document_number": "2024-0000101",
        "grantor_name": "Alpha Holdings LLC",
        "grantee_name": "Sunset Development LLC",
        "consideration_amount": 800000.0,
        "market_value_estimate": 820000.0,
        "grantor_address": "500 Market St, Santa Ana, CA",
        "grantee_address": "1000 Harbor Blvd, Costa Mesa, CA",
        "grantor_distress_flags": [],
    }
    base.update(overrides)
    return DeedTransferEvent.from_mapping(base)


def test_tokenization_is_deterministic_under_text_variation() -> None:
    e1 = _event(apn="123-456-10", situs_address="100 Main St, Santa Ana, CA")
    e2 = _event(apn="123 456 10", situs_address="100 MAIN ST   SANTA ANA CA")
    t1 = tokenize_transfer(e1)
    t2 = tokenize_transfer(e2)
    assert t1.property_token_id == t2.property_token_id


def test_pipeline_marks_high_risk_rapid_flip_related_party_and_undervalue() -> None:
    first = _event(
        recording_date="2024-01-03",
        instrument_type="Grant Deed",
        document_number="2024-0000101",
        grantor_name="Alpha Holdings LLC",
        grantee_name="Sunset Development LLC",
        consideration_amount=800000.0,
        market_value_estimate=820000.0,
    )
    second = _event(
        recording_date="2024-02-01",
        instrument_type="Quitclaim Deed",
        document_number="2024-0000441",
        grantor_name="Sunset Development LLC",
        grantee_name="Harbor Equity Trust",
        consideration_amount=320000.0,
        market_value_estimate=850000.0,
        grantor_address="1000 Harbor Blvd, Costa Mesa, CA",
        grantee_address="1000 Harbor Blvd, Costa Mesa, CA",
        grantor_distress_flags=["lis_pendens"],
    )

    scored = PropertyFraudPipeline().run([first, second])
    suspicious = scored[-1]

    assert suspicious.risk.score >= 60
    assert suspicious.risk.risk_tier in {"high", "critical"}
    assert "rapid_flip_180d" in suspicious.risk.reason_codes
    assert "related_party_overlap" in suspicious.risk.reason_codes
    assert "severe_undervalue_transfer" in suspicious.risk.reason_codes


def test_cli_demo_generates_outputs(tmp_path: Path) -> None:
    output_path = tmp_path / "scored.jsonl"
    summary_path = tmp_path / "summary.json"
    input_path = tmp_path / "demo_input.json"

    code = solis_property_fraud.main(
        [
            "demo",
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--demo-input",
            str(input_path),
        ]
    )

    assert code == 0
    assert output_path.exists()
    assert summary_path.exists()
    assert input_path.exists()

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_transfers"] == len(rows)


def test_cli_batch_skips_generated_artifacts_in_input_dir(tmp_path: Path) -> None:
    input_one = tmp_path / "part1.json"
    input_two = tmp_path / "part2.jsonl"
    output_path = tmp_path / "scores.jsonl"
    summary_path = tmp_path / "summary.json"
    checkpoint_path = tmp_path / "checkpoint.json"

    first_record = {
        "state_fips": "06",
        "county_fips": "059",
        "apn": "123-456-10",
        "situs_address": "100 Main St, Santa Ana, CA",
        "recording_date": "2024-01-03",
        "instrument_type": "Grant Deed",
        "document_number": "2024-0000101",
        "grantor_name": "Alpha Holdings LLC",
        "grantee_name": "Sunset Development LLC",
        "consideration_amount": 800000.0,
        "market_value_estimate": 820000.0,
        "grantor_address": "500 Market St, Santa Ana, CA",
        "grantee_address": "1000 Harbor Blvd, Costa Mesa, CA",
        "grantor_distress_flags": [],
    }
    second_record = {
        "state_fips": "06",
        "county_fips": "059",
        "apn": "123-456-10",
        "situs_address": "100 Main St, Santa Ana, CA",
        "recording_date": "2024-02-01",
        "instrument_type": "Quitclaim Deed",
        "document_number": "2024-0000441",
        "grantor_name": "Sunset Development LLC",
        "grantee_name": "Harbor Equity Trust",
        "consideration_amount": 320000.0,
        "market_value_estimate": 850000.0,
        "grantor_address": "1000 Harbor Blvd, Costa Mesa, CA",
        "grantee_address": "1000 Harbor Blvd, Costa Mesa, CA",
        "grantor_distress_flags": ["lis_pendens"],
    }

    input_one.write_text(json.dumps([first_record]) + "\n", encoding="utf-8")
    input_two.write_text(json.dumps(second_record) + "\n", encoding="utf-8")

    code_first = solis_property_fraud.main(
        [
            "batch",
            "--input-dir",
            str(tmp_path),
            "--recursive",
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--checkpoint",
            str(checkpoint_path),
        ]
    )
    code_second = solis_property_fraud.main(
        [
            "batch",
            "--input-dir",
            str(tmp_path),
            "--recursive",
            "--output",
            str(output_path),
            "--summary",
            str(summary_path),
            "--checkpoint",
            str(checkpoint_path),
        ]
    )

    assert code_first == 0
    assert code_second == 0

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 2

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_transfers"] == 2

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    processed_paths = set(checkpoint["processed_files"])

    assert str(input_one.resolve()) in processed_paths
    assert str(input_two.resolve()) in processed_paths
    assert str(output_path.resolve()) not in processed_paths
    assert str(summary_path.resolve()) not in processed_paths
    assert str(checkpoint_path.resolve()) not in processed_paths
