# Descricao Geral do Projeto

Resumo completo do app, cobrindo visao geral, estrutura, rotas, front-end e importacao de dados.

---

## O que o projeto faz

- App **Django 6** para rodar **simulados web** com base no Banco SENATRAN 2025: escolhe curso/modulo/filtros, sorteia questoes, registra respostas em sessao e mostra resultado/revisao.
- Usa **PostgreSQL** (variaveis no `.env`) como banco obrigatorio.
- Estaticos incluem **CSS/JS custom** e **imagens de placas**.

---

## Estrutura de pastas (nivel principal)

- `manage.py`: entrypoint Django.
- `config/`: projeto Django (settings, URLs, ASGI/WSGI, local_settings.py).
- `banco_questoes/`: app principal (modelos, views do simulado, admin, importadores, management commands, templates).
- `static/`: CSS/JS do simulado (`static/simulado/`) e imagens de placas (`static/placas/`).
- `config_simulado.json`: defaults/textos do simulado (curso padrao, filtros, limites, labels/hints).
- Arquivos de suporte: `.env`, `.env.example`, `.editorconfig`, `.gitattributes`, `.gitignore`, `README.md`.
- `doc/`: documentacao auxiliar.

---

## Configuracao e infraestrutura

- **config/settings.py**
  - Carrega `.env` via `python-dotenv`.
  - Exige `DJANGO_SECRET_KEY`, `DB_*` (PostgreSQL), `DJANGO_DEBUG`.
  - `ALLOWED_HOSTS` vem de `DJANGO_ALLOWED_HOSTS` (default `*`).
  - `LANGUAGE_CODE` / `TIME_ZONE`: `pt-br` / `America/Sao_Paulo` (env override).
  - Templates: `BASE_DIR/templates` + dirs dos apps.
  - Estaticos: `STATICFILES_DIRS` usa `BASE_DIR/static` quando existir.
  - `STATIC_ROOT`: `BASE_DIR.parent / "shared" / "staticfiles"`.
  - Seguranca: `SECURE_SSL_REDIRECT` via `DJANGO_SECURE_SSL_REDIRECT` (default `0`).
  - `CSRF_TRUSTED_ORIGINS` via `DJANGO_CSRF_TRUSTED_ORIGINS` (lista por virgula).
  - `INSTALLED_APPS` inclui `banco_questoes`.
  - Importa `config/local_settings.py` ao final (overrides por ambiente).

- **config/local_settings.py**
  - Arquivo de overrides por ambiente (importado no final do settings).
  - Em dev: `DEBUG=True`, `ALLOWED_HOSTS` local, `CSRF_TRUSTED_ORIGINS` local, `SECURE_SSL_REDIRECT=False`.
  - Em producao: pode ser criado/ajustado na VPS com hosts e CSRF do dominio.

- **config/urls.py**
  - Admin (`/admin/`) e include do namespace `simulado` em `/simulado/`.

- **config_simulado.json** / **banco_questoes/simulado_config.py**
  - JSON com defaults (curso padrao por id/slug/nome, modo/dificuldade, filtros, limites min/max, labels/hint do inicio rapido e mensagens UI).
  - Loader cacheado em `get_simulado_config()` com merge profundo e fallback para defaults internos se arquivo faltar ou estiver invalido.

- **README.md**
  - Passos de setup: instalar deps, configurar Postgres, `migrate`, `seed_modulos_senatran2025` (opcional) e `runserver`.

---
## Modelos e admin

### models.py

- **Curso**: UUID, nome/slug unicos, ativo.
- **CursoModulo**: ordem, nome, categoria (`CONTEUDO`/`SIMULADO`), faixa de paginas, ativo; constraints de ordem/nome por curso.
- **Documento**: titulo/ano, hash/nome de arquivo opcionais, hash unico quando presente.
- **Questao**: curso, modulo, documento, numero por modulo, dificuldade, enunciado, comentario, codigo de placa, arquivo de imagem, paginas de origem, `raw_block`, `import_hash` unico quando presente.
- **Alternativa**: texto, ordem, flag correta; garante **exatamente uma alternativa correta** por questao.

### admin.py
- Registra os modelos com listagem/filtros/busca basicos.

### migrations
- `0001_initial.py`: cria tabelas, indices e constraints.

---

## Views do simulado e URLs

### banco_questoes/urls_simulado.py (namespace `simulado`, montado em `/simulado/`)
- `""` â†’ `simulado_inicio` (tela inicial com escolha de inicio rapido ou com filtros).
- `"config/"` â†’ `simulado_config` (form de filtros).
- `"iniciar/"` â†’ `simulado_iniciar` (POST que sorteia questoes e cria sessao).
- `"questao/"` â†’ `simulado_questao`.
- `"responder/"` â†’ `simulado_responder` (POST).
- `"resultado/"` â†’ `simulado_resultado` (GET/POST).
- `"api/modulos/"` â†’ `api_modulos_por_curso` (AJAX).
- `"api/stats/"` â†’ `api_stats` (AJAX).

### banco_questoes/views_simulado.py
- Usa sessao `simulado_state_v1` com helpers `_get_state`, `_set_state`, `_clear_state`.
- `_build_frontend_config`: merge de defaults/hints/limites e resolve curso padrao (id/slug/nome) para inicio rapido.
- **simulado_inicio (GET)**: limpa sessao ao entrar, mostra cards de "inicio rapido" (POST direto para iniciar) e "inicio com filtros" (link para config) usando defaults do JSON.
- **simulado_config (GET)**: carrega cursos ativos, injeta JSON de config (defaults/limites/mensagens) e dados de inicio rapido para o front.
- **simulado_iniciar (POST)**: valida curso/modulo, aplica limites `qtd_min/qtd_max` e modos permitidos, filtra questoes por dificuldade/imagem/placas, sorteia IDs (`random.sample`), grava estado (modo, filtros, auditoria de tempo) e redireciona para `questao`. Se curso ausente â†’ volta para `inicio`; se filtro sem questoes â†’ renderiza `erro.html`.
- **simulado_questao (GET)**: exige sessao; carrega questao atual (`select_related` + alternativas embaralhadas), mostra contador de acertos/erros. Se acabou â†’ `resultado`.
- **simulado_responder (POST)**: valida alternativa, marca acerto/erro na sessao, avanca indice. No modo ESTUDO renderiza feedback imediato; senao redireciona para proxima/resultado. Sessao ausente â†’ `inicio`.
- **simulado_resultado (GET/POST)**: calcula acertos/percentual/tempos, monta revisao com alternativas; `POST` limpa sessao e volta para `inicio`. Sessao ausente â†’ `inicio`.
- **api_modulos_por_curso (GET JSON)**: recebe `curso_id`, retorna modulos ativos (`id`, `ordem`, `nome`) ou 400.
- **api_stats (GET JSON)**: contagens por filtro atual (total, com imagem, placas, por dificuldade) para preencher painel da config.

---

## Templates e UI

- **simulado/inicio.html**: landing antes da config; mostra card de inicio rapido (POST direto com defaults/overrides) e card â€œinicio com filtrosâ€ (link para config). Limpa sessao ao entrar. Usa `inicio.css` e `scroll-hint.css/js`.
- **simulado/config.html**: formulario de curso/modulo/modo/dificuldade/filtros/quantidade, painel de stats via AJAX, link para voltar ao inicio. Card centralizado na viewport. Injeta JSON de config em `<script id="simulado-config">`.
- **simulado/questao.html**: enunciado + alternativas (radio), imagem opcional de `static/placas/`, feedback opcional no modo ESTUDO, stats de acertos/erros.
- **simulado/resultado.html**: percentuais, contagens, revisao de questoes/alternativas e botao â€œNovo simuladoâ€ (POST limpa sessao e volta ao inicio).
- **simulado/erro.html**: mensagem simples + link para `inicio`.
- **simulado/config copy.html**: versao antiga guardada como referencia.

---

## Front-end e arquivos estaticos

- `static/simulado/simulado.css`: tema escuro, layout dos cards/form/stats/questoes; classe `simulado-container--center` para centralizar card; responsividade de imagens de questao por variaveis CSS.
- `static/simulado/simulado.js`: logica do config (carrega JSON injetado, reseta filtros com defaults, min/max de qtd, bloqueio de campos sem curso, AJAX de modulos e stats). Nao tem mais handler de inicio rapido (migrado para a landing).
- `static/simulado/inicio.css`: estilos da landing (hero + cards de inicio rapido/filtros).
- `static/simulado/scroll-hint.css` / `scroll-hint.js`: seta flutuante no canto inferior direito que aparece se houver overflow vertical; clique faz scroll suave ate o sentinel no final da pagina.
- `static/simulado/simulado copy*.js`: copias antigas.
- `static/placas/`: biblioteca de imagens usadas quando `Questao.imagem_arquivo` esta preenchido.

---

## Importacao SENATRAN 2025

### banco_questoes/importers/senatran2025
- **extractor.py**: usa PyMuPDF (`fitz`) para extrair texto por pagina em `PageText`.
- **normalizer.py**: limpa rodapes, normaliza quebras de linha, remove vazios.
- **parser.py**: regex/mquitetas para identificar inicio de questao, dificuldade, codigo de placa, alternativas correta/incorretas, comentario; maquina de estados monta `ParsedQuestion`; normaliza dificuldade e marca correta.
- **persist.py / report.py**: ganchos vazios.
- **docs/**: documentos de apoio (se houver).

### Management commands
- **import_senatran_pdf.py**  
  `python manage.py import_senatran_pdf <pdf> --curso --documento [--ano --pages A-B --dry-run --strict-modulo --max-errors]`  
  Resolve curso/documento, mapeia paginaâ†’modulo via `CursoModulo.pagina_inicio/fim`, roda extractor/normalizer/parser, monta `import_hash`, upsert de `Questao` e recria `Alternativa`, imprime estatisticas.
- **seed_modulos_senatran2025.py**  
  Cria/atualiza curso â€œPrimeira Habilitacaoâ€ com 8 modulos (conteudo e simulados) e faixas de paginas.

---

## Outros arquivos

- **apps.py**: `AppConfig` do app.
- **tests.py**: stub vazio.
- `__init__.py`: vazios.
- `.venv/` e `__pycache__/`: artefatos locais (ignorar).

