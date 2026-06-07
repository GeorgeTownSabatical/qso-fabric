class GlobalRewardAggregator:
    def __init__(self):
        self.node_rewards = {}

    def submit_reward(self, node_id, uri, reward):
        self.node_rewards.setdefault(node_id, {})[uri] = reward

    def compute_global_score(self, uri):
        values = [r[uri] for r in self.node_rewards.values() if uri in r]
        return sum(values) / len(values) if values else 0.0
