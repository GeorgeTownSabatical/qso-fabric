# OC Parcel Intelligence Engine

Automated APN-focused parcel intelligence workflow for Orange County.

## Features
- APN normalization (`40511217`, `405-112-17`, `405 112 17` -> `405-112-17`).
- Assessor/recorder/GIS agent interfaces.
- Ownership graph construction with NetworkX.
- JSON and graph artifact storage.
- Neighbor expansion and surname variant helper.

## Quickstart
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python pipeline/run_pipeline.py 405-112-17
python pipeline/expand_neighbors.py 405-112-17 --depth 1
```

## Outputs
- `data/parcels/<apn>.json`
- `data/documents/<apn>_docs.json`
- `data/graphs/<apn>_graph.json`
- `data/graphs/<apn>_graph.graphml`
