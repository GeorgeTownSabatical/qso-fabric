"""Deterministic render-scene projections for cognitive QSO fabrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.quantum.fabric.cognition import (
    AttentionField,
    CognitiveState,
    IntentSurface,
    MemoryTrace,
    ReasoningPath,
    UncertaintyField,
)
from services.quantum.fabric.fabric import QSOFabric


@dataclass(frozen=True, slots=True)
class RenderSceneObject:
    id: str
    ref: str
    object_type: str
    label: str
    position: list[float]
    scale: float
    intensity: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ref": self.ref,
            "object_type": self.object_type,
            "label": self.label,
            "position": [float(item) for item in self.position],
            "scale": self.scale,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RenderSceneObject":
        return cls(
            id=str(data["id"]),
            ref=str(data["ref"]),
            object_type=str(data["object_type"]),
            label=str(data.get("label", "")),
            position=[float(item) for item in data.get("position", [0.0, 0.0, 0.0])],
            scale=float(data.get("scale", 1.0)),
            intensity=float(data.get("intensity", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class RenderSceneEdge:
    id: str
    source_ref: str
    target_ref: str
    relationship: str
    strength: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_ref": self.source_ref,
            "target_ref": self.target_ref,
            "relationship": self.relationship,
            "strength": self.strength,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RenderSceneEdge":
        return cls(
            id=str(data["id"]),
            source_ref=str(data["source_ref"]),
            target_ref=str(data["target_ref"]),
            relationship=str(data["relationship"]),
            strength=float(data.get("strength", 0.0)),
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class RenderSceneField:
    id: str
    target_ref: str
    field_type: str
    magnitude: float
    radius: float
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "target_ref": self.target_ref,
            "field_type": self.field_type,
            "magnitude": self.magnitude,
            "radius": self.radius,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "RenderSceneField":
        return cls(
            id=str(data["id"]),
            target_ref=str(data["target_ref"]),
            field_type=str(data["field_type"]),
            magnitude=float(data.get("magnitude", 0.0)),
            radius=float(data.get("radius", 1.0)),
            confidence=float(data.get("confidence", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class CognitiveSceneProjection:
    scene_id: str
    fabric_id: str
    objects: list[RenderSceneObject]
    edges: list[RenderSceneEdge]
    fields: list[RenderSceneField]
    camera_hints: dict[str, Any] = field(default_factory=dict)
    interaction_hints: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "fabric_id": self.fabric_id,
            "objects": [item.to_json_dict() for item in sorted(self.objects, key=lambda item: item.id)],
            "edges": [item.to_json_dict() for item in sorted(self.edges, key=lambda item: item.id)],
            "fields": [item.to_json_dict() for item in sorted(self.fields, key=lambda item: item.id)],
            "camera_hints": dict(self.camera_hints),
            "interaction_hints": dict(self.interaction_hints),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "CognitiveSceneProjection":
        return cls(
            scene_id=str(data["scene_id"]),
            fabric_id=str(data["fabric_id"]),
            objects=[RenderSceneObject.from_json_dict(dict(item)) for item in data.get("objects", [])],
            edges=[RenderSceneEdge.from_json_dict(dict(item)) for item in data.get("edges", [])],
            fields=[RenderSceneField.from_json_dict(dict(item)) for item in data.get("fields", [])],
            camera_hints=dict(data.get("camera_hints", {})),
            interaction_hints=dict(data.get("interaction_hints", {})),
            metadata=dict(data.get("metadata", {})),
        )


def project_cognitive_scene(
    fabric: QSOFabric,
    *,
    cognitive_states: list[CognitiveState] | None = None,
    attention_fields: list[AttentionField] | None = None,
    intent_surfaces: list[IntentSurface] | None = None,
    memory_traces: list[MemoryTrace] | None = None,
    reasoning_paths: list[ReasoningPath] | None = None,
    uncertainty_fields: list[UncertaintyField] | None = None,
    scene_id: str | None = None,
) -> dict[str, Any]:
    """Project fabric cognition into a deterministic VR-friendly scene contract."""

    states = sorted(cognitive_states or [], key=lambda item: item.id)
    attention = sorted(attention_fields or [], key=lambda item: item.id)
    intents = sorted(intent_surfaces or [], key=lambda item: item.id)
    memories = sorted(memory_traces or [], key=lambda item: item.id)
    paths = sorted(reasoning_paths or [], key=lambda item: item.id)
    uncertainties = sorted(uncertainty_fields or [], key=lambda item: item.id)

    objects = _fabric_objects(fabric)
    objects.extend(_cognitive_objects(states, start_index=len(objects)))
    edges = _intent_edges(intents) + _memory_edges(memories) + _reasoning_edges(paths)
    fields = _attention_render_fields(attention) + _intent_render_fields(intents) + _uncertainty_render_fields(uncertainties)

    projection = CognitiveSceneProjection(
        scene_id=scene_id or f"scene.{fabric.id}",
        fabric_id=fabric.id,
        objects=objects,
        edges=edges,
        fields=fields,
        camera_hints={
            "target_ref": _camera_target(fabric, states),
            "layout": "deterministic_line",
            "units": "fabric_space",
        },
        interaction_hints={
            "selectable_refs": sorted({item.ref for item in objects}),
            "edge_relationships": sorted({item.relationship for item in edges}),
            "field_types": sorted({item.field_type for item in fields}),
        },
        metadata={
            "object_count": len(objects),
            "edge_count": len(edges),
            "field_count": len(fields),
        },
    )
    return projection.to_json_dict()


def _fabric_objects(fabric: QSOFabric) -> list[RenderSceneObject]:
    objects = []
    for index, (_, patch) in enumerate(sorted(fabric.patches.items())):
        objects.append(
            RenderSceneObject(
                id=f"render.object.{patch.id}",
                ref=patch.id,
                object_type="patch",
                label=patch.domain,
                position=[float(index) * 2.0, 0.0, 0.0],
                scale=1.0,
                intensity=0.5,
                confidence=1.0,
                metadata={"domain": patch.domain, "state_ref": patch.state.id},
            )
        )
    return sorted(objects, key=lambda item: item.id)


def _cognitive_objects(states: list[CognitiveState], *, start_index: int) -> list[RenderSceneObject]:
    objects = []
    for offset, state in enumerate(states):
        intensity = max(0.0, state.activation) * max(0.0, state.confidence)
        objects.append(
            RenderSceneObject(
                id=f"render.object.{state.id}",
                ref=state.state_ref,
                object_type="cognitive_state",
                label=state.cognitive_role,
                position=[float(start_index + offset) * 2.0, 1.5, 0.0],
                scale=1.0 + max(0.0, state.activation),
                intensity=intensity,
                confidence=state.confidence,
                metadata={"cognitive_state_id": state.id, "source_refs": list(state.source_refs)},
            )
        )
    return objects


def _intent_edges(intents: list[IntentSurface]) -> list[RenderSceneEdge]:
    edges = []
    for intent in intents:
        for target_ref in sorted(intent.target_refs):
            edges.append(
                RenderSceneEdge(
                    id=f"render.edge.{intent.id}.{target_ref}",
                    source_ref=intent.intent_ref,
                    target_ref=target_ref,
                    relationship="intent_surface",
                    strength=max(0.0, intent.priority) * max(0.0, intent.stability),
                    confidence=intent.confidence,
                    metadata={"intent_surface_id": intent.id},
                )
            )
    return edges


def _memory_edges(memories: list[MemoryTrace]) -> list[RenderSceneEdge]:
    edges = []
    for memory in memories:
        for left, right in zip(memory.patch_refs, memory.patch_refs[1:]):
            edges.append(
                RenderSceneEdge(
                    id=f"render.edge.{memory.id}.{left}.{right}",
                    source_ref=left,
                    target_ref=right,
                    relationship="memory_trace",
                    strength=max(0.0, memory.strength) * max(0.0, memory.recency),
                    confidence=memory.strength,
                    metadata={"memory_ref": memory.memory_ref, "source_refs": list(memory.source_refs)},
                )
            )
    return edges


def _reasoning_edges(paths: list[ReasoningPath]) -> list[RenderSceneEdge]:
    edges = []
    for path in paths:
        penalty = max(0.0, path.cost)
        strength = max(0.0, path.confidence) / (1.0 + penalty)
        for left, right in zip(path.path_refs, path.path_refs[1:]):
            edges.append(
                RenderSceneEdge(
                    id=f"render.edge.{path.id}.{left}.{right}",
                    source_ref=left,
                    target_ref=right,
                    relationship=f"reasoning_path.{path.path_type}",
                    strength=strength,
                    confidence=path.confidence,
                    metadata={"reasoning_path_id": path.id, "cost": path.cost},
                )
            )
    return edges


def _attention_render_fields(attention: list[AttentionField]) -> list[RenderSceneField]:
    return [
        RenderSceneField(
            id=f"render.field.{item.id}",
            target_ref=item.target_ref,
            field_type="attention",
            magnitude=max(0.0, item.intensity) * max(0.0, item.focus),
            radius=item.radius,
            confidence=item.focus,
            metadata={"source_refs": list(item.source_refs)},
        )
        for item in attention
    ]


def _intent_render_fields(intents: list[IntentSurface]) -> list[RenderSceneField]:
    return [
        RenderSceneField(
            id=f"render.field.{item.id}",
            target_ref=item.intent_ref,
            field_type="intent",
            magnitude=max(0.0, item.priority) * max(0.0, item.confidence),
            radius=1.0 + max(0.0, item.stability),
            confidence=item.confidence,
            metadata={"target_refs": list(item.target_refs)},
        )
        for item in intents
    ]


def _uncertainty_render_fields(uncertainties: list[UncertaintyField]) -> list[RenderSceneField]:
    return [
        RenderSceneField(
            id=f"render.field.{item.id}",
            target_ref=item.target_ref,
            field_type="uncertainty",
            magnitude=max(0.0, item.uncertainty) + max(0.0, item.entropy),
            radius=1.0 + max(0.0, item.entropy),
            confidence=1.0 - max(0.0, item.uncertainty),
            metadata={"source_refs": list(item.source_refs)},
        )
        for item in uncertainties
    ]


def _camera_target(fabric: QSOFabric, states: list[CognitiveState]) -> str | None:
    if states:
        strongest = max(states, key=lambda item: (item.activation * item.confidence, item.id))
        return strongest.state_ref
    if fabric.patches:
        return sorted(fabric.patches)[0]
    return None
