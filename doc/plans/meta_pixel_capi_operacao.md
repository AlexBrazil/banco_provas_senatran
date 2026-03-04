# Operacao - Meta Pixel + CAPI

Data: 2026-03-04

## 1) Objetivo

Guia pratico para:
1. configurar ambiente,
2. validar eventos no Meta Events Manager,
3. publicar com seguranca,
4. diagnosticar falhas mais comuns.

## 2) Variaveis de ambiente

No `.env` do servidor:

```env
META_PIXEL_ENABLED=1
META_PIXEL_ID=SEU_PIXEL_ID
META_CAPI_ENABLED=1
META_CAPI_ACCESS_TOKEN=SEU_TOKEN_CAPI
META_CAPI_API_VERSION=v20.0
META_CAPI_TEST_EVENT_CODE=SEU_CODIGO_TESTE
```

Notas:
1. `META_CAPI_TEST_EVENT_CODE` e apenas para homologacao.
2. Em producao estavel, deixar vazio.
3. Nunca commitar token CAPI em git.

## 3) O que esta implementado

Eventos ativos:
1. `PageView` (Pixel + CAPI)
2. `CompleteRegistration` (Pixel + CAPI)
3. `Lead` (Pixel + CAPI na tela de bloqueio)
4. `InitiateCheckout` (Pixel + CAPI na geracao do QR PIX)
5. `Purchase` (CAPI no webhook `billing.paid`)

## 4) Passo a passo de homologacao

1. Reiniciar aplicacao apos alterar `.env`.
2. Confirmar:
   - `.\.venv\Scripts\python.exe manage.py check`
3. Abrir Events Manager > Eventos de teste.
4. Executar funil:
   - abrir login (PageView),
   - concluir cadastro (CompleteRegistration),
   - forcar bloqueio de app (Lead),
   - gerar QR PIX (InitiateCheckout),
   - confirmar pagamento webhook (Purchase).
5. Validar se os eventos chegaram com status `Processado`.

## 5) Mapeamento esperado no BM (PT-BR)

1. `PageView` -> aparece como `PageView`.
2. `CompleteRegistration` -> aparece como `Concluir inscricao`.
3. `Lead` -> aparece como `Lead`.
4. `InitiateCheckout` -> aparece como `Iniciar finalizacao da compra`.
5. `Purchase` -> aparece como `Compra` (ou `Purchase`).

## 6) Checklist pre-deploy

1. `META_PIXEL_ID` correto.
2. `META_CAPI_ACCESS_TOKEN` valido e recente.
3. `META_CAPI_TEST_EVENT_CODE` preenchido para homologacao.
4. `manage.py check` sem erros.
5. Funil completo validado no Events Manager.

## 7) Checklist pos-deploy

1. Revalidar funil em producao.
2. Confirmar chegada de `Purchase` apos pagamento real.
3. Limpar `META_CAPI_TEST_EVENT_CODE` no `.env` de producao.
4. Monitorar logs de auditoria:
   - `meta_capi_event_sent`
   - `meta_capi_event_failed`
   - `meta_capi_purchase_sent`
   - `meta_capi_purchase_skipped_idempotent`

## 8) Troubleshooting rapido

1. Evento nao aparece no BM:
   - confirmar `META_CAPI_ENABLED=1`,
   - validar token CAPI,
   - conferir `META_CAPI_TEST_EVENT_CODE`,
   - reiniciar processo da aplicacao.

2. So aparece Browser, nao Server:
   - revisar variaveis CAPI no `.env`,
   - checar erros `meta_capi_event_failed` na auditoria.

3. So aparece Server, nao Browser:
   - confirmar `META_PIXEL_ENABLED=1`,
   - validar snippet no HTML (view source),
   - verificar bloqueio por extensao/adblock do navegador.

4. Duplicidade de compra:
   - confirmar que `Purchase` no webhook envia apenas quando `changed == True`.
   - checar `event_id` com prefixo `pur-` no evento.

## 9) Seguranca operacional

1. Rotacionar token CAPI periodicamente.
2. Evitar expor credenciais em docs e prints.
3. Em caso de exposicao de token, gerar novo imediatamente.

