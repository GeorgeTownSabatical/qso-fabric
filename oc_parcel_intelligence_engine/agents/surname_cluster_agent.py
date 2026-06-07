"""Surname variant detection and clustering."""

from __future__ import annotations

from difflib import SequenceMatcher


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def surname_variants(name: str, candidates: list[str], threshold: float = 0.82) -> list[str]:
    base = name.strip()
    return sorted({cand for cand in candidates if similarity(base, cand) >= threshold})
