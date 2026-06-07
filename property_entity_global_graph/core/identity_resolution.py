"""Identity resolution using normalization, fuzzy ratio, phonetic keys, and edit distance."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable
import math

from core.entity_normalizer import normalize_name


def levenshtein_distance(a: str, b: str) -> int:
    a = normalize_name(a)
    b = normalize_name(b)
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def fuzzy_match(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def soundex(text: str) -> str:
    t = normalize_name(text)
    if not t:
        return ""
    first = t[0]
    mapping = {
        "B": "1", "F": "1", "P": "1", "V": "1",
        "C": "2", "G": "2", "J": "2", "K": "2", "Q": "2", "S": "2", "X": "2", "Z": "2",
        "D": "3", "T": "3",
        "L": "4",
        "M": "5", "N": "5",
        "R": "6",
    }
    digits = []
    last = ""
    for ch in t[1:]:
        code = mapping.get(ch, "")
        if code != last:
            if code:
                digits.append(code)
            last = code
    return (first + "".join(digits) + "000")[:4]


def phonetic_match(a: str, b: str) -> bool:
    return soundex(a) == soundex(b)


@dataclass
class CanonicalEntity:
    canonical_name: str
    aliases: set[str] = field(default_factory=set)


@dataclass(slots=True)
class EntitySnapshot:
    """Feature snapshot for probabilistic identity linkage."""

    name: str
    address: str = ""
    neighbors: set[str] = field(default_factory=set)
    created_day: int | None = None
    transfer_days: list[int] = field(default_factory=list)


class IdentityResolver:
    def __init__(self, fuzzy_threshold: float = 0.9, max_distance: int = 2):
        self.fuzzy_threshold = fuzzy_threshold
        self.max_distance = max_distance
        self.canonical: list[CanonicalEntity] = []

    def resolve_name(self, name: str) -> str:
        normalized = normalize_name(name)
        if not normalized:
            return normalized
        for entity in self.canonical:
            ref = entity.canonical_name
            if normalized == ref:
                entity.aliases.add(normalized)
                return ref
            if fuzzy_match(normalized, ref) >= self.fuzzy_threshold:
                entity.aliases.add(normalized)
                return ref
            if levenshtein_distance(normalized, ref) <= self.max_distance:
                entity.aliases.add(normalized)
                return ref
            if phonetic_match(normalized, ref):
                entity.aliases.add(normalized)
                return ref
        self.canonical.append(CanonicalEntity(canonical_name=normalized, aliases={normalized}))
        return normalized

    def resolve_many(self, names: Iterable[str]) -> dict[str, str]:
        return {name: self.resolve_name(name) for name in names}


def _address_similarity(a: str, b: str) -> float:
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _temporal_similarity(a: EntitySnapshot, b: EntitySnapshot) -> float:
    # Higher score when creation timing and transfer cadence are close.
    score = 0.0
    parts = 0

    if a.created_day is not None and b.created_day is not None:
        parts += 1
        diff = abs(a.created_day - b.created_day)
        score += math.exp(-(diff / 365.0))

    if a.transfer_days and b.transfer_days:
        parts += 1
        avg_a = sum(a.transfer_days) / len(a.transfer_days)
        avg_b = sum(b.transfer_days) / len(b.transfer_days)
        score += math.exp(-(abs(avg_a - avg_b) / 180.0))

    if parts == 0:
        return 0.0
    return score / parts


def match_probability(a: EntitySnapshot, b: EntitySnapshot) -> float:
    """Weighted probabilistic linkage score in [0, 1]."""

    name_similarity = fuzzy_match(a.name, b.name)
    address_similarity = _address_similarity(a.address, b.address)
    graph_similarity = _jaccard(a.neighbors, b.neighbors)
    temporal_similarity = _temporal_similarity(a, b)

    score = (
        0.35 * name_similarity
        + 0.25 * address_similarity
        + 0.20 * graph_similarity
        + 0.20 * temporal_similarity
    )
    return max(0.0, min(1.0, score))
