# Próximos Passos

## Direção do Projeto

O planejamento executável está em [`../PLANS.md`](../PLANS.md), com objetivos em [`../GOALS.md`](../GOALS.md) e contratos de fase em [`../harness/build/`](../harness/build/). Este arquivo permanece como índice curto da direção do projeto.

## Baseline Fechado

O baseline do simulador está operacional no worktree local do snapshot `v0.2.0`
com:

- 34 testes de contrato para `Kernel`, `ExchangeAgent`, contabilidade, ambiente, protocolo e benchmark
- validações explícitas de invariantes do livro e do `_order_map`
- cenário padrão documentado com seed fixa, manifesto, horizonte efetivo e trace canônico
- reprodução local byte a byte do artifact curto

O baseline tem agora uma linha de qualidade local, políticas econômicas
explícitas, contrato RL versionado e benchmark headless. Isso fecha a fundação
de engenharia, mas não transforma o smoke de treino em evidência de vantagem
econômica. Como o worktree está sujo e o branch diverge de `origin/main`, a
prova de clone limpo permanece um gate de autorização separado.

## Ordem executável do próximo ciclo

### Gates remanescentes

- autorizar, se desejado, uma prova em clone Git limpo e decidir como
  reconciliar `main` com `origin/main`;
- escolher `minimum_effect`, orçamento e horizonte para uma campanha científica
  longa; até lá, os artifacts pareados devem permanecer `inconclusive`;
- aprovar metas de throughput/RSS/latência, type checking e plataformas se a
  escala for prioridade;
- reabrir MARL apenas com uma pergunta que exija dois ou mais agentes
  controlados simultaneamente;
- preparar publicação ou deploy somente em uma autorização separada.

## Entregas concluídas localmente: Fases 00–10

As fases 00–10 produziram a fundação local de engenharia. A Fase 03 é
explicitamente um fechamento de smoke, a Fase 08 fecha o plumbing científico
sem aprovar vantagem e a Fase 10 fecha performance/release local; nenhuma fase
autoriza publicação pública, capital real ou deploy.

As evidências e limitações estão em [`../harness/build-log.md`](../harness/build-log.md)
e nos contratos individuais em [`../harness/build/`](../harness/build/).

## O Que Não Deve Ser Prioridade Agora

- novas pastas de documentação fora de `docs/`
- expansão do blog antes de fechar a base experimental
- migração prematura para HPC/JAX sem gargalo medido e protocolo estatístico
- treino longo ou instalação de stack RL pesado antes da Fase 08
- novas famílias de agentes sem hipótese, baseline, métrica e critério de
  rejeição

## Como Atualizar Este Arquivo

Use este documento como backlog vivo. Quando uma frente for concluída:

- mova o registro histórico para `docs/archive/changelog/`
- atualize `docs/current-state.md`
- remova ou reordene prioridades aqui
