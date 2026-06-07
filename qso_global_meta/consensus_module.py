from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolicyProposal:
    """A deterministic proposal wrapper.

    - `digest` is computed from the canonical JSON form of the policy body.
    - `version` is carried for human readability and routing; digest is the true identity.
    """

    version: str
    body: Dict[str, Any]
    digest: str

    @staticmethod
    def from_policy(policy: Mapping[str, Any]) -> "PolicyProposal":
        body = dict(policy)
        version = str(body.get("version", "v1"))
        digest = _sha256(_canon(body))
        return PolicyProposal(version=version, body=body, digest=digest)


class ConsensusModule:
    """Minimal, deterministic consensus coordinator.

    This is intentionally transport-agnostic:
      - ingest proposals
      - track votes per node
      - decide deterministically (vote-count, then digest tie-break)

    It is not a BFT protocol; it is a deterministic *decision function* suitable
    for your federation layer to call after collecting node inputs.
    """

    def __init__(self) -> None:
        self._proposals: Dict[str, PolicyProposal] = {}  # digest -> proposal
        self._votes: Dict[str, Set[str]] = {}  # digest -> set(node_id)
        self._last_decision: Dict[str, Any] = {
            "accepted": False,
            "reason": "no_decision_yet",
            "chosen": None,
        }

    def propose(self, node_id: str, policy: Mapping[str, Any]) -> PolicyProposal:
        proposal = PolicyProposal.from_policy(policy)
        self._proposals.setdefault(proposal.digest, proposal)
        # proposer implicitly votes for its own proposal (deterministic + helpful)
        self.vote(node_id=node_id, proposal_digest=proposal.digest)
        return proposal

    def vote(self, node_id: str, proposal_digest: str) -> None:
        if proposal_digest not in self._proposals:
            raise KeyError(f"unknown proposal digest: {proposal_digest}")
        self._votes.setdefault(proposal_digest, set()).add(str(node_id))

    def observe_vote_packet(self, packet: Mapping[str, Any]) -> None:
        """Accepts a packet like {"node_id": "...", "proposal_digest": "..."}."""
        node_id = str(packet["node_id"])
        digest = str(packet["proposal_digest"])
        self.vote(node_id=node_id, proposal_digest=digest)

    def tally(self) -> List[Tuple[str, int]]:
        """Returns sorted list of (digest, vote_count) descending, digest asc tie-break."""
        items = [(d, len(voters)) for d, voters in self._votes.items()]
        items.sort(key=lambda x: (-x[1], x[0]))
        return items

    def decide(self, *, total_nodes: Optional[int] = None, quorum: float = 0.51) -> Dict[str, Any]:
        """Choose a proposal deterministically.

        If `total_nodes` is provided, require vote_count / total_nodes >= quorum.
        If not provided, accept the top proposal as the best current decision.
        """
        tally = self.tally()
        if not tally:
            self._last_decision = {"accepted": False, "reason": "no_votes", "chosen": None}
            return dict(self._last_decision)

        best_digest, best_votes = tally[0]
        chosen = self._proposals[best_digest]

        if total_nodes is not None:
            if total_nodes <= 0:
                raise ValueError("total_nodes must be > 0")
            frac = best_votes / float(total_nodes)
            if frac < quorum:
                self._last_decision = {
                    "accepted": False,
                    "reason": "quorum_not_met",
                    "quorum": quorum,
                    "vote_fraction": frac,
                    "chosen": {
                        "digest": chosen.digest,
                        "version": chosen.version,
                        "votes": best_votes,
                        "body": dict(chosen.body),
                    },
                }
                return dict(self._last_decision)

        self._last_decision = {
            "accepted": True,
            "reason": "ok",
            "chosen": {
                "digest": chosen.digest,
                "version": chosen.version,
                "votes": best_votes,
                "body": dict(chosen.body),
            },
            "tally": [{"digest": d, "votes": c} for d, c in tally],
        }
        return dict(self._last_decision)

    def current(self) -> Dict[str, Any]:
        return dict(self._last_decision)
