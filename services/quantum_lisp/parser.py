from __future__ import annotations

from typing import Any

from solis.shared.hashing import sha256_hex_obj

from services.quantum_lisp.models import QuantumLispProgram


class QuantumLispSyntaxError(ValueError):
    pass


def _tokens(source: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(source):
        char = source[i]
        if char == ";":
            while i < len(source) and source[i] != "\n":
                i += 1
            continue
        if char.isspace():
            i += 1
            continue
        if char in "()":
            tokens.append(char)
            i += 1
            continue
        if char == '"':
            i += 1
            value = []
            while i < len(source):
                if source[i] == "\\" and i + 1 < len(source):
                    value.append(source[i + 1])
                    i += 2
                    continue
                if source[i] == '"':
                    i += 1
                    tokens.append('"' + "".join(value) + '"')
                    break
                value.append(source[i])
                i += 1
            else:
                raise QuantumLispSyntaxError("unterminated string")
            continue
        start = i
        while i < len(source) and not source[i].isspace() and source[i] not in "();":
            i += 1
        tokens.append(source[start:i])
    return tokens


def _atom(token: str) -> Any:
    if token.startswith('"') and token.endswith('"'):
        return token[1:-1]
    try:
        if "." not in token:
            return int(token)
        return float(token)
    except ValueError:
        return token


def _read(tokens: list[str], index: int) -> tuple[Any, int]:
    if index >= len(tokens):
        raise QuantumLispSyntaxError("unexpected end of source")
    token = tokens[index]
    if token == "(":
        out = []
        index += 1
        while index < len(tokens) and tokens[index] != ")":
            expr, index = _read(tokens, index)
            out.append(expr)
        if index >= len(tokens):
            raise QuantumLispSyntaxError("missing closing paren")
        return out, index + 1
    if token == ")":
        raise QuantumLispSyntaxError("unexpected closing paren")
    return _atom(token), index + 1


def parse_quantum_lisp(source: str) -> QuantumLispProgram:
    tokens = _tokens(source)
    forms: list[Any] = []
    index = 0
    while index < len(tokens):
        expr, index = _read(tokens, index)
        if not isinstance(expr, list):
            raise QuantumLispSyntaxError("top-level forms must be lists")
        forms.append(expr)
    return QuantumLispProgram(
        source=source,
        forms=forms,
        source_hash=sha256_hex_obj({"source": source}),
        ast_hash=sha256_hex_obj({"forms": forms}),
    )
