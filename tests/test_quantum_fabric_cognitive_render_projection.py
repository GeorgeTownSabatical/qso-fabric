from __future__ import annotations

import pytest

from services.quantum.fabric import (
    AttentionField,
    CognitiveSceneProjection,
    CognitiveState,
    IntentSurface,
    MemoryTrace,
    Patch,
    QSOFabric,
    QuantumStateObject,
    ReasoningPath,
    RenderSceneEdge,
    RenderSceneField,
    RenderSceneObject,
    UncertaintyField,
    project_cognitive_scene,
)


def test_cognitive_primitives_round_trip_json() -> None:
    state = CognitiveState(
        id="cognitive.state.1",
        state_ref="state.memory",
        cognitive_role="working_memory",
        activation=0.8,
        confidence=0.7,
        source_refs=["observation.1"],
        metadata={"kind": "recall"},
    )
    attention = AttentionField(
        id="attention.1",
        target_ref="patch.memory",
        intensity=0.9,
        focus=0.8,
        radius=2.5,
        source_refs=["intent.1"],
        metadata={"mode": "inspect"},
    )
    intent = IntentSurface(
        id="intent.surface.1",
        intent_ref="intent.solve",
        priority=0.9,
        confidence=0.75,
        stability=0.6,
        target_refs=["patch.memory", "patch.task"],
        metadata={"goal": "answer"},
    )
    memory = MemoryTrace(
        id="memory.trace.1",
        memory_ref="memory.prior",
        patch_refs=["patch.memory", "patch.task"],
        strength=0.8,
        recency=0.6,
        source_refs=["recall.1"],
        metadata={"path": "short"},
    )
    path = ReasoningPath(
        id="reasoning.path.1",
        path_refs=["patch.memory", "patch.task", "patch.projection"],
        path_type="hypothesis",
        confidence=0.7,
        cost=0.25,
        metadata={"step_count": 3},
    )
    uncertainty = UncertaintyField(
        id="uncertainty.1",
        target_ref="patch.projection",
        uncertainty=0.4,
        entropy=0.3,
        source_refs=["projection.1"],
        metadata={"needs": "evidence"},
    )

    assert CognitiveState.from_json_dict(state.to_json_dict()) == state
    assert AttentionField.from_json_dict(attention.to_json_dict()) == attention
    assert IntentSurface.from_json_dict(intent.to_json_dict()) == intent
    assert MemoryTrace.from_json_dict(memory.to_json_dict()) == memory
    assert ReasoningPath.from_json_dict(path.to_json_dict()) == path
    assert UncertaintyField.from_json_dict(uncertainty.to_json_dict()) == uncertainty


def test_render_scene_primitives_round_trip_json() -> None:
    obj = RenderSceneObject(
        id="render.object.patch.memory",
        ref="patch.memory",
        object_type="patch",
        label="memory",
        position=[0.0, 1.0, 2.0],
        scale=1.2,
        intensity=0.8,
        confidence=0.9,
        metadata={"domain": "memory"},
    )
    edge = RenderSceneEdge(
        id="render.edge.1",
        source_ref="patch.memory",
        target_ref="patch.task",
        relationship="memory_trace",
        strength=0.5,
        confidence=0.8,
        metadata={"trace": "memory.1"},
    )
    field = RenderSceneField(
        id="render.field.1",
        target_ref="patch.memory",
        field_type="attention",
        magnitude=0.72,
        radius=2.0,
        confidence=0.8,
        metadata={"source_refs": ["intent.1"]},
    )
    scene = CognitiveSceneProjection(
        scene_id="scene.fabric",
        fabric_id="fabric.cognition",
        objects=[obj],
        edges=[edge],
        fields=[field],
        camera_hints={"target_ref": "patch.memory"},
        interaction_hints={"selectable_refs": ["patch.memory"]},
        metadata={"object_count": 1},
    )

    assert RenderSceneObject.from_json_dict(obj.to_json_dict()) == obj
    assert RenderSceneEdge.from_json_dict(edge.to_json_dict()) == edge
    assert RenderSceneField.from_json_dict(field.to_json_dict()) == field
    assert CognitiveSceneProjection.from_json_dict(scene.to_json_dict()) == scene


def test_project_cognitive_scene_is_deterministic() -> None:
    fabric = _fabric()
    kwargs = _projection_inputs()

    first = project_cognitive_scene(fabric, scene_id="scene.test", **kwargs)
    second = project_cognitive_scene(fabric, scene_id="scene.test", **kwargs)

    assert first == second
    assert first["scene_id"] == "scene.test"
    assert first["fabric_id"] == "fabric.cognition"
    assert first["metadata"] == {"object_count": 5, "edge_count": 5, "field_count": 3}


def test_cognitive_signal_shapes_render_scene_contract() -> None:
    fabric = _fabric()
    scene = project_cognitive_scene(fabric, scene_id="scene.test", **_projection_inputs())

    objects_by_id = {item["id"]: item for item in scene["objects"]}
    edges_by_relationship = {item["relationship"] for item in scene["edges"]}
    fields_by_type = {item["field_type"]: item for item in scene["fields"]}

    assert objects_by_id["render.object.cognitive.working"]["object_type"] == "cognitive_state"
    assert objects_by_id["render.object.cognitive.working"]["intensity"] == 0.7200000000000001
    assert edges_by_relationship == {"intent_surface", "memory_trace", "reasoning_path.hypothesis"}
    assert fields_by_type["attention"]["magnitude"] == pytest.approx(0.72)
    assert fields_by_type["intent"]["magnitude"] == pytest.approx(0.675)
    assert fields_by_type["uncertainty"]["magnitude"] == pytest.approx(0.7)
    assert scene["camera_hints"]["target_ref"] == "state.memory"
    assert "patch.memory" in scene["interaction_hints"]["selectable_refs"]


def test_project_cognitive_scene_does_not_mutate_fabric() -> None:
    fabric = _fabric()
    before = fabric.to_json_dict()

    scene = project_cognitive_scene(fabric, scene_id="scene.test", **_projection_inputs())

    assert scene["fabric_id"] == "fabric.cognition"
    assert fabric.to_json_dict() == before


def _projection_inputs() -> dict[str, object]:
    return {
        "cognitive_states": [
            CognitiveState(
                id="cognitive.working",
                state_ref="state.memory",
                cognitive_role="working_memory",
                activation=0.9,
                confidence=0.8,
                source_refs=["observation.1"],
                metadata={},
            ),
            CognitiveState(
                id="cognitive.goal",
                state_ref="state.task",
                cognitive_role="goal_context",
                activation=0.7,
                confidence=0.8,
                source_refs=["intent.1"],
                metadata={},
            ),
        ],
        "attention_fields": [
            AttentionField(id="attention.focus", target_ref="patch.memory", intensity=0.9, focus=0.8, radius=2.0, source_refs=["intent.1"], metadata={}),
        ],
        "intent_surfaces": [
            IntentSurface(id="intent.surface", intent_ref="intent.solve", priority=0.9, confidence=0.75, stability=0.6, target_refs=["patch.memory", "patch.task"], metadata={}),
        ],
        "memory_traces": [
            MemoryTrace(id="memory.trace", memory_ref="memory.prior", patch_refs=["patch.memory", "patch.task"], strength=0.8, recency=0.6, source_refs=["recall.1"], metadata={}),
        ],
        "reasoning_paths": [
            ReasoningPath(id="reasoning.path", path_refs=["patch.memory", "patch.task", "patch.projection"], path_type="hypothesis", confidence=0.7, cost=0.25, metadata={}),
        ],
        "uncertainty_fields": [
            UncertaintyField(id="uncertainty.projection", target_ref="patch.projection", uncertainty=0.4, entropy=0.3, source_refs=["projection.1"], metadata={}),
        ],
    }


def _fabric() -> QSOFabric:
    fabric = QSOFabric(id="fabric.cognition")
    for patch_id, state_id, domain, vector in (
        ("patch.memory", "state.memory", "memory", [1 + 0j, 0j]),
        ("patch.task", "state.task", "task", [0j, 1 + 0j]),
        ("patch.projection", "state.projection", "projection", [1 + 0j, 1 + 0j]),
    ):
        fabric.add_patch(
            Patch(
                id=patch_id,
                domain=domain,
                basis=["|0>", "|1>"],
                state=QuantumStateObject(id=state_id, vector=vector),
            )
        )
    return fabric
