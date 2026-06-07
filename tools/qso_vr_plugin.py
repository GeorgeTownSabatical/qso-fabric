from __future__ import annotations


class QSOVRPlugin:
    def subscribe_scene(self, uri: str) -> str:
        return uri

    def push_updates(self, uri: str, scene_patch: dict) -> dict:
        return {"uri": uri, "patch": scene_patch}
