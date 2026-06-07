"""Minimal Streamlit anomaly dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


OUT = Path(__file__).resolve().parents[1] / "data" / "outputs"


def _load(name: str):
    path = OUT / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    st.title("Graph Reasoning Anomaly Dashboard")
    summary = _load("reasoning_summary.json") or {}
    anomalies = _load("anomalies.json") or {}
    st.subheader("Summary")
    st.json(summary)
    st.subheader("Anomalies")
    st.json(anomalies)


if __name__ == "__main__":
    main()
