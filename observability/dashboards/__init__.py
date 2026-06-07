from __future__ import annotations

from typing import Any, Dict

from observability.dashboards.solis_telemetry import build_solis_telemetry_dashboards


def runtime_dashboard(runtime: Any) -> Dict[str, Any]:
    uris = getattr(getattr(runtime, "registry", None), "list_uris", lambda: [])()
    policy = {}
    try:
        if hasattr(runtime, "gdml") and hasattr(runtime.gdml, "policy_sync"):
            policy = runtime.gdml.policy_sync.current()
    except Exception:
        policy = {}

    meta_learning = {}
    try:
        glb = getattr(runtime, "global_meta", None)
        if glb is not None and hasattr(glb, "suggest"):
            meta_learning = glb.suggest()
    except Exception:
        meta_learning = {}

    return {
        "objects": len(list(uris)),
        "uris": list(uris),
        "policy": policy,
        "meta_learning": meta_learning,
    }


__all__ = ["runtime_dashboard", "build_solis_telemetry_dashboards"]
