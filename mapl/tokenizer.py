from __future__ import annotations

import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"\s*(@|>|\+|->|,|[A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(source):
        match = TOKEN_RE.match(source, pos)
        if not match:
            raise ValueError(f"Unexpected token at position {pos}")
        raw = match.group(1)
        pos = match.end()
        if raw in {"@", ">", "+", "->", ","}:
            tokens.append(Token(kind=raw, value=raw))
        else:
            tokens.append(Token(kind="IDENT", value=raw))
    return tokens
