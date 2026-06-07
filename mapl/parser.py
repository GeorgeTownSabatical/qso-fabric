from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .tokenizer import Token, tokenize


@dataclass(frozen=True)
class MAPLAst:
    context: str
    task: str
    modules: tuple[str, ...]
    output: tuple[str, ...]


def parse(source: str) -> MAPLAst:
    tokens = tokenize(source)
    cursor = _Cursor(tokens)
    cursor.expect("@")
    context = cursor.expect_ident()
    cursor.expect(">")
    task = cursor.expect_ident()
    cursor.expect("+")
    modules = _parse_list(cursor)
    cursor.expect("->")
    output = _parse_list(cursor)
    cursor.ensure_done()
    return MAPLAst(context=context, task=task, modules=modules, output=output)


def _parse_list(cursor: "_Cursor") -> tuple[str, ...]:
    values = [cursor.expect_ident()]
    while cursor.peek() == ",":
        cursor.expect(",")
        values.append(cursor.expect_ident())
    return tuple(values)


class _Cursor:
    def __init__(self, tokens: Iterable[Token]):
        self.tokens = list(tokens)
        self.index = 0

    def peek(self) -> str | None:
        if self.index >= len(self.tokens):
            return None
        return self.tokens[self.index].kind

    def expect(self, kind: str) -> None:
        if self.peek() != kind:
            raise ValueError(f"Expected {kind} but found {self.peek()}")
        self.index += 1

    def expect_ident(self) -> str:
        if self.peek() != "IDENT":
            raise ValueError(f"Expected IDENT but found {self.peek()}")
        value = self.tokens[self.index].value
        self.index += 1
        return value

    def ensure_done(self) -> None:
        if self.index != len(self.tokens):
            raise ValueError("Unexpected trailing tokens")
