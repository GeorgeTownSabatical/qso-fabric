from __future__ import annotations


def rejects_cycle(graph: dict[str, list[str]], source: str, target: str) -> bool:
    stack = [target]
    seen = set()
    while stack:
        node = stack.pop()
        if node == source:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, []))
    return False
