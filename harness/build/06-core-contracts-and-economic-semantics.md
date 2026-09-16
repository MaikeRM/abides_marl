# Phase 06 — Contratos públicos e semântica econômica do core

Status: Complete (local)

## Source inputs

- contrato reconciliado da Fase 05
- `app/core/kernel.py`, `app/core/runner.py`
- `app/agents/exchange.py`, `app/agents/base.py`, `app/models/types.py`
- agentes em `app/agents/` e invariantes descritas em `AGENTS.md`
- `tests/test_kernel.py`, `tests/test_exchange.py`, `tests/test_accounting.py`
- `docs/baseline-scenario.md` e decisões de `GOALS.md`

## Objective

Tornar o motor de eventos, a exchange, o lifecycle das ordens e a contabilidade
contratos públicos, tipados o suficiente para falhar cedo e explícitos quanto à
semântica econômica usada em cada experimento.

## In scope

- Modelar estados de ordem, aceite, resting, execução parcial, execução total,
  cancelamento, rejeição e expiração/terminalidade.
- Padronizar mensagens de aceitação, rejeição, cancelamento, fill, consulta e
  ausência de liquidez, incluindo IDs, owner e quantidade remanescente.
- Expor snapshots públicos do livro, trades, relógio, agentes e métricas sem
  exigir acesso a heaps ou mapas privados.
- Testar invariantes do kernel, exchange e `_order_map` após cada mutação
  relevante, inclusive cancelamentos e fills concorrentes.
- Introduzir uma política econômica nomeada, preservando o comportamento legado
  como perfil explícito até existir comparação que autorize outra política.
- Fechar regras para capital, margem, short selling, self-trade, taxas,
  marcação, VWAP, PnL realizado/não realizado e liquidação terminal.
- Validar contabilidade contra o trade registrado e o histórico de ambas as
  pontas, com reconciliação de quantidade, caixa e posição.
- Cobrir agentes heurísticos usados no baseline e registrar o status das
  variantes, inclusive a semântica incompleta de POV.

## Non-goals

- Criar ambiente Gymnasium/PettingZoo ou alterar o algoritmo de treinamento.
- Otimizar `heapq`, migrar para JAX ou trocar a arquitetura por throughput.
- Remover agentes legados ou mudar o cenário padrão sem artifact de comparação.
- Conectar dados reais, corretoras, capital real ou serviços externos.

## Dependencies and prerequisites

- Fase 05 concluída.
- Baseline anterior preservado para regressão.
- Política econômica escolhida por nome e configurável, sem defaults implícitos.
- Orçamento para ampliar testes e revisar todos os caminhos de erro.

## Expected files or components

- `app/models/types.py`, `app/core/kernel.py`, `app/core/runner.py`.
- `app/agents/exchange.py`, `app/agents/base.py` e agentes afetados.
- schema/serializer de política econômica e snapshots públicos.
- testes unitários, de propriedade/invariante quando adequados e integração do
  runner.
- documentação da política e alteração do baseline apenas se aprovada.

## Decisions requiring human input

- Perfil padrão: manter `legacy_unconstrained` para compatibilidade ou adotar
  uma política com caixa/margem limitada como novo baseline.
- Permissão de short selling e self-trade; a recomendação é tornar ambos
  configuráveis e falhar de modo explícito quando proibidos.
- Modelo de taxas, tick, arredondamento, marcação de posição aberta e
  liquidação ao fim do episódio.
- Semântica de ordem MARKET sem liquidez e se rejeições são mensagens, exceções
  ou ambos em camadas diferentes.

## Approval gate

Nenhuma mudança de resultado econômico entra no baseline sem política nomeada,
teste de regressão, comparação de artifact e registro da decisão. Correções de
contrato mecânico podem avançar, mas qualquer alteração de caixa, PnL ou reward
deve ser tratada como mudança experimental.

## Red

- Adicionar testes que falhem para cada transição ausente do lifecycle e para
  qualquer duplicação/omissão no heap ou `_order_map`.
- Construir cenários de fill parcial dos dois lados, cancelamento do owner e
  tentativa de cancelamento por outro agente.
- Criar casos de market sem liquidez, preço/quantidade inválidos, self-trade,
  capital insuficiente e posição incompatível com a política escolhida.
- Testar reconciliação de caixa, posição, VWAP, PnL, active orders e trade log.

## Green

- A exchange retorna estados e IDs suficientes para reconciliar cada ordem e
  trade sem consultar internals.
- Toda mutação concluída deixa o livro não cruzado/locked e as estruturas
  internas consistentes.
- A política econômica é observável no artifact e não muda silenciosamente o
  baseline legado.
- Falhas de entrada não deixam estado parcial e são cobertas por testes.

## Refactor boundary

Pode extrair tipos, enums, validadores, policy objects e adapters públicos.
Não trocar o algoritmo de matching, o relógio do kernel ou o protocolo RL nesta
fase, salvo correção mínima necessária para manter os invariantes.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run ruff check app tests
uv run python -m app.core.runner --artifact-dir <before>
uv run python -m app.core.runner --artifact-dir <after>
git diff --check
```

Adicionar casos de erro e reconciliação ao conjunto de testes; repetir o
baseline anterior e o novo perfil econômico separadamente. Toda diferença de
hash precisa de explicação no build log.

## Security, reliability, observability, and recovery

- Mensagens e artifacts não devem conter credenciais ou dados externos.
- Erros devem preservar a causa, o order/trade ID e o estado seguro anterior.
- Logs devem separar sim-time de wall-time e permitir reconstruir o lifecycle.
- Não apagar agentes legados antes de registrar a decisão e uma substituição.
- Recuperar por revert dos arquivos da fase e restaurar artifacts preservados.

## Acceptance criteria

- [x] Lifecycle de ordens e trades é público, completo e testado.
- [x] Invariantes do kernel/exchange passam em cenários normais e de erro.
- [x] Política econômica nomeada governa capital, risco, taxas, marcação e fim.
- [x] Contabilidade reconcilia cada fill e não deixa estado parcial após falha.
- [x] Baseline e perfis novos são distinguíveis por configuração e artifact.
- [x] Agentes usados na avaliação têm cobertura e limitações documentadas.

## Evidence observed

- **Red/green:** `tests/test_exchange.py` e `tests/test_economic_policy.py`
  cobrem fills parciais, IDs, cancelamento autorizado, cancelamento indevido,
  market sem liquidez, ordem inválida, reservas, self-trade, caixa, inventário
  e expiração; a suíte integrada observou 34/34 pass.
- **Accounting:** `tests/test_accounting.py` observou posição, caixa, VWAP,
  taxas, PnL realizado e liquidação `mark_to_market` reconciliáveis.
- **Policy:** `legacy_unconstrained` permanece default e
  `cash_inventory_constrained` é registrado em `manifest.economic_policy` e
  `metrics.economic_policy`; não houve mudança silenciosa no baseline.
- **Public API:** `Kernel.snapshot()`, `SimulationRunner` snapshots,
  `ExchangeAgent.order_lifecycle`, `trades`, `rejections` e `get_*` retornam
  cópias públicas; a exchange valida heap/map após mutações.
- **Limitation:** `POVMarketMakerAgent` continua uma aproximação de POV e as
  variantes históricas não são promovidas a evidência de equivalência.

## Evidence required

- Testes red/green, saídas da suíte e exemplos de lifecycle.
- Tabela de decisão econômica e comparação dos artifacts antes/depois.
- Snapshots/logs que demonstrem as invariantes e reconciliação contábil.
- Handoff no build log com mudanças de semântica explicitadas.

## Handoff / stop condition

Parar quando o core puder ser consumido por um agente externo apenas por APIs
públicas e quando a política econômica estiver congelada para o protocolo RL.
Entregar a especificação final de episódio para a Fase 07.
