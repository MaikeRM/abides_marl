# Plano de Execução: Pipeline de Melhorias ABIDES-MARL

Este plano detalha as etapas sistemáticas para implementar as 5 melhorias estruturais de micra-estrutura de mercado documentadas no pipeline, sem quebrar o ecossistema existente.

---

## Fase 1: Infraestrutura de Rede e Tempo (Kernel)

**Foco:** Melhorar a gestão do tempo, implementar latência estocástica e controle de tempo de processamento.

**Tarefas:**

1. **`app/core/kernel.py`**:
   - Adicionar atributos para rastrear o tempo local de cada agente (`agent_current_times`) e seu tempo de processamento (`agent_computation_delays`).
   - Modificar `send()` para embutir atrasos aleatórios de latência de comunicação (`latencyNoise`).
   - Atualizar a lógica do loop em `step()` (ou no disparo de eventos) para não permitir que o agente execute no "futuro" relativo à simulação global. Aplicar a penalidade de _delay_ de processamento na volta do `wakeup` e `receive`.
2. **`app/agents/base.py` / `app/core/runner.py`**:
   - Criar um método `kernelStopping()` em `Agent` (herdado por `HeuristicAgent`).
   - No `SimulationRunner`, antes de encerrar ou limpar a execução (`stop` ou fim do dataset), chamar iterativamente o `kernelStopping` de todos os agentes.
   - Computar o _Surplus_ da Marcação a Mercado: `surplus = (position * last_fundamental_price) + cash`.

_(Cobre Melhorias 4 e 5)_

---

## Fase 2: Isolamento de Memória e Protocolo de Dados (Exchange)

**Foco:** Padrão de comunicação estrito, forçando os agentes a "pedirem" e "esperarem" pelos dados em vez de enxergarem diretamente.

**Tarefas:**

1. **`app/agents/exchange.py`**:
   - Implementar recebimento de mensagens `"QUERY_MKT_DATA"`, `"QUERY_SPREAD"`, `"QUERY_LAST_TRADE"`.
   - Adicionar respostas da exchange empacotando os melhores bids/asks ou o último preço executado (mensagens de volta).
2. **`app/agents/base.py`**:
   - Criar máquina de estados interna do agente (`state = "INACTIVE", "AWAITING_DATA", "ACTIVE"`).
3. **`app/agents/liquidity.py`, `market_maker.py`, `informed.py`**:
   - Remover os acessos `exchange = self.kernel._agents[self.exchange_id]` dos métodos `wakeup`.
   - Modificar o `wakeup` para apenas enviar a requisição (ex: `QUERY_MKT_DATA`) para a Exchange e trocar o estado para `AWAITING_DATA`.
   - Mover a lógica atual de tomada de decisão (postar/cancelar ordem) para dentro do `receive()` mediante a chegada do pacote de dados da Exchange.

_(Cobre Melhoria 1)_

---

## Fase 3: Dinâmica Estocástica de Chegada (Market Microstructure)

**Foco:** Uniformizar as chegadas de mercado sob Processos de Filas Tradicionais.

**Tarefas:**

1. **Modelos de Agentes (`liquidity.py`, `informed.py`, `market_maker.py`)**:
   - Substituir variáveis como `wake_interval = X` e `jitter` por `lambda_a = 1.0 / X` (Taxa média de chegada).
   - No agendamento da próxima ação `self.kernel.wakeup(self.agent_id, next_time)` presente após a submissão das ações em `receive()`:
     Substituir os `rng.randint(0, 5)` por sorteios baseados na distribuição de tempos de espera da chegada de Poisson:
     `delta_time = self.rng.expovariate(self.lambda_a)`
     `self.kernel.wakeup(self.agent_id, now + max(1, int(delta_time)))`.

_(Cobre Melhoria 2)_

---

## Fase 4: Rigor Fundamental: ZI e Value Agents

**Foco:** Finalizar a fundação Heurística com modelos comprovadamente bayesianos, substituindo o informed trader que utiliza "regras quebradiças".

**Tarefas:**

1. **`app/agents/value_agent.py` & `zi_agent.py`** (Novos arquivos ou refatoração profunda do `informed`):
   - Migrar a estratégia clássica "Value" do ABIDES-sim.
   - Definir a função `updateEstimates()` com calibração Bayesiana de Valor Fundamental `r_t` baseada em reversão à média (`kappa`), erro observacional (`sigma_n`) e variância de evento/choque (`sigma_s`).
   - Implementar a tomada de decisão focada não no Mid-Price diretamente, mas sim no **Surplus Requisitado ($R$)** e Valores de Benefício Privado ($\theta$).
2. **`app/core/runner.py` / `main.py`**:
   - Plugar na simulação os novos agentes bayesianos em substituição ao atual `InformedTrader` estático, testando o equilíbrio de preços formado na interface gráfica Textual.

_(Cobre Melhoria 3)_

---

## Estratégia de Deploy

Sugerimos implementar linearmente, começando pela **Fase 1** (mais intrusiva na engrenagem principal - limitador e penalizador temporal no `kernel`). Uma vez rodando sob o tempo penalizado, a **Fase 2** será construída sem que as assincronias quebrem; em seguida **Fase 3** ajeita as distribuições matemáticas, dando base sólida para injetarmos o cerébro rigoroso bayesiano na **Fase 4**.
