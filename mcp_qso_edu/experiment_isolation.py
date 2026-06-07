from __future__ import annotations

import hashlib

FORBIDDEN_ROOT_URIS = (
    "qso://infra.transport",
    "qso://identity.root",
    "qso://infra.registry.global",
    "qso://capital",
)


def sandbox_id_for_token(session_token: str) -> str:
    token = str(session_token).strip() or "anonymous"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return digest[:24]


def rewrite_uri(sandbox_id: str, uri: str) -> str:
    normalized = str(uri).strip()
    if not normalized:
        raise ValueError("uri must be non-empty")

    if normalized.startswith(f"qso://sandbox/{sandbox_id}/"):
        return normalized

    if normalized.startswith("qso://"):
        tail = normalized[len("qso://") :]
    else:
        tail = normalized

    return f"qso://sandbox/{sandbox_id}/{tail}"


def forbidden_root(uri: str) -> str | None:
    normalized = str(uri).strip()
    for prefix in FORBIDDEN_ROOT_URIS:
        if normalized.startswith(prefix):
            return prefix
    return None
