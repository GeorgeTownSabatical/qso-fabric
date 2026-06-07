"""Name normalization and entity typing."""

from __future__ import annotations

import re
import unicodedata

CORP_HINTS = {"LLC", "INC", "CORP", "BANK", "ASSOCIATION", "TRUST", "COMPANY", "LP", "LLP"}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9,&\- ]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def entity_type(name: str) -> str:
    toks = set(normalize_text(name).replace(",", " ").split())
    return "entity" if toks & CORP_HINTS else "person"


def extract_surname(name: str) -> str:
    text = normalize_text(name)
    if not text:
        return ""
    if "," in text:
        return text.split(",", 1)[0].strip()
    parts = text.split()
    return parts[-1] if parts else ""
