from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class PackageSpec:
    package: str
    section: str
    purpose: str
    implemented: bool
    module: str | None
    dependencies: Tuple[str, ...] = ()


_PACKAGE_SPECS: Tuple[PackageSpec, ...] = (
    PackageSpec(
        package="qso-xr-scene-graph",
        section="I. Core QSO + XR Runtime Packages",
        purpose="Deterministic scene graph and matrix projection for QSO world nodes.",
        implemented=True,
        module="qso_xr.scene_graph",
    ),
    PackageSpec(
        package="qso-xr-physics-engine",
        section="I. Core QSO + XR Runtime Packages",
        purpose="Deterministic tick physics with replayable body state evolution.",
        implemented=True,
        module="qso_xr.physics_engine",
    ),
    PackageSpec(
        package="qso-xr-stream-projection",
        section="I. Core QSO + XR Runtime Packages",
        purpose="Low-latency projection stream with interest filtering and backpressure control.",
        implemented=True,
        module="qso_xr.stream_projection",
    ),
    PackageSpec(
        package="qso-xr-avatar-engine",
        section="I. Core QSO + XR Runtime Packages",
        purpose="Identity-bound avatar and signed motion event surface.",
        implemented=True,
        module="qso_xr.avatar_engine",
    ),
    PackageSpec(
        package="qso-xr-entanglement-propagator",
        section="I. Core QSO + XR Runtime Packages",
        purpose="Bidirectional state propagation graph for linked XR objects.",
        implemented=True,
        module="qso_xr.entanglement_propagator",
        dependencies=("qso-xr-stream-projection",),
    ),
    PackageSpec(
        package="qso-diffusion-3d",
        section="II. AI World Generation Stack",
        purpose="Latent-to-mesh generation and consistency correction.",
        implemented=False,
        module=None,
        dependencies=("qso-xr-scene-graph",),
    ),
    PackageSpec(
        package="qso-nerf-engine",
        section="II. AI World Generation Stack",
        purpose="Neural radiance field synthesis and distillation for XR scenes.",
        implemented=False,
        module=None,
        dependencies=("qso-xr-stream-projection",),
    ),
    PackageSpec(
        package="qso-llm-scene-director",
        section="II. AI World Generation Stack",
        purpose="Narrative-aware high-level scene orchestration for generated worlds.",
        implemented=True,
        module="qso_xr.llm_scene_director",
        dependencies=("qso-xr-scene-graph", "qso-behavioral-npc-engine"),
    ),
    PackageSpec(
        package="qso-behavioral-npc-engine",
        section="II. AI World Generation Stack",
        purpose="AI NPC cognition with deterministic dialogue and memory traces.",
        implemented=False,
        module=None,
        dependencies=("qso-emotion-field-model",),
    ),
    PackageSpec(
        package="qso-physics-aware-diffusion",
        section="II. AI World Generation Stack",
        purpose="Physics-constrained generative geometry for stable world synthesis.",
        implemented=False,
        module=None,
        dependencies=("qso-diffusion-3d", "qso-xr-physics-engine"),
    ),
    PackageSpec(
        package="qso-webxr-client",
        section="III. XR Interface Layer",
        purpose="WebXR bridge for projection streaming and action ingestion.",
        implemented=True,
        module="tools.qso_web_api.WebXRAdapter",
        dependencies=("qso-xr-stream-projection",),
    ),
    PackageSpec(
        package="qso-apple-arkit-adapter",
        section="III. XR Interface Layer",
        purpose="ARKit ingress and projection bridge.",
        implemented=True,
        module="qso_xr.arkit_adapter",
    ),
    PackageSpec(
        package="qso-unity-bridge",
        section="III. XR Interface Layer",
        purpose="Unity runtime bridge for QSO scene/state sync.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-unreal-bridge",
        section="III. XR Interface Layer",
        purpose="Unreal runtime bridge for QSO scene/state sync.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-xr-mcp-node",
        section="IV. Distributed XR Layer",
        purpose="MCP-native node surface for XR workloads and state tools.",
        implemented=True,
        module="api.mcp_tools.qso_tools.QSOMCPTools",
    ),
    PackageSpec(
        package="qso-xr-consensus-layer",
        section="IV. Distributed XR Layer",
        purpose="Consensus and reconciliation for distributed XR state.",
        implemented=False,
        module=None,
        dependencies=("qso-xr-mcp-node",),
    ),
    PackageSpec(
        package="qso-xr-global-meta-learning",
        section="IV. Distributed XR Layer",
        purpose="Global policy/meta-learning adaptation across XR nodes.",
        implemented=False,
        module=None,
        dependencies=("qso-xr-consensus-layer",),
    ),
    PackageSpec(
        package="qso-biometric-binding",
        section="V. Identity + Presence Layer",
        purpose="Biometric identity attachment for avatars and session trust.",
        implemented=True,
        module="qso_xr.avatar_engine",
        dependencies=("qso-xr-avatar-engine",),
    ),
    PackageSpec(
        package="qso-avatar-cryptographic-attestation",
        section="V. Identity + Presence Layer",
        purpose="Cryptographic attestation of avatar identity and motion lineage.",
        implemented=True,
        module="qso_xr.avatar_engine",
        dependencies=("qso-biometric-binding",),
    ),
    PackageSpec(
        package="qso-haptic-feedback-engine",
        section="V. Identity + Presence Layer",
        purpose="Haptic event routing and feedback adaptation.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-symbolic-gesture-parser",
        section="V. Identity + Presence Layer",
        purpose="Semantic gesture decoding for symbolic XR controls.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-emotion-field-model",
        section="V. Identity + Presence Layer",
        purpose="Emotion and affect field model for NPC and avatar modulation.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-xr-qff-exporter",
        section="VI. Persistence + Replay",
        purpose="XR state export into QFF snapshot artifacts.",
        implemented=True,
        module="qso_xr.qff_exporter",
        dependencies=("qso-xr-scene-graph",),
    ),
    PackageSpec(
        package="qso-replay-render-engine",
        section="VI. Persistence + Replay",
        purpose="Deterministic frame replay projection for audits and verification.",
        implemented=True,
        module="qso_vr_visualization.scene_render_projector.SceneRenderProjector",
        dependencies=("qso-xr-scene-graph",),
    ),
    PackageSpec(
        package="qso-gpu-kernel-runtime",
        section="VII. Runtime + Performance",
        purpose="GPU kernel runtime surface for high-throughput XR compute.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-edge-node-runtime",
        section="VII. Runtime + Performance",
        purpose="Edge deployment runtime for XR nodes with bounded latency.",
        implemented=False,
        module=None,
    ),
    PackageSpec(
        package="qso-hilbert-scene-compression",
        section="VII. Runtime + Performance",
        purpose="Hilbert/topology-informed scene compression for streaming.",
        implemented=False,
        module=None,
        dependencies=("qso-xr-stream-projection",),
    ),
    PackageSpec(
        package="qso-quantum-aware-renderer",
        section="VIII. Quantum/Advanced",
        purpose="Quantum-aware rendering surface for advanced simulation modes.",
        implemented=False,
        module=None,
        dependencies=("qso-hilbert-scene-compression",),
    ),
    PackageSpec(
        package="qso-lattice-collapse-simulator",
        section="VIII. Quantum/Advanced",
        purpose="Lattice collapse simulator for scenario stress testing.",
        implemented=False,
        module=None,
        dependencies=("qso-quantum-aware-renderer",),
    ),
    PackageSpec(
        package="qso-autonomous-world-evolver",
        section="IX. Autonomy + Tooling",
        purpose="Autonomous world evolution with policy and stability controls.",
        implemented=False,
        module=None,
        dependencies=("qso-llm-scene-director", "qso-xr-global-meta-learning"),
    ),
    PackageSpec(
        package="qso-xr-dev-cli",
        section="IX. Autonomy + Tooling",
        purpose="Developer CLI for package coverage and knowledge merge simulation.",
        implemented=True,
        module="tools.qso_xr_dev_cli",
        dependencies=("qso-xr-dashboard",),
    ),
    PackageSpec(
        package="qso-xr-dashboard",
        section="IX. Autonomy + Tooling",
        purpose="Operational dashboard summaries for package/runtime coverage and knowledge stability.",
        implemented=True,
        module="qso_xr.dashboard",
    ),
)


def list_packages() -> List[PackageSpec]:
    return list(_PACKAGE_SPECS)


def get_package(package: str) -> PackageSpec:
    for spec in _PACKAGE_SPECS:
        if spec.package == package:
            return spec
    raise KeyError(package)


def coverage_summary() -> Dict[str, object]:
    implemented = [spec.package for spec in _PACKAGE_SPECS if spec.implemented]
    scaffolded = [spec.package for spec in _PACKAGE_SPECS if not spec.implemented]
    return {
        "total_packages": len(_PACKAGE_SPECS),
        "implemented_count": len(implemented),
        "scaffolded_count": len(scaffolded),
        "implemented_packages": implemented,
        "scaffolded_packages": scaffolded,
    }


def missing_dependencies(package: str, installed: Iterable[str] | None = None) -> List[str]:
    if installed is None:
        installed_set = {spec.package for spec in _PACKAGE_SPECS if spec.implemented}
    else:
        installed_set = {str(item) for item in installed}
    spec = get_package(package)
    return [dependency for dependency in spec.dependencies if dependency not in installed_set]
