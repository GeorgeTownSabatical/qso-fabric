from __future__ import annotations

import hashlib
import json
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from core.entanglement.dag_validator import rejects_cycle


def deterministic_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def seeded_choice(index: int, modulo: int, seed: int) -> int:
    return (index * 9301 + 49297 + seed) % modulo


def canonical_payload(event: Dict[str, Any]) -> str:
    payload = {k: v for k, v in event.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sign_event(event: Dict[str, Any], secret: str) -> str:
    return deterministic_hash(f"{canonical_payload(event)}|{secret}")


def verify_event(event: Dict[str, Any], secret: str) -> bool:
    expected = sign_event(event, secret)
    return expected == event.get("signature", "")


def event_key(event: Dict[str, Any]) -> Tuple[int, str]:
    return int(event["logical_time"]), str(event["event_id"])


@dataclass
class MetricsCollector:
    started_at: float = 0.0
    finished_at: float = 0.0
    peak_memory_bytes: int = 0
    checkpoint_ms: float = 0.0
    reconcile_ms: float = 0.0

    def start(self) -> None:
        tracemalloc.start()
        self.started_at = time.perf_counter()

    def stop(self) -> None:
        self.finished_at = time.perf_counter()
        _, peak = tracemalloc.get_traced_memory()
        self.peak_memory_bytes = peak
        tracemalloc.stop()

    @property
    def duration_s(self) -> float:
        return round(self.finished_at - self.started_at, 6)


@dataclass
class FederationNode:
    name: str
    role: str
    secret: str
    trusted_actors: set[str] = field(default_factory=set)
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    rejected_events: List[Dict[str, Any]] = field(default_factory=list)
    state: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    policy_version: int = 1
    policy_activation_index: int = 0
    entanglement_graph: Dict[str, List[str]] = field(default_factory=dict)
    policy_by_time: Dict[int, int] = field(default_factory=dict)

    def _apply_delta(self, event: Dict[str, Any]) -> None:
        uri = str(event["object_uri"])
        delta = dict(event.get("delta", {}))
        if uri not in self.state:
            self.state[uri] = {}
        self.state[uri].update(delta)

    def _apply_measure(self, event: Dict[str, Any]) -> None:
        uri = str(event["object_uri"])
        rule = str(event.get("collapse_rule", "parity"))
        if uri not in self.state:
            self.state[uri] = {"value": 0}
        base = int(self.state[uri].get("value", 0))
        t = int(event["logical_time"])

        if rule == "parity":
            self.state[uri]["value"] = (base + t) % 2
        else:
            self.state[uri]["value"] = (base + (t % 7)) % 11

    def _apply_entangle(self, event: Dict[str, Any]) -> bool:
        src = str(event["source_uri"])
        tgt = str(event["target_uri"])

        self.entanglement_graph.setdefault(src, [])
        self.entanglement_graph.setdefault(tgt, [])

        if rejects_cycle(self.entanglement_graph, src, tgt):
            return False

        if tgt not in self.entanglement_graph[src]:
            self.entanglement_graph[src].append(tgt)
        return True

    def _apply_detangle(self, event: Dict[str, Any]) -> None:
        src = str(event["source_uri"])
        tgt = str(event["target_uri"])
        if src in self.entanglement_graph:
            self.entanglement_graph[src] = [x for x in self.entanglement_graph[src] if x != tgt]

    def _apply_event_internal(self, event: Dict[str, Any], strict: bool = True, append_log: bool = True) -> bool:
        actor = str(event["actor"])
        if self.trusted_actors and actor not in self.trusted_actors:
            self.rejected_events.append(event)
            return False

        if not verify_event(event, self.secret):
            self.rejected_events.append(event)
            if strict:
                return False

        etype = str(event["type"])
        e_policy = int(event["policy_version"])

        if etype != "POLICY" and e_policy != self.policy_version:
            self.rejected_events.append(event)
            return False

        if etype == "POLICY":
            next_version = int(event["next_policy_version"])
            activation_index = int(event["activation_index"])
            logical_time = int(event["logical_time"])

            existing = self.policy_by_time.get(logical_time)
            if existing is not None and existing != next_version:
                self.rejected_events.append(event)
                return False
            self.policy_by_time[logical_time] = next_version

            if next_version <= self.policy_version:
                self.rejected_events.append(event)
                return False

            self.policy_version = next_version
            self.policy_activation_index = activation_index

        elif etype == "DELTA":
            self._apply_delta(event)

        elif etype == "MEASURE":
            self._apply_measure(event)

        elif etype == "ENTANGLE":
            if not self._apply_entangle(event):
                self.rejected_events.append(event)
                return False

        elif etype == "DETANGLE":
            self._apply_detangle(event)

        if append_log:
            self.event_log.append(event)
        return True

    def apply_event(self, event: Dict[str, Any], strict: bool = True) -> bool:
        return self._apply_event_internal(event, strict=strict, append_log=True)

    def replay(self) -> None:
        events = sorted(self.event_log, key=event_key)
        saved_policy = self.policy_version

        self.event_log = list(events)
        self.state = {}
        self.entanglement_graph = {}
        self.policy_version = 1
        self.policy_activation_index = 0
        self.policy_by_time = {}
        self.rejected_events = []

        for event in events:
            self._apply_event_internal(event, strict=True, append_log=False)

        self.policy_version = max(self.policy_version, saved_policy)

    def event_hash_chain(self) -> str:
        h = ""
        for event in sorted(self.event_log, key=event_key):
            h = deterministic_hash(h + deterministic_hash(canonical_payload(event)))
        return h

    def state_hash(self) -> str:
        return deterministic_hash(json.dumps(self.state, sort_keys=True, separators=(",", ":")))

    def entanglement_hash(self) -> str:
        canon = {k: sorted(v) for k, v in sorted(self.entanglement_graph.items())}
        return deterministic_hash(json.dumps(canon, sort_keys=True, separators=(",", ":")))

    def snapshot_hash(self) -> str:
        payload = {
            "state_hash": self.state_hash(),
            "event_hash_chain": self.event_hash_chain(),
            "policy_version": self.policy_version,
            "entanglement_hash": self.entanglement_hash(),
        }
        return deterministic_hash(json.dumps(payload, sort_keys=True, separators=(",", ":")))


class SyntheticEventGenerator:
    def __init__(self, seed: int, secret: str, qso_per_ns: int = 20) -> None:
        self.seed = seed
        self.secret = secret
        self.qso_per_ns = qso_per_ns

    def _event_base(self, event_id: str, logical_time: int, actor: str, policy_version: int) -> Dict[str, Any]:
        return {
            "event_id": event_id,
            "logical_time": logical_time,
            "actor": actor,
            "policy_version": policy_version,
            "node_id": actor,
        }

    def normal_event(self, i: int, policy_version: int, actor: str = "node://A") -> Dict[str, Any]:
        ns = ["ai", "vr", "identity"][seeded_choice(i, 3, self.seed)]
        obj = seeded_choice(i, self.qso_per_ns, self.seed)
        event = {
            **self._event_base(f"{i:09d}-delta", i, actor, policy_version),
            "type": "DELTA",
            "object_uri": f"qso://{ns}.obj.{obj}",
            "delta": {"value": i},
        }
        event["signature"] = sign_event(event, self.secret)
        return event

    def measure_event(self, i: int, policy_version: int, actor: str = "node://A") -> Dict[str, Any]:
        target = seeded_choice(i, self.qso_per_ns, self.seed)
        event = {
            **self._event_base(f"{i:09d}-measure", i, actor, policy_version),
            "type": "MEASURE",
            "object_uri": f"qso://ai.obj.{target}",
            "collapse_rule": "parity",
            "delta": {},
        }
        event["signature"] = sign_event(event, self.secret)
        return event

    def policy_event(self, i: int, current_policy_version: int, actor: str = "meta://gdml", jump: int = 1) -> Dict[str, Any]:
        next_version = current_policy_version + jump
        event = {
            **self._event_base(f"{i:09d}-policy-v{next_version}", i, actor, current_policy_version),
            "type": "POLICY",
            "object_uri": "qso://policy.global",
            "next_policy_version": next_version,
            "activation_index": i,
            "delta": {"mode": "stress", "version": f"v{next_version}"},
        }
        event["signature"] = sign_event(event, self.secret)
        return event

    def entangle_event(self, i: int, policy_version: int, actor: str = "node://A") -> Dict[str, Any]:
        src = seeded_choice(i, self.qso_per_ns, self.seed)
        tgt = seeded_choice(i + 1, self.qso_per_ns, self.seed)
        event = {
            **self._event_base(f"{i:09d}-entangle", i, actor, policy_version),
            "type": "ENTANGLE",
            "source_uri": f"qso://ai.obj.{src}",
            "target_uri": f"qso://vr.obj.{tgt}",
            "object_uri": f"qso://ai.obj.{src}",
            "delta": {},
        }
        event["signature"] = sign_event(event, self.secret)
        return event


class PolicyChurnEngine:
    def __init__(self, interval: int) -> None:
        self.interval = interval

    def should_emit(self, i: int) -> bool:
        return i != 0 and i % self.interval == 0


class PartitionSimulator:
    def __init__(self, start: int, duration: int, partitioned_node: str) -> None:
        self.start = start
        self.end = start + duration
        self.partitioned_node = partitioned_node

    def is_partitioned(self, i: int, node_name: str) -> bool:
        return self.start <= i < self.end and node_name == self.partitioned_node


class ReconciliationValidator:
    @staticmethod
    def merge_logs(base: List[Dict[str, Any]], other: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_id: Dict[str, Dict[str, Any]] = {}
        for event in base + other:
            by_id[event["event_id"]] = event
        return sorted(by_id.values(), key=event_key)

    @staticmethod
    def reconcile_to_reference(reference: FederationNode, target: FederationNode) -> float:
        t0 = time.perf_counter()
        merged = ReconciliationValidator.merge_logs(reference.event_log, target.event_log)
        target.event_log = merged
        target.replay()
        return (time.perf_counter() - t0) * 1000.0

    @staticmethod
    def reconcile_cluster(nodes: List[FederationNode]) -> float:
        t0 = time.perf_counter()
        merged: List[Dict[str, Any]] = []
        for node in nodes:
            merged = ReconciliationValidator.merge_logs(merged, node.event_log)
        for node in nodes:
            node.event_log = list(merged)
            node.replay()
        return (time.perf_counter() - t0) * 1000.0


class DeterminismAsserter:
    @staticmethod
    def assert_converged(nodes: List[FederationNode]) -> None:
        chains = {n.event_hash_chain() for n in nodes}
        states = {n.state_hash() for n in nodes}
        ent = {n.entanglement_hash() for n in nodes}
        policy = {n.policy_version for n in nodes}
        snaps = {n.snapshot_hash() for n in nodes}

        if len(chains) != 1:
            raise AssertionError("event hash chain mismatch")
        if len(states) != 1:
            raise AssertionError("state hash mismatch")
        if len(ent) != 1:
            raise AssertionError("entanglement hash mismatch")
        if len(policy) != 1:
            raise AssertionError("active policy version mismatch")
        if len(snaps) != 1:
            raise AssertionError("snapshot hash mismatch")


@dataclass
class StressReport:
    phase: str
    total_events: int
    duration_s: float
    peak_memory_bytes: int
    reconcile_ms: float
    event_hash_chain: str
    state_hash: str
    entanglement_hash: str
    policy_version: int
    snapshot_hash: str
    rejected_events: int


def run_phase(
    phase: str,
    total_events: int,
    policy_churn_interval: int,
    measure_interval: int,
    partition_start: int,
    partition_duration: int,
    seed: int,
    entangle_every: int = 0,
    policy_conflict_at: int | None = None,
) -> StressReport:
    secret = "stress-secret"
    trusted = {"node://A", "node://B", "node://C", "meta://gdml"}

    nodes = {
        "A": FederationNode("A", "standard", secret, trusted_actors=set(trusted)),
        "B": FederationNode("B", "standard", secret, trusted_actors=set(trusted)),
        "C": FederationNode("C", "anchor", secret, trusted_actors=set(trusted)),
        "D": FederationNode("D", "observer", secret, trusted_actors=set(trusted)),
    }

    generator = SyntheticEventGenerator(seed=seed, secret=secret, qso_per_ns=20)
    churn = PolicyChurnEngine(policy_churn_interval)
    partition = PartitionSimulator(partition_start, partition_duration, partitioned_node="B")
    metrics = MetricsCollector()
    metrics.start()

    policy_version = 1

    for i in range(total_events):
        if churn.should_emit(i):
            jump = 1
            if policy_conflict_at is not None and i == policy_conflict_at:
                jump = 5
            event = generator.policy_event(i, current_policy_version=policy_version, jump=jump)
            policy_version = int(event["next_policy_version"])
        elif i != 0 and i % measure_interval == 0:
            event = generator.measure_event(i, policy_version=policy_version)
        elif entangle_every > 0 and i != 0 and i % entangle_every == 0:
            event = generator.entangle_event(i, policy_version=policy_version)
        else:
            event = generator.normal_event(i, policy_version=policy_version)

        # connected cluster emits canonical event from A/C
        for name in ("A", "C"):
            nodes[name].apply_event(event, strict=True)

        # partitioned B: independent deterministic stream while isolated
        if partition.is_partitioned(i, "B"):
            b_event = generator.normal_event(i, policy_version=nodes["B"].policy_version, actor="node://B")
            nodes["B"].apply_event(b_event, strict=True)
        else:
            nodes["B"].apply_event(event, strict=True)

    # deterministic cluster reconciliation
    rec_ms = ReconciliationValidator.reconcile_cluster([nodes["A"], nodes["B"], nodes["C"]])

    # observer verifies by consuming canonical chain from anchor C
    nodes["D"].event_log = list(nodes["C"].event_log)
    nodes["D"].replay()

    metrics.reconcile_ms = round(rec_ms, 3)
    metrics.stop()

    DeterminismAsserter.assert_converged([nodes["A"], nodes["B"], nodes["C"], nodes["D"]])

    ref = nodes["A"]
    rejected_total = sum(len(n.rejected_events) for n in nodes.values())

    return StressReport(
        phase=phase,
        total_events=total_events,
        duration_s=metrics.duration_s,
        peak_memory_bytes=metrics.peak_memory_bytes,
        reconcile_ms=metrics.reconcile_ms,
        event_hash_chain=ref.event_hash_chain(),
        state_hash=ref.state_hash(),
        entanglement_hash=ref.entanglement_hash(),
        policy_version=ref.policy_version,
        snapshot_hash=ref.snapshot_hash(),
        rejected_events=rejected_total,
    )
