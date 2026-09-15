# Performance e qualidade

## Protocolo

O benchmark do core é headless e não importa a GUI para executar o loop. Ele
registra Python, plataforma, cenário, número de execuções, eventos processados
e eventos por segundo:

```bash
uv run python -m benchmarks.benchmark_core --runs 3 --max-events 2000 \
  --output /tmp/abides-core-benchmark.json
```

Os números abaixo são uma medição local do worktree, não uma meta universal.
O arquivo `/tmp/abides-core-benchmark.json` usado na verificação é descartável;
o protocolo e a configuração permanecem versionados.

Medição observada em 2026-09-15: Python `3.12.11`, macOS `26.6.2 arm64`,
3 execuções de 2.000 eventos, média de `94.311,765` eventos/s, mínimo de
`93.704,430` e máximo de `95.166,154`. Esses valores são apenas uma linha de
base local; não são uma promessa de throughput entre máquinas.

O perfil curto complementar (`1 x 500` eventos) observou `0,14 s` de tempo
real, `0,06 s` de CPU de usuário e pico de RSS de `28.196.864` bytes sem swap.
O `cProfile` apontou `Kernel._record_event` como o caminho cumulativo mais
frequente (`678` chamadas, incluindo a trilha de observabilidade), seguido do
loop `SimulationRunner.step`/`Kernel.step`. Isso identifica um ponto de
medição, não autoriza removê-lo: a trilha canônica é parte do contrato.

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

Type checking está explicitamente fora deste ciclo: não há anotação suficiente
no código legado para introduzir `mypy` sem ampliar a fase, e a ausência é
registrada em vez de fingir um gate que não existe.
