"""CLI entrypoint for ocrecorder_pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from acquire.slicer import QuerySlice, generate_query_slices, save_slices
from analytics.parcel_scores import compute_parcel_scores
from analytics.rapid_conveyance import detect_rapid_conveyances
from analytics.surname_stats import compute_surname_summary
from analytics.title_chain import parcel_timeline
from graph.build_graph import build_projection_graph
from graph.communities import summarize_communities
from normalize.entities import normalize_records
from viz.heatmaps import build_surname_apn_density_matrix, compute_parcel_stats
from viz.network_export import export_graphml


def _comma_list(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def cmd_slice(args: argparse.Namespace) -> int:
    surnames = _comma_list(args.surnames)
    slices = generate_query_slices(
        surnames=surnames,
        year_start=args.year_start,
        year_end=args.year_end,
        use_quarters=args.quarters,
        doc_types=_comma_list(args.doc_types) if args.doc_types else None,
    )
    save_slices(Path(args.output), slices)
    print(f"wrote {len(slices)} slices -> {args.output}")
    return 0


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def cmd_analyze(args: argparse.Namespace) -> int:
    input_csv = Path(args.input_csv)
    normalized_out = Path(args.normalized_out)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(input_csv)
    normalized = normalize_records(df)

    _ensure_parent(normalized_out)
    normalized.to_csv(normalized_out, index=False)

    surname_summary = compute_surname_summary(normalized)
    surname_path = output_dir / "surname_anomaly_table.csv"
    surname_summary.to_csv(surname_path, index=False)

    alerts = detect_rapid_conveyances(normalized)
    alerts_path = output_dir / "parcel_alert_table.csv"
    alerts.to_csv(alerts_path, index=False)

    parcel_scores = compute_parcel_scores(normalized)
    parcel_scores_path = output_dir / "parcel_scores.csv"
    parcel_scores.to_csv(parcel_scores_path, index=False)

    density = build_surname_apn_density_matrix(normalized)
    density_path = output_dir / "surname_apn_density_matrix.csv"
    density.to_csv(density_path)

    parcel_stats = compute_parcel_stats(normalized)
    parcel_stats_path = output_dir / "parcel_stats.csv"
    parcel_stats.to_csv(parcel_stats_path, index=False)

    projection = build_projection_graph(normalized)
    graphml_path = output_dir / "title_projection.graphml"
    export_graphml(projection, graphml_path)

    communities = summarize_communities(projection, normalized)
    communities_path = output_dir / "network_cluster_report.csv"
    communities.to_csv(communities_path, index=False)

    title_dir = output_dir / "title_chains"
    title_dir.mkdir(parents=True, exist_ok=True)
    apns = list(parcel_scores["apn"].head(args.top_apns)) if not parcel_scores.empty else []
    for apn in apns:
        timeline = parcel_timeline(normalized, apn)
        if timeline.empty:
            continue
        timeline.to_csv(title_dir / f"title_chain_{apn.replace('-', '_')}.csv", index=False)

    summary = {
        "input_rows": int(len(df)),
        "normalized_rows": int(len(normalized)),
        "surname_rows": int(len(surname_summary)),
        "alert_rows": int(len(alerts)),
        "parcel_rows": int(len(parcel_scores)),
        "communities": int(len(communities)),
    }
    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"outputs -> {output_dir}")
    return 0


def cmd_run_demo(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    parsed_dir = Path(args.parsed_dir)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    sample_csv = parsed_dir / "sample_records.csv"

    # Minimal synthetic pilot with repeat APNs, notary concentration, and rapid conveyances.
    rows = [
        ["2024-0000001", "2024-01-02", "GRANT DEED", "405-112-17", "GARCIA, MARIA", "SMITH, DANIEL", "R LOPEZ"],
        ["2024-0000002", "2024-01-10", "DEED OF TRUST", "405-112-17", "SMITH, DANIEL", "SMITH FAMILY TRUST", "R LOPEZ"],
        ["2024-0000003", "2024-01-22", "QUITCLAIM DEED", "405-112-17", "SMITH FAMILY TRUST", "OC HOLDINGS LLC", "R LOPEZ"],
        ["2024-0000004", "2024-01-30", "GRANT DEED", "405-112-17", "OC HOLDINGS LLC", "SMITH, DANIEL", "R LOPEZ"],
        ["2024-0000005", "2024-03-14", "GRANT DEED", "405-112-18", "NGUYEN, ANH", "KIM, JI", "T CHEN"],
        ["2024-0000006", "2024-04-02", "DEED OF TRUST", "405-112-18", "KIM, JI", "PACIFIC BANK", "T CHEN"],
        ["2024-0000007", "2024-05-01", "GRANT DEED", "405-112-19", "LEE, MIN", "HERNANDEZ, ANA", "P REYES"],
        ["2024-0000008", "2024-05-20", "GRANT DEED", "405-112-19", "HERNANDEZ, ANA", "MARTINEZ, LUIS", "P REYES"],
        ["2024-0000009", "2024-06-05", "GRANT DEED", "405-112-19", "MARTINEZ, LUIS", "LEE FAMILY TRUST", "P REYES"],
        ["2024-0000010", "2024-06-15", "QUITCLAIM DEED", "405-112-19", "LEE FAMILY TRUST", "LEE, MIN", "P REYES"],
    ]

    demo_df = pd.DataFrame(
        rows,
        columns=["doc_number", "record_date", "doc_type", "apn", "grantor", "grantee", "notary"],
    )
    demo_df.to_csv(sample_csv, index=False)

    ns = argparse.Namespace(
        input_csv=str(sample_csv),
        normalized_out=str(Path("data/normalized/normalized_records.csv")),
        output_dir=str(output_dir),
        top_apns=args.top_apns,
    )
    print(f"demo input -> {sample_csv}")
    return cmd_analyze(ns)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OC Recorder pipeline CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_slice = sub.add_parser("slice", help="generate query slices")
    p_slice.add_argument("--surnames", required=True, help="comma-separated surnames")
    p_slice.add_argument("--year-start", type=int, required=True)
    p_slice.add_argument("--year-end", type=int, required=True)
    p_slice.add_argument("--doc-types", default="", help="comma-separated optional document types")
    p_slice.add_argument("--quarters", action="store_true")
    p_slice.add_argument("--output", default="manifests/query_slices.json")
    p_slice.set_defaults(func=cmd_slice)

    p_analyze = sub.add_parser("analyze", help="run normalization + analytics")
    p_analyze.add_argument("--input-csv", required=True)
    p_analyze.add_argument("--normalized-out", default="data/normalized/normalized_records.csv")
    p_analyze.add_argument("--output-dir", default="data/exports")
    p_analyze.add_argument("--top-apns", type=int, default=10)
    p_analyze.set_defaults(func=cmd_analyze)

    p_demo = sub.add_parser("run-demo", help="run full pipeline on synthetic sample")
    p_demo.add_argument("--output-dir", default="data/exports")
    p_demo.add_argument("--parsed-dir", default="data/parsed")
    p_demo.add_argument("--top-apns", type=int, default=5)
    p_demo.set_defaults(func=cmd_run_demo)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
