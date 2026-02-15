# Plano de implementacao - app menu + base de apps futuros (v1)

## Objetivo
Criar um novo app `menu` como hub principal com 8 icones de apps, usando as imagens em `static/menu_app/icons`, e preparar a base dos apps futuros com tela padrao de "Em construcao...".

## Escopo
- Criar app Django `menu`.
- Criar tela de menu com 8 cards/icones.
- Integrar o app existente `banco_questoes` como um dos cards.
- Criar base dos apps futuros (rotas + view + template), com pagina placeholder "Em construcao...".
- Manter o sistema atual funcionando sem quebra de URL durante a transicao.

Fora de escopo nesta etapa:
- Implementacao de regras de negocio dos apps futuros.
- Persistencia/modelos especificos de cada app futuro.

## Contexto atual
- Projeto com apps: `banco_questoes` e `payments`.
- Entrada atual do simulado: `path("", views_simulado.simulado_inicio, name="inicio")` em `banco_questoes/urls_simulado.py`.
- `config/urls.py` inclui `banco_questoes.urls_simulado` na raiz (`""`).

## Decisoes de arquitetura (recomendadas)
1. Criar um app dedicado `menu` para concentrar navegacao, catalogo de apps e UX inicial.
2. Criar apps separados para os futuros modulos (base minima), para evitar acoplamento e facilitar evolucao independente.
3. Introduzir transicao de URL em 2 fases para nao quebrar acesso atual:
   - Fase A: menu em `/menu/`, simulado continua funcionando como hoje.
   - Fase B: menu vira raiz `/`, e simulado passa a ter URL canonica `/simulado/`.
4. Usar um template padrao unico de "Em construcao..." reaproveitado pelos apps futuros.

## Mapa de apps e icones (8 cards)
Sugestao de mapeamento dos icones `icon_app_1.png ... icon_app_8.png`:

1. Perguntas e Respostas para Estudo
- slug: `perguntas-respostas`
- app tecnico: `perguntas_respostas`
- status inicial: em construcao
- rota: `/perguntas-respostas/`
- icone: `static/menu_app/icons/icon_app_1.png`

2. Apostila da CNH do Brasil
- slug: `apostila-cnh`
- app tecnico: `apostila_cnh`
- status inicial: em construcao
- rota: `/apostila-cnh/`
- icone: `static/menu_app/icons/icon_app_2.png`

3. Simulacao do Ambiente de Prova do DETRAN (novo modulo futuro)
- slug: `simulacao-prova-detran`
- app tecnico: `simulacao_prova`
- status inicial: em construcao
- rota: `/simulacao-prova-detran/`
- icone: `static/menu_app/icons/icon_app_3.png`

4. Manual de Aulas Praticas
- slug: `manual-aulas-praticas`
- app tecnico: `manual_pratico`
- status inicial: em construcao
- rota: `/manual-aulas-praticas/`
- icone: `static/menu_app/icons/icon_app_4.png`

5. Aprenda jogando
- slug: `aprenda-jogando`
- app tecnico: `aprenda_jogando`
- status inicial: em construcao
- rota: `/aprenda-jogando/`
- icone: `static/menu_app/icons/icon_app_5.png`

6. Oraculo
- slug: `oraculo`
- app tecnico: `oraculo`
- status inicial: em construcao
- rota: `/oraculo/`
- icone: `static/menu_app/icons/icon_app_6.png`

7. Aprova+
- slug: `aprova-plus`
- app tecnico: `aprova_plus`
- status inicial: em construcao
- rota: `/aprova-plus/`
- icone: `static/menu_app/icons/icon_app_7.png`

8. Simulado Digital (app atual `banco_questoes`)
- slug: `simulado-digital`
- app tecnico: `banco_questoes`
- status inicial: ativo
- rota alvo: `/simulado/` (canonica)
- fallback na transicao: rota atual `/`
- icone: `static/menu_app/icons/icon_app_8.png`

## Estrutura de arquivos alvo

### Novo app menu
- `menu/apps.py`
- `menu/urls.py`
- `menu/views.py`
- `menu/catalog.py` (ou `menu/services/catalog.py`) para definir cards do menu
- `menu/templates/menu/home.html`
- `menu/templates/menu/under_construction.html` (template padrao para placeholders)
- `menu/tests.py`

### Novos apps base (placeholders)
- `perguntas_respostas/`
- `apostila_cnh/`
- `simulacao_prova/`
- `manual_pratico/`
- `aprenda_jogando/`
- `oraculo/`
- `aprova_plus/`

Cada app com base minima:
- `apps.py`, `urls.py`, `views.py`, `templates/<app>/index.html`, `tests.py`
- A view inicial so renderiza "Em construcao...".

## Rotas e estrategia de transicao

### Fase A (sem quebra)
- Adicionar `path("menu/", include("menu.urls"))` em `config/urls.py`.
- Manter include atual de `banco_questoes.urls_simulado` na raiz.
- Adicionar tambem include do simulado em `/simulado/` para preparar URL canonica.

Resultado:
- Menu acessivel em `/menu/`.
- Simulado continua em `/` (legado) e passa a existir tambem em `/simulado/`.

### Fase B (troca de entrada)
- Tornar menu a raiz (`""`).
- Remover include raiz antigo do simulado.
- Manter simulado em `/simulado/`.
- Criar redirect de compatibilidade do `/` legado, se necessario, para `/menu/`.

## UX da tela de menu
- Grid responsivo com 8 cards.
- Cada card com: icone, titulo, subtitulo curto, badge de status (`Ativo` ou `Em construcao`).
- Cards ativos: navegam para rota real.
- Cards em construcao: navegam para tela padrao "Em construcao...".
- CTA global opcional: "Voltar ao simulado" enquanto o menu nao for raiz.

## Controle de acesso
- Recomendado proteger menu e placeholders com login (mesma regra do simulado atual).
- Reutilizar padrao de autenticacao existente (`LOGIN_URL`, templates registration).

## Etapas de implementacao (sequenciais)

### Etapa 1) Criar app menu
- Criar app e registrar em `INSTALLED_APPS`.
- Criar `menu/urls.py` e `menu/views.py`.
- Criar template `menu/home.html` com 8 cards.

Entregavel:
- `/menu/` renderiza com os 8 icones.

### Etapa 2) Catalogo central de apps
- Criar `menu/catalog.py` com metadados dos apps:
  - id, titulo, descricao, rota, icone, status.
- View do menu consome esse catalogo.

Entregavel:
- Cards gerados por dados centralizados (facil alteracao futura).

### Etapa 3) Criar base dos apps futuros (placeholders)
- Criar 7 apps listados acima.
- Em cada app, criar rota principal e view/template "Em construcao...".

Entregavel:
- Todas as rotas futuras existentes com placeholder funcional.

### Etapa 4) Integrar rotas no projeto
- Incluir `menu.urls` em `config/urls.py`.
- Incluir rotas dos 7 apps novos.
- Expor `banco_questoes` em `/simulado/` alem da rota atual.

Entregavel:
- Navegacao completa sem 404.

### Etapa 5) Integrar card do app atual `banco_questoes`
- Card "Simulado Digital" aponta para `/simulado/`.
- Durante Fase A, aceitar tambem rota antiga `/` como fallback.

Entregavel:
- App atual acessivel via menu.

### Etapa 6) Ajustes visuais e responsividade
- CSS dedicado em `static/menu_app/`.
- Garantir mobile first e desktop.

Entregavel:
- Tela de menu estavel em celular e desktop.

### Etapa 7) Testes minimos
- Testar HTTP 200 para `/menu/` e todas as 7 rotas placeholders + `/simulado/`.
- Testar redirecionamento para login quando deslogado (se protegido).

Entregavel:
- Suite minima de smoke tests de rotas.

### Etapa 8) Migracao da entrada principal (Fase B)
- Planejar janela de troca.
- Trocar raiz para menu somente apos validacao completa.

Entregavel:
- Sistema abre no menu sem quebrar acesso ao simulado.

## Padrao da pagina "Em construcao..."
Conteudo minimo sugerido:
- Titulo do app.
- Mensagem: "Este modulo esta em construcao e sera liberado em breve.".
- Botao: "Voltar ao menu".
- Botao opcional: "Ir para Simulado Digital".

## Checklist de validacao manual
1. `/menu/` abre e mostra 8 cards com os icones corretos.
2. Card `banco_questoes` abre o simulado normalmente.
3. Os 7 cards futuros abrem tela "Em construcao..." sem erro.
4. Nenhuma rota existente de pagamentos/auth/simulado quebra.
5. Em mobile, cards nao sobrepoem e botoes ficam clicaveis.

## Riscos e mitigacao
- Risco: conflito de rota raiz com simulado atual.
  - Mitigacao: adotar Fase A antes da troca definitiva de raiz.
- Risco: duplicidade conceitual entre "Simulacao do Ambiente de Prova do DETRAN" e app atual.
  - Mitigacao: manter ambos no catalogo com descricoes claras ate decisao de consolidacao.
- Risco: regressao de navegacao por includes de URL.
  - Mitigacao: smoke tests de rotas e validacao manual antes de deploy.

## Definicao de pronto (DoD)
- App `menu` criado e integrado.
- 8 icones exibidos com links funcionais.
- 7 apps futuros com placeholder "Em construcao...".
- App atual `banco_questoes` acessivel pelo menu.
- Documentacao atualizada (`doc/description_project.md`) com novo mapa de navegacao.

---

## Plano final - controle por app + pagamento libera todos

### Objetivo funcional
Implementar controle de acesso e limite por app de forma centralizada, mantendo compatibilidade com o que ja funciona hoje, e garantindo que quando o pagamento for confirmado o aluno tenha acesso liberado aos 8 apps.

### Principios
1. Nao quebrar fluxo atual de login, assinatura e pagamento.
2. Entregar em camadas (schema -> seed -> service -> integracao -> cutover).
3. Cada etapa com teste objetivo e criterio de rollback.
4. Reutilizar `Plano` e `Assinatura` atuais, adicionando camada de permissao por app.

### Modelo de dados proposto

#### 1) Catalogo de apps
- Model: `AppModulo` (pode ficar em `banco_questoes/models.py` ou novo app `acesso`)
- Campos:
  - `slug` (unico, ex.: `simulado-digital`, `oraculo`)
  - `nome`
  - `ativo` (bool)
  - `ordem_menu` (int)
  - `icone_path` (string)
  - `rota_nome` (nome de rota Django para o menu)
  - `em_construcao` (bool)

#### 2) Permissao por plano e app
- Model: `PlanoPermissaoApp`
- Campos:
  - `plano` (FK `Plano`)
  - `app_modulo` (FK `AppModulo`)
  - `permitido` (bool)
  - `limite_qtd` (nullable int; null = ilimitado)
  - `limite_periodo` (DIARIO/SEMANAL/MENSAL/ANUAL/null)
- Regra:
  - Unique `(plano, app_modulo)`.
  - Se `permitido=False`, acesso negado mesmo com assinatura ativa.

#### 3) Uso por app (janela corrido)
- Model: `UsoAppJanela`
- Campos:
  - `usuario` (FK auth user)
  - `app_modulo` (FK `AppModulo`)
  - `janela_inicio`
  - `janela_fim`
  - `contador`
- Regras:
  - Unique `(usuario, app_modulo, janela_inicio, janela_fim)`.
  - Incremento transacional com `select_for_update()` (mesma ideia do `SimuladoUso`).

### Compatibilidade com o sistema atual
- `Plano` e `Assinatura` permanecem como fonte de verdade do status da assinatura.
- `payments` continua atualizando assinatura do usuario como hoje.
- `SimuladoUso` atual nao e removido no inicio:
  - Fase de transicao com dupla escrita/leitura controlada por flag.
  - Depois da validacao, simulado passa a ler apenas `UsoAppJanela`.

### Regras de negocio finais
1. Usuario precisa de assinatura ativa (`Assinatura`) para acessar apps protegidos.
2. Para cada app acessado, o sistema resolve a regra em `PlanoPermissaoApp` do plano ativo.
3. Se `permitido=True` e limite definido, controla uso por `UsoAppJanela`.
4. Se `permitido=True` e limite `null`, app liberado sem contador.
5. Plano pago (ex.: `Aprova DETRAN`) recebe permissao `permitido=True` para os 8 apps e, preferencialmente, `limite_qtd=null`.
6. Resultado esperado: pagamento confirmado => assinatura muda para plano pago => todos os apps liberados automaticamente.

### Padrao obrigatorio de consumo de credito por app (apps futuros)
1. Cada app deve consumir credito apenas no evento de negocio que inicia o uso real da sessao.
2. Rotas de entrada, navegacao, preferencias e APIs auxiliares devem validar acesso sem consumir credito.
3. A navegacao interna (refresh, redirect, proxima/anterior tela) nao pode gerar novo consumo.
4. Bloqueio por limite deve ocorrer ao iniciar nova sessao, nao no meio de sessao ja iniciada.
5. Excecao temporaria: `simulado-digital` pode manter fluxo legado durante transicao (dual-write/cutover), sem impor esse padrao ate a consolidacao final.

### Componentes de servico (camada de dominio)

Criar modulo de servico, por exemplo `banco_questoes/access_control.py`:
- `get_assinatura_ativa(user)`
- `get_regra_app(assinatura, app_slug)`
- `check_and_increment_app_use(user, app_slug)` -> `(allowed: bool, reason: str|None, contexto: dict)`
- `build_app_access_status(user)` para exibir no menu quais apps estao bloqueados/liberados

Decorator utilitario:
- `require_app_access(app_slug)`:
  - exige login
  - valida assinatura
  - valida regra por app
  - incrementa uso (quando aplicavel)
  - renderiza pagina de bloqueio padrao com CTA de upgrade quando plano Free

### Flags de rollout (importante para nao quebrar)
Adicionar no `settings.py` (via env):
- `APP_ACCESS_V2_ENABLED=0|1`:
  - `0`: comportamento antigo.
  - `1`: comportamento novo por app.
- `APP_ACCESS_DUAL_WRITE=0|1`:
  - durante transicao do simulado, grava nos dois contadores (`SimuladoUso` e `UsoAppJanela`).

### Seed de dados inicial

1. Criar 8 registros em `AppModulo` (os 7 novos + `simulado-digital`).
2. Seed para plano Free:
  - `simulado-digital`: permitido com limite atual (ex.: 3/DIARIO).
  - demais apps: definir conforme estrategia de lancamento:
    - opcao A: permitido com limite baixo (preview)
    - opcao B: bloqueado ate assinatura paga
3. Seed para plano pago (`Aprova DETRAN`):
  - 8 apps com `permitido=True` e `limite_qtd=null`.

### Integracao com app menu
- Menu passa a consultar `build_app_access_status(user)`.
- Exibir badge por card:
  - `Liberado`
  - `Bloqueado pelo plano`
  - `Em construcao`
- Clicar em app bloqueado pode:
  - abrir tela de bloqueio com explicacao e CTA para PIX (quando Free), ou
  - desabilitar card com tooltip.

### Integracao com payments
- Nao precisa alterar arquitetura do webhook.
- So garantir dado mestre:
  - plano pago tenha permissao de todos os apps em `PlanoPermissaoApp`.
- No `upgrade_free` e no webhook, ao ativar assinatura paga, o acesso pleno vira automatico pela regra de plano.

### Etapas de implementacao com testes (sequencial e segura)

#### Etapa A) Schema sem efeito colateral
- Criar models: `AppModulo`, `PlanoPermissaoApp`, `UsoAppJanela`.
- Criar admin para visualizar/editar regras.
- Nao alterar views existentes.

Teste da etapa:
1. `makemigrations` e `migrate` sem erro.
2. `manage.py check` sem erro.
3. Admin abre e lista os novos modelos.

Criterio de rollback:
- Reverter migration e remover includes novos (sem impactar fluxo antigo).

#### Etapa B) Seed e consistencia de dados
- Criar command `seed_apps_menu_access`:
  - popula `AppModulo`.
  - popula regras padrao para Free e plano pago.
- Executar command em dev.

Teste da etapa:
1. Conferir 8 apps cadastrados.
2. Conferir regras Free/pago no admin.
3. Validar idempotencia (rodar command 2x sem duplicar).

#### Etapa C) Camada de servico e feature flag
- Implementar `access_control.py`.
- Nao conectar ainda em todas as views.
- Ativar somente para 1 endpoint de teste (ex.: placeholder de um app novo).

Teste da etapa:
1. Usuario Free acessa app teste conforme regra definida.
2. Usuario pago acessa app teste sem bloqueio.
3. Mensagens de bloqueio corretas.

#### Etapa D) Integrar menu com status de acesso
- Menu exibe status por app usando servico.
- Ajustar cards/links para refletir bloqueio/liberacao.

Teste da etapa:
1. Menu mostra 8 apps.
2. Status muda ao trocar plano no admin.
3. Sem regressao nas rotas atuais de simulado e payments.

#### Etapa E) Integrar placeholders dos 7 apps ao controle novo
- Aplicar `require_app_access(app_slug)` nas views placeholder.
- Manter simulado ainda no fluxo antigo (seguranca de transicao).

Teste da etapa:
1. Cada app futuro respeita regra por plano.
2. Free bloqueado recebe CTA correto.
3. Pago acessa todos os placeholders.

#### Etapa F) Migrar simulado para controle por app (transicao)
- Ativar `APP_ACCESS_DUAL_WRITE=1`.
- No simulado:
  - manter validacao antiga
  - gravar tambem em `UsoAppJanela` para `simulado-digital`
- Comparar contadores por alguns dias.

Teste da etapa:
1. Contador antigo e novo evoluem de forma equivalente.
2. Nao ha regressao no bloqueio atual do simulado.

#### Etapa G) Cutover do simulado para V2
- Ativar `APP_ACCESS_V2_ENABLED=1`.
- Simulado passa a usar regra de `PlanoPermissaoApp` + `UsoAppJanela`.
- Manter fallback temporario de seguranca (se regra ausente, usar fluxo antigo).

Teste da etapa:
1. Free atinge limite e recebe CTA PIX.
2. Apos pagamento confirmado, simulado + 7 apps liberam.
3. Webhook repetido continua idempotente.

#### Etapa H) Limpeza tecnica (quando estavel)
- Remover fallback antigo.
- Planejar deprecacao de `SimuladoUso` (opcional, fase posterior).

Teste da etapa:
1. Sem referencias ao fluxo legado.
2. Suite de testes verde.

### Plano de testes por cenarios de negocio (E2E)
1. Cadastro novo -> assinatura Free criada -> menu mostra restricoes de Free.
2. Free usa app com limite ate bloquear.
3. Free tenta app sem permissao e recebe bloqueio padrao.
4. Free paga via PIX -> webhook confirma -> assinatura muda.
5. Apos pagamento: 8 apps liberados.
6. Usuario pago com sessao ativa nao precisa relogar para ver liberacao (menu atualizado no proximo request).
7. Erro de configuracao (app sem regra no plano) -> fallback seguro (bloqueia com mensagem administrativa).

### Observabilidade e auditoria
- Registrar eventos:
  - `app_access_granted`
  - `app_access_blocked`
  - `app_usage_incremented`
  - `app_rule_missing`
- Incluir `app_slug`, `plano`, `limite`, `janela_inicio/fim` no `contexto_json`.

### Riscos e mitigacao
- Risco: regra faltando para algum app/plano.
  - Mitigacao: fallback deny + alerta em auditoria + command de validacao.
- Risco: divergencia entre contador antigo e novo.
  - Mitigacao: fase dual-write com comparacao antes do cutover.
- Risco: bloqueio indevido apos pagamento.
  - Mitigacao: seed obrigatorio para plano pago com 8 apps liberados + teste E2E de webhook.

### Checklist de pre-deploy
1. Migrations aplicadas.
2. `seed_apps_menu_access` executado.
3. Plano pago com 8 permissoes ativas validado no admin.
4. Flags configuradas conforme fase.
5. Smoke test manual:
   - menu
   - simulado
   - 2 apps placeholders
   - fluxo PIX

### Definicao de pronto (DoD)
- Controle por app ativo e validado.
- Free com restricoes por app conforme regra.
- Pagamento confirmado libera todos os 8 apps sem ajustes manuais por usuario.
- Fluxo atual (simulado + payments) preservado durante transicao.

---

## Checklist operacional (execucao)

### Ordem principal (ajustada)
1. Fase 1: implementar menu e chamadas definitivas dos 8 apps (Etapas 1 a 8).
2. Fase 2: implementar controle por plano/assinatura por app (Etapas A a H).

### Fase 1 - Menu + rotas definitivas

#### Etapas da Fase 1
1. Etapa 1 (criar app menu).
2. Etapa 2 (catalogo central).
3. Etapa 3 (base dos 7 apps placeholders).
4. Etapa 4 (integrar rotas no projeto).
5. Etapa 5 (integrar card do app atual `banco_questoes`).
6. Etapa 6 (ajustes visuais/responsividade).
7. Etapa 7 (testes minimos).
8. Etapa 8 (troca da entrada principal, quando aprovado).

#### Comandos base da Fase 1
```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py runserver
```

Se houver novos apps/models nesta fase:
```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
```

Aceite da Fase 1:
1. Menu mostra 8 apps com os icones corretos.
2. Os 7 apps futuros abrem placeholder "Em construcao...".
3. App atual (`banco_questoes`) abre pelo menu.
4. Rotas atuais de auth/simulado/payments seguem funcionando.

### Fase 2 - Controle por plano e assinatura por app

#### Etapa A - Schema
```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Aceite:
1. Migrations aplicadas sem erro.
2. `manage.py check` sem erro.
3. Admin abre os novos modelos.

#### Etapa B - Seed de apps e permissoes
```powershell
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
```

Aceite:
1. Existem 8 registros em `AppModulo`.
2. Regras Free/pago criadas em `PlanoPermissaoApp`.
3. Command idempotente (segunda execucao nao duplica).

#### Etapa C - Service + flag em app piloto
```powershell
# em .env/local_settings:
# APP_ACCESS_V2_ENABLED=1
# APP_ACCESS_DUAL_WRITE=0

.\.venv\Scripts\python.exe manage.py runserver
```

Aceite:
1. Usuario Free respeita regra do app piloto.
2. Usuario pago acessa app piloto.
3. Bloqueio mostra mensagem esperada.

#### Etapa D - Menu com status por app
```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Aceite:
1. Menu mostra 8 cards.
2. Badge/status muda conforme plano do usuario.
3. Nenhuma regressao em auth/simulado/payments.

#### Etapa E - Placeholders protegidos
```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Aceite:
1. 7 apps futuros respondem 200 quando liberados.
2. Apps bloqueados exibem tela de bloqueio.
3. Usuario pago acessa todos os placeholders.

#### Etapa F - Dual-write no simulado
```powershell
# em .env/local_settings:
# APP_ACCESS_DUAL_WRITE=1
# APP_ACCESS_V2_ENABLED=0

.\.venv\Scripts\python.exe manage.py runserver
```

Aceite:
1. Simulado continua com comportamento atual.
2. Contador antigo e novo variam de forma equivalente.
3. Sem regressao no bloqueio do plano Free.

#### Etapa G - Cutover V2
```powershell
# em .env/local_settings:
# APP_ACCESS_V2_ENABLED=1
# APP_ACCESS_DUAL_WRITE=1

.\.venv\Scripts\python.exe manage.py runserver
```

Aceite:
1. Simulado passa a respeitar regra por app.
2. Free bloqueado continua recebendo CTA PIX.
3. Apos pagamento confirmado, os 8 apps ficam liberados.

#### Etapa H - Limpeza
```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Aceite:
1. Sem fallback legado em uso.
2. Sem erro de migracao/check.
3. Fluxo E2E permanece estavel.

### Teste rapido de regressao (obrigatorio apos cada etapa)
1. Login.
2. Acesso ao menu.
3. Acesso ao simulado.
4. Acesso ao checkout PIX.
5. Logout e novo login.

### Gate Go/No-Go por etapa
Pode promover para a proxima etapa somente se:
1. Todos os criterios de aceite da etapa atual passaram.
2. Regressao rapida passou.
3. Nao houve erro novo em logs de aplicacao.
