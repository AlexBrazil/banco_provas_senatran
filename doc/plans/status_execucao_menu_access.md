# Status de Execucao - Menu e Controle de Acesso por App

Data de sincronizacao: 2026-02-09

## Resumo rapido
- Fase 1 (Etapas 1 a 8): concluida.
- Fase 2 (Etapas A a H): implementada localmente.
- Validacoes funcionais manuais: Etapas D, E, F e G confirmadas durante a execucao assistida.

## Estado atual do projeto
- `manage.py check`: sem erros.
- Migration de schema de acesso por app aplicada:
  - `banco_questoes.0004_app_access_schema` marcada como aplicada.
- Slug canonico do simulado alinhado para `simulado-digital` (catalogo + seed + testes).
- Simulado em V2 sem fallback legado de decisao:
  - regra por app via `PlanoPermissaoApp` + contador `UsoAppJanela`;
  - dual-write para `SimuladoUso` mantido como opcional via flag (`APP_ACCESS_DUAL_WRITE`).
- Observacao de testes:
  - `manage.py test menu` ainda depende de permissao `CREATE DATABASE` no PostgreSQL local.

## Fase 1 - Menu e rotas
- Etapa 1: app `menu` criado e integrado.
- Etapa 2: catalogo central em `menu/catalog.py`.
- Etapa 3: 7 apps placeholders criados com tela "Em construcao...".
- Etapa 4: rotas dos placeholders + `/simulado/` integradas.
- Etapa 5: card do app atual apontando para URL canonica `/simulado/`.
- Etapa 6: ajustes visuais e responsividade do menu.
- Etapa 7: smoke tests de rotas implementados em `menu/tests.py`.
- Etapa 8 (Fase B): menu virou raiz `/`; `/menu/` virou alias de compatibilidade.

## Fase 2 - Controle por app
- Etapa A (schema): concluida.
  - Modelos: `AppModulo`, `PlanoPermissaoApp`, `UsoAppJanela`.
  - Admin registrado para os novos modelos.
- Etapa B (seed): concluida.
  - Command `seed_apps_menu_access` criada e validada como idempotente.
- Etapa C (service + piloto): concluida.
  - `banco_questoes/access_control.py` implementado.
  - Piloto aplicado em `oraculo/views.py` com `@require_app_access("oraculo")`.
  - Template de bloqueio: `menu/templates/menu/access_blocked.html`.
- Etapa D (menu com status por app): concluida.
  - Menu usa `build_app_access_status(user)` quando V2 esta ligada.
  - Badges dinamicas no menu: `Liberado`, `Bloqueado pelo plano`, `Em construcao`.
- Etapa E (placeholders protegidos): concluida.
  - 7 placeholders usando `@require_app_access(...)`.
- Etapa F (dual-write no simulado): concluida.
  - Incremento legado (`SimuladoUso`) + incremento novo (`UsoAppJanela`) validado.
- Etapa G (cutover do simulado para V2): concluida.
  - Simulado passou a validar acesso por app com fallback seguro durante a transicao.
- Etapa H (limpeza tecnica): concluida.
  - Fallback legado removido da decisao do simulado.
  - `SimuladoUso` mantido apenas para observabilidade/compatibilidade temporaria via dual-write opcional.

## Arquivos com alteracao local (nao commitados)
- `apostila_cnh/views.py`
- `aprenda_jogando/views.py`
- `aprova_plus/views.py`
- `banco_questoes/access_control.py`
- `banco_questoes/management/commands/seed_apps_menu_access.py`
- `banco_questoes/views_simulado.py`
- `manual_pratico/views.py`
- `menu/catalog.py`
- `menu/views.py`
- `menu/templates/menu/home.html`
- `menu/tests.py`
- `perguntas_respostas/views.py`
- `simulacao_prova/views.py`
- `static/menu_app/menu.css`

## Proximos passos sugeridos (ordem)
1. Rodar regressao manual completa (menu, simulado, checkout PIX, login/logout).
2. Monitorar eventos de auditoria (`app_rule_missing`, `app_access_blocked`, `app_usage_increment_failed`).
3. Planejar fase posterior de deprecacao de `SimuladoUso` e remocao de caminhos legacy restantes.

## Comandos de validacao (execucao assistida)
```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations banco_questoes
```
