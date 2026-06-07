"""Normalization utilities for names, addresses, and entities."""

from __future__ import annotations

import re
import unicodedata


STOPWORDS = {"THE", "AND", "OF"}


def _ascii_upper(text: str) -> str:
    norm = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode("ascii")
    norm = norm.upper().strip()
    norm = re.sub(r"[^A-Z0-9,&\- ]+", " ", norm)
    norm = re.sub(r"\s+", " ", norm)
    return norm


def normalize_name(name: str) -> str:
    return _ascii_upper(name)


def normalize_address(address: str) -> str:
    text = _ascii_upper(address)
    text = text.replace(" STREET", " ST").replace(" AVENUE", " AVE").replace(" ROAD", " RD")
    return text


def normalize_company(name: str) -> str:
    text = _ascii_upper(name)
    tokens = [tok for tok in text.split() if tok not in STOPWORDS]
    return " ".join(tokens)


def surname(name: str) -> str:
    text = normalize_name(name)
    if "," in text:
        return text.split(",", 1)[0].strip()
    parts = text.split()
    return parts[-1] if parts else ""
