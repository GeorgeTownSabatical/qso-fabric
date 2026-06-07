from __future__ import annotations

from copy import deepcopy


class NodeRegistry:
    def __init__(self):
        self.nodes = {}

    def register_node(self, node_id, address, capabilities):
        self.nodes[node_id] = {"address": address, "capabilities": capabilities}

    def get_active_nodes(self):
        return list(self.nodes)

    def get_node(self, node_id):
        return deepcopy(self.nodes.get(node_id))
