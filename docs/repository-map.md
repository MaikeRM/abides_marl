# Mapa do Repositório

## Estrutura Atual

| Caminho | Papel |
| --- | --- |
| `app/` | código-fonte da simulação e dashboard |
| `app/agents/` | exchange e agentes de mercado |
| `app/core/` | kernel, oracle e runner |
| `app/models/` | dataclasses e contratos de mensagens/ordens/trades |
| `docs/` | documentação ativa do projeto |
| `docs/reference/` | material técnico de apoio ainda relevante |
| `docs/archive/` | histórico de evolução, backlog antigo e posts |
| `papers/` | papers e referências externas |

## Convenção de Organização

Para evitar que o repositório volte a ficar confuso:

- documentação ativa fica somente em `docs/`
- histórico fica somente em `docs/archive/`
- posts e narrativas não voltam para a raiz; ficam em `docs/archive/blog/`
- backlog histórico não volta para a raiz; fica em `docs/archive/backlog/`
- changelog de releases fica em `docs/archive/changelog/`

## Onde Registrar Cada Coisa

| Tipo de informação | Lugar correto |
| --- | --- |
| estado atual do projeto | `docs/current-state.md` |
| próximos passos e prioridades | `docs/next-steps.md` |
| mapa e convenções do repositório | `docs/repository-map.md` |
| comparação arquitetural com ABIDES | `docs/reference/abides-reference-vs-implementation.md` |
| histórico de release | `docs/archive/changelog/` |
| anotações e planos antigos | `docs/archive/backlog/` |
| posts de desenvolvimento | `docs/archive/blog/` |

## Regra Prática

Se um arquivo responde "como o projeto está hoje?" ou "o que vem agora?", ele deve estar em `docs/`.

Se o arquivo responde "como chegamos até aqui?" ele deve estar em `docs/archive/`.
