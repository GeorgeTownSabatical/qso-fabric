from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Set

TOTAL_EVENTS = 50_000
SEED = 12345


def dhash(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def seeded(i: int, mod: int) -> int:
    return (i * 11400714819323198485 + SEED) % mod


@dataclass
class Identity:
    identity_id: str
    status: str = "active"
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


@dataclass
class Node:
    name: str

    def __post_init__(self):
        self.identities: Dict[str, Identity] = {}
        self.event_log: List[dict] = []
        self.state_hash = ""
        self.seen_event_ids: Set[str] = set()
        self.last_logical_time = -1

    def validate_event(self, event: dict) -> bool:
        if event["event_id"] in self.seen_event_ids:
            return False

        if event["logical_time"] <= self.last_logical_time:
            return False

        if not event.get("signature_valid", False):
            return False

        if event["policy_version"] < 1:
            return False

        if event["type"] == "MUTATE":
            ident = self.identities.get(event["identity_id"])
            if ident is None:
                return False
            if ident.status == "revoked":
                return False

        if event["type"] == "REVOKE":
            if event["identity_id"] not in self.identities:
                return False

        return True

    def apply_event(self, event: dict):
        if not self.validate_event(event):
            return False

        self.event_log.append(event)
        self.seen_event_ids.add(event["event_id"])
        self.last_logical_time = event["logical_time"]
        self.state_hash = dhash(self.state_hash + dhash(str(event)))

        if event["type"] == "CREATE":
            self.identities[event["identity_id"]] = Identity(event["identity_id"])
        elif event["type"] == "MUTATE":
            self.identities[event["identity_id"]].roles.append(event["role"])
        elif event["type"] == "REVOKE":
            self.identities[event["identity_id"]].status = "revoked"

        return True

    def export_snapshot(self):
        return {
            "event_log": list(self.event_log),
            "state_hash": self.state_hash,
            "event_hash_chain": dhash("".join(dhash(str(e)) for e in self.event_log)),
        }

    def strict_import(self, snapshot: dict):
        # strict archival validation: any invalid historical event rejects import
        shadow_seen: Set[str] = set()
        shadow_last = -1
        shadow_identities: Dict[str, Identity] = {}

        for e in snapshot["event_log"]:
            if e["event_id"] in shadow_seen:
                raise Exception("Snapshot import failed: duplicate historical event_id")
            if e["logical_time"] <= shadow_last:
                raise Exception("Snapshot import failed: non-monotonic historical logical_time")
            if not e.get("signature_valid", False):
                raise Exception("Snapshot import failed: invalid historical signature")
            if e["policy_version"] < 1:
                raise Exception("Snapshot import failed: invalid historical policy version")

            if e["type"] == "MUTATE":
                ident = shadow_identities.get(e["identity_id"])
                if ident is None or ident.status == "revoked":
                    raise Exception("Snapshot import failed: invalid historical identity mutation")
            if e["type"] == "REVOKE" and e["identity_id"] not in shadow_identities:
                raise Exception("Snapshot import failed: invalid historical revoke")

            # shadow apply
            if e["type"] == "CREATE":
                shadow_identities[e["identity_id"]] = Identity(e["identity_id"])
            elif e["type"] == "MUTATE":
                shadow_identities[e["identity_id"]].roles.append(e["role"])
            elif e["type"] == "REVOKE":
                shadow_identities[e["identity_id"]].status = "revoked"

            shadow_seen.add(e["event_id"])
            shadow_last = e["logical_time"]

        # replay into this node
        for e in snapshot["event_log"]:
            self.apply_event(e)

        if self.state_hash != snapshot["state_hash"]:
            raise Exception("Snapshot state mismatch")


def legit_event(i):
    return {
        "event_id": f"evt_{i}",
        "type": "CREATE" if i < 1000 else "MUTATE",
        "identity_id": f"id_{seeded(i, 1000)}",
        "role": f"role_{seeded(i, 20)}",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": True,
    }


def forged_event(i):
    return {
        "event_id": f"forged_{i}",
        "type": "MUTATE",
        "identity_id": f"id_{seeded(i, 1000)}",
        "role": "admin",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": False,
    }


def run_composite_airgap():
    t0 = time.perf_counter()

    a = Node("A")
    b = Node("B")

    # Phase 1: shared baseline
    for i in range(1000):
        event = legit_event(i)
        a.apply_event(event)
        b.apply_event(event)

    # Phase 2: B offline under adversarial pressure
    for i in range(1000, TOTAL_EVENTS):
        if i % 100 == 0:
            event = forged_event(i)
        else:
            event = legit_event(i)
        b.apply_event(event)

    # Phase 3: B exports snapshot
    snapshot = b.export_snapshot()

    # Phase 4: A strict import
    a_import = Node("A_import")
    a_import.strict_import(snapshot)

    # Convergence
    if a_import.state_hash != b.state_hash:
        raise Exception("Air-gap convergence failure")

    duration = round(time.perf_counter() - t0, 6)
    return {
        "duration_s": duration,
        "state_hash": b.state_hash,
        "strict_import_passed": True,
    }


if __name__ == "__main__":
    print("=== Composite Sovereign Air-Gap Zero-Trust Test ===")
    out = run_composite_airgap()
    print("Duration:", out["duration_s"], "seconds")
    print("Final State Hash:", out["state_hash"])
    print("Strict Archival Integrity: ✔")
    print("Converged: ✔")
