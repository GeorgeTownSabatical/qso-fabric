# Graph Reasoning Engine

AI reasoning layer over the unified property/entity graph.

## Capabilities
- Graph loading from Neo4j or JSON export.
- Feature extraction for entities.
- Community detection and influence analysis.
- Link prediction and anomaly detection.
- Beneficial owner and influence agent outputs.

## Quickstart
```bash
cd graph_reasoning_engine
python3 pipeline/reasoning_pipeline.py \
  --graph-json ../property_entity_global_graph/data/outputs/global_graph.json
```

Outputs are written under `data/outputs/`.
