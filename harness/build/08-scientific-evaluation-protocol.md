# Phase 08 — Protocolo de avaliação científica

Status: Complete (plumbing local; threshold approval open)

## Source inputs

- ambiente e política congelados da Fase 07
- semântica econômica da Fase 06
- `app/experiments/train.py`, `app/experiments/evaluate.py`,
  `app/experiments/config.py`
- `app/agents/` e `docs/baseline-scenario.md`
- resultados smoke das Fases 03–04 e limitações no build log
- literatura local somente como contexto, não como evidência de resultado

## Objective

Substituir a comparação smoke por um protocolo capaz de sustentar conclusões
condicionais, reproduzíveis e fail-closed sobre uma política aprendida, sem
promover um resultado positivo isolado a vantagem econômica.

## In scope

- Definir unidade experimental, papel controlado, população, composição do
  mercado, cenário, horizonte e seed.
- Parear política e heurísticas com o mesmo cenário, participantes, seed,
  orçamento de eventos e regras de custo; separar diferenças de policy de
  diferenças de população.
- Separar treino, validação, holdout/teste e, se necessário, stress scenarios;
  congelar checkpoint e parâmetros antes do holdout.
- Incluir baselines HOLD, random e heurísticos relevantes, com a mesma API e
  contabilização.
- Definir métricas de retorno/PnL, inventário, risco, fill ratio, shortfall,
  turnover, impacto, qualidade de mercado e estabilidade.
- Escolher número de seeds, bootstrap/intervalos de confiança, tamanho de
  efeito, testes múltiplos e limiares de sucesso/rejeição.
- Gerar artifacts versionados contendo config, seeds, versões, hashes,
  métricas brutas, agregados, falhas e limitações.
- Implementar avaliação que não retreine, não retune e não sobrescreva outputs;
  falhas de integridade ou amostra devem impedir conclusão automática.

## Non-goals

- Alterar reward ou ambiente para melhorar o resultado depois de ver holdout.
- Declarar política pronta para produção, capital real ou publicação.
- Treino distribuído, GPU, JAX ou stack pesado antes de justificar custo.
- Transformar a literatura ou resultados de outras combinações em evidência da
  combinação atual.

## Dependencies and prerequisites

- Fases 06 e 07 completas.
- Definição de política, custos e papéis pareados.
- Orçamento computacional aprovado para o número de seeds e cenários.
- Formato de artifact e retenção definidos antes do treino longo.

## Expected files or components

- schema de protocolo e configuração de campanhas.
- runner de avaliação pareada e agregador estatístico.
- baselines HOLD/random/heurísticos e fixtures de cenário.
- artifacts brutos, sumários, tabela de resultados e relatório de limitações.
- testes contra leakage, seeds duplicadas, checkpoint errado e output parcial.

## Decisions requiring human input

- Número final de seeds, horizonte, cenários e orçamento de CPU/tempo.
- Métricas primárias/secundárias e limiar mínimo de efeito econômico.
- Método de intervalo de confiança e política para comparação múltipla.
- Critério de sucesso, inconclusivo e rejeitado; a recomendação é que
  insuficiência de amostra, NaN, leakage ou falha de pareamento seja
  automaticamente `inconclusive`/`rejected`, nunca `pass`.

## Approval gate

O protocolo precisa ser congelado antes de executar treino longo ou consultar o
holdout. Um resultado smoke pode validar plumbing, mas não aprova nenhuma
alegação econômica.

## Red

- Criar um caso de avaliação que falhe ao misturar população/papel entre policy
  e heurística ou ao reutilizar seed de treino no holdout sem registro.
- Criar testes para checkpoint/config/hash incompatíveis, seeds duplicadas,
  outputs sobrescritos, amostra insuficiente e NaN/inf.
- Verificar que o agregador não conclui superioridade quando os limiares ainda
  estão ausentes ou quando o intervalo cruza o baseline.

## Green

- Cada comparação registra exatamente o protocolo, cenário, seed, checkpoint,
  versão do código e artifact de entrada.
- Avaliação policy/heurística é pareada e reproduzível; treino e holdout são
  separados por contrato.
- O relatório distingue resultado bruto, incerteza, efeito, decisão e
  limitações, sem overclaiming.

## Refactor boundary

Pode separar train/evaluate/report, introduzir agregadores e schemas. Não
retunar a policy com base em holdout nem alterar o ambiente para acomodar o
relatório.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run ruff check app tests
uv run python -m app.experiments.train --config <protocol-config> --output-dir <train-dir>
uv run python -m app.experiments.evaluate --checkpoint <train-dir>/checkpoint.npz --config <protocol-config> --output-dir <eval-dir>
uv run python -m app.experiments.evaluate --checkpoint <train-dir>/checkpoint.npz --config <holdout-config> --output-dir <holdout-dir>
git diff --check
```

Executar uma campanha duplicada somente para verificar reprodução; não contar
essa duplicação como seed independente. Conferir artifacts por hash e manter
outputs de treino, validação e holdout separados.

## Security, reliability, observability, and recovery

- Não usar dados reais, credenciais ou fontes externas não versionadas.
- Guardar configuração e hashes junto dos resultados, mas limitar tamanho de
  traces e excluir informação sensível.
- Interromper campanhas com corrupção, NaN, overflow ou ambiente inválido.
- Nunca retunar depois de observar holdout sem abrir uma nova campanha e uma
  nova identidade de lineage.
- Se uma campanha falhar, conservar outputs parciais como `failed`, não como
  resultado válido.

## Acceptance criteria

- [x] Protocolo pareado e versionado define cenário, papel, seeds e horizonte.
- [x] Treino, validação, holdout e stress são separados e auditáveis.
- [x] Baselines nulos e heurísticos usam o mesmo contrato de avaliação.
- [x] Métricas, ICs, efeitos e gates fail-closed estão implementados.
- [x] Artifacts preservam config, versões, hashes, dados brutos e limitações.
- [x] Nenhum relatório declara superioridade sem critério estatístico aprovado.

## Evidence observed

- **Protocol:** `configs/evaluation_protocol.json` e
  `app/experiments/protocol.py` observam schema versionado, papel,
  `training/validation/holdout/stress` disjuntos, métricas de retorno/risco/
  mercado, bootstrap determinístico e Bonferroni.
- **Paired run:** treino NumPy/CEM seguido de avaliação `validation` e
  `holdout` gerou `evaluation-result.v2`, checkpoint/config/protocol hashes e
  os seis comparadores (`HOLD`, `RANDOM` e quatro adapters heurísticos). As
  duas execuções observaram decisão `inconclusive` e não treinaram durante a
  avaliação.
- **Fail closed:** `tests/test_protocol.py` cobre seed duplicada, amostra
  insuficiente, tamanho incompatível, NaN e ausência de `minimum_effect`; a
  suíte integrada observou 34/34 pass.
- **Limitation:** `minimum_effect=null` permanece deliberado; sem decisão
  humana de efeito mínimo e orçamento, nenhum artifact pode ser lido como
  superioridade econômica. Os adapters heurísticos são comparadores pela mesma
  API, não prova de identidade comportamental completa.

## Evidence required

- Protocolo aprovado e orçamento de campanha.
- Artifacts de uma campanha completa e de uma repetição de reprodução.
- Relatório com resultados por seed, agregados, incerteza, decisão e falhas.
- Revisão independente contra leakage e pareamento.

## Handoff / stop condition

Parar quando a avaliação puder classificar uma policy como pass, inconclusive ou
rejected sem julgamento oculto. Só então decidir MARL na Fase 09 e escala na
Fase 10.
