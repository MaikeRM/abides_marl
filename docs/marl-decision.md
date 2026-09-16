# ADR 009 — No-go para MARL simultâneo neste ciclo

**Status:** `no-go` condicionado, registrado em 2026-09-15.

## Decisão

O laboratório mantém `AbidesGymEnv` single-agent como superfície oficial e não
adiciona PettingZoo, AEC ou Parallel API neste ciclo.

## Evidência e pergunta-alvo

Os objetivos atuais exigem testar a execução de um participante contra um
background heurístico e comparar políticas por seed. Essa pergunta pode ser
expressa pelo wrapper single-agent: um agente controlável, uma barreira de
market-data, observação privada do participante e uma contabilidade
reconciliável. Não há, no escopo aprovado, uma hipótese que exija atribuição de
crédito entre agentes controlados simultaneamente, coordenação conjunta ou
informação privada compartilhada.

| Alternativa | Benefício | Custo/risco agora | Resultado |
| --- | --- | --- | --- |
| wrapper próprio single-agent | contrato pequeno, já testado, sem dependência nova | não responde coordenação controlada | adotado |
| PettingZoo AEC | ecossistema MARL e turnos explícitos | nova dependência, semântica de turnos distinta do kernel | adiado |
| PettingZoo Parallel | ações simultâneas naturais | exige barreira, masks, IDs e rewards por agente ainda não necessários | adiado |

## Critérios de reabertura

Reabrir somente quando existir uma pergunta reproduzível que falhe no
single-agent e especifique: ao menos dois agentes controlados, observações
privadas, regra de crédito/reward, orçamento computacional e métrica primária.
Uma futura decisão `go` deverá congelar IDs, ordem de ações no mesmo sim-time,
barreira, masks, terminalidade e teste de não vazamento antes de instalar uma
dependência.

Este `no-go` não afirma que MARL seja desnecessário em geral; apenas evita
inferir essa necessidade de um smoke ou de literatura. O caminho single-agent
e o baseline continuam independentes e reproduzíveis.
