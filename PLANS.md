# Plan

## Estado atual

O projeto tem uma fundação local v0.2.0 funcional, contratos econômicos e RL
versionados, avaliação pareada fail-closed e benchmark headless. A tabela
separa o que foi observado localmente dos gates que ainda dependem de decisão
ou autorização externa.

| Área | Estado observado | O que falta fechar | Fase |
| --- | --- | --- | --- |
| Kernel | API pública e invariantes testadas localmente | CI remoto continua não observado | 06/10 |
| Exchange/LOB | CDA, lifecycle, policy, rejeições e terminalidade explícitos | promoção de perfil econômico ainda é decisão humana | 06 |
| Contabilidade | reconciliação de fills, taxas, marcação e liquidação testadas | novas semânticas exigem campanha própria | 06 |
| Agentes heurísticos | população baseline e adapters pareados | POV completo e variantes legadas continuam limitados | 06/08 |
| Runner/baseline | horizonte efetivo e artifact byte-estável | prova em clone limpo ainda não executada | 05 |
| Estado de entrega | worktree local auditado e proveniência registrada | `main` sujo/divergente; Git externo não autorizado | 05 |
| Testes e qualidade | 34 testes, compileall e Ruff locais | CI remoto não foi executado | 05/10 |
| GUI | defeito de seleção inválida corrigido | smoke gráfico nesta sessão: `Unavailable` | 10 |
| RL single-agent | `EpisodeSpec`, API pública, ações e terminalidade testadas | nenhum claim econômico implícito | 07 |
| Treinamento/avaliação | protocolo pareado, splits, IC e hashes executáveis | threshold e campanha longa ainda não aprovados | 08 |
| MARL/PettingZoo | ADR `no-go` condicionado | reabrir somente com pergunta simultânea verificável | 09 |
| Performance/release | benchmark v2, `cProfile`, CI e release local documentados | metas, type checking e publicação continuam abertas | 10 |

## Roadmap

1. [x] [Fase 00 — Reconciliação do baseline e governança](harness/build/00-baseline-reconciliation.md)
2. [x] [Fase 01 — Contratos do core, contabilidade e reprodução](harness/build/01-core-contracts.md)
3. [x] [Fase 02 — Ambiente RL single-agent](harness/build/02-rl-single-agent.md)
4. [x] [Fase 03 — MARL, treinamento e avaliação smoke](harness/build/03-marl-training-evaluation.md)
5. [x] [Fase 04 — Performance, CI e release local](harness/build/04-performance-release.md)
6. [x] [Fase 05 — Reconciliar e entregar o v0.2.0](harness/build/05-reconcile-and-deliver-v020.md)
7. [x] [Fase 06 — Contratos públicos e semântica econômica do core](harness/build/06-core-contracts-and-economic-semantics.md)
8. [x] [Fase 07 — Contrato científico do RL single-agent](harness/build/07-rl-single-agent-research-contract.md)
9. [x] [Fase 08 — Protocolo de avaliação científica](harness/build/08-scientific-evaluation-protocol.md)
10. [x] [Fase 09 — Decisão MARL e PettingZoo opcional](harness/build/09-marl-decision-and-optional-pettingzoo.md)
11. [x] [Fase 10 — Escala, performance e release verificável](harness/build/10-performance-scale-and-release.md)

## Phases / Fases

As fases do roadmap têm contratos individuais em `harness/build/`; somente uma
fase pode estar em execução por vez.

## Dependências e pontos de decisão

- As Fases 00–04 fecharam uma fundação local, não uma prova de entrega em clone
  limpo nem uma conclusão de performance econômica.
- A Fase 05 reconciliou o artifact e a documentação local; o clone limpo ficou
  explicitamente `Unavailable` por falta de autorização Git/infraestrutura.
- A Fase 06 fecha o core com políticas nomeadas; mudanças futuras de capital,
  risco ou reward exigem artifact de comparação.
- A Fase 07 trata o wrapper single-agent como interface pública e congelada.
- A Fase 08 é o gate de qualquer alegação econômica: o protocolo executa, mas a
  configuração atual deixa o limiar ausente e portanto o resultado inconclusivo.
- A Fase 09 concluiu `no-go` condicionado; PettingZoo só entra se o produto
  exigir controle simultâneo mensurável.
- A Fase 10 decidiu permanecer em Python com base no perfil local; metas e CI
  remoto ainda são gates separados.
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
