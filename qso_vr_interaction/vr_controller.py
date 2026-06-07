from __future__ import annotations


class VRInteractionController:
    def __init__(self, controller, visualizer=None) -> None:
        self.controller = controller
        self.visualizer = visualizer
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False
