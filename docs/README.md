# Documentação do Projeto

Este diretório concentra o material que explica o estado atual do projeto e para onde ele está indo. A ideia é manter o caminho de leitura curto para qualquer pessoa que entrar no repositório.

## Leia Nesta Ordem

1. [`current-state.md`](current-state.md): fotografia fiel da implementação atual.
2. [`baseline-scenario.md`](baseline-scenario.md): cenário padrão reproduzível, comandos e métricas mínimas.
3. [`next-steps.md`](next-steps.md): backlog ativo e prioridades de evolução.
4. [`repository-map.md`](repository-map.md): convenções de organização do repositório.
5. [`reference/abides-reference-vs-implementation.md`](reference/abides-reference-vs-implementation.md): comparação da arquitetura com a referência ABIDES.
6. [`performance.md`](performance.md): benchmark, perfil e gates locais.
7. [`release.md`](release.md): escopo da release experimental `0.2.0`.
8. [`provenance.md`](provenance.md): distinção entre worktree, Git e clone limpo.

## Contratos experimentais

- [`economic-policy.md`](economic-policy.md): perfis, lifecycle e contabilidade.
- [`rl-contract.md`](rl-contract.md): episódio single-agent versionado.
- [`evaluation-protocol.md`](evaluation-protocol.md): pareamento, ICs e gates.
- [`marl-decision.md`](marl-decision.md): ADR do no-go condicionado para MARL.

## Planejamento de Engenharia

- [`../GOALS.md`](../GOALS.md): resultados desejados, escopo e decisões abertas.
- [`../PLANS.md`](../PLANS.md): roadmap, dependências e gates.
- [`../AGENTS.md`](../AGENTS.md): acordos duráveis do repositório.
- [`../harness/build-log.md`](../harness/build-log.md): evidências observadas de execução.

## Histórico

Todo material que ajuda a entender a evolução, mas não representa mais a visão principal do projeto, foi movido para [`archive/`](archive/):

- `archive/changelog/`: releases e mudanças por versão
- `archive/backlog/`: planos e listas históricas de melhorias
- `archive/blog/`: posts e narrativas de construção
- `archive/legacy-docs/`: documentos antigos que continuam úteis como contexto

## Regra de Atualização

Para manter clareza daqui para frente:

- atualize `current-state.md` quando a implementação real mudar
- atualize `next-steps.md` quando a prioridade do projeto mudar
- registre releases e marcos em `archive/changelog/`
- evite criar novas pastas de documentação na raiz do repositório
