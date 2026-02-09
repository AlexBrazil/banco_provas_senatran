# Descricao Geral do Projeto

Resumo completo do app, cobrindo visao geral, estrutura, rotas, front-end, regras de negocio, autenticacao, pagamentos e importacao de dados.

---

## O que o projeto faz

- App Django 6 para rodar simulados web com base no Banco SENATRAN 2025.
- Permite escolher curso/modulo/filtros, sorteia questoes, registra respostas em sessao e mostra resultado/revisao.
- Exige login para todo o fluxo de simulado e APIs.
- Tem regra de planos/assinaturas para limitar simulados por janela (ex.: Free) e fluxo de upgrade via PIX (AbacatePay).
- Banco obrigatorio: PostgreSQL (variaveis no `.env`).
- Estaticos incluem CSS/JS do simulado e imagens de placas em `static/placas/`.

---

## Estrutura de pastas (nivel principal)

- `manage.py`: entrypoint Django.
- `config/`: projeto Django (settings, URLs, ASGI/WSGI).
- `banco_questoes/`: app principal (modelos, views, auth, admin, importadores, management commands, templates).
- `payments/`: app de checkout PIX, webhook e status de cobranca.
- `static/`: CSS/JS do simulado (`static/simulado/`), CSS de pagamento (`static/payments/`) e imagens de placas (`static/placas/`).
- `config_simulado.json`: defaults/textos do simulado (curso padrao, filtros, limites, mensagens, config de imagens).
- Arquivos de suporte: `.env`, `.env.example`, `.editorconfig`, `.gitattributes`, `.gitignore`, `README.md`.
- `doc/`: documentacao auxiliar.

---

## Configuracao e infraestrutura

### config/settings.py
- Carrega `.env` via `python-dotenv` antes de qualquer `os.getenv`.
- Variaveis obrigatorias: `DJANGO_SECRET_KEY`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- Variaveis suportadas: `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_LANGUAGE_CODE`, `DJANGO_TIME_ZONE`,
  `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DB_HOST`, `DB_PORT`.
- `INSTALLED_APPS` inclui os apps locais `banco_questoes` e `payments`.
- `ALLOWED_HOSTS` vem de `DJANGO_ALLOWED_HOSTS` (default `"*"`), separado por virgula.
- `LANGUAGE_CODE` / `TIME_ZONE`: `pt-br` / `America/Sao_Paulo` (env override).
- Templates: `BASE_DIR/templates` + `APP_DIRS=True`.
- Estaticos: `STATICFILES_DIRS` usa `BASE_DIR/static` quando existir.
- `STATIC_ROOT`: `BASE_DIR.parent / "shared" / "staticfiles"`.
- Seguranca: `SECURE_SSL_REDIRECT` via env; `CSRF_TRUSTED_ORIGINS` via lista separada por virgula.
- Sessao/login: `LOGIN_URL=/login/`, `LOGIN_REDIRECT_URL=/`, `LOGOUT_REDIRECT_URL=/login/`, `SESSION_COOKIE_AGE=20 dias`.
- Toggle de cooldown de cadastro: `REGISTER_COOLDOWN_ENABLED` (0/1).
- Config de pagamento AbacatePay:
  - `ABACATEPAY_API_URL`
  - `ABACATEPAY_API_TOKEN`
  - `ABACATEPAY_WEBHOOK_SECRET`
  - `ABACATEPAY_WEBHOOK_PUBLIC_HMAC_KEY`
  - `ABACATEPAY_WEBHOOK_SIGNATURE_HEADER`
- Importa `config/local_settings.py` ao final (arquivo opcional para override por ambiente/deploy).

### .env e .env.example
- `.env.example` mostra as variaveis base de Django e PostgreSQL.
- `.env` local do projeto contem tambem variaveis de email SMTP e chaves de pagamento.
- `GOOGLE_API_KEY` aparece no `.env`, mas nao ha uso no fluxo principal do simulado/pagamentos.

---

## URLs

### config/urls.py
- Admin em `/admin/`.
- Rotas de autenticacao montadas na raiz (`/`), via `banco_questoes.urls_auth`.
- Rotas do simulado montadas na raiz (`/`), via `banco_questoes.urls_simulado`.
- Existe um include comentado para usar `/simulado/`, mas nao esta ativo.
- Rotas de pagamento em `/payments/`, via `payments.urls`.

### banco_questoes/urls_auth.py
- `"login/"` -> login com email.
- `"logout/"` -> logout.
- `"registrar/"` -> cadastro de usuario (com criacao de assinatura Free).
- `"senha/reset/"` -> solicitar reset de senha.
- `"senha/reset/feito/"` -> confirmacao de envio.
- `"senha/reset/confirmar/<uidb64>/<token>/"` -> definir nova senha.
- `"senha/reset/completo/"` -> senha atualizada.

### banco_questoes/urls_simulado.py (namespace `simulado`)
- `""` -> `simulado_inicio`
- `"config/"` -> `simulado_config`
- `"iniciar/"` -> `simulado_iniciar` (POST)
- `"questao/"` -> `simulado_questao`
- `"responder/"` -> `simulado_responder` (POST)
- `"resultado/"` -> `simulado_resultado` (GET/POST)
- `"api/modulos/"` -> `api_modulos_por_curso` (AJAX)
- `"api/stats/"` -> `api_stats` (AJAX)

### payments/urls.py (namespace `payments`)
- `"upgrade/free/"` -> tela de checkout PIX (GET/POST).
- `"upgrade/free/check/"` -> revalidacao manual (POST).
- `"upgrade/free/status/"` -> status para polling no checkout (GET).
- `"webhook/abacatepay/"` -> webhook de confirmacao (POST).

Notas importantes do webhook (evitar falhas):
- URL deve terminar com `/` (sem barra final pode virar POST -> GET e gerar 405).
- `webhookSecret` chega na query string e deve bater com `ABACATEPAY_WEBHOOK_SECRET`.
- `ABACATEPAY_WEBHOOK_PUBLIC_HMAC_KEY` vem do dashboard e NAO e o ID publico.
- Header esperado: `X-Webhook-Signature`, assinatura HMAC-SHA256 em Base64 do corpo bruto.
- Mudou `.env`? Reinicie o servico do app.

---

## Modelos e regras de dados

### banco_questoes/models.py
- **Curso**: UUID, `nome`/`slug` unicos, `ativo`.
- **CursoModulo**: ordem, nome, categoria (`CONTEUDO`/`SIMULADO`), faixa de paginas, `ativo`.
  - Constraints: `curso+ordem` e `curso+nome` unicos.
- **Documento**: titulo/ano, hash/nome de arquivo opcionais.
  - Constraint: `arquivo_hash` unico quando preenchido.
- **Questao**: curso, modulo, documento, numero por modulo, dificuldade, enunciado, comentario,
  codigo de placa, imagem, paginas, `raw_block`, `import_hash`.
  - Constraints: `documento+modulo+numero_no_modulo` unico; `import_hash` unico quando preenchido.
- **Alternativa**: texto, ordem, `is_correta`.
  - Constraints: no maximo uma alternativa correta por questao (unique condicional) e ordem unica por questao.
- **Plano**: nome, limites (`limite_qtd`, `limite_periodo`), validade, ciclo de cobranca, preco, ativo.
- **Assinatura**: relacao usuario/plano + snapshots de limites/preco no momento da ativacao, status, `inicio`, `valid_until`.
- **SimuladoUso**: contador por usuario e janela (`janela_inicio`, `janela_fim`) para bloqueio por limite de plano.
- **EventoAuditoria**: trilha de eventos (`tipo`, usuario, ip, device_id, contexto_json).

### payments/models.py
- **Billing**: cobranca local do upgrade via PIX (status, valor, `billing_ref`, `pix_id`, payloads de criacao/webhook).
- **WebhookEvent**: armazenagem de eventos recebidos do webhook (tipo, event_id, payload, status de processamento).

### admin.py
- `banco_questoes/admin.py` registra todos os modelos principais, planos/assinaturas, uso e auditoria.
- `PlanoAdmin` registra alteracao de preco em auditoria.
- `AssinaturaAdmin` preenche snapshots na criacao e registra renovacoes relevantes.
- `payments/admin.py` registra `Billing` e `WebhookEvent` para suporte operacional.

---

## Regras de negocio e fluxo do simulado

### Protecao de rotas
- Decorator `login_required_audit` protege todas as views do simulado e APIs.
- Sem login, registra evento `auth_required` e redireciona para login.

### Assinatura e limite
- Antes de iniciar/continuar simulado, valida assinatura ativa (`status=ATIVO` e `valid_until` valido).
- Para planos limitados, usa janela corridas (diario/semanal/mensal/anual) com contador em `SimuladoUso`.
- Ao atingir limite, bloqueia fluxo e pode exibir CTA de upgrade para usuarios Free.

### Sessao
- Usa `SESSION_KEY = "simulado_state_v1"`.
- Estrutura: `curso_id`, `modulo_id`, `qtd`, `index`, `question_ids`, `answers`,
  `mode`, `filters`, `started_at`, `finished_at`.

### simulado_inicio (GET)
- Carrega config via `get_simulado_config()`.
- Resolve curso padrao (id/slug/nome) e filtros de inicio rapido.
- Limpa sessao anterior ao entrar.
- Exibe status de plano no modal "Meu plano".

### simulado_config (GET)
- Carrega cursos ativos e injeta JSON de config no template.
- Define defaults/limites e dados para inicio rapido.
- Exibe resumo de plano atual, uso e bloqueio por limite.

### simulado_iniciar (POST)
- Valida curso e aplica limites `qtd_min/qtd_max`.
- Valida modo permitido (`PROVA`/`ESTUDO`).
- Aplica filtros: dificuldade, com imagem, so placas.
- Se nao houver questoes, renderiza `erro.html` com status 400.
- Incrementa uso do plano (com lock transacional).
- Sorteia IDs com `random.sample` e grava o estado na sessao.

### simulado_questao (GET)
- Exige sessao; carrega questao atual com alternativas.
- Embaralha alternativas antes de renderizar.
- Se terminar, redireciona para `resultado`.

### simulado_responder (POST)
- Valida alternativa e se ela pertence a questao atual.
- Atualiza sessao com acerto/erro e avanca indice.
- Em `ESTUDO`, renderiza feedback imediato (correta/selecionada/comentario).

### simulado_resultado (GET/POST)
- Calcula acertos, erros, nao respondidas e percentual.
- Monta revisao com alternativas corretas e selecionadas.
- Calcula tempo total com `started_at`/`finished_at`.
- `POST` limpa sessao e volta ao inicio.

### API auxiliares
- `api_modulos_por_curso`: retorna modulos ativos (`id`, `ordem`, `nome`).
- `api_stats`: retorna total para filtros atuais e painel por dificuldade/imagem/placas.

---

## Autenticacao e cadastro

### Login/Logout
- Login por email (campo `username` tratado como email).
- Logout com registro de auditoria (`auth_logout`).

### Cadastro
- `registrar` cria usuario e assinatura Free automaticamente.
- Aplica cooldown de cadastro por IP + device (quando habilitado em settings).
- Registra eventos `auth_register`, `auth_register_blocked`.

### Reset de senha
- Fluxo completo via `PasswordResetView` e templates em `templates/registration/`.
- Envio usa templates:
  - `password_reset_email.txt`
  - `password_reset_subject.txt`

---

## Pagamentos e upgrade de plano (PIX)

### Fluxo principal
- `upgrade_free`: somente usuario com assinatura Free ativa pode gerar QRCode.
- Valor e parametros do checkout vem do plano `Aprova DETRAN` cadastrado no admin.
- Cria registro `Billing` com status `PENDING`.

### Revalidacao manual
- `upgrade_free_check`: consulta status do PIX na AbacatePay.
- Tem atraso minimo para botao "Ja paguei" e cooldown entre tentativas.
- Se pago, finaliza billing e ativa plano de upgrade.

### Polling de status
- `upgrade_free_status`: endpoint GET usado pelo frontend do checkout para redirecionar apos pagamento.

### Webhook
- `webhook_abacatepay`: valida segredo/query, assinatura HMAC (quando configurada), registra `WebhookEvent`.
- Processa `billing.paid`, localiza `Billing` por `billing_ref`/`pix_id`, finaliza pagamento e ativa plano.
- Idempotencia: se billing ja estiver `PAID`, nao reaplica troca de plano.

### Integracao AbacatePay (service layer)
- `payments/abacatepay.py` centraliza:
  - criacao de QRCode PIX
  - consulta de status
  - validacao de assinatura webhook

---

## Templates e UI

### Simulado
- `simulado/inicio.html`: landing com inicio rapido, acesso a configuracao e modal "Meu plano".
- `simulado/config.html`: formulario de filtros, status do plano e painel de stats via AJAX.
- `simulado/questao.html`: tela de questoes (inclui feedback no modo estudo).
- `simulado/resultado.html`: resumo, filtros usados e revisao.
- `simulado/erro.html`: mensagens de bloqueio/erro com CTA condicional de upgrade.
- `simulado/base.html`: layout base de templates.

### Auth
- `registration/login.html`
- `registration/register.html`
- `registration/logged_out.html`
- `registration/password_reset_*.html/.txt`

### Payments
- `payments/checkout_free_pix.html`: checkout PIX com QRCode, copia e cola, revalidacao manual e polling.

### JS/CSS
- Todas as telas principais carregam `scroll-hint`.
- `inicio.js` controla modal "Meu plano".
- `simulado.js` controla carregamento de modulos/stats e validacao de formulario.
- `simulado.css`, `inicio.css` e `checkout_free_pix.css` concentram estilos.

---

## Front-end e comunicacao entre scripts

### static/simulado/simulado.js
- Le JSON injetado em `config.html` (`<script id="simulado-config">`).
- Faz merge com defaults do JS (fallback se JSON falhar).
- Usa `SIMULADO_ENDPOINTS` para buscar:
  - `/api/modulos/` (modulos do curso).
  - `/api/stats/` (contagem total e painel).
- Desabilita campos ate um curso ser selecionado.
- Atualiza limites de quantidade conforme stats.

### static/simulado/scroll-hint.js
- Cria botao flutuante para rolar ate o fim quando ha overflow vertical.
- Usa `IntersectionObserver` quando disponivel.

### Imagens responsivas das questoes
- `config_simulado.json` define tamanhos e padding por breakpoints.
- `questao.html` aplica as configs via JS, ajustando variaveis CSS.

### Audio e acessibilidade
- `config.html`, `questao.html` e `resultado.html` usam WebAudio para feedback sonoro.

---

## Config do simulado

### config_simulado.json / banco_questoes/simulado_config.py
- Defaults: curso padrao (por nome/slug/id), modo, dificuldade, filtros e quantidade.
- `inicio_rapido`: label/hint/tooltip e overrides de filtros.
- `limits`: `qtd_min`, `qtd_max`, `modes`.
- `ui.messages`: textos para hints e erros no frontend.
- `imagens`: limites de tamanho e padding para imagens de questoes.
- Loader com cache (LRU) e merge profundo; fallback para defaults se faltar arquivo.
- Aceita override de caminho via `SIMULADO_CONFIG_PATH` (se definido no settings).

---

## Importacao SENATRAN 2025

### Pipeline (importers/senatran2025)
- `extractor.py`: extrai texto de cada pagina do PDF usando PyMuPDF (`fitz`).
- `normalizer.py`: remove rodapes e normaliza quebras de linha.
- `parser.py`: regex + maquina de estados para montar `ParsedQuestion`:
  - reconhece inicio de questao, dificuldade, codigo de placa, correta, comentario e incorretas.
  - normaliza dificuldade e limpa marcadores da alternativa correta.
- `persist.py` e `report.py`: vazios (ganchos futuros).

### Management commands
- `seed_modulos_senatran2025`:
  - Cria/atualiza o curso "Primeira Habilitacao".
  - Cria 8 modulos (conteudo e simulados) com faixa de paginas.
- `import_senatran_pdf`:
  - `python manage.py import_senatran_pdf <pdf> --curso --documento [--ano --pages A-B --dry-run --strict-modulo --max-errors]`
  - Resolve curso/documento.
  - Mapeia pagina -> modulo por `pagina_inicio/pagina_fim`.
  - Gera `import_hash` por modulo+numero+enunciado+correta.
  - Upsert de `Questao` e recria `Alternativa`.
- `purge_audit_events`:
  - remove eventos de auditoria antigos por cutoff de dias (default: 180).

---

## Outros arquivos

- `banco_questoes/migrations/0001_initial.py`: cria tabelas, indices e constraints da base de questoes.
- `banco_questoes/migrations/0002_planos_assinaturas.py`: cria planos/assinaturas/uso/auditoria e seed do plano Free.
- `payments/migrations/0001_initial.py`: cria billing/webhookevent.
- `config/wsgi.py` e `config/asgi.py`: bootstrap Django.
