# Routing fine-tuning data

`routing-train-v1` is the synthetic/compositional training corpus for the routing-specific Verdict 2.0 fine-tune.

The frozen `benchmarks/routing_v1` benchmark is **holdout only**. Its examples and templates must never be copied into training, validation, or calibration data.

The generator creates explicit train, validation, and calibration splits using the typed-decisions-compatible shape expected by the Verdict 2.0 marker-pointer architecture. Candidate order is randomized, canonical routing instructions are used most of the time, and alternative descriptions are mixed in for wording robustness.

Gold targets are distributions rather than only one-hot labels. Clear examples receive concentrated mass on the target lane; boundary examples retain the same gold lane but assign meaningful probability to the adjacent lane. This is intended to train both selection and calibration.

Default corpus size:

- train: 12,000 decisions (3,000 per lane)
- validation: 1,600 decisions (400 per lane)
- calibration: 1,600 decisions (400 per lane)
- languages: English and PT-BR
- lanes: LOW, MEDIUM, HIGH, ESCALATE

Deterministic policy signals such as explicit `failed_checks` floors remain the responsibility of `agent-routing-mcp`; the model corpus focuses on semantic scope, ambiguity, coupling, and architectural risk.
