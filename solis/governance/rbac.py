from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

KNOWN_ROLES = {"dev", "whale", "operator", "system"}


@dataclass(frozen=True)
class RBACDecision:
    action: str
    actor: str
    role: str
    allowed: bool
    reason_code: str


@dataclass(frozen=True)
class RBACPolicy:
    action_roles: Mapping[str, frozenset[str]]
    strict_unmapped_actions: bool = True

    @classmethod
    def default(cls) -> "RBACPolicy":
        return cls(
            action_roles={
                "strategy.submit": frozenset({"dev"}),
                "strategy.shadow.run": frozenset({"dev", "operator"}),
                "proposal.approve": frozenset({"whale"}),
                "allocation.weights.set": frozenset({"whale"}),
                "allocation.ceiling.set": frozenset({"whale"}),
                "fund.pause": frozenset({"whale", "operator"}),
                "fund.resume": frozenset({"whale", "operator"}),
                "policy.propose": frozenset({"dev", "whale"}),
                "policy.activate": frozenset({"whale"}),
                "execution.operate": frozenset({"operator"}),
                "execution.read": frozenset({"dev", "whale", "operator"}),
                "identity.mutate": frozenset({"operator"}),
                "archive.operate": frozenset({"operator"}),
                "policy.read": frozenset({"dev", "whale", "operator"}),
            },
            strict_unmapped_actions=True,
        )

    def allowed_roles_for(self, action: str) -> frozenset[str]:
        return self.action_roles.get(action, frozenset())


def extract_actor_role(actor: str, *, explicit_role: str | None = None, default_role: str = "operator") -> str:
    if explicit_role:
        role = explicit_role.strip().lower()
        if role in KNOWN_ROLES:
            return role

    actor_text = actor.strip().lower()
    if "://" in actor_text:
        prefix = actor_text.split("://", 1)[0].strip()
        if prefix in KNOWN_ROLES:
            return prefix
    if actor_text.startswith("solis.") or actor_text.startswith("system://"):
        return "system"
    if default_role in KNOWN_ROLES:
        return default_role
    return "operator"


class RBACAuthorizer:
    def __init__(self, policy: RBACPolicy | None = None) -> None:
        self.policy = policy or RBACPolicy.default()

    def authorize(
        self,
        *,
        action: str,
        actor: str,
        explicit_role: str | None = None,
        default_role: str = "operator",
    ) -> RBACDecision:
        role = extract_actor_role(actor, explicit_role=explicit_role, default_role=default_role)
        if role == "system":
            return RBACDecision(
                action=action,
                actor=actor,
                role=role,
                allowed=True,
                reason_code="SYSTEM_ACTOR_ALLOW",
            )

        allowed_roles = self.policy.allowed_roles_for(action)
        if not allowed_roles:
            if self.policy.strict_unmapped_actions:
                return RBACDecision(
                    action=action,
                    actor=actor,
                    role=role,
                    allowed=False,
                    reason_code="ACTION_UNMAPPED_DENY",
                )
            return RBACDecision(
                action=action,
                actor=actor,
                role=role,
                allowed=True,
                reason_code="ACTION_UNMAPPED_ALLOW",
            )

        if role in allowed_roles:
            return RBACDecision(
                action=action,
                actor=actor,
                role=role,
                allowed=True,
                reason_code="ROLE_ALLOWED",
            )

        return RBACDecision(
            action=action,
            actor=actor,
            role=role,
            allowed=False,
            reason_code="ROLE_NOT_ALLOWED",
        )
