from acquire.slicer import generate_query_slices


def test_generate_query_slices_quarters():
    slices = generate_query_slices(["smith"], 1982, 1982, use_quarters=True)
    assert len(slices) == 4
    assert slices[0].surname == "SMITH"
