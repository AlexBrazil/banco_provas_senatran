# Status de Execucao - Menu e Controle de Acesso por App

Data de sincronizacao: 2026-03-04

## Resumo rapido
- Fase 1 (Etapas 1 a 8): concluida.
- Fase 2 (Etapas A a H): concluida e estabilizada.
- Evolucao comercial de bloqueio/upgrade: implementada.
- Telemetria Meta Pixel + CAPI: implementada no codigo (homologacao em andamento).

## Estado atual do projeto
- `manage.py check`: sem erros no ultimo ciclo de validacao.
- Migrations relevantes aplicadas:
  - `banco_questoes.0004_app_access_schema`
  - `banco_questoes.0005_ofertaupgradeusuario`
  - `banco_questoes.0006_convitecadastroplano`
  - `banco_questoes.0007_convitecadastroplano_permitir_fallback_free`
  - `banco_questoes.0008_convitecadastroplano_logo_url_and_more`
  - `banco_questoes.0009_plano_permite_upgrade_pix`
- Slug canonico do simulado alinhado em todo o fluxo: `simulado-digital`.
- Simulado em V2 sem fallback legado de decisao:
  - regra por app via `PlanoPermissaoApp` + `UsoAppJanela`;
  - dual-write para `SimuladoUso` opcional via `APP_ACCESS_DUAL_WRITE`.
- Bloqueio unificado:
  - todos os fluxos (incluindo simulado) usam `menu/templates/menu/access_blocked.html`.
- Oferta comercial 24h:
  - persistida por usuario em `OfertaUpgradeUsuario`;
  - cronometro nao reinicia em cada entrada;
  - novo ciclo automatico apos expiracao da janela.
- Elegibilidade de upgrade PIX por plano:
  - controlada por `Plano.permite_upgrade_pix` (backend);
  - `True`: CTA de bloqueio + checkout PIX habilitados;
  - `False`: CTA oculto e checkout bloqueado para o plano.
- Tracking de marketing:
  - Pixel frontend com include centralizado;
  - CAPI server-side com cliente reutilizavel;
  - `PageView` por middleware (namespaces dos apps);
  - eventos de funil: `CompleteRegistration`, `Lead`, `InitiateCheckout`, `Purchase`.
- Cadastro por representante:
  - rota dedicada `/registrar/parceiro/<token>/`;
  - convite com vigencia e limite de usos no banco;
  - toggle `permitir_fallback_free` para decidir fallback em convite indisponivel.

## Fase 1 - Menu e rotas
- Etapa 1: app `menu` criado e integrado.
- Etapa 2: catalogo central em `menu/catalog.py`.
- Etapa 3: 7 apps placeholders criados com tela "Em construcao...".
- Etapa 4: rotas dos placeholders + `/simulado/` integradas.
- Etapa 5: card do app atual apontando para URL canonica `/simulado/`.
- Etapa 6: ajustes visuais e responsividade do menu.
- Etapa 7: smoke tests de rotas implementados em `menu/tests.py`.
- Etapa 8: menu virou raiz `/`; `/menu/` virou alias de compatibilidade.

## Fase 2 - Controle por app
- Etapa A (schema): concluida.
  - Modelos: `AppModulo`, `PlanoPermissaoApp`, `UsoAppJanela`.
- Etapa B (seed): concluida.
  - Command `seed_apps_menu_access` idempotente.
- Etapa C (service + piloto): concluida.
  - `banco_questoes/access_control.py` com `@require_app_access(...)`.
- Etapa D (menu com status por app): concluida.
  - `build_app_access_status(user)` em producao.
- Etapa E (placeholders protegidos): concluida.
- Etapa F (dual-write no simulado): concluida.
- Etapa G (cutover do simulado para V2): concluida.
- Etapa H (limpeza tecnica): concluida.
  - fallback legado removido da decisao do simulado.

## Evolucao comercial (2026-02-27)
- Tela de bloqueio comercial padronizada e aplicada no simulado.
- CTA primario do bloqueio alterado para fluxo direto de pagamento:
  - POST em `payments:upgrade_free`.
- Checkout PIX:
  - botao secundario alterado para `Voltar ao menu`;
  - texto de beneficio alterado para `Uso ilimitado`.
- Menu:
  - botao `Sair` adicionado ao lado de `Meu plano`.
- Auth:
  - telas de login e registro refinadas;
  - imagem superior compartilhada (`alegre2.png`);
  - acao de conta no topo direito;
  - link "Esqueci a senha" ocultado no login por enquanto.

## Evolucao onboarding parceiro (2026-03-02)
- Modelo `ConviteCadastroPlano` implementado e disponivel no admin.
- Convite com token opaco e controle de:
  - vigencia;
  - limite de usos;
  - revogacao imediata (`ativo=False`).
- Convite com identidade visual opcional:
  - `nome_representante`;
  - `logo_url`.
- Rota de login parceiro:
  - `/login/parceiro/<token>/`.
- Comportamento de convite indisponivel:
  - com fallback: redireciona para `/registrar/`;
  - sem fallback: exibe tela informativa de indisponibilidade.

## Evolucao Meta Pixel + CAPI (2026-03-04)
- Configuracao em `settings.py`:
  - `META_PIXEL_ENABLED`, `META_PIXEL_ID`,
  - `META_CAPI_ENABLED`, `META_CAPI_ACCESS_TOKEN`,
  - `META_CAPI_API_VERSION`, `META_CAPI_TEST_EVENT_CODE`.
- Context processor:
  - `banco_questoes.context_processors.meta_pixel_context`.
- Middleware:
  - `banco_questoes.middleware.MetaPageViewCapiMiddleware` para `PageView` server-side.
- Include frontend:
  - `banco_questoes/templates/includes/meta_pixel.html`.
- Eventos implementados:
  - `PageView` (Pixel + CAPI),
  - `CompleteRegistration` (Pixel + CAPI),
  - `Lead` no bloqueio (Pixel + CAPI),
  - `InitiateCheckout` no QR PIX (Pixel + CAPI),
  - `Purchase` no webhook `billing.paid` (CAPI).
- Idempotencia e deduplicacao:
  - `Purchase` somente na transicao real para pago,
  - uso de `event_id` consistente entre canais quando aplicavel.

## Proximos passos sugeridos (ordem)
1. Rodar regressao manual completa (login, menu, bloqueio, checkout PIX, webhook, logout/login).
2. Homologar eventos no Meta Events Manager (com `META_CAPI_TEST_EVENT_CODE`).
3. Monitorar auditoria incluindo eventos Meta (`meta_capi_event_sent`, `meta_capi_event_failed`, `meta_capi_purchase_sent`).
4. Remover `META_CAPI_TEST_EVENT_CODE` em producao estavel.
5. Planejar fase de deprecacao definitiva de `SimuladoUso` quando dual-write nao for mais necessario.

## Comandos de validacao (execucao assistida)
```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations banco_questoes
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
```
