# Planos e assinaturas (guia rapido atualizado)

Este guia descreve como funcionam `Plano`, `Assinatura`, controle por app (`AppModulo` / `PlanoPermissaoApp` / `UsoAppJanela`), oferta promocional 24h de upgrade (`OfertaUpgradeUsuario`) e onboarding por convite de representante (`ConviteCadastroPlano`).

---

## 1) Modelo atual de acesso

No estado atual do projeto, o acesso e controlado em duas camadas:

1. Assinatura ativa do usuario
- modelo `Assinatura`
- valida status e validade temporal (`valid_until`)

2. Regra por app do plano
- modelos `AppModulo` + `PlanoPermissaoApp`
- define se cada app esta liberado e qual limite por app se houver

Consumo:
- modelo `UsoAppJanela` registra uso por usuario + app + janela.

---

## 2) Campos do Plano

Modelo: `Plano`

- `nome`
- `limite_qtd`
- `limite_periodo` (`DIARIO`, `SEMANAL`, `MENSAL`, `ANUAL`)
- `validade_dias`
- `ciclo_cobranca` (`MENSAL`, `ANUAL`, `NAO_RECORRENTE`)
- `preco`
- `ativo`

Importante no contexto atual:
- limites globais de `Plano` nao sao suficientes para o V2 por app;
- no V2, a regra efetiva por modulo fica em `PlanoPermissaoApp`;
- no seed padrao, o plano Free ainda fornece limite base do app `simulado-digital`.

---

## 3) Campos da Assinatura

Modelo: `Assinatura`

Campos principais:
- `usuario`
- `plano`
- `status` (`ATIVO`, `EXPIRADO`, `PAUSADO`)
- `inicio`
- `valid_until`

Snapshots:
- `nome_plano_snapshot`
- `limite_qtd_snapshot`
- `limite_periodo_snapshot`
- `validade_dias_snapshot`
- `ciclo_cobranca_snapshot`
- `preco_snapshot`

Observacao importante:
- no V2 por app, limites de acesso devem vir de `PlanoPermissaoApp`, nao do snapshot global da assinatura;
- snapshots continuam uteis para trilha comercial/historica.

---

## 4) Regras por app (core do V2)

### 4.1 `AppModulo`
- catalogo persistido dos apps.
- slug canonico do simulado: `simulado-digital`.
- slug do estudo rapido: `perguntas-respostas`.

### 4.2 `PlanoPermissaoApp`
- chave unica: (`plano`, `app_modulo`).
- campos de regra:
  - `permitido` (bool)
  - `limite_qtd` (null = ilimitado)
  - `limite_periodo` (ou null)

### 4.3 `UsoAppJanela`
- contador por usuario/app/janela.
- usado para bloqueio quando `limite_qtd` esta definido.

---

## 5) Oferta promocional 24h (escassez)

Modelo: `OfertaUpgradeUsuario`

Objetivo:
- persistir janela promocional por usuario para evitar reinicio do cronometro a cada acesso.

Chave:
- (`usuario`, `campanha_slug`) unica.

Campos principais:
- `campanha_slug` (atual: `upgrade-free-24h`)
- `ciclo` (1 no primeiro periodo; incrementa apos expirar)
- `janela_inicio`
- `janela_fim`

Regra atual (camada `access_control.py`):
- duracao fixa de 24h por ciclo;
- desconto comercial exibido de `50% OFF`;
- preco "de" e calculado por ancoragem (`preco do plano * 2`);
- se o usuario voltar apos expirar 24h:
  - inicia novo ciclo de 24h;
  - exibe mensagem de nova oportunidade (`ciclo > 1`).

Importante:
- essa logica e de apresentacao/comercial da tela de bloqueio;
- o preco real cobrado segue `Plano.preco` no checkout PIX.

---

## 6) Simulado e legado

- Simulado usa regra V2 do app `simulado-digital`.
- `SimuladoUso` (legado) permanece apenas para dual-write opcional/observabilidade.
- dual-write legado depende de `APP_ACCESS_DUAL_WRITE=1`.

---

## 7) Cadastro por convite de representante

Modelo: `ConviteCadastroPlano`

Objetivo:
- direcionar novos cadastros para plano especifico sem alterar o cadastro padrao (`/registrar/`).

Rota:
- `/registrar/parceiro/<token>/`
- `/login/parceiro/<token>/`

Campos relevantes:
- `token` (opaco e unico)
- `plano` (plano de entrada do novo usuario)
- `nome_representante` (rotulo comercial da marca)
- `logo_url` (logo exibida nas telas de login/cadastro do parceiro)
- `ativo`
- `inicio_vigencia` / `fim_vigencia`
- `limite_usos` / `usos_realizados`
- `permitir_fallback_free` (bool)

Comportamento quando convite esta indisponivel (expirado, sem creditos, inativo):
- `permitir_fallback_free=True`: redireciona para `/registrar/`.
- `permitir_fallback_free=False`: exibe tela informativa de indisponibilidade de creditos.

Observacao:
- token inexistente/invalido continua redirecionando para `/registrar/`.
- login parceiro com token valido usa a identidade visual do convite (quando configurada).

---

## 8) Seed oficial de apps e permissoes

Comando:

```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
```

O que garante:
- 8 apps em `AppModulo`;
- permissoes Free e Aprova DETRAN em `PlanoPermissaoApp`;
- migracao de slug legado `simulado-provas` -> `simulado-digital`.

Importante para deploy:
- no seed atual, `perguntas-respostas` e atualizado com `em_construcao=False`;
- manter o valor coerente com o estado real de liberacao de cada app.

---

## 9) Configuracao recomendada de planos (padrao do projeto)

Free:
- permitido somente `simulado-digital`;
- limite vindo do plano Free (ex.: 3/DIARIO).

Aprova DETRAN:
- 8 apps permitidos;
- sem limite por app (`limite_qtd=null`, `limite_periodo=null`).

Observacao:
- permissao de plano e visibilidade no menu dependem tambem de `AppModulo.em_construcao`.

---

## 10) Fluxo comercial de bloqueio e upgrade

1. Usuario Free atinge limite ou acessa app sem permissao.
2. Sistema renderiza `menu/access_blocked.html` com contexto comercial.
3. CTA principal `Pagar com PIX e liberar agora` faz POST direto para `payments:upgrade_free`.
4. Checkout gera QRCode PIX.
5. Em `billing.paid` (webhook ou check manual), assinatura migra para `Aprova DETRAN`.

Notas:
- CTA de upgrade so aparece para plano Free.
- Checkout mostra `Uso ilimitado` quando plano de destino nao possui limite.

Cenarios praticos (representante):
1. Convite do representante sem creditos:
- se `permitir_fallback_free=True`, o acesso por `/registrar/parceiro/<token>/` redireciona para `/registrar/`;
- se `permitir_fallback_free=False`, exibe tela de indisponibilidade de cadastro.

2. Aluno do representante atingiu o limite de uso de um app:
- o bloqueio ocorre por regra de `PlanoPermissaoApp` + `UsoAppJanela`;
- no estado atual, CTA de pagamento PIX direto na tela de bloqueio permanece exclusivo para plano `Free`.

---

## 11) Criar/ajustar assinatura manualmente (admin)

Passos:
1. Confirmar que o `Plano` desejado existe e esta ativo.
2. Criar/editar `Assinatura` do usuario com `status=ATIVO`.
3. Garantir `inicio` e `valid_until` coerentes com a regra comercial.
4. Confirmar que o plano da assinatura possui regras em `PlanoPermissaoApp`.

Sem regra em `PlanoPermissaoApp`:
- o app correspondente pode bloquear (comportamento esperado de seguranca).

---

## 12) Checklist de deploy (acesso por app + oferta + convite)

1. Aplicar migrations (incluindo `banco_questoes.0005_ofertaupgradeusuario`, `0006_convitecadastroplano`, `0007_convitecadastroplano_permitir_fallback_free` e `0008_convitecadastroplano_logo_url_and_more`).
2. Rodar `seed_apps_menu_access`.
3. Validar no admin:
  - 8 `AppModulo`;
  - regras Free e Aprova DETRAN em `PlanoPermissaoApp`;
  - campo `em_construcao` coerente com os apps liberados.
4. Validar flags de ambiente conforme rollout.
5. Smoke test:
  - usuario Free;
  - usuario Aprova DETRAN;
  - menu + simulado + perguntas-respostas + bloqueio comercial + checkout PIX.
  - cadastro parceiro com convite valido e convite indisponivel (com e sem fallback).
  - login parceiro com logo personalizada.
