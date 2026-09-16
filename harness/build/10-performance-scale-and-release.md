# Phase 10 — Escala, performance e release verificável

Status: Complete (local; approval gates open)

## Source inputs

- baseline e artifacts reconciliados da Fase 05
- contratos do core, RL e avaliação das Fases 06–09
- `benchmarks/benchmark_core.py`, `docs/performance.md`,
  `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`
- evidências locais de benchmark, coverage, Ruff e CI configurado
- limitações da GUI em `app/main.py`

## Objective

Estabelecer limites de escala mensuráveis e uma entrega verificável, mantendo o
caminho headless reproduzível e só aplicando otimizações ou mudanças de runtime
quando um gargalo medido e um protocolo estável justificarem o custo.

## In scope

- Benchmarkar eventos, episódios e campanhas em configurações curta, média e
  longa, registrando hardware, Python, dependências, seed e configuração.
- Medir CPU, memória, alocação, tamanho/serialização de trace, tempo por step e
  custo de treino/evaluation; separar warmup de medida.
- Criar série histórica de benchmark e metas aprovadas de throughput, latência,
  memória, duração e tamanho de artifact.
- Corrigir gargalos medidos sem alterar a ordem canônica ou a semântica
  econômica; repetir reprodução antes/depois.
- Fechar workflow de CI com dependências pinadas, testes, compilação, lint,
  coverage, artifact comparison e benchmark smoke; executar em runner
  autorizado ou marcar o limite como `Unavailable`.
- Avaliar type checking incremental e compatibilidade de plataformas.
- Verificar GUI manualmente e corrigir apenas defeitos de release/inspeção,
  mantendo-a separada do core.
- Preparar pacote/changelog/release local verificável, sem publicar.

## Non-goals

- Deploy, publicação pública, integração com corretoras ou dados reais.
- JAX/GPU/HPC sem gatilho quantitativo e decisão registrada.
- Otimização que mude matching, reward, trace ou política econômica para ganhar
  números.
- Fazer merge, commit, push ou criar release remota automaticamente.

## Dependencies and prerequisites

- Fases 05–09 concluídas ou `no-go` MARL registrado.
- Protocolo científico e baseline congelados.
- Acesso/autoridade para qualquer runner CI ou ambiente externo que venha a ser
  usado; ausência deve ser registrada, não mascarada.
- Metas e orçamento aprovados antes de benchmark longo.

## Expected files or components

- benchmark parametrizado, relatório de perfil e série histórica.
- workflow CI e documentação de plataformas/suporte.
- configuração de type checking, se aprovada.
- smoke de GUI/manual checklist e correções isoladas.
- pacote de release local e changelog alinhado aos artifacts.

## Decisions requiring human input

- Plataformas oficiais, versão de Python, orçamento de CI e política de cache.
- Metas de throughput, memória, latência e tamanho de artifact.
- Gatilho numérico para vetorizar, trocar estrutura, usar multiprocessing ou
  avaliar JAX/GPU.
- Política de retenção de artifacts e critério de release experimental.

## Approval gate

Nenhuma carga longa, serviço externo, publicação ou migração de runtime começa
sem orçamento, destino e recuperação definidos. Otimização só é aprovada após
perfil reproduzível e comparação de comportamento.

## Red

- Executar o benchmark atual em configuração controlada e confirmar que não há
  meta ou série histórica suficiente para declarar escala.
- Criar checks que falhem quando testes, compilação, Ruff, coverage ou
  reprodução do baseline falharem.
- Fazer uma medição de perfil que capture o caminho headless e o tamanho do
  trace, incluindo o custo de artifacts.
- Verificar o caminho inválido de `_sync_agent` e a ausência de smoke gráfico
  automatizado; não tratar a GUI não aberta como pass.

## Green

- Relatório de performance inclui ambiente, configuração, dispersão e limites;
  cada otimização mostra antes/depois e preserva o artifact canônico.
- CI executado no ambiente autorizado ou sua indisponibilidade fica explícita;
  checks locais continuam copy-pasteáveis.
- Type checking é adotado apenas onde contratos e cobertura tornam o sinal útil.
- Pacote de release local pode ser instalado, executado e comparado sem GUI.

## Refactor boundary

Pode separar caminhos de benchmark, reduzir overhead medido e reorganizar
configuração de CI. Não mudar o modelo econômico ou a identidade do trace para
melhorar benchmark.

## Verification commands

```bash
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests benchmarks
uv run ruff check app tests benchmarks
uv run python -m benchmarks.benchmark_core --runs <runs> --max-events <events>
uv run python -m app.core.runner --artifact-dir <artifact-a>
uv run python -m app.core.runner --artifact-dir <artifact-b>
cmp <artifact-a>/baseline.json <artifact-b>/baseline.json
git diff --check
```

Executar o workflow CI apenas no runner autorizado e anexar o resultado. Se
type checking, GUI ou runner remoto não estiverem disponíveis, registrar
`Unavailable` com a razão e manter o gate correspondente aberto.

## Security, reliability, observability, and recovery

- Redigir segredos e caminhos sensíveis dos logs de CI e perfil.
- Limitar artifacts de benchmark e separar traces brutos de sumários.
- Manter o benchmark headless se a GUI falhar.
- Guardar resultados antes/depois e reverter somente a otimização que degradar
  correção, reprodução ou custo.
- Não publicar pacote ou changelog como release pública sem autorização.

## Acceptance criteria

- [x] Benchmark longo e perfil reproduzível têm ambiente e configuração.
- [ ] Metas e limites de recursos estão aprovados e medidos — decisão humana
  permanece aberta; o benchmark publica `resource_budget.status=not_configured`.
- [x] CI cobre os gates essenciais ou limitações estão explicitamente abertas.
- [x] Qualquer otimização preserva semântica e artifact canônico — nenhuma
  otimização de runtime foi aplicada nesta fase.
- [x] GUI e caminho headless têm verificação proporcional ao risco — correção
  estática/compilação da GUI e benchmark headless passaram; smoke gráfico é
  `Unavailable` sem sessão gráfica.
- [x] Pacote/release local é instalável e reproduzível sem publicação externa.

## Evidence observed

- **Benchmark:** `uv run python -m benchmarks.benchmark_core --runs 3
  --warmup-runs 1 --max-events 20000` observou Python `3.12.11`, macOS
  `26.6.2 arm64`, média de `59.042,319` eventos/s, mínimo de `58.169,056`,
  máximo de `60.316,534`, artifact médio de `3.976.019,667` bytes e variação de
  RSS de `19.988.480` bytes.
- **Profile:** `uv run python -m benchmarks.profile_core --max-events 1000
  --top 10` observou `0,0732775 s`, 1.224 eventos de trace e identificou
  `deepcopy`/trilha canônica como custo relevante.
- **Quality:** 34 testes, compileall, Ruff, coverage local, comparação de
  artifacts e workflow CI versionado foram observados localmente; nenhum
  runner GitHub remoto foi executado nesta sessão.
- **Release:** `uv sync --locked` e o runner headless são os caminhos locais;
  tag, pacote publicado, deploy e CI remoto continuam não autorizados.
- **Open gates:** type checking e budgets de recurso permanecem
  `Unavailable/by decision`, conforme `docs/performance.md`.

## Evidence required

- Relatórios de benchmark/perfil antes e depois, com série histórica.
- Logs de CI ou status `Unavailable` fundamentado.
- Resultado de type checking e checklist visual, quando aplicáveis.
- Artifact e checksum da release local, changelog e limitações.

## Handoff / stop condition

Parar quando os limites de escala e a release local forem verificáveis. Depois
disso, abrir experimentos de pesquisa somente com hipótese, lineage, baseline,
holdout e critério de rejeição próprios; não transformar este plano em
autorização de publicação ou produção.
