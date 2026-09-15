# Phase 02 — Ambiente RL single-agent

Status: Complete

## Source inputs

- `GOALS.md` e `PLANS.md`
- contrato produzido pela Fase 01
- `app/core/runner.py`, `app/core/kernel.py`, `app/agents/base.py`
- candidato não integrado em `origin/claude/eager-leakey:app/env/gym_env.py`
- referência local `papers/ABIDES-Gym- Gym Environments for Multi-Agent Discrete Event Simulation and Application to Financial Markets.pdf`

## Objective

Expor um episódio single-agent com sincronização correta entre o loop assíncrono
e a API `reset`/`step`/`close`, sem esconder decisões de mercado em estado
privado ou depender da GUI.

## In scope

- Escolher o agente controlado e formalizar observação, ação, reward,
  termination, truncation e info.
- Implementar o mecanismo de barreira/`StopSignalAgent` equivalente.
- Adicionar `app/env` e dependências mínimas aprovadas.
- Definir bounds, dtype, normalização, seed e comportamento de reset.
- Integrar background heurístico e testar ações HOLD, limit e market conforme o
  contrato aprovado.
- Validar o ambiente com checker da biblioteca e testes de episódios curtos.

## Non-goals

- PettingZoo, controle simultâneo de vários agentes ou treinamento longo.
- Reward experimental sem especificação aprovada.
- Renderização da GUI como parte do ambiente.

## Dependencies and prerequisites

- Fase 01 completa.
- Decisões sobre agente, espaços e reward.
- Aprovação explícita para adicionar `gymnasium`/`numpy` ao manifesto.

## Expected files or components

- `app/env/__init__.py` e wrapper de ambiente.
- Proxy/agente RL e testes de contrato em `tests/`.
- `pyproject.toml`/`uv.lock`, somente se a dependência for aprovada.

## Decisions requiring human input

- Agente inicial e objetivo: execução, market making ou descoberta de preço.
- Número de níveis LOB, normalização e limites de posição.
- Espaço discreto/contínuo e semântica de preço/quantidade.
- Reward e tratamento de posição aberta ao fim do episódio.

## Approval gate

Revisar a especificação de interface antes de implementar. O wrapper remoto é
apenas referência de trabalho; não é evidência de compatibilidade. Dependências
novas e alteração do manifesto exigem aprovação nesta fase.

## Red

- Testes devem falhar inicialmente para import do ambiente, `reset`, `step`,
  shapes/dtypes, ação inválida, seed repetida, sincronização e término.
- Rodar o checker Gymnasium contra o contrato pretendido e registrar cada falha.

## Green

- Implementar o ambiente mínimo que satisfaz o contrato aprovado, com um único
  agente RL e background determinístico.
- Garantir que cada `step` consuma exatamente uma decisão RL e retorne uma
  observação/reward coerentes.

## Refactor boundary

Pode desacoplar o ambiente do runner e criar adaptadores. Não introduzir
multiagente, algoritmo de treinamento ou mudança no matching nesta fase.

## Verification commands

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run python -c "from app.env import AbidesGymEnv; env = AbidesGymEnv(seed=42); obs, info = env.reset(); print(obs.shape, info); env.close()"
```

Executar o checker oficial da biblioteca e um episódio com seed fixa; se uma
ferramenta não estiver instalada, registrar `Unavailable` em vez de inferir
sucesso.

## Security, reliability, observability, and recovery

- Validar ações antes de enviá-las à exchange.
- Não permitir que um episódio pendente continue consumindo eventos depois de
  `terminated` ou `truncated`.
- Limitar logs de treino e manter `seed`, versão e configuração no `info`/trace.
- Fechar e reconstruir o ambiente após erro para evitar vazamento de estado.

## Acceptance criteria

- [x] `reset(seed=...)` é determinístico e retorna shape/dtype do contrato.
- [x] `action_space` e `observation_space` aceitam exatamente os valores definidos.
- [x] `step` sincroniza uma ação, retorna reward finito e sinaliza término corretamente.
- [x] Ações inválidas são rejeitadas sem corromper o episódio.
- [x] O ambiente passa o checker oficial ou a limitação está documentada.
- [x] GUI e ambiente podem executar separadamente.

## Evidence required

- Especificação aprovada de obs/action/reward.
- Testes red/green, checker e episódio de smoke.
- Registro de dependências e lockfile, se alterados.
- Output determinístico de dois resets com a mesma seed.

## Handoff / stop condition

Parar com um ambiente single-agent verificável. Só abrir a Fase 03 após
confirmar que o episódio é estável e decidir se há necessidade de MARL real.
