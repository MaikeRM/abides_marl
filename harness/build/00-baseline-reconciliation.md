# Phase 00 — Reconciliação do baseline e governança

Status: Complete

## Source inputs

- `README.md`
- `docs/current-state.md`
- `docs/next-steps.md`
- `docs/baseline-scenario.md`
- `pyproject.toml` e `uv.lock`
- `app/core/runner.py`, `app/core/kernel.py`, `app/agents/`
- `tests/`
- estado observado de `main`, `origin/main` e worktrees

## Objective

Definir uma fonte de trabalho inequívoca e tornar o baseline operacional um
contrato de experimento que possa ser reproduzido, auditado e passado para a
Fase 01.

## In scope

- Registrar a decisão sobre `main` versus `origin/main` e o wrapper candidato de
  `origin/claude/eager-leakey`.
- Alinhar a documentação ativa com o código atual e separar fatos de histórico.
- Definir a política para `InformedTrader`/`NoiseTrader` legados e para agentes
  usados no cenário padrão.
- Definir o formato mínimo do manifesto, métricas e trace canônico de uma
  execução.
- Definir comandos locais de verificação e o primeiro gate de CI, se aprovado.

## Non-goals

- Implementar o ambiente RL ou mudar a lógica de negociação.
- Fazer merge, rebase, push ou apagar worktrees.
- Remover agentes legados sem decisão registrada.
- Prometer reprodução de timestamps de parede.

## Dependencies and prerequisites

- Python `3.12.11`, `uv` e acesso ao worktree local.
- Decisão humana sobre o estado canônico do branch.

## Expected files or components

- Documentação ativa e harness do repositório.
- Manifesto/trace do baseline, caso a implementação seja aprovada nesta fase.
- Gate automatizado de CI, caso a política de integração seja aprovada.

## Decisions requiring human input

- Qual branch será a base oficial.
- Integrar, reescrever ou descartar o wrapper remoto.
- Manter, descontinuar ou remover os agentes legados.
- Formato e local dos artefatos de execução.

## Approval gate

Nenhum código de aplicação, teste novo, dependência ou alteração de Git começa
sem aprovar essas decisões e este escopo. A aprovação da fase não autoriza
merge, commit, push ou deploy.

## Red

- Criar um check de reprodução que compare duas execuções completas, incluindo
  o trace canônico. Ele deve falhar enquanto o trace incluir valores voláteis de
  `datetime.now()` ou enquanto não houver serialização canônica.
- Executar `git diff --check` e a verificação de alinhamento documental; registrar
  divergências observadas, sem corrigi-las fora do escopo aprovado.

## Green

- Registrar configuração, versão, seed, horizonte, métricas e um trace sem
  campos voláteis, ou separar explicitamente observabilidade de reprodução.
- Tornar a política de branch, agentes legados e wrapper remoto explícita.
- Fazer os checks de documentação e reprodução passarem.

## Refactor boundary

Pode reorganizar a configuração e a serialização do baseline sem alterar a
dinâmica econômica ou a ordem de processamento. Qualquer mudança em matching,
latência, contabilidade ou agentes passa para a Fase 01.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run python -m app.core.runner
git diff --check
```

Também executar duas vezes o baseline com a mesma seed e comparar os artefatos
canônicos byte a byte ou por hash documentado.

## Security, reliability, observability, and recovery

- Não persistir credenciais ou dados externos.
- Preservar o trace de falha e a configuração usada.
- Não tomar decisão destrutiva sobre branches ou worktrees sem aprovação.
- Recuperação: reverter apenas arquivos da fase por Git após registrar a falha;
  não usar reset destrutivo.

## Acceptance criteria

- [x] O branch e o estado candidato remoto estão classificados e a decisão está registrada.
- [x] O cenário padrão possui manifesto, seed, versão, horizonte e métricas definidos.
- [x] Duas execuções iguais produzem o mesmo artefato canônico.
- [x] Documentação ativa não atribui ao `main` comportamento que só existe em branch remoto.
- [x] Os comandos de verificação passam ou cada limitação está registrada.

## Evidence required

- Decisões humanas registradas em `GOALS.md`/`PLANS.md` ou no build log.
- Dois outputs ou hashes de execução.
- Resultados dos comandos acima em `harness/build-log.md`.
- Diff documental e lista final de arquivos.

## Observed evidence

- `uv run python -m unittest discover -s tests -v` — observado como pass no
  fechamento da fase, com 6 testes; a revalidação atual do mesmo contrato
  passou com 15 testes.
- `uv run python -m compileall -q app tests` — observado como pass.
- `uv run python -m app.core.runner` — observado como pass no baseline padrão.
- Duas execuções de
  `uv run python -m app.core.runner --max-time 120 --artifact-dir <tmp>`
  produziram artifacts byte a byte idênticos, com SHA-256
  `be9f7491ff59d7289dbad62f57e237763d0c932524a70c4493b166334ca15303`.
- `git diff --check` — observado como pass.
- O conjunto completo de comandos, hashes, limitações e a divergência entre
  worktree e branch remoto está registrado em
  [`../build-log.md`](../build-log.md).

## Handoff / stop condition

Parar quando o baseline tiver contrato de reprodução e a fonte de trabalho
estiver decidida. Entregar o contrato da Fase 01; não iniciar contabilidade ou
RL no mesmo ciclo.
