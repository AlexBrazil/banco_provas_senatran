# AbacatePay - Guia de IntegraÃ§Ã£o para Modelos de Linguagem (Atualizado e Sincronizado)

## VisÃ£o Geral

A AbacatePay Ã© um gateway de pagamento que permite a criaÃ§Ã£o e gestÃ£o de cobranÃ§as de forma eficiente.
Atualmente, aceita pagamentos via **PIX** e **CartÃ£o**.
Outros mÃ©todos (boleto, crypto, etc.) poderÃ£o ser implementados futuramente.

## AutenticaÃ§Ã£o

- **MÃ©todo:** Bearer Token
- **Detalhes:** Todas as requisiÃ§Ãµes Ã  API devem incluir um token JWT no cabeÃ§alho de autorizaÃ§Ã£o.
- **Exemplo de CabeÃ§alho:**
  Authorization: Bearer {SEU_TOKEN_AQUI}
- **DocumentaÃ§Ã£o:** [Authentication](https://docs.abacatepay.com/pages/authentication)

## Modo Desenvolvedor (Dev Mode)

- **DescriÃ§Ã£o:** Ambiente para testes e desenvolvimento. Todas as operaÃ§Ãµes realizadas neste modo sÃ£o simuladas e nÃ£o afetam o ambiente de produÃ§Ã£o.
- **DocumentaÃ§Ã£o:** [Dev Mode](https://docs.abacatepay.com/pages/devmode)

---

## Endpoints Principais

### Clientes

#### âž¤ Criar Cliente

- **Endpoint:** `POST /v1/customer/create`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url https://api.abacatepay.com/v1/customer/create \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "name": "Fulano de tal",
    "cellphone": "(00) 0000-0000",
    "email": "cliente@gmail.com",
    "taxId": "123.456.789-01"
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro do Body:**

- **name** (string, obrigatÃ³rio): Nome completo do cliente. Exemplo: "Fulano de tal".
- **cellphone** (string, obrigatÃ³rio): Telefone celular do cliente. Exemplo: "(00) 0000-0000".
- **email** (string, obrigatÃ³rio): EndereÃ§o de e-mail do cliente. Exemplo: "cliente@gmail.com".
- **taxId** (string, obrigatÃ³rio): CPF ou CNPJ vÃ¡lido do cliente. Exemplo: "123.456.789-01".
- **Observacao:** CPF (taxId) agora Ã© Ãºnico; nÃ£o sÃ£o permitidos clientes com CPF duplicado.
- **Observacao:** se vocÃª nÃ£o tiver CPF/nome/email/telefone, prefira criar uma cobranÃ§a em modo Checkout para o cliente se cadastrar.

**Observacao:** para evitar erros de validacao, envie `metadata` como objeto com valores string (ex.: `"user_id": "123"`).

**Modelo de resposta:**

```json
{
  "data": {
    "id": "cust_abcdef123456",
    "metadata": {
      "name": "Fulano de tal",
      "cellphone": "(00) 0000-0000",
      "email": "cliente@gmail.com",
      "taxId": "123.456.789-01"
    }
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Criar Cliente](https://docs.abacatepay.com/pages/client/create)

---

#### âž¤ Listar Clientes

- **Endpoint:** `GET /v1/customer/list`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url https://api.abacatepay.com/v1/customer/list \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

_Esta rota nÃ£o necessita de body. Os parÃ¢metros de autenticaÃ§Ã£o via cabeÃ§alho sÃ£o obrigatÃ³rios._

**Modelo de resposta:**

```json
{
  "data": [
    {
      "id": "cust_abcdef123456",
      "metadata": {
        "name": "Fulano de tal",
        "cellphone": "(00) 0000-0000",
        "email": "cliente@gmail.com",
        "taxId": "123.456.789-01"
      }
    }
  ],
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Listar Clientes](https://docs.abacatepay.com/pages/client/list)

---

### Cupons de Desconto

#### âž¤ Criar Cupom

- **Endpoint:** `POST /v1/coupon/create`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url https://api.abacatepay.com/v1/coupon/create \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "data": {
      "code": "DEYVIN_20",
      "notes": "Cupom de desconto para meu pÃºblico",
      "maxRedeems": 10,
      "discountKind": "PERCENTAGE",
      "discount": 20,
      "metadata": {}
    }
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro do Body (dentro do objeto "data"):**

- **code** (string, obrigatÃ³rio): Identificador Ãºnico do cupom. Exemplo: "DEYVIN_20".
- **notes** (string): DescriÃ§Ã£o ou observaÃ§Ã£o sobre o cupom. Exemplo: "Cupom de desconto para meu pÃºblico".
- **maxRedeems** (number, obrigatÃ³rio): NÃºmero mÃ¡ximo de vezes que o cupom pode ser resgatado. Exemplo: 10. Use `-1` para ilimitado.
- **discountKind** (string, obrigatÃ³rio): Tipo de desconto, podendo ser "PERCENTAGE" ou "FIXED".
- **discount** (number, obrigatÃ³rio): Valor de desconto a ser aplicado. Exemplo: 20.
- **metadata** (object, opcional): Objeto para incluir metadados adicionais do cupom.

**Modelo de resposta:**

```json
{
  "data": {
    "id": "DEYVIN_20",
    "notes": "Cupom de desconto para meu pÃºblico",
    "maxRedeems": 10,
    "redeemsCount": 0,
    "discountKind": "PERCENTAGE",
    "discount": 20,
    "devMode": true,
    "status": "ACTIVE",
    "createdAt": "2025-05-25T23:43:25.250Z",
    "updatedAt": "2025-05-25T23:43:25.250Z",
    "metadata": {}
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** https://docs.abacatepay.com/api-reference/criar-um-novo-cupom

---

#### âž¤ Listar Cupons

- **Endpoint:** `GET /v1/coupon/list`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url https://api.abacatepay.com/v1/coupon/list \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

_Esta rota nÃ£o necessita de parÃ¢metros no body._

**Modelo de resposta:**

```json
{
  "data": [
    {
      "id": "DEYVIN_20",
      "notes": "Cupom de desconto para meu pÃºblico",
      "maxRedeems": -1,
      "redeemsCount": 0,
      "discountKind": "PERCENTAGE",
      "discount": 20,
      "devMode": true,
      "status": "ACTIVE",
      "createdAt": "2025-05-25T23:43:25.250Z",
      "updatedAt": "2025-05-25T23:43:25.250Z",
      "metadata": {}
    }
  ],
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Listar Cupons](https://docs.abacatepay.com/pages/payment/list)

---

### CobranÃ§as

#### âž¤ Criar CobranÃ§a

- **Endpoint:** `POST /v1/billing/create`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url https://api.abacatepay.com/v1/billing/create \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "frequency": "ONE_TIME",
    "methods": ["PIX","CARD"],
    "products": [
      {
        "externalId": "prod-1234",
        "name": "Assinatura de Programa Fitness",
        "description": "Acesso ao programa fitness premium por 1 mÃªs.",
        "quantity": 2,
        "price": 2000
      }
    ],
    "returnUrl": "https://example.com/billing",
    "completionUrl": "https://example.com/completion",
    "customerId": "cust_abcdefghij"
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro do Body:**

- **frequency** (string, obrigatÃ³rio): Define o tipo de frequÃªncia da cobranÃ§a. Valores possÃ­veis: `"ONE_TIME"` ou `"MULTIPLE_PAYMENTS"`.
- **methods** (array de string, obrigatÃ³rio): Lista com os mÃ©todos de pagamento aceitos. Agora aceita `"PIX"` e `"CARD"`.
- **products** (array de objeto, obrigatÃ³rio): Lista de produtos incluso na cobranÃ§a.
  - **externalId** (string, obrigatÃ³rio): Identificador Ãºnico do produto no seu sistema.
  - **name** (string, obrigatÃ³rio): Nome do produto.
  - **description** (string): DescriÃ§Ã£o do produto.
  - **quantity** (integer, obrigatÃ³rio, â‰¥1): Quantidade do produto.
  - **price** (integer, obrigatÃ³rio, mÃ­nimo 100): PreÃ§o unitÃ¡rio em centavos.
- **returnUrl** (string, obrigatÃ³rio - URI): URL para redirecionamento caso o cliente escolha a opÃ§Ã£o "Voltar".
- **completionUrl** (string, obrigatÃ³rio - URI): URL para redirecionamento apÃ³s a conclusÃ£o do pagamento.
- **customerId** (string, opcional): ID de um cliente jÃ¡ cadastrado.
- **customer** (object, opcional): Objeto contendo os dados do cliente para criaÃ§Ã£o imediata.

**Modelo de resposta:**

```json
{
  "data": {
    "id": "bill_123456",
    "url": "https://pay.abacatepay.com/bill-5678",
    "amount": 4000,
    "status": "PENDING",
    "devMode": true,
    "methods": ["PIX","CARD"],
    "products": [
      {
        "id": "prod_123456",
        "externalId": "prod-1234",
        "quantity": 2
      }
    ],
    "frequency": "ONE_TIME",
    "nextBilling": null,
    "customer": {
      "id": "cust_abcdef123456",
      "metadata": {
        "name": "Fulano de tal",
        "cellphone": "(00) 0000-0000",
        "email": "cliente@gmail.com",
        "taxId": "123.456.789-01"
      }
    },
    "createdAt": "2025-03-24T21:50:20.772Z",
    "updatedAt": "2025-03-24T21:50:20.772Z"
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Criar CobranÃ§a](https://docs.abacatepay.com/pages/payment/create)

---

#### âž¤ Buscar CobranÃ§a

- **Endpoint:** `GET /v1/billing/get?id=bill_123456`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url 'https://api.abacatepay.com/v1/billing/get?id=bill_123456' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

**Modelo de resposta:** Igual ao modelo da criaÃ§Ã£o de cobranÃ§a, retornando os detalhes de uma cobranÃ§a especÃ­fica.

---

#### âž¤ Listar CobranÃ§as

- **Endpoint:** `GET /v1/billing/list`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url https://api.abacatepay.com/v1/billing/list \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

**Modelo de resposta:**

```json
{
  "data": [
    {
      "id": "bill_123456",
      "url": "https://pay.abacatepay.com/bill-5678",
      "amount": 4000,
      "status": "PENDING",
      "devMode": true,
      "methods": ["PIX","CARD"],
      "products": [
        {
          "id": "prod_123456",
          "externalId": "prod-1234",
          "quantity": 2
        }
      ],
      "frequency": "ONE_TIME",
      "nextBilling": null,
      "customer": {
        "id": "cust_abcdef123456",
        "metadata": {
          "name": "Fulano de tal",
          "cellphone": "(00) 0000-0000",
          "email": "cliente@gmail.com",
          "taxId": "123.456.789-01"
        }
      }
    }
  ],
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Listar CobranÃ§as](https://docs.abacatepay.com/pages/payment/list)

---

### PIX QRCode

#### âž¤ Criar QRCode PIX

- **Endpoint:** `POST /v1/pixQrCode/create`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url https://api.abacatepay.com/v1/pixQrCode/create \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "amount": 100,
    "expiresIn": 3600,
    "description": "Pagamento de serviÃ§o",
    "customer": {
      "name": "Fulano de tal",
      "cellphone": "(00) 0000-0000",
      "email": "cliente@gmail.com",
      "taxId": "123.456.789-01"
    },
    "metadata": {
      "user_id": "123",
      "plano_id": "45",
      "billing_ref": "abcd1234"
    }
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro do Body:**

- **amount** (number, obrigatÃ³rio): Valor da cobranÃ§a em centavos. Exemplo: 100 (R$1,00).
- **expiresIn** (number, opcional): Tempo de expiraÃ§Ã£o da cobranÃ§a em segundos. Exemplo: 3600 (1 hora).
- **description** (string, opcional, mÃ¡ximo 140 caracteres): Mensagem que serÃ¡ exibida durante o pagamento do PIX. Exemplo: "Pagamento de serviÃ§o".
- **customer** (object, opcional): Objeto contendo os dados do cliente para criaÃ§Ã£o, caso este ainda nÃ£o esteja cadastrado.
  - **name** (string, obrigatÃ³rio caso customer seja passado): Nome do cliente.
  - **cellphone** (string, obrigatÃ³rio caso customer seja passado): Telefone do cliente.
  - **email** (string, obrigatÃ³rio caso customer seja passado): E-mail do cliente.
  - **taxId** (string, obrigatÃ³rio caso customer seja passado): CPF ou CNPJ do cliente.
- **metadata** (object, opcional): Objeto contendo os dados de um metadata customizÃ¡vel por parte de quem estÃ¡ integrando.

**Modelo de resposta:**

```json
{
  "data": {
    "id": "pix_char_123456",
    "amount": 100,
    "status": "PENDING",
    "devMode": true,
    "brCode": "00020101021226950014br.gov.bcb.pix",
    "brCodeBase64": "data:image/png;base64,iVBORw0KGgoAAA",
    "platformFee": 80,
    "createdAt": "2025-03-24T21:50:20.772Z",
    "updatedAt": "2025-03-24T21:50:20.772Z",
    "expiresAt": "2025-03-25T21:50:20.772Z",
    "metadata": {
      "teste": "Valor do teste de metadata"
    }
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Criar QRCode PIX](https://docs.abacatepay.com/pages/pix)

---

#### âž¤ Checar Status do QRCode PIX

- **Endpoint:** `GET /v1/pixQrCode/check`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url 'https://api.abacatepay.com/v1/pixQrCode/check?id=pix_char_123456' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

_Esta rota utiliza um parÃ¢metro na query:_

- **id** (string, obrigatÃ³rio): ID do QRCode PIX. Exemplo: "pix_char_123456".

**Modelo de resposta:**

```json
{
  "data": {
    "status": "PENDING",
    "expiresAt": "2025-03-25T21:50:20.772Z"
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Checar Status](https://docs.abacatepay.com/pages/pix)

---

#### âž¤ Simular Pagamento do QRCode PIX (Somente em Dev Mode)

- **Endpoint:** `POST /v1/pixQrCode/simulate-payment`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url 'https://api.abacatepay.com/v1/pixQrCode/simulate-payment?id=pix_char_123456' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "metadata": {}
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro:**

- **Query Parameter - id** (string, obrigatÃ³rio): ID do QRCode PIX que terÃ¡ o pagamento simulado.
- **No Body:**
  - **metadata** (object, opcional): Objeto para incluir dados adicionais sobre a simulaÃ§Ã£o, se necessÃ¡rio.

**Modelo de resposta:**

```json
{
  "data": {
    "id": "pix_char_123456",
    "amount": 100,
    "status": "PAID",
    "devMode": true,
    "brCode": "00020101021226950014br.gov.bcb.pix",
    "brCodeBase64": "data:image/png;base64,iVBORw0KGgoAAA",
    "platformFee": 80,
    "createdAt": "2025-03-24T21:50:20.772Z",
    "updatedAt": "2025-03-24T21:50:20.772Z",
    "expiresAt": "2025-03-25T21:50:20.772Z"
  },
  "error": null
}
```

- **DocumentaÃ§Ã£o:** [Simular Pagamento](https://docs.abacatepay.com/pages/pix)

---

### Saques (Novo)

#### âž¤ Criar Saque

- **Endpoint:** `POST /v1/withdraw/create`
- **curl esperado como exemplo:**

```bash
curl --request POST \
  --url https://api.abacatepay.com/v1/withdraw/create \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}' \
  --header 'content-type: application/json' \
  --data '{
    "amount": 5000,
    "pixKey": "fulano@banco.com",
    "notes": "Saque de teste"
  }'
```

**ExplicaÃ§Ã£o de cada parÃ¢metro:**

- **amount** (number, obrigatÃ³rio): valor do saque em centavos.
- **pixKey** (string, obrigatÃ³rio): chave PIX do destinatÃ¡rio.
- **notes** (string, opcional): observaÃ§Ã£o ou descriÃ§Ã£o do saque.

**Modelo de resposta:**

```json
{
  "data": {
    "id": "wd_123456",
    "amount": 5000,
    "status": "PENDING",
    "pixKey": "fulano@banco.com",
    "createdAt": "2025-03-24T21:50:20.772Z",
    "updatedAt": "2025-03-24T21:50:20.772Z"
  },
  "error": null
}
```

---

#### âž¤ Buscar Saque

- **Endpoint:** `GET /v1/withdraw/get?id=wd_123456`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url 'https://api.abacatepay.com/v1/withdraw/get?id=wd_123456' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

**Modelo de resposta:** igual ao da criaÃ§Ã£o.

---

#### âž¤ Listar Saques

- **Endpoint:** `GET /v1/withdraw/list`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url https://api.abacatepay.com/v1/withdraw/list \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

**Modelo de resposta:**

```json
{
  "data": [
    {
      "id": "wd_123456",
      "amount": 5000,
      "status": "PENDING",
      "pixKey": "fulano@banco.com",
      "createdAt": "2025-03-24T21:50:20.772Z",
      "updatedAt": "2025-03-24T21:50:20.772Z"
    }
  ],
  "error": null
}
```

---

### Loja (Novo)

#### âž¤ Obter Detalhes da Loja

- **Endpoint:** `GET /v1/store/get`
- **curl esperado como exemplo:**

```bash
curl --request GET \
  --url https://api.abacatepay.com/v1/store/get \
  --header 'accept: application/json' \
  --header 'authorization: Bearer {SEU_TOKEN_AQUI}'
```

**Modelo de resposta:**

```json
{
  "data": {
    "id": "store_123456",
    "name": "Minha Loja",
    "createdAt": "2025-03-24T21:50:20.772Z"
  },
  "error": null
}
```

---

## Webhooks

- NotificaÃ§Ãµes automÃ¡ticas enviadas pela AbacatePay.
- Eventos disponÃ­veis: `billing.paid`, `pix.paid`, `pix.expired`, `withdraw.paid`.
- Sempre validar a assinatura enviada.
- Implementar retries para lidar com falhas de rede.

Checklist rapido (evita erros comuns):
- URL do webhook deve terminar com `/`. Ex.: `https://SEU-DOMINIO/payments/webhook/abacatepay/`.
- `webhookSecret` vem na query string e deve bater com `ABACATEPAY_WEBHOOK_SECRET`.
- `ABACATEPAY_WEBHOOK_PUBLIC_HMAC_KEY` vem do dashboard e NAO e o "ID publico" do webhook.
- Assinatura chega em `X-Webhook-Signature` e e HMAC-SHA256 em Base64 do corpo bruto.
- Diagnostico rapido: `405` = metodo errado ou falta de `/` no final; `401` = webhookSecret diferente; `400` = assinatura invalida.
- Mudou `.env`? Reinicie o serviço do app (ex.: `systemctl restart gunicorn_simulado.service`).

- Exemplo real de payload (evento `billing.paid` com QRCode PIX):
  - `data.pixQrCode.id` -> id do QRCode (usado para consultar `pixQrCode/check`).
  - `data.pixQrCode.metadata` -> objeto com `billing_ref`, `user_id`, `plano_id` (valores string).

```json
{
  "id": "log_exemplo_123",
  "event": "billing.paid",
  "data": {
    "pixQrCode": {
      "id": "pix_char_exemplo_123",
      "amount": 990,
      "kind": "PIX",
      "status": "PAID",
      "metadata": {
        "billing_ref": "038e850f3e5a4c10b5486c1bb5f9c2fd",
        "user_id": "9",
        "plano_id": "4"
      }
    }
  }
}
```

---

## SDKs

- SDKs oficiais disponÃ­veis para integraÃ§Ã£o em linguagens populares.

---

## TransiÃ§Ã£o para ProduÃ§Ã£o

- **DescriÃ§Ã£o:** Para migrar do ambiente de desenvolvimento para produÃ§Ã£o, Ã© necessÃ¡rio desativar o Dev Mode e completar o cadastro com informaÃ§Ãµes adicionais.
- **DocumentaÃ§Ã£o:** [ProduÃ§Ã£o](https://docs.abacatepay.com/pages/production)

---

_Este guia foi elaborado para auxiliar modelos de linguagem e desenvolvedores a integrar-se de forma eficaz com a API da AbacatePay utilizando os endpoints atualizados._
