# Examples

Run bootstrap:

```bash
qso-dev bootstrap
```

Run tests:

```bash
qso-dev test
qso-dev smoke
```

Three.js WebXR scene-on-QSO demo:

```bash
. .venv/bin/activate
python main.py --serve-http --host 127.0.0.1 --port 8000
```

Then open:

```text
http://127.0.0.1:8000/demo/three-webxr-scene-qso
```

Relevant schema and projection surfaces:

```text
api/schemas/scene_node.schema.json
GET /v1/qso/scene/render_v1?world_uri=qso://vr.world/demo&viewpoint=...
GET /v1/qso/scene/validate?world_uri=qso://vr.world/demo
POST /v1/qso/scene/reparent
POST /v1/qso/create
POST /v1/qso/patch
GET /v1/qso/read?uri=...
```
