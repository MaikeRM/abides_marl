# Arquitetura do Simulador ABIDES (Referência vs. Implementação)

Este documento descreve a arquitetura referencial do **ABIDES** apresentada no diagrama "Figure 2: Class relations within the ABIDES simulation framework" e verifica o nível de aderência da implementação atual da Prova de Conceito (PoC) disponível no repositório.

## 1. Arquitetura de Referência (Diagrama Original)

De acordo com o diagrama original do ABIDES, o ecossistema de simulação é composto pelas seguintes camadas e hierarquias de classes principais:

### 1.1 Entidades Nucleares

- **Kernel**: Controla a simulação, aplica regras temporais, serve como central de distribuição (clearinghouse) de mensagens e registra logs de tudo o que ocorre.
- **Message**: Classe base para toda a comunicação trafegando através do Kernel.
- **Agent**: Classe ancestral comum para todos os agentes na simulação. Interage de forma completa com o ciclo de vida ditado pelo Kernel.
- **Oracle**: Conecta agentes com a realidade fora da simulação, injetando sinais ou valores verdadeiros.

### 1.2 Configuração e Inicialização

- **ABIDES**: Bloco de software que localiza as configurações do experimento e evoca o carregamento global.
- **Config**: Registra os parâmetros do experimento (agentes instanciados, oráculos requeridos e semente do kernel).

### 1.3 Hierarquia Financeira e de Mercado

- **Order e LimitOrder**: A interface de execução de intenções no mercado, sendo `LimitOrder` estendida para suportar um teto ou piso de preço.
- **OrderBook**: A estrutura que mantém duas listas de `LimitOrder` rankeadas (melhor cotação primeiro): _bids_ e _asks_.
- **Oracle de Dados**: O diagrama descreve especializações como `MeanReversionOracle` (um gerador ruidoso mean-reverting) e `DataOracle` (leitor de dados reais do passado).
- **Hierarquia de Agentes (Financial & Trading)**: O `Agent` herda para `FinancialAgent` (lidar com moeda/ativos). A partir deste, derivam o `ExchangeAgent` (especializado em manter os _OrderBooks_ do símbolo) e o `TradingAgent` (base para classes emissoras de ordens).
- **Subtipos de TradingAgents**: Agentes de fundo como `BackgroundAgent` (arbitragem fundamental leve), `MomentumAgent` (seguidor de tendência) e `ImpactAgent` (executa uma agressão unidirecional programada).

---

## 2. Aderência da Implementação Atual (Nossa Base de Código)

Avaliando o código nos diretórios `app/core/`, `app/agents/` e `app/models/`, determinamos que a nossa implementação atual é largamente alinhada na **mecânica de fluxo (message-passing)**, contudo apresenta **achatamentos hierárquicos** com o fim de obter uma arquitetura mais leve e adaptada à próxima fase focada em Aprendizado por Reforço (MARL).

### O que o código implementa **exatamente como o fluxo**

- **Kernel (`app/core/kernel.py`)**: Implementado com precisão. Retém a fila de mensagens no tempo e realiza os despachos (dispatch) de rotinas e envios.
- **Message (`app/models/types.py`)**: A estrutura central transacional segue firme (inclusive repassando `kind`, `source` e cargas úteis `data`).
- **Agent (`app/agents/base.py`)**: A classe construtora básica para agentes simulados está presente e define bem as interfaces essenciais como `wakeup` e `receive`.
- **ExchangeAgent (`app/agents/exchange.py`)**: Cumpre seu propósito primordial — processa recepção de ordens, limpa _matchings_ pelo preço e notifica execuções, englobando perfeitamente a lógica temporal requerida.

### Desvios, Adaptações e Simplificações Identificadas

1. **Achatamento de Herança de Agentes**:
   - Em vez de ter múltiplas camadas (`Agent` $\rightarrow$ `FinancialAgent` $\rightarrow$ `TradingAgent`), o nosso simulador salta para uma camada prática `HeuristicAgent` baseada em `Agent`. O `ExchangeAgent` é também uma derivação direta do nível base `Agent`.
2. **Ordens não segregadas**:
   - A classe `LimitOrder` e `Order` foram unificadas (`app/models/types.py`). A distinção lógica de ordens limite para agressivas a mercado e cancelamentos é tratada pelos atributos e parâmetros internos no processamento da _Exchange_, evitando a necessidade de classes separadas.
3. **Abstração do OrderBook Inline**:
   - O `OrderBook` no diagrama original mantém duas hierarquias fixas de referências. O nosso `ExchangeAgent` abstrai isso internamente usando listas formatadas como Max-Heaps e Min-Heaps da biblioteca nativa `heapq`, reduzindo sobrecarga orientada a objetos (OOP) e mantendo lookup de complexidade O(log N).
4. **Agentes Heurísticos Específicos (Substituição de Background/Momentum)**:
   - No lugar dos agentes de demonstração originais, implementamos em `app/agents/` um _pool_ tático validado nas heurísticas da microestrutura, tais como `InformedTrader` (Kyle Model), `MarketMaker` (Avellaneda-Stoikov/Glosten-Milgrom), `LiquidityTrader` e `NoiseAgent`. Eles substituem a representação de `BackgroundAgent` e `ImpactAgent` com maior nível de detalhes.
5. **Oracles**:
   - Só implementamos um `Oracle` isolado (`app/core/oracle.py`), que por acaso se comporta exatamente como o `MeanReversionOracle` referenciado pelo O.U. Process (Ornstein-Uhlenbeck). Não possuímos de momento o `DataOracle`.
6. **Invocation (Config & ABIDES)**:
   - Removemos a complexidade estática e a transformamos em uma aplicação rodando via Terminal User Interface (TUI) a partir do `app/main.py`. A inicialização dos agentes e injeção do kernel ocorrem programaticamente atreladas a uma classe `SimulationRunner`.

---

## 3. Conclusão

O código atende perfeitamente ao **fluxo dinâmico de eventos** (comunicação baseada no Kernel e roteamento dos pacotes) descrito pelo paper do ABIDES. Freqüentemente as interfaces interativas das setas programáticas ($---- \triangleright$ "enviado para") coincidem com as trocas que ocorrem entre nosso `ExchangeAgent` e nossos `HeuristicAgents`.

Todavia, a estrita taxonomia de **orientação a objetos** (Classes Derivadas) apresentada no diagrama de classe (Figura 2) foi deliberadamente descartada a favor de uma implementação direta, moderna e adaptada diretamente para o _wrapper_ de ambientes do **Gymnasium** para a futura Fase MARL. Seu simulador é funcionalmente idêntico no motor assíncrono, mas modularmente muito mais prático e menos verborrágico.
