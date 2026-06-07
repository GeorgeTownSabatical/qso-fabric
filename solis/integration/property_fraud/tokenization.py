from __future__ import annotations

import re

from solis.integration.property_fraud.models import DeedTransferEvent, TransferTokens
from solis.shared.hashing import sha256_hex_text


_NON_ALNUM_PATTERN = re.compile(r"[^A-Z0-9]+")


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    text = str(value).strip().upper()
    text = _NON_ALNUM_PATTERN.sub(" ", text)
    return " ".join(piece for piece in text.split(" ") if piece)


def _normalize_apn(apn: str) -> str:
    compact = normalize_text(apn).replace(" ", "")
    return compact


def property_token_id(event: DeedTransferEvent) -> str:
    key = "|".join(
        [
            normalize_text(event.state_fips),
            normalize_text(event.county_fips),
            _normalize_apn(event.apn),
            normalize_text(event.situs_address),
        ]
    )
    return sha256_hex_text(key)


def party_token_id(name: str, address: str | None) -> str:
    key = "|".join([normalize_text(name), normalize_text(address)])
    return sha256_hex_text(key)


def instrument_token_id(event: DeedTransferEvent) -> str:
    key = "|".join(
        [
            normalize_text(event.state_fips),
            normalize_text(event.county_fips),
            normalize_text(event.document_number),
            normalize_text(event.book),
            normalize_text(event.page),
            event.recording_date.isoformat(),
        ]
    )
    return sha256_hex_text(key)


def tokenize_transfer(event: DeedTransferEvent) -> TransferTokens:
    return TransferTokens(
        property_token_id=property_token_id(event),
        grantor_token_id=party_token_id(event.grantor_name, event.grantor_address),
        grantee_token_id=party_token_id(event.grantee_name, event.grantee_address),
        instrument_token_id=instrument_token_id(event),
    )
