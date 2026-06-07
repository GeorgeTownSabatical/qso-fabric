from __future__ import annotations


class HUDControls:
    def __init__(self, controller, hud) -> None:
        self.controller = controller
        self.hud = hud
        self.selected_qso = None

    def select_qso(self, uri):
        self.selected_qso = uri

    def collapse_selected(self):
        if self.selected_qso:
            self.controller.patch(self.selected_qso, {"collapsed": True})

    def patch_selected(self, patch_data):
        if self.selected_qso:
            self.controller.patch(self.selected_qso, patch_data)

    def entangle_selected_with(self, target_uri, strength=1.0):
        _ = strength
        if self.selected_qso:
            self.controller.tools.qso_entangle(self.selected_qso, target_uri, "hud")
