from __future__ import annotations

from qso_xr.package_registry import coverage_summary, list_packages, missing_dependencies


def test_qso_xr_package_registry_contains_full_spec_surface() -> None:
    names = {row.package for row in list_packages()}
    expected = {
        "qso-xr-scene-graph",
        "qso-xr-physics-engine",
        "qso-xr-stream-projection",
        "qso-xr-avatar-engine",
        "qso-xr-entanglement-propagator",
        "qso-diffusion-3d",
        "qso-nerf-engine",
        "qso-llm-scene-director",
        "qso-behavioral-npc-engine",
        "qso-physics-aware-diffusion",
        "qso-webxr-client",
        "qso-apple-arkit-adapter",
        "qso-unity-bridge",
        "qso-unreal-bridge",
        "qso-xr-mcp-node",
        "qso-xr-consensus-layer",
        "qso-xr-global-meta-learning",
        "qso-biometric-binding",
        "qso-avatar-cryptographic-attestation",
        "qso-haptic-feedback-engine",
        "qso-symbolic-gesture-parser",
        "qso-emotion-field-model",
        "qso-xr-qff-exporter",
        "qso-replay-render-engine",
        "qso-gpu-kernel-runtime",
        "qso-edge-node-runtime",
        "qso-hilbert-scene-compression",
        "qso-quantum-aware-renderer",
        "qso-lattice-collapse-simulator",
        "qso-autonomous-world-evolver",
        "qso-xr-dev-cli",
        "qso-xr-dashboard",
    }
    assert names == expected
    assert len(names) == 32


def test_qso_xr_coverage_summary_and_dependency_resolution() -> None:
    summary = coverage_summary()
    assert summary["total_packages"] == 32
    assert summary["implemented_count"] >= 13
    assert summary["scaffolded_count"] >= 1

    missing = missing_dependencies("qso-autonomous-world-evolver")
    assert missing == ["qso-xr-global-meta-learning"]
