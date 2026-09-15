# Estado Atual

## Resumo

O repositório hoje representa um simulador de microestrutura orientado a
eventos, com interface gráfica em `DearPyGui`, ambiente Gymnasium single-agent e
pipeline experimental curto de treino/avaliação. MARL simultâneo ainda não foi
adotado: a base atual é motor + agentes + observabilidade + um executor RL
controlável.

Snapshot usado como baseline desta organização:

- versão documentada: `v0.2.0`
- entrada principal: `app/main.py`
- runner padrão: `app/core/runner.py`

O planejamento de evolução e os gates de execução estão em [`../GOALS.md`](../GOALS.md), [`../PLANS.md`](../PLANS.md) e [`../harness/`](../harness/).

## O Que Está Implementado

| Área | Status | Observação |
| --- | --- | --- |
| Kernel de eventos | Implementado | fila por `heapq`, latência por par de agentes, histórico de eventos e atraso computacional |
| Exchange / LOB | Implementado | `LIMIT`, `MARKET`, cancelamento por `order_id`, price-time priority, consultas assíncronas de mercado |
| Oracle | Implementado | processo Ornstein-Uhlenbeck em `app/core/oracle.py` |
| Agentes heurísticos | Implementado | `MarketMakerAgent`, `ValueAgent`, `ZeroIntelligenceAgent`, `LiquidityTrader` |
| Contabilidade dos agentes | Implementado | posição, caixa, VWAP, PnL realizado, ordens ativas, histórico de trades |
| Dashboard | Implementado | order book, trades, logs, heatmap e tracker de agentes em `DearPyGui` |
| Encapsulamento de market data | Implementado | agentes consultam a exchange via mensagens `QUERY_*`, sem acesso direto ao objeto |
| Baseline reproduzível | Implementado | `BaselineScenario`, manifesto, métricas e trace canônico em `app/core/artifacts.py` |
| Testes automatizados | Implementado | 15 testes, Ruff, Coverage e checker Gymnasium |
| Ambiente RL | Implementado | `AbidesGymEnv` single-agent, barreira de market-data, espaços e reward incremental |
| Treino e avaliação | Implementado | NumPy/CEM curto, checkpoint, três seeds e comparação com heurísticas |
| Performance e CI | Implementado | benchmark headless, workflow de CI e decisão documentada de permanecer em Python |

## Inventário de Prontidão

### Pronto no worktree local auditado

- O baseline headless executa com seed fixa, cenário versionado, manifesto,
  métricas e trace canônico sem timestamps de parede.
- Kernel, exchange, contabilidade, runner e agentes possuem contratos de
  sanidade; a suíte atual tem 15 testes e passou localmente.
- `AbidesGymEnv` oferece um episódio single-agent com `reset`/`step`/`close`,
  barreira de market data, espaços definidos e reward incremental; o checker
  Gymnasium passou em cenário reduzido.
- O pipeline NumPy/CEM produz checkpoint e avaliação smoke com três seeds; isso
  demonstra execução, não superioridade econômica.
- Há Ruff, compilação, coverage local, benchmark headless e workflow de CI
  versionado. O workflow não foi executado por um runner remoto nesta auditoria.
- A GUI `DearPyGui` permite inspeção do livro, trades, eventos e agentes, mas
  permanece um caminho manual separado do laboratório headless.

### Pronto apenas como contrato de engenharia

| Área | Evidência atual | Leitura correta |
| --- | --- | --- |
| Reprodução | duas execuções do artifact curto produziram o mesmo SHA-256 | cobre o cenário/configuração exercitados; ainda falta prova em clone limpo |
| Treino | checkpoint e `evaluation.json` são gerados e reproduzíveis | smoke curto; não há holdout, IC, tamanho de efeito ou gate econômico |
| Performance | benchmark headless e perfil curto observados | não há série histórica, orçamento ou meta aprovada para escala |
| Release | versão `0.2.0`, changelog e CI configurados no worktree | não é uma release integrada/publicada |

### Lacunas e defeitos conhecidos

| Prioridade | Área | Lacuna observada | Destino |
| --- | --- | --- | --- |
| P0 | Entrega | o worktree de `main` está sujo e divergente de `origin/main`; o estado local ainda não foi provado em clone limpo | Fase 05 |
| P0 | Manifesto | `SimulationRunner.build_artifact()` registra `scenario.max_time` mesmo quando `run_artifact(max_time=...)` executa horizonte menor | Fase 05 |
| P1 | Core econômico | capital inicial zero, short selling/self-trade permitidos, sem política completa de margem, taxas e liquidação terminal | Fase 06 |
| P1 | Protocolo de ordens | rejeições, cancelamentos, market sem liquidez e fills parciais ainda precisam de um contrato público uniforme | Fase 06 |
| P1 | Ambiente RL | wrapper depende de internals do runner e não impõe sempre o horizonte do cenário; faltam testes para todas as ações e estados terminais | Fase 07 |
| P1 | Avaliação | política e heurísticas são executadas em populações/papéis não totalmente pareados; não há IC, efeito, holdout ou limiar estatístico | Fase 08 |
| P2 | MARL | não existe contrato PettingZoo nem decisão baseada em necessidade do produto | Fase 09 |
| P2 | Performance/release | CI remoto, type checking, benchmark longo, metas de recursos e pacote de release ainda não foram validados | Fase 10 |
| P2 | GUI | `_sync_agent` tem caminho de seleção inválida que pode usar `adata` antes de atribuição; não há smoke gráfico automatizado | Fase 10 |
| P3 | Agentes | `POVMarketMakerAgent` não implementa ainda a semântica completa de POV; agentes legados/variantes têm cobertura limitada | Fase 06/08 |

O código em worktrees ou branches remotos não representa funcionalidade
integrada até ser revisado, testado e incorporado ao estado canônico. Os itens
acima são backlog explícito, não evidência de que as fases futuras já estejam
concluídas.

## Leitura Rápida do Código

- `app/main.py`: dashboard `DearPyGui`
- `app/core/kernel.py`: agenda eventos, aplica latência e controla o relógio
- `app/core/runner.py`: monta e executa o baseline reproduzível da simulação
- `app/agents/exchange.py`: matching engine e protocolo de market data
- `app/agents/base.py`: interface comum e contabilidade dos agentes
- `app/agents/value_agent.py`: agente bayesiano baseado em valor
- `app/agents/zi_agent.py`: baseline zero-intelligence
- `app/agents/market_maker.py`: família de market makers
- `app/agents/liquidity.py`: agente de execução com urgência crescente
- `app/env/gym_env.py`: contrato Gymnasium e barreira de episódio
- `app/experiments/`: treino/evaluation e política NumPy
- `benchmarks/benchmark_core.py`: medição headless
- `tests/`: contratos do core, ambiente e pipeline smoke

## Leitura Correta do Progresso

Se alguém quiser entender o projeto sem se perder:

1. Leia este arquivo para saber o que existe de verdade.
2. Leia `baseline-scenario.md` para ver o experimento padrão reproduzível.
3. Leia `next-steps.md` para ver o backlog ativo.
4. Use `archive/changelog/` para reconstruir a sequência das mudanças já feitas.

Esse fluxo separa claramente implementação atual, intenção futura e histórico.
