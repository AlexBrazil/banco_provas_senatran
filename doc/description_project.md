# Descricao Geral do Projeto

Resumo completo do app, cobrindo visao geral, estrutura, rotas, front-end, regras de negocio e importacao de dados.

---

## O que o projeto faz

- App Django 6 para rodar simulados web com base no Banco SENATRAN 2025.
- Permite escolher curso/modulo/filtros, sorteia questoes, registra respostas em sessao e mostra resultado/revisao.
- Banco obrigatorio: PostgreSQL (variaveis no `.env`).
- Estaticos incluem CSS/JS do simulado e imagens de placas em `static/placas/`.

---

## Estrutura de pastas (nivel principal)

- `manage.py`: entrypoint Django.
- `config/`: projeto Django (settings, URLs, ASGI/WSGI).
- `banco_questoes/`: app principal (modelos, views, admin, importadores, management commands, templates).
- `static/`: CSS/JS do simulado (`static/simulado/`) e imagens de placas (`static/placas/`).
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
- `ALLOWED_HOSTS` vem de `DJANGO_ALLOWED_HOSTS` (default `"*"`), separado por virgula.
- `LANGUAGE_CODE` / `TIME_ZONE`: `pt-br` / `America/Sao_Paulo` (env override).
- Templates: `BASE_DIR/templates` + `APP_DIRS=True`.
- Estaticos: `STATICFILES_DIRS` usa `BASE_DIR/static` quando existir.
- `STATIC_ROOT`: `BASE_DIR.parent / "shared" / "staticfiles"`.
- Seguranca: `SECURE_SSL_REDIRECT` via env; `CSRF_TRUSTED_ORIGINS` via lista separada por virgula.
- Importa `config/local_settings.py` ao final (arquivo nao existe no repo, mas pode ser criado no deploy).

### .env e .env.example
- `.env.example` mostra as variaveis suportadas e sugere defaults.
- `.env` do repo inclui as variaveis do banco e debug; existe tambem `GOOGLE_API_KEY`, que nao e usada no codigo.

---

## URLs

### config/urls.py
- Admin em `/admin/`.
- Rotas do simulado montadas na raiz (`/`), via `banco_questoes.urls_simulado`.
- Existe um include comentado para usar `/simulado/`, mas nao esta ativo.
- Rotas de pagamento em `/payments/`, via `payments.urls`.

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

---

## Modelos e regras de dados

### models.py
- **Curso**: UUID, `nome`/`slug` unicos, `ativo`.
- **CursoModulo**: ordem, nome, categoria (`CONTEUDO`/`SIMULADO`), faixa de paginas, `ativo`.
  - Constraints: `curso+ordem` e `curso+nome` unicos.
- **Documento**: titulo/ano, hash/nome de arquivo opcionais.
  - Constraint: `arquivo_hash` unico quando preenchido.
- **Questao**: curso, modulo, documento, numero por modulo, dificuldade, enunciado, comentario,
  codigo de placa, imagem, paginas, `raw_block`, `import_hash`.
  - Constraints: `documento+modulo+numero_no_modulo` unico; `import_hash` unico quando preenchido.
- **Alternativa**: texto, ordem, `is_correta`.
  - Constraint: no maximo uma alternativa correta por questao (unique condicional).
  - Ordem unica por questao.

### admin.py
Registra modelos com listagem, filtros e busca basica.

---

## Regras de negocio e fluxo do simulado

### Sessao
- Usa `SESSION_KEY = "simulado_state_v1"`.
- Estrutura: `curso_id`, `modulo_id`, `qtd`, `index`, `question_ids`, `answers`,
  `mode`, `filters`, `started_at`, `finished_at`.

### simulado_inicio (GET)
- Carrega config via `get_simulado_config()`.
- Resolve curso padrao (id/slug/nome) e filtros de inicio rapido.
- Limpa sessao anterior ao entrar.

### simulado_config (GET)
- Carrega cursos ativos e injeta JSON de config no template.
- Define defaults, limites e dados para inicio rapido.

### simulado_iniciar (POST)
- Valida curso e aplica limites `qtd_min/qtd_max`.
- Valida modo permitido (`PROVA`/`ESTUDO`).
- Aplica filtros: dificuldade, com imagem, so placas.
- Se nao houver questoes, renderiza `erro.html` com status 400.
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

### api_modulos_por_curso (GET JSON)
- Retorna modulos ativos de um curso (`id`, `ordem`, `nome`).

### api_stats (GET JSON)
- Total para o filtro atual (curso/modulo/dificuldade/imagem/placas).
- Painel separado por criterio (curso/modulo), com contagens por dificuldade, com imagem e placas.

---

## Templates e UI

- `simulado/inicio.html`: landing com "inicio rapido" e link para configuracao.
- `simulado/config.html`: formulario de filtros e painel de stats via AJAX.
- `simulado/questao.html`: tela de questoes (template sem HTML completo, injeta CSS/JS direto).
- `simulado/resultado.html`: resumo, filtros usados e revisao.
- `simulado/erro.html`: mensagem simples com link para inicio.
- `simulado/base.html`: layout basico (nao utilizado nos templates atuais).
- `payments/checkout_free_pix.html`: checkout PIX com QRCode, copia e cola, revalidacao manual e polling.
- Todas as telas principais carregam `scroll-hint`.

---

## Front-end e comunicacao entre scripts

### static/simulado/simulado.js
- Le o JSON injetado em `config.html` (`<script id="simulado-config">`).
- Faz merge com defaults do JS (fallback se JSON falhar).
- Usa `SIMULADO_ENDPOINTS` para buscar:
  - `/api/modulos/` (modulos do curso).
  - `/api/stats/` (contagem total e painel).
- Desabilita campos ate um curso ser selecionado.
- Atualiza limites de quantidade conforme stats.

### static/simulado/scroll-hint.js
- Cria um botao flutuante para rolar ate o fim quando ha overflow vertical.
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

---

## Outros arquivos

- `banco_questoes/tests.py`: stub vazio.
- `banco_questoes/migrations/0001_initial.py`: cria tabelas, indices e constraints.
- `config/wsgi.py` e `config/asgi.py`: bootstrap Django.
