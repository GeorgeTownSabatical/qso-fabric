# Investigation AI (Local Orchestration Stack)

Local control-node wrapper for the full investigative stack:
1. `property_entity_global_graph`
2. `graph_reasoning_engine`
3. `autonomous_investigation_ai`

## Run full local cycle
```bash
cd investigation_ai
python3 pipeline/orchestrate_stack.py
```

## Run dashboard
```bash
streamlit run visualization/dashboard.py
```
