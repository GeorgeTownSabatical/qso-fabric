from core.apn_parser import normalize_apn


def test_normalize_apn_variants():
    assert normalize_apn("40511217")["formatted"] == "405-112-17"
    assert normalize_apn("405-112-17")["formatted"] == "405-112-17"
    assert normalize_apn("405 112 17")["formatted"] == "405-112-17"
