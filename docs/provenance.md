# Proveniência da entrega local

Este documento separa o estado que foi executado do estado que está integrado
em Git. A implementação desta rodada foi validada no worktree de `main`; ela
continua sem commit, merge, rebase, push ou publicação.

## Snapshot Git observado em 2026-09-15

| Referência | Valor | Leitura |
| --- | --- | --- |
| branch de trabalho | `main` | fonte local autorizada |
| `HEAD` | `c8596e1ee08e6316a7237db204095fab80e57acb` | último commit anterior às mudanças desta rodada |
| `origin/main` | `bfa25e66f2bebc120e7a838fe6f2a49c59127800` | estado remoto observado, não atualizado |
| divergência | `ahead 2, behind 2` | não há reconciliação de histórico implícita |
| worktree `eager-leakey` | `8a89f8b6551fc3581f11df8c1da74b04bb2e4c09` | estado separado, não integrado |
| worktree `happy-mclaren` | `12aec3563a20dff04a975c9c1cb8361430df25a4` | estado separado, não integrado |
| mudanças locais | presentes | são o estado auditado nesta rodada |

Os hashes e worktrees foram observados com `git rev-parse`, `git status` e
`git worktree list --porcelain`. Nenhuma referência remota ou worktree foi
alterada.

## O que compõe o estado local auditado

- `app/core/`: kernel, exchange-facing runner, artifact e política econômica;
- `app/agents/` e `app/models/`: lifecycle, fills, contabilidade e agentes;
- `app/env/`: `EpisodeSpec` e wrapper Gymnasium single-agent;
- `app/experiments/` e `configs/`: treino NumPy/CEM e protocolo pareado;
- `benchmarks/`: benchmark repetido e perfilamento `cProfile` headless;
- `tests/`: regressões do core, economia, ambiente, protocolo e benchmark;
- `docs/`, `GOALS.md`, `PLANS.md` e `harness/`: contratos e evidências.

## Evidência executada

O artifact curto local de duas execuções idênticas foi byte-a-byte igual:

- comando: `uv run python -m app.core.runner --max-time 120 --artifact-dir <dir>`;
- SHA-256 do JSON: `c832e7a18bccd56435a7d204c928ff042766b8768c8207b67d90cc9153da1c0b`;
- SHA-256 do trace: `5fa5d9067458dc8672d30c35965b486fc221609298787e3605f0c1dd944ccbeb`;
- horizonte: `max_time=120`, `final_time=120`, `7648` eventos de trace.

O protocolo de avaliação gerou artifacts separados para validação e holdout,
com decisão `inconclusive`, porque `minimum_effect` permanece `null` no arquivo
versionado. Isso valida o plumbing e não autoriza uma conclusão econômica.

Como verificação auxiliar, uma cópia do source sem `.git`, `.venv`, caches ou
`graphify-out` foi instalada com `uv sync --locked`, passou 34 testes e
`compileall`, e reproduziu duas vezes o artifact de `--max-time 40`. O SHA-256
observado foi `8edcec07a889ca7028d4e705c22025fb253762de3b3051a41e44cb3e09e5350c`
e o trace foi
`4aa8aa9ef8adeab375baedd2682ad5ff53db8c8c5f23f97c38d2134c1b1b5a7a`. Essa
cópia reduz o risco de arquivos ignorados, mas não é um clone Git integrado.

## Clone limpo e publicação

Prova em clone limpo: `Unavailable` nesta rodada. O ambiente não autorizou
clone/pull nem alteração de histórico remoto, e o estado atual ainda não tem
um commit que contenha as mudanças locais. Uma cópia limpa do source pode ser
testada localmente para reduzir risco de arquivos ignorados, mas não substitui
a prova de instalação de um clone Git integrado.

Release pública, tag, pacote publicado, deploy, credenciais e integração com
corretora continuam fora do escopo.
