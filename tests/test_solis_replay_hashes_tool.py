from __future__ import annotations

from tools.solis_replay_hashes import (
    LONG_CONST_KEYS,
    NIGHTLY_CONST_KEYS,
    replace_constant_hashes,
)


def test_replace_constant_hashes_updates_expected_keys() -> None:
    source = (
        'EXPECTED_LONG_SEQUENCE_STATE_HASH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n'
        'EXPECTED_LONG_SEQUENCE_ROOT_HASH = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"\n'
        'EXPECTED_LONG_SEQUENCE_ANCHOR_CHAIN_HASH = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"\n'
    )
    updates = {
        "EXPECTED_LONG_SEQUENCE_STATE_HASH": "1" * 64,
        "EXPECTED_LONG_SEQUENCE_ROOT_HASH": "2" * 64,
        "EXPECTED_LONG_SEQUENCE_ANCHOR_CHAIN_HASH": "3" * 64,
    }
    rendered = replace_constant_hashes(source, updates)
    assert '"1111111111111111111111111111111111111111111111111111111111111111"' in rendered
    assert '"2222222222222222222222222222222222222222222222222222222222222222"' in rendered
    assert '"3333333333333333333333333333333333333333333333333333333333333333"' in rendered


def test_constant_key_maps_cover_state_root_and_anchor_chain() -> None:
    long_values = set(LONG_CONST_KEYS.values())
    nightly_values = set(NIGHTLY_CONST_KEYS.values())
    assert long_values == {"state", "root", "anchor_chain"}
    assert nightly_values == {"state", "root", "anchor_chain"}
