from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List, Set

SEED = 9001
TOTAL_EVENTS = 100_000


def dhash(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()


def seeded(i: int, mod: int) -> int:
    return (i * 6364136223846793005 + SEED) % mod


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
    identities: Dict[str, Identity]
    event_log: List[dict]
    seen_event_ids: Set[str]
    state_hash: str
    last_logical_time: int

    def __init__(self, name: str):
        self.name = name
        self.identities = {}
        self.event_log = []
        self.seen_event_ids = set()
        self.state_hash = ""
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

        elif event["type"] == "REVOKE":
            self.identities[event["identity_id"]].status = "revoked"

        elif event["type"] == "MUTATE":
            self.identities[event["identity_id"]].roles.append(event["role"])

        return True


def legit_event(i):
    identity_id = f"id_{seeded(i, 1000)}"
    return {
        "event_id": f"evt_{i}",
        "type": "CREATE" if i < 1000 else "MUTATE",
        "identity_id": identity_id,
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


def downgrade_policy_event(i):
    return {
        "event_id": f"downgrade_{i}",
        "type": "MUTATE",
        "identity_id": f"id_{seeded(i, 1000)}",
        "role": "user",
        "logical_time": i,
        "policy_version": 0,
        "signature_valid": True,
    }


def run_zero_trust_identity_attack():
    print("\n=== Zero-Trust Identity Adversarial Test ===")
    t0 = time.perf_counter()

    a = Node("A")
    b = Node("B")
    c = Node("C")
    nodes = [a, b, c]

    rejected = 0

    for i in range(TOTAL_EVENTS):
        if i % 50 == 0:
            event = forged_event(i)
        elif i % 200 == 0:
            event = downgrade_policy_event(i)
        else:
            event = legit_event(i)

        for node in nodes:
            if not node.apply_event(event):
                rejected += 1

    hashes = [n.state_hash for n in nodes]
    if len(set(hashes)) != 1:
        raise Exception("Divergence under zero-trust.")

    duration = time.perf_counter() - t0
    print("Rejected:", rejected)
    print("Final State Hash:", a.state_hash)
    print("Duration:", round(duration, 6), "seconds")
    print("Converged: ✔")

    return {
        "rejected": rejected,
        "state_hash": a.state_hash,
        "duration_s": round(duration, 6),
    }


if __name__ == "__main__":
    run_zero_trust_identity_attack()
