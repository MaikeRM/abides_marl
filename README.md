# ABIDES-MARL PoC

Simulador de mercado multiagente inspirado em ABIDES e ABIDES-MARL, com kernel de eventos discretos, limit order book com prioridade preco-tempo, agentes heurísticos e dashboard em `DearPyGui`.

## Status Atual

- Snapshot documentado do repositório: `v0.1.6`
- Interface principal atual: `DearPyGui` em [`app/main.py`](app/main.py)
- Motor de simulação atual: kernel assíncrono, exchange CDA, `MarketMaker`, `ValueAgent`, `ZeroIntelligenceAgent` e `LiquidityTrader`
- Baseline experimental atual: cenário reproduzível em [`app/core/runner.py`](app/core/runner.py) com seed fixa, métricas mínimas e suíte de sanidade
- Próxima fronteira do projeto: interface RL (`Gymnasium`/`PettingZoo`), treinamento MARL e validação experimental

## Execução

Requisitos:

- Python `==3.12.11`

Instalação com `uv`:

```bash
uv sync
```

Execução:

```bash
uv run python -m app.main
```

Alternativa com ambiente ativo:

```bash
python -m app.main
```

## Baseline e Testes

Rodar a suíte de sanidade:

```bash
uv run python -m unittest discover -s tests -v
```

Rodar o baseline reproduzível e imprimir métricas:

```bash
uv run python -m app.core.runner
```

## Onde Ler Primeiro

- [`docs/README.md`](docs/README.md): índice de documentação
- [`docs/current-state.md`](docs/current-state.md): o que já foi implementado
- [`docs/baseline-scenario.md`](docs/baseline-scenario.md): cenário padrão reproduzível e métricas
- [`docs/next-steps.md`](docs/next-steps.md): o que ainda falta
- [`docs/repository-map.md`](docs/repository-map.md): como o repositório está organizado

## Estrutura do Repositório

```text
app/
  agents/      agentes de mercado e exchange
  core/        kernel, oracle e runner
  models/      contratos de dados
docs/
  current-state.md   estado atual do projeto
  next-steps.md      roadmap ativo
  repository-map.md  mapa de pastas e convenções
  reference/         documentação técnica de apoio
  archive/           changelog, backlog, blog e notas históricas
papers/
  artigos e referências acadêmicas
```

## O Que Já Existe

- Kernel de eventos com latência estocástica e atraso computacional por agente
- Exchange com `LIMIT`, `MARKET`, cancelamento validado por proprietário e consultas assíncronas de mercado
- Oracle por processo Ornstein-Uhlenbeck
- Agentes heurísticos com contabilização de posição, caixa, VWAP e PnL
- Dashboard gráfico com order book, trades, heatmap, logs e tracker de agentes
- Suíte de testes de sanidade para kernel, exchange, contabilidade e baseline
- Cenário padrão documentado com seed fixa e métricas mínimas de saída

## O Que Ainda Falta

- Wrapper formal para RL/MARL
- `StopSignalAgent` ou mecanismo equivalente de sincronização
- definição de observações, ações e recompensas treináveis
- pipeline de treino e avaliação comparativa

## Referências

- `papers/ABIDES- Towards High-Fidelity Multi-Agent Market Simulation.pdf`
- `papers/ABIDES-MARL- A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation and Execution in a Limit Order Book.pdf`
- `papers/ABIDES-Gym- Gym Environments for Multi-Agent Discrete Event Simulation and Application to Financial Markets.pdf`
- `papers/JAX-LOB- A GPU-Accelerated limit order book simulator to unlock large scale reinforcement learning for trading.pdf`
