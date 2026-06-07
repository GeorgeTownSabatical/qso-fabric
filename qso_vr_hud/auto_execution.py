from __future__ import annotations

from typing import Any, Dict, List


class AutoExecutor:
    def __init__(self, advisor, controls, interval=1.0):
        self.advisor = advisor
        self.controls = controls
        self.interval = interval
        self.enabled = True

    def run_loop(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        recommendations = self.advisor.evaluate()
        executed: List[Dict[str, Any]] = []
        for rec in recommendations:
            uri = rec.get("uri")
            patch = rec.get("patch")
            if not uri or not isinstance(patch, dict):
                continue
            self.controls.select_qso(uri)
            self.controls.patch_selected(patch)
            executed.append({"uri": uri, "patch": patch, "status": "applied"})
        return executed
