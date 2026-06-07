# Autonomous Investigation AI

Self-evolving investigative layer that generates and verifies hypotheses from graph patterns.

## What it does
- Reads graph reasoning outputs.
- Generates hypotheses automatically.
- Gathers evidence and scores confidence.
- Updates hypothesis/evidence ledgers.
- Emits knowledge updates for confirmed hypotheses.

## Run one cycle
```bash
cd autonomous_investigation_ai
python3 pipeline/autonomous_cycle.py \
  --graph-json ../property_entity_global_graph/data/outputs/global_graph.json \
  --reasoning-dir ../graph_reasoning_engine/data/outputs \
  --output-dir data/outputs
```
