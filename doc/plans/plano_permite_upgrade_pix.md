# Plano de implementacao - elegibilidade PIX por plano (`permite_upgrade_pix`)

Data: 2026-03-04
Status: em planejamento detalhado (Fase 1 ja aplicada: campo no modelo)

## 1) Objetivo

Permitir que **planos alem do `Free`** possam acionar o fluxo de upgrade por PIX, de forma segura e controlada, usando a flag:

- `Plano.permite_upgrade_pix` (bool)

Com isso, planos como `Apostila_Free_cfc` podem oferecer CTA de pagamento quando o usuario atingir limites de uso dos apps bloqueados/restritos.

## 2) Contexto atual (estado real do codigo)

Hoje, o fluxo PIX direto esta amarrado a `Free` em pontos criticos:

1. Exibicao do CTA de upgrade na tela de bloqueio:
- em `banco_questoes/access_control.py` (decorator `require_app_access`)
- em `banco_questoes/views_simulado.py` (fluxo de bloqueio do simulado)

2. Validacao do checkout:
- em `payments/views.py` (`upgrade_free`) via `_assinatura_is_free(...)`

3. Copy/mensagens:
- mensagens citam explicitamente `Free` em alguns pontos.

Impacto:
- usuarios de planos nao-Free (mesmo com limites baixos) nao conseguem iniciar PIX direto.

## 3) O que ja foi feito

Fase inicial concluida:
1. Campo adicionado em `Plano`:
- `permite_upgrade_pix = models.BooleanField(default=False)`
2. Campo exposto no admin de planos.
3. Migration criada/aplicada:
- `banco_questoes.0009_plano_permite_upgrade_pix`

## 4) Escopo da mudanca (proxima etapa)

Incluido:
1. Trocar regra "plano == Free" por "plano.permite_upgrade_pix == True" nos pontos de CTA e validacao do checkout.
2. Garantir compatibilidade de rota atual (`/payments/upgrade/free/`) sem quebrar links existentes.
3. Ajustar mensagens para nao depender de `Free`.
4. Corrigir auditoria para registrar `plano_origem` real.
5. Cobrir com testes.

Fora de escopo:
1. Multiplo destino de upgrade (continua destino unico: `Aprova DETRAN`).
2. Alteracao de precificacao por plano de origem.
3. A/B test de copy.

## 5) Requisitos funcionais

1. Usuario com assinatura ativa em plano com `permite_upgrade_pix=True`:
- deve ver CTA PIX na tela de bloqueio quando bloqueado.

2. Usuario com assinatura ativa em plano com `permite_upgrade_pix=False`:
- nao deve ver CTA PIX.

3. Checkout PIX:
- deve aceitar usuarios elegiveis por flag;
- deve rejeitar nao elegiveis com mensagem clara.

4. Fluxo legado Free:
- deve continuar funcionando sem regressao.

## 6) Requisitos nao funcionais

1. Seguranca:
- elegibilidade sempre validada no backend (nunca so no front).

2. Consistencia:
- mesma regra de elegibilidade em tela de bloqueio e na view de pagamento.

3. Compatibilidade:
- manter rotas e nomes atuais para nao quebrar links em producao.

## 7) Arquitetura proposta

### 7.1 Regra central de elegibilidade

Criar funcao unica (recomendado em `payments/views.py` ou modulo compartilhado):

- `is_upgrade_pix_eligible(assinatura: Assinatura | None) -> bool`

Regra:
1. assinatura existe e ativa;
2. plano existe e esta ativo;
3. `plano.permite_upgrade_pix == True`.

Obs.:
- Evitar checagem por nome do plano (`free`) em qualquer lugar.

### 7.2 Pontos a alterar

1. `banco_questoes/access_control.py`
- hoje: `show_upgrade_cta = plano_nome.strip().lower() == "free"`
- novo: usar assinatura/plano com flag.

2. `banco_questoes/views_simulado.py`
- hoje: `plano_status.is_free` controla CTA.
- novo: adicionar `is_upgrade_pix_eligible` no status (ou checar flag diretamente).

3. `payments/views.py`
- substituir `_assinatura_is_free` por elegibilidade por flag.
- manter endpoint atual (`upgrade_free`) por compatibilidade de rota.

4. Templates/mensagens
- remover textos que indiquem exclusividade de `Free` onde nao for mais verdade.

5. Auditoria
- `_registrar_troca_plano`: `plano_origem` deve vir da assinatura real, nao constante `FREE_PLAN_NAME`.

## 8) Estratégia de compatibilidade

1. Rota:
- manter `/payments/upgrade/free/` no curto prazo para evitar quebra.
- opcional futuro: alias `/payments/upgrade/pix/` e deprecacao gradual.

2. Dados:
- manter `permite_upgrade_pix=False` como default seguro.
- configurar manualmente no admin os planos elegiveis.

## 9) Riscos e mitigacoes

1. Risco: usuario nao elegivel abrir checkout por URL direta.
- Mitigacao: validacao obrigatoria no backend da view de checkout.

2. Risco: CTA aparece mas checkout bloqueia.
- Mitigacao: usar mesma funcao central de elegibilidade em ambos.

3. Risco: cobranca indevida para plano ja premium.
- Mitigacao: condicao de bloqueio para plano destino atual (se ja for `Aprova DETRAN`, nao oferecer checkout).

4. Risco: auditoria comercial incorreta.
- Mitigacao: registrar `plano_origem` dinamico.

## 10) Plano de execucao

### Fase 1 - Regra central
1. Implementar helper unico de elegibilidade por flag.
2. Cobrir helper com testes unitarios simples.

Entregavel:
- criterio de elegibilidade desacoplado de nome de plano.

### Fase 2 - Tela de bloqueio
1. Ajustar `access_control.py`.
2. Ajustar `views_simulado.py`.
3. Revisar template e copy minima.

Entregavel:
- CTA coerente com elegibilidade real.

### Fase 3 - Checkout
1. Ajustar `payments/views.py` para validar por flag.
2. Ajustar mensagens de erro.
3. Corrigir auditoria de plano origem.

Entregavel:
- fluxo PIX aceitando todos os planos elegiveis.

### Fase 4 - Regressao e testes
1. Teste Free elegivel (continua OK).
2. Teste `Apostila_Free_cfc` elegivel.
3. Teste plano nao elegivel.
4. Teste usuario ja no plano de destino.
5. Teste acesso direto por URL ao checkout.

Entregavel:
- seguranca funcional validada.

## 11) Casos de teste (praticos)

1. Plano `Free` com `permite_upgrade_pix=True`:
- bloquear app -> CTA aparece -> checkout permite.

2. Plano `Apostila_Free_cfc` com `permite_upgrade_pix=True`:
- bloquear app -> CTA aparece -> checkout permite.

3. Plano `Representante Viviane` com `permite_upgrade_pix=False`:
- bloquear app -> CTA nao aparece;
- acesso manual ao checkout -> resposta de negacao.

4. Usuario no plano `Aprova DETRAN`:
- nao deve cair em bloqueio por limite (regra padrao sem limite);
- se tentar checkout direto, deve ser bloqueado por elegibilidade/regra de negocio.

## 12) Criterios de aceite (DoD)

1. Nenhum ponto do fluxo depende mais de `nome == "Free"` para elegibilidade PIX.
2. Elegibilidade controlada exclusivamente por `Plano.permite_upgrade_pix`.
3. CTA e checkout seguem a mesma regra.
4. Auditoria registra plano origem real.
5. Fluxo `Free` continua operacional.
6. Fluxo `Apostila_Free_cfc` elegivel operacional quando flag marcada.

## 13) Operacao no admin (apos implementacao)

1. Abrir `Plano` no admin.
2. Marcar `permite_upgrade_pix=True` para planos autorizados.
3. Salvar.
4. Validar com usuario de cada plano autorizado.

## 14) Rollout recomendado

1. Homologar primeiro com apenas `Free=True`.
2. Ativar `Apostila_Free_cfc=True`.
3. Monitorar 24-48h:
- taxa de abertura checkout,
- taxa de pagamento aprovado,
- erros de elegibilidade.

## 15) Rollback

Se houver problema:
1. Desmarcar `permite_upgrade_pix` nos planos afetados.
2. Manter apenas `Free=True`.
3. Revisar logs/eventos e corrigir.

## 16) Documentacao a atualizar apos codar

1. `doc/description_project.md`
2. `doc/planos_assinaturas.md`
3. `doc/plans/status_execucao_menu_access.md`

Com destaque para:
- nova elegibilidade por flag;
- fim da restricao hardcoded ao nome `Free`.
