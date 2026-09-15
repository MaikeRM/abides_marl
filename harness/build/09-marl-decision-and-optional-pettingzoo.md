# Phase 09 — Decisão MARL e PettingZoo opcional

Status: Not started

## Source inputs

- resultados e limites da Fase 08
- caso de uso em `GOALS.md` e a interface single-agent da Fase 07
- contratos públicos do core da Fase 06
- referências locais a ABIDES-Gym, PettingZoo e JaxMARL, apenas para
  compatibilidade de interface

## Objective

Decidir com evidência se controle multiagente simultâneo é necessário ao
produto/pesquisa. Se for, especificar e validar um ambiente MARL; se não for,
registrar um no-go explícito e evitar complexidade sem caso de uso.

## In scope

- Formular perguntas que single-agent não responde: coordenação, competição,
  informação privada, crédito por agente ou política conjunta.
- Comparar custo/benefício de manter o wrapper próprio, adotar PettingZoo AEC,
  Parallel API ou outra interface mínima.
- Se `no-go`: registrar decisão, critérios de reabertura e preservar o
  single-agent como superfície oficial.
- Se `go`: definir agentes controláveis, IDs estáveis, ordem de observações,
  ações simultâneas, barreira/eventos, máscaras, rewards individuais e
  centralizados, `terminations`, `truncations` e `infos`.
- Definir como o kernel serializa ações com o mesmo sim-time e como a avaliação
  pareia políticas e agentes sem leakage de informação privada.
- Implementar apenas um smoke multiagente mínimo após o contrato aprovado,
  incluindo determinismo, reset, erro e desligamento.

## Non-goals

- Instalar PettingZoo ou outro stack antes da decisão.
- Treino MARL longo, benchmark econômico ou alegação de coordenação.
- Expor estado privado de agentes ao observador errado.
- Reescrever o kernel apenas para imitar uma biblioteca.

## Dependencies and prerequisites

- Fases 06–08 completas.
- Pergunta científica/produto que não possa ser respondida no single-agent.
- Orçamento de implementação e avaliação aprovado se o resultado for `go`.

## Expected files or components

- ADR/decisão `go` ou `no-go` com critérios de reabertura.
- spec de mapeamento agent ID → obs/action/reward/info.
- adapter PettingZoo ou equivalente somente no caminho `go`.
- testes de barreira, simultaneidade, máscaras, terminalidade e privacidade.
- campanha smoke separada da avaliação single-agent.

## Decisions requiring human input

- O produto realmente precisa treinar mais de um agente simultaneamente?
- API preferida se `go`: AEC, Parallel ou contrato próprio compatível.
- Observação centralizada versus descentralizada e política de crédito.
- Dependência, versão, suporte de plataforma e orçamento computacional.

## Approval gate

O default é `no-go` até existir uma pergunta verificável que exija MARL. Um
resultado `go` exige spec, orçamento e dependência aprovados antes de qualquer
instalação ou alteração do manifesto.

## Red

- Tentar expressar a pergunta-alvo com o ambiente single-agent; registrar se
  ela realmente exige simultaneidade.
- Se `go`, criar testes que falhem para IDs instáveis, ordem ambígua de ações,
  barreira incompleta, vazamento de observação e término inconsistente.
- Verificar que o baseline single-agent permanece byte a byte igual quando o
  caminho MARL não é usado.

## Green

- Há uma decisão `go`/`no-go` reproduzível, com hipótese, custo e critério de
  reabertura.
- No caminho `go`, cada tick de decisão tem ordem e barreira explícitas,
  rewards/infos por agente e determinismo testado.
- No caminho `no-go`, nenhuma dependência nova é adicionada e o roadmap
  single-agent permanece suficiente e documentado.

## Refactor boundary

Pode criar um adapter fino e tipos de mapeamento. Não alterar semântica
econômica ou inserir treinamento longo; qualquer mudança no core volta à Fase
06.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run ruff check app tests
uv run python -m app.core.runner --artifact-dir <single-agent-a>
uv run python -m app.core.runner --artifact-dir <single-agent-b>
git diff --check
```

Se o resultado for `go`, adicionar o checker da biblioteca aprovada e um smoke
de reset/step/close para dois ou mais agentes. Se for `no-go`, verificar apenas
que o contrato single-agent e o baseline não regrediram.

## Security, reliability, observability, and recovery

- Enforcear fronteiras de observação e não registrar estado privado em logs.
- Identificar cada agente e cada ação no trace sem depender de wall-time.
- Abortar a barreira em caso de agente ausente, ação inválida ou erro de kernel.
- Manter o caminho single-agent recuperável e independente.
- Não remover a dependência nova parcialmente; reverter a fase como unidade se
  o contrato não se sustentar.

## Acceptance criteria

- [ ] A necessidade ou não de MARL está justificada por pergunta verificável.
- [ ] Decisão inclui custo, risco, dependência e critérios de reabertura.
- [ ] No caminho `go`, sincronização, IDs, masks, obs, reward e terminalidade
  estão especificados e testados.
- [ ] No caminho `no-go`, PettingZoo não foi adicionado sem necessidade.
- [ ] Baseline e ambiente single-agent não sofrem regressão.

## Evidence required

- ADR de decisão e matriz de alternativas.
- Testes red/green e smoke multiagente, ou prova de no-go.
- Comparação de artifact single-agent antes/depois.
- Registro de dependências e orçamento, somente se `go`.

## Handoff / stop condition

Parar após uma decisão explícita. Se `no-go`, seguir para a Fase 10; se `go`,
entregar o contrato MARL e iniciar somente o smoke aprovado antes de qualquer
campanha longa.
