# Plano: tipos de usuarios e login

## Contexto atual (confirmado)
- Django auth habilitado em `config/settings.py` (contrib.auth).
- Nao existe modelo de usuario/perfil/assinatura em `banco_questoes/models.py`.

## Modelo de planos configuraveis (decidido)
Objetivo: substituir tiers fixos por planos com regras editaveis, sem afetar assinaturas antigas.

### Regras de negocio fechadas
- Planos podem mudar preco/limites sem impactar assinaturas antigas (snapshot).
- Renovacao acontece por confirmacao de pagamento.
- Na renovacao, apenas o preco_snapshot e atualizado (limites ficam do snapshot original).
- Limite de simulados conta por usuario logado.
- Nao existem beneficios alem de simulados; ao liberar, todos os recursos sao acessiveis.
- Limites usam periodo corrido, iniciado na confirmacao do pagamento.
- Fuso horario oficial: America/Sao_Paulo.

### Entidades e campos sugeridos
Plano (editavel):
- nome
- limite_qtd (null = ilimitado)
- limite_periodo (diario/semanal/mensal/anual ou null)
- validade_dias (null = vitalicio)
- ciclo_cobranca (mensal/anual/nao_recorrente)
- preco
- ativo

Assinatura (snapshot do que foi comprado):
- usuario
- plano (referencia)
- nome_plano_snapshot
- limite_qtd_snapshot
- limite_periodo_snapshot
- validade_dias_snapshot
- ciclo_cobranca_snapshot
- preco_snapshot
- status (ativo/expirado/pausado)
- inicio
- valid_until

Uso/contador:
- usuario
- janela_inicio
- janela_fim
- contador

### Regras de contagem (periodo corrido)
- Diario = 24h, semanal = 7 dias, mensal = 30 dias, anual = 365 dias.
- Janela 1 inicia na confirmacao do pagamento.
- Novas janelas seguem em sequencia enquanto a assinatura estiver ativa.
- Bloqueia quando contador >= limite_qtd.

## Fluxo de login/registro/recuperacao (Etapa 4 definido)
Registro:
- Email unico como identificador.
- Nao usar verificacao de email.
- Cria assinatura free automaticamente no registro (editavel depois no admin).
- Cooldown de 2h por IP + dispositivo; bloquear direto e informar motivo e prazo.
- Nao bloquear emails temporarios.

Login:
- Email + senha.
- Sessao com "lembrar-me" por 20 dias.
- Ao entrar, validar assinatura ativa e limites do snapshot.

Recuperacao:
- Solicita link por email para redefinir senha (link expira).

## Pontos provaveis de bloqueio no app (a validar)
- Inicio/configuracao do simulado em `banco_questoes/views_simulado.py` para aplicar limites e bloquear recursos.
- Templates em `banco_questoes/templates/simulado/` para esconder/opcionar recursos.
- JS em `static/simulado/` para feedback UX (sem confiar apenas no client-side).

## Etapa 5: pontos de controle no backend e templates (definido)
Regras decididas:
- Tudo exige login (inicio, config, iniciar, questao, resultado e APIs).
- Acesso sem login redireciona para a pagina de login.

Backend:
- `banco_questoes/views_simulado.py`: proteger `simulado_inicio`, `simulado_config`, `simulado_iniciar`, `simulado_questao`, `simulado_responder`, `simulado_resultado`, `api_modulos_por_curso`, `api_stats`.
- Sempre validar assinatura ativa e limite vigente antes de iniciar simulado; revalidar nos passos seguintes.

Templates/UX:
- `banco_questoes/templates/simulado/inicio.html`: pagina inicial ja autenticada.
- `banco_questoes/templates/simulado/config.html`: exibir limite/contagem e CTA de upgrade quando bloqueado.
- `banco_questoes/templates/simulado/erro.html`: mensagem objetiva para limite estourado/assinatura expirada.

JS:
- `static/simulado/simulado.js`: apenas feedback visual (nao confiar no client-side).

## Etapa 6: testes e metricas (definido)
Roteiro de validacao manual:
1) Tentar acessar inicio, config, iniciar, questao, resultado e APIs sem login.
   - Esperado: redireciona para login.
2) Registrar novo usuario.
   - Esperado: cria assinatura free automaticamente (ver admin/banco).
3) Iniciar simulado dentro do limite.
   - Esperado: contador incrementa e registro de uso criado.
4) Estourar limite do plano.
   - Esperado: bloqueio com mensagem e sem nova sessao de simulado.
5) Tentar burlar por URL com e sem login.
   - Esperado: sem login redireciona; com login sem limite/assinatura ativa bloqueia.
6) Expirar assinatura manualmente (valid_until no passado).
   - Esperado: bloqueio ao iniciar simulado.
7) Renovar com pagamento confirmado.
   - Esperado: preco_snapshot atualiza, limites snapshot permanecem.
8) Alterar preco do plano.
   - Esperado: novas assinaturas usam preco novo; antigas nao mudam; renovacao atualiza preco_snapshot.
9) Cooldown de cadastro (2h por IP + dispositivo).
   - Esperado: segunda tentativa bloqueia com prazo de espera.
10) Sessao "lembrar-me" por 20 dias.
   - Esperado: expira conforme configuracao; para teste rapido usar `config/local_settings.py`:
     SESSION_COOKIE_AGE = 120

Tabela de eventos/auditoria:
- Campos: tipo, usuario, timestamp, ip, device_id, contexto_json.
- Admin: lista com filtros por data, IP e plano.
- Retencao: 6 meses.

## Plano de implementacao (faseado)
Etapa A: modelos e migrations
- Entregas: modelos de Plano, Assinatura (snapshot), Uso/contador e Evento/Auditoria + migrations; seed do plano free.
- Verificar: migrations aplicadas, tabelas criadas e plano free presente no admin/banco.

Etapa B: admin
- Entregas: admin para planos, assinaturas, uso e eventos com filtros (data, IP, plano).
- Verificar: listagens e filtros funcionando no Django admin.

Etapa C: autenticacao e sessao
- Entregas: registro, login, logout, recuperacao; sessao "lembrar-me" 20 dias; cooldown 2h IP+dispositivo no registro.
- Verificar: fluxo completo de cadastro/login e persistencia de sessao; para teste rapido, reduzir `SESSION_COOKIE_AGE` via `config/local_settings.py`.

Etapa D: enforce no backend
- Entregas: proteger todas as views e APIs com login; validar assinatura ativa e limite antes de iniciar; revalidar nos passos seguintes.
- Verificar: sem login redireciona; com assinatura expirada ou limite estourado bloqueia.

Etapa E: UX/templates
- Entregas: mensagens e CTAs de bloqueio/upgrade; exibir limites/contagem em telas de inicio/config/erro.
- Verificar: mensagens corretas e sem bypass por URL.

Etapa F: auditoria e roteiros
- Entregas: registrar eventos 1-10 na tabela de auditoria; rotina de retencao de 6 meses.
- Verificar: eventos aparecendo no admin; retencao funcionando (limpeza/expurgo conforme regra).

## Plano de trabalho e status
- [x] Etapa 1: rascunho inicial de tipos de usuario
- [x] Etapa 2: regras de negocio definidas (planos, renovacao, limites)
- [x] Etapa 3: modelo de dados proposto (plano, assinatura snapshot, uso)
- [x] Etapa 4: definir fluxo de login/registro/recuperacao
- [x] Etapa 5: definir pontos de controle no backend e templates
- [x] Etapa 6: plano de testes e metricas de conversao
