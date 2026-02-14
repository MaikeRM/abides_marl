# 📊 Análise Comparativa: `v010_abides_poc.py` vs Artigo ABIDES-MARL

> **Data:** 2026-02-14  
> **Artigo:** _ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation and Execution in a Limit Order Book_ (Nov 2025)  
> **Código:** `v010_abides_poc.py` — POC v0.1.0

---

## 1. Resumo Executivo

A `v010` implementa uma **Proof of Concept** funcional que captura os elementos fundamentais de arquitetura do ABIDES original (Byrd et al. 2020), sobre o qual o ABIDES-MARL se constrói. O código reproduce com sucesso a estrutura de simulação multi-agente com kernel de eventos discretos, exchange com matching engine, oracle de valor fundamental e agentes heterogêneos. Porém, **ainda não incorpora os avanços específicos do ABIDES-MARL**, como o framework de RL, a formulação do modelo de Kyle, o mecanismo pro-rata de market makers, e o treinamento via MARL.

---

## 2. Componentes Implementados na v010 ✅

### 2.1 Kernel de Eventos Discretos (DEMAS)

| Aspecto                              | Artigo                                | v010                                    | Status              |
| ------------------------------------ | ------------------------------------- | --------------------------------------- | ------------------- |
| Fila de prioridade de eventos (heap) | ✅ Kernel com priority-queue          | ✅ `heapq` em `Kernel._events`          | ✅ **Implementado** |
| Registro de agentes                  | ✅ Agent registry                     | ✅ `Kernel.register()` / `_agents` dict | ✅ **Implementado** |
| Envio de mensagens com latência      | ✅ Message passing com latência       | ✅ `Kernel.send()` com `_delay()`       | ✅ **Implementado** |
| Wakeup scheduling                    | ✅ Agents agendam próximo wakeup      | ✅ `Kernel.wakeup()`                    | ✅ **Implementado** |
| Time advancement                     | ✅ Avanço discreto baseado em eventos | ✅ `Kernel.step()` avança `self.time`   | ✅ **Implementado** |

**Observações:**

- O kernel da v010 é uma versão simplificada, mas funcionalmente correta do conceito DEMAS descrito no artigo.
- O artigo descreve um kernel mais complexo com capacidade de interrupção (`StopSignalAgent`), que a v010 não possui.

### 2.2 Oracle / Valor Fundamental (Ornstein-Uhlenbeck)

| Aspecto                                  | Artigo                      | v010                                      | Status              |
| ---------------------------------------- | --------------------------- | ----------------------------------------- | ------------------- |
| Processo mean-reverting (OU)             | ✅ Fundamental value via OU | ✅ `Oracle` com `r_bar`, `kappa`, `sigma` | ✅ **Implementado** |
| Parâmetros r_bar (média de longo prazo)  | ✅                          | ✅ `r_bar=100.0`                          | ✅ **Implementado** |
| Parâmetro kappa (velocidade de reversão) | ✅                          | ✅ `kappa=0.05`                           | ✅ **Implementado** |
| Parâmetro sigma (volatilidade)           | ✅                          | ✅ `sigma=0.5`                            | ✅ **Implementado** |
| Lazy evaluation temporal                 | ✅                          | ✅ `get_value(t)` avança sob demanda      | ✅ **Implementado** |
| Seed reprodutível                        | ✅                          | ✅ `random.Random(seed)`                  | ✅ **Implementado** |

**Correspondência com o artigo:**
O artigo usa o processo OU como base para o valor fundamental `v`, com a fórmula:

```
dV = κ(r̄ − V)dt + σdW
```

A v010 discretiza isso corretamente como:

```python
self.value += self.kappa * (self.r_bar - self.value) + self.sigma * self.rng.gauss(0, 1)
```

### 2.3 Exchange Agent (Continuous Double Auction)

| Aspecto                      | Artigo               | v010                                                    | Status              |
| ---------------------------- | -------------------- | ------------------------------------------------------- | ------------------- |
| Limit Order Book (LOB)       | ✅ LOB com bids/asks | ✅ `bids[]` e `asks[]` listas de `Order`                | ✅ **Implementado** |
| Price-Time Priority matching | ✅                   | ✅ `_best_index()` com prioridade por preço e timestamp | ✅ **Implementado** |
| Ordens LIMIT                 | ✅                   | ✅ Suporte completo                                     | ✅ **Implementado** |
| Ordens MARKET                | ✅                   | ✅ Via preço extremo (1e9 / 0.0)                        | ✅ **Implementado** |
| Cancelamento de ordens       | ✅                   | ✅ `CANCEL_ORDER` (por ID ou cancel_all)                | ✅ **Implementado** |
| Notificação ORDER_ACCEPTED   | ✅                   | ✅ Enviado após inserção no book                        | ✅ **Implementado** |
| Notificação EXECUTION        | ✅                   | ✅ Enviado para ambos buyer/seller                      | ✅ **Implementado** |
| Tick size discreto           | ✅                   | ✅ `TICK_SIZE=0.01` / `round_to_tick()`                 | ✅ **Implementado** |
| Trade tape / histórico       | ✅                   | ✅ `history: List[Trade]` (últimos 100)                 | ✅ **Implementado** |
| Aggressor side tracking      | ✅                   | ✅ `Trade.aggressor_side`                               | ✅ **Implementado** |

### 2.4 Tipos de Agentes

| Agente                | Artigo                                               | v010                                                                | Status                             |
| --------------------- | ---------------------------------------------------- | ------------------------------------------------------------------- | ---------------------------------- | ----------- | ---------------------------------- |
| **Noise Trader (ZI)** | ✅ Gera fluxo de ordens exógeno `u(n) ~ N(0, σ²)`    | ✅ `NoiseTrader` — ordens aleatórias BUY/SELL com 15% market orders | ✅ **Implementado**                |
| **Informed Trader**   | ✅ Observa `v` e negocia `x(n) = β(n)(v - p̄(n-1))τ`  | ✅ `InformedTrader` — observa Oracle com ruído e negocia quando     | diff                               | > threshold | ✅ **Implementado (simplificado)** |
| **Market Maker**      | ✅ Cota preços e ajusta por inventário               | ✅ `MarketMakerAgent` — spread simétrico com inventory skew         | ✅ **Implementado (simplificado)** |
| **Liquidity Trader**  | ✅ Executa Q unidades até deadline com TWAP/urgência | ✅ `LiquidityTrader` — TWAP com urgência crescente                  | ✅ **Implementado (simplificado)** |

### 2.5 Data Classes e Mensageria

| Aspecto             | Artigo | v010                                                            | Status              |
| ------------------- | ------ | --------------------------------------------------------------- | ------------------- |
| Messages tipadas    | ✅     | ✅ `Message(src, dst, kind, data)`                              | ✅ **Implementado** |
| Orders estruturadas | ✅     | ✅ `Order(order_id, agent_id, side, price, qty, ts)`            | ✅ **Implementado** |
| Trades registrados  | ✅     | ✅ `Trade(price, qty, buyer_id, seller_id, ts, aggressor_side)` | ✅ **Implementado** |

### 2.6 Modelo de Latência

| Aspecto                               | Artigo | v010                                              | Status              |
| ------------------------------------- | ------ | ------------------------------------------------- | ------------------- |
| Latência assimétrica por par          | ✅     | ✅ `Kernel.latency` dict com (src, dst) → delay   | ✅ **Implementado** |
| Delay na entrega de mensagens         | ✅     | ✅ `delivery = self.time + self._delay(src, dst)` | ✅ **Implementado** |
| Latência randomizada na inicialização | ✅     | ✅ `kernel.rng.randint(1, 10)` por par de agentes | ✅ **Implementado** |

### 2.7 Tracking de Posição e PnL

| Aspecto              | Artigo | v010                                             | Status              |
| -------------------- | ------ | ------------------------------------------------ | ------------------- |
| Posição por agente   | ✅     | ✅ `self.position` em todos os agentes           | ✅ **Implementado** |
| Cash tracking        | ✅     | ✅ `self.cash` em todos os agentes               | ✅ **Implementado** |
| Mark-to-Market (MtM) | ✅     | ✅ Calculado como `cash + position * last_trade` | ✅ **Implementado** |

### 2.8 Visualização (TUI)

| Aspecto                             | Artigo                  | v010                                        | Status                            |
| ----------------------------------- | ----------------------- | ------------------------------------------- | --------------------------------- |
| Interface terminal estilo Bloomberg | N/A (artigo não aborda) | ✅ `curses` TUI com order book, tape, stats | ✅ **Extra — Não está no artigo** |

---

## 3. Componentes NÃO Implementados na v010 ❌

### 3.1 🔴 StopSignalAgent e Sistema de Sincronização MARL

**Prioridade: ALTA (fundamento do ABIDES-MARL)**

O artigo introduz o `StopSignalAgent` como inovação-chave:

- Um agente dedicado que **interrompe o kernel** para sincronizar todos os agentes RL
- Garante ordem de ação consistente (sequencial ou simultânea)
- Separa a interrupção do kernel da coleta de estado

**Na v010:** Não existe. O kernel roda continuamente com wakeups individuais.

### 3.2 🔴 Interface Gymnasium/PettingZoo

**Prioridade: ALTA**

O artigo descreve compatibilidade com:

- **Gymnasium** (Towers et al. 2024) para RL single-agent
- **PettingZoo** (Terry et al. 2021) para MARL
- Interface padrão: `(observation, reward, termination, truncation, info)`

**Na v010:** Não possui nenhuma interface RL. Os agentes são puramente heurísticos.

### 3.3 🔴 Formulação do Modelo de Kyle

**Prioridade: ALTA**

O artigo formula o modelo de Kyle completo com:

- **Equilíbrio linear recursivo**: `β(n)`, `λ(n)`, `Σ(n)` determinados por sistema de equações
- **Informed trader**: `x(n) = β(n)(v − p̄(n-1))τ` (estratégia linear ótima)
- **Price impact**: `p(n) = p̄(n-1) + λ(n)q(n)` (incorporação eficiente de informação)
- **Variância condicional** decrescente: `Σ(n) = Var(v|q(1),...,q(n))`
- **Price discovery gradual**: preços convergem para `v` ao longo do tempo

**Na v010:** O `InformedTrader` usa uma heurística simplificada com threshold e ruído, não a formulação ótima de Kyle.

### 3.4 🔴 Mecanismo Pro-Rata para Market Makers

**Prioridade: MÉDIA-ALTA**

O artigo define:

- **Market depth**: `d(n)_i = 1/|λ(n)_i|` (profundidade implícita por MM)
- **Order allocation proporcional**: `Order(n)_i = q(n) · d(n)_i / Σd(n)_j`
- **VWAP unânime** (Claim 3.1): todos transacionam ao mesmo VWAP
- **Zero-sum entre MMs** (Lemma 3.2): `Σ R_MM = 0`

**Na v010:** O exchange usa price-time priority (CDA clássico), não pro-rata. Cada MM posta quotes independentes.

### 3.5 🔴 Observation/Action/Reward Spaces Formais

**Prioridade: ALTA**

O artigo define espaços formais para cada tipo de agente:

**Observations:**

- **Global**: `[p̄(n-1), d_i1, p_i1, ..., d_iM, p_iM]` (LOB) ou `[p̄(n-1)]` (OTC)
- **Informed Trader**: `[t(n), v]`
- **Market Maker i**: `[t(n), q(n)]` (net order flow)
- **Liquidity Trader**: `[t(n), Q(n)]` (remaining inventory)

**Actions:**

- **Informed**: `x(n) = β(n)(v − p̄(n-1))τ` (linear) ou `x(n)` direto (nonlinear)
- **MM**: `λ(n)_i` (linear) ou `p(n)_i` direto (nonlinear)
- **Liquidity**: `θ(n)` → `x(n) = θ(n)Q(n)`

**Rewards:**

- **Informed**: `R_IT = (v − p̄(n))x(n)`
- **MM**: `R_MM_i = Order(n)_i · (p(n)_i − p̄(n))`
- **Liquidity**: `R_LT = -(x(n)p(n) + φQ(n)²)` + penalidade terminal

**Na v010:** Nenhum desses espaços formais é definido. Os agentes usam heurísticas internas.

### 3.6 🔴 Treinamento PPO / MARL

**Prioridade: ALTA (objetivo final do framework)**

O artigo demonstra:

- Treinamento com **Independent PPO (IPPO)** para cada grupo de agentes
- Políticas **lineares** (para validação contra Kyle) e **não-lineares** (para generalização)
- Comparação de estratégias de execução: PPO, VWAP, TWAP, Analytical, PPO-Single
- **Implementation Shortfall (IS)** como métrica de performance
- Convergência para equilíbrio com price discovery gradual

**Na v010:** Nenhum treinamento RL implementado.

### 3.7 🔴 Modos OTC vs Exchange

**Prioridade: MÉDIA**

O artigo distingue dois regimes de informação:

- **Exchange**: LOB completo visível (depth + prices de todos os MMs)
- **OTC**: apenas VWAP visível, sem LOB

**Na v010:** Não há distinção. O exchange opera como CDA aberto.

### 3.8 🔴 Formulação de Risco de Inventário (φ)

**Prioridade: MÉDIA**

O artigo inclui penalidade de risco na função objetivo do liquidity trader:

```
min E[Σ p(n)x(n) + φ Σ Q(n)²]
```

Com `φ ≥ 0` controlando aversão ao risco e `β` como penalidade terminal por inventário não preenchido.

**Na v010:** O `LiquidityTrader` usa urgência temporal, mas não tem penalidade formal de risco `φ`.

### 3.9 🟡 Solução Analítica via Programação Dinâmica (Theorem 3.3)

**Prioridade: MÉDIA**

O artigo fornece a solução ótima exata:

```
x(n) = θ(n)Q(n), onde θ(n) = 1 - λ(n)(1+α) / (2μ(n+1))
```

Com `μ(n)` satisfazendo recursão backward.

**Na v010:** O liquidity trader usa TWAP heurístico, não a solução ótima.

### 3.10 🟡 Métricas de Avaliação

**Prioridade: MÉDIA**

O artigo usa:

- **Implementation Shortfall (IS)**: custo de execução normalizado
- **Kyle regression**: `Δp = c + λΔq + ε` para medir eficiência de preços
- **Half-life** de convergência de preços
- **Excess Kurtosis** das distribuições de retornos
- **Variance ratio tests** para eficiência de mercado

**Na v010:** Apenas MtM e posição são rastreados. Nenhuma métrica formal.

### 3.11 🟡 News Component / Price Dynamics Estendido

**Prioridade: BAIXA**

O artigo inclui:

```
p̂(n) = αp̂(n-1) + (1-α)p(n-1) + ε(n)
```

Com `α ∈ [0,1]` controlando impacto permanente e `ε(n) ~ N(0, σ²_ε)` como componente de notícias.

**Na v010:** Não implementado. O preço evolui apenas via matching.

---

## 4. Diferenças Qualitativas Importantes

### 4.1 Paradigma de Execução

| Aspecto   | Artigo ABIDES-MARL                | v010                          |
| --------- | --------------------------------- | ----------------------------- |
| Paradigma | **Timestep-based** (sincronizado) | **Event-driven** (assíncrono) |
| Controle  | StopSignalAgent coordena          | Wakeups independentes         |
| Objetivo  | Treinamento RL                    | Visualização/demonstração     |

### 4.2 Market Maker

| Aspecto            | Artigo                                    | v010                              |
| ------------------ | ----------------------------------------- | --------------------------------- |
| Objetivo           | `min E[(g_i - v)²]` (estimador Bayesiano) | Spread simétrico + inventory skew |
| Definição de preço | `p(n)_i = p̄(n-1) + λ(n)_i · q(n)`         | `mid ± spread/2 + skew`           |
| Competição         | Pro-rata entre múltiplos MMs              | Price-time priority (CDA)         |

### 4.3 Informed Trader

| Aspecto     | Artigo                            | v010                           |
| ----------- | --------------------------------- | ------------------------------ | ---- | --------------------------------- |
| Sinal       | Observa `v` diretamente           | Observa `v + ruído(noise_std)` |
| Estratégia  | `x = β(v - p̄)τ` (ótima/aprendida) | `se                            | diff | > threshold → trade` (heurística) |
| Intensidade | `β` aprendido via RL              | Proporção fixa ao diff         |

### 4.4 Liquidity Trader

| Aspecto    | Artigo                     | v010                              |
| ---------- | -------------------------- | --------------------------------- |
| Objetivo   | `min E[Σ px + φΣ Q²]`      | Executar Q até deadline (TWAP)    |
| Estratégia | `θ(n)Q(n)` (ótima/PPO)     | TWAP com urgência + market orders |
| Risco      | Penalidade φ no inventário | Urgência temporal implícita       |

---

## 5. Pontuação de Completude

| Componente            | Peso     | Completude | Score         |
| --------------------- | -------- | ---------- | ------------- |
| Kernel DEMAS          | 15%      | 90%        | 13.5          |
| Oracle (OU)           | 10%      | 95%        | 9.5           |
| Exchange/LOB          | 15%      | 85%        | 12.75         |
| Noise Trader          | 5%       | 80%        | 4.0           |
| Informed Trader       | 10%      | 40%        | 4.0           |
| Market Maker          | 10%      | 45%        | 4.5           |
| Liquidity Trader      | 10%      | 50%        | 5.0           |
| Framework RL (Gym/PZ) | 10%      | 0%         | 0.0           |
| MARL Training         | 10%      | 0%         | 0.0           |
| Métricas/Avaliação    | 5%       | 10%        | 0.5           |
| **TOTAL**             | **100%** | —          | **53.75/100** |

> A v010 está em **~54% de completude** em relação ao artigo ABIDES-MARL completo. A base de infraestrutura (Kernel, Oracle, Exchange) está sólida. O gap principal é na camada de RL e na formalização dos modelos econômicos.

---

## 6. Roadmap — Próximos Passos

### 🏗️ Fase 1: Formalização dos Agentes (v0.2.0)

Objetivo: Alinhar os agentes heurísticos com os modelos formais do artigo.

- [ ] **Informed Trader com Kyle β**: Implementar `x(n) = β(v - p̄)τ` com parâmetro `β` configurável
- [ ] **Market Maker com λ pricing**: Implementar `p(n) = p̄ + λ·q` e mecanismo pro-rata
- [ ] **Liquidity Trader com objetivo formal**: Adicionar penalidade de inventário `φ·Q²` e proporção `θ(n)`
- [ ] **Noise Trader gaussiano**: Alinhar com `u(n) ~ N(0, σ²_u·τ)` do artigo
- [ ] **VWAP tracking**: Implementar cálculo de VWAP no exchange
- [ ] **News component**: Adicionar `ε(n)` ao processo de preços

### 🔌 Fase 2: Interface RL (v0.3.0)

Objetivo: Criar compatibilidade com frameworks de RL.

- [ ] **Observation spaces**: Definir obs para cada tipo de agente conforme Seção 3.1.2–3.2.2
- [ ] **Action spaces**: Definir ações (β, λ, θ) como espaços contínuos
- [ ] **Reward functions**: Implementar R_IT, R_MM, R_LT formais
- [ ] **StopSignalAgent**: Implementar agente de sincronização
- [ ] **Gymnasium wrapper**: Interface `step()` → `(obs, reward, terminated, truncated, info)`
- [ ] **PettingZoo wrapper**: Interface multi-agent

### 🧠 Fase 3: Treinamento MARL (v0.4.0)

Objetivo: Treinar agentes com PPO.

- [ ] **Integração Stable-Baselines3**: Setup de treinamento single-agent
- [ ] **Independent PPO (IPPO)**: Treinamento multi-agente independente
- [ ] **Políticas lineares**: Validação contra equilíbrio de Kyle analítico
- [ ] **Políticas não-lineares**: Redes neurais para β e λ
- [ ] **Kyle regression**: `Δp = c + λΔq + ε` como validação
- [ ] **Half-life analysis**: Convergência de preços para valor fundamental

### 📊 Fase 4: Métricas e Comparações (v0.5.0)

Objetivo: Reproduzir os experimentos do artigo.

- [ ] **Implementation Shortfall (IS)**: PPO vs VWAP vs TWAP vs Analytical vs PPO-Single
- [ ] **Solução analítica** (Theorem 3.3): Implementar recursão backward para θ(n) ótimo
- [ ] **Experimentos com 2 vs 20 MMs**: Impacto da competição no price discovery
- [ ] **Modos OTC vs Exchange**: Comparar regimes de informação
- [ ] **Excess Kurtosis e distribuição de retornos**: Análise estatística
- [ ] **Variance ratio tests**: Eficiência de mercado

### 🚀 Fase 5: Extensões Avançadas (v0.6.0+)

Conforme sugerido na Seção 5 do artigo:

- [ ] **Múltiplos informed traders** com crenças heterogêneas
- [ ] **Market makers risk-averse** com ajuste de spread por inventário (Ho-Stoll)
- [ ] **Continuous double auction completo** com extensões
- [ ] **Historical market replay agents**: agentes que reproduzem dados reais
- [ ] **Integração com Agentic AI / LLMs**: sinais textuais + execução RL
- [ ] **Counterfactual training**: stress-testing de políticas

---

## 7. Referências Cruzadas

| Conceito no Artigo | Arquivo no Código    | Linha(s) |
| ------------------ | -------------------- | -------- |
| DEMAS Kernel       | `v010_abides_poc.py` | 85–133   |
| Oracle (OU)        | `v010_abides_poc.py` | 53–80    |
| Exchange (CDA)     | `v010_abides_poc.py` | 153–304  |
| Noise Trader (ZI)  | `v010_abides_poc.py` | 309–354  |
| Informed Trader    | `v010_abides_poc.py` | 359–412  |
| Market Maker       | `v010_abides_poc.py` | 417–489  |
| Liquidity Trader   | `v010_abides_poc.py` | 494–555  |
| TUI Visualization  | `v010_abides_poc.py` | 564–692  |
| Demo/Setup         | `v010_abides_poc.py` | 697–789  |

---

## 8. Conclusão

A **v010** é uma base sólida que captura corretamente a **arquitetura DEMAS** do ABIDES:

- ✅ Kernel com event-driven simulation
- ✅ Agentes heterogêneos com comunicação via mensagens
- ✅ Exchange com LOB e price-time priority
- ✅ Oracle com processo Ornstein-Uhlenbeck
- ✅ Modelo de latência assimétrica
- ✅ TUI de visualização em tempo real

O **gap principal** em relação ao ABIDES-MARL está em:

- ❌ Framework de Reinforcement Learning (Gymnasium/PettingZoo)
- ❌ Formulação econômica formal (Kyle model, pro-rata, observation/action/reward spaces)
- ❌ Treinamento multi-agente com PPO
- ❌ Métricas de avaliação (IS, Kyle regression, half-life)

A evolução deve ser incremental: primeiro formalizar os agentes heurísticos, depois criar a interface RL, e finalmente treinar e avaliar os agentes com MARL.
