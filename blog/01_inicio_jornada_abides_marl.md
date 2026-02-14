# Engenharia de Microestrutura de Mercado: Construindo um Simulador ABIDES-MARL do Zero (Parte 1)

**Status:** _Work in Progress_
**Stack:** Python, Discrete Event Simulation, Reinforcement Learning

---

A simulação de mercados financeiros evoluiu drasticamente na última década. Passamos de backtests estáticos baseados em velas OHLC para ambientes de **Agent-Based Modeling (ABM)** de alta fidelidade, capazes de replicar a dinâmica de ticks, latência de rede e impacto de mercado endógeno.

Nesta série de artigos, documentarei o processo de engenharia reversa e implementação do framework proposto no paper recentíssimo **"ABIDES-MARL: A Multi-Agent Reinforcement Learning Environment for Endogenous Price Formation"** (2025).

O objetivo não é apenas "rodar um backtest", mas construir um laboratório de **Multi-Agent Reinforcement Learning (MARL)** onde agentes autônomos (Market Makers, Execution Algos) aprendem estratégias ótimas em um Limit Order Book (LOB) vivo.

Também manteremos no radar frameworks de execução vetorial em GPU, como **JAX-LOB** e **JAXMARL**, que representam o estado da arte em performance para treinamento massivo.

---

## 1. A Arquitetura Teórica: DEMAS

A base de qualquer simulador de microestrutura sério é o **Discrete Event Multi-Agent Simulation (DEMAS)**. Diferente de simulações baseadas em _time-stepping_ (onde o relógio avança em intervalos fixos $t, t+1...$), um kernel DEMAS avança de **evento em evento**.

Isso é crucial para modelar **latência**. No mercado real, a ordem de chegada no matching engine define a prioridade de execução. Se meu algoritmo em Colocation (1ms) compete com um trader de varejo (200ms), o simulador precisa respeitar essa fila exata, não agrupar tudo no mesmo "segundo".

### O Kernel (`v010_abides_poc.py`)

Na nossa implementação v0.1.0, o Kernel gerencia o tempo global e uma fila de prioridade (Priority Queue) de mensagens.

```python
# Core do Kernel de Eventos Discretos
def step(self):
    if not self._events:
        return False

    # O tempo "salta" para o próximo evento agendado
    when, _, msg = heapq.heappop(self._events)
    self.time = when

    agent = self._agents[msg.dst]
    if msg.kind == "WAKEUP":
        agent.wakeup(self.time)
    else:
        agent.receive(msg)
    return True
```

Observe que não existe um loop `while True: time.sleep(1)`. O tempo é uma variável contínua que salta instantaneamente para o momento exato da entrega da próxima mensagem ou despertar de um agente.

---

## 2. Modelagem de Preços e Agentes

Para criar um mercado que não seja apenas um passeio aleatório (Random Walk), precisamos de **agentes heterogêneos** com objetivos conflitantes. Implementamos a estrutura clássica da literatura de microestrutura:

### A. O Processo Fundamental (Oracle)

O valor "justo" do ativo ($V_t$) segue um processo de **Ornstein-Uhlenbeck** (Mean Reverting). Isso simula a tendência dos preços de retornarem a um valor fundamental de longo prazo, ao mesmo tempo que sofrem choques estocásticos (Brownian Motion).

Matematicamente, implementamos em `Oracle.get_value`:
$$ dV_t = \kappa(\bar{r} - V_t)dt + \sigma dW_t $$

Esse valor é invisível para a maioria, exceto para...

### B. Informed Traders (Alpha Seekers)

Estes agentes possuem "informação privilegiada" ou modelos preditivos superiores. Eles observam $V_t$ (com algum ruído $\epsilon$) e agridem o livro quando o preço de mercado diverge do valor fundamental além de um limiar $\alpha$.

No código:

```python
# Alpha signal strategy
diff = fundamental - market_price
if abs(diff) > self.threshold:
    # Agressão direcional para corrigir o mispricing
    side = "BUY" if diff > 0 else "SELL"
    self.kernel.send(..., "NEW_ORDER", side, ...)
```

### C. Market Makers (Liquidity Providers)

Eles ganham no spread (Bid-Ask) e perdem na seleção adversa (quando negociam com Informed Traders). Na nossa v0.1.0, o `MarketMakerAgent` gere dinamicamente seu inventário. Se ele acumula muita posição comprada, ele "skew" (inclina) seus quotes para baixo para incentivar vendas e desencorajar novas compras.

```python
# Inventory Skew Logic
inventory_skew = -self.position * risk_aversion_factor
mid_price = last_trade + inventory_skew

# Postagem de quotes simétricos ao redor do mid ajustado
bid = mid_price - spread/2
ask = mid_price + spread/2
```

---

## 3. Mecanismo de Matching (The Exchange)

A bolsa (`ExchangeAgent`) opera um **Continuous Double Auction (CDA)**.
Para a v0.1.0, implementamos a lógica de matching `O(n)` padrão com prioridade **Price-Time**:

1.  Ordens de **Melhor Preço** executam primeiro.
2.  Ordens no mesmo preço executam na ordem de chegada (FIFO).

O matching engine verifica cruzamento de ordens a cada nova mensagem `NEW_ORDER` recebida. Se há liquidez compatível, gera um `EXECUTION` trade; caso contrário, a ordem repousa no LOB (`Limit Order Book`).

---

## 4. Gap Analysis: O Caminho para o ABIDES-MARL

Embora nossa infraestrutura suporte a simulação, estamos tecnicamente distantes do framework **MARL (Multi-Agent Reinforcement Learning)** do estado da arte.

Realizei uma análise de gap detalhada (`changelog/v010_analise_abides_marl.md`), identificando:

1.  **Modelo de Kyle Ausente**: Nossos Informed Traders usam heurísticas simples (`if diff > threshold`). O paper propõe agentes que aprendem a função de impacto de mercado linear de Kyle ($\lambda$), otimizando o tamanho da ordem para maximizar lucro sem mover o preço excessivamente.
2.  **Espaços de Observação/Ação (RL)**: Atualmente, os agentes são hard-coded. Para usar RL (PPO - Proximal Policy Optimization), precisamos expor o estado do LOB (profundidade, preços) como tensores normalizados e definir ações discretas ou contínuas para a rede neural.
3.  **Sincronização para Treinamento**: Um ambiente de RL requer um loop `step(action) -> reward, next_state`. O DEMAS é assíncrono. Precisaremos de um `StopSignalAgent` ou um wrapper compatível com **Gymnasium/PettingZoo** para "congelar" o mercado e permitir que a rede neural tome decisões.

---

## Roadmap Técnico: O Caminho para a v1.0

Nosso backlog para as próximas sprints divide-se em fases incrementais, detalhadas em nossa análise de gap:

### Fase 1: Formalização dos Agentes (Prioridade Imediata)

O foco será alinhar nossos agentes heurísticos com os modelos econômicos formais do artigo.

- **Informed Trader:** Implementar a estratégia linear de Kyle $x(n) = \beta(v - \bar{p})\tau$, substituindo a heurística de threshold fixa.
- **Market Maker:** Implementar a precificação baseada em impacto $\lambda$ ($p(n) = \bar{p} + \lambda q$) e o mecanismo de alocação pro-rata.
- **Liquidity Trader:** Adicionar a função de utilidade com penalidade de risco quadrática $\phi Q^2$, essencial para criar aversão a risco realista.

### Fase 2: Interface RL (Gymnasium)

Preparar o terreno para a "cérebro" da IA.

- **Observation Spaces:** Definir os tensores normalizados que representarão o LOB ($p_{i}, q_{i}$) para a rede neural.
- **Wrappers:** Implementar a interface `gym.Env` e `pettingzoo` para tornar o simulador compatível com bibliotecas padrão de RL (Stable-Baselines3, RLLib).
- **Sincronização:** Criar o `StopSignalAgent` para coordenar a tomada de decisão dos agentes em um ambiente de tempo contínuo.

### Fase 3: Treinamento Multi-Agente (MARL)

Onde a mágica acontece.

- **Independent PPO (IPPO):** Treinar múltiplos agentes simultaneamente, cada um otimizando sua própria recompensa (lucro + gestão de risco).
- **Validação:** Comparar as estratégias aprendidas ("orgânicas") com as soluções analíticas conhecidas da literatura para garantir que a IA funciona conforme o esperado.

### Fase 4: High-Performance Computing (JAX)

Visando escala massiva.

- **Vetorização:** Migração do Kernel para **JAX**, permitindo rodar milhares de ambientes em paralelo numa única GPU. Isso é vital para reduzir o tempo de treinamento de semanas para horas.

O código está disponível no repositório. Convido outros quants e engenheiros a clonarem a `v0.1.0` e rodarem a simulação.

```bash
python v010_abides_poc.py
```

A saída é um TUI em tempo real mostrando a formação de preço emergente da interação entre nossos agentes ruidosos e informados.

_Fique ligado para o deep dive na implementação do Wrapper Gymnasium na Parte 2._
