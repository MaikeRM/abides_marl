# Goals

## Purpose

Evoluir o PoC ABIDES-MARL de um simulador visual executável para um laboratório
reproduzível de microestrutura e aprendizado por reforço, preservando a
correção do motor de eventos e tornando cada experimento auditável.

## Outcomes / Resultados desejados

- Um baseline de mercado determinístico no que diz respeito à seed, configuração,
  métricas e trace canônico.
- Contratos explícitos para mensagens, ordens, trades, contabilidade, reset,
  observações, ações, recompensas e término de episódios.
- Um ambiente Gymnasium single-agent testável contra agentes heurísticos.
- Uma decisão fundamentada sobre suporte multiagente e, se necessário, um
  ambiente PettingZoo ou equivalente com sincronização clara.
- Um pipeline de treinamento e avaliação que compare políticas aprendidas com o
  baseline heurístico em múltiplas seeds.
- Um núcleo mensurável, separável da GUI e preparado para otimização apenas
  quando os contratos experimentais estiverem estáveis.

## Success / Condição de sucesso

O projeto estará pronto para a próxima etapa quando uma pessoa em um clone
limpo puder:

1. instalar o ambiente com `uv sync`;
2. executar os testes e o baseline documentado;
3. reproduzir o mesmo resultado canônico para a mesma configuração e seed;
4. executar um episódio RL com `reset`/`step`/`close` e verificar os espaços,
   recompensas e sinais de término;
5. treinar e avaliar uma política com seeds e artefatos registrados;
6. comparar o resultado contra os agentes heurísticos sem depender da GUI.

Cada item precisa de um comando ou artefato de evidência no
`harness/build-log.md`; intenção documentada não conta como conclusão.

## Escopo

- Um ativo e um livro de ofertas contínuo na primeira versão experimental.
- Kernel discreto por eventos, exchange CDA e agentes heurísticos existentes.
- Execução local, testes automatizados, experimentos offline e documentação
  técnica.
- Primeiro um ambiente single-agent; suporte multiagente somente após decisão
  explícita baseada no caso de uso e na capacidade de avaliação.

## Non-goals / Fora de escopo

- Negociação real, conexão com corretoras, dados privados ou execução de ordens.
- Garantia de produção financeira, recomendação de investimento ou uso de
  capital real.
- HPC, GPU ou migração para JAX antes de haver benchmark que justifique a
  mudança.
- Reescrever o simulador inteiro para imitar a hierarquia interna do ABIDES.
- Adicionar novas famílias de agentes sem hipótese experimental, teste e
  métrica de avaliação.
- Fazer merge, rebase, commit, push, deploy ou publicar artefatos sem aprovação
  própria.

## Restrições técnicas e operacionais

- Python `3.12.11` é a versão declarada em `.python-version` e no manifesto.
- `uv` é o caminho de instalação e execução documentado.
- A auditoria atual ocorre no worktree de `main`, que contém mudanças locais
  ainda não demonstradas em um clone limpo. O branch está divergente de
  `origin/main` (`ahead 1, behind 2`); isso é um risco de entrega, não uma
  autorização para executar operações Git.
- O estado local v0.2.0 possui 15 testes, Ruff, coverage, checker Gymnasium,
  ambiente single-agent, treino/evaluation smoke, benchmark e configuração de
  CI. A configuração de CI não foi executada por um runner remoto nesta
  auditoria.
- Existe código em worktrees e branches remotos, inclusive a referência
  histórica `origin/claude/eager-leakey`; esses estados não são funcionalidade
  integrada até serem revisados, testados e incorporados ao estado canônico.
- Artefatos e traces devem ser validados contra o horizonte efetivamente
  executado. A auditoria encontrou uma divergência conhecida no manifesto
  produzido por `SimulationRunner.run_artifact(max_time=...)`, que pertence à
  Fase 05.

## Correção, confiabilidade e recuperação

- Validar invariantes do kernel, exchange e contabilidade em testes focados e em
  uma execução integrada.
- Separar dados canônicos de reprodução de timestamps de observabilidade em
  tempo de parede.
- Não registrar segredos, dados pessoais ou credenciais em logs, traces ou
  prompts.
- Manter artefatos de experimento versionáveis e pequenos; dados volumosos devem
  ter política explícita antes de serem persistidos.
- Usar Git como recuperação do código, sem presumir que merge ou push sejam
  permitidos.
- Toda falha de fase deve preservar a evidência, limitar a mudança à fase
  autorizada e parar no handoff definido.

## Decisões adotadas para este ciclo

Para executar o roadmap completo solicitado, foram adotadas decisões
conservadoras e reversíveis, sempre registradas com a evidência correspondente:

- `main` permanece como fonte de trabalho; nenhum merge, rebase, commit ou push
  foi feito. `origin/claude/eager-leakey` é referência de revisão, não fonte de
  código integrado.
- `InformedTrader` e `NoiseTrader` permanecem no repositório por
  compatibilidade histórica, mas não fazem parte do cenário padrão.
- O baseline usa capital inicial zero, short selling permitido e marcação pelo
  último preço negociado; isso preserva a dinâmica legada e não representa uma
  política de risco financeiro.
- O agente RL inicial é um executor single-agent com observação contínua de 8
  valores normalizados, `MultiDiscrete([5, 20, 10])` e reward incremental de
  PnL marcado a mercado. O limite de posição é 100 unidades.
- O primeiro pipeline de treino usa somente NumPy e Cross-Entropy Method em
  horizonte curto. A escolha evita instalar um stack pesado antes de haver
  benchmark; não autoriza promoção de política nem uso de capital.

## Decisões humanas ainda pendentes

- Qual estado Git será promovido a clone limpo reproduzível e como a divergência
  com `origin/main` será reconciliada; a Fase 05 prepara a decisão, mas não
  executa merge, commit ou push.
- Se o wrapper candidato deve ser formalmente reescrito em uma fase futura; ele
  continua fora da integração atual.
- Qual política econômica deve governar capital, margem, short selling,
  self-trade, taxas, marcação e liquidação terminal; a política atual é apenas
  uma decisão de laboratório.
- Se single-agent deixa de ser suficiente para o caso de uso e justifica
  PettingZoo/multiagente simultâneo.
- Seeds, horizonte, intervalos de confiança, baselines nulos e limiares
  estatísticos para um benchmark científico longo; o arquivo smoke usa três
  seeds apenas como gate de engenharia.
- Critério objetivo para justificar otimização em Python, vetorização ou JAX;
  o benchmark atual sustenta somente a decisão provisória de permanecer em
  Python.

## Estado de fechamento do objetivo

### Pronto no estado local auditado

- O motor headless, a exchange CDA, os agentes heurísticos, o runner e a
  contabilidade executam com testes de contrato mínimos.
- O baseline produz manifesto, métricas e trace canônico reproduzível para a
  mesma configuração e seed; a reprodução foi observada em duas execuções.
- O ambiente Gymnasium single-agent passa o checker em cenário reduzido e o
  pipeline NumPy/CEM cria checkpoint e evaluation smoke com três seeds.
- Há benchmark headless, cobertura local, Ruff, compilação e workflow de CI
  versionado.

### Ainda necessário para considerar o laboratório evoluído

- Reconciliar a entrega local v0.2.0, corrigir o horizonte do manifesto,
  eliminar contradições documentais e provar instalação/execução em clone limpo.
- Fechar contratos públicos e semântica econômica do core, incluindo rejeições,
  fills parciais, terminalidade, taxas, risco e reconciliação contábil.
- Tornar o wrapper RL independente de internals do runner e testar todas as
  ações, estados terminais, seeds, horizontes e falhas relevantes.
- Substituir a avaliação smoke por protocolo científico pareado, com cenários
  de treino/validação/teste, baselines, intervalos de confiança, tamanhos de
  efeito e gates fail-closed.
- Tomar uma decisão explícita sobre MARL/PettingZoo, escala, type checking e
  release; nenhuma dessas decisões deve ser inferida a partir de um smoke.
