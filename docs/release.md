# Release experimental 0.2.0

Esta entrega fecha a primeira trilha experimental do roadmap local:

- baseline com manifesto, métricas e trace canônico reprodutível;
- contratos de ordem, fill, reset, lifecycle e contabilidade reforçados;
- políticas econômicas nomeadas, snapshots públicos e expiração terminal;
- ambiente Gymnasium single-agent com reward incremental e barreira de evento;
- treino curto NumPy/CEM, checkpoint e avaliação pareada em splits disjuntos;
- benchmark/profile headless, lint, cobertura, checker Gymnasium e CI
  localizáveis.

O estado reproduzível desta entrega é o worktree local auditado. A execução
curta do baseline em `--max-time 120` produziu o mesmo artifact em duas
execuções (`baseline.json` SHA-256
`c832e7a18bccd56435a7d204c928ff042766b8768c8207b67d90cc9153da1c0b`), mas a
prova em clone Git limpo e a publicação continuam gates separados.

Não é uma release de produção financeira. Não inclui negociação real, capital,
deploy, publicação externa ou conclusão de superioridade econômica.
