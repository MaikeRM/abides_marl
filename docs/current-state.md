# Estado Atual

## Resumo

O repositório hoje representa um simulador de microestrutura orientado a
eventos, com interface gráfica em `DearPyGui`, ambiente Gymnasium single-agent,
pipeline experimental pareado e benchmark headless. MARL simultâneo ainda não
foi adotado: a base atual é motor + agentes + observabilidade + um executor RL
controlável, com políticas econômicas explícitas.

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
| Política econômica | Implementado | perfis nomeados, taxas, reservas, risco, marcação e liquidação terminal |
| Lifecycle público | Implementado | estados, IDs, fills parciais, rejeições, cancelamento e expiração |
| Dashboard | Implementado | order book, trades, logs, heatmap e tracker de agentes em `DearPyGui` |
| Encapsulamento de market data | Implementado | agentes consultam a exchange via mensagens `QUERY_*`, sem acesso direto ao objeto |
| Baseline reproduzível | Implementado | `BaselineScenario`, manifesto, métricas e trace canônico em `app/core/artifacts.py` |
| Testes automatizados | Implementado | 34 testes, Ruff, Coverage e checker Gymnasium |
| Ambiente RL | Implementado | `EpisodeSpec` versionado, barreira de market-data, espaços, reward e terminalidade |
| Treino e avaliação | Implementado | NumPy/CEM curto, hashes, pareamento, validação/holdout/stress e gate fail-closed |
| Performance e CI | Implementado localmente | benchmark v2, `cProfile`, workflow de CI e decisão documentada de permanecer em Python |

## Inventário de Prontidão

### Pronto no branch canônico integrado

- O baseline headless executa com seed fixa, cenário versionado, manifesto,
  métricas e trace canônico sem timestamps de parede; o manifesto registra o
  horizonte efetivo solicitado.
- Kernel, exchange, contabilidade, runner e agentes possuem contratos de
  sanidade; a suíte atual tem 34 testes e passou localmente.
- `EconomicPolicy` explicita o perfil legado e o perfil restrito; lifecycle,
  reservas, reconciliação e expiração terminal são observáveis por APIs públicas.
- `AbidesGymEnv` oferece um episódio single-agent com `reset`/`step`/`close`,
  barreira de market data, `EpisodeSpec`, espaços definidos e reward incremental;
  todas as ramificações de ação e o checker Gymnasium passaram em cenário reduzido.
- O pipeline NumPy/CEM produz checkpoint e avaliação pareada em seeds disjuntas;
  o artifact classifica a campanha como `inconclusive` sem limiar humano, não
  como superioridade econômica.
- Há Ruff, compilação, coverage local, benchmark v2, perfilamento headless e
  workflow de CI versionado. O workflow não foi executado por um runner remoto.
- O branch `main` está limpo e sincronizado com `origin/main`; a integração
  preservou as mudanças locais e remotas sem force push.
- A GUI `DearPyGui` permite inspeção do livro, trades, eventos e agentes, mas
  permanece um caminho manual separado do laboratório headless.

### Pronto apenas como contrato de engenharia

| Área | Evidência atual | Leitura correta |
| --- | --- | --- |
| Reprodução | duas execuções pós-merge do artifact curto produziram o mesmo SHA-256 | cobre o cenário/configuração exercitados; ainda falta prova em clone limpo |
| Treino/avaliação | checkpoint, hashes, pareamento, IC bootstrap e splits são gerados | campanha curta; `minimum_effect` está ausente e o gate permanece inconclusivo |
| Performance | benchmark v2 e `cProfile` registram ambiente, dispersão, trace e bytes | budgets de RSS/latência/throughput ainda não foram aprovados |
| Release | versão `0.2.0`, changelog e CI configurados e integrados em `origin/main` | publicação como pacote/release continua não validada |

### Lacunas e defeitos conhecidos

| Prioridade | Área | Lacuna observada | Destino |
| --- | --- | --- | --- |
| P1 | Avaliação | o protocolo é executável e pareado, mas o limiar mínimo de efeito e o orçamento de campanha continuam decisões humanas | Fase 08 |
| P2 | Performance/release | CI remoto, type checking, metas aprovadas e instalação de pacote publicado ainda não foram validados | Fase 10 |
| P2 | GUI | a seleção inválida foi corrigida, mas não há smoke gráfico automatizado nesta sessão | Fase 10 |
| P3 | Agentes | `POVMarketMakerAgent` ainda é uma aproximação de POV; variantes legadas têm cobertura limitada | pós-roadmap |

O código em worktrees ou branches remotos não representa funcionalidade
integrada até ser revisado, testado e incorporado ao estado canônico. Os itens
acima são backlog explícito, não evidência de que as fases futuras já estejam
concluídas.

## Leitura Rápida do Código

- `app/main.py`: dashboard `DearPyGui`
- `app/core/kernel.py`: agenda eventos, aplica latência e controla o relógio
- `app/core/runner.py`: monta e executa o baseline reproduzível da simulação
- `app/core/economic.py`: perfis econômicos versionados
- `app/agents/exchange.py`: matching engine e protocolo de market data
- `app/agents/base.py`: interface comum e contabilidade dos agentes
- `app/agents/value_agent.py`: agente bayesiano baseado em valor
- `app/agents/zi_agent.py`: baseline zero-intelligence
- `app/agents/market_maker.py`: família de market makers
- `app/agents/liquidity.py`: agente de execução com urgência crescente
- `app/env/gym_env.py`: contrato Gymnasium e barreira de episódio
- `app/env/spec.py`: especificação versionada de episódio/ação/observação
- `app/experiments/`: treino/evaluation e política NumPy
- `benchmarks/benchmark_core.py`: medição headless repetida
- `benchmarks/profile_core.py`: perfilamento `cProfile` do core
- `tests/`: contratos do core, ambiente e pipeline smoke

## Leitura Correta do Progresso

Se alguém quiser entender o projeto sem se perder:

1. Leia este arquivo para saber o que existe de verdade.
2. Leia `baseline-scenario.md` para ver o experimento padrão reproduzível.
3. Leia `next-steps.md` para ver o backlog ativo.
4. Use `archive/changelog/` para reconstruir a sequência das mudanças já feitas.

Esse fluxo separa claramente implementação atual, intenção futura e histórico.
