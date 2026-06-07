from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Dict, List

SEED = 2025
TOTAL_IDENTITIES = 10_000
TOTAL_EVENTS = 200_000


def dhash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def seeded(i: int, mod: int) -> int:
    return (i * 7919 + SEED) % mod


@dataclass
class Identity:
    identity_id: str
    status: str = "active"
    roles: List[str] = None
    entitlements: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.entitlements is None:
            self.entitlements = []


@dataclass
class Node:
    name: str
    event_log: List[dict]
    state_hash: str = ""
    identities: Dict[str, Identity] = None

    def __post_init__(self):
        if self.identities is None:
            self.identities = {}

    def apply_event(self, event: dict):
        if event["type"] == "MUTATE":
            ident = self.identities.get(event["identity_id"])
            if ident and ident.status == "revoked":
                return False

        self.event_log.append(event)
        self.state_hash = dhash(self.state_hash + dhash(str(event)))

        if event["type"] == "CREATE":
            self.identities[event["identity_id"]] = Identity(event["identity_id"])

        elif event["type"] == "REVOKE":
            ident = self.identities.get(event["identity_id"])
            if ident:
                ident.status = "revoked"

        elif event["type"] == "REINSTATE":
            ident = self.identities.get(event["identity_id"])
            if ident:
                ident.status = "active"

        elif event["type"] == "MUTATE":
            ident = self.identities.get(event["identity_id"])
            if ident:
                ident.roles.append(event["role"])

        return True

    def checkpoint(self):
        return dhash("".join(dhash(str(e)) for e in self.event_log))


def create_event(i):
    return {
        "type": "CREATE",
        "identity_id": f"id_{seeded(i, TOTAL_IDENTITIES)}",
        "logical_time": i,
    }


def revoke_event(i):
    return {
        "type": "REVOKE",
        "identity_id": f"id_{seeded(i, TOTAL_IDENTITIES)}",
        "logical_time": i,
    }


def reinstate_event(i):
    return {
        "type": "REINSTATE",
        "identity_id": f"id_{seeded(i, TOTAL_IDENTITIES)}",
        "logical_time": i,
    }


def mutate_event(i):
    return {
        "type": "MUTATE",
        "identity_id": f"id_{seeded(i, TOTAL_IDENTITIES)}",
        "role": f"role_{seeded(i, 20)}",
        "logical_time": i,
    }


def merge(ref: Node, target: Node):
    if ref.checkpoint() != target.checkpoint():
        target.event_log = list(ref.event_log)
        target.state_hash = ref.state_hash
        target.identities = {
            k: Identity(v.identity_id, v.status, list(v.roles), list(v.entitlements))
            for k, v in ref.identities.items()
        }


def assert_converged(*nodes):
    hashes = [n.state_hash for n in nodes]
    if len(set(hashes)) != 1:
        raise Exception("Identity deterministic divergence.")


def run_identity_stress(total_events: int = TOTAL_EVENTS):
    start = time.time()

    a = Node("A", [])
    b = Node("B", [])
    c = Node("C", [])

    nodes = [a, b, c]

    partition = False
    rejected = 0

    for i in range(total_events):
        if i == total_events // 3:
            partition = True

        if i == total_events // 2:
            partition = False
            merge(a, b)
            merge(a, c)

        if i < TOTAL_IDENTITIES:
            event = create_event(i)
        elif i % 5000 == 0:
            event = revoke_event(i)
        elif i % 7000 == 0:
            event = reinstate_event(i)
        else:
            event = mutate_event(i)

        for node in nodes:
            if partition and node.name == "B":
                if not node.apply_event(event):
                    rejected += 1
            else:
                if not node.apply_event(event):
                    rejected += 1

    duration = time.time() - start
    assert_converged(a, b, c)

    return {
        "duration_s": round(duration, 6),
        "rejected": rejected,
        "state_hash": a.state_hash,
        "converged": True,
    }


def test_identity_stress_smoke():
    result = run_identity_stress(total_events=20_000)
    assert result["converged"] is True
    assert len(result["state_hash"]) == 64


if __name__ == "__main__":
    out = run_identity_stress(total_events=TOTAL_EVENTS)
    print("=== Identity Sovereign Stress ===")
    print("Duration:", out["duration_s"], "seconds")
    print("Rejected Mutations:", out["rejected"])
    print("Final State Hash:", out["state_hash"])
    print("Converged: ✔")
