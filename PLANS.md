# Plan

## Estado atual

O projeto tem uma fundação local v0.2.0 funcional e um pipeline RL de smoke,
mas ainda não é um laboratório científico fechado nem uma entrega comprovada em
clone limpo. A tabela abaixo separa o que foi observado do que continua
pendente.

| Área | Estado observado | O que falta fechar | Fase |
| --- | --- | --- | --- |
| Kernel | Pronto para smoke e baseline | API pública, falhas estruturadas e contratos de lifecycle ainda precisam ser endurecidos | 06 |
| Exchange/LOB | CDA funcional com invariantes testadas | política econômica de risco, taxas, self-trade, rejeições e terminalidade ainda não está fechada | 06 |
| Contabilidade | Implementada para laboratório | reconciliação formal de caixa/posição/PnL, marcação e liquidação terminal ainda são simplificadas | 06 |
| Agentes heurísticos | População inicial funcional | ampliar cobertura dos agentes alternativos e definir papéis pareados para avaliação | 06/08 |
| Runner/baseline | Artefato reproduzível observado | `run_artifact(max_time=...)` registra o horizonte do cenário, não necessariamente o horizonte executado | 05 |
| Estado de entrega | Funcional no worktree local | `main` está sujo e divergente de `origin/main`; falta prova de clone limpo e reconciliação de entrega | 05 |
| Testes e qualidade | Gate local observado | CI remoto não foi executado; cobertura e contratos ainda não representam todo o comportamento econômico | 05/06 |
| GUI | Disponível para inspeção manual | smoke gráfico e correção de caminho de seleção ainda não foram validados em sessão real | 10 |
| RL single-agent | Implementado como smoke | reduzir dependência de internals, completar ações/terminalidade e formalizar horizonte | 07 |
| Treinamento/avaliação | NumPy/CEM curto reproduzível | protocolo científico pareado, baselines, holdout, ICs, tamanho de efeito e gate econômico | 08 |
| MARL/PettingZoo | Não adotado | decisão de necessidade; se aprovada, contrato de sincronização e observabilidade multiagente | 09 |
| Performance/release | Benchmark e CI configurados localmente | série histórica, metas, orçamento, type checking e pacote de release verificável | 10 |

## Roadmap

1. [x] [Fase 00 — Reconciliação do baseline e governança](harness/build/00-baseline-reconciliation.md)
2. [x] [Fase 01 — Contratos do core, contabilidade e reprodução](harness/build/01-core-contracts.md)
3. [x] [Fase 02 — Ambiente RL single-agent](harness/build/02-rl-single-agent.md)
4. [x] [Fase 03 — MARL, treinamento e avaliação smoke](harness/build/03-marl-training-evaluation.md)
5. [x] [Fase 04 — Performance, CI e release local](harness/build/04-performance-release.md)
6. [ ] [Fase 05 — Reconciliar e entregar o v0.2.0](harness/build/05-reconcile-and-deliver-v020.md)
7. [ ] [Fase 06 — Contratos públicos e semântica econômica do core](harness/build/06-core-contracts-and-economic-semantics.md)
8. [ ] [Fase 07 — Contrato científico do RL single-agent](harness/build/07-rl-single-agent-research-contract.md)
9. [ ] [Fase 08 — Protocolo de avaliação científica](harness/build/08-scientific-evaluation-protocol.md)
10. [ ] [Fase 09 — Decisão MARL e PettingZoo opcional](harness/build/09-marl-decision-and-optional-pettingzoo.md)
11. [ ] [Fase 10 — Escala, performance e release verificável](harness/build/10-performance-scale-and-release.md)

## Phases / Fases

As fases do roadmap têm contratos individuais em `harness/build/`; somente uma
fase pode estar em execução por vez.

## Dependências e pontos de decisão

- As Fases 00–04 fecharam uma fundação local, não uma prova de entrega em clone
  limpo nem uma conclusão de performance econômica.
- A Fase 05 deve vir primeiro: sem ela, resultados do worktree não devem ser
  descritos como release integrada.
- A Fase 06 fecha o core antes de ampliar o protocolo experimental; mudanças em
  capital, risco ou reward exigem testes de regressão e comparação de baseline.
- A Fase 07 trata o wrapper single-agent como interface pública, sem acesso a
  internals do runner e com terminalidade/horizonte determinísticos.
- A Fase 08 é o gate de qualquer alegação econômica: CEM NumPy continua smoke
  até algoritmo, orçamento, seeds, holdout e limiares serem aprovados.
- A Fase 09 primeiro pode concluir que MARL não é necessário. PettingZoo só deve
  entrar se a decisão de produto exigir controle simultâneo mensurável.
- A Fase 10 usa perfil e benchmark longos para decidir Python, vetorização ou
  JAX; a decisão provisória atual é permanecer em Python.
- Branch, merge, rebase, commit, push, pull request, dependências externas e
  deploy são gates separados e não estão autorizados pelo roadmap.

## Estratégia de verificação

- Red: cada fase começa com o menor teste que demonstra a lacuna, sem tratar um
  teste já verde como prova de comportamento novo.
- Green: implementar apenas o contrato aprovado e repetir o teste focado.
- Refactor: reorganizar sem ampliar escopo e repetir as verificações afetadas.
- Verificação ampla: testes unitários, integração do runner, compilação,
  validação de ambiente, benchmark ou revisão manual conforme o risco.
- Evidência: registrar comando exato, resultado observado, skips, limitações e
  próximo handoff em `harness/build-log.md`.

## Handoff e conclusão

- Apenas uma fase pode estar `In progress`.
- Uma fase só pode ser `Complete` quando seus critérios, checks, revisão,
  limitações e evidências estiverem registrados.
- Se uma decisão humana bloquear a fase, registrar a pergunta e parar sem
  iniciar a fase seguinte.
- O fechamento do roadmap exige que os critérios de `GOALS.md` sejam verificados
  em um clone limpo; uma execução apenas no worktree deve ser rotulada como
  evidência local.
- O roadmap não autoriza merge, rebase, commit, push, deploy, publicação,
  conexão com corretora ou dados reais. Esses atos continuam sendo gates
  separados.

## Backlog pós-roadmap

Somente depois da Fase 08 aprovar o protocolo científico poderão ser abertas
frentes de pesquisa, cada uma com hipótese, baseline, métrica, seeds, custo,
holdout e critério de rejeição:

- fatos estilizados e qualidade de mercado em cenários controlados;
- robustez a latência, liquidez, volatilidade e composição de agentes;
- novas famílias de agentes ou políticas RL com comparação congelada;
- ablação de observações, reward e restrições econômicas;
- otimização de runtime apenas se o benchmark reproduzível mostrar gargalo
  material.
