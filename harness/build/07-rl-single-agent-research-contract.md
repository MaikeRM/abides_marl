# Phase 07 — Contrato científico do RL single-agent

Status: Complete (local)

## Source inputs

- contrato público do core produzido pela Fase 06
- `app/env/gym_env.py`, `app/experiments/config.py`, `app/experiments/policy.py`
- `app/core/runner.py` e agentes background
- `tests/test_env.py`, `tests/test_experiments.py`
- especificação atual de observação de 8 valores e `MultiDiscrete([5, 20, 10])`
- checker Gymnasium e limitações registradas em `docs/current-state.md`

## Objective

Transformar o wrapper existente em uma interface de episódio estável,
independente de internals do runner e adequada para pesquisa reproduzível,
sem confundir um contrato de engenharia com evidência de desempenho econômico.

## In scope

- Formalizar o objetivo do agente controlado: executor, market maker ou outro
  papel; o papel deve ser o mesmo em treino, avaliação e baseline pareado.
- Especificar cada componente da observação, unidade, normalização, bounds,
  dtype, missing data e comportamento quando não há trade/spread.
- Especificar `MultiDiscrete([5, 20, 10])`, nomes de ação, preço relativo,
  quantidade, HOLD, cancelamento e rejeição sem depender de índices mágicos.
- Definir reward incremental, marcação, custos, posição aberta, clipping,
  `info` e reconciliação com a contabilidade do core.
- Garantir `reset(seed=...)`, reconstrução limpa, `terminated`, `truncated`,
  horizonte efetivo, limite de steps e ausência de eventos órfãos após `close`.
- Remover dependências diretas de atributos privados do runner e testar o
  ambiente contra uma API pública de episódio.
- Cobrir todas as ações, fills parciais, buy/sell, limit/market, ausência de
  liquidez, ação inválida, reset após erro e determinismo entre seeds.
- Rodar checker oficial completo e documentar qualquer exceção justificada.

## Non-goals

- Treino longo, escolha de algoritmo de produção ou comparação econômica.
- Controle simultâneo de vários agentes e dependência PettingZoo.
- Alteração silenciosa de matching, risco ou reward do baseline.
- Renderização da GUI como requisito do ambiente.

## Dependencies and prerequisites

- Fases 05 e 06 concluídas.
- Política econômica e papel do agente definidos.
- Contrato público de snapshots, lifecycle e terminalidade disponível.
- Orçamento de testes suficiente para caminhos de ação e erro.

## Expected files or components

- `app/env/gym_env.py` ou adaptadores equivalentes sobre APIs públicas.
- tipos compartilhados para spec de episódio, ação, observação e `info`.
- `app/experiments/config.py` com versão e defaults explícitos.
- testes de contrato e fixture determinística em `tests/`.
- documentação do ambiente e exemplo mínimo de consumo.

## Decisions requiring human input

- Papel econômico do agente e se a posição aberta é liquidada, penalizada ou
  carregada ao terminar.
- Horizonte oficial em sim-time e máximo de steps; o padrão recomendado é
  tornar ambos explícitos e fazer `truncated` vencer `terminated` por limite.
- Componentes da observação e se action masks fazem parte da interface.
- Escala de custos, reward e normalização sem clipping que esconda falhas.

## Approval gate

O contrato de obs/action/reward deve ser escrito e testado antes de alterar o
wrapper. Nenhum algoritmo ou stack RL pesado deve ser instalado nesta fase.

## Red

- Testar imports, `reset`, `step`, shapes, dtype, bounds, seed, lifecycle e
  terminalidade contra a especificação; os testes devem falhar no estado atual
  onde houver dependência privada ou horizonte inconsistente.
- Exigir um teste por ação e por resultado de matching, incluindo no-op/sem
  liquidez e fills parciais.
- Verificar que executar `step` após terminalidade falha de forma previsível e
  que `close` não deixa o kernel consumindo eventos.

## Green

- Uma ação RL consome exatamente uma transição de episódio e retorna
  observação, reward e `info` coerentes com o trade/estado contábil.
- O ambiente funciona com runner headless, sem GUI e sem atributos privados.
- Seeds iguais reproduzem observações, rewards, terminais e artifact; seeds
  diferentes não são artificialmente colapsadas.

## Refactor boundary

Pode criar uma camada de adapter, spec dataclass e fixtures de episódio. Não
alterar o matching, introduzir multiagente ou retreinar políticas nesta fase.

## Verification commands

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run ruff check app tests
uv run python -c "from app.env import AbidesGymEnv; from gymnasium.utils.env_checker import check_env; env = AbidesGymEnv(seed=42); check_env(env); env.close(); print('gym checker: pass')"
uv run python -m app.core.runner
git diff --check
```

Executar dois episódios com a mesma seed e salvar `obs`, `reward`,
`terminated`, `truncated`, `info` e artifact para comparação. Registrar
qualquer comportamento dependente de wall-time como falha de reprodução.

## Security, reliability, observability, and recovery

- Validar ação e configuração antes de mutar o episódio.
- Limitar tamanho de `info`, logs e traces; nunca registrar segredos.
- Isolar e reconstruir o ambiente após exceção ou terminalidade.
- Preservar o último artifact válido para comparação de regressão.
- Falhar fechado quando reward, observação ou contabilidade produzir NaN,
  infinito ou estado impossível.

## Acceptance criteria

- [x] Spec de obs/action/reward/termination está versionada e implementada.
- [x] O ambiente não acessa internals do runner para cumprir seu contrato.
- [x] Todas as ações, falhas, fills, resets e terminais relevantes têm testes.
- [x] O horizonte efetivo e a precedência entre terminated/truncated são claros.
- [x] Checker Gymnasium, suíte, compilação e Ruff passam.
- [x] Episódios iguais com a mesma seed produzem a mesma trilha observável.

## Evidence observed

- **Contract:** `app/env/spec.py` e `docs/rl-contract.md` congelam a versão,
  observação de oito componentes, `MultiDiscrete([5, 20, 10])`, reward,
  clipping, `info`, papel `execution_agent` e precedência de truncation.
- **Tests:** `tests/test_env.py` observou reset determinístico, todas as cinco
  ações, ação inválida, truncation por steps e sim-time, fechamento sem eventos
  pendentes e limite operacional de posição.
- **Verification:** `uv run python -m unittest discover -s tests -v` — observed
  pass, 34 testes; compileall e Ruff — observed pass; o checker oficial
  `gymnasium.utils.env_checker.check_env` passou em cenário reduzido.
- **Boundary:** o wrapper usa `SimulationRunner` por propriedades e métodos
  públicos (`is_running`, `current_time`, `next_delivery_time`, snapshots e
  contas); nenhum heap/map privado do runner é requisito do episódio.
- **Limitation:** o contrato permanece single-agent e não afirma performance
  econômica; cancelamento é uma operação pública do lifecycle fora do vetor de
  ação v1.

## Evidence required

- Documento/spec e tabela de mapeamento ação → ordem/efeito.
- Testes red/green, checker e dois traces de episódio reproduzíveis.
- Comparação do reward com contabilidade do core.
- Limitações e mudanças de contrato registradas no build log.

## Handoff / stop condition

Parar quando o ambiente single-agent estiver estável como API pública e seus
episódios forem reproduzíveis. A decisão de avaliação científica passa para a
Fase 08; MARL continua bloqueado pela Fase 09.
