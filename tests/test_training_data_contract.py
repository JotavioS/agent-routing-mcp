import json
from pathlib import Path

from training.generate_routing_train_v1 import LANES, generate_split


def test_training_generator_is_balanced_unique_and_typed():
    import random

    rng = random.Random(7)
    used = set()
    rows = generate_split(rng, "test", 8, used)

    assert len(rows) == 32
    assert len({row["state"].casefold() for row in rows}) == 32

    for lane in LANES:
        assert sum(row["metadata"]["lane"] == lane for row in rows) == 8

    for row in rows:
        question = row["questions"]["route"]
        gold = row["gold"]["route"]
        assert question["type"] == "choice"
        assert set(question["criteria"]) == set(LANES)
        assert gold["label"] in LANES
        assert abs(sum(gold["probabilities"].values()) - 1.0) < 1e-9
        assert max(gold["probabilities"], key=gold["probabilities"].get) == gold["label"]


def test_frozen_holdout_policy_is_declared():
    manifest = json.loads(Path("benchmarks/routing_v1_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "frozen-holdout"
    assert "Do not use" in manifest["policy"]
