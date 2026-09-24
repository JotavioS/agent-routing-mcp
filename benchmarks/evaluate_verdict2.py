from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoTokenizer

from verdict2.data import build_item, collate
from verdict2.model import VerdictModel, apply_temperature

ORDER = ["LOW", "MEDIUM", "HIGH", "ESCALATE"]
RANK = {name: index for index, name in enumerate(ORDER)}


def load_benchmark(path: Path, tokenizer):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = []
    for row in rows:
        criteria = {candidate["id"]: candidate["description"] for candidate in row["candidates"]}
        qdef = {"type": "choice", "instructions": row["question"], "criteria": criteria}
        gold = {
            "label": row["expected"],
            "probabilities": {name: float(name == row["expected"]) for name in criteria},
        }
        item = build_item(
            tokenizer,
            {"state": row["task"], "id": row["id"], "workflow": "software_model_routing"},
            "route",
            qdef,
            gold,
        )
        if item is None:
            raise RuntimeError(f"could not encode {row['id']}")
        pairs.append((row, item, qdef, gold))
    return pairs


def predict(model, pairs, pad_id, device, batch_size):
    result = {}
    model.eval()
    with torch.no_grad():
        for start in range(0, len(pairs), batch_size):
            chunk = pairs[start : start + batch_size]
            items = [item for _, item, _, _ in chunk]
            batch = collate(items, pad_id)
            batch = {key: value.to(device) for key, value in batch.items()}
            logits = model.option_logits(batch)
            k = batch["marker_mask"].sum(-1)
            logits = apply_temperature(logits, batch["qtype"], k, model.temperature)
            probs = torch.softmax(logits, dim=-1).cpu()
            for index, (row, item, _, _) in enumerate(chunk):
                width = len(item.option_keys)
                values = probs[index, :width].tolist()
                best = max(range(width), key=values.__getitem__)
                result[row["id"]] = item.option_keys[best]
    return result


def reversed_pairs(tokenizer, pairs):
    result = []
    for row, item, qdef, gold in pairs:
        rebuilt = build_item(
            tokenizer,
            {"state": row["task"], "id": row["id"], "workflow": "software_model_routing"},
            "route",
            qdef,
            gold,
            option_order=list(reversed(range(len(item.option_keys)))),
        )
        if rebuilt is None:
            raise RuntimeError(f"could not permute {row['id']}")
        result.append((row, rebuilt, qdef, gold))
    return result


def summarize(pairs, predictions, reversed_predictions):
    total = len(pairs)
    correct = under = over = severe_under = flips = abs_error = 0
    confusion = {gold: Counter() for gold in ORDER}
    languages = {}

    for row, _, _, _ in pairs:
        gold = row["expected"]
        pred = predictions[row["id"]]
        confusion[gold][pred] += 1
        correct += pred == gold
        delta = RANK[pred] - RANK[gold]
        under += delta < 0
        over += delta > 0
        abs_error += abs(delta)
        severe_under += gold == "ESCALATE" and RANK[pred] <= RANK["MEDIUM"]
        flips += reversed_predictions[row["id"]] != pred
        stat = languages.setdefault(row["language"], [0, 0])
        stat[0] += 1
        stat[1] += pred == gold

    return {
        "n": total,
        "accuracy": correct / total,
        "under_routing_rate": under / total,
        "over_routing_rate": over / total,
        "mean_lane_distance": abs_error / total,
        "severe_under_route_rate": severe_under / total,
        "reversed_order_argmax_flip_rate": flips / total,
        "per_class": {
            gold: {
                "n": sum(confusion[gold].values()),
                "accuracy": confusion[gold][gold] / max(1, sum(confusion[gold].values())),
                "predictions": {lane: confusion[gold][lane] for lane in ORDER},
            }
            for gold in ORDER
        },
        "per_language": {
            lang: {"n": values[0], "accuracy": values[1] / values[0]}
            for lang, values in languages.items()
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--checkpoint")
    parser.add_argument("--backbone", default="answerdotai/ModernBERT-base")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--out")
    args = parser.parse_args()

    checkpoint = None
    backbone = args.backbone
    if args.checkpoint:
        checkpoint = torch.load(args.checkpoint, map_location=args.device, weights_only=False)
        backbone = checkpoint["backbone"]

    tokenizer = AutoTokenizer.from_pretrained(backbone)
    model = VerdictModel(backbone).to(args.device)
    if checkpoint:
        model.load_state_dict(checkpoint["state_dict"])

    pairs = load_benchmark(Path(args.benchmark), tokenizer)
    predictions = predict(model, pairs, tokenizer.pad_token_id or 0, args.device, args.batch_size)
    reverse = reversed_pairs(tokenizer, pairs)
    reversed_predictions = predict(model, reverse, tokenizer.pad_token_id or 0, args.device, args.batch_size)

    report = {
        "baseline": "checkpoint" if checkpoint else "untrained_head",
        "backbone": backbone,
        "checkpoint": args.checkpoint,
        "metrics": summarize(pairs, predictions, reversed_predictions),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
