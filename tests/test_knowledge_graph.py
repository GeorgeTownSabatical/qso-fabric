from knowledge_graph.entity_extractor import extract
from knowledge_graph.relation_builder import build_relations
from knowledge_graph.graph_query import find_relations


def test_extract_entities():
    entities = extract("Solis implements QSO")
    assert entities


def test_relation_query():
    rels = build_relations([("Solis", "IMPLEMENTS", "QSO")])
    assert find_relations(rels, source="Solis")
