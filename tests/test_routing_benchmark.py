from benchmarks.generate_routing_v1 import LANES, build


def test_routing_v1_is_balanced_and_unique():
    rows = build()
    assert len(rows) == 160
    assert len({row["id"] for row in rows}) == 160
    assert len({row["task"] for row in rows}) == 160

    for lane in LANES:
        assert sum(row["expected"] == lane for row in rows) == 40

    assert sum(row["language"] == "en" for row in rows) == 80
    assert sum(row["language"] == "pt-BR" for row in rows) == 80


def test_routing_v1_candidate_contract():
    for row in build():
        ids = [candidate["id"] for candidate in row["candidates"]]
        assert sorted(ids) == sorted(LANES)
        assert row["expected"] in ids
        assert all(candidate["description"] for candidate in row["candidates"])
