from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qs, urlparse

from api.grpc import QSOFederationService, QSOIdentityService
from api.mcp_tools.qso_tools import QSOMCPTools
from api.rest import QSOIdentityRESTAPI
from api.websocket import QSOWebSocketGateway


def test_rest_identity_routes_smoke() -> None:
    api = QSOIdentityRESTAPI()

    status, created = api.route_post(
        "/v1/identity/create",
        {
            "identity_id": "rest_user_01",
            "immutable_core": {"subject_ref": "rest_user_01"},
            "actor": "authority://root",
            "policy_version": "v1",
            "signature": "test-signature",
        },
    )
    assert status == 200
    assert created["object_uri"] == "qso://identity.person.rest_user_01"

    status, mutated = api.route_post(
        "/v1/identity/mutate",
        {
            "identity_id": "rest_user_01",
            "delta": {"scene": "alpha"},
            "actor": "authority://root",
            "policy_version": "v1",
            "signature": "test-signature",
        },
    )
    assert status == 200
    assert mutated["object_uri"] == created["object_uri"]

    status, frozen = api.route_post(
        "/v1/identity/revoke",
        {
            "identity_id": "rest_user_01",
            "reason": "manual test",
            "actor": "authority://root",
            "policy_version": "v1",
            "signature": "test-signature",
        },
    )
    assert status == 200
    assert frozen["object_uri"] == created["object_uri"]


def test_grpc_identity_service_smoke() -> None:
    svc = QSOIdentityService()
    created = svc.CreateIdentity(
        {
            "auth": {"actor": "authority://root", "policy_version": "v1"},
            "identity_id": "grpc_user_01",
            "immutable_core": {"subject_ref": "grpc_user_01"},
        }
    )
    assert created["object_uri"] == "qso://identity.person.grpc_user_01"

    mutated = svc.MutateIdentity(
        {
            "auth": {"actor": "authority://root", "policy_version": "v1"},
            "identity_id": "grpc_user_01",
            "delta": {"role": "viewer"},
        }
    )
    assert mutated["object_uri"] == created["object_uri"]


def test_grpc_federation_handshake() -> None:
    federation = QSOFederationService(runtime_version="qso-fabric/0.1.0")
    ok = federation.Handshake(
        {
            "runtime_version": "qso-fabric/0.1.0",
            "policy_set_hash": "abc123",
            "trust_roots": ["trust://root"],
            "latest_block": 42,
        }
    )
    assert ok["accepted"] is True

    bad = federation.Handshake(
        {
            "runtime_version": "qso-fabric/9.9.9",
            "policy_set_hash": "abc123",
            "trust_roots": ["trust://root"],
            "latest_block": 42,
        }
    )
    assert bad["accepted"] is False


def test_rest_qso_scene_render_routes_smoke() -> None:
    api = QSOIdentityRESTAPI()
    world_uri = "qso://vr.world/demo"
    root_uri = f"{world_uri}/node/root"
    cube_uri = f"{world_uri}/node/cube"

    status, _ = api.route_post(
        "/v1/qso/create",
        {
            "uri": root_uri,
            "schema": {"type": "scene_node"},
            "state": {
                "id": "root",
                "kind": "scene_node",
                "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
                "bounds": {"type": "aabb", "min": [-1, -1, -1], "max": [1, 1, 1]},
                "layer_mask": 1,
            },
        },
    )
    assert status == 200

    status, _ = api.route_post(
        "/v1/qso/create",
        {
            "uri": cube_uri,
            "schema": {"type": "scene_node"},
            "state": {
                "id": "cube",
                "kind": "scene_node",
                "parent": root_uri,
                "transform": {"pos": [0, 1, -2], "rot": [0, 0, 0, 1], "scl": [1, 1, 1]},
                "components": {"mesh": {"uri": "qso://asset/mesh/cube"}},
                "bounds": {"type": "aabb", "min": [-0.5, -0.5, -0.5], "max": [0.5, 0.5, 0.5]},
                "layer_mask": 1,
            },
        },
    )
    assert status == 200

    status, render = api.route_get(
        "/v1/qso/scene/render_v1",
        query={
            "world_uri": world_uri,
            "viewpoint": json.dumps({"center": [0, 0, 0], "radius": 200, "layer_mask": 1}),
        },
    )
    assert status == 200
    assert render["projection"] == "scene.render_v1"
    assert render["stats"]["visible"] >= 2

    status, validated = api.route_get(
        "/v1/qso/scene/validate",
        query={"world_uri": world_uri},
    )
    assert status == 200
    assert validated["ok"] is True

    status, moved = api.route_post(
        "/v1/qso/scene/reparent",
        {
            "node_uri": cube_uri,
            "parent_uri": root_uri,
            "actor": "scene-author",
            "policy_version": "v1",
        },
    )
    assert status == 200
    assert moved["node"]["state_layer"]["parent"] == root_uri


def test_rest_demo_plugin_routes_smoke() -> None:
    api = QSOIdentityRESTAPI()
    world_uri = "qso://vr.world/plugin_demo"

    status, manifest = api.route_get("/v1/demo/plugins", query={"world_uri": world_uri})
    assert status == 200
    assert isinstance(manifest.get("plugins"), list)
    assert manifest["plugins"]
    plugin_ids = {plugin["plugin_id"] for plugin in manifest["plugins"]}
    assert "quantum_sphere_demo" in plugin_ids
    assert "satoshi_chain_demo" in plugin_ids
    assert "nlm_digital_collections_demo" in plugin_ids
    assert isinstance(manifest.get("animations"), list)

    status, filtered = api.route_get(
        "/v1/demo/plugins",
        query={"world_uri": world_uri, "plugin_ids": "satoshi_chain_demo"},
    )
    assert status == 200
    filtered_ids = {plugin["plugin_id"] for plugin in filtered["plugins"]}
    assert filtered_ids == {"satoshi_chain_demo"}

    status, filtered_nlm = api.route_get(
        "/v1/demo/plugins",
        query={"world_uri": world_uri, "plugin_ids": "nlm_digital_collections_demo"},
    )
    assert status == 200
    filtered_nlm_ids = {plugin["plugin_id"] for plugin in filtered_nlm["plugins"]}
    assert filtered_nlm_ids == {"nlm_digital_collections_demo"}

    status, applied = api.route_post(
        "/v1/demo/plugins/apply",
        {
            "world_uri": world_uri,
            "actor": "test-plugin",
            "policy_version": "v1",
            "node_id": "test",
        },
    )
    assert status == 200
    assert int(applied["applied_nodes"]) >= 1
    assert isinstance(applied.get("animations"), list)

    status, satoshi_only = api.route_post(
        "/v1/demo/plugins/apply",
        {
            "world_uri": world_uri,
            "plugin_ids": ["satoshi_chain_demo"],
            "actor": "test-plugin",
            "policy_version": "v1",
            "node_id": "test",
        },
    )
    assert status == 200
    selected_ids = {plugin["plugin_id"] for plugin in satoshi_only["plugins"]}
    assert selected_ids == {"satoshi_chain_demo"}
    assert int(satoshi_only["applied_nodes"]) >= 1

    status, bad = api.route_get(
        "/v1/demo/plugins",
        query={"world_uri": world_uri, "plugin_ids": "unknown_demo_plugin"},
    )
    assert status == 400
    assert "unknown demo plugin ids" in str(bad.get("error", ""))


def test_rest_demo_nlm_search_routes_smoke() -> None:
    api = QSOIdentityRESTAPI()
    calls: list[dict[str, str]] = []
    sample_xml = """\
<nlmSearchResult>
  <term>cholera</term>
  <file>viv_briwYO</file>
  <server>pvlbsrch05</server>
  <count>2</count>
  <retstart>0</retstart>
  <retmax>2</retmax>
  <list num="2" start="0" per="2">
    <document rank="0" url="http://resource.nlm.nih.gov/34711120R">
      <content name="dc:title">The laws of cholera</content>
      <content name="dc:subject">Cholera - prevention &amp; control</content>
      <content name="snippet">The laws of cholera</content>
    </document>
    <document rank="1" url="http://resource.nlm.nih.gov/64710040R">
      <content name="dc:title">An account of the rise and progress of cholera</content>
      <content name="dc:date">1832</content>
      <content name="snippet">... progress of cholera ...</content>
    </document>
  </list>
</nlmSearchResult>
"""

    def fake_http_get(url: str) -> bytes:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        calls.append({key: values[-1] for key, values in params.items()})
        return sample_xml.encode("utf-8")

    api.nlm_client._http_get = fake_http_get  # type: ignore[method-assign]

    status, out = api.route_post(
        "/v1/demo/plugins/nlm/search",
        {"term": "cholera", "retmax": 2, "use_cache": False},
    )
    assert status == 200
    assert out["term"] == "cholera"
    assert out["count"] == 2
    assert out["documents"][0]["content"]["dc:title"][0] == "The laws of cholera"
    assert out["meta"]["source"] == "NLM Digital Collections Web Service"

    status, out2 = api.route_post(
        "/v1/demo/plugins/nlm/search/continue",
        {"file": out["file"], "server": out["server"], "retstart": 1, "retmax": 2, "use_cache": False},
    )
    assert status == 200
    assert out2["file"] == "viv_briwYO"
    assert out2["server"] == "pvlbsrch05"
    assert len(calls) == 2
    assert calls[0]["db"] == "digitalCollections"
    assert calls[0]["term"] == "cholera"
    assert calls[1]["file"] == "viv_briwYO"
    assert calls[1]["server"] == "pvlbsrch05"


def test_websocket_gateway_uri_stream() -> None:
    tools = QSOMCPTools()
    gateway = QSOWebSocketGateway(tools)
    uri = "qso://stream.test.uri"
    tools.qso_create(uri, {"type": "stream"})

    async def scenario() -> None:
        stream = gateway.stream_uri(uri, include_replay=False)
        consumer = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        tools.qso_patch(uri, {"tick": 1}, actor="tester")
        packet = await asyncio.wait_for(consumer, timeout=1.5)
        assert packet["type"] == "qso.event"
        assert packet["payload"]["delta"]["tick"] == 1
        await stream.aclose()

    asyncio.run(scenario())
