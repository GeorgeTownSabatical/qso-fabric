from __future__ import annotations


class QSOActions:
    def __init__(self, controller) -> None:
        self.controller = controller

    def measure_qso(self, uri: str) -> None:
        state = self.controller.read(uri)
        self.controller.patch(uri, {"measured": True, "state_keys": list(state.keys())})

    def patch_qso(self, uri: str, delta: dict) -> None:
        self.controller.patch(uri, delta)

    def entangle_qso(self, uri_a: str, uri_b: str, strength: float = 0.8) -> None:
        _ = strength
        self.controller.tools.qso_entangle(uri_a, uri_b, "interactive")
