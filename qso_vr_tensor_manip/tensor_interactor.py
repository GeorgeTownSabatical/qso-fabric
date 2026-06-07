from __future__ import annotations

from qso_vr_tensor_manip.deformation_tools import TensorDeformation


class TensorInteractor:
    def __init__(self, controller) -> None:
        self.controller = controller

    def apply_deformation(self, uri, deformation, **kwargs):
        state = self.controller.read(uri)
        tensor = state.get("state_layer", {}).get("tensor")
        if deformation == "stretch":
            tensor = TensorDeformation.stretch(tensor, **kwargs)
        elif deformation == "compress":
            tensor = TensorDeformation.compress(tensor, **kwargs)
        elif deformation == "rotate":
            tensor = TensorDeformation.rotate(tensor, **kwargs)
        return self.controller.patch(uri, {"tensor": tensor})
