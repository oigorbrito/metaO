# HANDOFF — metaO — 2026-08-25

## 1. Objetivo do projeto

O `metaO` é um **meta-orquestrador / Control Plane de orquestradores**.

Ele **não implementa agentes diretamente**. A unidade estratégica é o orquestrador inteiro, por exemplo:

- LangGraph
- CrewAI
- OpenAI Agents
- Microsoft Agent Framework
- outros runtimes compatíveis com o contrato

Cada runtime pode possuir internamente agentes, tools, memory, prompts, routing e workflows. O `metaO Core` não deve depender dessa topologia interna.

### Teste arquitetural central

```text
Consigo substituir um orquestrador inteiro,
incluindo seus agents/tools/memory/workflows,
sem alterar o metaO Core?
```

Se a resposta for não, a abstração está errada.

---

## 2. Arquitetura congelada

```text
Mission
  ↓
Strategy / Selection
  ↓
Policy / Budget
  ↓
OrchestratorContract
  ↓
Runtime Adapter
  ↓
Orchestrator real
  ↓
Evidence
  ↓
Independent Acceptance
  ↓
Accept / Replan / Failover / Block
```

Invariantes congeladas:

```text
ORCHESTRATOR_DONE != METAO_ACCEPTED
ADOPT > ADAPT > BUILD
SDK/framework-specific types must not enter metaO Core
latest certification generation is authoritative
old PASS never regains authority behind newer FAIL/revoke/stale
```

Não introduzir agora apenas por sofisticação:

- quarto runtime só para aumentar contagem
- learned routing / RL
- Kubernetes
- microservices
- banco distribuído
- cloud infra
- UI sofisticada

---

## 3. Runtime pins atuais

```text
Python             = 3.12.x
OpenAI Agents      = 0.20.0
CrewAI             = 1.15.16
LangGraph          = 1.2.11
```

`OpenAI Agents 0.21.1` foi rejeitado pelo resolver real porque exige OpenAI client `>=3,<4`, enquanto CrewAI `1.15.16` exige `>=2.30,<3`.

---

## 4. Baseline consolidado antes do Roadmap 8

PR canônica Roadmaps 2–7:

```text
PR #68
validated candidate SHA = aa9e4e9a2aae73c693eb43a31c71f0801d80d7ea
local release gate       = PASS 21/21
full unit suite          = PASS 279/279
clean worktree           = true
fatal_error              = null
main merge commit        = 58feb12531982342bf3c12b9e8b8c61a5e819c5f
```

Hosted GitHub Actions permanece classificado como:

```text
HOSTED_ACTIONS = BLOCKED_EXTERNAL_PRE_STEP
```

Evidência histórica:

- standard Ubuntu/Windows/macOS jobs falharam antes de checkout/setup/test
- `steps=null` / `steps=[]`
- `runner_id=0`
- `BlobNotFound` observado em execuções anteriores

Issue de controle: `#71`.

Isso não invalida os testes funcionais locais já executados, mas impede usar hosted CI como evidência neste momento.

---

## 5. PRs de documentação consolidadas em 2026-08-25

Após autorização explícita, foram incorporadas ao `main`:

```text
#89  Docs: reconcile post-Roadmap 7 release state
#93  Docs: Roadmap 8 acceptance A01-A20 gap audit
#95  Docs: A02 independent verifier donor fit
#97  Docs: authoritative terminal sources donor fit
#99  Docs: A11 authoritative retry history donor fit
#101 Docs: A16/A19 terminal proof and adversarial closure fit
#103 Docs: A14 bound confidence advisory donor fit
```

Essas PRs eram docs-only e não alteraram `src/metao/**`.

---

## 6. Roadmap 8 — auditoria A01–A20

Classificação congelada no audit:

```text
FINAL_PATH_PROVEN = 7
  A01 A03 A10 A13 A15 A17 A20

PARTIAL_COMPOSITION = 9
  A04 A05 A06 A07 A08 A09 A11 A16 A19

PRIMITIVE_ONLY = 1
  A14

BLOCKED_BY_DEPENDENCY = 2
  A12 A18

MISSING = 1
  A02
```

Ordem de implementação registrada:

```text
1. WU01 canonical EvidenceEnvelope
2. A18 AcceptanceBudget final-path accounting
3. A02 independent VerifierPort / registry
4. A05/A07/A09 authoritative terminal sources
5. A11 authoritative retry history
6. A14 confidence advisory integration
7. A08/A04/A06 remaining approval/trust/provenance
8. A16/A19 terminal proof + adversarial closure
```

---

## 7. PR #91 — WU01 canonical EvidenceEnvelope

Status atual:

```text
PR #91 = OPEN / DRAFT
MERGE = NOT AUTHORIZED
EXECUTABLE PASS = PENDING
```

Objetivo: eliminar os dois `EvidenceEnvelope` divergentes e estabelecer um único contrato framework-neutral.

Implementação principal:

```text
src/metao/evidence.py
```

As seguintes referências devem resolver para a mesma classe:

```text
metao.EvidenceEnvelope
metao.core.EvidenceEnvelope
metao.acceptance.EvidenceEnvelope
```

A PR também corrige persistência durável:

```text
mission snapshot schema = 4
```

Campos acceptance-critical passam a ser persistidos, incluindo:

- evidence_id
- obligation_id
- mission/execution/orchestrator/adapter/version/attempt bindings
- subject/state
- verification context
- policy bundle
- verifier
- payload digest
- provenance root
- authority id
- passed
- freshness fields
- approval
- confidence
- verification_cost_units

Snapshots legados contendo evidence sem `evidence_id`, `authority_id` ou `passed` devem falhar fechado como `MissionStoreCorrupt`; não fabricar valores.

### Testes obrigatórios antes do merge

```text
python -m unittest tests.unit.test_roadmap_8_work_unit_01 -v
python -m unittest tests.unit.test_block_j_acceptance_trust -v
python -m unittest tests.unit.test_block_l_multi_orchestrator -v
python -m unittest discover -s tests/unit -p 'test_*.py' -v
```

Não mergear #91 enquanto esses testes não tiverem evidência executável verde.

Observação: depois dos merges docs-only de hoje, a consulta remota passou a apresentar #91 como `mergeable=false`; tratar isso separadamente do gate funcional e atualizar/reconciliar a branch apenas quando for trabalhar nela.

---

## 8. PR #69 — release evidence validator

Status:

```text
PR #69 = OPEN / DRAFT
REAL_PASS_JSON_VALIDATION = BLOCKED_EVIDENCE_FILE_UNAVAILABLE
MERGE = BLOCKED_BY_OWN_FAIL_CLOSED_EVIDENCE_RULE
```

O validator em si teve:

```text
VALIDATOR_UNIT_SCENARIOS = PASS 7/7
VALID_CLI_FIXTURE        = PASS / exit 0
MALFORMED_CLI_FIXTURE    = rejected / exit 1
```

Mas o JSON exato do gate local real não está disponível no repositório/sessão.

Último caminho local conhecido:

```text
C:\Users\Igor B\AppData\Local\metaO\release-gate-evidence\gate-20260825-103527.json
```

Não enfraquecer o validator para liberar o merge.

Observação: após os merges docs-only de hoje, a consulta remota também apresentou #69 como `mergeable=false`; isso é secundário ao blocker principal do JSON real.

---

## 9. Donor-fit congelado para A02

```text
Inspect AI = ADAPT verifier execution / registry / structured-result patterns
OMA        = ADAPT validation/binding/authority/closure invariants
in-toto    = REFERENCE hostile-boundary authorization/fail-closed verification
BUILD      = minimum metaO VerifierPort + VerifierRegistry + VerifierResult
```

Regra:

```text
VERIFIER_PASS != METAO_ACCEPTED
```

Verifier selection deve vir de política/registry pertencente ao metaO, nunca de uma string fornecida pelo executor.

---

## 10. Donor-fit congelado para A05/A07/A09

Primary donor: `tihotm/oma@ca43381dc8bce4041da4fc09efbe939642729939`.

Decisão:

```text
A05 authoritative state re-read = ADAPT
A07 durable authority registry  = ADAPT
A09 deterministic policy root   = ADAPT
whole OMA dependency            = NO
```

Ports propostos:

```text
SubjectStatePort.current(subject_id)
AuthorityRegistryPort.resolve(authority_context_id, request)
PolicyRegistryPort.get(policy_bundle_id)
```

Regra:

```text
CALLER_CONTEXT = CANDIDATE CLAIMS
AUTHORITATIVE_PORTS = TERMINAL SOURCE OF TRUTH
```

---

## 11. Donor-fit congelado para A11

Primary donor: OMA retry/retry-ledger.

Responsabilidade:

```text
MissionStorePort = current operational mission snapshot/state
RetryHistoryPort = append-only factual attempt/retry/cost authority
```

Podem compartilhar o mesmo SQLite; não criar serviço/banco externo desnecessário.

Regra:

```text
CALLER_OR_MISSION_SNAPSHOT_HISTORY = CANDIDATE / PROJECTION
RETRY_HISTORY_PORT = FACTUAL SOURCE OF TRUTH
```

A11 trata fatos de execução/retry; A18 tratará custos da fase de verificação/aceitação. Evitar dupla contagem.

---

## 12. Donor-fit congelado para A14

Current helper:

```text
apply_confidence_after_hard_gates
```

Semântica preservada:

```text
HARD_GATE_DENY -> confidence cannot rescue candidate
```

Confidence pode apenas tornar verificação mais estrita ou orientar caminhos já elegíveis.

Proibido:

- `BLOCK -> ACCEPT`
- `STALE -> ACCEPT`
- preencher evidência ausente com score
- autorizar por confidence
- best-of-N cherry-picking
- learned threshold/RL
- budget bypass

Integração de produto fica depois de A18 + A02.

---

## 13. Donor-fit congelado para A16/A19

Decisão:

```text
OMA validation closure/root pattern = ADAPT
OMA adversarial terminal tests      = ADAPT
metaO EventLedger/MissionStore      = REUSE
metaO standards-provider boundary   = REUSE
whole OMA dependency                = NO
new audit database/service          = NO
custom crypto                       = FORBIDDEN
```

Regra crítica:

```text
EVENTS_EXIST != TERMINAL_DECISION_RECONSTRUCTIBLE
SECURITY_PRIMITIVE_EXISTS != ADVERSARIAL_TERMINAL_PATH_PROVEN
LOCAL_HASH_ROOT != CRYPTOGRAPHIC_AUTHENTICITY
```

Hostile/distributed claims devem usar vetted standards-based attestation; não implementar crypto caseira.

---

## 14. Próximo bloco exato — A18 AcceptanceBudget donor fit

Depois de deixar o estado remoto/documental consistente, o próximo bloco independente é congelar o donor-fit A18.

Estado atual do metaO:

`control_plane.py` já faz precheck de quatro dimensões:

```text
money_used < money_limit
tokens_used < token_limit
wall_time_used_s < wall_time_limit_s
verifier_attempts_used < verifier_attempt_limit
```

Mas a composição final atualmente consome de forma efetiva apenas `verifier_attempts=1`. Money/tokens/wall-clock da fase de verificação ainda não estão completamente contabilizados.

Donor congelado:

```text
UKGovernmentBEIS/inspect_ai@ebf4815ee260afcc8c34ad9d66e6f8d98a89e905
src/inspect_ai/util/_limit.py
```

Padrão a adaptar:

```text
explicit limit + usage + remaining + fail-closed
```

### Decisões a congelar em A18

1. Usage deve ser medido/normalizado pelo metaO/verifier wrapper, não por texto bruto do executor.
2. Criar um `VerificationUsage` framework-neutral contendo pelo menos money, tokens, wall_time_s e verifier_attempts, ligado ao verifier/request.
3. A18 mede a fase de verification/acceptance, não toda a execução do runtime.
4. A11 continua sendo autoridade factual de execution/retry cost; A18 é autoridade factual de verification/acceptance cost.
5. Fazer precheck antes do verifier e post-accounting após execução.
6. Se o uso real ultrapassar o limite, persistir o uso e falhar fechado.
7. Uma tentativa deve contar quando começou/foi tentada, não apenas se retornou PASS.
8. Wall-clock deve vir do relógio do control-plane/verifier wrapper.
9. Tokens/money devem vir de usage metadata normalizada quando disponível.
10. Ausência de accounting obrigatório sob política estrita não pode virar zero silenciosamente.
11. Avaliar um `AcceptanceUsagePort`/`VerificationUsagePort` append-only para evitar reset/truncation após restart, possivelmente compartilhando o SQLite existente.
12. `verification_cost_units` é compatibilidade opaca e não deve ser reinterpretado como money/tokens/time.
13. A16 futuramente deve bindar a raiz/closure desse usage no terminal proof.

Fit provável:

```text
Inspect AI _limit.py limit/usage/remaining = ADAPT
Inspect AI scorer usage capture           = ADAPT
existing AcceptanceBudget                 = REUSE
metaO control-plane clock                  = REUSE
whole Inspect AI dependency                = NO
minimum BUILD                              = bound VerificationUsage + authoritative usage persistence/composition
```

A18 deve começar como issue + docs-only donor-fit. Não fazer implementação de produto antes de #91 ficar executable-green.

---

## 15. Regra operacional para bloqueios

Quando uma Work Unit ficar bloqueada:

```text
1. registrar BLOCKED com evidência concreta
2. não mascarar o blocker como PASS
3. seguir para o próximo bloco independente
4. voltar ao blocker quando a dependência estiver disponível
```

Exemplos atuais:

```text
#91 = BLOCKED até testes executáveis verdes + reconciliação da branch
#69 = BLOCKED pelo JSON real + eventual reconciliação da branch
A18 docs donor-fit = pode continuar independentemente
```

---

## 16. Regra de merge

Não mergear código de produto apenas porque GitHub mostra `mergeable=true`.

Para código:

```text
implementation complete
+ required executable tests green
+ scope/invariant audit green
+ explicit merge authorization
= eligible for merge
```

Docs-only podem ser consolidadas separadamente quando não alteram contratos/runtime e houver autorização explícita.

---

## 17. Ponto de retomada

Ao abrir novo chat, começar por:

```text
A18 AcceptanceBudget donor fit
```

Sem refazer a pesquisa anterior.

Depois:

```text
A18 donor-fit docs
→ voltar a #91 quando houver ambiente para rodar os testes
→ #91 executable-green
→ merge #91 com autorização explícita
→ A18 product implementation
→ A02 VerifierPort / VerifierRegistry
```

PR #69 permanece fluxo de release independente até o JSON real aparecer.
