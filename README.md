# PoC minima de simulacao multiagente (estilo ABIDES)

Este projeto implementa **o minimo necessario** para uma prova de conceito inspirada nos papers:

- `papers/ABIDES- Towards High-Fidelity Multi-Agent Market Simulation.pdf`
- `papers/ABIDES-Gym- Gym Environments for Multi-Agent Discrete Event Simulation and Application to Financial Markets.pdf`

## O que foi mantido (essencial)

- Kernel de eventos discretos com fila de prioridade
- Comunicacao entre agentes por mensagens
- Latencia simples entre pares de agentes
- Agente de Exchange com livro de ofertas (bid/ask)
- Casamento por prioridade preco/tempo
- Agentes traders simples acordando periodicamente

## O que foi removido (para manter simples)

- Sem RL e sem OpenAI Gym
- Sem historico real de mercado
- Sem cancelamento de ordem
- Sem persistencia/logs avancados
- Sem arquitetura em varios arquivos

## Como rodar

```bash
python3 simple_abides_poc.py
```

Durante a execucao, o terminal mostra em tempo real:

- ordem enviada por cada trader
- ordem recebida pela exchange
- trades executados (comprador, vendedor, preco, quantidade)
- atualizacao de posicao e caixa de cada agente

Se quiser rodar sem visualizacao em tempo real:

```bash
python3 -c "import simple_abides_poc as s; s.run_demo(visualize=False)"
```

## Arquivo principal

- `simple_abides_poc.py`

Ao final, o script imprime:

- tempo final simulado
- ultimo preco negociado
- posicao, caixa e mark-to-market por trader
