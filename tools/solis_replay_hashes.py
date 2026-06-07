from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

LONG_TEST_PATH = Path("solis/tests/test_replay_determinism.py")
NIGHTLY_TEST_PATH = Path("solis/tests/test_multinode_replay_nightly.py")
STAR_ID = "spherechain"

LONG_CONST_KEYS = {
    "EXPECTED_LONG_SEQUENCE_STATE_HASH": "state",
    "EXPECTED_LONG_SEQUENCE_ROOT_HASH": "root",
    "EXPECTED_LONG_SEQUENCE_ANCHOR_CHAIN_HASH": "anchor_chain",
}
NIGHTLY_CONST_KEYS = {
    "EXPECTED_NIGHTLY_1000_STATE_HASH": "state",
    "EXPECTED_NIGHTLY_1000_ROOT_HASH": "root",
    "EXPECTED_NIGHTLY_1000_ANCHOR_CHAIN_HASH": "anchor_chain",
}


def _load_solis_runtime() -> tuple[type, type]:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from solis.config import SolisConfig  # noqa: PLC0415
    from solis.services.solis_star_service import SolisStarService  # noqa: PLC0415

    return SolisConfig, SolisStarService


def _hash_obj(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _long_delta(step: int) -> dict[str, object]:
    mass_value = 0.001 + ((step % 5) * 0.00015)
    luminosity_value = 0.0012 + ((step % 7) * 0.00011)
    entropy_value: object = "8e-05" if (step % 9 == 0) else "-3e-05"
    magnetic_value: object = "5e-05" if (step % 4 == 0) else -0.00004

    mass: object = format(mass_value, ".12e") if (step % 2 == 0) else mass_value
    luminosity: object = format(luminosity_value, ".12e") if (step % 3 == 0) else luminosity_value

    if step % 17 == 0:
        entropy_value = "1e-24"
    if step % 23 == 0:
        magnetic_value = "-1e-24"

    return {
        "mass": mass,
        "luminosity": luminosity,
        "entropy_index": entropy_value,
        "magnetic_field": magnetic_value,
    }


def _nightly_delta(step: int) -> dict[str, float]:
    mass = 0.0009 + ((step % 13) * 0.00017)
    luminosity = 0.0011 + ((step % 11) * 0.00013)
    entropy = 0.00008 if (step % 7 == 0) else -0.00003
    magnetic = 0.00005 if (step % 5 == 0) else -0.00004
    return {
        "mass": mass,
        "luminosity": luminosity,
        "entropy_index": entropy,
        "magnetic_field": magnetic,
    }


def compute_long_hashes(*, event_count: int = 360) -> dict[str, str]:
    SolisConfig, SolisStarService = _load_solis_runtime()
    config = SolisConfig(anchor_interval=8, runtime_gate_enabled=False)
    nodes = [SolisStarService(config=config) for _ in range(3)]
    for node in nodes:
        node.create_star(star_id=STAR_ID, chain_id=STAR_ID)

    for idx in range(event_count):
        delta = _long_delta(idx)
        for node in nodes:
            node.patch_star(star_uri_or_id=STAR_ID, delta=delta, actor="replay-long")

    state_hash = next(iter({_hash_obj(node.get_star(STAR_ID)["state_layer"]) for node in nodes}))
    root_hash = next(iter({node.merkle_anchor.root() for node in nodes}))
    anchor_epoch = len(nodes[0].merkle_anchor.event_hashes) // config.anchor_interval
    anchor_hashes: list[str] = []
    for epoch in range(1, anchor_epoch + 1):
        uri = f"qso://solis.anchor.{epoch}"
        hashes = {_hash_obj(node.qso.read(uri)["state_layer"]) for node in nodes}
        if len(hashes) != 1:
            raise RuntimeError(f"anchor hash divergence at long epoch {epoch}: {sorted(hashes)}")
        anchor_hashes.append(next(iter(hashes)))
    return {
        "state": state_hash,
        "root": root_hash,
        "anchor_chain": _hash_obj(anchor_hashes),
    }


def compute_nightly_hashes(*, event_count: int = 1000) -> dict[str, str]:
    SolisConfig, SolisStarService = _load_solis_runtime()
    config = SolisConfig(anchor_interval=8, runtime_gate_enabled=False)
    nodes = [SolisStarService(config=config) for _ in range(3)]
    for node in nodes:
        node.create_star(star_id=STAR_ID, chain_id=STAR_ID)

    for idx in range(event_count):
        delta = _nightly_delta(idx)
        for node in nodes:
            node.patch_star(star_uri_or_id=STAR_ID, delta=delta, actor="replay-nightly")

    state_hash = next(iter({_hash_obj(node.get_star(STAR_ID)["state_layer"]) for node in nodes}))
    root_hash = next(iter({node.merkle_anchor.root() for node in nodes}))
    anchor_epoch = len(nodes[0].merkle_anchor.event_hashes) // config.anchor_interval
    anchor_hashes: list[str] = []
    for epoch in range(1, anchor_epoch + 1):
        uri = f"qso://solis.anchor.{epoch}"
        hashes = {_hash_obj(node.qso.read(uri)["state_layer"]) for node in nodes}
        if len(hashes) != 1:
            raise RuntimeError(f"anchor hash divergence at nightly epoch {epoch}: {sorted(hashes)}")
        anchor_hashes.append(next(iter(hashes)))
    return {
        "state": state_hash,
        "root": root_hash,
        "anchor_chain": _hash_obj(anchor_hashes),
    }


def extract_constant_hashes(path: Path, keys: dict[str, str]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for const_name, normalized_key in keys.items():
        match = re.search(rf"^{const_name}\s*=\s*\"([0-9a-f]{{64}})\"\s*$", text, flags=re.MULTILINE)
        if match is None:
            raise ValueError(f"missing constant {const_name} in {path}")
        values[normalized_key] = match.group(1)
    return values


def replace_constant_hashes(text: str, updates: dict[str, str]) -> str:
    updated = text
    for const_name, value in updates.items():
        pattern = rf"^({const_name}\s*=\s*\")([0-9a-f]{{64}})(\"\s*)$"
        updated, replacements = re.subn(pattern, rf"\g<1>{value}\g<3>", updated, count=1, flags=re.MULTILINE)
        if replacements != 1:
            raise ValueError(f"unable to replace constant {const_name}")
    return updated


def verify(constants: dict[str, str], computed: dict[str, str], *, label: str) -> list[str]:
    mismatches: list[str] = []
    for key in ("state", "root", "anchor_chain"):
        if constants[key] != computed[key]:
            mismatches.append(
                f"{label}:{key}: expected={constants[key]} actual={computed[key]}"
            )
    return mismatches


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controlled replay-hash compute/verify/update tooling.")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--scope", choices=["all", "long", "nightly"], default="all")
    common.add_argument("--long-events", type=int, default=360)
    common.add_argument("--nightly-events", type=int, default=1000)

    compute = sub.add_parser("compute", parents=[common], help="Compute replay hashes and print JSON")
    compute.add_argument("--pretty", action="store_true", help="Pretty-print JSON")

    sub.add_parser("verify", parents=[common], help="Verify computed hashes against pinned constants")

    update = sub.add_parser("update", parents=[common], help="Preview or apply constant updates")
    update.add_argument("--apply", action="store_true", help="Apply updates to test files")

    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    include_long = args.scope in {"all", "long"}
    include_nightly = args.scope in {"all", "nightly"}

    computed: dict[str, dict[str, str]] = {}
    if include_long:
        computed["long"] = compute_long_hashes(event_count=args.long_events)
    if include_nightly:
        computed["nightly"] = compute_nightly_hashes(event_count=args.nightly_events)

    if args.command == "compute":
        if args.pretty:
            print(json.dumps(computed, indent=2, sort_keys=True))
        else:
            print(json.dumps(computed, sort_keys=True))
        return 0

    if args.command == "verify":
        failures: list[str] = []
        if include_long:
            failures.extend(
                verify(
                    extract_constant_hashes(LONG_TEST_PATH, LONG_CONST_KEYS),
                    computed["long"],
                    label="long",
                )
            )
        if include_nightly:
            failures.extend(
                verify(
                    extract_constant_hashes(NIGHTLY_TEST_PATH, NIGHTLY_CONST_KEYS),
                    computed["nightly"],
                    label="nightly",
                )
            )
        if failures:
            for failure in failures:
                print(f"MISMATCH: {failure}")
            return 1
        print("OK: replay hash constants are in sync")
        return 0

    if args.command == "update":
        update_summary: list[str] = []
        if include_long:
            long_updates = {const_name: computed["long"][normalized_key] for const_name, normalized_key in LONG_CONST_KEYS.items()}
            long_text = LONG_TEST_PATH.read_text(encoding="utf-8")
            new_long_text = replace_constant_hashes(long_text, long_updates)
            if new_long_text != long_text:
                if args.apply:
                    LONG_TEST_PATH.write_text(new_long_text, encoding="utf-8")
                    update_summary.append(f"updated {LONG_TEST_PATH}")
                else:
                    update_summary.append(f"would update {LONG_TEST_PATH}")

        if include_nightly:
            nightly_updates = {
                const_name: computed["nightly"][normalized_key]
                for const_name, normalized_key in NIGHTLY_CONST_KEYS.items()
            }
            nightly_text = NIGHTLY_TEST_PATH.read_text(encoding="utf-8")
            new_nightly_text = replace_constant_hashes(nightly_text, nightly_updates)
            if new_nightly_text != nightly_text:
                if args.apply:
                    NIGHTLY_TEST_PATH.write_text(new_nightly_text, encoding="utf-8")
                    update_summary.append(f"updated {NIGHTLY_TEST_PATH}")
                else:
                    update_summary.append(f"would update {NIGHTLY_TEST_PATH}")

        if not update_summary:
            print("No constant updates required")
            return 0
        for line in update_summary:
            print(line)
        if not args.apply:
            print("Dry-run complete. Re-run with --apply to persist changes.")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
