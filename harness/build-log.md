# Build log

## Status and evidence / Status e evidência

| Phase | Status | Branch | Started | Completed | Evidence | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| 00 — Baseline e governança | Complete | `main` | 2026-09-15T00:50-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/00-baseline-reconciliation.md); canonical artifact hashes | decisões registradas em `GOALS.md` |
| 01 — Core e contabilidade | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/01-core-contracts.md); contract tests | nenhuma |
| 02 — RL single-agent | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/02-rl-single-agent.md); Gymnasium checker | nenhuma |
| 03 — Treino e avaliação smoke | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:12-03:00 | [phase file](build/03-marl-training-evaluation.md); checkpoint/evaluation JSON | avaliação científica segue para Fase 08 |
| 04 — Performance e release local | Complete | `main` | 2026-09-15T01:12-03:00 | 2026-09-15T01:15-03:00 | [phase file](build/04-performance-release.md); benchmark/CI config | CI remoto e type checking não observados |
| 05 — Reconciliar e entregar v0.2.0 | Complete local | `main` | 2026-09-15T13:00-03:00 | 2026-09-15T13:20-03:00 | [phase file](build/05-reconcile-and-deliver-v020.md); effective horizon, provenance | clone limpo e integração Git não autorizados |
| 06 — Core e semântica econômica | Complete local | `main` | 2026-09-15T13:20-03:00 | 2026-09-15T13:35-03:00 | [phase file](build/06-core-contracts-and-economic-semantics.md); 33 tests | promoção de perfil econômico é decisão futura |
| 07 — Contrato científico RL | Complete local | `main` | 2026-09-15T13:35-03:00 | 2026-09-15T13:45-03:00 | [phase file](build/07-rl-single-agent-research-contract.md); spec/checker | single-agent permanece por decisão de escopo |
| 08 — Avaliação científica | Complete plumbing local | `main` | 2026-09-15T13:45-03:00 | 2026-09-15T13:55-03:00 | [phase file](build/08-scientific-evaluation-protocol.md); paired v2 artifacts | limiar e campanha longa não aprovados |
| 09 — Decisão MARL/PettingZoo | Complete no-go condicionado | `main` | 2026-09-15T13:55-03:00 | 2026-09-15T14:00-03:00 | [phase file](build/09-marl-decision-and-optional-pettingzoo.md); ADR | reabrir somente com pergunta simultânea |
| 10 — Escala e release verificável | Complete local | `main` | 2026-09-15T14:00-03:00 | 2026-09-15T14:10-03:00 | [phase file](build/10-performance-scale-and-release.md); benchmark/profile | metas, type check, CI remoto e publicação abertos |


## Activity

### 2026-09-15T00:09:14-03:00 — Planning audit

- **Status:** `Not started`
- **Authorized scope:** criação do harness e alinhamento da documentação ativa; nenhuma fase de implementação autorizada.
- **Changes:** criado o conjunto inicial de objetivos, roadmap, contratos de fase, prompts e acordos duráveis; código de aplicação não foi alterado nesta etapa.
- **Red:** `Not applicable` para o harness; a auditoria identificou que o trace atual contém `datetime.now()` e que o projeto não possui contrato canônico de trace.
- **Green:** `Not applicable`; a implementação de fases ainda não começou.
- **Refactor:** `Not applicable`.
- **Verification:** `uv run python -m unittest discover -s tests -v` — observed pass, 6 testes; `uv run python -m compileall -q app tests` — observed pass; `uv run python -m app.core.runner` — observed pass, baseline com `final_time=1000`, `events_processed=79419`, `trade_count=196`, `traded_volume=314`, `last_trade=100.33`, `spread=0.54`; imports dos módulos da aplicação — observed pass; `git diff --check` — observed pass antes desta escrita.
- **Review:** auditoria estrutural com `graphify` no diretório `app`: 14 arquivos de código, 176 nós, 261 relações e 9 comunidades; resultado foi mantido fora do worktree.
- **Operational evidence:** nenhum segredo, sistema externo, branch, commit, push, deploy ou infraestrutura foi alterado.
- **Limitations:** não há CI, lint, type check, coverage, Gymnasium, PettingZoo ou pipeline de treinamento no `main`; o wrapper em `origin/claude/eager-leakey` é apenas candidato não integrado; o dashboard não foi aberto em sessão gráfica.
- **Blockers:** decisão sobre branch canônico, destino do wrapper remoto e contratos econômicos de reward/capital.
- **Next action:** aprovar e iniciar separadamente a Fase 00.
- **Evidence references:** `docs/current-state.md`, `docs/baseline-scenario.md`, `app/core/runner.py`, `tests/`, `pyproject.toml`, `uv.lock`, estado Git observado em `main` (`ahead 1, behind 2`).

### 2026-09-15T00:17:41-03:00 — Harness validation

- **Status:** `Planning complete; phases not started`
- **Authorized scope:** governança, inventário, roadmap e contratos de fase; não
  houve autorização para implementar RL, alterar o motor ou integrar o wrapper
  remoto.
- **Changes:** adicionados `AGENTS.md`, `GOALS.md`, `PLANS.md`, `PROMPTS.md`,
  `harness/build-log.md` e cinco contratos em `harness/build/`; documentação
  ativa atualizada em `docs/`; `.gitignore` passou a versionar explicitamente os
  contratos do harness sem liberar outros diretórios `build/`.
- **Red:** a primeira execução estrita encontrou oito avisos de seções não
  reconhecidas; os títulos foram alinhados ao contrato do validador.
- **Green:** `uv run python /Users/maikermota/.codex/skills/harness-author/scripts/validate_harness.py --repo . --strict --json` — observed pass, `valid=true`, zero warnings e zero errors; `uv run python /Users/maikermota/.codex/skills/harness-author/scripts/test_validate_harness.py` — observed pass, 13 testes.
- **Refactor:** corrigido somente o formato das seções e a regra de ignore dos
  contratos; nenhum comportamento de aplicação foi refatorado.
- **Verification:** `uv run python -m unittest discover -s tests -v` — observed
  pass, 6 testes; `uv run python -m compileall -q app tests` — observed pass;
  `uv run python -m app.core.runner` — observed pass, `final_time=1000`,
  `events_processed=79419`, `trade_count=196`, `traded_volume=314`,
  `last_trade=100.33`, `spread=0.54`; `git diff --check` — observed pass.
- **Versioning evidence:** os cinco arquivos em `harness/build/` aparecem como
  não rastreados versionáveis; não houve commit, push, merge, rebase ou deploy.
- **Limitations:** as lacunas científicas e de implementação permanecem
  intencionais e estão descritas em `GOALS.md`, `PLANS.md` e
  `docs/current-state.md`; a Fase 00 ainda requer decisão humana sobre branch
  canônico e destino do wrapper candidato.
- **Next action:** selecionar e aprovar a Fase 00; nenhuma fase posterior deve
  ser iniciada antes de seu handoff.
- **Evidence references:** `AGENTS.md`, `GOALS.md`, `PLANS.md`, `PROMPTS.md`,
  `harness/build/`, `docs/current-state.md`, `docs/next-steps.md` e o estado Git
  observado em `main` (`ahead 1, behind 2`).

### 2026-09-15T00:19:37-03:00 — Final planning audit

- **Status:** `Planning complete; ready for Phase 00 approval`
- **Evidence:** validador estrito do harness — observed pass, zero findings;
  suíte do projeto — observed pass, 6 testes; compilação — observed pass;
  `git diff --check` — observed pass.
- **Scope boundary:** nenhum arquivo de aplicação, dependência ou configuração
  de treinamento foi alterado; a mudança final foi somente editorial em
  `PROMPTS.md`.
- **Handoff:** o inventário está em `docs/current-state.md`, a visão curta em
  `docs/next-steps.md`, o roadmap em `PLANS.md` e os contratos executáveis em
  `harness/build/`. A próxima ação autorizável é a Fase 00.

### 2026-09-15T01:08:45-03:00 — Fases 00–02: baseline, core e ambiente RL

- **Status:** `Complete` para as Fases 00, 01 e 02; Fases 03–04 ainda não
  iniciadas.
- **Authorized scope:** o pedido explícito de implementar todas as fases,
  limitado pelas decisões conservadoras registradas em `GOALS.md`; nenhuma
  operação Git, publicação, dado real ou credencial foi usada.
- **Changes:** adicionado `BaselineArtifact` com manifesto, métricas, trace
  canônico e SHA-256; wall-time foi separado da trilha reprodutível; cenário e
  mensagens passaram a validar entradas; exchange passou a expor IDs de ambas
  as ordens e `trade_id` em cada fill; reset, snapshot público, lifecycle e
  rejeição de market sem liquidez foram fechados; adicionados `app/env` com
  `AbidesGymEnv` e `RLMarketAgent`; `gymnasium`, `numpy`, `ruff` e `coverage`
  foram fixados no manifesto/lock.
- **Red:** os testes novos de artifact sem wall-time, fill parcial com IDs,
  market sem liquidez, entrada inválida, reset e contrato Gym falhavam antes das
  implementações correspondentes.
- **Green:** `uv run python -m unittest discover -s tests -v` — observed pass,
  14 testes; `uv run python -m compileall -q app tests` — observed pass;
  `uv run ruff check app tests` — observed pass; checker oficial
  `gymnasium.utils.env_checker.check_env` — observed pass; smoke de três steps
  com `AbidesGymEnv` — observed pass, observação `(8,)`, `float32`, reward
  finito e truncation determinística.
- **Reproduction evidence:** duas execuções com
  `uv run python -m app.core.runner --max-time 120 --artifact-dir ...`
  produziram SHA-256
  `be9f7491ff59d7289dbad62f57e237763d0c932524a70c4493b166334ca15303`;
  cada trace tinha 7.648 eventos e hash
  `9a421fad1455295147c49947ac2d3a172ce9be0edc6f7b28839da76faff8634a`.
- **Refactor:** o runner deixou de depender da heap para controlar o loop
  público; `Kernel` expõe consulta de eventos e trace canônico; o ambiente usa
  `SimulationRunner.register_agent` e uma barreira de market-data para não
  devolver reward antes da liquidação dos eventos da ação.
- **Review:** o mapa estrutural com `graphify` encontrou 176 nós, 261 relações
  e 9 comunidades em `app`; os artefatos gerados foram movidos para `/tmp` e
  não ficaram no worktree.
- **Limitations:** capital/margem continuam política experimental simples;
  self-trade e short selling permanecem permitidos no core legado; o checker
  foi executado em cenário reduzido; o pipeline de treino ainda precisa ser
  implementado e avaliado.
- **Handoff:** a Fase 03 pode usar o ambiente single-agent validado e o
  protocolo de reward acima. A Fase 04 só deve usar números medidos, não
  suposições de throughput.

### 2026-09-15T01:15:00-03:00 — Fases 03–04: treino, avaliação, performance e release

- **Status:** `Complete` para as Fases 03 e 04; roadmap de implementação
  concluído no `main` local.
- **Authorized scope:** execução curta e local conforme o pedido do usuário;
  nenhum treino longo, deploy, publicação, capital ou integração externa foi
  iniciado.
- **Changes:** adicionado `TrainingConfig` versionado em
  `configs/smoke_training.json`; política linear `MultiDiscrete` e treino CEM
  NumPy em `app/experiments/train.py`; checkpoint `.npz`; avaliação
  independente em `app/experiments/evaluate.py` com três seeds e métricas de
  retorno, PnL, posição, trades e volume; comparação com
  `MarketMakerAgent`, `ValueAgent`, `ZeroIntelligenceAgent` e
  `LiquidityTrader`; benchmark headless em `benchmarks/`; workflow `.github`
  com sync locked, Ruff, compilação, cobertura, reprodução por `cmp` e smoke do
  benchmark; release experimental `0.2.0` e changelog.
- **Red:** antes do pipeline, o smoke de treino/checkpoint/avaliação não tinha
  módulo nem artefato; antes da Fase 04 não havia benchmark, gate de CI ou
  relatório de perfil.
- **Green:** `uv run python -m app.experiments.train --config
  configs/smoke_training.json --output-dir <tmp>` — observed pass, checkpoint
  criado e seeds `[11, 22, 33]`; `uv run python -m app.experiments.evaluate
  --checkpoint <tmp>/checkpoint.npz --config configs/smoke_training.json
  --output-dir <tmp>` — observed pass, três episódios e quatro tipos
  heurísticos; suíte final — observed pass, 15 testes; cobertura — observed
  pass, 60%, gate 55%; Ruff/compileall — observed pass; benchmark — observed
  pass, 3×2.000 eventos, média `94.311,765` eventos/s.
- **Profile:** `cProfile` em 1×500 eventos apontou 678 chamadas a
  `Kernel._record_event`; `/usr/bin/time -l` observou 0,14 s real e
  28.196.864 bytes de RSS máximo, sem swap. A decisão foi manter Python e
  preservar a trilha, conforme `docs/performance.md`.
- **Review:** o resultado de treino é smoke reproduzível, não evidência de
  superioridade; retornos da política foram finitos, mas o protocolo ainda não
  tem limiar estatístico aprovado. Type checking ficou explicitamente
  `Unavailable/by decision`, sem instalar `mypy` no legado.
- **Limitations:** não há PettingZoo, treino longo, intervalos de confiança,
  publicação de release, deploy ou conexão com dados reais; CI foi configurado,
  mas não executado por um runner GitHub nesta sessão.
- **Handoff:** o laboratório local está pronto para a próxima decisão humana
  sobre protocolo científico, MARL real e metas de escala. O objetivo de
  implementação das cinco fases está completo.

### 2026-09-15T12:30:31-03:00 — Auditoria de estado e planejamento pós-v0.2.0

- **Status:** `Planning update; implementation phases not started`.
- **Authorized scope:** inventariar o que está pronto, reconciliar a
  documentação ativa, registrar evidências atuais e criar o plano das Fases
  05–10. Nenhum código de aplicação, teste, dependência, infraestrutura ou
  operação Git foi alterado nesta atividade.
- **Observed ready state:** worktree local v0.2.0 com 15 testes, compilação,
  Ruff, coverage local de 60% com gate 55%, checker Gymnasium, baseline
  reproduzível, treino/evaluation smoke, benchmark headless e workflow de CI
  configurado.
- **Observed gaps:** o worktree de `main` está sujo e divergente de
  `origin/main`; a execução de `run_artifact(max_time=12)` produziu trace e
  métricas no horizonte 12, mas o manifesto ainda informou o horizonte 1000 do
  cenário; a avaliação não é pareada nem estatisticamente fechada; PettingZoo,
  treino longo, type checking, CI remoto e release pública não foram
  observados.
- **Red:** a validação estrita inicial do harness falhou com dois
  `verification-claim-without-evidence` em
  `harness/build/00-baseline-reconciliation.md` e
  `harness/build/03-marl-training-evaluation.md`.
- **Green target:** adicionar evidência observada a esses contratos e criar
  contratos separados para as Fases 05–10, mantendo o backlog não executado.
- **Refactor:** somente editorial; números históricos anteriores foram
  preservados e a auditoria atual não os trata como prova de clone limpo.
- **Verification observed before this update:**
  `uv sync --locked` — pass; `uv run python -m unittest discover -s tests -v` —
  pass, 15 testes; `uv run python -m compileall -q app tests benchmarks` —
  pass; `uv run ruff check app tests benchmarks` — pass; cobertura — pass,
  60% contra gate 55%; duas execuções do baseline curto — pass, artifact
  byte-identical com SHA-256
  `be9f7491ff59d7289dbad62f57e237763d0c932524a70c4493b166334ca15303`;
  `uv run python -m app.experiments.train` e `evaluate` — pass; benchmark
  curto — pass; `git diff --check` — pass; testes do validador do harness —
  pass, 13 testes.
- **Structural review:** `graphify` observou 22 arquivos de código, 292 nós,
  440 arestas e 12 comunidades; a saída foi mantida fora do worktree e esse
  mapa não substitui testes comportamentais.
- **Limitations:** a auditoria não executou clone limpo, runner de CI remoto,
  GUI interativa, treino longo, deploy ou publicação. As Fases 05–10 são
  planejamento, não evidência de implementação.
- **Handoff:** iniciar pela Fase 05; não iniciar a Fase 06 antes de fechar a
  reconciliação do artifact, documentação e prova de entrega local.

### 2026-09-15T12:45:00-03:00 — Validação final do pacote harness-author

- **Status:** `Planning package complete; Phase 05 not started`.
- **Changes:** reconciliados `GOALS.md`, `PLANS.md`,
  `docs/current-state.md` e `docs/next-steps.md`; adicionada evidência aos
  contratos históricos das Fases 00 e 03; criados os contratos das Fases 05–10.
  Nenhum arquivo de aplicação, teste, dependência, infraestrutura ou Git foi
  alterado nesta etapa.
- **Red:** a validação anterior tinha dois erros
  `verification-claim-without-evidence` em contratos completos históricos.
- **Green:**
  `uv run python /Users/maikermota/.codex/skills/harness-author/scripts/validate_harness.py --repo . --harness-only --strict --json`
  — observed pass, `valid=true`, zero warnings e zero errors; testes do
  validador — observed pass, 13 testes; `git diff --check` — observed pass.
- **Refactor:** somente organização editorial e planejamento; as fases novas
  permanecem `Not started` e não são tratadas como evidência de implementação.
- **Handoff:** a próxima unidade executável é a Fase 05, começando pela
  regressão do horizonte efetivo do artifact e pela reconciliação de clone
  limpo. Operações Git, CI remoto, publicação e deploy continuam fora deste
  pacote.

### 2026-09-15T13:00:00-03:00 — Fase 05: reconciliação local do artifact e da proveniência

- **Status:** `Complete local`; clone Git limpo e integração de histórico
  permanecem `Unavailable`/não autorizados.
- **Authorized scope:** corrigir o horizonte efetivo, contratos documentais e
  matriz de proveniência; não executar commit, merge, rebase, pull, push ou
  publicação.
- **Red:** o caso `scenario.max_time=1000` com `run_artifact(max_time=12)`
  reproduziu o manifesto incorreto como `1000` antes da mudança.
- **Green:** o mesmo caso passou a produzir `max_time=12` em manifesto e
  métricas; duas execuções `--max-time 120` passaram em `cmp`, com artifact
  `3be4ea5e87e43bd22efb0e60db20ba1eccdb5044787f58550be63df6028ebd1b` e trace
  `5fa5d9067458dc8672d30c35965b486fc221609298787e3605f0c1dd944ccbeb`.
- **Refactor:** `BaselineArtifact` valida a igualdade dos horizontes e o
  runner expõe a execução efetiva sem alterar o relógio ou o matching.
- **Verification:** `uv sync --locked` — observed pass; suíte — observed
  27/27 pass; compileall e Ruff — observed pass; harness estrito — observed
  `valid=true`, zero warnings/erros; testes do validador — observed pass,
  13 testes; cópia temporária sem `.git` em `/tmp/abides-clean-source.TZukRh`
  instalou e passou 27 testes, com artifact de 40 unidades
  `8edcec07a889ca7028d4e705c22025fb253762de3b3051a41e44cb3e09e5350c`.
- **Limitations:** a cópia source limpa não prova clone Git integrado; o
  estado `main` continua sujo e divergente de `origin/main` (`ahead 2,
  behind 2`).
- **Handoff:** Fase 06 iniciada somente após o artifact, a documentação e a
  limitação de proveniência estarem registradas.

### 2026-09-15T13:20:00-03:00 — Fase 06: contratos públicos e semântica econômica

- **Status:** `Complete local`.
- **Authorized scope:** lifecycle, snapshots, política econômica, contabilidade
  e regressões; nenhum agente legado foi removido e o baseline default foi
  preservado.
- **Red:** os novos casos de reservas, rejeições, fills parciais e expiração
  identificaram a necessidade de liberar reservas por quantidade preenchida e
  de limpar ordens no terminal.
- **Green:** 27 testes passaram, incluindo heap/`_order_map`, IDs de trade,
  cancelamento do owner, market sem liquidez, caixa/inventário/self-trade,
  taxas e mark-to-market.
- **Refactor:** `EconomicPolicy` versionada, `ExchangeAgent` lifecycle público,
  snapshots do kernel/runner, reconciliação formal e expiração `EXPIRED` foram
  adicionados sem mudar o perfil `legacy_unconstrained` implicitamente.
- **Verification:** `docs/economic-policy.md` documenta os perfis; artifacts
  registram `economic_policy`; `uv run python -m unittest discover -s tests -v`
  — observed 27/27 pass.
- **Limitations:** o perfil restrito é experimental e a implementação POV
  continua aproximada; nenhuma política foi promovida a risco financeiro real.
- **Handoff:** Fase 07 recebeu o contrato público de snapshots, lifecycle e
  terminalidade.

### 2026-09-15T13:35:00-03:00 — Fase 07: contrato científico RL single-agent

- **Status:** `Complete local`.
- **Authorized scope:** formalizar o executor single-agent e o adapter público;
  não instalar stack MARL nem retreinar uma política longa.
- **Red:** o horizonte de sim-time curto podia terminar como `terminated` sem
  indicar truncation; o teste de boundary expôs e corrigiu essa ambiguidade.
- **Green:** `EpisodeSpec`/`docs/rl-contract.md` congelam oito observações,
  `MultiDiscrete([5,20,10])`, reward, `info`, seed e precedência; todas as cinco
  ações, rejeição de posição, close e reset determinístico passaram.
- **Refactor:** o wrapper consome propriedades/métodos públicos do runner e
  limpa eventos no terminal; não depende de heap/map privado para operar.
- **Verification:** checker oficial Gymnasium — observed `gym checker: pass`
  (com apenas o warning esperado de render sem spec); suíte 27/27, compileall e
  Ruff — observed pass.
- **Limitations:** cancelamento permanece operação pública fora do vetor v1 e o
  contrato não constitui evidência de performance econômica.
- **Handoff:** Fase 08 recebeu papel, seeds, horizonte e métricas do episódio.

### 2026-09-15T13:45:00-03:00 — Fase 08: protocolo de avaliação científica

- **Status:** `Complete plumbing local`; aprovação de threshold/campanha longa
  permanece aberta.
- **Authorized scope:** adicionar protocolo pareado, baselines nulos, hashes,
  intervalos e gates; não declarar superioridade nem retunar em holdout.
- **Red:** a avaliação smoke anterior não separava a unidade pareada nem
  distinguia holdout de seeds de configuração; os testes de partição e hash
  foram adicionados antes do fechamento.
- **Green:** treino seguido de validation e holdout gerou
  `evaluation-result.v2`, seeds disjuntas, seis comparadores e decisão
  `inconclusive` com `minimum_effect=null`; nenhuma avaliação retreinou.
- **Refactor:** `EvaluationProtocol`, bootstrap determinístico, Bonferroni,
  `config_hash`, `checkpoint_sha256`, runtime metadata e proteção contra output
  não vazio foram centralizados em `app/experiments/`.
- **Verification:** `tests/test_protocol.py` e o teste de integração do
  protocolo observaram 27/27 pass; artifacts de validação/holdout ficaram em
  diretórios separados.
- **Limitations:** o adapter de cada heurística usa a mesma API Gym mas não é
  prova de identidade da implementação completa; threshold e orçamento humano
  ainda não foram configurados.
- **Handoff:** Fase 09 recebeu a decisão de produto baseada no escopo atual,
  sem inferir necessidade de controle simultâneo.

### 2026-09-15T13:55:00-03:00 — Fase 09: decisão MARL/PettingZoo

- **Status:** `Complete no-go condicionado`.
- **Authorized scope:** decidir necessidade e registrar ADR; não instalar
  PettingZoo nem alterar o caminho single-agent.
- **Red:** a pergunta atual foi testada contra a superfície single-agent e não
  exigiu coordenação de agentes controlados, crédito conjunto ou observação
  privada compartilhada.
- **Green:** `docs/marl-decision.md` compara wrapper próprio, AEC e Parallel,
  fixa critérios de reabertura e mantém o manifesto sem dependência nova.
- **Refactor:** nenhuma alteração no core foi necessária para simular MARL.
- **Verification:** suíte, checker e reprodução do baseline — observed pass;
  `pyproject.toml`/`uv.lock` não receberam PettingZoo.
- **Limitations:** uma nova hipótese verificável pode reabrir o no-go em fase
  própria, com orçamento e contrato de simultaneidade.
- **Handoff:** Fase 10 seguiu com o core headless e o wrapper single-agent como
  superfícies oficiais.

### 2026-09-15T14:00:00-03:00 — Fase 10: performance e release local

- **Status:** `Complete local`; metas aprovadas, type checking, CI remoto e
  publicação continuam gates separados.
- **Authorized scope:** benchmark/profiling, correção de inspeção da GUI, CI
  localizável e documentação de release; nenhuma otimização sem gatilho medido.
- **Red:** o benchmark anterior não expunha warmup, bytes do artifact ou
  orçamento; `_sync_agent` também tinha caminho de seleção inválida.
- **Green:** benchmark v2 em 3×20.000 eventos com warmup 1 observou média
  `56.813,971` eventos/s, mínimo `56.224,260`, máximo `57.673,398`, artifact
  médio `3.966.176` bytes e RSS delta `20.168.704` bytes. Perfil 1×1.000
  observou 1.224 eventos de trace; suíte de benchmark passou.
- **Refactor:** adicionado `benchmarks/profile_core.py`, budget explícito como
  `not_configured`, workflow mantém compile/lint/test/coverage/reprodução e a
  GUI agora falha de forma segura para seleção inexistente.
- **Verification:** 27/27 testes, cobertura `65%` com gate 55%, compileall,
  Ruff, baseline `--max-time 120` comparado e benchmark/profile — observed pass.
- **Limitations:** não houve sessão gráfica automatizada, runner CI remoto,
  type checking ou meta de recursos aprovada; release permanece apenas local.
- **Handoff:** roadmap local 00–10 fechado; próximos atos exigem decisão sobre
  clone Git, threshold científico, budgets ou publicação.

### 2026-09-15T14:31:47-03:00 — Regressão final pós-roadmap

- **Status:** `Complete local`; nenhuma operação Git ou publicação foi feita.
- **Red/green:** os contratos históricos de lifecycle, reset e artifact foram
  restaurados na suíte junto aos novos casos de policy, corrida assíncrona,
  RL, protocolo e benchmark; `uv run python -m unittest discover -s tests -v`
  observou 34/34 pass.
- **Verification:** `uv sync --locked`, compileall, Ruff, coverage `67%` com
  gate 55%, checker oficial Gymnasium, validador estrito do harness (`valid=true`,
  zero warnings/erros) e seus 13 testes passaram.
- **Baseline:** duas execuções de
  `uv run python -m app.core.runner --max-time 120 --artifact-dir <dir>` foram
  comparadas com `cmp`; artifact SHA-256
  `3be4ea5e87e43bd22efb0e60db20ba1eccdb5044787f58550be63df6028ebd1b` e trace
  `5fa5d9067458dc8672d30c35965b486fc221609298787e3605f0c1dd944ccbeb`.
- **Evaluation:** treino e avaliação via CLI geraram `evaluation-result.v2`
  com seeds de validação `[101, 102, 103]`, seeds de configuração
  `[11, 22, 33]`, seis comparadores e decisão `inconclusive`.
- **Performance:** benchmark final 3×20.000 observou média `54.138,646`
  eventos/s, mínimo `53.450,045`, máximo `55.311,462`, artifact médio
  `3.976.020` bytes e RSS delta `20.267.008` bytes; perfil 1×1.000 observou
  `0,083026458 s` e 1.224 eventos de trace.
- **Source snapshot:** cópia sem metadados Git instalou, passou 34 testes e
  reproduziu o artifact de 40 unidades; isso não substitui clone Git limpo.
- **Limitations:** clone Git integrado, CI remoto, type checking, budgets
  aprovados, threshold científico, smoke gráfico e publicação permanecem gates
  externos ou decisões humanas.

### 2026-09-15T14:47:26-03:00 — Revalidação dos artefatos finais

- **Status:** `Complete local`; documentação e evidências foram alinhadas ao
  estado atual do worktree, sem operação Git ou publicação.
- **Verification:** `uv run python -m unittest discover -s tests -v` — 34/34;
  coverage — 67% com gate 55%; compileall, Ruff, checker Gymnasium, validador
  estrito do harness (`valid=true`, zero warnings/erros) e seus 13 testes —
  pass.
- **Baseline:** duas execuções de `--max-time 120` passaram em `cmp`; artifact
  SHA-256 `c832e7a18bccd56435a7d204c928ff042766b8768c8207b67d90cc9153da1c0b`,
  trace `5fa5d9067458dc8672d30c35965b486fc221609298787e3605f0c1dd944ccbeb`,
  7.648 eventos no trace, 7.089 eventos processados, 23 trades, volume 40 e
  horizonte `{max_time: 120, max_events: null, final_time: 120}`.
- **Evaluation:** o CLI de treino/avaliação gerou `evaluation-result.v2` na
  validação com seeds `[101, 102, 103]`, configuração `[11, 22, 33]`, seis
  comparadores e decisão `inconclusive`; `minimum_effect=null` permanece
  fail-closed.
- **Performance:** benchmark 3×20.000 com warmup 1 observou média
  `55.566,564` eventos/s, mínimo `54.391,816`, máximo `57.465,650`, artifact
  médio `3.976.019,667` bytes e RSS delta `20.021.248` bytes; perfil 1×1.000
  observou `0,0740455 s`, 1.224 eventos de trace, artifact `224.286` bytes e
  trace `83dcf99e08c2459b4a4f316bbceb14b97f9f368339e4fd0460175733d02030b6`.
- **Source snapshot:** cópia sem `.git`, `.venv`, caches e `graphify-out`
  instalou com `uv sync --locked`, passou 34 testes e reproduziu duas vezes o
  artifact de `--max-time 40`: SHA `8edcec07a889ca7028d4e705c22025fb253762de3b3051a41e44cb3e09e5350c`,
  trace `4aa8aa9ef8adeab375baedd2682ad5ff53db8c8c5f23f97c38d2134c1b1b5a7a`.
- **Limitations:** clone Git integrado, CI remoto, type checking, budgets
  aprovados, threshold científico, smoke gráfico e publicação continuam
  gates externos ou decisões humanas.

### 2026-09-15T14:50:27-03:00 — Revalidação final de benchmark e perfil

- **Benchmark/profile:** a execução versionada passou com schema
  `core-benchmark.v2` e `core-profile.v1`; benchmark 3×20.000 com warmup 1
  observou média `59.042,319` eventos/s, mínimo `58.169,056`, máximo
  `60.316,534`, artifact médio `3.976.019,667` bytes e RSS delta
  `19.988.480` bytes. O perfil 1×1.000 observou `0,0732775 s`, 1.224 eventos
  de trace, artifact `224.286` bytes e manteve o trace hash
  `83dcf99e08c2459b4a4f316bbceb14b97f9f368339e4fd0460175733d02030b6`.
- **Scope:** `resource_budget.status=not_configured` permanece explícito; os
  números são medição local, não uma meta aprovada.

### 2026-09-15T22:37:56-03:00 — Integração Git do branch canônico

- **Status:** `Complete`; `main` integrado e sincronizado com `origin/main`.
- **Authorized scope:** autorização explícita para resolver conflitos, criar os
  commits pendentes e publicar com push normal; nenhum force push foi usado.
- **Changes:** o merge incorporou `origin/main` em `main`, preservando o
  harness v0.2.0 local e as correções remotas de observabilidade dos agentes e
  arredondamento de ticks. O merge commit é `9186302669d48ef259c3492384d9310d59305be5`.
- **Red:** o push inicial foi rejeitado por `non-fast-forward` porque `main`
  estava divergente (`ahead 3, behind 2`).
- **Green:** não há caminhos não mesclados nem marcadores de conflito; o push
  normal atualizou `origin/main` para `9186302`.
- **Verification:** 34/34 testes passaram; compileall e Ruff passaram; coverage
  ficou em `67%` com gate `55%`; benchmark smoke `core-benchmark.v2` passou; o
  runner padrão passou com `events_processed=80540`, `trade_count=198`,
  `traded_volume=313` e `last_trade=99.95`. Duas execuções do artifact em
  `--max-time 120` foram byte-idênticas: baseline SHA-256
  `97a565e6d63fcb5e39077dcecb413dc6749cbf84c94d0ebc3a2f7ed339f3e5f2` e
  trace hash `ae234b4410ca09942be135ba096eb97278728cf79d20385a85d5939c62c5f7ae`.
- **Limitations:** clone Git limpo, CI remoto, type checking, budgets aprovados
  e publicação como pacote/release continuam não validados; a avaliação
  científica permanece `inconclusive` por decisão fail-closed.
- **Handoff:** `main` está pronto para continuidade; qualquer nova alteração
  deve partir da referência remota sincronizada.
