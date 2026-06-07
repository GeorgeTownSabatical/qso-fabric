# Property Entity Global Graph

Unified investigative entity graph integrating parcel ownership, recorder docs, corporate registry data, SEC-style records, and court records.

## What this repo does
- Normalizes entities and resolves aliases.
- Ingests heterogeneous records into one graph.
- Stores nodes/edges and append-only events.
- Runs beneficial-owner, shell-chain, surname cluster, and transfer velocity analysis.
- Exports graph and report artifacts.

## Quickstart
```bash
cd property_entity_global_graph
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run_global_graph.py
```

## Output artifacts
- `data/outputs/global_graph.json`
- `data/outputs/event_log.jsonl`
- `data/outputs/beneficial_owner_report.json`
- `data/outputs/shell_company_report.json`
- `data/outputs/surname_cluster_report.json`
- `data/outputs/transfer_velocity_report.json`
