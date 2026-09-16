# Política econômica do laboratório

O core não escolhe regras econômicas por efeito colateral. Cada
`BaselineScenario` carrega `economic_policy`, e o artifact registra a política
expandida em `manifest.economic_policy` e `metrics.economic_policy`.

## Perfis disponíveis

| Nome | Caixa inicial | Short | Self-trade | Taxas | Marca | Fim do episódio |
| --- | ---: | --- | --- | --- | --- | --- |
| `legacy_unconstrained` | 0 | permitido | permitido | 0 | último trade | somente marcação |
| `cash_inventory_constrained` | 100000 | proibido | proibido | maker 1 bp / taker 5 bp | mid quando disponível | liquidação pela marca |

`legacy_unconstrained` é o perfil de compatibilidade do baseline v0.2.0. Ele
não é uma política de risco financeiro. O perfil restrito é uma superfície
experimental explícita; sua diferença de resultado não pode ser atribuída à
policy aprendida sem uma comparação própria.

## Lifecycle público

Cada ordem aceita recebe um registro em `ExchangeAgent.order_lifecycle`, com
owner, lado, preço, quantidade original/remanescente, timestamps de simulação,
fills e um dos estados `RECEIVED`, `RESTING`, `PARTIALLY_FILLED`, `FILLED`,
`CANCELLED`, `NO_LIQUIDITY` ou `EXPIRED`. Erros de validação e violações da policy ficam
em `ExchangeAgent.rejections` e não deixam mutação parcial no livro.

Cada fill contém `trade_id`, `buyer_order_id`, `seller_order_id`, quantidade,
preço, taxa, contraparte e liquidez (`maker`/`taker`). A contabilidade do
agente reconcilia posição e caixa contra o próprio histórico de fills por
`HeuristicAgent.reconcile_accounting()`.

O algoritmo de matching e o relógio não foram substituídos. Uma mudança de
policy, taxa ou marcação deve usar uma nova configuração e um novo artifact;
ela não deve sobrescrever o hash de um resultado anterior.
