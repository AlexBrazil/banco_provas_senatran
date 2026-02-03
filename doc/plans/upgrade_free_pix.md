# Plano de implementacao - upgrade Free via PIX (AbacatePay) v2

## Objetivo
Implementar uma regra de negocio em que usuarios do plano Free possam pagar via PIX para desbloquear o sistema e migrar para o plano "Free Upgrade", com valor configuravel no admin. Para usuarios de outros planos, manter a mensagem "Para alterar o plano, contate o administrador.". Registrar auditoria das mudancas de plano.

## Contexto e referencias
- Planos/assinaturas e snapshots: `banco_questoes/models.py` e `planos_assinaturas.md`.
- Mensagens de bloqueio e CTA atual: `banco_questoes/templates/simulado/erro.html`.
- Regras de assinatura ativa e limite: `banco_questoes/views_simulado.py`.
- Integracao AbacatePay: `doc/gateway_PIX.md` (pixQrCode e webhooks).
- App de pagamentos existente (vazio): `payments/`.

## Regra de negocio (alvo)
- Se o usuario estiver no plano Free e estiver bloqueado por limite/assinatura, exibir opcao de pagamento via PIX para comprar o plano "Free Upgrade" (configuravel no admin).
- A tela de compra deve mostrar os detalhes do plano comprado (nome, validade, limites e preco vigente no admin) a partir do "Free Upgrade".
- Para usuarios de outros planos, manter a mensagem "Para alterar o plano, contate o administrador pelo whatsapp (53)99121-4707.".
- A troca de plano deve ser registrada em auditoria (com dados do pagamento e do plano origem/destino).

## Etapas (sequenciais)

### Etapa 1) Confirmacoes e preparo de dados
- Verificar se os planos "Free" e "Free Upgrade" existem e estao ativos.
- Definir que o valor de cobranca e os detalhes exibidos vem de `Plano` do "Free Upgrade".
- Definir que a opcao de pagamento sera exibida apenas em `simulado/erro.html`.

Entregaveis:
- Checklist de configuracao do plano "Free Upgrade" (nome, validade, limites, preco, ativo).

### Etapa 2) Modelos de pagamento e auditoria
- Criar modelos em `payments/models.py`:
  - `Billing` (id local, usuario, plano_destino, valor_centavos, status, pix_id, pix_qrcode_base64, pix_br_code, payload_criacao, payload_webhook, criado_em, atualizado_em).
  - `WebhookEvent` (event_id, tipo, payload, recebido_em, processado_em, status_processamento).
- Manter `EventoAuditoria` para registrar a troca de plano (tipo ex.: `plano_trocado_pix`).
- Criar migrations e admin basico para visualizar cobrancas e eventos.

Entregaveis:
- Migrations aplicadas.
- Admin com listagem de `Billing` e `WebhookEvent`.

### Etapa 3) Cliente AbacatePay (service layer)
- Implementar client simples em `payments/abacatepay.py` (ou similar):
  - `create_pix_qrcode(...)` usando `POST /v1/pixQrCode/create`.
  - `check_pix_qrcode(...)` usando `GET /v1/pixQrCode/check`.
- Ler token e webhook secret do `.env` (ja existem) e manter em `settings.py`.
- Normalizar valores em centavos (ex.: R$ 9,90 -> 990), usando o preco configurado no plano "Free Upgrade".
- Enviar `metadata` como objeto com valores string (ex.: `billing_ref`, `user_id`, `plano_id`), para evitar erro de validacao.

Entregaveis:
- Funcoes de criacao e consulta de QRCode retornando `id`, `brCode` (copia e cola) e `brCodeBase64`.

### Etapa 4) Fluxo de compra (views/urls/templates)
- Criar endpoints em `payments/views.py`:
  - `GET /payments/upgrade/free/` (tela de compra com detalhes do plano).
  - `POST /payments/upgrade/free/` (cria QRCode PIX, salva `Billing` e exibe QRCode + copia e cola).
  - `POST /payments/upgrade/free/check/` (revalida status via `pixQrCode/check` quando o usuario clicar "Ja paguei").
  - `GET /payments/upgrade/free/status/` (status simples para polling no checkout).
- Bloquear o fluxo para usuarios que nao estao no plano Free.
- Exibir detalhes do plano na tela de compra (nome, validade, limites, preco) a partir do modelo `Plano` do "Free Upgrade".

Entregaveis:
- Template de checkout simples (ex.: `payments/checkout_free_pix.html`) com QRCode (imagem base64) e campo de copia e cola (`brCode`).
- Rotas adicionadas em `config/urls.py`.

Layout sugerido da tela de pagamento:
- Cabecalho com nome do plano "Free Upgrade" e preco.
- Bloco 1: QRCode (imagem) + instrucoes rapidas de pagamento.
- Bloco 2: campo de texto com o codigo "copia e cola" (`brCode`) e botao "Copiar".
- Bloco 3: status do pagamento (aguardando / pago) e botao "Ja paguei".
  - O botao "Ja paguei" deve aparecer apenas apos 60 segundos da criacao do QRCode e enquanto o status estiver PENDING.

Detalhe do "Ja paguei" (revalidacao manual):
- Ao clicar, chamar o endpoint `POST /payments/upgrade/free/check/` para consultar `pixQrCode/check` na AbacatePay usando o `pix_id` salvo no `Billing`.
- Se o status vier `PAID`, atualizar `Billing` e seguir o mesmo fluxo do webhook (ativar o plano e registrar auditoria).
- Se continuar `PENDING`, retornar mensagem "Pagamento ainda nao confirmado".
- Aplicar rate-limit simples (ex.: 1 tentativa a cada 30s por usuario/billing) e registrar tentativas em auditoria.

Detalhe do redirecionamento automatico:
- No checkout, fazer polling do endpoint `GET /payments/upgrade/free/status/`.
- Ao detectar `PAID`, redirecionar automaticamente para `simulado:inicio`.
- Se o polling expirar (timeout), exibir mensagem "Ainda nao confirmou, tente novamente".

### Etapa 5) Webhook e confirmacao de pagamento
- Criar endpoint `POST /payments/webhook/abacatepay/`:
  - Validar assinatura do webhook (conforme `doc/gateway_PIX.md`).
  - Registrar `WebhookEvent` com payload completo.
  - Processar eventos `billing.paid`.
  - Parsear payload real: `data.pixQrCode.id` (pix_id) e `data.pixQrCode.metadata` (com `billing_ref`, `user_id`, `plano_id` em string).
- Confirmar que o valor e o metadata batem com o plano esperado (anti-fraude basico).
- Marcar `Billing` como pago e idempotente (evitar reprocesso).

Entregaveis:
- Webhook funcional com idempotencia.

### Etapa 6) Troca de plano e auditoria
- Ao receber pagamento valido:
  - Criar nova `Assinatura` para o usuario com o plano "Free Upgrade" e snapshot atualizado.
  - Marcar assinatura Free anterior como `EXPIRADO` ou `PAUSADO`.
  - Registrar evento em `EventoAuditoria` com `contexto_json` contendo:
    - usuario_id, plano_origem, plano_destino, billing_id, valor, metodo=PIX, timestamp.
- Garantir que `valid_until` e `inicio` sejam definidos corretamente.

Entregaveis:
- Upgrade efetivo de plano via webhook.
- Evento de auditoria registrado.

### Etapa 7) Ajustes nas telas de bloqueio
- Atualizar `banco_questoes/views_simulado.py` para expor no contexto:
  - `plano_is_free` e/ou `plano_upgrade_url`.
- Atualizar templates:
  - Em `simulado/erro.html`, se `plano_is_free`: substituir a mensagem "contate o administrador" por CTA de pagamento.
  - Em `simulado/erro.html`, se nao for Free: manter a mensagem atual.
- Padronizar textos/labels de UI para mostrar "Free Upgrade" quando o CTA for exibido.

Entregaveis:
- UI condicional por plano.

### Etapa 8) Testes e validacao
- Testes unitarios: criacao de cobranca, webhook, revalidacao manual e upgrade de plano.
- Testes manuais:
  1) Usuario Free bloqueado -> CTA PIX aparece.
  2) Usuario de outro plano -> mensagem antiga.
  3) Pagamento confirmado -> assinatura "Free Upgrade" ativa.
  4) Botao "Ja paguei" aparece apos 1 min e revalida o status.
  5) Webhook repetido -> idempotente.

Entregaveis:
- Casos de teste documentados.

### Etapa 9) Deploy e monitoramento
- Atualizar `.env.example` com chaves de pagamentos (se necessario).
- Registrar URL do webhook no painel AbacatePay.
- Monitorar logs de `EventoAuditoria` e tabela `Billing`.

Entregaveis:
- Checklist de deploy.

## Riscos e cuidados
- Garantir que o preco cobrado esteja alinhado com o plano "Free Upgrade".
- Evitar upgrade sem confirmar evento de pagamento valido.
- Tratar idempotencia para webhooks repetidos.
- Futuro: se a AbacatePay passar a exigir dados de cliente (CPF/email/telefone), sera necessario capturar esses dados e criar `customer` ou usar modo Checkout.

## Melhorias opcionais
- Armazenar `expiresAt` e `amount` do QRCode para auditoria e controle de expiracao.
- Salvar o payload da revalidacao (`pixQrCode/check`) no `Billing` ou em `WebhookEvent` para rastreio.

## Observacao
Este planejamento assume QRCode local via `pixQrCode/create` e revalidacao via `pixQrCode/check`, com confirmacao final pelo webhook `billing.paid`.
