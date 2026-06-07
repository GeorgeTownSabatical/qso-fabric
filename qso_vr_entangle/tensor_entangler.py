from __future__ import annotations


class TensorEntangler:
    def __init__(self, controller, entanglement_graph=None) -> None:
        self.controller = controller
        self.graph = entanglement_graph or {}

    def propagate_deformation(self, uri, deformation_func, **kwargs) -> None:
        deformation_func(uri, **kwargs)
