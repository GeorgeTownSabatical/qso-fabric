from __future__ import annotations

from typing import Any, Dict, List


class PolicyEngine:
    def __init__(self, advisor, controls, policies=None, interval=1.0):
        self.advisor = advisor
        self.controls = controls
        self.policies = policies or []
        self.interval = interval
        self.enabled = True

    def apply_policy_hint(self, hint: Dict[str, Any]) -> Dict[str, Any]:
        mode = str(hint.get("mode", "balanced"))
        policy = {"mode": mode, "source": str(hint.get("source", "policy_engine")), "raw": dict(hint)}
        self.policies.append(policy)
        if len(self.policies) > 200:
            self.policies = self.policies[-200:]
        return {"status": "applied", "policy": policy}

    def run_loop(self) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        recommendations = self.advisor.evaluate()
        out: List[Dict[str, Any]] = []
        for rec in recommendations:
            patch = rec.get("patch")
            if isinstance(patch, dict):
                out.append(self.apply_policy_hint({"mode": "balanced", "source": "advisor", "patch": patch}))
        return out
