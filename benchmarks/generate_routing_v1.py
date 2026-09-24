from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

LANES = ["LOW", "MEDIUM", "HIGH", "ESCALATE"]

DESCRIPTIONS = {
    "LOW": "Simple isolated deterministic edit; usually one file or function; no design decision.",
    "MEDIUM": "Routine feature work across a few files using known patterns, with focused validation and tests.",
    "HIGH": "Complex implementation or debugging with substantial cross-module reasoning or uncertain root cause, but no system redesign.",
    "ESCALATE": "System-level architecture redesign, security-critical architecture, highly ambiguous cross-system work, no-downtime migration, or repeated lower-tier failure.",
}

QUESTIONS = [
    "Choose the lowest sufficient execution lane for this software-engineering task.",
    "Select the cheapest model lane that is still sufficient to complete the task reliably.",
    "Escolha a menor faixa de execução suficiente para esta tarefa de engenharia de software.",
]

ENTITIES_EN = ["customer", "invoice", "catalog", "tenant", "order", "session", "payment", "subscription"]
ENTITIES_PT = ["cliente", "fatura", "catálogo", "tenant", "pedido", "sessão", "pagamento", "assinatura"]

TEMPLATES = {
    "LOW": {
        "en": [
            "Adjust only the wording of one validation error for {e}; no rule or branch changes.",
            "Change one existing label for {e} without changing event handling or state.",
            "Remove one unused import from the {e} module after confirming it has no side effects.",
            "Change the default page-size constant for {e} from 20 to 25 in one configuration location.",
            "Add one missing type annotation to an isolated {e} helper without changing runtime behavior.",
            "Delete one unreachable debug log line from a single {e} method.",
            "Rename one local variable in the {e} formatter without changing behavior.",
            "Correct one typo in documentation next to the {e} implementation.",
        ],
        "pt": [
            "Ajuste apenas a mensagem de um erro de validação de {e}, sem alterar regras ou fluxos.",
            "Altere apenas o texto de um rótulo de {e}, sem modificar eventos ou estado.",
            "Remova um único import não utilizado do módulo de {e}, sem efeitos colaterais.",
            "Altere o tamanho padrão de página de {e} de 20 para 25 em uma única configuração.",
            "Adicione uma anotação de tipo ausente em um helper isolado de {e} sem mudar o comportamento.",
            "Remova uma única linha de log de debug inalcançável de um método de {e}.",
            "Renomeie uma variável local no formatador de {e} sem mudar o comportamento.",
            "Corrija um erro de digitação na documentação ao lado da implementação de {e}.",
        ],
    },
    "MEDIUM": {
        "en": [
            "Add an optional sort parameter to the {e} endpoint and propagate it through validation, query builder, and tests.",
            "Integrate one additional field from an already-supported provider into the existing {e} sync flow and tests.",
            "Add soft-delete support to {e} using the framework's established conventions and focused regression tests.",
            "Add a routine webhook handler for {e} using the existing signature-validation and queue patterns.",
            "Add CSV export for the existing {e} listing using current authorization and query patterns, plus focused tests.",
            "Add a new authenticated {e} endpoint following the application's existing CRUD pattern with validation and tests.",
            "Add pagination to the existing {e} listing and update validation, query logic, and integration tests.",
            "Add one nullable {e} field through migration, model, API resource, validation, and focused tests.",
        ],
        "pt": [
            "Adicione um parâmetro opcional de ordenação ao endpoint de {e} e propague por validação, query e testes.",
            "Integre um campo adicional de um provedor já suportado ao fluxo de sincronização de {e} e aos testes.",
            "Adicione soft delete a {e} usando as convenções existentes do framework e testes de regressão focados.",
            "Adicione um webhook rotineiro de {e} usando os padrões existentes de validação de assinatura e fila.",
            "Adicione exportação CSV à listagem de {e} usando os padrões atuais de autorização e consulta, com testes.",
            "Adicione um novo endpoint autenticado de {e} seguindo o padrão CRUD existente, com validação e testes.",
            "Adicione paginação à listagem de {e} e atualize validação, consulta e testes de integração.",
            "Adicione um campo opcional de {e} passando por migration, model, resource, validação e testes.",
        ],
    },
    "HIGH": {
        "en": [
            "Trace a data-integrity defect where {e} updates occasionally disappear across retries, events, and transaction boundaries.",
            "Find the source of a performance regression that appears only under production-like {e} load and spans ORM, cache, and serialization.",
            "Migrate several internal callers from a deprecated {e} interface to a new incompatible interface while preserving behavior.",
            "Resolve a deadlock involving {e} writes across two transaction paths and background workers, with intermittent reproduction.",
            "Refactor shared authorization middleware used by several {e} modules while preserving behavior and regression coverage.",
            "Diagnose inconsistent {e} state caused by transactions, events, retries, and cache invalidation.",
            "Replace a core library used by multiple {e} modules, adapt incompatible interfaces, and resolve resulting test failures.",
            "Implement tenant-aware {e} behavior across API and portal modules without redesigning the tenancy architecture.",
        ],
        "pt": [
            "Rastreie um defeito de integridade em que atualizações de {e} somem ocasionalmente entre retries, eventos e transações.",
            "Encontre uma regressão de desempenho que só aparece com carga semelhante à produção de {e} e envolve ORM, cache e serialização.",
            "Migre vários consumidores internos de uma interface antiga de {e} para uma nova interface incompatível preservando o comportamento.",
            "Resolva um deadlock envolvendo gravações de {e} em dois fluxos transacionais e workers, com reprodução intermitente.",
            "Refatore middleware compartilhado de autorização usado por vários módulos de {e}, preservando comportamento e regressões.",
            "Diagnostique estado inconsistente de {e} causado por transações, eventos, retries e invalidação de cache.",
            "Substitua uma biblioteca central usada por vários módulos de {e}, adapte interfaces incompatíveis e resolva falhas de teste.",
            "Implemente comportamento multi-tenant de {e} em API e portal sem redesenhar a arquitetura de tenancy.",
        ],
    },
    "ESCALATE": {
        "en": [
            "Create the security architecture for rotating and delegating privileged {e} credentials across tenants and services.",
            "After multiple failed fixes, redesign the systemic {e} workflow spanning API, worker, database, and external provider boundaries.",
            "Design a reversible zero-downtime migration of the {e} authorization model across independently deployed applications.",
            "Define the new cross-service data-ownership architecture for {e}, including compatibility period, cutover, rollback, and failure recovery.",
            "Redesign multitenant authorization for {e} across API, portal, and storefront while preserving tenant isolation and defining migration strategy.",
            "Design security-critical storage, encryption, rotation, and access-control architecture for {e} secrets.",
            "Plan a no-downtime migration of {e} from a legacy topology to a canonical topology across several applications.",
            "A complex {e} implementation has already failed three times; tests still fail and the architectural root cause remains unresolved.",
        ],
        "pt": [
            "Crie a arquitetura de segurança para rotação e delegação de credenciais privilegiadas de {e} entre tenants e serviços.",
            "Após várias correções fracassadas, redesenhe o fluxo sistêmico de {e} entre API, worker, banco e provedor externo.",
            "Projete uma migração reversível sem downtime do modelo de autorização de {e} entre várias aplicações implantadas separadamente.",
            "Defina a nova arquitetura de ownership de dados de {e} entre serviços, incluindo compatibilidade, cutover, rollback e recuperação.",
            "Redesenhe a autorização multi-tenant de {e} entre API, portal e storefront, preservando isolamento e definindo migração.",
            "Projete a arquitetura de armazenamento, criptografia, rotação e controle de acesso para segredos de {e}.",
            "Planeje uma migração sem downtime de {e} da topologia legada para uma topologia canônica entre várias aplicações.",
            "Uma implementação complexa de {e} já falhou três vezes; os testes continuam falhando e a causa arquitetural segue incerta.",
        ],
    },
}


def build(seed: int = 20260924, per_lane_language: int = 20) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for lane in LANES:
        for language in ("en", "pt"):
            entities = ENTITIES_EN if language == "en" else ENTITIES_PT
            templates = TEMPLATES[lane][language]
            for index in range(per_lane_language):
                template = templates[index % len(templates)]
                entity = entities[(index // len(templates) + index) % len(entities)]
                candidate_ids = list(LANES)
                rng.shuffle(candidate_ids)
                rows.append(
                    {
                        "id": f"routing-v1-{lane.lower()}-{language}-{index:03d}",
                        "language": "pt-BR" if language == "pt" else "en",
                        "task": template.format(e=entity),
                        "question": rng.choice(QUESTIONS),
                        "candidates": [
                            {"id": item, "description": DESCRIPTIONS[item]}
                            for item in candidate_ids
                        ],
                        "expected": lane,
                    }
                )
    rng.shuffle(rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="benchmarks/routing_v1.jsonl")
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--per-lane-language", type=int, default=20)
    args = parser.parse_args()

    rows = build(args.seed, args.per_lane_language)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
    out.write_text(payload, encoding="utf-8")

    counts = Counter(row["expected"] for row in rows)
    langs = Counter(row["language"] for row in rows)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(json.dumps({"rows": len(rows), "labels": counts, "languages": langs, "sha256": digest}, indent=2))


if __name__ == "__main__":
    main()
