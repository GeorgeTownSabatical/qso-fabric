"""Control-node dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

BASE = Path(__file__).resolve().parents[1]


def _load(path: Path):
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else []


def main():
    st.title("National Investigation AI Control Node")
    st.subheader("Node Registry")
    st.json(_load(BASE / "data" / "queue" / "nodes.json"))

    st.subheader("Task Queue")
    st.json(_load(BASE / "data" / "queue" / "tasks.json"))

    st.subheader("Results")
    st.json(_load(BASE / "data" / "results" / "results.json"))


if __name__ == "__main__":
    main()
