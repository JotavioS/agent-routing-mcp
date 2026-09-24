# Routing fine-tuning data

`generate_routing_training_data.py` deterministically builds the v1 software model-routing dataset used to fine-tune Verdict 2.0.

Generated locally:

- train: 12,000 cases (3,000 per lane)
- validation: 1,600 cases (400 per lane)
- calibration: 1,600 cases (400 per lane)
- languages: approximately 50% English / 50% PT-BR
- targets: soft distributions with explicit boundary cases
- workflow: `software_model_routing`

The generator writes LocalLLaMA/typed-decisions-compatible JSONL with `state`, `questions`, and `gold` fields.

## Isolation

`benchmarks/routing-v1.json` is a frozen evaluation-only holdout and must never be used for training.

Generation fails if it finds an exact benchmark match or token-Jaccard similarity >= 0.90.

The manifest and aggregate SHA-256 identify the generated v1 corpus without committing the ~19 MB JSONL files.
