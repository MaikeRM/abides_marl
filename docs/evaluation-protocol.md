# Protocolo de avaliação científica

`configs/evaluation_protocol.json` implementa
`evaluation-protocol.v1`. A unidade é um episódio do papel
`execution_agent`, em um cenário fixo e uma seed fixa. Policy e cada
comparador recebem o mesmo conjunto de seeds e a mesma configuração de
episódio; os comparadores usam a mesma API Gym e a mesma contabilidade.

## Partições

- treino: `11, 22, 33`;
- validação: `101, 102, 103`;
- holdout: `201, 202, 203`;
- stress: `301, 302, 303`.

As partições são validadas como disjuntas. O checkpoint e a configuração são
identificados por SHA-256, e o artifact também registra versão do pacote e do
Python. Avaliação não treina, não retuna e recusa reutilizar um diretório de
saída não vazio.

Os comparadores são `HOLD`, `RANDOM` e adaptadores determinísticos para
`MarketMakerAgent`, `ValueAgent`, `ZeroIntelligenceAgent` e
`LiquidityTrader`. O nome do comparador não transforma o adaptador em uma
prova de equivalência da implementação heurística completa; a avaliação
legada da população permanece registrada separadamente.

## Estatística e gate

Para cada seed, o efeito é `policy - baseline`. O agregador calcula média,
desvio, bootstrap percentile CI determinístico e aplica Bonferroni entre os
comparadores. A decisão é:

- `pass`: limite mínimo configurado e o limite inferior do IC atinge esse
  limite em todos os comparadores;
- `rejected`: o limite superior fica abaixo do limite mínimo;
- `inconclusive`: amostra insuficiente, IC cruzando o limite ou limite mínimo
  ausente.

O arquivo versionado deixa `minimum_effect: null` de propósito: o plumbing
fica executável, mas nenhum smoke pode declarar vantagem econômica sem uma
decisão humana sobre o efeito mínimo. NaN, infinito, seed duplicada,
checkpoint incompatível ou pareamento incompleto falham fechado.

Quando o protocolo está habilitado, `paired.seeds` e o bloco `paired` são a
fonte autoritativa da comparação; `config_seeds` identifica as seeds do
artefato de treino/configuração legado mantido para compatibilidade.
