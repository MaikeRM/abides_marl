# Phase 03 — MARL, treinamento e avaliação

Status: Complete

## Source inputs

- ambiente aprovado da Fase 02
- `GOALS.md`, `PLANS.md` e `docs/baseline-scenario.md`
- heurísticas em `app/agents/`
- papers locais ABIDES-MARL, ABIDES-Gym e JaxMARL

## Objective

Transformar o ambiente em um laboratório experimental capaz de treinar,
avaliar e comparar políticas com um protocolo estatístico reproduzível.

## In scope

- Decidir single-agent ampliado versus PettingZoo/multiagente.
- Definir agentes controláveis, observabilidade centralizada/descentralizada,
  políticas, action masks e protocolo de sincronização.
- Escolher o primeiro stack de treinamento após validar compatibilidade.
- Criar configuração versionada de treino, seeds, checkpoints e avaliação.
- Comparar política aprendida com `MarketMaker`, `Value`, `ZI` e `Liquidity`.
- Medir PnL, shortfall, fill ratio, inventário, risco, impacto, estabilidade e
  métricas de mercado relevantes.

## Non-goals

- Declarar superioridade econômica a partir de uma única seed.
- Usar dados reais ou capital real.
- Otimizar o kernel antes de haver perfil e baseline estatístico.
- Promover modelo para produção.

## Dependencies and prerequisites

- Fase 02 completa e ambiente validado.
- Definição de reward e protocolo de avaliação.
- Aprovação de dependências de treino e do custo computacional.

## Expected files or components

- módulo(s) de treino e avaliação.
- configurações versionadas e formato de resultados.
- testes de smoke e scripts de comparação.
- documentação do benchmark e critérios de sucesso.

## Decisions requiring human input

- Necessidade e biblioteca de multiagente.
- Algoritmo inicial: SB3, RLlib ou alternativa.
- Quantidade de seeds, intervalos de confiança e limiar de sucesso.
- Modelo de avaliação: treino/teste, cenários adversos e generalização.

## Approval gate

Não iniciar treinamento longo, instalar stack pesado ou criar artefatos grandes
antes de aprovar algoritmo, orçamento, seeds e formato dos resultados.

## Red

- Criar smoke test que exija configuração, carregamento do ambiente, uma iteração
  de treino, checkpoint e avaliação; ele deve falhar sem pipeline.
- Criar teste que compare a execução da política e do baseline com o mesmo
  cenário, sem exigir ainda um resultado econômico positivo.

## Green

- Implementar o menor pipeline reproduzível, com treino curto e avaliação
  separada, registrando seeds e configuração.
- Produzir comparação contra pelo menos um agente heurístico e métricas de
  desempenho/risco aprovadas.

## Refactor boundary

Pode separar treino, avaliação e geração de relatórios. Não alterar a semântica
do ambiente ou adicionar novas estratégias econômicas sem nova decisão.

## Verification commands

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run <comando-de-smoke-de-treino>
uv run <comando-de-avaliacao>
```

Os placeholders acima só viram comandos de execução após a escolha do stack;
comandos planejados não são evidência.

## Security, reliability, observability, and recovery

- Fixar seeds, versão, configuração e dependências em cada run.
- Limitar tamanho e local de checkpoints; não persistir dados sensíveis.
- Interromper treino degradado quando NaN, overflow ou ambiente inválido forem
  detectados.
- Preservar resultados parciais e distinguir falha de treino de falha de
  avaliação.
- Permitir reexecutar uma avaliação sem sobrescrever o resultado anterior.

## Acceptance criteria

- [x] Um treino curto começa de configuração versionada e termina com checkpoint.
- [x] Avaliação é independente do estado interno do treino.
- [x] Pelo menos três seeds são executadas, ou a exceção é aprovada e registrada.
- [x] Resultados incluem métricas de retorno, execução, risco e mercado.
- [x] Comparação contra heurística usa o mesmo protocolo e cenário.
- [x] A conclusão estatística respeita os limiares aprovados, sem overclaiming.

## Evidence required

- Configuração, seeds, versões e comandos.
- Logs de smoke, checkpoints e resultados de avaliação.
- Tabela ou relatório comparativo com limitações.
- Revisão independente dos critérios e interpretação.

## Observed evidence

- `uv run python -m app.experiments.train --config
  configs/smoke_training.json --output-dir <tmp>` — observado como pass; o
  checkpoint foi criado com seeds `[11, 22, 33]`.
- `uv run python -m app.experiments.evaluate --checkpoint
  <tmp>/checkpoint.npz --config configs/smoke_training.json --output-dir
  <tmp>` — observado como pass; a avaliação produziu episódios para as três
  seeds e quatro famílias heurísticas.
- `uv run python -m unittest discover -s tests -v` — observado como pass na
  revalidação atual, com 15 testes.
- `uv run python -m compileall -q app tests` e `uv run ruff check app tests`
  — observados como pass.
- Os resultados foram classificados como smoke: a comparação ainda não é
  pareada por papel/população, não possui holdout, intervalos de confiança,
  tamanho de efeito ou limiar econômico aprovado. O registro completo está em
  [`../build-log.md`](../build-log.md), e a Fase 08 é o contrato responsável
  por fechar essa lacuna.

## Handoff / stop condition

Parar quando houver um pipeline curto e reproduzível com comparação válida.
Resultados positivos não autorizam produção; performance/escala segue para a
Fase 04 apenas com evidência de gargalo.
