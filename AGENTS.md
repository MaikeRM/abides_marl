# ABIDES-MARL PoC

## Purpose

Este repositório mantém um simulador de microestrutura de mercado orientado a
eventos, com agentes heurísticos e uma trilha de evolução para experimentos de
RL/MARL.

## Fontes de verdade

- `app/`: comportamento executável do simulador.
- `tests/`: contratos automatizados e regressões observadas.
- `pyproject.toml` e `uv.lock`: versão do Python e dependências.
- `docs/current-state.md`: inventário do estado atual.
- `docs/baseline-scenario.md`: cenário e métricas do baseline.
- `GOALS.md`: resultados desejados e limites do projeto.
- `PLANS.md`: ordem das fases e dependências.
- `harness/build/<phase>.md`: contrato de uma fase autorizada.
- `harness/build-log.md`: evidências observadas, nunca resultados planejados.

Quando fontes divergirem, o código e os comandos executados têm precedência
sobre documentação histórica ou planos anteriores. Divergências devem ser
registradas e resolvidas no artefato que possui a responsabilidade pelo fato.

## Acordos de trabalho

- Usar Python `3.12.11` e preferir `uv run` para comandos do projeto.
- Executar `uv run python -m unittest discover -s tests -v` antes de concluir
  qualquer mudança que atravesse o núcleo ou os agentes.
- Executar `uv run python -m compileall -q app tests` como verificação mínima de
  sintaxe.
- Executar `uv run python -m app.core.runner` para validar o cenário padrão
  quando a mudança tocar o runner, a exchange, o kernel ou os agentes.
- Trabalhar em uma fase por vez. A fase seguinte não começa automaticamente
  quando a anterior termina.
- Ler o arquivo da fase, explicitar escopo e aprovação, e registrar red, green,
  refactor, verificações, limitações e handoff no build log.
- Manter código de aplicação, testes e documentação de estado separados dos
  artefatos de planejamento; não transformar um plano em evidência de execução.
- Usar comentários apenas para invariantes ou decisões que não sejam óbvias no
  código.

## Invariantes do domínio

- A fila do kernel usa `(delivery, seq, message)`; `seq` deve ser único e
  preservar a ordem quando entregas têm o mesmo tempo.
- Toda ordem resting deve aparecer exatamente uma vez no heap correspondente e
  no `_order_map` da exchange.
- Ordens resting devem ter quantidade positiva; o livro não pode permanecer
  cruzado ou locked depois de uma mutação concluída.
- Cancelamento só pode remover ordens pertencentes ao agente solicitante.
- Um fill deve atualizar posição, caixa, VWAP, PnL e ordens ativas de forma
  reconciliável com o trade registrado.
- A seed deve controlar a aleatoriedade do experimento; timestamps de parede não
  podem ser usados como evidência de reprodução.

## Comandos de referência

```bash
uv sync
uv run python -m unittest discover -s tests -v
uv run python -m compileall -q app tests
uv run python -m app.core.runner
```

## Limites e aprovações

- Não ler, adicionar ou persistir credenciais para executar o simulador.
- Branches, merge, rebase, commit, push, pull request e publicação exigem
  autorização separada; a aprovação de uma fase não autoriza essas operações.
- Integração com serviços externos, infraestrutura, deploy ou dados reais exige
  autorização separada e um plano de recuperação específico.
- O branch `main` é a fonte de trabalho atual. Worktrees em `.claude/` são
  estados separados e não são evidência de que uma mudança esteja integrada.
- Agentes, dependências ou arquivos históricos não devem ser removidos apenas
  por parecerem obsoletos; registrar a decisão na fase apropriada primeiro.
