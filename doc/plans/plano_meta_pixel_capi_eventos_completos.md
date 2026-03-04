# Plano de implementacao - Meta Pixel + CAPI (eventos completos)

Data: 2026-03-04  
Status: implementado no codigo e em homologacao

## 1) Objetivo

Implementar rastreamento de marketing com **Meta Pixel (frontend)** + **Meta Conversions API (backend)** para os eventos:

1. `PageView` (todas as paginas elegiveis)
2. `CompleteRegistration` (cadastro concluido)
3. `Lead` ou `ViewContent` (tela de bloqueio)
4. `InitiateCheckout` (QRCode PIX gerado)
5. `Purchase` (confirmacao `billing.paid` no webhook)

## 2) Decisoes deste plano

1. Canal de eventos: hibrido (Pixel + CAPI).
2. `Purchase` sera enviado pelo codigo do projeto apos confirmacao do webhook.
3. Consentimento LGPD: fora de escopo neste ciclo por decisao de produto (risco assumido).
4. URL de parceiro com token: sem mascaramento neste ciclo por decisao de produto.
5. Cobertura de navegacao (`PageView`) inclui todos os apps do `menu/catalog.py`.
6. Configuracao por ambiente obrigatoria: `Pixel ID` vem do `.env` via `settings.py` e e injetado no template.

## 3) Escopo

Incluido:

1. Snippet base do Pixel.
2. Biblioteca JS de disparo de eventos Pixel.
3. Cliente CAPI no backend.
4. Disparo dos 5 eventos nos pontos corretos.
5. Idempotencia e deduplicacao por `event_id` quando houver evento em ambos os canais.
6. Logs de observabilidade.

Fora de escopo:

1. Banner de consentimento.
2. Gestor de preferencias de cookies.
3. Data warehouse/BI externo.
4. Regras avancadas de atribuicao multitoque.

## 4) Variaveis de ambiente

Adicionar no `.env`:

1. `META_PIXEL_ENABLED=1`
2. `META_PIXEL_ID=...`
3. `META_CAPI_ENABLED=1`
4. `META_CAPI_ACCESS_TOKEN=...`
5. `META_CAPI_API_VERSION=v20.0` (ou versao vigente adotada pelo projeto)
6. `META_CAPI_TEST_EVENT_CODE=` (opcional para homologacao)

Regras operacionais por ambiente:

1. `dev`: manter `META_PIXEL_ENABLED=0` por padrao (ou usar `META_CAPI_TEST_EVENT_CODE` para testes pontuais).
2. `staging`: usar Pixel de teste e `META_CAPI_TEST_EVENT_CODE` ativo.
3. `prod`: usar Pixel oficial de producao.

## 5) Arquitetura proposta

### 5.1 Frontend (Pixel)

1. Incluir snippet base do Pixel em template comum, lendo `META_PIXEL_ID` injetado pelo backend.
2. Criar helper JS para:
   - `window.trackMeta(eventName, params, eventId)`
   - encapsular chamada `fbq('track', ...)`
   - evitar erro quando Pixel estiver desativado.
3. Renderizar snippet somente quando:
   - `META_PIXEL_ENABLED=True`
   - `META_PIXEL_ID` nao vazio.

### 5.2 Backend (CAPI)

Criar modulo dedicado (sugestao):

1. `payments/meta_capi.py` (ou modulo compartilhado `banco_questoes/meta_capi.py`)
2. Funcao principal:
   - `send_meta_event(event_name, *, event_id, user_data, custom_data, event_source_url, action_source='website')`
3. Envio para endpoint Graph:
   - `https://graph.facebook.com/{META_CAPI_API_VERSION}/{META_PIXEL_ID}/events`
4. Timeout curto e falha nao bloqueante (logar erro e seguir fluxo principal).

### 5.3 Deduplicacao por `event_id`

Regra:

1. Quando o mesmo evento for enviado por Pixel e CAPI, usar **o mesmo** `event_id`.
2. Para eventos puramente server-side, manter `event_id` unico por ocorrencia para idempotencia interna.

Chaves recomendadas por evento:

1. `PageView`: `pv-{request_id_or_uuid}`.
2. `CompleteRegistration`: `reg-{user_id}`.
3. `Lead/ViewContent` bloqueio: `blk-{user_id}-{app_slug}-{timestamp_bucket}`.
4. `InitiateCheckout`: `chk-{billing_ref}`.
5. `Purchase`: `pur-{billing_ref}`.

## 6) Mapa de eventos (ponto a ponto)

## 6.1 `PageView`

Pixel:

1. Disparo automatico em paginas elegiveis via snippet global.

CAPI:

1. Opcao A (recomendada): middleware com whitelist de paths.
2. Opcao B: disparo por view nas rotas principais.

Paginas elegiveis iniciais (base):

1. `/login/`, `/registrar/`, `/`
2. `/simulado/`, `/simulado/config/`, `/simulado/iniciar/` (quando render)
3. `/payments/upgrade/free/`

Cobertura por apps do catalogo (`menu/catalog.py`):

1. `simulado-digital` -> namespace/rotas `simulado:*`
2. `perguntas-respostas` -> `perguntas_respostas:*`
3. `apostila-cnh` -> `apostila_cnh:*`
4. `simulacao-prova-detran` -> `simulacao_prova:*`
5. `manual-aulas-praticas` -> `manual_pratico:*`
6. `aprenda-jogando` -> `aprenda_jogando:*`
7. `oraculo` -> `oraculo:*`
8. `aprova-plus` -> `aprova_plus:*`

Diretriz de implementacao:

1. Para `PageView`, preferir filtro por `resolver_match.namespace`/nome de rota, nao por string fixa de path.
2. Atualizar a whitelist de `PageView` sempre que houver novo app no `menu/catalog.py`.
3. Apps "Em construcao" tambem podem enviar `PageView` para medir interesse de uso.

## 6.2 `CompleteRegistration`

Pontos backend:

1. `banco_questoes/views_auth.py` em `registrar` (apos `form.save()` + assinatura).
2. `banco_questoes/views_auth.py` em `registrar_parceiro` (apos sucesso do cadastro).

Pixel:

1. Disparo no response de sucesso (template ou redirect landing com flag de evento).

CAPI:

1. Disparo no backend no mesmo momento do sucesso.

## 6.3 `Lead` ou `ViewContent` (bloqueio)

Pontos:

1. `banco_questoes/access_control.py` (render de `menu/access_blocked.html`).
2. `banco_questoes/views_simulado.py` (`_render_access_blocked`).

Regra de nomenclatura:

1. Usar `Lead` como padrao.
2. Opcional: manter `ViewContent` em paralelo somente na fase de teste A/B.

## 6.4 `InitiateCheckout` (QRCode PIX gerado)

Ponto:

1. `payments/views.py` em `upgrade_free`, no `POST`, apos `Billing.objects.create(...)`.

Dados minimos:

1. `value` (valor do plano)
2. `currency` (`BRL`)
3. `content_name` (nome do plano destino)
4. `event_id` com base em `billing_ref`.

## 6.5 `Purchase` (webhook `billing.paid`)

Ponto:

1. `payments/views.py` em `webhook_abacatepay`, apos `changed = _finalizar_billing_pago(...)`.
2. Enviar apenas quando `changed == True` (transicao real para pago).

Dados minimos:

1. `value` (billing valor)
2. `currency` (`BRL`)
3. `content_name` (plano destino)
4. `event_id = pur-{billing_ref}`

## 7) Dados de usuario (CAPI)

Campos recomendados quando disponiveis:

1. `em`: hash SHA-256 do email normalizado.
2. `external_id`: hash SHA-256 do `user.id`.
3. `client_ip_address`: IP do request (quando existir).
4. `client_user_agent`: User-Agent (quando existir).

Observacao:

1. Nunca enviar senha, token de autenticacao, token de convite, ou dados sensiveis nao necessarios.

## 8) Logging e observabilidade

Usar `EventoAuditoria` para rastrear:

1. `meta_pixel_event_dispatched` (quando aplicavel)
2. `meta_capi_event_sent`
3. `meta_capi_event_failed`
4. `meta_capi_purchase_sent`
5. `meta_capi_purchase_skipped_idempotent`

Contexto minimo:

1. `event_name`
2. `event_id`
3. `billing_ref` (quando houver)
4. `http_status` e `response_excerpt` em caso de falha

## 9) Fases de execucao

### Fase 1 - Base tecnica

1. Configurar variaveis de ambiente.
2. Criar cliente CAPI reutilizavel.
3. Criar helper JS de eventos Pixel.

Entregavel:

1. infraestrutura pronta para eventos.

### Fase 2 - Eventos de topo/funil medio

1. Implementar `PageView`.
2. Implementar `CompleteRegistration`.
3. Implementar `Lead` no bloqueio.

Entregavel:

1. funil ate bloqueio rastreado.

### Fase 3 - Checkout e compra

1. Implementar `InitiateCheckout` no QR gerado.
2. Implementar `Purchase` no webhook `billing.paid`.
3. Validar idempotencia de `Purchase` via transicao `PENDING -> PAID`.

Entregavel:

1. funil completo com conversao.

### Fase 4 - Homologacao e release

1. Validar eventos no Meta Test Events.
2. Conferir parametros e consistencia de valores.
3. Publicar em producao.

Entregavel:

1. rastreamento completo ativo.

## 10) Testes (checklist pratico)

1. Abrir pagina de login -> `PageView`.
2. Abrir ao menos 1 tela de cada app do `menu/catalog.py` -> `PageView`.
3. Cadastro concluido com sucesso -> `CompleteRegistration`.
4. Forcar bloqueio de app -> `Lead`/`ViewContent`.
5. Gerar QR PIX -> `InitiateCheckout`.
6. Confirmar pagamento via webhook -> `Purchase`.
7. Reenviar webhook de mesmo pagamento -> nao duplicar `Purchase` de negocio no sistema.
8. Validar valores:
   - `currency=BRL`
   - `value` correto em `InitiateCheckout`/`Purchase`.

## 11) Riscos e mitigacoes

1. Falha da API Meta interromper fluxo de negocio.
   - Mitigacao: envio nao bloqueante, com log.

2. Duplicidade de eventos.
   - Mitigacao: `event_id` padronizado + idempotencia no webhook.

3. Divergencia entre Pixel e CAPI.
   - Mitigacao: mapa unico de eventos e nomenclatura fixa.

4. Queda de sinal por adblock.
   - Mitigacao: manter CAPI para eventos criticos.

## 12) Criterios de aceite (DoD)

1. Todos os 5 eventos ativos em homologacao.
2. `Purchase` enviado pelo codigo no webhook apos confirmacao real (`billing.paid` processado).
3. Sem impacto no fluxo de checkout/ativacao mesmo se Meta indisponivel.
4. Logs de sucesso/falha disponiveis para suporte.
5. Documentacao operacional atualizada.

## 13) Documentos para atualizar ao final

1. `doc/description_project.md`
2. `doc/planos_assinaturas.md`
3. `doc/plans/status_execucao_menu_access.md`
4. (opcional) novo runbook: `doc/plans/meta_pixel_capi_operacao.md`
