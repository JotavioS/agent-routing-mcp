from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

LANES = ["LOW", "MEDIUM", "HIGH", "ESCALATE"]
INDEX = {x: i for i, x in enumerate(LANES)}
CRITERIA = {
    "LOW": "Use for an isolated deterministic edit with no design decision.",
    "MEDIUM": "Use for ordinary feature implementation across a few files following known patterns.",
    "HIGH": "Use for difficult implementation or debugging with substantial cross-module reasoning, while the overall architecture is known.",
    "ESCALATE": "Use for system architecture, security-critical design, cross-system migration, highly ambiguous work, or repeated lower-tier failure.",
}
INSTRUCTIONS = [
    "Choose the lowest sufficient execution lane for this software-engineering task.",
    "Select the cheapest execution lane that can complete this task reliably.",
    "Choose the minimum model/reasoning lane sufficient for the implementation.",
    "Escolha a menor faixa de execução suficiente para esta tarefa de engenharia de software.",
    "Selecione a faixa de modelo mais barata que ainda seja suficiente para executar a tarefa com confiabilidade.",
]
ENTITIES_EN = ["customer", "invoice", "catalog", "product", "tenant", "order", "payment", "session", "subscription", "shipment", "inventory", "profile"]
ENTITIES_PT = ["cliente", "fatura", "catálogo", "produto", "tenant", "pedido", "pagamento", "sessão", "assinatura", "entrega", "estoque", "perfil"]
TECH = ["Laravel", "PHP", "Python", "TypeScript", "React", "SQL", "Go", "Java"]
COMPONENTS = ["controller", "service", "repository", "worker", "middleware", "resource", "query builder", "event handler"]
CONTEXT_EN = [
    "In the {t} API", "In the {t} admin portal", "In the {t} storefront",
    "In the {t} worker service", "In the {t} back-office module", "In the {t} integration layer",
    "In the {t} tenant module", "In the {t} reporting module",
]
CONTEXT_PT = [
    "Na API {t}", "No portal administrativo {t}", "Na loja {t}",
    "No serviço de workers {t}", "No módulo de back-office {t}", "Na camada de integração {t}",
    "No módulo de tenant {t}", "No módulo de relatórios {t}",
]
LOW_SUFFIX_EN = [
    "Existing tests already cover the behavior.",
    "Do not alter control flow.",
    "No schema or API contract changes are required.",
    "The surrounding implementation is already correct.",
]
LOW_SUFFIX_PT = [
    "Os testes existentes já cobrem o comportamento.",
    "Não altere o fluxo de controle.",
    "Nenhuma mudança de schema ou contrato de API é necessária.",
    "A implementação ao redor já está correta.",
]
MED_SUFFIX_EN = [
    "Follow the established application pattern and add focused tests.",
    "No architecture redesign is required.",
    "Use the existing validation, persistence, and authorization conventions.",
    "The expected behavior and integration points are already known.",
]
MED_SUFFIX_PT = [
    "Siga o padrão existente da aplicação e adicione testes focados.",
    "Nenhum redesenho de arquitetura é necessário.",
    "Use as convenções existentes de validação, persistência e autorização.",
    "O comportamento esperado e os pontos de integração já são conhecidos.",
]
HIGH_SUFFIX_EN = [
    "The root cause is not yet known.",
    "Several modules interact and regression risk is significant.",
    "The solution must preserve behavior across multiple call paths.",
    "Reproduction is intermittent and requires investigation.",
]
HIGH_SUFFIX_PT = [
    "A causa raiz ainda não é conhecida.",
    "Vários módulos interagem e o risco de regressão é significativo.",
    "A solução deve preservar o comportamento em vários fluxos.",
    "A reprodução é intermitente e exige investigação.",
]
ESC_SUFFIX_EN = [
    "Define staged cutover, rollback, and compatibility guarantees.",
    "The decision changes trust or ownership boundaries across systems.",
    "The rollout must remain reversible while production stays available.",
    "Lower-tier attempts have already failed or left architectural uncertainty.",
]
ESC_SUFFIX_PT = [
    "Defina cutover gradual, rollback e garantias de compatibilidade.",
    "A decisão altera limites de confiança ou ownership entre sistemas.",
    "O rollout deve permanecer reversível enquanto produção continua disponível.",
    "Tentativas de menor capacidade já falharam ou deixaram incerteza arquitetural.",
]

TRAIN_TEMPLATES = {
    "LOW": [
        "Rename one local variable for {e} in a single {t} method.",
        "Correct a typo in one {t} comment near the {e} implementation.",
        "Change one UI label related to {e} without changing its handler.",
        "Update one numeric constant in the {e} configuration.",
        "Remove one unused import from a single {e} module.",
        "Add one null guard to an isolated {e} helper.",
        "Replace one deprecated helper call with its direct equivalent for {e}.",
        "Add one missing field to an existing {e} log message.",
    ],
    "MEDIUM": [
        "Implement an authenticated {e} API endpoint with validation, persistence, serialization, and tests.",
        "Add pagination to the existing {e} endpoint with validation and integration tests.",
        "Add one nullable {e} field through migration, model, resource, validation, and tests.",
        "Add a CLI option for {e} and wire it through the existing service with tests.",
        "Add caching around one {e} repository operation and update service and tests.",
        "Add a background job for {e} using the established queue pattern.",
        "Expose an existing {e} filter in API and UI following current conventions.",
        "Add CSV export to the {e} listing using current authorization and query patterns.",
    ],
    "HIGH": [
        "Debug an intermittent {e} transaction defect spanning {c}, service, repository, worker, and integration tests.",
        "Refactor shared authorization middleware used by several {e} modules while preserving existing behavior.",
        "Diagnose a performance regression involving {e} queries, caching, async jobs, and instrumentation.",
        "Replace a core library used across multiple {e} modules and adapt incompatible interfaces.",
        "Fix a concurrency race affecting {e} writes across worker processes.",
        "Implement tenant-aware {e} behavior across API and portal boundaries without redesigning tenancy.",
        "Diagnose inconsistent {e} state involving transactions, events, retries, and cache invalidation.",
        "Rework a shared {e} state machine used by several modules while preserving compatible transitions.",
    ],
    "ESCALATE": [
        "Redesign multitenant authorization for {e} across API, portal, and storefront while preserving tenant isolation.",
        "Design storage, encryption, rotation, and access-control architecture for privileged {e} credentials.",
        "Plan a no-downtime migration of {e} from a legacy topology to a new canonical topology across applications.",
        "Redesign the {e} workflow after three materially different implementation attempts failed.",
        "Design cross-service {e} idempotency, authorization boundaries, failure recovery, and migration strategy.",
        "Redesign ownership and trust boundaries for {e} across independently deployed services.",
        "Define a new cross-application identity and authorization model for {e}.",
        "Replace the production consistency architecture for {e} across services without downtime.",
    ],
}

VAL_TEMPLATES = {
    "LOW": [
        "Delete one unreachable debug statement from a single {e} method.",
        "Add a missing return annotation to one isolated {e} helper.",
        "Change the default page-size constant for {e} in one configuration location.",
        "Adjust only the wording of one {e} validation error.",
    ],
    "MEDIUM": [
        "Add an optional sort parameter to {e} and propagate it through validation, query construction, and tests.",
        "Integrate one additional provider field into the existing {e} synchronization flow.",
        "Add soft-delete support to {e} using established framework conventions.",
        "Add a routine webhook handler for {e} using existing signature and queue patterns.",
    ],
    "HIGH": [
        "Trace a data-integrity defect where {e} updates disappear across retries, events, and transaction boundaries.",
        "Find an N+1 regression that appears only under production-like {e} load across ORM, cache, and serialization.",
        "Migrate several internal callers from a deprecated {e} interface to an incompatible replacement while preserving behavior.",
        "Resolve an intermittent deadlock involving {e} writes through two transaction paths and background workers.",
    ],
    "ESCALATE": [
        "Create the security architecture for rotating privileged {e} credentials across tenants and services.",
        "After multiple failed fixes, redesign the systemic {e} flow spanning API, worker, database, and external provider.",
        "Design a reversible zero-downtime migration of the {e} authorization model across several deployed applications.",
        "Define cross-service data ownership for {e}, including compatibility period, cutover, rollback, and recovery.",
    ],
}

PT_REWRITES = {
    "Rename one local variable for {e} in a single {t} method.": "Renomeie uma variável local de {e} em um único método {t}.",
    "Correct a typo in one {t} comment near the {e} implementation.": "Corrija um erro de digitação em um comentário {t} próximo da implementação de {e}.",
    "Implement an authenticated {e} API endpoint with validation, persistence, serialization, and tests.": "Implemente um endpoint autenticado de {e} com validação, persistência, serialização e testes.",
    "Add pagination to the existing {e} endpoint with validation and integration tests.": "Adicione paginação ao endpoint existente de {e} com validação e testes de integração.",
    "Debug an intermittent {e} transaction defect spanning {c}, service, repository, worker, and integration tests.": "Depure um defeito intermitente de transação de {e} envolvendo {c}, service, repository, worker e testes de integração.",
    "Diagnose a performance regression involving {e} queries, caching, async jobs, and instrumentation.": "Diagnostique uma regressão de desempenho envolvendo queries de {e}, cache, jobs assíncronos e instrumentação.",
    "Redesign multitenant authorization for {e} across API, portal, and storefront while preserving tenant isolation.": "Redesenhe a autorização multi-tenant de {e} entre API, portal e storefront preservando o isolamento.",
    "Plan a no-downtime migration of {e} from a legacy topology to a new canonical topology across applications.": "Planeje uma migração sem downtime de {e} de uma topologia legada para uma topologia canônica entre aplicações.",
}
def norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()

def soft_probs(label: str, boundary: str, rng: random.Random) -> dict[str, float]:
    i = INDEX[label]
    probs = {x: 0.02 for x in LANES}
    if boundary == "clear":
        probs[label] = 0.90
        neighbor = LANES[i - 1] if i > 0 else LANES[i + 1]
        probs[neighbor] += 0.04
    else:
        direction = -1 if boundary == "down" else 1
        j = max(0, min(len(LANES) - 1, i + direction))
        neighbor = LANES[j]
        probs[label] = 0.62
        probs[neighbor] = 0.32
    jitter = {k: rng.uniform(-0.008, 0.008) for k in LANES}
    vals = {k: max(0.001, probs[k] + jitter[k]) for k in LANES}
    if max(vals, key=vals.get) != label:
        vals[label] = max(vals.values()) + 0.02
    total = sum(vals.values())
    return {k: round(vals[k] / total, 6) for k in LANES}

def choose_boundary(label: str, rng: random.Random) -> str:
    choices = ["clear"] * 7
    if INDEX[label] > 0:
        choices += ["down"] * 2
    if INDEX[label] < len(LANES) - 1:
        choices += ["up"] * 2
    return rng.choice(choices)

def render_task(label: str, split: str, lang: str, rng: random.Random) -> str:
    templates = TRAIN_TEMPLATES if split == "train" else VAL_TEMPLATES
    template = rng.choice(templates[label])
    if lang == "pt" and template in PT_REWRITES:
        template = PT_REWRITES[template]
    entity = rng.choice(ENTITIES_PT if lang == "pt" else ENTITIES_EN)
    tech = rng.choice(TECH)
    context = rng.choice(CONTEXT_PT if lang == "pt" else CONTEXT_EN).format(t=tech)
    task = context + ", " + template.format(e=entity, t=tech, c=rng.choice(COMPONENTS))
    suffixes = {
        "LOW": LOW_SUFFIX_PT if lang == "pt" else LOW_SUFFIX_EN,
        "MEDIUM": MED_SUFFIX_PT if lang == "pt" else MED_SUFFIX_EN,
        "HIGH": HIGH_SUFFIX_PT if lang == "pt" else HIGH_SUFFIX_EN,
        "ESCALATE": ESC_SUFFIX_PT if lang == "pt" else ESC_SUFFIX_EN,
    }
    return task + " " + rng.choice(suffixes[label])
def make_row(label: str, split: str, idx: int, rng: random.Random) -> dict:
    lang = "pt" if rng.random() < 0.5 else "en"
    task = render_task(label, split, lang, rng)
    boundary = choose_boundary(label, rng)
    probs = soft_probs(label, boundary, rng)
    qdef = {
        "route": {
            "type": "choice",
            "instructions": rng.choice(INSTRUCTIONS),
            "criteria": CRITERIA,
        }
    }
    gold = {
        "route": {
            "type": "choice",
            "label": label,
            "probabilities": probs,
            "confidence": round(max(probs.values()), 6),
        }
    }
    return {
        "id": f"model_routing_{split}_{idx:06d}",
        "workflow": "software_model_routing",
        "split": split,
        "state": task,
        "questions": json.dumps(qdef, ensure_ascii=False),
        "gold": json.dumps(gold, ensure_ascii=False),
        "factors": json.dumps({"language": lang, "boundary": boundary}, ensure_ascii=False),
        "label_agreement": json.dumps({}, ensure_ascii=False),
        "n_questions": 1,
    }

def build_split(split: str, per_class: int, seed: int, forbidden: set[str] | None = None) -> list[dict]:
    rng = random.Random(seed)
    rows, seen = [], set(forbidden or ())
    for label in LANES:
        created = 0
        while created < per_class:
            row = make_row(label, split, len(rows), rng)
            key = norm(row["state"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
            created += 1
    rng.shuffle(rows)
    return rows
def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def audit(rows_by_split: dict[str, list[dict]], benchmark_path: Path) -> dict:
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))["cases"]
    bench_norm = {norm(x["task"]) for x in benchmark}
    bench_tokens = [(x["id"], set(norm(x["task"]).split())) for x in benchmark]
    all_seen = {}
    exact_contamination = []
    near_contamination = []
    for split, rows in rows_by_split.items():
        for row in rows:
            key = norm(row["state"])
            if key in all_seen:
                raise ValueError(f"duplicate across splits: {split} / {all_seen[key]}")
            all_seen[key] = split
            if key in bench_norm:
                exact_contamination.append(row["id"])
            tokens = set(key.split())
            for case_id, other in bench_tokens:
                union = tokens | other
                ratio = len(tokens & other) / max(1, len(union))
                if ratio >= 0.90:
                    near_contamination.append({"row": row["id"], "benchmark": case_id, "ratio": round(ratio, 4)})
    counts = {}
    for split, rows in rows_by_split.items():
        labels = Counter(json.loads(r["gold"])["route"]["label"] for r in rows)
        boundaries = Counter(json.loads(r["factors"])["boundary"] for r in rows)
        languages = Counter(json.loads(r["factors"])["language"] for r in rows)
        counts[split] = {"n": len(rows), "labels": dict(labels), "boundaries": dict(boundaries), "languages": dict(languages)}
    return {
        "counts": counts,
        "exact_benchmark_contamination": exact_contamination,
        "near_benchmark_matches_jaccard_ge_0_90": near_contamination,
        "unique_states": len(all_seen),
    }
def main() -> None:
    out = Path("routing_training_v1")
    out.mkdir(parents=True, exist_ok=True)
    train = build_split("train", 3000, 41001)
    used = {norm(r["state"]) for r in train}
    validation = build_split("validation", 400, 42002, forbidden=used)
    used.update(norm(r["state"]) for r in validation)
    calibration = build_split("calibration", 400, 43003, forbidden=used)
    rows = {
        "train": train,
        "validation": validation,
        "calibration": calibration,
    }
    for split, records in rows.items():
        write_jsonl(out / f"{split}.jsonl", records)

    audit_result = audit(rows, Path("routing_benchmark_v1.json"))
    if audit_result["exact_benchmark_contamination"]:
        raise SystemExit("benchmark contamination detected")
    if audit_result["near_benchmark_matches_jaccard_ge_0_90"]:
        raise SystemExit("near benchmark contamination detected")

    manifest = {
        "version": "routing-training-v1",
        "format": "LocalLLaMA/typed-decisions compatible JSONL",
        "workflow": "software_model_routing",
        "lanes": LANES,
        "benchmark_excluded": "routing_benchmark_v1.json",
        "soft_targets": True,
        "audit": audit_result,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    digest = hashlib.sha256()
    for name in ("train.jsonl", "validation.jsonl", "calibration.jsonl"):
        digest.update((out / name).read_bytes())
    (out / "sha256.txt").write_text(digest.hexdigest() + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
