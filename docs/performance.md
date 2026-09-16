# Performance e qualidade

## Protocolo

O benchmark do core é headless e não importa a GUI para executar o loop. Ele
registra Python, plataforma, cenário, warmup, número de execuções, eventos
processados, artifact serializado e eventos por segundo:

```bash
uv run python -m benchmarks.benchmark_core --runs 3 --warmup-runs 1 --max-events 20000 \
  --output /tmp/abides-core-benchmark.json
```

Os números abaixo são uma medição local do worktree, não uma meta universal.
O arquivo `/tmp/abides-core-benchmark.json` usado na verificação é descartável;
o protocolo e a configuração permanecem versionados.

Medição final observada em 2026-09-15: Python `3.12.11`, macOS `26.6.2 arm64`,
warmup `1`, `3` execuções de 20.000 eventos, média de `59.042,319` eventos/s,
mínimo de `58.169,056` e máximo de `60.316,534`. O artifact serializado médio
teve `3.976.019,667` bytes e a variação observada do high-water RSS foi de
`19.988.480` bytes. Esses valores são uma linha de base local, não uma meta
universal.

O perfil complementar (`1 x 1.000` eventos) observou `0,0732775 s`, `1.224`
eventos de trace e artifact de `224.286` bytes. O `cProfile` apontou o custo
de `copy.deepcopy` da trilha e `Kernel._record_event` como caminhos relevantes,
além do wrapper `run_artifact`; isso identifica um ponto de medição, não
autoriza remover a trilha, que faz parte do contrato.

O benchmark publica `resource_budget.status=not_configured`: ainda não existe
meta humana aprovada de throughput, RSS, latência ou tamanho de artifact.

## Decisão de runtime

O core permanece em Python nesta fase. Não há evidência de gargalo que
justifique JAX ou GPU antes de comparar o custo do treinamento e da avaliação
em um protocolo mais longo. Otimizações futuras devem preservar o artifact
canônico e incluir perfil antes/depois.

## Gates

- `uv sync --locked`
- `uv run ruff check app tests benchmarks`
- `uv run python -m compileall -q app tests benchmarks`
- `uv run coverage run --source=app,benchmarks -m unittest discover -s tests -v`
- `uv run coverage report --fail-under=55`
- duas execuções do artifact do baseline comparadas com `cmp`
- `uv run python -m benchmarks.profile_core --max-events 500 --top 10`

Type checking está explicitamente fora deste ciclo: não há anotação suficiente
no código legado para introduzir `mypy` sem ampliar a fase, e a ausência é
registrada em vez de fingir um gate que não existe.
