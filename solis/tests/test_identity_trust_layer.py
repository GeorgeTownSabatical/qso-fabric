from __future__ import annotations

from dataclasses import dataclass

from solis.identity.anchor.merkle import hash_leaf, merkle_root
from solis.identity.identity_object import IdentityService, IrisIdentityObject
from solis.identity.iris_hash import hash_iris_template
from solis.identity.pq_keys import generate_keypair, nist_primitives_available, sign, verify
from solis.identity.recovery_model import RecoveryPolicy, recovery_allowed
from solis.identity.zk.proof_adapter import generate_collapse_proof
from solis.identity.zk.verifier import verify_collapse_proof
from solis.physics.fixed_math import Fixed64


@dataclass
class _FakeQSO:
    store: dict[str, dict] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = {}

    def has(self, uri: str) -> bool:
        return uri in self.store

    def create(self, uri: str, schema: dict) -> dict:
        self.store.setdefault(uri, {"schema": schema, "state_layer": {}})
        return {"uri": uri}

    def patch(self, uri: str, delta: dict, *, actor: str, policy_version: str, node_id: str) -> dict:
        obj = self.store.setdefault(uri, {"schema": {}, "state_layer": {}})
        obj["state_layer"].update(delta)
        return {"uri": uri, "delta": delta, "actor": actor, "policy_version": policy_version, "node_id": node_id}

    def read(self, uri: str) -> dict:
        return self.store[uri]


def test_iris_hash_and_pq_deterministic() -> None:
    if not nist_primitives_available():
        import pytest

        pytest.skip("liboqs ML-KEM/ML-DSA primitives are not available in this environment")

    rec1 = hash_iris_template(b"0123456789abcdef0123456789abcdef", salt=b"salt-salt", rounds=4)
    rec2 = hash_iris_template(b"0123456789abcdef0123456789abcdef", salt=b"salt-salt", rounds=4)
    assert rec1 == rec2

    kp = generate_keypair(b"seed-seed-seed-seed")
    sig = sign(b"hello", kp.private_key)
    assert verify(b"hello", sig, kp.private_key)


def test_recovery_policy_deterministic() -> None:
    policy = RecoveryPolicy(required_devices=2, time_delay_sec=60)
    registered = {"dev-a", "dev-b", "dev-c"}
    approving = {"dev-a", "dev-b"}

    assert not recovery_allowed(
        registered_devices=registered,
        approving_devices=approving,
        policy=policy,
        elapsed_sec=59,
    )
    assert recovery_allowed(
        registered_devices=registered,
        approving_devices=approving,
        policy=policy,
        elapsed_sec=61,
    )


def test_identity_object_event_sourced() -> None:
    qso = _FakeQSO()
    service = IdentityService(qso=qso)  # type: ignore[arg-type]

    ident = IrisIdentityObject(
        iris_hash="abc123",
        pq_public_key="pk",
        recovery_policy={"required_devices": 2, "time_delay_sec": 60},
        device_registry=["dev-a"],
    )
    service.create_identity(ident)
    service.record_consent(iris_hash="abc123", consent_type="payments", granted=True)

    state = qso.read("qso://identity.iris.abc123")["state_layer"]
    assert state["iris_hash"] == "abc123"
    assert state["consent_ledger"][-1]["consent_type"] == "payments"


def test_zk_proof_adapter_and_anchor_merkle() -> None:
    proof = generate_collapse_proof(
        entropy=Fixed64.from_str("0.2"),
        magnetic=Fixed64.from_str("0.8"),
        fusion=Fixed64.from_str("0.7"),
        threshold=Fixed64.from_str("0.5"),
    )
    assert verify_collapse_proof(proof)

    leaves = [hash_leaf("a"), hash_leaf("b")]
    root1 = merkle_root(leaves)
    root2 = merkle_root(leaves)
    assert root1 == root2
