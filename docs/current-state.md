# Estado Atual

## Resumo

O repositório hoje representa um simulador de microestrutura orientado a eventos, já com interface gráfica em `DearPyGui` e com a base heurística necessária para evoluir para RL. O ponto central é que o projeto ainda não é um ambiente MARL treinável; ele está na etapa de motor + agentes + observabilidade.

Snapshot usado como baseline desta organização:

- versão documentada: `v0.1.6`
- entrada principal: `app/main.py`
- runner padrão: `app/core/runner.py`

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
| Baseline reproduzível | Implementado | `BaselineScenario` em `app/core/runner.py`, seed fixa, horizonte padrão e métricas mínimas |
| Testes automatizados | Implementado | suíte de sanidade cobre `Kernel`, `ExchangeAgent`, contabilidade e reprodutibilidade do baseline |
| Base para RL | Parcial | `Agent` expõe `get_observation()` e `get_reward()`, mas não existe wrapper RL funcional |

## O Que Não Está Fechado

| Área | Status | Lacuna atual |
| --- | --- | --- |
| Interface `Gymnasium` / `PettingZoo` | Não implementado | não existe ambiente RL consumível |
| Sincronização para treino | Não implementado | `StopSignalAgent` ou equivalente não está presente no código-fonte |
| Espaços de observação e ação | Não implementado | ainda não há contrato formal treinável |
| Recompensa para RL | Não implementado | `get_reward()` continua vazio para a base heurística |
| Configuração reprodutível de experimentos | Parcial | o baseline padrão está fechado, mas ainda faltam variantes formais de benchmark |
| Avaliação experimental | Não implementado | faltam scripts, métricas e baselines para comparar resultados |

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
- `tests/`: suíte de sanidade do baseline

## Leitura Correta do Progresso

Se alguém quiser entender o projeto sem se perder:

1. Leia este arquivo para saber o que existe de verdade.
2. Leia `baseline-scenario.md` para ver o experimento padrão reproduzível.
3. Leia `next-steps.md` para ver o backlog ativo.
4. Use `archive/changelog/` para reconstruir a sequência das mudanças já feitas.

Esse fluxo separa claramente implementação atual, intenção futura e histórico.
