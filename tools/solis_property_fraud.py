from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from solis.integration.property_fraud import (
    DeedTransferEvent,
    PropertyFraudPipeline,
    load_events,
    parse_events,
    summarize_scored_transfers,
    write_scored_transfers,
)


def _default_output_path() -> Path:
    return Path(".codex/state/solis_property_fraud_scores.jsonl")


def _default_summary_path() -> Path:
    return Path(".codex/state/solis_property_fraud_summary.json")


def _default_checkpoint_path() -> Path:
    return Path(".codex/state/solis_property_fraud_checkpoint.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_scored_transfers(path: Path, rows: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")


def _write_summary(path: Path | None, summary: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _summarize_output_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "total_transfers": 0,
            "tier_counts": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "high_or_critical_count": 0,
            "max_score": 0,
        }

    by_tier: dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    total = 0
    high_or_critical = 0
    max_score = 0

    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        risk = row.get("risk", {})
        tier = str(risk.get("risk_tier", "low")).lower()
        score = int(risk.get("score", 0))
        by_tier[tier] = by_tier.get(tier, 0) + 1
        total += 1
        if tier in {"high", "critical"}:
            high_or_critical += 1
        if score > max_score:
            max_score = score

    return {
        "total_transfers": total,
        "tier_counts": by_tier,
        "high_or_critical_count": high_or_critical,
        "max_score": max_score,
    }


def _load_existing_events_from_output(path: Path) -> list[DeedTransferEvent]:
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [DeedTransferEvent.from_mapping(row) for row in rows]


def _load_checkpoint(path: Path, *, reset: bool) -> dict[str, Any]:
    if reset or not path.exists():
        return {
            "schema_version": "1.0",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "processed_files": {},
        }
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("checkpoint must be a JSON object")
    loaded.setdefault("schema_version", "1.0")
    loaded.setdefault("created_at", _utc_now())
    loaded.setdefault("processed_files", {})
    loaded.setdefault("updated_at", _utc_now())
    if not isinstance(loaded["processed_files"], dict):
        raise ValueError("checkpoint processed_files must be an object")
    return loaded


def _write_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    checkpoint["updated_at"] = _utc_now()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iter_input_files(input_dir: Path, recursive: bool) -> list[Path]:
    globber = input_dir.rglob if recursive else input_dir.glob
    files = [
        path
        for path in globber("*")
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
    ]
    return sorted(files)


def _demo_records() -> list[dict[str, Any]]:
    return [
        {
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
        },
        {
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
        },
        {
            "state_fips": "06",
            "county_fips": "059",
            "apn": "888-222-99",
            "situs_address": "44 Cedar Rd, Irvine, CA",
            "recording_date": "2024-06-11",
            "instrument_type": "Grant Deed",
            "document_number": "2024-0011021",
            "grantor_name": "Westlake Family Trust",
            "grantee_name": "Orchid Homes LLC",
            "consideration_amount": 1210000.0,
            "market_value_estimate": 1200000.0,
            "grantor_address": "44 Cedar Rd, Irvine, CA",
            "grantee_address": "311 Fleet St, Irvine, CA",
            "grantor_distress_flags": [],
        },
    ]


def _run_pipeline(records: list[dict[str, Any]], output_path: Path, summary_path: Path | None) -> int:
    events = parse_events(records)
    scored = PropertyFraudPipeline().run(events)
    write_scored_transfers(output_path, scored)

    summary = summarize_scored_transfers(scored)
    _write_summary(summary_path, summary)

    print(json.dumps({"output_path": str(output_path), "summary": summary}, indent=2, sort_keys=True))
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    events = load_events(args.input)
    scored = PropertyFraudPipeline().run(events)
    write_scored_transfers(args.output, scored)

    summary = summarize_scored_transfers(scored)
    _write_summary(args.summary, summary)
    print(json.dumps({"output_path": str(args.output), "summary": summary}, indent=2, sort_keys=True))
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    records = _demo_records()
    if args.demo_input is not None:
        args.demo_input.parent.mkdir(parents=True, exist_ok=True)
        args.demo_input.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return _run_pipeline(records, args.output, args.summary)


def _cmd_batch(args: argparse.Namespace) -> int:
    checkpoint = _load_checkpoint(args.checkpoint, reset=args.reset_checkpoint)
    processed_files: dict[str, Any] = checkpoint["processed_files"]

    if args.replace_output and args.output.exists():
        args.output.unlink()

    input_files = _iter_input_files(args.input_dir, args.recursive)
    if args.max_files is not None:
        input_files = input_files[: args.max_files]

    excluded_paths = {str(args.output.resolve()), str(args.checkpoint.resolve())}
    if args.summary is not None:
        excluded_paths.add(str(args.summary.resolve()))

    candidates: list[tuple[Path, str, str]] = []
    skipped = 0
    for file_path in input_files:
        abs_path = str(file_path.resolve())
        if abs_path in excluded_paths:
            skipped += 1
            continue
        file_hash = _hash_file(file_path)
        prior = processed_files.get(abs_path)
        if isinstance(prior, dict) and prior.get("sha256") == file_hash:
            skipped += 1
            continue
        candidates.append((file_path, abs_path, file_hash))

    pipeline = PropertyFraudPipeline()
    if args.seed_from_output and args.output.exists():
        prior_events = _load_existing_events_from_output(args.output)
        pipeline.prime(prior_events)

    all_new_events: list[DeedTransferEvent] = []
    file_event_counts: dict[str, int] = {}
    for file_path, abs_path, _ in candidates:
        events = load_events(file_path)
        all_new_events.extend(events)
        file_event_counts[abs_path] = len(events)

    scored = pipeline.run(all_new_events)

    if scored:
        if args.output.exists() and not args.replace_output:
            _append_scored_transfers(args.output, scored)
        else:
            write_scored_transfers(args.output, scored)
    elif not args.output.exists():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text("", encoding="utf-8")

    processed_at = _utc_now()
    for _, abs_path, file_hash in candidates:
        processed_files[abs_path] = {
            "sha256": file_hash,
            "event_count": file_event_counts.get(abs_path, 0),
            "processed_at": processed_at,
        }

    summary = _summarize_output_file(args.output)
    _write_summary(args.summary, summary)
    _write_checkpoint(args.checkpoint, checkpoint)

    result = {
        "output_path": str(args.output),
        "summary_path": str(args.summary) if args.summary is not None else None,
        "checkpoint_path": str(args.checkpoint),
        "processed_files": len(candidates),
        "skipped_files": skipped,
        "scored_rows_added": len(scored),
        "summary": summary,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Solis property fraud tokenization and risk scoring automation.")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Score deed/grant events from JSON or JSONL input.")
    run_cmd.add_argument("--input", type=Path, required=True, help="Input file (.json list/.json with events/.jsonl).")
    run_cmd.add_argument("--output", type=Path, default=_default_output_path(), help="Output JSONL for scored rows.")
    run_cmd.add_argument("--summary", type=Path, default=_default_summary_path(), help="Output summary JSON path.")
    run_cmd.set_defaults(func=_cmd_run)

    demo_cmd = sub.add_parser("demo", help="Run scoring against bundled sample transfers.")
    demo_cmd.add_argument("--output", type=Path, default=_default_output_path(), help="Output JSONL for scored rows.")
    demo_cmd.add_argument("--summary", type=Path, default=_default_summary_path(), help="Output summary JSON path.")
    demo_cmd.add_argument("--demo-input", type=Path, default=None, help="Optional path to write demo input records.")
    demo_cmd.set_defaults(func=_cmd_demo)

    batch_cmd = sub.add_parser(
        "batch",
        help="Incrementally process JSON/JSONL files from a directory with checkpointing.",
    )
    batch_cmd.add_argument("--input-dir", type=Path, required=True, help="Directory containing deed/grant JSON or JSONL files.")
    batch_cmd.add_argument("--recursive", action="store_true", help="Recursively discover input files.")
    batch_cmd.add_argument("--output", type=Path, default=_default_output_path(), help="Output JSONL for scored rows.")
    batch_cmd.add_argument("--summary", type=Path, default=_default_summary_path(), help="Output summary JSON path.")
    batch_cmd.add_argument(
        "--checkpoint",
        type=Path,
        default=_default_checkpoint_path(),
        help="Checkpoint JSON for incremental file processing state.",
    )
    batch_cmd.add_argument("--reset-checkpoint", action="store_true", help="Ignore existing checkpoint and rebuild file processing state.")
    batch_cmd.add_argument("--replace-output", action="store_true", help="Replace output JSONL instead of appending.")
    batch_cmd.add_argument(
        "--seed-from-output",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Prime feature history from existing output before scoring new files.",
    )
    batch_cmd.add_argument("--max-files", type=int, default=None, help="Optional cap on number of discovered files to process.")
    batch_cmd.set_defaults(func=_cmd_batch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
