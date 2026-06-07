"""Stack dashboard across ingestion, reasoning, and autonomous layers."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from core.service_config import AUTO_REPO, OUT, PROPERTY_REPO, REASONING_REPO


def _load(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    st.title("Investigation AI Stack Dashboard")

    st.subheader("Stack Orchestration")
    st.json(_load(OUT / "stack_run_summary.json"))

    st.subheader("Property Graph Summary")
    st.json(_load(PROPERTY_REPO / "data" / "outputs" / "run_summary.json"))

    st.subheader("Graph Reasoning Summary")
    st.json(_load(REASONING_REPO / "data" / "outputs" / "reasoning_summary.json"))

    st.subheader("Autonomous Cycle Summary")
    st.json(_load(AUTO_REPO / "data" / "outputs" / "autonomous_cycle_summary.json"))


if __name__ == "__main__":
    main()
