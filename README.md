# ABIDES-MARL PoC

Simulador de mercado multiagente orientado a pesquisa, inspirado na arquitetura ABIDES e no ambiente ABIDES-MARL. O foco do projeto e permitir experimentos de microestrutura de mercado e evoluir para cenarios de MARL.

## Conteudo

- [Visao geral](#visao-geral)
- [Status atual](#status-atual)
- [Arquitetura](#arquitetura)
- [Instalacao](#instalacao)
- [Execucao](#execucao)
- [Interface TUI](#interface-tui)
- [Logs: dicionario de colunas](#logs-dicionario-de-colunas)
- [Lacunas em relacao ao ABIDES-MARL](#lacunas-em-relacao-ao-abides-marl)
- [Roadmap](#roadmap)
- [Estrutura do repositorio](#estrutura-do-repositorio)
- [Referencias](#referencias)

## Visao geral

Este repositorio implementa um ambiente de **simulacao discreta por eventos (DEMAS)** com:

- kernel de eventos com latencia assimetrica entre agentes;
- bolsa com **Limit Order Book (LOB)** e matching por prioridade preco-tempo;
- oracle de valor fundamental via processo **Ornstein-Uhlenbeck (OU)**;
- agentes heuristicas (noise, informed, market maker e liquidity trader);
- interface em terminal com **Textual** para monitoramento em tempo real.

## Status atual

- Versao funcional da TUI: **v0.1.1** (`app/main.py`)
- Versao declarada no pacote Python: `0.1.0` (`pyproject.toml`)
- Cobertura estimada frente ao paper ABIDES-MARL: **~55%**

## Arquitetura

### 1) Kernel de eventos

- Fila de prioridade com `heapq`
- Registro de agentes e agendamento de wakeups
- Envio de mensagens com atraso de rede simulado

### 2) Exchange e mecanismo de matching

- Livro de ofertas completo (bid/ask)
- Matching por **Price-Time Priority**
- Ordens `LIMIT`, `MARKET` e cancelamentos
- Historico de trades e validacao de tick size

### 3) Oracle de valor fundamental

- Processo OU para dinamica do valor justo
- Parametros configuraveis: `r_bar`, `kappa`, `sigma`

### 4) Agentes implementados

- **Noise Trader**: fluxo aleatorio exogeno
- **Informed Trader**: opera com base em valor fundamental observado com ruido
- **Market Maker**: provimento de liquidez dos dois lados com ajuste por inventario
- **Liquidity Trader**: execucao de quantidade alvo via TWAP com urgencia crescente

## Instalacao

### Requisitos

- Python `==3.12.11`
- Dependencias principais: `textual`, `textual-plotext`, `rich`, `plotext`

### Ambiente (recomendado com uv)

```bash
uv sync
```

Alternativa com `venv` + `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Execucao

```bash
# recomendado
uv run python -m app.main

# alternativa com ambiente ativo
python -m app.main
```

## Interface TUI

Painel principal:

- grafico de preco em tempo real (`plotext`)
- order book (melhores niveis bid/ask)
- estatisticas de mercado (tempo, ultimo preco, fundamental)
- fita de trades recentes
- aba de logs de eventos do kernel

Controles:

- `SPACE`: passo unico de simulacao
- `S`: inicia/pausa simulacao continua
- `R`: reinicia simulacao
- `Q`: sai da aplicacao

## Logs: dicionario de colunas

A tabela `Logs` e alimentada por `Kernel.event_history` em `app/core/kernel.py` e renderizada em `app/main.py`.

Comportamento importante:

- eventos com `phase == "LOG"` ou `kind == "LOG"` sao filtrados na UI;
- por isso, mensagens textuais de `kernel.log(...)` normalmente nao aparecem na grade.

| Coluna | Origem no evento | Significado |
|---|---|---|
| `Timestamp` | `event["timestamp"]` | Horario de criacao do registro (tempo real, nao tempo de simulacao). |
| `Sim Time` | `event["sim_time"]` | Tempo discreto da simulacao associado ao evento. |
| `Phase` | `event["phase"]` | Estagio de ciclo de vida (`ENQUEUED` ou `PROCESSED`). |
| `Kind` | `event["kind"]` | Tipo de mensagem (`NEW_ORDER`, `CANCEL_ORDER`, `ORDER_ACCEPTED`, `EXECUTION`, etc.). |
| `Seq` | `event["seq"]` | Sequencia monotonicamente crescente usada como tie-breaker na fila. |
| `Delivery` | `event["delivery"]` | Tempo de entrega agendado da mensagem. |
| `Source` | `event["src_name"]`/`src` | Origem da mensagem. |
| `Destination` | `event["dst_name"]`/`dst` | Destino da mensagem. |
| `Order Type` | `event["data"]["order_type"]` | Tipo de ordem (`LIMIT` ou `MARKET`, quando aplicavel). |
| `Side` | `event["data"]["side"]` | Lado da ordem (`BUY` ou `SELL`, quando aplicavel). |
| `Qty` | `event["data"]["qty"]` | Quantidade da ordem/mensagem. |
| `Price` | `event["data"]["price"]` | Preco associado a ordem ou execucao. |
| `Order ID` | `event["data"]["order_id"]` | Identificador da ordem na exchange. |
| `Cancel All` | `event["data"]["cancel_all"]` | Flag de cancelamento em lote. |
| `Text` | `event["data"]["text"]` | Campo textual livre (em geral vazio na tabela filtrada). |

Semantica de eventos:

- `ENQUEUED`: evento entrou na fila via `kernel.send(...)` ou `kernel.wakeup(...)`.
- `PROCESSED`: evento foi retirado da fila e entregue ao destino.

## Lacunas em relacao ao ABIDES-MARL

- ainda sem interface RL formal (Gymnasium/PettingZoo);
- agentes ainda heuristicas, sem formulacao completa estilo Kyle (`beta`, `lambda`, etc.);
- mecanismo atual da exchange e CDA classico, sem modo pro-rata para market makers.

## Roadmap

### Fase 1 - Formalizacao de agentes (v0.2.0)

- informed trader com modelo de Kyle (`beta`)
- market maker com precificacao por fluxo (`lambda`)
- penalidade de risco de inventario (`phi`) no liquidity trader

### Fase 2 - Interface RL (v0.3.0)

- `StopSignalAgent` para sincronizacao
- wrappers para Gymnasium e PettingZoo
- definicao formal de observacoes e acoes

### Fase 3 - Treinamento MARL (v0.4.0)

- integracao com Stable-Baselines3 ou RLlib
- treinamento com IPPO
- validacao de convergencia e descoberta de preco

## Estrutura do repositorio

- `app/main.py`: aplicacao TUI
- `app/core/`: kernel, oracle, runner e constantes
- `app/agents/`: implementacoes de agentes e exchange
- `app/models/`: tipos e contratos de dados
- `simple_abides_poc.py`: versao monolitica inicial (v0.1.0)
- `changelog/`: historico tecnico de evolucao
- `papers/`: artigos e referencias academicas
- `blog/`: notas de desenvolvimento

## Referencias

- _ABIDES: Towards High-Fidelity Multi-Agent Market Simulation_ (Byrd et al., 2020)
- _ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation and Execution in a Limit Order Book_ (2025)
