# Formalização dos Agentes Heurísticos (Fase 1)

Este documento descreve a implementação dos agentes heurísticos no simulador ABIDES-MARL PoC (Fase 1) e como suas formulações matemáticas e comportamentais se alinham com o paper de referência _"ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation and Execution in a Limit Order Book"_ e com a teoria clássica de microestrutura de mercado.

## O Papel dos Agentes Heurísticos

No contexto do ABIDES e do ABIDES-MARL, a simulação de um Limit Order Book (LOB) realista requer a presença de agentes de "background" que interajam com o mercado. Esses agentes de fundo, baseados em heurísticas, criam a dinâmica de mercado, a liquidez e o ruído contra os quais um agente de Reinforcement Learning (RL) - a ser introduzido na Fase 2 - irá interagir e aprender.

A calibração e a lógica desses agentes são fundamentais para que o ambiente de simulação e a descoberta de preços (price discovery) convirjam para condições que espelhem a realidade e a teoria acadêmica.

---

## 1. InformedTrader e o Modelo de Kyle ($\beta$)

O `InformedTrader` representa agentes de mercado que possuem informação privilegiada ou superior sobre o verdadeiro valor do ativo (o valor fundamental $v_t$). O paper do ABIDES-MARL valida seu ambiente simulando e recuperando o fenômeno de "descoberta gradual de preço" descrito de forma clássica por **Kyle (1985)**.

### A Teoria

No modelo de Kyle, o formador de mercado informado calibra a agressividade do seu lote ($x_t$) de modo linear e proporcional ao descolamento (spread) entre sua observação do preço justo ($v_t$) e o preço de tela atual do mercado ($p_t$). A intensidade dessa agressividade é dada pelo fator $\beta$.

> $x_t = \beta \cdot (v_t - p_t)$

### Na Implementação (`app/agents/informed.py`)

Introduzimos o parâmetro `beta` e ajustamos a lógica de quantidade (`qty`).

```python
diff = fundamental - market_price
if abs(diff) > self.threshold:
    side = "BUY" if diff > 0 else "SELL"
    # A agressividade da ordem (qty) é extraída como um fator beta da distorção do preço
    qty = max(1, min(100, int(abs(diff) * self.beta)))
```

Isso garante que quanto maior for a distorção no preço (ou maior for a confiança/fator de escala $\beta$), mais pesadamente o agente atuará para forçar o fechamento do gap.

---

## 2. MarketMaker e a Precificação por Inventário ($\lambda$)

O `MarketMakerAgent` provê liquidez contínua posicionando ordens nos dois lados do livro (bid e ask). Num modelo contínuo com múltiplos formadores de mercado limitados por capital (competing market makers), não se pode assumir risco infinito.

### A Teoria

Para sobreviver ao viés direcional de traders informados (seleção adversa) e não explodir o risco direcional da carteira, market makers reais utilizam o inventário (posição acumulada) para deslocar o ponto focal das cotações (mid-price de referência), como preconizam os modelos de controle de estoque de **Avellaneda-Stoikov** ou **Glosten-Milgrom**. Se a posição global ($q$) for muito positiva, o risco é de queda de preço, então aplica-se uma penalidade negativa proporcional a um parâmetro $\lambda$.

> $Preço\ de\ Referência\ Ajustado = p - \lambda \cdot q$

### Na Implementação (`app/agents/market_maker.py`)

Trocamos a métrica rígida de recuo por uma sensível baseada no parâmetro `lambda_param`.

```python
# Skew (deslocamento) que reduz a exposição com base no fluxo de mercado e posições vigentes
inventory_skew = -self.position * self.lambda_param
adjusted_mid = mid + inventory_skew
```

Esse mecanismo enriquece organicamente o livro de ofertas simulado, gerando recuos de liquidez (liquidity shading) quando um lado do mercado sofre grande impacto direcional.

---

## 3. LiquidityTrader e o Impacto/Risco de Tempo ($\phi$)

O `LiquidityTrader` é modelado como um gestor que necessita desovar (ou comprar) uma cota total $Q_{target}$ até um prazo $T$ (optimal execution deadline).

### A Teoria

Na teoria de execução ótima clássica, existe um _trade-off_ contínuo. Andar rápido com ordens a mercado (agressivas) garante execução mas incorre em custos de spread (impacto). Andar pacientemente com ordens limitadas economiza custos, mas cria variância da não-execução perto do fim do prazo. Geralmente introduz-se uma probabilidade de urgência ancorada ao risco estocado (quantidade restante vs alvo base) penalizado por $\phi$.

### Na Implementação (`app/agents/liquidity.py`)

A heurística de urgência foi escalada considerando tanto a fração de tempo até a deadline quanto uma avaliação de risco baseada no fator `phi`.

```python
time_fraction = remaining_time / self.deadline
# Urgência base derivada do tempo, acrescida da penalidade pelo risco de possuir muito inventário a ser despachado (phi)
risk_penalty = self.phi * (self.remaining_qty / self.target_qty)
urgency = min(1.0, (1.0 - time_fraction) + risk_penalty)
```

Com o decair do tempo, e mantendo uma quantidade grande, a urgência se aproxima de 1.0, submetendo envios à `exchange` utilizando `MARKET` order no lugar de `LIMIT` e sacrificando prêmio em prol da certeza de liquidação.

---

## Conexão com Próximos Passos (RL)

Ao concretizarmos os referenciais teóricos que alimentam a mecânica LOB da **Fase 1**, preparamos um laboratório hostil e com reatividade microestrutural coerente onde agentes MARL (Gymnasium Wrappers - **Fase 2**) poderão ser treinados não para bater táticas primitivas, mas para navegar o impacto do seu footprint frente a market makers resilientes de inventário real e reagir frente ao fluxo tóxico impulsionado pelos Informed Traders.
