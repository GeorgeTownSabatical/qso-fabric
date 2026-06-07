import asyncio

import pytest

from api.mcp_tools.qso_tools import QSOMCPTools
from qff.deserializer.service import QFFDeserializer
from qff.serializer.service import QFFSerializer


def test_create_read_patch_timeline() -> None:
    tools = QSOMCPTools()
    uri = "qso://ai.model.core"

    created = tools.qso_create(uri, {"type": "model"})
    assert created["uri"] == uri

    tools.qso_patch(uri, {"weights": {"layer1": 0.5}}, actor="trainer")
    current = tools.qso_read(uri)

    assert current["state_layer"]["weights"]["layer1"] == 0.5
    timeline = tools.qso_timeline(uri)
    assert len(timeline) == 1
    assert timeline[0]["actor"] == "trainer"


def test_snapshot_export_import_roundtrip() -> None:
    tools = QSOMCPTools()
    uri = "qso://simulation.gravity_field"

    tools.qso_create(uri, {"type": "simulation"})
    tools.qso_patch(uri, {"g": 9.81}, actor="sim")

    blob = tools.qso_export_snapshot(uri)
    parsed = tools.qso_import_snapshot(blob)

    assert parsed["header"]["uri"] == uri
    assert parsed["state"]["g"] == 9.81


def test_snapshot_import_rejects_tampered_signature() -> None:
    tools = QSOMCPTools()
    uri = "qso://simulation.tampered"

    tools.qso_create(uri, {"type": "simulation"})
    tools.qso_patch(uri, {"epoch": 1}, actor="sim")

    blob = tools.qso_export_snapshot(uri)
    parsed = QFFDeserializer().deserialize(blob)
    parsed["signature"] = "00" * 32
    tampered = QFFSerializer().serialize(parsed)

    with pytest.raises(ValueError, match="signature"):
        tools.qso_import_snapshot(tampered)


def test_entanglement_subscription_propagates() -> None:
    tools = QSOMCPTools()
    src = "qso://vr.world.city_01"
    dst = "qso://identity.user.hash"

    tools.qso_create(src, {"type": "world"})
    tools.qso_create(dst, {"type": "identity"})
    tools.qso_entangle(src, dst, "influences", bidirectional=False)

    async def scenario() -> None:
        stream = tools.qso_subscribe(dst)

        async def consume_one() -> dict:
            return await anext(stream)

        consumer_task = asyncio.create_task(consume_one())
        await asyncio.sleep(0)
        tools.qso_patch(src, {"tick": 1}, actor="engine")

        event = await asyncio.wait_for(consumer_task, timeout=1.5)
        assert event["entangled_from"] == src
        assert event["uri"] == src

    asyncio.run(scenario())


def test_subscription_cursor_replays_then_streams_live() -> None:
    tools = QSOMCPTools()
    uri = "qso://vr.world.cursor_stream"

    tools.qso_create(uri, {"type": "world"})
    tools.qso_patch(uri, {"frame": 1}, actor="engine")
    tools.qso_patch(uri, {"frame": 2}, actor="engine")

    async def scenario() -> None:
        stream = tools.qso_subscribe(uri, cursor=1)

        replay_event = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert replay_event["source"] == "replay"
        assert replay_event["event_index"] == 1
        assert replay_event["delta"]["frame"] == 2

        tools.qso_patch(uri, {"frame": 3}, actor="engine")
        live_event = await asyncio.wait_for(anext(stream), timeout=1.5)

        assert live_event["source"] == "live"
        assert live_event["event_index"] == 2
        assert live_event["delta"]["frame"] == 3

    asyncio.run(scenario())


def test_subscription_cursor_token_resumes_single_uri() -> None:
    tools = QSOMCPTools()
    uri = "qso://vr.world.cursor_token_uri"

    tools.qso_create(uri, {"type": "world"})
    tools.qso_patch(uri, {"frame": 1}, actor="engine")
    tools.qso_patch(uri, {"frame": 2}, actor="engine")
    tools.qso_patch(uri, {"frame": 3}, actor="engine")

    async def scenario() -> None:
        stream = tools.qso_subscribe(uri, cursor=0)
        first = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert first["event_index"] == 0
        token = first["cursor_token"]

        decoded = tools.qso_cursor_decode(token)
        assert decoded["kind"] == "uri"
        assert decoded["uri"] == uri
        assert decoded["next_event_index"] == 1

        resumed = tools.qso_subscribe(uri, cursor=token)
        next_event = await asyncio.wait_for(anext(resumed), timeout=1.5)
        assert next_event["event_index"] == 1
        assert next_event["delta"]["frame"] == 2

    asyncio.run(scenario())


def test_prefix_subscription_cursor_token_replay_and_live_resume() -> None:
    tools = QSOMCPTools()
    prefix = "qso://vr.zone."
    uri_a = "qso://vr.zone.a"
    uri_b = "qso://vr.zone.b"

    tools.qso_create(uri_a, {"type": "zone"})
    tools.qso_create(uri_b, {"type": "zone"})
    tools.qso_patch(uri_a, {"seq": 1}, actor="engine")
    tools.qso_patch(uri_b, {"seq": 10}, actor="engine")
    tools.qso_patch(uri_a, {"seq": 2}, actor="engine")

    async def scenario() -> None:
        stream = tools.qso_subscribe_prefix(prefix)
        first = await asyncio.wait_for(anext(stream), timeout=1.5)
        second = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert first["source"] == "replay"
        assert second["source"] == "replay"

        token = second["cursor_token"]
        decoded = tools.qso_cursor_decode(token)
        assert decoded["kind"] == "prefix"
        assert decoded["prefix"] == prefix

        resumed = tools.qso_subscribe_prefix(prefix, cursor=token)
        replay_tail = await asyncio.wait_for(anext(resumed), timeout=1.5)
        assert replay_tail["source"] == "replay"
        assert replay_tail["uri"] == uri_a
        assert replay_tail["delta"]["seq"] == 2
        assert "uri_cursor_token" in replay_tail

        live_consumer = asyncio.create_task(anext(resumed))
        await asyncio.sleep(0)
        tools.qso_patch(uri_b, {"seq": 11}, actor="engine")
        live_event = await asyncio.wait_for(live_consumer, timeout=1.5)
        assert live_event["source"] == "live"
        assert live_event["uri"] == uri_b
        assert live_event["delta"]["seq"] == 11

    asyncio.run(scenario())


def test_subscription_backpressure_drop_newest() -> None:
    tools = QSOMCPTools()
    uri = "qso://vr.world.backpressure"
    tools.qso_create(uri, {"type": "world"})

    async def scenario() -> None:
        stream = tools.qso_subscribe(uri, backpressure="drop_newest", queue_size=1)
        consumer_first = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)

        tools.qso_patch(uri, {"seq": 1}, actor="engine")
        first = await asyncio.wait_for(consumer_first, timeout=1.5)
        assert first["delta"]["seq"] == 1

        tools.qso_patch(uri, {"seq": 2}, actor="engine")
        await asyncio.sleep(0)
        tools.qso_patch(uri, {"seq": 3}, actor="engine")
        await asyncio.sleep(0)

        second = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert second["delta"]["seq"] == 2

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(anext(stream), timeout=0.15)

    asyncio.run(scenario())


def test_projection_subscription_filters_by_interest() -> None:
    tools = QSOMCPTools()
    src = "qso://vr.world.city_02"
    dst = "qso://identity.user.viewer_02"

    tools.qso_create(src, {"type": "world"})
    tools.qso_create(dst, {"type": "identity"})
    tools.qso_entangle(src, dst, "feeds-view", bidirectional=False)

    async def scenario() -> None:
        near_stream = tools.qso_subscribe_projection(
            dst,
            viewpoint={"center": [0, 0, 0], "radius": 20},
        )
        far_stream = tools.qso_subscribe_projection(
            dst,
            viewpoint={"center": [0, 0, 0], "radius": 5},
        )

        await asyncio.sleep(0)
        tools.qso_patch(
            src,
            {
                "position": [10, 0, 0],
                "objects": {"cube": {"position": [10, 0, 0], "visible": True}},
            },
            actor="engine",
        )

        projection = await asyncio.wait_for(anext(near_stream), timeout=1.5)
        assert projection["uri"] == src
        assert projection["render_delta"]["spatial"]["position"] == [10.0, 0.0, 0.0]
        assert projection["render_delta"]["objects"][0]["id"] == "cube"

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(anext(far_stream), timeout=0.15)

    asyncio.run(scenario())


def test_scene_render_subscription_snapshot_then_live_change() -> None:
    tools = QSOMCPTools()
    world = "qso://vr.world.scene_stream"
    root = f"{world}/node/root"
    cube = f"{world}/node/cube"

    tools.qso_create(root, {"type": "scene_node"})
    tools.qso_patch(
        root,
        {
            "kind": "scene_node",
            "id": "root",
            "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
            "layer_mask": 1,
        },
        actor="seed",
    )
    tools.qso_create(cube, {"type": "scene_node"})
    tools.qso_patch(
        cube,
        {
            "kind": "scene_node",
            "id": "cube",
            "parent": root,
            "transform": {"pos": [0, 1, -2], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
            "layer_mask": 1,
        },
        actor="seed",
    )

    async def scenario() -> None:
        stream = tools.qso_subscribe_scene_render_v1(world_uri=world, viewpoint={"center": [0, 0, 0], "radius": 200, "layer_mask": 1})
        first = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert first["source"] == "snapshot"
        assert first["stats"]["visible"] >= 2

        tools.qso_patch(
            cube,
            {"transform": {"pos": [2, 1, -2], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]}},
            actor="seed",
        )
        second = await asyncio.wait_for(anext(stream), timeout=1.5)
        assert second["source"] == "live"
        assert second["changed_uri"] == cube
        assert "cursor_token" in second
        await stream.aclose()

    asyncio.run(scenario())


def test_scene_reparent_rejects_cycle() -> None:
    tools = QSOMCPTools()
    world = "qso://vr.world.reparent"
    root = f"{world}/node/root"
    child = f"{world}/node/child"

    tools.qso_create(root, {"type": "scene_node"})
    tools.qso_patch(
        root,
        {
            "kind": "scene_node",
            "id": "root",
            "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
            "layer_mask": 1,
        },
        actor="seed",
    )
    tools.qso_create(child, {"type": "scene_node"})
    tools.qso_patch(
        child,
        {
            "kind": "scene_node",
            "id": "child",
            "parent": root,
            "transform": {"pos": [0, 1, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
            "bounds": {"type": "aabb", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
            "layer_mask": 1,
        },
        actor="seed",
    )

    with pytest.raises(ValueError, match="cycle"):
        tools.qso_scene_reparent(node_uri=root, parent_uri=child, actor="seed")


def test_identity_tool_surface_create_event_state() -> None:
    tools = QSOMCPTools()
    uri = "qso://identity.person.viewer_003"

    created = tools.qso_identity_create(
        uri,
        {"subject_ref": "viewer_003"},
        actor="authority",
        policy_version="v1",
    )
    assert created["object_uri"] == uri

    tools.qso_identity_event(
        uri,
        "LINK_ATTACH",
        {
            "link_id": "guardian_1",
            "target_uri": "qso://identity.person.guardian_1",
            "relationship": "guardian_relationship",
        },
        actor="authority",
        policy_version="v1",
    )
    tools.qso_identity_event(
        uri,
        "LINK_REVOKE",
        {"link_id": "guardian_1", "reason": "guardianship ended"},
        actor="authority",
        policy_version="v1",
    )

    state = tools.qso_identity_state(uri)
    link = state["entanglement_links"]["guardian_1"]
    assert link["status"] == "inert"
    assert link["relationship"] == "guardian_relationship"


def test_identity_authority_tool_surface_issue_and_policy() -> None:
    tools = QSOMCPTools()
    uri = "qso://identity.person.viewer_004"

    policy = tools.qso_identity_authority_publish_policy(
        {
            "version": "v2",
            "mode": "authority",
            "allowed_actors": ["authority://root"],
        },
        actor="governance://board",
    )
    assert policy["version"] == "v2"

    tools.qso_identity_authority_create(
        uri=uri,
        immutable_core={"subject_ref": "viewer_004"},
        actor="authority://root",
        policy_version="v2",
    )
    tools.qso_identity_authority_issue_credential(
        uri=uri,
        credential_id="cred.viewer.access",
        credential_body={"scope": "viewer"},
        actor="authority://root",
        policy_version="v2",
    )
    tools.qso_identity_authority_revoke_credential(
        uri=uri,
        credential_id="cred.viewer.access",
        reason="access revoked",
        actor="authority://root",
        policy_version="v2",
    )

    state = tools.qso_identity_state(uri)
    credential = state["credential_refs"]["cred.viewer.access"]
    assert credential["status"] == "inert"
    assert credential["revocation_reason"] == "access revoked"


def test_identity_bundle_export_verify_tool_surface() -> None:
    tools = QSOMCPTools()
    uri = "qso://identity.person.viewer_005"

    tools.qso_identity_authority_create(
        uri=uri,
        immutable_core={"subject_ref": "viewer_005"},
        actor="authority://root",
        policy_version="v1",
    )
    tools.qso_identity_authority_issue_credential(
        uri=uri,
        credential_id="cred.viewer.verified",
        credential_body={"scope": "verified"},
        actor="authority://root",
        policy_version="v1",
    )

    bundle = tools.qso_identity_export_bundle(uri, trust_roots=["trust://root"])
    verified = tools.qso_identity_verify_bundle(bundle)
    assert verified["accepted"] is True

    tampered = dict(bundle)
    tampered["declared_state_hash"] = "00" * 32
    tampered = tools.qso_identity_bundle_sign(tampered)

    rejected = tools.qso_identity_verify_bundle(tampered)
    assert rejected["accepted"] is False
    assert rejected["failed_step"] == "compare_state_hash"
