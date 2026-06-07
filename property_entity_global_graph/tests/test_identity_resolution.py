from core.identity_resolution import EntitySnapshot, match_probability


def test_probabilistic_match_prefers_close_variants():
    a = EntitySnapshot(name="Jacob T Messer", address="101 Harbor St", neighbors={"LLC1", "PARCEL1"}, created_day=7000, transfer_days=[10, 15])
    b = EntitySnapshot(name="J T Messer", address="101 Harbor Street", neighbors={"LLC1", "PARCEL2"}, created_day=7010, transfer_days=[12, 14])
    c = EntitySnapshot(name="Alice Brown", address="999 Main Ave", neighbors={"X"}, created_day=3000, transfer_days=[200])

    assert match_probability(a, b) > match_probability(a, c)
