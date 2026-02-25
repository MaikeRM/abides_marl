# Pipeline de Melhorias: Migração para o Padrão ABIDES-MARL

Este documento estabelece o backlog estruturado de refatorações baseadas nas diferenças entre a nossa implementação atual e a arquitetura oficial do simulador [ABIDES](https://github.com/abides-sim/abides). Todas as melhorias aqui contidas têm foco em aumentar o rigor acadêmico da microestrutura de mercado e preparar o terreno para a integração de Agentes de Aprendizado por Reforço (MARL).

---

## Melhoria 1: Remoção de Acesso Direto à Memória da Exchange (Strict Encapsulation)

**Status:** A Fazer
**Arquivos Afetados:** `app/agents/*.py`, `app/agents/exchange.py`

### Descrição:

Atualmente, os agentes têm referências em memória e extraem o preço médio do objeto de exchange com `self.kernel._agents[self.exchange_id].last_trade`. A infraestrutura realística do ABIDES impede esse comportamento.
Criaremos um tipo de mensagem `"QUERY_SPREAD"` e/ou `"QUERY_LAST_TRADE"`. A exchange responderá a essas requisições.

### Por que é uma melhoria?

Acessar os dados internos do Exchange como se fossem variáveis locais ignora os atrasos da simulação. Pela perspectiva de sistemas distribuídos e de Inteligência Artificial que imita agentes no mercado financeiro global: o fluxo dos _market data_ deve ocorrer consumindo a rede da simulação. Isso adicionará a possibilidade natural de reagir apenas quando os dados de mercado chegam via UDP/TCP e sofrem da latência do nó correspondente ao agente na rede simulada.

---

## Melhoria 2: Dinâmica de Chegada Padrão de Poisson (Processos Estocásticos)

**Status:** A Fazer
**Arquivos Afetados:** `app/agents/*.py` (Métodos `wakeup`)

### Descrição:

Ao invés de estipular o intervalo de `wakeup` da seguinte forma:
`self.kernel.wakeup(self.agent_id, now + self.wake_interval + jitter)` (que simula uma janela constante),
Substituiremos por sorteios paramétricos em uma distribuição exponencial padrão com a taxa de média $\lambda_a$ (Lambda de Chegada da classe de agente):
`delta_time = self.rng.expovariate(1.0 / mean_arrival_rate)`

### Por que é uma melhoria?

Filas de livro de ordens e submissões limitam-se ao que conhecemos da modelagem de Filas da Microestrutura de Mercado Padrão para Mercados Contínuos de Duplo Leilão. Isso fará com que o padrão dos submetedores de rotinas e negociações (Liquidity, Noise Traders) formem _clusters_ mais condizentes à distribuição real de eventos. Os tempos determinísticos causariam ressonâncias rítmicas nas caudas e desvio padrão irreal.

---

## Melhoria 3: Agentes Heurísticos Clássicos (Value / ZI) baseados em Teorema de Bayes

**Status:** A Fazer
**Arquivos Afetados:** `app/agents/informed.py` -> Criação de `ValueAgent` e/ou `ZeroIntelligenceAgent`

### Descrição:

Substituir lógicas rígidas baseadas em desvio linear por Inferência Bayesiana. Os ValueAgents do repositório ABIDES fundamenntam a crença reversiva de `r_t` e `sigma_t` usando um sistema estocástico: Observação -> Reversão à Média (`kappa`) ao valor bar (`r_bar`) com choque (`sigma_s`) e ruído de observação (`sigma_n`).

### Por que é uma melhoria?

Torna o sistema financeiro compatível teórica e estatisticamente. A atual predefinição no Informed Trader subestima fortemente como as partes atuam em re-avaliações após longas observações (no momento observamos apenas valor vs mercado), criando um choque binário que não existe em LOB realista, mas sim um fluxo incerto baseados em erro da percepção do próprio Agente. Permitirá testes bem mais rigorosos das IAs vs "Crenças Bayesianas Dinâmicas".

---

## Melhoria 4: Cálculo e Penalidade de Atraso Computacional Individual

**Status:** A Fazer
**Arquivos Afetados:** `app/core/kernel.py`

### Descrição:

Incorporar o `agentComputationDelays` no `kernel` para gerenciar penalidades de relógio por uso de tempo de pensar do Agente (`wakeup` ou processamentos complexos na execução de MARL).
Ao final do turno do agente, a próxima vez que ele pode pensar sofrerá a punição do tempo processual de sua complexidade local.

### Por que é uma melhoria?

Treinar Inteligências artificiais envolve lidar com a fricção do poder de computação do RL de inferir com os Tensores. Quando as IAs forem plugadas no MARL, elas demorarão um tempo virtual muito maior do que agentes heurísticos triviais. O Kernel precisa cobrar essa dívida estomacal de pensamento do RL penalizando a data dele ser acordado e poder despachar mais ordens para a Exchange no `kernel._record_event()`.

---

## Melhoria 5: Final Valuation na Marcação de Encerramento do Pregão

**Status:** A Fazer
**Arquivos Afetados:** `app/agents/base.py`, `app/core/runner.py` e `main.py`

### Descrição:

Implementar uma etapa `kernelStopping()` e o log de fim de dia em que varremos os agentes para avaliar os fluxos totais das participações:
$ Surplus = Cash*{t_N} - Cash*{t*0} + Position*{t*N} \cdot OraclePrice*{t_N} $.
Esse `surplus` terminal será centralizado nas rotinas de resumo final do `runner.py` e extraído pela UI.

### Por que é uma melhoria?

## RL e Testes unitários precisam de Escores (_Rewards_) precisos para saber quão bem o agente sobrepujou o mercado. Hoje nós estocamos posições residuais + Cash final. É vital liquidar (marcar) a posição de forma justa para calcular a Recompensa em Reais Monetários Terminal de um longo ciclo da simulação com o Oráculo da última vela, sem a fricção de liquidez da bid-ask real. Precisamos desse dado para normalizar as métricas dos Gráficos futuros RL.

---

## Melhoria 6: Market Makers Canônicos (Chakraborty-Kearns, POV, Adaptive)

**Status:** Concluído
**Arquivos Afetados:** `app/agents/market_maker.py`

### Descrição:

Refatorar a lógica do Formador de Mercado (Market Maker) existente para se alinhar estritamente aos agentes canônicos do simulador ABIDES original.
Isto envolve a construção de uma hierarquia de classes baseadas no `BaseMarketMakerAgent` para abranger as seguintes abordagens acadêmicas e heurísticas comprovadas:

1. `MarketMakerAgent` clássico baseado em dispersão fixa ("quote levels dict").
2. `SpreadBasedMarketMakerAgent` (Escada Simétrica de Chakraborty-Kearns), operando num intervalo de _window_ para profundidade sem distorcer o ponto de _mid-price_.
3. `AdaptiveMarketMakerAgent` (Escada com desequilíbrio de Inventário - _Inventory Skew Beta_), manipulando exclusivamente os volumes com Sigmoid através da distorção do limite ofertado nas duas pontas, e não através da alteração ativa do _mid-price_.
4. `POVMarketMakerAgent` dimensionando lotes pelo Volume Transacionado (% Of Volume).

### Por que é uma melhoria?

Anteriormente, nosso agente MM distorcia ativamente o _mid-price_ de forma ingênua quando assumia inventário e atuava operando ativamente um par singular de Bid/Ask. Ao replicar a classe Adaptive original (e as demais de suporte), garantimos as dinâmicas clássicas de _order placement_ (que mantêm o preço intacto, mas induzem agressão mudando volume nos lados da escada), criando a base técnica real necessária para expor um RL Agent a interagir com um fornecedor de liquidez acadêmico padronizado, de onde podemos mensurar a superioridade de uma IA sem viés arquitetural.
