# Workflow prompts

Estes pontos de entrada são reutilizáveis. Eles apontam para os artefatos
canônicos e não substituem decisões registradas em `GOALS.md` ou `PLANS.md`.

## Approval / Aprovação

Preparar uma fase produz o escopo para aprovação; executar uma fase exige o
gate explícito definido no contrato correspondente.

## Orientar o repositório

Leia `AGENTS.md`, `GOALS.md`, `PLANS.md`, `docs/current-state.md`, o arquivo de
baseline e o `harness/build-log.md`. Confirme branch, worktree, fontes de
verdade, comandos e lacunas com arquivos e execução local. Não escreva antes
de apresentar escopo, riscos e caminhos exatos.

## Preparar uma fase

Leia `AGENTS.md`, `GOALS.md`, `PLANS.md` e o contrato da fase selecionada em
`harness/build/`. Reavalie o estado vivo, dependências, decisões humanas,
red/green/refactor e critérios de aceitação. Proponha apenas a fase indicada e
pare no gate de aprovação; não implemente a fase seguinte.

## Executar uma fase aprovada

Use somente o escopo e os arquivos do contrato aprovado. Rode o menor check
red, implemente o green mínimo, faça o refactor permitido e execute as
verificações nomeadas. Não altere branch, dependências, infraestrutura ou
artefatos externos sem autorização separada. Pare no handoff da fase.

## Verification / Verificar e registrar evidência

Rode os comandos do contrato e compare o resultado com critérios observáveis.
Classifique cada verificação como `Planned`, `Observed pass`, `Observed fail`,
`Skipped`, `Unavailable` ou `Reported`. Atualize apenas o
`harness/build-log.md` com resultados reais, limitações e referências aos
arquivos.

## Revisar ou remediar

Compare código, testes, manifestos, documentação, fase aprovada e build log.
Priorize bugs, regressões, contratos quebrados e evidência insuficiente. Cada
achado deve ter um dono único: instrução, objetivo, plano, fase, teste,
validador ou revisão. Não transforme uma recomendação em implementação sem
aprovação da fase correspondente.

## Handoff

Resuma alterações, red/green/refactor, verificações, skips, limitações,
decisões pendentes e próximo passo. Confirme que não há trabalho implícito da
fase seguinte. Commit, push, pull request e deploy continuam sendo decisões
separadas.
