# Próximos Passos

## Direção do Projeto

O planejamento executável está em [`../PLANS.md`](../PLANS.md), com objetivos em [`../GOALS.md`](../GOALS.md) e contratos de fase em [`../harness/build/`](../harness/build/). Este arquivo permanece como índice curto da direção do projeto.

## Baseline Fechado

O baseline do simulador está operacional no worktree local do snapshot `v0.2.0`
com:

- testes de contrato para `Kernel`, `ExchangeAgent`, contabilidade, ambiente e pipeline
- validações explícitas de invariantes do livro e do `_order_map`
- cenário padrão documentado com seed fixa, manifesto e trace canônico
- reprodução local byte a byte do artifact curto

O baseline tem agora uma linha de qualidade local e um benchmark headless. Isso
fecha a fundação de engenharia, mas não transforma o smoke de treino em
evidência de vantagem econômica. Como o worktree está sujo e o branch diverge
de `origin/main`, a entrega ainda precisa passar pela reconciliação de clone
limpo da Fase 05.

## Ordem executável do próximo ciclo

### P0 — Fase 05: reconciliar e entregar v0.2.0

- corrigir o horizonte efetivo no manifesto do artifact;
- alinhar `GOALS.md`, `PLANS.md`, `docs/current-state.md` e build log;
- fazer o harness estrito passar com evidência observada;
- separar explicitamente estado local, `HEAD`, `origin/main` e worktrees;
- provar instalação, testes e baseline em clone limpo antes de chamar a entrega
  de integrada.

### P1 — Fase 06: fechar o core e a economia do experimento

- tornar mensagens, ordens, trades, rejeições, cancelamentos e fills parciais
  contratos públicos e testáveis;
- definir capital, margem, short selling, self-trade, taxas, marcação e
  liquidação terminal;
- ampliar invariantes e reconciliação de contabilidade sem alterar o baseline
  silenciosamente.

### P2 — Fase 07: tornar o RL single-agent research-grade

- desacoplar o ambiente de atributos privados do runner;
- completar o contrato de observação, ação, reward, seed, horizonte,
  `terminated`, `truncated` e `info`;
- cobrir todas as ações, fills, ausência de liquidez, reset, fechamento e
  determinismo.

### P3 — Fase 08: substituir smoke por avaliação científica

- parear política e heurísticas por cenário, população, papel e seed;
- separar treino, validação e holdout, incluindo baselines HOLD/random;
- definir métricas econômicas e de risco, ICs, tamanho de efeito, orçamento e
  gates fail-closed;
- registrar configuração, versões, hashes e limitações em artifacts imutáveis.

### P4 — Fase 09: decidir MARL/PettingZoo

- responder se o caso de uso realmente exige agentes controláveis simultâneos;
- se não exigir, registrar no-go e preservar o single-agent;
- se exigir, especificar mapeamento de agentes, barreira, masks, observações,
  rewards e paridade determinística antes de adicionar dependência.

### P5 — Fase 10: escala e release verificável

- executar benchmark longo e perfil de CPU/memória/trace;
- aprovar metas de throughput, latência, memória, CI e plataformas;
- adicionar type checking e otimizações somente com gatilho medido;
- validar pacote/release local, mantendo deploy e publicação como decisões
  separadas.

## Entregas concluídas localmente: Fases 00–04

As cinco fases anteriores produziram a fundação local de engenharia. A Fase 03
é explicitamente um fechamento de smoke e a Fase 04 um fechamento de
performance/CI local; nenhuma das duas autoriza uma alegação econômica ou uma
release pública.

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
