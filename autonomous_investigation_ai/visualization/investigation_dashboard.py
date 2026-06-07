"""Streamlit dashboard for autonomous investigation state."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

OUT = Path(__file__).resolve().parents[1] / "data" / "outputs"


def _read(name: str):
    p = OUT / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    st.title("Autonomous Investigation AI")
    st.subheader("Cycle Summary")
    st.json(_read("autonomous_cycle_summary.json") or {})

    st.subheader("Latest Cycle Report")
    st.json(_read("autonomous_cycle_report.json") or {})

    st.subheader("Hypothesis Store")
    st.json(_read("hypothesis_store.json") or [])

    st.subheader("Evidence Store")
    st.json(_read("evidence_store.json") or [])


if __name__ == "__main__":
    main()
