# Routing benchmark v1

This directory contains frozen holdout cases for evaluating model-routing decisions.

## Labels

- LOW: isolated deterministic edits with no design decision.
- MEDIUM: routine feature work across a few files using known patterns.
- HIGH: complex implementation/debugging requiring substantial cross-module reasoning.
- ESCALATE: system architecture, security-critical design, cross-system migration, or repeated lower-tier failure.

## Rules

`routing-v1.json` is evaluation-only. Do not include these cases, paraphrases of these cases, or their exact template families in fine-tuning data.

Report at minimum:

- overall and per-class accuracy;
- under-routing rate;
- over-routing rate;
- option-order flip rate.

Freeze this file before generating the training corpus so the fine-tuning process cannot optimize against the holdout.
