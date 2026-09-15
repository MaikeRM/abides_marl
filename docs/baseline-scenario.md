# Baseline do Simulador

## Objetivo

Este arquivo define o cenário padrão usado para validar o simulador como baseline reproduzível antes da etapa de interface RL.

## Configuração Padrão

Fonte única: `app/core/runner.py`

- seed fixa: `42`
- preço inicial: `100.0`
- horizonte padrão: `max_time=1000`
- `5` `MarketMakerAgent`
- `10` `ValueAgent`
- `1` `LiquidityTrader` comprador com `target_qty=100`
- `20` `ZeroIntelligenceAgent`
- latência por par de agentes: uniforme inteira entre `1` e `10`

## Como Executar

Rodar o baseline e imprimir as métricas em JSON:

```bash
uv run python -m app.core.runner
```

Gerar o manifesto, as métricas e o trace canônico em um único artifact:

```bash
uv run python -m app.core.runner --artifact-dir /tmp/abides-baseline
```

Rodar a suíte de sanidade:

```bash
uv run python -m unittest discover -s tests -v
```

## Métricas Mínimas de Saída

O baseline deve sempre expor pelo menos:

- `final_time`
- `events_processed`
- `trade_count`
- `traded_volume`
- `traded_notional`
- `last_trade`
- `fundamental_value`
- `best_bid`
- `best_ask`
- `spread`
- `resting_bid_qty`
- `resting_ask_qty`
- `liquidity_trader.fill_ratio`

## Critério de Sanidade

Para considerar o baseline fechado:

- a suíte em `tests/` precisa passar
- o `ExchangeAgent` precisa manter invariantes explícitas do livro e do `_order_map`
- o baseline precisa produzir a mesma saída para a mesma seed e o mesmo horizonte
- o cenário documentado aqui precisa continuar alinhado com `app/core/runner.py`

O artifact persistido usa `baseline-artifact.v1`; seu trace não inclui
timestamps de parede. A trilha completa da GUI continua disponível
separadamente para observabilidade.
