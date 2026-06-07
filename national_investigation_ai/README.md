# National Investigation AI (Control Node + Distributed Workers)

Control-node architecture where the local machine orchestrates tasks and workers execute ingestion/reasoning/hypothesis jobs.

## Components
- `control/`: orchestration server, task dispatcher, node registry.
- `agents/`: task publishers for ingestion/reasoning/hypothesis workloads.
- `worker/`: worker loop and task executor.
- `dashboard/`: Streamlit UI for queue and result status.

## Run local distributed simulation
```bash
cd national_investigation_ai
python3 run_simulation.py
```
