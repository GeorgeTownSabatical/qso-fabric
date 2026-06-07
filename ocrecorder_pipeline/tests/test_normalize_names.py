from normalize.names import entity_type, extract_surname, normalize_text


def test_normalize_text_ascii_upper():
    assert normalize_text(" José  García ") == "JOSE GARCIA"


def test_extract_surname_comma_and_space():
    assert extract_surname("SMITH, JOHN A") == "SMITH"
    assert extract_surname("JOHN SMITH") == "SMITH"


def test_entity_type_detects_entities():
    assert entity_type("SMITH FAMILY TRUST") == "entity"
    assert entity_type("Jane Doe") == "person"
