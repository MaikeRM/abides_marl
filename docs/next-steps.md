# Próximos Passos

## Direção do Projeto

O objetivo do próximo ciclo não deve ser adicionar mais documentação histórica ou mais variantes de agentes sem fechar a base. A prioridade agora é transformar o simulador atual em um baseline reproduzível e depois em um ambiente RL treinável.

## Baseline Fechado

O baseline do simulador foi fechado no snapshot `v0.1.6` com:

- testes de sanidade para `Kernel`, `ExchangeAgent`, contabilidade e reprodutibilidade
- validações explícitas de invariantes do livro e do `_order_map`
- cenário padrão documentado com seed fixa e métricas mínimas

O próximo ciclo passa a priorizar a interface RL.

## Prioridade 1: Interface RL

Objetivo: expor o simulador como ambiente consumível por bibliotecas de RL.

Entregáveis:

- criar `StopSignalAgent` ou mecanismo equivalente de sincronização
- definir observações por agente ou por ambiente
- definir espaço de ações
- formalizar função de recompensa
- implementar wrapper `Gymnasium` e avaliar necessidade de `PettingZoo`

## Prioridade 2: Treinamento e Avaliação

Objetivo: sair de um motor simulável para um laboratório experimental.

Entregáveis:

- integrar um pipeline inicial com `Stable-Baselines3` ou `RLlib`
- registrar métricas de treino e validação
- comparar agentes treinados contra heurísticos
- documentar cenários de benchmark e critérios de sucesso

## Prioridade 3: Performance e Escala

Objetivo: preparar a transição para execuções massivas quando a interface RL estiver madura.

Entregáveis:

- separar o core do simulador da camada visual
- medir throughput do loop de eventos sem GUI
- definir se a próxima etapa de escala será otimização em Python ou migração para JAX

## O Que Não Deve Ser Prioridade Agora

- novas pastas de documentação fora de `docs/`
- expansão do blog antes de fechar a base experimental
- migração prematura para HPC sem wrapper RL estável

## Como Atualizar Este Arquivo

Use este documento como backlog vivo. Quando uma frente for concluída:

- mova o registro histórico para `docs/archive/changelog/`
- atualize `docs/current-state.md`
- remova ou reordene prioridades aqui
