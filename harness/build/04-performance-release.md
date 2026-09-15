# Phase 04 — Performance, CI e release

Status: Complete

## Source inputs

- resultados e gargalos da Fase 03
- `app/core/`, `app/agents/`, `app/main.py`
- `pyproject.toml`, `uv.lock`, `.python-version`
- comandos e limitações registrados no build log

## Objective

Tornar o laboratório operável e mensurável, separando o caminho headless do
visual, adicionando gates de qualidade e decidindo se alguma otimização é
justificada.

## In scope

- Benchmark do loop de eventos sem GUI, com configuração e hardware registrados.
- Perfil de CPU/memória e identificação de gargalos reais.
- Separação de core, execução batch e dashboard quando o perfil justificar.
- CI para testes, compilação, lint/type check e validação do baseline.
- Política de versionamento, changelog ativo e artefatos de release experimental.
- Decisão documentada: permanecer em Python, otimizar partes ou avaliar JAX.

## Non-goals

- HPC, deploy ou publicação automática.
- Otimizar antes de medir.
- Alterar o modelo econômico apenas para ganhar throughput.
- Fazer merge/push ou criar release pública sem autorização.

## Dependencies and prerequisites

- Fase 01 para benchmark válido.
- Fase 03 para medir custo de treino/avaliação e justificar escala.
- Aprovação de CI, ferramentas e eventual aumento de dependências.

## Expected files or components

- benchmark headless e fixtures de performance.
- configuração de CI e checks locais.
- documentação de release e decisão de performance.
- mudanças de arquitetura somente quando sustentadas por perfil.

## Decisions requiring human input

- Plataforma e orçamento de CI.
- Metas de throughput, latência e memória.
- Suporte oficial de OS/Python.
- Critério para aceitar uma migração para JAX ou outra arquitetura.

## Approval gate

Não instalar infraestrutura, publicar artefatos ou executar carga prolongada sem
aprovação do orçamento, destino e política de recuperação.

## Red

- Medir e registrar o benchmark atual sem GUI; o gate deve revelar que não há
  série histórica, meta ou CI definido.
- Criar um check de CI que falhe quando testes ou compilação não passam.

## Green

- Adicionar benchmark reproduzível, gates mínimos e relatório de perfil.
- Corrigir somente gargalos medidos e preservar o resultado canônico.
- Documentar a decisão de permanecer ou migrar de runtime.

## Refactor boundary

Pode mover código entre módulos para separar core/UI e introduzir ferramentas de
desenvolvimento aprovadas. Não reescrever o matching ou o ambiente sem fase
própria.

## Verification commands

```bash
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run <comando-de-benchmark-headless>
git diff --check
```

Executar o pipeline de CI em branch de validação quando essa integração tiver
autorização; registrar falhas de ambiente como `Unavailable`.

## Security, reliability, observability, and recovery

- Não expor segredos em logs de CI ou artefatos de performance.
- Fixar configuração e ambiente do benchmark para evitar conclusões falsas.
- Manter caminho de execução headless funcional se a GUI falhar.
- Guardar resultados anteriores antes de substituir uma implementação.
- Recuperação por revert dos arquivos da fase, seguida de execução dos gates.

## Acceptance criteria

- [x] O throughput do core é medido sem GUI e com configuração reproduzível.
- [x] Há gates automatizados para testes e compilação.
- [x] Lint/type check/coverage estão presentes ou a ausência é uma decisão registrada.
- [x] A separação core/UI não quebra o dashboard nem o runner headless.
- [x] A decisão de otimização é sustentada por dados, não por suposição.
- [x] A versão e o changelog correspondem ao estado entregue.

## Evidence required

- Relatório de benchmark com ambiente e configuração.
- Resultados de CI e checks locais.
- Perfil antes/depois, se houve otimização.
- ADR ou decisão equivalente sobre runtime e release.

## Handoff / stop condition

Parar após os gates de qualidade e a decisão de performance estarem verificáveis.
Deploy, publicação e release externa continuam exigindo aprovação própria.
