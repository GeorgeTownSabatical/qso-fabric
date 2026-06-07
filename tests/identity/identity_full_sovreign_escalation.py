from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Dict, List, Set


TOTAL_EVENTS = 40_000
SEED = 424242


def dhash(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def seeded(i: int, mod: int) -> int:
    return (i * 6364136223846793005 + SEED) % mod


# -------------------- Identity -------------------- #

@dataclass
class Identity:
    identity_id: str
    status: str = "active"
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []


# -------------------- Entanglement -------------------- #

@dataclass
class Entanglement:
    source: str
    target: str
    inert: bool = False


# -------------------- Node -------------------- #

class Node:

    def __init__(self, name: str):
        self.name = name
        self.identities: Dict[str, Identity] = {}
        self.entanglements: List[Entanglement] = []
        self.event_log: List[dict] = []
        self.seen_event_ids: Set[str] = set()
        self.last_logical_time = -1
        self.state_hash = ""

    # -------- Validation -------- #

    def validate_event(self, e: dict) -> bool:

        if e["event_id"] in self.seen_event_ids:
            return False

        if e["logical_time"] <= self.last_logical_time:
            return False

        if not e.get("signature_valid", False):
            return False

        if e["policy_version"] < 1:
            return False

        if e["type"] == "MUTATE":
            ident = self.identities.get(e["identity_id"])
            if ident is None or ident.status == "revoked":
                return False

        if e["type"] == "REVOKE":
            if e["identity_id"] not in self.identities:
                return False

        return True

    # -------- Apply -------- #

    def apply_event(self, e: dict):

        if not self.validate_event(e):
            return False

        self.event_log.append(e)
        self.seen_event_ids.add(e["event_id"])
        self.last_logical_time = e["logical_time"]
        self.state_hash = dhash(self.state_hash + dhash(str(e)))

        if e["type"] == "CREATE":
            self.identities[e["identity_id"]] = Identity(e["identity_id"])

        elif e["type"] == "MUTATE":
            self.identities[e["identity_id"]].roles.append(e["role"])

        elif e["type"] == "REVOKE":
            ident = self.identities[e["identity_id"]]
            ident.status = "revoked"
            # Inert entanglements
            for link in self.entanglements:
                if link.source == e["identity_id"]:
                    link.inert = True

        elif e["type"] == "REINSTATE":
            ident = self.identities[e["identity_id"]]
            ident.status = "active"
            for link in self.entanglements:
                if link.source == e["identity_id"]:
                    link.inert = False

        elif e["type"] == "ENTANGLE":
            self.entanglements.append(
                Entanglement(e["source"], e["target"], inert=False)
            )

        return True

    # -------- Snapshot -------- #

    def export_snapshot(self):
        return {
            "event_log": list(self.event_log),
            "state_hash": self.state_hash,
        }

    def strict_import(self, snapshot):
        # Strict archival validation against a shadow reducer:
        # no invalid historical event may exist in the imported chain.
        shadow_identities: Dict[str, Identity] = {}
        shadow_seen: Set[str] = set()
        shadow_last_time = -1

        for e in snapshot["event_log"]:
            if e["event_id"] in shadow_seen:
                raise Exception("Invalid event in archival history.")
            if e["logical_time"] <= shadow_last_time:
                raise Exception("Invalid event in archival history.")
            if not e.get("signature_valid", False):
                raise Exception("Invalid event in archival history.")
            if e["policy_version"] < 1:
                raise Exception("Invalid event in archival history.")

            if e["type"] == "MUTATE":
                ident = shadow_identities.get(e["identity_id"])
                if ident is None or ident.status == "revoked":
                    raise Exception("Invalid event in archival history.")

            if e["type"] == "REVOKE":
                if e["identity_id"] not in shadow_identities:
                    raise Exception("Invalid event in archival history.")

            if e["type"] == "REINSTATE":
                if e["identity_id"] not in shadow_identities:
                    raise Exception("Invalid event in archival history.")

            # Shadow apply
            if e["type"] == "CREATE":
                shadow_identities[e["identity_id"]] = Identity(e["identity_id"])
            elif e["type"] == "MUTATE":
                shadow_identities[e["identity_id"]].roles.append(e["role"])
            elif e["type"] == "REVOKE":
                shadow_identities[e["identity_id"]].status = "revoked"
            elif e["type"] == "REINSTATE":
                shadow_identities[e["identity_id"]].status = "active"

            shadow_seen.add(e["event_id"])
            shadow_last_time = e["logical_time"]

        for e in snapshot["event_log"]:
            self.apply_event(e)

        if self.state_hash != snapshot["state_hash"]:
            raise Exception("State hash mismatch after replay.")


# -------------------- Event Generators -------------------- #

def legit_event(i):
    return {
        "event_id": f"evt_{i}",
        "type": "CREATE" if i < 500 else "MUTATE",
        "identity_id": f"id_{seeded(i, 500)}",
        "role": f"role_{seeded(i, 20)}",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": True,
    }


def entangle_event(i):
    return {
        "event_id": f"ent_{i}",
        "type": "ENTANGLE",
        "source": f"id_{seeded(i, 500)}",
        "target": f"agent_{seeded(i, 100)}",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": True,
    }


def revoke_event(i):
    return {
        "event_id": f"rev_{i}",
        "type": "REVOKE",
        "identity_id": f"id_{seeded(i, 500)}",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": True,
    }


def reinstate_event(i):
    return {
        "event_id": f"rein_{i}",
        "type": "REINSTATE",
        "identity_id": f"id_{seeded(i, 500)}",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": True,
    }


def forged_event(i):
    return {
        "event_id": f"forged_{i}",
        "type": "MUTATE",
        "identity_id": f"id_{seeded(i, 500)}",
        "role": "admin",
        "logical_time": i,
        "policy_version": 1,
        "signature_valid": False,
    }


# -------------------- Full Escalation -------------------- #

def run_full_escalation():

    print("\n=== FULL SOVEREIGN ESCALATION ===")

    A = Node("A")
    B = Node("B")

    # Shared baseline
    for i in range(1000):
        e = legit_event(i)
        A.apply_event(e)
        B.apply_event(e)

    # Partition: B offline + adversarial pressure
    for i in range(1000, TOTAL_EVENTS):

        if i % 100 == 0:
            e = forged_event(i)
        elif i % 250 == 0:
            e = revoke_event(i)
        elif i % 400 == 0:
            e = reinstate_event(i)
        elif i % 150 == 0:
            e = entangle_event(i)
        else:
            e = legit_event(i)

        B.apply_event(e)

    snapshot = B.export_snapshot()

    A_import = Node("A_import")
    A_import.strict_import(snapshot)

    if A_import.state_hash != B.state_hash:
        raise Exception("Final divergence.")

    print("Final State Hash:", B.state_hash)
    print("Escalation Passed: ✔")
    print("Strict Archival Integrity: ✔")


if __name__ == "__main__":
    run_full_escalation()
