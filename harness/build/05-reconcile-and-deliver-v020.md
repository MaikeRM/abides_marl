# Phase 05 — Reconciliar e entregar o v0.2.0

Status: Not started

## Source inputs

- `AGENTS.md`, `GOALS.md` e `PLANS.md`
- `docs/current-state.md`, `docs/baseline-scenario.md`, `docs/next-steps.md`
- `harness/build-log.md` e contratos das Fases 00–04
- `app/core/runner.py`, `app/core/artifacts.py`, `tests/`
- estado observado de `HEAD`, `main`, `origin/main` e worktrees
- resultado atual do validador estrito do harness

## Objective

Transformar o estado local v0.2.0 em uma entrega tecnicamente reconciliada,
com documentação sem contradições, manifesto fiel ao horizonte executado e
prova separada entre worktree local, estado Git e clone limpo.

## In scope

- Corrigir a divergência entre `scenario.max_time` e o `max_time` efetivamente
  passado a `run_artifact()`.
- Adicionar uma regressão que falhe quando manifesto, métricas e trace
  declararem horizontes diferentes.
- Revalidar baseline padrão e baseline curto, preservando os hashes anteriores
  quando a mudança for somente de metadados.
- Fazer `validate_harness.py --strict` passar sem apagar evidência histórica.
- Reconciliar `GOALS.md`, `PLANS.md`, `docs/current-state.md`,
  `docs/next-steps.md` e `harness/build-log.md` com o código observado.
- Produzir uma matriz de proveniência: `HEAD`, worktree, `origin/main`,
  worktrees remotos e arquivos que compõem o v0.2.0 local.
- Definir o procedimento de instalação e reprodução em clone limpo; executá-lo
  somente com a autorização Git/infraestrutura correspondente.

## Non-goals

- Alterar matching, latência, contabilidade, reward ou comportamento econômico.
- Integrar ou remover branches, worktrees ou o wrapper remoto.
- Fazer commit, merge, rebase, push, publicação ou release externa.
- Corrigir dívidas de GUI, type checking ou performance que não sejam necessárias
  para a reconciliação da entrega.

## Dependencies and prerequisites

- Fases 00–04 concluídas no escopo local de engenharia.
- `uv` funcional e Python `3.12.11` disponível pelo projeto.
- Definição explícita de qual estado será chamado de entrega v0.2.0.
- Se houver clone remoto, autorização separada para operações Git e para o
  destino de qualquer cópia temporária.

## Expected files or components

- `app/core/runner.py` e teste de artifact/horizonte.
- `GOALS.md`, `PLANS.md`, `docs/current-state.md`, `docs/next-steps.md`.
- `harness/build-log.md` e contratos do harness.
- Relatório de verificação de clone limpo, caso a operação seja autorizada.

## Decisions requiring human input

- Qual commit/estado será a base oficial da entrega; o padrão recomendado é o
  estado local reconciliado, sem assumir que `origin/main` já o contém.
- Se a prova de clone limpo deve usar um remote existente ou uma cópia local
  do worktree, sem publicar nada.
- Se o artifact deve permanecer `baseline-artifact.v1` com correção compatível
  de metadados ou receber nova versão por mudança de schema.

## Approval gate

Pode-se corrigir documentação e adicionar o teste de horizonte no escopo desta
fase. Qualquer operação que altere histórico Git, remote, branch, publicação ou
infraestrutura deve parar e obter sua autorização específica.

## Red

- Criar um teste em que o cenário tenha `max_time=1000`, mas a execução peça
  `max_time=12`; ele deve falhar se o manifesto informar 1000 como horizonte
  efetivo.
- Executar o validador estrito antes da correção; os dois contratos históricos
  sem evidência devem ser identificados ou a ausência de finding deve ser
  explicada.
- Comparar a documentação ativa com o inventário do código e registrar cada
  divergência, sem converter plano em evidência.

## Green

- Manifesto, métricas e trace informam o horizonte realmente executado e
  preservam também o horizonte padrão do cenário quando necessário.
- O teste de regressão, suíte, compilação, lint e validador estrito passam.
- A documentação distingue claramente pronto local, pronto em clone limpo,
  smoke experimental e lacuna científica.
- A matriz de proveniência permite repetir o baseline sem depender da GUI.

## Refactor boundary

Pode extrair uma variável de horizonte efetivo e um serializer pequeno. Não
alterar o relógio, a ordem de eventos, o matching, a política econômica ou os
agentes.

## Verification commands

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests benchmarks
uv run ruff check app tests benchmarks
uv run python -m app.core.runner --artifact-dir <artifact-dir-a>
uv run python -m app.core.runner --artifact-dir <artifact-dir-b>
cmp <artifact-dir-a>/baseline.json <artifact-dir-b>/baseline.json
uv run python /Users/maikermota/.codex/skills/harness-author/scripts/validate_harness.py --repo . --harness-only --strict --json
uv run python /Users/maikermota/.codex/skills/harness-author/scripts/test_validate_harness.py
git diff --check
```

Se a prova de clone limpo for autorizada, repetir `uv sync --locked`, a suíte,
o baseline e a comparação do artifact dentro do clone, registrando o commit e
o caminho usados. `Unavailable` é resultado válido quando o ambiente externo
necessário não estiver autorizado ou disponível.

## Security, reliability, observability, and recovery

- Não copiar credenciais para o clone, logs ou artifacts.
- Manter os artifacts antigos antes de substituir qualquer output.
- Registrar o comando, configuração, commit/estado e hash de cada execução.
- Se o teste de horizonte alterar o schema, preservar um leitor compatível ou
  registrar a migração antes de mudar a versão.
- Recuperar somente os arquivos da fase; não usar reset destrutivo nem remover
  worktrees.

## Acceptance criteria

- [ ] O horizonte efetivo do artifact é correto e coberto por teste de regressão.
- [ ] A documentação ativa não contradiz o código ou o estado de integração.
- [ ] O harness estrito e seus testes passam com evidência registrada.
- [ ] A reprodução local do baseline continua byte a byte determinística.
- [ ] A proveniência entre worktree, branch, remote e clone limpo está explícita.
- [ ] Nenhuma operação Git externa ou publicação foi inferida como concluída.

## Evidence required

- Diff e teste que demonstram a correção do horizonte.
- Saídas completas da suíte, compilação, Ruff, comparação de artifacts e
  validador do harness.
- Matriz de estado Git e, se autorizada, log do clone limpo.
- Registro no build log com limitações, recuperação e handoff.

## Handoff / stop condition

Parar com a entrega local reconciliada ou com o bloqueio de clone limpo
explicitamente registrado. Só iniciar a Fase 06 quando o artifact e a fonte de
verdade documental estiverem estáveis.
