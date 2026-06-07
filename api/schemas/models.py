from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field
from solis.schemas import SCHEMA_VERSION


class SyncMode(str, Enum):
    PUSH = "push"
    PULL = "pull"
    BIDIRECTIONAL = "bidirectional"


class QSOEvent(BaseModel):
    schema_version: str = SCHEMA_VERSION
    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    object_uri: str
    delta: Dict[str, Any]
    signature: str
    policy_version: str
    node_id: str = "local"


class PolicyMutationEvent(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str
    node_id: str
    from_version: str
    to_version: str
    policy_delta: Dict[str, Any]
    signature: str


class EntanglementLink(BaseModel):
    source_uri: str
    target_uri: str
    relationship: str
    strength: float = 1.0
    sync_mode: SyncMode = SyncMode.PUSH
    latency_target_ms: int = 100
    bidirectional: bool = False


class SnapshotManifest(BaseModel):
    uri: str
    event_count: int
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    compression: str = "gzip"
    encrypted: bool = False
    policy_version: str = "v1"
    runtime_version: str = "qso-fabric/0.1.0"
    event_hash_checkpoint: str = ""


class QSOObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    uri: str
    schema_def: Dict[str, Any] = Field(alias="schema")
    identity_layer: Dict[str, Any]
    state_layer: Dict[str, Any]
    timeline_layer: List[QSOEvent]
    entanglement_layer: List[EntanglementLink]
    snapshot_layer: Dict[str, Any] = Field(default_factory=dict)


class PatchRequest(BaseModel):
    uri: str
    delta: Dict[str, Any]
    actor: str
    policy_version: str = "v1"


class QSOCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    uri: str
    schema_def: Dict[str, Any] = Field(alias="schema")
    actor: str = "system"


class QSOReadResponse(BaseModel):
    qso: QSOObject


class TimelineResponse(BaseModel):
    uri: str
    events: List[QSOEvent]


class AuditQuery(BaseModel):
    uri: Optional[str] = None
    actor: Optional[str] = None
    since: Optional[datetime] = None


class MetaMetrics(BaseModel):
    latency_ms: float
    throughput: float
    reward_signal: float
    error_rate: float
    policy_performance: float


class TransportMode(str, Enum):
    DIRECT = "direct"
    VPN = "vpn"
    TOR = "tor"


class TransportState(BaseModel):
    mode: TransportMode
    node_id: str = "local"
    latency_ms: float = 0.0
    throughput_mbps: float = 0.0
    risk_profile: str = "balanced"
    health_status: str = "unknown"
    policy_version: str = "v1"
    exit_fingerprint: str = ""


class TransportModeMutationRequest(BaseModel):
    mode: TransportMode
    actor: str = "transport-controller"
    policy_version: str = "v1"
    node_id: str = "local"
