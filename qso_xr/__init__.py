from qso_xr.arkit_adapter import ARKitAdapter
from qso_xr.avatar_engine import XRAvatarEngine
from qso_xr.dashboard import XRDashboard
from qso_xr.demo_schema import DemoExample, DemoNode, KnowledgeClaim, validate_demo_example
from qso_xr.demo_examples import get_demo_example, list_demo_examples
from qso_xr.entanglement_propagator import XREntanglementPropagator
from qso_xr.knowledge_lattice import ConsistencyConflict, KnowledgeLattice
from qso_xr.llm_scene_director import LLMSceneDirector
from qso_xr.package_registry import PackageSpec, coverage_summary, list_packages, missing_dependencies
from qso_xr.physics_engine import XRPhysicsEngine
from qso_xr.runtime import QSOXRRuntime
from qso_xr.scene_graph import XRSceneGraph
from qso_xr.stream_projection import XRStreamProjection

__all__ = [
    "ARKitAdapter",
    "ConsistencyConflict",
    "DemoExample",
    "DemoNode",
    "KnowledgeLattice",
    "LLMSceneDirector",
    "KnowledgeClaim",
    "PackageSpec",
    "QSOXRRuntime",
    "XRAvatarEngine",
    "XRDashboard",
    "XREntanglementPropagator",
    "XRPhysicsEngine",
    "XRSceneGraph",
    "XRStreamProjection",
    "coverage_summary",
    "get_demo_example",
    "list_packages",
    "list_demo_examples",
    "missing_dependencies",
    "validate_demo_example",
]
