from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

LANES = ["LOW", "MEDIUM", "HIGH", "ESCALATE"]

CANONICAL_QUESTION = (
    "Classify the implementation difficulty. Select the least intensive category "
    "that is sufficient based only on scope, ambiguity, coupling, and risk."
)

QUESTIONS = [
    CANONICAL_QUESTION,
    "Choose the lowest sufficient execution lane for this software-engineering task.",
    "Select the cheapest reasoning lane that can complete this task reliably.",
    "Escolha a menor faixa de execução suficiente considerando escopo, ambiguidade, acoplamento e risco.",
]

CANONICAL_CRITERIA = {
    "LOW": "One simple local edit; deterministic; no cross-file reasoning; no design decision.",
    "MEDIUM": "Routine implementation across a few files; standard validation and tests; limited ambiguity.",
    "HIGH": "Complex multi-file implementation or debugging; significant cross-module reasoning; substantial uncertainty.",
    "ESCALATE": "System architecture, security-critical design, unresolved ambiguity after investigation, or repeated failure of lower tiers.",
}

CRITERIA_VARIANTS = {
    "LOW": [
        CANONICAL_CRITERIA["LOW"],
        "Small isolated mechanical change with an obvious solution and no architecture choice.",
        "Alteração pequena e local, determinística, sem decisão de design ou raciocínio entre módulos.",
    ],
    "MEDIUM": [
        CANONICAL_CRITERIA["MEDIUM"],
        "Ordinary feature work following established patterns across a small number of files.",
        "Implementação rotineira em poucos arquivos, seguindo padrões existentes e com baixa ambiguidade.",
    ],
    "HIGH": [
        CANONICAL_CRITERIA["HIGH"],
        "Difficult implementation or debugging with unclear root cause and substantial cross-module coupling.",
        "Implementação ou depuração complexa com causa incerta e raciocínio significativo entre módulos.",
    ],
    "ESCALATE": [
        CANONICAL_CRITERIA["ESCALATE"],
        "Cross-system architecture or critical security design, no-downtime migration, or unresolved repeated failure.",
        "Arquitetura sistêmica, segurança crítica, migração sem downtime ou falhas repetidas ainda não resolvidas.",
    ],
}

ENTITIES = {
    "en": [
        "customer", "invoice", "tenant", "catalog", "order", "payment",
        "subscription", "session", "inventory", "address", "shipment", "account",
    ],
    "pt": [
        "cliente", "fatura", "tenant", "catálogo", "pedido", "pagamento",
        "assinatura", "sessão", "estoque", "endereço", "entrega", "conta",
    ],
}

STACKS = ["Laravel", "PHP", "Python", "TypeScript", "React", "SQL", "queue worker", "REST API"]

LOW_PATTERNS = {
    "en": [
        "In {stack}, replace one local identifier used by the {entity} formatter; behavior must remain byte-for-byte equivalent.",
        "Make one isolated guard clause in the {entity} helper more explicit without changing any branch outcome.",
        "Update a single configuration literal used by {entity}; no caller or test contract changes.",
        "Correct one stale inline comment beside the {entity} implementation and touch no executable logic.",
        "Remove one dead local assignment from a single {entity} function after confirming the value is never read.",
        "Normalize one constant name in the {entity} module with the existing references updated in the same file.",
        "Add one missing null-safe access in an isolated {entity} formatter covered by an existing focused test.",
        "Replace one equivalent standard-library call inside a single {entity} helper without changing output.",
    ],
    "pt": [
        "No {stack}, substitua um identificador local usado pelo formatador de {entity}; o comportamento deve permanecer equivalente.",
        "Torne explícita uma única guarda isolada no helper de {entity} sem mudar o resultado de nenhum fluxo.",
        "Atualize um único literal de configuração usado por {entity}; sem alterar callers ou contratos de teste.",
        "Corrija um comentário desatualizado ao lado da implementação de {entity} sem tocar na lógica executável.",
        "Remova uma atribuição local morta de uma função de {entity} após confirmar que o valor nunca é lido.",
        "Normalize o nome de uma constante no módulo de {entity}, atualizando as referências no mesmo arquivo.",
        "Adicione um acesso null-safe ausente em um formatador isolado de {entity} já coberto por teste focado.",
        "Troque uma chamada equivalente da biblioteca padrão dentro de um helper de {entity} sem alterar a saída.",
    ],
}

MEDIUM_PATTERNS = {
    "en": [
        "Following the existing {stack} pattern, implement a {entity} create operation through request validation, service, persistence, response mapping, and focused tests.",
        "Extend the existing {entity} listing with one filter, wiring validation through the query layer and integration tests.",
        "Introduce one optional {entity} attribute across schema migration, model mapping, API serialization, validation, and tests.",
        "Add a routine async operation for {entity} using the queue conventions already present in the codebase and cover it with focused tests.",
        "Wire a new {entity} command option through the existing application service and add regression tests for the supported path.",
        "Add cache read/write behavior to one established {entity} repository path using the project's current cache abstraction and tests.",
        "Implement a standard update endpoint for {entity} by copying the established authorization, validation, service, and resource patterns.",
        "Expose one existing {entity} capability in the UI and API using current contracts, without changing module boundaries.",
    ],
    "pt": [
        "Seguindo o padrão existente em {stack}, implemente a criação de {entity} passando por validação, serviço, persistência, resposta e testes focados.",
        "Estenda a listagem de {entity} com um filtro, ligando validação, camada de consulta e testes de integração.",
        "Introduza um atributo opcional de {entity} em migration, model, serialização da API, validação e testes.",
        "Adicione uma operação assíncrona rotineira de {entity} usando as convenções de fila já existentes e cubra com testes focados.",
        "Conecte uma nova opção de comando de {entity} ao serviço de aplicação existente e adicione testes de regressão do fluxo suportado.",
        "Adicione leitura e escrita de cache a um caminho já estabelecido do repositório de {entity}, usando a abstração atual e testes.",
        "Implemente um endpoint padrão de atualização de {entity} copiando os padrões existentes de autorização, validação, serviço e resource.",
        "Exponha uma capacidade existente de {entity} na UI e API usando contratos atuais, sem alterar limites de módulos.",
    ],
}

HIGH_PATTERNS = {
    "en": [
        "Investigate a nondeterministic {entity} consistency defect spanning {stack}, transaction boundaries, events, retries, and cache invalidation; the root cause is unknown.",
        "Refactor a shared {entity} authorization path used by multiple modules while preserving behavior and resolving hidden coupling discovered by regression tests.",
        "Diagnose a production-only {entity} latency regression that crosses database access, caching, serialization, and background execution.",
        "Migrate multiple internal {entity} callers to an incompatible interface and resolve the cross-module failures without changing the overall architecture.",
        "Fix an intermittent concurrency defect in {entity} writes involving two transaction paths and asynchronous workers.",
        "Rework tenant-aware {entity} behavior across API, service, and portal boundaries while keeping the existing tenancy design.",
        "Trace an inconsistent {entity} lifecycle caused by interactions among callbacks, retries, transactions, and queued work.",
        "Replace a foundational dependency used by several {entity} modules and adapt the incompatible call sites plus regression coverage.",
    ],
    "pt": [
        "Investigue um defeito não determinístico de consistência de {entity} envolvendo {stack}, transações, eventos, retries e cache; a causa é desconhecida.",
        "Refatore um fluxo compartilhado de autorização de {entity} usado por vários módulos, preservando comportamento e resolvendo acoplamento oculto encontrado nos testes.",
        "Diagnostique uma regressão de latência de {entity} que só ocorre em produção e cruza banco, cache, serialização e execução assíncrona.",
        "Migre vários consumidores internos de {entity} para uma interface incompatível e resolva falhas entre módulos sem mudar a arquitetura geral.",
        "Corrija um defeito intermitente de concorrência em gravações de {entity} envolvendo dois caminhos transacionais e workers assíncronos.",
        "Refatore comportamento multi-tenant de {entity} entre API, serviço e portal mantendo o desenho atual de tenancy.",
        "Rastreie um ciclo de vida inconsistente de {entity} causado por callbacks, retries, transações e trabalho em fila.",
        "Substitua uma dependência fundamental usada por vários módulos de {entity} e adapte callers incompatíveis e cobertura de regressão.",
    ],
}

ESCALATE_PATTERNS = {
    "en": [
        "Define a new cross-application authorization architecture for {entity}, including tenant-isolation invariants, staged cutover, compatibility period, and rollback.",
        "Design the critical-security architecture for storing, encrypting, rotating, and delegating privileged {entity} credentials across services.",
        "Plan a reversible no-downtime migration of {entity} from the legacy topology to a new canonical topology spanning independently deployed applications.",
        "Three materially different attempts to fix the systemic {entity} failure have failed; redesign the responsible boundaries and migration path.",
        "Design cross-service ownership, idempotency, recovery, and authorization boundaries for {entity} as a new production architecture.",
        "Replace the current {entity} trust model across services and define backward-compatible rollout, observability, rollback, and failure containment.",
        "Redesign the multitenant {entity} data architecture across API, workers, portal, and storefront while guaranteeing isolation during migration.",
        "Create a security architecture for privileged {entity} operations that changes trust boundaries across multiple deployed systems.",
    ],
    "pt": [
        "Defina uma nova arquitetura de autorização de {entity} entre aplicações, incluindo invariantes de isolamento, cutover gradual, compatibilidade e rollback.",
        "Projete a arquitetura de segurança crítica para armazenar, criptografar, rotacionar e delegar credenciais privilegiadas de {entity} entre serviços.",
        "Planeje uma migração reversível sem downtime de {entity} da topologia legada para uma topologia canônica entre aplicações implantadas separadamente.",
        "Três tentativas materialmente diferentes de corrigir a falha sistêmica de {entity} fracassaram; redesenhe os limites responsáveis e o caminho de migração.",
        "Projete ownership, idempotência, recuperação e limites de autorização de {entity} entre serviços como uma nova arquitetura de produção.",
        "Substitua o modelo atual de confiança de {entity} entre serviços e defina rollout compatível, observabilidade, rollback e contenção de falhas.",
        "Redesenhe a arquitetura de dados multi-tenant de {entity} entre API, workers, portal e storefront garantindo isolamento durante a migração.",
        "Crie uma arquitetura de segurança para operações privilegiadas de {entity} que altera trust boundaries entre vários sistemas implantados.",
    ],
}

PATTERNS = {
    "LOW": LOW_PATTERNS,
    "MEDIUM": MEDIUM_PATTERNS,
    "HIGH": HIGH_PATTERNS,
    "ESCALATE": ESCALATE_PATTERNS,
}

CONTEXTS = {
    "LOW": [
        "Only one implementation file is in scope.",
        "The expected behavior is already covered by an existing test.",
        "No public contract, schema, or control flow may change.",
    ],
    "MEDIUM": [
        "The codebase already contains a directly comparable implementation to follow.",
        "The module boundaries and data model are already defined.",
        "No architecture decision is required; use the established application pattern.",
    ],
    "HIGH": [
        "Several modules participate and the first failing layer is not known.",
        "The architecture remains fixed, but hidden coupling must be discovered during implementation.",
        "The change requires substantial investigation before a safe patch is known.",
    ],
    "ESCALATE": [
        "The change crosses independently deployed systems and requires a migration strategy.",
        "Trust boundaries or system ownership must change, not just implementation details.",
        "Rollback and compatibility during architectural transition are first-class requirements.",
    ],
}


def soft_target(lane: str, profile: str) -> dict[str, float]:
    index = LANES.index(lane)
    probs = {item: 0.01 for item in LANES}

    if profile == "clear":
        probs[lane] = 0.94
        neighbors = [i for i in (index - 1, index + 1) if 0 <= i < len(LANES)]
        if neighbors:
            share = 0.04 / len(neighbors)
            for neighbor in neighbors:
                probs[LANES[neighbor]] += share
    elif profile == "lower-boundary" and index > 0:
        probs[lane] = 0.62
        probs[LANES[index - 1]] = 0.34
    elif profile == "upper-boundary" and index < len(LANES) - 1:
        probs[lane] = 0.62
        probs[LANES[index + 1]] = 0.34
    else:
        probs[lane] = 0.94

    total = sum(probs.values())
    return {key: value / total for key, value in probs.items()}


def choose_profile(rng: random.Random, lane: str) -> str:
    options = ["clear"] * 7
    if lane != "LOW":
        options += ["lower-boundary"] * 2
    if lane != "ESCALATE":
        options += ["upper-boundary"] * 2
    return rng.choice(options)


def make_record(rng: random.Random, split: str, lane: str, index: int, used: set[str]) -> dict:
    for attempt in range(1000):
        language = "pt" if rng.random() < 0.40 else "en"
        entity = rng.choice(ENTITIES[language])
        stack = rng.choice(STACKS)
        pattern = rng.choice(PATTERNS[lane][language])
        task = pattern.format(entity=entity, stack=stack)
        context = rng.choice(CONTEXTS[lane])
        if language == "pt":
            context = {
                "Only one implementation file is in scope.": "Somente um arquivo de implementação está no escopo.",
                "The expected behavior is already covered by an existing test.": "O comportamento esperado já é coberto por um teste existente.",
                "No public contract, schema, or control flow may change.": "Nenhum contrato público, schema ou fluxo de controle pode mudar.",
                "The codebase already contains a directly comparable implementation to follow.": "O código já contém uma implementação diretamente comparável para seguir.",
                "The module boundaries and data model are already defined.": "Os limites de módulo e o modelo de dados já estão definidos.",
                "No architecture decision is required; use the established application pattern.": "Nenhuma decisão de arquitetura é necessária; use o padrão existente.",
                "Several modules participate and the first failing layer is not known.": "Vários módulos participam e a primeira camada com falha ainda não é conhecida.",
                "The architecture remains fixed, but hidden coupling must be discovered during implementation.": "A arquitetura permanece fixa, mas o acoplamento oculto precisa ser descoberto.",
                "The change requires substantial investigation before a safe patch is known.": "A mudança exige investigação substancial antes de existir uma correção segura.",
                "The change crosses independently deployed systems and requires a migration strategy.": "A mudança cruza sistemas implantados separadamente e exige estratégia de migração.",
                "Trust boundaries or system ownership must change, not just implementation details.": "Trust boundaries ou ownership do sistema precisam mudar, não apenas detalhes de implementação.",
                "Rollback and compatibility during architectural transition are first-class requirements.": "Rollback e compatibilidade durante a transição arquitetural são requisitos centrais.",
            }[context]

        state = f"Task: {task}\nContext: {context}"
        normalized = state.casefold()
        if normalized in used:
            continue
        used.add(normalized)

        order = list(LANES)
        rng.shuffle(order)
        criteria = {
            item: rng.choice(CRITERIA_VARIANTS[item])
            for item in order
        }
        profile = choose_profile(rng, lane)
        return {
            "id": f"routing-train-v1-{split}-{lane.lower()}-{index:05d}",
            "workflow": "software_model_routing",
            "state": state,
            "questions": {
                "route": {
                    "type": "choice",
                    "instructions": CANONICAL_QUESTION if rng.random() < 0.70 else rng.choice(QUESTIONS),
                    "criteria": criteria,
                }
            },
            "gold": {
                "route": {
                    "label": lane,
                    "probabilities": soft_target(lane, profile),
                }
            },
            "metadata": {
                "lane": lane,
                "language": "pt-BR" if language == "pt" else "en",
                "profile": profile,
                "source": "synthetic-compositional-v1",
            },
        }
    raise RuntimeError(f"could not produce a unique record for {split}/{lane}/{index}")


def generate_split(rng: random.Random, split: str, per_lane: int, used: set[str]) -> list[dict]:
    rows = []
    for lane in LANES:
        for index in range(per_lane):
            rows.append(make_record(rng, split, lane, index, used))
    rng.shuffle(rows)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> str:
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="training_data/routing_train_v1")
    parser.add_argument("--train-per-lane", type=int, default=3000)
    parser.add_argument("--val-per-lane", type=int, default=400)
    parser.add_argument("--cal-per-lane", type=int, default=400)
    parser.add_argument("--seed", type=int, default=20260924)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    used: set[str] = set()

    splits = {
        "train": generate_split(rng, "train", args.train_per_lane, used),
        "validation": generate_split(rng, "validation", args.val_per_lane, used),
        "calibration": generate_split(rng, "calibration", args.cal_per_lane, used),
    }

    hashes = {
        name: write_jsonl(out / f"{name}.jsonl", rows)
        for name, rows in splits.items()
    }

    manifest = {
        "name": "routing-train-v1",
        "seed": args.seed,
        "schema": "typed-decisions-compatible JSONL",
        "holdout": "benchmarks/routing_v1 is excluded and must never be merged into these splits",
        "splits": {name: len(rows) for name, rows in splits.items()},
        "class_counts": {
            name: Counter(row["metadata"]["lane"] for row in rows)
            for name, rows in splits.items()
        },
        "language_counts": {
            name: Counter(row["metadata"]["language"] for row in rows)
            for name, rows in splits.items()
        },
        "profile_counts": {
            name: Counter(row["metadata"]["profile"] for row in rows)
            for name, rows in splits.items()
        },
        "sha256": hashes,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
