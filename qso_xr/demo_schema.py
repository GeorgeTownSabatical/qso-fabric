from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class DemoNode(TypedDict):
    suffix: str
    patch: Dict[str, Any]


class KnowledgeClaim(TypedDict):
    section: str
    claim_id: str
    statement: str
    confidence: float


class DemoExample(TypedDict):
    title: str
    input_reference: str
    profile: str
    distinct_needs: List[str]
    viewpoint: Dict[str, Any]
    nodes: List[DemoNode]
    knowledge_claims: List[KnowledgeClaim]


def validate_demo_example(value: Dict[str, Any]) -> DemoExample:
    required_str = ("title", "input_reference", "profile")
    for field in required_str:
        if not isinstance(value.get(field), str) or not str(value[field]).strip():
            raise ValueError(f"demo example requires non-empty string field '{field}'")

    needs = value.get("distinct_needs")
    if not isinstance(needs, list) or not needs or not all(isinstance(item, str) and item.strip() for item in needs):
        raise ValueError("demo example requires non-empty 'distinct_needs' string list")

    viewpoint = value.get("viewpoint")
    if not isinstance(viewpoint, dict):
        raise ValueError("demo example requires object field 'viewpoint'")

    nodes = value.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("demo example requires non-empty 'nodes' list")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"nodes[{index}] must be object")
        if not isinstance(node.get("suffix"), str) or not str(node["suffix"]).strip():
            raise ValueError(f"nodes[{index}].suffix must be non-empty string")
        if not isinstance(node.get("patch"), dict):
            raise ValueError(f"nodes[{index}].patch must be object")

    claims = value.get("knowledge_claims")
    if not isinstance(claims, list):
        raise ValueError("demo example requires 'knowledge_claims' list")
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ValueError(f"knowledge_claims[{index}] must be object")
        for field in ("section", "claim_id", "statement"):
            if not isinstance(claim.get(field), str) or not str(claim[field]).strip():
                raise ValueError(f"knowledge_claims[{index}].{field} must be non-empty string")
        confidence = claim.get("confidence")
        if not isinstance(confidence, (int, float)):
            raise ValueError(f"knowledge_claims[{index}].confidence must be numeric")
        if float(confidence) < 0.0 or float(confidence) > 1.0:
            raise ValueError(f"knowledge_claims[{index}].confidence must be in [0, 1]")

    return value  # type: ignore[return-value]
