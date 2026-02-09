# Status de Execucao - Menu e Controle de Acesso por App

Data de sincronizacao: 2026-02-09

## Resumo rapido
- Fase 1 (Etapas 1 a 8): concluida.
- Fase 2: Etapas A, B, C concluidas; Etapa D implementada e em validacao.
- Pendentes: Etapas E, F, G, H.

## Estado atual do projeto
- `manage.py check`: sem erros.
- Migration de schema de acesso por app aplicada:
  - `banco_questoes.0004_app_access_schema` marcada como aplicada.
- Flags no `.env`:
  - `APP_ACCESS_V2_ENABLED=1`
  - `APP_ACCESS_DUAL_WRITE=0`
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
- Etapa D (menu com status por app): implementada e pendente de validacao funcional final.
  - Menu usa `build_app_access_status(user)` quando V2 esta ligada.
  - Badges dinamicas no menu: `Liberado`, `Bloqueado pelo plano`, `Em construcao`.

## Arquivos com alteracao local (nao commitados)
- `banco_questoes/access_control.py`
- `menu/views.py`
- `menu/templates/menu/home.html`
- `menu/tests.py`
- `static/menu_app/menu.css`

## Proximos passos sugeridos (ordem)
1. Fechar validacao da Etapa D (menu mudando status conforme plano).
2. Etapa E: aplicar `require_app_access` nos 7 placeholders.
3. Etapa F: dual-write no simulado (`SimuladoUso` + `UsoAppJanela`).
4. Etapa G: cutover do simulado para regras V2.
5. Etapa H: limpeza tecnica/fallback legado.

## Comandos de validacao (execucao assistida)
```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations banco_questoes
```

