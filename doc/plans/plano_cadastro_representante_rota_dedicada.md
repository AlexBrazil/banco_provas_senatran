# Plano de implementacao - cadastro por representante com rota dedicada

Data: 2026-03-02
Status: implementado (MVP concluido)

## 1) Contexto e decisoes ja definidas

Objetivo de negocio:
- manter cadastro padrao em `Free` para publico geral;
- permitir que representantes direcionem novos usuarios para plano especifico diferente de `Free`, de forma controlada.

Decisoes confirmadas:
1. Nao perguntar codigo promocional no cadastro padrao.
2. Usar rota separada para cadastro de alunos vindos de representantes.
3. Validade curta por link/campanha deve ser configuravel no banco.
4. Limite de usos por link/campanha deve ser configuravel no banco.
5. Vinculo por email/dominio/lista nao sera implementado nesta etapa.
6. Trilha de auditoria detalhada (quem gerou/quem usou/IP/device) nao sera implementada nesta etapa.
7. Revogacao imediata no admin deve existir.
8. Chave logica por convite para fallback:
- `True`: redireciona para `/registrar/` quando convite indisponivel;
- `False`: exibe tela informando indisponibilidade de creditos do plano.

## 2) Proposta de arquitetura

### 2.1 Fluxo funcional

1. Usuario comum continua usando `/registrar/`:
- comportamento atual inalterado;
- cria assinatura `Free`.

2. Usuario de representante usa rota dedicada:
- exemplo: `/registrar/parceiro/<token>/`;
- sistema valida token/campanha no banco;
- se valido, cadastro cria assinatura no plano da campanha;
- se invalido/expirado/sem saldo, bloqueia uso da campanha e oferece ir para `/registrar/`.

### 2.2 Modelo de dados implementado

Nome sugerido: `ConviteCadastroPlano`

Campos:
- `token` (char unico; valor opaco para URL)
- `plano` (FK para `Plano`)
- `ativo` (bool, default `True`)
- `permitir_fallback_free` (bool, default `True`)
- `inicio_vigencia` (datetime, opcional)
- `fim_vigencia` (datetime, opcional)
- `limite_usos` (int, opcional; `null` = ilimitado)
- `usos_realizados` (int, default `0`)
- `criado_em` / `atualizado_em`

Observacoes:
- validade e limite de usos ficam 100% configuraveis no banco/admin.
- revogacao imediata via `ativo=False` (e opcionalmente `fim_vigencia=agora`).

### 2.3 Regras de validacao de campanha

Campanha/token e considerado valido quando:
1. `ativo=True`
2. dentro da vigencia:
- se `inicio_vigencia` informado: `agora >= inicio_vigencia`
- se `fim_vigencia` informado: `agora <= fim_vigencia`
3. limite de usos respeitado:
- se `limite_usos` informado: `usos_realizados < limite_usos`

### 2.4 Consumo seguro de usos

No POST de cadastro da rota de parceiro:
1. abrir transacao atomica;
2. buscar campanha com `select_for_update()`;
3. revalidar regras (vigencia/ativo/limite) dentro da transacao;
4. criar usuario + assinatura no plano da campanha;
5. incrementar `usos_realizados`;
6. commit.

Isso evita race condition quando varios usuarios usam o mesmo link ao mesmo tempo.

## 3) Rotas e backend

### 3.1 Rotas

Adicionar em `banco_questoes/urls_auth.py`:
- `path("registrar/parceiro/<str:token>/", views_auth.registrar_parceiro, name="register_partner")`

### 3.2 Views

Em `banco_questoes/views_auth.py`:
- manter `registrar` atual sem alteracao de regra;
- criar `registrar_parceiro(request, token)` com:
  - validacao de token/campanha;
  - render da tela de cadastro (reuso do template atual, com contexto indicando origem parceiro);
  - criacao de assinatura no plano alvo da campanha, nao no `Free`.

### 3.3 Mensagens UX (simples e diretas)

Estados da rota de parceiro:
1. Token invalido: "Link de cadastro invalido."
2. Token expirado: "Este link de cadastro expirou."
3. Limite atingido: "Este link atingiu o limite de cadastros."
4. Revogado: "Este link foi desativado."

Com CTA:
- "Ir para cadastro padrao" (`/registrar/`).

## 4) Admin (operacao)

Registrar `ConviteCadastroPlano` no admin com:
- filtros: `ativo`, `plano`, vigencia;
- campos editaveis: plano, ativo, inicio/fim vigencia, limite_usos;
- campos leitura: `usos_realizados`, criado_em, atualizado_em;
- acao rapida de revogacao:
  - marcar `ativo=False` para selecao.

## 5) Seguranca

Escopo desta etapa (enxuto):
1. Token opaco e nao sequencial (gerado com alta entropia).
2. Validacao server-side obrigatoria em GET e POST.
3. Consumo transacional para limite de usos.
4. Nao aceitar override de plano via payload de formulario.

Fora de escopo desta etapa:
- vinculo por email/dominio;
- auditoria detalhada de campanha.

## 6) Impacto em telas

Opcoes:
1. Reuso total do template `registration/register.html` com faixa discreta:
- "Cadastro via parceiro - Plano: X".
2. Template dedicado `registration/register_partner.html` (mais controle visual).

Recomendacao inicial:
- Reusar template atual para reduzir risco e tempo.

## 7) Plano de execucao

### Fase A - Schema e admin
1. Criar modelo `ConviteCadastroPlano`.
2. Gerar migration.
3. Registrar admin com filtros e acao de revogacao.

Entregavel:
- campanha configuravel no banco e revogavel no admin.

### Fase B - Rota e regra de cadastro
1. Adicionar rota `register_partner`.
2. Implementar view de cadastro por token.
3. Aplicar criacao de assinatura no plano da campanha.
4. Manter `/registrar/` inalterado no `Free`.

Entregavel:
- dois fluxos separados (padrao e parceiro).

### Fase C - UX e mensagens
1. Ajustar mensagens de erro da campanha.
2. Exibir plano alvo no formulario de parceiro.
3. CTA para cadastro padrao quando token invalido.

Entregavel:
- fluxo claro para usuario final.

### Fase D - Testes
1. Cadastro padrao cria `Free`.
2. Cadastro parceiro com token valido cria plano alvo.
3. Token revogado bloqueia.
4. Token expirado bloqueia.
5. Limite de usos bloqueia apos atingir teto.
6. Concorrencia basica: garantir nao ultrapassar `limite_usos`.

Entregavel:
- cobertura de regressao minima para nao quebrar onboarding atual.

## 8) Criterios de aceite (DoD)

1. `/registrar/` continua sem perguntar codigo e mantendo plano `Free`.
2. `/registrar/parceiro/<token>/` aplica plano da campanha quando valido.
3. Validade e limite de usos sao editaveis no banco/admin.
4. Revogacao imediata funciona via admin.
5. Limite de usos e respeitado com seguranca transacional.
6. Nao existe caminho de override de plano pelo cliente.

## 9) Decisoes aplicadas

1. Path final da rota dedicada:
- `/registrar/parceiro/<token>/`.

2. Comportamento em token invalido:
- redirecionar automaticamente para `/registrar/`.

3. Comportamento em convite indisponivel:
- com `permitir_fallback_free=True`: redireciona para `/registrar/`;
- com `permitir_fallback_free=False`: exibe tela informativa.

4. Formato do token:
- string unica opaca.
