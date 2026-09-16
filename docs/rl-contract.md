# Contrato do episódio RL single-agent

O contrato versionado é `single-agent-episode.v1`, exposto por
`app.env.EpisodeSpec`. O agente controlado tem o papel `execution_agent`; os
agentes heurísticos continuam no background do mesmo cenário.

## Observação

`observation_space` é `Box(low=-1, high=1, shape=(8,), dtype=float32)`. A ordem
e a unidade de cada componente são fixas:

| Índice | Nome | Definição |
| ---: | --- | --- |
| 0 | `best_bid_return` | `(best_bid - start_price) / price_scale` |
| 1 | `best_ask_return` | `(best_ask - start_price) / price_scale` |
| 2 | `spread_ticks_scaled` | `spread / 10` |
| 3 | `mid_return` | `(mid - start_price) / price_scale` |
| 4 | `position_fraction` | `position / position_limit` |
| 5 | `marked_pnl_scaled` | `marked_pnl / reward_scale` |
| 6 | `vwap_return` | `(vwap - start_price) / price_scale` |
| 7 | `last_trade_return` | `(last_trade - start_price) / price_scale` |

Livro vazio usa o último trade como fallback para bid/ask/mid. Valores são
limitados a `[-1, 1]` apenas para respeitar o espaço; `info` mantém os valores
contábeis sem esse clipping.

## Ação

`action_space = MultiDiscrete([5, 20, 10])`:

| Componente | Valores | Semântica |
| --- | --- | --- |
| `action_type` | 0–4 | `HOLD`, `BUY_LIMIT`, `SELL_LIMIT`, `BUY_MARKET`, `SELL_MARKET` |
| `price_ticks` | 0–19 | offset relativo ao mid, em ticks de 0.01, para limit |
| `qty_bin` | 0–9 | quantidade `qty_bin + 1` |

`HOLD` não envia ordem. Cancelamento é uma operação de lifecycle pública
(`RLMarketAgent.cancel_all_orders()`), deliberadamente fora do vetor fixo v1;
isso mantém compatibilidade com a política NumPy existente. Ordens inválidas
falham antes de mutar o episódio; rejeições econômicas retornam em `info` com
`action_status=REJECTED`.

## Transição e reward

Uma chamada `step` enfileira no máximo uma decisão. A barreira espera o próximo
market-data depois da liquidação dos eventos gerados pela decisão. O reward é a
variação incremental de equity marcada pela policy (`last_trade` no perfil
legado), dividido por `reward_scale` e limitado a `[-10, 10]`; taxas entram no
caixa e no PnL realizado antes do cálculo.

`terminated` representa exaustão anormal/natural da simulação. `truncated`
representa `max_steps` ou o horizonte de sim-time. Quando ambos ocorrem no
mesmo tick, `truncated` vence. Depois de qualquer terminalidade ou `close`,
novos `step`s falham e a fila de eventos é limpa.

`reset(seed=...)` reconstrói runner, exchange, agentes e policy; o mesmo seed,
configuração e ações produz a mesma observação, reward, terminalidade e trace
canônico. O contrato não afirma superioridade econômica.
