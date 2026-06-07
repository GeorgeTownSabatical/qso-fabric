from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.naming.snapshot_terms import resolve_snapshot_artifact_path

ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / resolve_snapshot_artifact_path("xr_demo_previews")


def _load_demo_specs() -> List[Dict[str, Any]]:
    specs = [
        {
            "id": "image_1_shadow_throne",
            "title": "Shadow Throne Demo",
            "theme": "cinematic_low_light",
            "png": "image_1_shadow_throne.preview.png",
            "svg": "image_1_shadow_throne.preview.svg",
            "render": "image_1_shadow_throne.png.render.json",
            "source_image": "Image #1",
            "needs": [
                "atmospheric low-key lighting",
                "single focal silhouette clarity",
                "depth layering for sentinel figure",
                "slow camera drift with minimal UI",
            ],
        },
        {
            "id": "image_2_torus_topology",
            "title": "Torus Topology Demo",
            "theme": "analytic_educational",
            "png": "image_2_torus_topology.preview.png",
            "svg": "image_2_torus_topology.preview.svg",
            "render": "image_2_torus_topology.png.render.json",
            "source_image": "Image #2",
            "needs": [
                "annotation and label readability",
                "geometry-first clarity",
                "semantic color channel separation",
                "fixed camera framing",
            ],
        },
    ]
    for item in specs:
        render_path = PREVIEW_DIR / item["render"]
        if not render_path.exists():
            raise FileNotFoundError(f"missing render payload: {render_path}")
        item["render_payload"] = json.loads(render_path.read_text(encoding="utf-8"))
    return specs


def _write_index_html(specs: List[Dict[str, Any]]) -> Path:
    embedded = json.dumps(specs, sort_keys=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QSO XR Local Demo Viewer</title>
  <style>
    :root {{
      --bg: #0f1117;
      --panel: #181c26;
      --panel-2: #11151e;
      --text: #e7eaf1;
      --muted: #a6afc0;
      --accent: #4f8cff;
      --border: #2a3140;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      background: radial-gradient(circle at 20% 0%, #1a2233 0%, var(--bg) 46%);
      color: var(--text);
    }}
    header {{ padding: 20px 24px; border-bottom: 1px solid var(--border); }}
    h1 {{ margin: 0 0 8px 0; font-size: 22px; }}
    .sub {{ color: var(--muted); font-size: 13px; }}
    .sub a {{ color: var(--accent); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
      gap: 16px;
      padding: 16px;
    }}
    .card {{
      background: linear-gradient(160deg, var(--panel), var(--panel-2));
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.24);
    }}
    .title {{ font-size: 17px; margin: 0 0 10px 0; }}
    .meta {{ font-size: 12px; color: var(--muted); margin-bottom: 10px; line-height: 1.55; }}
    .preview {{
      width: 100%;
      border-radius: 8px;
      border: 1px solid var(--border);
      margin-bottom: 10px;
      background: #0c0f16;
    }}
    .links a {{ color: var(--accent); text-decoration: none; margin-right: 10px; font-size: 12px; }}
    .links a:hover {{ text-decoration: underline; }}
    .needs {{ margin: 10px 0 8px 0; padding-left: 16px; font-size: 12px; color: var(--muted); }}
    .hash {{ font-size: 11px; color: #8dd3ff; word-break: break-all; margin: 8px 0; }}
    .controls {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      margin-bottom: 10px;
      background: rgba(17,22,31,0.6);
      font-size: 12px;
    }}
    .controls .row {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      margin: 6px 0;
    }}
    .controls label {{ color: #c9d3e5; }}
    .controls input[type="range"] {{ width: 160px; }}
    .controls button {{
      border: 1px solid var(--border);
      background: #202738;
      color: #dce7ff;
      border-radius: 6px;
      padding: 4px 9px;
      cursor: pointer;
    }}
    canvas {{
      width: 100%;
      height: 260px;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: #0d1119;
      cursor: grab;
    }}
    canvas:active {{ cursor: grabbing; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
    th, td {{ border-bottom: 1px solid #273043; padding: 6px; text-align: left; }}
    th {{ color: #9db4d8; }}
    .footer {{ padding: 0 16px 16px 16px; color: var(--muted); font-size: 12px; }}
    .tag {{ display:inline-block; padding:2px 8px; border:1px solid var(--border); border-radius: 999px; font-size: 11px; color: #c0d6ff; margin-right: 6px; }}
  </style>
</head>
<body>
  <header>
    <h1>QSO XR Local Demo Viewer</h1>
    <div class="sub">Interactive diagnostic viewer for the two canonical demos. Drag in plot to pan, use controls for camera yaw/pitch/zoom and layer masking. Also open the <a href="./webxr_viewer.html">WebGL/WebXR renderer</a>.</div>
  </header>

  <main class="grid" id="grid"></main>
  <div class="footer">Projection uses rotated world centers with perspective depth. Layer toggles apply bitmask filtering against each node's layer_mask.</div>

<script>
const DEMOS = {embedded};

function rotateXYZ(p, yawDeg, pitchDeg) {{
  const yaw = yawDeg * Math.PI / 180;
  const pitch = pitchDeg * Math.PI / 180;
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  const cp = Math.cos(pitch), sp = Math.sin(pitch);
  const x1 = cy * p.x - sy * p.z;
  const z1 = sy * p.x + cy * p.z;
  const y2 = cp * p.y - sp * z1;
  const z2 = sp * p.y + cp * z1;
  return {{ x: x1, y: y2, z: z2 }};
}}

function drawPlot(canvas, rows, theme, camera, filterMask) {{
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width = canvas.clientWidth * dpr;
  const h = canvas.height = canvas.clientHeight * dpr;
  const pad = 30 * dpr;

  ctx.fillStyle = theme === 'cinematic_low_light' ? '#0b0d14' : '#f7f9ff';
  ctx.fillRect(0, 0, w, h);
  if (!rows.length) return [];

  const filtered = rows.filter(r => ((r.layer_mask || 0) & filterMask) !== 0);
  if (!filtered.length) {{
    ctx.fillStyle = theme === 'cinematic_low_light' ? '#f0f2f6' : '#111827';
    ctx.font = `${{12*dpr}}px Menlo, Monaco, monospace`;
    ctx.fillText('No nodes visible with current layer mask.', pad, pad + 15 * dpr);
    return [];
  }}

  const transformed = filtered.map(row => {{
    const c = row.world_bounds.center;
    const p = rotateXYZ({{x: c[0], y: c[1], z: c[2]}}, camera.yaw, camera.pitch);
    return {{ row, p }};
  }});

  const xs = transformed.map(v => v.p.x);
  const ys = transformed.map(v => v.p.y);
  const zs = transformed.map(v => v.p.z);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const spanX = Math.max(1e-6, maxX - minX);
  const spanY = Math.max(1e-6, maxY - minY);
  const zMin = Math.min(...zs), zMax = Math.max(...zs);
  const zSpan = Math.max(1e-6, zMax - zMin);

  const baseW = (w - 2 * pad);
  const baseH = (h - 2 * pad);
  ctx.strokeStyle = theme === 'cinematic_low_light' ? '#2a3244' : '#ccd7ef';
  ctx.strokeRect(pad, pad, baseW, baseH);

  const outRows = [];
  transformed.forEach(item => {{
    const zNorm = (item.p.z - zMin) / zSpan;
    const depth = 0.65 + (1.0 - zNorm) * 0.7;
    const x = pad + ((item.p.x - minX) / spanX) * baseW * camera.zoom * depth + camera.panX * dpr;
    const y = h - pad - ((item.p.y - minY) / spanY) * baseH * camera.zoom * depth + camera.panY * dpr;
    const radius = item.row.world_bounds.radius || 1;
    const r = Math.max(4*dpr, Math.min(20*dpr, (4 + radius * 3.2) * depth));

    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = theme === 'cinematic_low_light'
      ? `rgba(211,74,74,${{Math.min(0.98, 0.55 + depth*0.25)}})`
      : `rgba(41,87,216,${{Math.min(0.98, 0.50 + depth*0.28)}})`;
    ctx.fill();
    ctx.strokeStyle = theme === 'cinematic_low_light' ? '#f0f2f640' : '#11182750';
    ctx.stroke();

    ctx.fillStyle = theme === 'cinematic_low_light' ? '#f0f2f6' : '#111827';
    ctx.font = `${{10*dpr}}px Menlo, Monaco, monospace`;
    ctx.fillText(item.row.node_id, x + 8*dpr, y - 8*dpr);

    outRows.push(item.row);
  }});
  return outRows;
}}

function tableRowsHTML(rows) {{
  return rows.map(r => `<tr><td>${{r.node_id}}</td><td>${{r.world_bounds.center.map(v => Number(v).toFixed(3)).join(', ')}}</td><td>${{Number(r.world_bounds.radius).toFixed(3)}}</td><td>${{r.layer_mask}}</td></tr>`).join('');
}}

function buildCard(demo) {{
  const render = demo.render_payload;
  const rows = render.visible || [];
  const uid = demo.id.replace(/[^a-z0-9_\\-]/gi, '_');

  const card = document.createElement('section');
  card.className = 'card';
  card.innerHTML = `
    <h2 class="title">${{demo.title}}</h2>
    <div class="meta">
      <span class="tag">${{demo.source_image}}</span>
      <span class="tag">${{demo.theme}}</span><br/>
      visible_nodes=${{render.stats?.visible ?? 0}} | total_nodes=${{render.stats?.total_nodes ?? 0}}
    </div>
    <img class="preview" src="${{demo.png}}" alt="${{demo.title}} PNG preview" />
    <div class="links">
      <a href="${{demo.png}}" target="_blank">open PNG</a>
      <a href="${{demo.svg}}" target="_blank">open SVG</a>
      <a href="${{demo.render}}" target="_blank">open render JSON</a>
    </div>
    <div class="hash">frame_hash=${{render.frame_hash || ''}}</div>
    <ul class="needs">${{demo.needs.map(n => `<li>${{n}}</li>`).join('')}}</ul>
    <div class="controls">
      <div class="row">
        <label><input type="checkbox" data-layer="1" checked /> layer 1</label>
        <label><input type="checkbox" data-layer="2" checked /> layer 2</label>
        <label><input type="checkbox" data-layer="4" checked /> layer 4</label>
        <button data-action="reset">reset camera</button>
      </div>
      <div class="row">
        <label>yaw <input type="range" min="-180" max="180" value="35" step="1" data-range="yaw" /></label>
        <label>pitch <input type="range" min="-80" max="80" value="15" step="1" data-range="pitch" /></label>
        <label>zoom <input type="range" min="0.4" max="2.6" value="1" step="0.05" data-range="zoom" /></label>
      </div>
      <div class="row" id="stats-${{uid}}"></div>
    </div>
    <canvas></canvas>
    <table>
      <thead><tr><th>node_id</th><th>center (x,y,z)</th><th>radius</th><th>layer</th></tr></thead>
      <tbody id="table-${{uid}}"></tbody>
    </table>
  `;

  const canvas = card.querySelector('canvas');
  const statsEl = card.querySelector(`#stats-${{uid}}`);
  const tableEl = card.querySelector(`#table-${{uid}}`);
  const checks = Array.from(card.querySelectorAll('input[type=checkbox][data-layer]'));
  const ranges = Array.from(card.querySelectorAll('input[type=range][data-range]'));
  const resetBtn = card.querySelector('button[data-action=reset]');

  const camera = {{ yaw: 35, pitch: 15, zoom: 1, panX: 0, panY: 0 }};
  let dragging = false;
  let lastX = 0;
  let lastY = 0;

  function currentMask() {{
    return checks.reduce((acc, el) => acc | (el.checked ? Number(el.dataset.layer) : 0), 0);
  }}

  function renderFrame() {{
    const mask = currentMask();
    const visible = drawPlot(canvas, rows, demo.theme, camera, mask);
    statsEl.textContent = `mask=${{mask}} | shown=${{visible.length}} | yaw=${{camera.yaw.toFixed(0)}} | pitch=${{camera.pitch.toFixed(0)}} | zoom=${{camera.zoom.toFixed(2)}} | pan=(${{camera.panX.toFixed(1)}}, ${{camera.panY.toFixed(1)}})`;
    tableEl.innerHTML = tableRowsHTML(visible);
  }}

  checks.forEach(el => el.addEventListener('change', renderFrame));
  ranges.forEach(el => el.addEventListener('input', () => {{
    const key = el.dataset.range;
    camera[key] = Number(el.value);
    renderFrame();
  }}));
  resetBtn.addEventListener('click', () => {{
    camera.yaw = 35; camera.pitch = 15; camera.zoom = 1; camera.panX = 0; camera.panY = 0;
    ranges.forEach(el => {{
      if (el.dataset.range === 'yaw') el.value = '35';
      if (el.dataset.range === 'pitch') el.value = '15';
      if (el.dataset.range === 'zoom') el.value = '1';
    }});
    renderFrame();
  }});

  canvas.addEventListener('mousedown', (ev) => {{
    dragging = true;
    lastX = ev.clientX;
    lastY = ev.clientY;
  }});
  window.addEventListener('mouseup', () => dragging = false);
  canvas.addEventListener('mousemove', (ev) => {{
    if (!dragging) return;
    const dx = ev.clientX - lastX;
    const dy = ev.clientY - lastY;
    lastX = ev.clientX;
    lastY = ev.clientY;
    camera.panX += dx;
    camera.panY += dy;
    renderFrame();
  }});
  canvas.addEventListener('wheel', (ev) => {{
    ev.preventDefault();
    const delta = ev.deltaY > 0 ? -0.06 : 0.06;
    camera.zoom = Math.min(2.6, Math.max(0.4, camera.zoom + delta));
    const zoomRange = ranges.find(r => r.dataset.range === 'zoom');
    if (zoomRange) zoomRange.value = String(camera.zoom);
    renderFrame();
  }}, {{ passive: false }});

  window.addEventListener('resize', renderFrame);
  renderFrame();
  return card;
}}

const grid = document.getElementById('grid');
DEMOS.forEach(d => grid.appendChild(buildCard(d)));
</script>
</body>
</html>
"""
    target = PREVIEW_DIR / "index.html"
    target.write_text(html, encoding="utf-8")
    return target


def _write_webxr_viewer(specs: List[Dict[str, Any]]) -> Path:
    embedded = json.dumps(specs, sort_keys=True)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>QSO XR WebGL/WebXR Viewer</title>
  <style>
    :root {{
      --bg: #0b1017;
      --panel: #131a25;
      --text: #e7eefb;
      --muted: #9fb0cc;
      --border: #2b384d;
      --accent: #62a1ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      display: grid;
      grid-template-rows: auto 1fr;
      height: 100vh;
      background: radial-gradient(circle at 10% 0%, #1b273b 0%, var(--bg) 42%);
      color: var(--text);
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    }}
    header {{
      border-bottom: 1px solid var(--border);
      padding: 10px 14px;
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      align-items: center;
      background: rgba(8,12,18,0.78);
      backdrop-filter: blur(6px);
    }}
    .controls {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
      font-size: 12px;
      color: var(--muted);
    }}
    select, button {{
      background: #1a2433;
      color: #dfe9ff;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 4px 8px;
      font-family: inherit;
      font-size: 12px;
    }}
    #viewport {{ position: relative; }}
    #overlay {{
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(7, 10, 16, 0.68);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 11px;
      line-height: 1.5;
      max-width: min(440px, calc(100% - 20px));
      pointer-events: none;
    }}
    #overlay b {{ color: #dbe8ff; }}
    #fallback {{
      display: none;
      position: absolute;
      inset: 0;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 24px;
      color: #c9d8f5;
      background: rgba(5,8,12,0.86);
    }}
    #fallback a {{ color: var(--accent); }}
  </style>
</head>
<body>
  <header>
    <div><b>QSO XR WebGL/WebXR Viewer</b></div>
    <div class="controls">
      <label>demo
        <select id="demoSelect"></select>
      </label>
      <label><input type="checkbox" id="layer1" checked /> layer 1</label>
      <label><input type="checkbox" id="layer2" checked /> layer 2</label>
      <label><input type="checkbox" id="layer4" checked /> layer 4</label>
      <button id="resetBtn" type="button">reset camera</button>
      <a href="./index.html" style="color: var(--accent); text-decoration:none;">diagnostic viewer</a>
    </div>
  </header>
  <div id="viewport">
    <div id="overlay"></div>
    <div id="fallback"></div>
  </div>

  <script type="module">
    const DEMOS = {embedded};
    const viewport = document.getElementById('viewport');
    const overlay = document.getElementById('overlay');
    const fallback = document.getElementById('fallback');
    const demoSelect = document.getElementById('demoSelect');
    const layerChecks = [
      document.getElementById('layer1'),
      document.getElementById('layer2'),
      document.getElementById('layer4'),
    ];

    for (const demo of DEMOS) {{
      const opt = document.createElement('option');
      opt.value = demo.id;
      opt.textContent = `${{demo.title}} (${{demo.theme}})`;
      demoSelect.appendChild(opt);
    }}

    let THREE, OrbitControls, VRButton;
    try {{
      THREE = await import('https://unpkg.com/three@0.166.1/build/three.module.js');
      OrbitControls = (await import('https://unpkg.com/three@0.166.1/examples/jsm/controls/OrbitControls.js')).OrbitControls;
      VRButton = (await import('https://unpkg.com/three@0.166.1/examples/jsm/webxr/VRButton.js')).VRButton;
    }} catch (err) {{
      fallback.style.display = 'flex';
      fallback.innerHTML = `Unable to load Three.js modules (network required).<br/>Open <a href="./index.html">index.html</a> instead.`;
      throw err;
    }}

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1017);
    const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 2000);
    camera.position.set(16, 12, 18);

    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(window.devicePixelRatio || 1);
    renderer.setSize(viewport.clientWidth, viewport.clientHeight);
    renderer.xr.enabled = true;
    viewport.appendChild(renderer.domElement);
    document.body.appendChild(VRButton.createButton(renderer));

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.target.set(0, 0, 0);

    scene.add(new THREE.AmbientLight(0xffffff, 0.42));
    const key = new THREE.DirectionalLight(0xffffff, 0.88);
    key.position.set(10, 16, 8);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0x88a9ff, 0.28);
    fill.position.set(-8, 6, -10);
    scene.add(fill);

    const grid = new THREE.GridHelper(40, 20, 0x385070, 0x223145);
    grid.position.set(0, -0.01, 0);
    scene.add(grid);

    const group = new THREE.Group();
    scene.add(group);

    function layerMask() {{
      let mask = 0;
      if (layerChecks[0].checked) mask |= 1;
      if (layerChecks[1].checked) mask |= 2;
      if (layerChecks[2].checked) mask |= 4;
      return mask;
    }}

    function clearGroup() {{
      while (group.children.length) {{
        const child = group.children.pop();
        if (child.geometry) child.geometry.dispose();
        if (child.material) {{
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }}
      }}
    }}

    function makeLabel(text, color) {{
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'rgba(8,10,14,0.65)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = 'rgba(220,230,255,0.28)';
      ctx.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
      ctx.fillStyle = color;
      ctx.font = '28px Menlo, monospace';
      ctx.fillText(text, 12, 40);
      const tex = new THREE.CanvasTexture(canvas);
      tex.needsUpdate = true;
      const mat = new THREE.SpriteMaterial({{ map: tex, transparent: true }});
      const sprite = new THREE.Sprite(mat);
      sprite.scale.set(4.8, 0.6, 1);
      return sprite;
    }}

    function colorForTheme(theme, index) {{
      if (theme === 'cinematic_low_light') {{
        const palette = [0xd34a4a, 0x8f2d2d, 0xe99b9b];
        return palette[index % palette.length];
      }}
      const palette = [0x2d5be3, 0x66a4ff, 0x87bfff];
      return palette[index % palette.length];
    }}

    function applyDemo() {{
      clearGroup();
      const id = demoSelect.value || DEMOS[0].id;
      const demo = DEMOS.find(d => d.id === id) || DEMOS[0];
      const rows = (demo.render_payload.visible || []).filter(r => ((r.layer_mask || 0) & layerMask()) !== 0);

      rows.forEach((row, index) => {{
        const c = row.world_bounds.center || [0, 0, 0];
        const radius = Math.max(0.3, Number(row.world_bounds.radius || 1) * 0.08);
        const geom = new THREE.SphereGeometry(radius, 24, 16);
        const mat = new THREE.MeshStandardMaterial({{
          color: colorForTheme(demo.theme, index),
          roughness: 0.35,
          metalness: 0.2,
          emissive: demo.theme === 'cinematic_low_light' ? 0x200808 : 0x0b1233,
          emissiveIntensity: demo.theme === 'cinematic_low_light' ? 0.6 : 0.24,
        }});
        const mesh = new THREE.Mesh(geom, mat);
        mesh.position.set(Number(c[0]), Number(c[1]), Number(c[2]));
        group.add(mesh);

        const label = makeLabel(row.node_id, demo.theme === 'cinematic_low_light' ? '#ffe8e8' : '#dbe7ff');
        label.position.set(Number(c[0]), Number(c[1]) + radius + 0.45, Number(c[2]));
        group.add(label);
      }});

      const total = demo.render_payload.stats?.total_nodes ?? rows.length;
      overlay.innerHTML = `
        <div><b>${{demo.title}}</b> <span style="opacity:.78">(${{demo.theme}})</span></div>
        <div>source: ${{demo.source_image}}</div>
        <div>frame_hash: <span style="word-break:break-all;">${{demo.render_payload.frame_hash || ''}}</span></div>
        <div>visible: ${{rows.length}} / ${{total}} | layer_mask=${{layerMask()}}</div>
        <div>world_uri: ${{demo.render_payload.world_uri}}</div>
      `;
    }}

    demoSelect.addEventListener('change', applyDemo);
    layerChecks.forEach(chk => chk.addEventListener('change', applyDemo));
    document.getElementById('resetBtn').addEventListener('click', () => {{
      camera.position.set(16, 12, 18);
      controls.target.set(0, 0, 0);
      controls.update();
    }});

    function onResize() {{
      const w = viewport.clientWidth;
      const h = viewport.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }}
    window.addEventListener('resize', onResize);
    onResize();
    applyDemo();

    renderer.setAnimationLoop(() => {{
      controls.update();
      renderer.render(scene, camera);
    }});
  </script>
</body>
</html>
"""
    target = PREVIEW_DIR / "webxr_viewer.html"
    target.write_text(html, encoding="utf-8")
    return target


def main() -> int:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    specs = _load_demo_specs()
    index_path = _write_index_html(specs)
    webxr_path = _write_webxr_viewer(specs)
    print(index_path)
    print(webxr_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
