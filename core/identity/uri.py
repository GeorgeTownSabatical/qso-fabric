from __future__ import annotations

import re


PERSON_URI_RE = re.compile(r"^qso://identity\.person\.[A-Za-z0-9._-]+$")
DEVICE_URI_RE = re.compile(r"^qso://identity\.device\.[A-Za-z0-9._-]+$")
TRUST_ROOT_URI_RE = re.compile(r"^qso://identity\.trustroot\.[A-Za-z0-9._-]+$")


def is_identity_person_uri(uri: str) -> bool:
    return bool(PERSON_URI_RE.fullmatch(uri))


def is_identity_device_uri(uri: str) -> bool:
    return bool(DEVICE_URI_RE.fullmatch(uri))


def is_identity_trust_root_uri(uri: str) -> bool:
    return bool(TRUST_ROOT_URI_RE.fullmatch(uri))


def validate_identity_person_uri(uri: str) -> None:
    if not is_identity_person_uri(uri):
        raise ValueError(f"invalid identity person uri: {uri}")

