from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, Optional

from qso_global_meta.consensus_module import ConsensusModule
from qso_global_meta.distributed_optimizer import DistributedOptimizer
from qso_global_meta.self_learning_sync import SelfLearningSync


class MetaSyncEngine:
    """Orchestrates global-meta sync (policy consensus + learning aggregation + optimization hints)."""

    def __init__(self) -> None:
        self.consensus = ConsensusModule()
        self.learning = SelfLearningSync()
        self.optimizer = DistributedOptimizer()

        self._policies_by_node: Dict[str, Dict[str, Any]] = {}
        self._last_sync: Dict[str, Any] = {"status": "idle"}

    def ingest_policy(self, node_id: str, policy: Mapping[str, Any]) -> Dict[str, Any]:
        nid = str(node_id)
        pol = dict(policy)
        self._policies_by_node[nid] = pol
        proposal = self.consensus.propose(nid, pol)
        return {"node_id": nid, "proposal_digest": proposal.digest, "version": proposal.version}

    def ingest_learning(self, node_id: str, signals: Mapping[str, Any]) -> Dict[str, Any]:
        st = self.learning.update(str(node_id), signals)
        return {"node_id": st.node_id, "uris": len(st.rewards_by_uri)}

    def sync(self, *, total_nodes: Optional[int] = None, quorum: float = 0.51) -> Dict[str, Any]:
        decision = self.consensus.decide(total_nodes=total_nodes, quorum=quorum)
        rewards = self.learning.aggregate_rewards()
        hint = self.learning.policy_hint()
        recs = self.optimizer.recommend(rewards, top_k=10)

        self._last_sync = {
            "status": "ok",
            "consensus": decision,
            "learning": {"policy_hint": hint, "rewards_by_uri": deepcopy(rewards)},
            "optimizer": {"recommendations": recs},
        }
        return deepcopy(self._last_sync)

    def snapshot(self) -> Dict[str, Any]:
        return deepcopy(
            {
                "policies_by_node": deepcopy(self._policies_by_node),
                "learning": self.learning.snapshot(),
                "consensus": self.consensus.current(),
                "last_sync": self._last_sync,
            }
        )
