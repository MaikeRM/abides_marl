# Build log

## Status and evidence / Status e evidência

| Phase | Status | Branch | Started | Completed | Evidence | Blockers |
| --- | --- | --- | --- | --- | --- | --- |
| 00 — Baseline e governança | Complete | `main` | 2026-09-15T00:50-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/00-baseline-reconciliation.md); canonical artifact hashes | decisões registradas em `GOALS.md` |
| 01 — Core e contabilidade | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/01-core-contracts.md); contract tests | nenhuma |
| 02 — RL single-agent | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:08-03:00 | [phase file](build/02-rl-single-agent.md); Gymnasium checker | nenhuma |
| 03 — Treino e avaliação smoke | Complete | `main` | 2026-09-15T01:08-03:00 | 2026-09-15T01:12-03:00 | [phase file](build/03-marl-training-evaluation.md); checkpoint/evaluation JSON | avaliação científica segue para Fase 08 |
| 04 — Performance e release local | Complete | `main` | 2026-09-15T01:12-03:00 | 2026-09-15T01:15-03:00 | [phase file](build/04-performance-release.md); benchmark/CI config | CI remoto e type checking não observados |
| 05 — Reconciliar e entregar v0.2.0 | Not started | `main` | — | — | [phase file](build/05-reconcile-and-deliver-v020.md) | clone limpo, horizonte do artifact e integração |
| 06 — Core e semântica econômica | Not started | `main` | — | — | [phase file](build/06-core-contracts-and-economic-semantics.md) | decisões econômicas e regressão do baseline |
| 07 — Contrato científico RL | Not started | `main` | — | — | [phase file](build/07-rl-single-agent-research-contract.md) | API pública e terminalidade |
| 08 — Avaliação científica | Not started | `main` | — | — | [phase file](build/08-scientific-evaluation-protocol.md) | protocolo, holdout, ICs e limiares |
| 09 — Decisão MARL/PettingZoo | Not started | `main` | — | — | [phase file](build/09-marl-decision-and-optional-pettingzoo.md) | decisão de produto e custo da dependência |
| 10 — Escala e release verificável | Not started | `main` | — | — | [phase file](build/10-performance-scale-and-release.md) | benchmark longo, metas e pacote |


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
