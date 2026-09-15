# Phase 01 — Contratos do core, contabilidade e reprodução

Status: Complete

## Source inputs

- `app/core/kernel.py`
- `app/core/runner.py`
- `app/agents/exchange.py`
- `app/agents/base.py`
- `app/models/types.py`
- `app/core/oracle.py`
- `tests/test_kernel.py`, `tests/test_exchange.py`, `tests/test_accounting.py`, `tests/test_runner_baseline.py`
- contrato aprovado da Fase 00

## Objective

Fechar os contratos mecânicos que sustentam experimentos comparáveis: tempo,
ordens, fills, contabilidade, reset, métricas e falhas de entrada.

## In scope

- API pública do runner para executar por horizonte/eventos sem depender de
  estruturas privadas quando isso for necessário.
- Validação de configuração, mensagens, ordens, preços, quantidades e tipos.
- Semântica completa de lifecycle da ordem, incluindo IDs de ambos os lados do
  trade e reconciliação de ordens parciais.
- Invariantes do heap, `_order_map`, livro cruzado, cancelamento e prioridade.
- Política de capital inicial, margem, posição, VWAP, PnL marcado e reward
  incremental, após decisão humana.
- Reset de kernel, exchange, oracle, agentes e seeds.
- Testes de borda e métricas canônicas.

## Non-goals

- Espaços Gymnasium, sincronização RL ou treinamento.
- Mudança de modelo econômico sem hipótese e critério de avaliação.
- Otimização prematura da estrutura de dados.

## Dependencies and prerequisites

- Fase 00 completa.
- Decisões sobre capital, margem, marcação e reward.

## Expected files or components

- `app/core/kernel.py`, `app/core/runner.py`, `app/agents/exchange.py`,
  `app/agents/base.py`, `app/models/types.py`.
- Testes unitários e integrados em `tests/`.
- Schema ou serializer de configuração/trace, se a Fase 00 o exigir.

## Decisions requiring human input

- Permitir short selling e self-trade.
- Capital/margem e comportamento quando não há caixa ou inventário.
- Marca de mercado por último trade, mid ou liquidação conservadora.
- Reward baseado em PnL, shortfall, risco ou combinação.

## Approval gate

Os contratos econômicos devem ser aprovados antes de mudar contabilidade ou
reward. Uma alteração de interface que afete o ambiente RL precisa ser
registrada para a Fase 02.

## Red

- Adicionar testes para ordens de mercado sem liquidez, fills parciais em ambos
  os lados, cancelamento em lote, IDs de fill, reset, entradas inválidas,
  invariantes e reprodução do trace.
- Esses testes devem falhar contra qualquer comportamento ausente no contrato.

## Green

- Implementar apenas as validações, lifecycle, contabilidade e reset necessários
  para os testes vermelhos.
- Expor métricas e trace estáveis sem alterar a prioridade preço-tempo aprovada.

## Refactor boundary

Pode extrair tipos, serializers e validadores pequenos. Não separar serviços,
trocar `heapq` ou introduzir dependência de RL nesta fase.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run python -m app.core.runner
git diff --check
```

Adicionar, quando disponível, cobertura e type check como gates separados e
registrar o resultado real.

## Security, reliability, observability, and recovery

- Entradas inválidas devem falhar de modo explícito e não corromper o livro.
- Logs e traces devem distinguir sim-time de wall-time.
- Testar recuperação após uma falha de mensagem/configuração sem manter estado
  parcial de episódio.
- Preservar outputs do baseline anterior para comparar regressões.

## Acceptance criteria

- [x] Toda ordem resting tem lifecycle e ID reconciliáveis.
- [x] O livro e `_order_map` permanecem consistentes após cada mutação testada.
- [x] Contabilidade conserva quantidade, caixa, posição e PnL conforme a política aprovada.
- [x] Reset produz estado inicial idêntico para a mesma seed.
- [x] Casos de borda e entradas inválidas têm testes observáveis.
- [x] O baseline antigo não sofre regressão nos seus critérios aprovados.

## Evidence required

- Testes novos com falha red e passagem green.
- Output de baseline antes/depois ou justificativa para mudança esperada.
- Resultado de todos os comandos e limitações no build log.
- Decisões econômicas apontadas por link e aprovadas.

## Handoff / stop condition

Parar quando os contratos do core estiverem estáveis e o agente de teste puder
ser conduzido por uma API de episódio sem acessar internals. Entregar a
especificação de observação/ação/reward para a Fase 02.
