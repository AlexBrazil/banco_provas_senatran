# Planos e assinaturas (guia rapido)

Este arquivo explica como preencher os campos de um Plano e como criar uma Assinatura para um usuario.

## 1) Campos do Plano
- `nome`: identificador do plano (ex.: Free, Mensal 30, Anual Ilimitado).
- `limite_qtd`: quantidade maxima de simulados no periodo. Vazio = ilimitado.
- `limite_periodo`: janela de limite quando `limite_qtd` esta preenchido.
  Valores: `DIARIO`, `SEMANAL`, `MENSAL`, `ANUAL`.
- `validade_dias`: quando a assinatura expira. Vazio = vitalicio.
- `ciclo_cobranca`: `MENSAL`, `ANUAL` ou `NAO_RECORRENTE`.
- `preco`: valor do plano.
- `ativo`: se o plano esta disponivel.

Regras importantes:
- Se `limite_qtd` estiver vazio, o plano e ilimitado e `limite_periodo` pode ficar vazio.
- Se `limite_qtd` estiver preenchido e `limite_periodo` estiver vazio, o sistema bloqueia
  com "Plano sem periodo de limite configurado".

Exemplos:
- Free (3 por dia): `limite_qtd=3`, `limite_periodo=DIARIO`, `validade_dias` vazio,
  `ciclo_cobranca=NAO_RECORRENTE`, `preco=0`, `ativo`.
- Anual ilimitado: `limite_qtd` vazio, `limite_periodo` vazio, `validade_dias=365`,
  `ciclo_cobranca=ANUAL`, `preco=199.90`, `ativo`.

## 2) Campos da Assinatura
- `usuario`: dono da assinatura.
- `plano`: referencia do plano atual.
- `nome_plano_snapshot`: copia do nome no momento da compra.
- `limite_qtd_snapshot`: copia do limite do plano no momento da compra.
- `limite_periodo_snapshot`: copia do periodo do plano no momento da compra.
- `validade_dias_snapshot`: copia da validade do plano no momento da compra.
- `ciclo_cobranca_snapshot`: copia do ciclo do plano no momento da compra.
- `preco_snapshot`: copia do preco do plano no momento da compra.
- `status`: `ATIVO`, `EXPIRADO`, `PAUSADO`.
- `inicio`: data de inicio da assinatura (usada para a janela de limite).
- `valid_until`: data de expiracao (pode ser vazio se vitalicio).

Regras importantes:
- A janela de limite e "periodo corrido", contando a partir de `inicio`.
- Na renovacao, **apenas** `preco_snapshot` deve ser atualizado (limites permanecem).

## 3) Como criar uma assinatura manualmente (admin)
1) Garanta que o Plano desejado existe e esta `ativo`.
2) Crie a Assinatura para o usuario:
   - Preencha o campo `plano`.
   - Copie os valores do plano para os campos `_snapshot`.
   - Defina `inicio` (agora) e `valid_until` conforme a validade.
   - Ajuste `status` para `ATIVO`.

Observacao:
- Ao criar uma Assinatura no admin com um plano selecionado, os campos `_snapshot`
  sao preenchidos automaticamente com os dados do plano.
- Ao criar a Assinatura, `inicio` e `valid_until` sao preenchidos automaticamente.
- Ao editar a Assinatura, `inicio` passa a ser obrigatorio e `valid_until` e
  recalculado **apenas** quando o plano possui `validade_dias`.
