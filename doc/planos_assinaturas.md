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
- `permite_upgrade_pix` (bool)

Importante no contexto atual:
- limites globais de `Plano` nao sao suficientes para o V2 por app;
- no V2, a regra efetiva por modulo fica em `PlanoPermissaoApp`;
- no seed padrao, o plano Free ainda fornece limite base do app `simulado-digital`.
- elegibilidade para CTA/checkout PIX no bloqueio e controlada por `permite_upgrade_pix`:
  - `True`: exibe CTA e permite checkout PIX;
  - `False`: nao exibe CTA e bloqueia checkout PIX para o plano.

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

1. Usuario de plano elegivel ao PIX (`permite_upgrade_pix=True`) atinge limite ou acessa app sem permissao.
2. Sistema renderiza `menu/access_blocked.html` com contexto comercial.
3. CTA principal `Pagar com PIX e liberar agora` faz POST direto para `payments:upgrade_free`.
4. Checkout gera QRCode PIX.
5. Em `billing.paid` (webhook ou check manual), assinatura migra para `Aprova DETRAN`.

Notas:
- CTA de upgrade aparece apenas para planos com `permite_upgrade_pix=True`.
- Checkout mostra `Uso ilimitado` quando plano de destino nao possui limite.

Cenarios praticos (representante):
1. Convite do representante sem creditos:
- se `permitir_fallback_free=True`, o acesso por `/registrar/parceiro/<token>/` redireciona para `/registrar/`;
- se `permitir_fallback_free=False`, exibe tela de indisponibilidade de cadastro.

2. Aluno do representante atingiu o limite de uso de um app:
- o bloqueio ocorre por regra de `PlanoPermissaoApp` + `UsoAppJanela`;
- no estado atual, CTA de pagamento PIX direto na tela de bloqueio depende de `Plano.permite_upgrade_pix=True`.

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

1. Aplicar migrations (incluindo `banco_questoes.0005_ofertaupgradeusuario`, `0006_convitecadastroplano`, `0007_convitecadastroplano_permitir_fallback_free`, `0008_convitecadastroplano_logo_url_and_more` e `0009_plano_permite_upgrade_pix`).
2. Rodar `seed_apps_menu_access`.
3. Validar no admin:
  - 8 `AppModulo`;
  - regras Free e Aprova DETRAN em `PlanoPermissaoApp`;
  - campo `em_construcao` coerente com os apps liberados.
4. Validar flags de ambiente conforme rollout.
5. No admin de `Plano`, marcar `permite_upgrade_pix=True` para os planos autorizados ao upgrade via PIX.
6. Smoke test:
  - usuario Free;
  - usuario Aprova DETRAN;
  - usuario de plano nao-Free com `permite_upgrade_pix=True`;
  - usuario de plano com `permite_upgrade_pix=False`;
  - menu + simulado + perguntas-respostas + bloqueio comercial + checkout PIX.
  - cadastro parceiro com convite valido e convite indisponivel (com e sem fallback).
  - login parceiro com logo personalizada.

---

## 13) Telemetria de conversao (Meta Pixel + CAPI)

Objetivo:
- acompanhar funil de cadastro, bloqueio, checkout e compra com maior confiabilidade.

Configuracao por ambiente (`.env`):
1. `META_PIXEL_ENABLED`
2. `META_PIXEL_ID`
3. `META_CAPI_ENABLED`
4. `META_CAPI_ACCESS_TOKEN`
5. `META_CAPI_API_VERSION`
6. `META_CAPI_TEST_EVENT_CODE` (somente homologacao)

Eventos mapeados:
1. `PageView`
- Pixel: snippet frontend.
- CAPI: middleware server-side por namespace de app.

2. `CompleteRegistration`
- cadastro concluido em `registrar` e `registrar_parceiro`.

3. `Lead`
- exibicao da tela de bloqueio (`menu/access_blocked.html`).

4. `InitiateCheckout`
- QR PIX gerado (criacao de `Billing` pendente).

5. `Purchase`
- confirmacao no webhook `billing.paid` (transicao real para pago).

Deduplicacao:
1. Quando o evento existe em Pixel e CAPI, o mesmo `event_id` e usado nos dois canais.
2. Exemplo de chaves: `pv-*`, `reg-*`, `blk-*`, `chk-*`, `pur-*`.

Validacao recomendada no Events Manager:
1. Testar login/cadastro e confirmar `PageView` + `CompleteRegistration`.
2. Forcar bloqueio e confirmar `Lead`.
3. Gerar QR e confirmar `InitiateCheckout`.
4. Confirmar webhook pago e validar `Purchase`.
