# Descrição Geral do Projeto

Aqui vai uma descrição bem completa, organizada por visão geral, estrutura e detalhes de cada parte relevante.

---

## O que o projeto faz

- App **Django 6** (“Simulado Digital - Banco de Questões”) para importar o **PDF do Banco SENATRAN 2025**, mapear cursos/módulos e rodar **simulados na web** com sessão, contagem de acertos e revisão simples.
- Banco obrigatório: **PostgreSQL** (variáveis no `.env`).
- Estáticos incluem **centenas de imagens de placas** e um **CSS customizado** para as telas do simulado.

---

## Estrutura de pastas (nível principal)

- `manage.py`: entrypoint Django.
- `config/`: projeto Django (settings, URLs, ASGI/WSGI).
- `banco_questoes/`: app principal (modelos, views do simulado, admin, importadores, management commands, templates).
- `static/`: CSS do simulado e imagens de placas.
- `config_simulado.json`: defaults/textos do simulado (curso padrão, filtros, limites, hint/label do início rápido).
- `.env`, `.env.example`, `.editorconfig`, `.gitignore`, `README.md`.

---

## Configuração e infraestrutura

- **settings.py**
  - Carrega `.env` com `python-dotenv`.
  - Exige `DJANGO_SECRET_KEY` e credenciais `DB_*`.
  - `DEBUG` via `DJANGO_DEBUG`.
  - `LANGUAGE_CODE` / `TIME_ZONE` default: `pt-BR` / `America/Sao_Paulo`.
  - Templates em `BASE_DIR/templates` + diretórios dos apps.
  - Estáticos em `BASE_DIR/static`.
  - `INSTALLED_APPS` inclui o app `banco_questoes`.

- **urls.py**
  - Rota de admin e `include` do namespace `simulado`.

- **asgi.py / wsgi.py**
  - Entrypoints padrão.

- **.env.example**
  - Chaves obrigatórias (segredo Django, debug, PostgreSQL).

- **config_simulado.json / banco_questoes/simulado_config.py**
  - JSON de defaults do simulado (curso padrão por id/slug/nome, modo/dificuldade, filtros, limites min/max, labels/hint do início rápido).
  - Loader cacheado em `get_simulado_config()` com fallback para defaults internos quando o arquivo está ausente ou inválido.

- **README.md**
  - Passos de setup (migrar, seed opcional e `runserver`).

---

## Modelos e admin

### models.py

- **Curso**
  - UUID, nome/slug únicos, ativo.

- **CursoModulo**
  - Ordem, nome, categoria `CONTEUDO` / `SIMULADO`,
  - Faixa de páginas,
  - Ativo,
  - Constraints de ordem e nome por curso.

- **Documento**
  - Título/ano,
  - Hash e nome de arquivo opcionais,
  - Hash único quando preenchido.

- **Questao**
  - Curso, módulo, documento,
  - Número por módulo,
  - Dificuldade,
  - Enunciado,
  - Comentário,
  - Código de placa,
  - Nome do arquivo da imagem,
  - Páginas de origem,
  - `raw_block`,
  - `import_hash` único quando presente.

- **Alternativa**
  - Texto,
  - Ordem,
  - Flag correta,
  - Garante **exatamente uma alternativa correta** por questão.

### admin.py

- Registra os modelos com listagens, filtros e buscas básicas.

### migrations

- **0001_initial.py**
  - Cria tabelas, índices e constraints descritas acima.

---

## Views do simulado e URLs

### urls_simulado.py

Namespace `simulado` com rotas:

- `""` → `simulado_config`
- `iniciar/` → `simulado_iniciar`
- `questao/` → `simulado_questao`
- `responder/` → `simulado_responder`
- `resultado/` → `simulado_resultado`
- `api/modulos/` → `api_modulos_por_curso` (AJAX)

### views_simulado.py

Controla todo o fluxo do simulador usando sessão `simulado_state_v1`.

- Helpers: `_get_state`, `_set_state`, `_clear_state`
- **simulado_config (GET)**  
  Carrega `config_simulado.json` via `get_simulado_config()`, resolve curso padrão (id/slug/nome), mescla defaults e overrides do início rápido, injeta limites/mensagens e JSON para o front.
- **simulado_iniciar (POST)**  
  Valida curso/módulo, aplica limites `qtd_min/qtd_max` e modos permitidos do config, monta queryset de `Questao`, faz `random.sample` dos IDs, grava estado na sessão e redireciona para a primeira questão.
- **simulado_questao (GET)**  
  Lê estado, carrega questão atual com `select_related` e alternativas embaralhadas; renderiza tela; ao fim do fluxo redireciona para resultado.
- **simulado_responder (POST)**  
  Valida alternativa, marca acerto/erro na sessão, avança índice e redireciona para próxima ou resultado.
- **simulado_resultado (GET/POST)**  
  Calcula acertos/percentual, prepara lista de revisão (questão + status respondida/acertou).  
  `POST` limpa estado e volta para configuração.
- **api_modulos_por_curso (GET JSON)**  
  Recebe `curso_id` e retorna módulos ativos (`id`, `ordem`, `nome`) ou erro 400.
### views.py

- Placeholder vazio.

---

## Templates do simulado

- **config.html**
  - Formulário de seleção de curso, módulo (carregado via `fetch` na API), filtros e quantidade.
  - Recebe do backend o JSON de config (`<script id="simulado-config">`) com defaults, limites, mensagens e curso do início rápido.
  - Botão de início rápido usa filtros/label/hint do config e desabilita se não houver curso padrão ou se estiver desativado.
  - Painel de stats e mensagens de status controlados pelo JS.
- **questao.html**
  - Exibe enunciado, módulo, imagem opcional (`static/placas/<arquivo>`),
  - Alternativas em radio,
  - Botão de submit.

- **resultado.html**
  - Mostra acertos / total / percentual,
  - Resumo textual de revisão,
  - Botão “Novo simulado” (POST limpa sessão),
  - Link de retorno.

- **erro.html**
  - Mensagem simples de erro + link de retorno.

---

## Front-end e arquivos estáticos

- **simulado.css**
  - Tema escuro com gradiente,
  - Cards,
  - Estilos para alternativas e imagem de questão,
  - Comentários sobre imagem 70% menor.
  - ⚠️ Atenção: templates referenciam  
    `{% static 'simulado.css' %}` (case-sensitive em produção Linux),  
    enquanto o arquivo está em `static/Simulado/`.  
    Alinhar nome/pasta se necessário.

- **simulado.js**
  - Lê o JSON injetado no `<script id="simulado-config">` para defaults, limites, mensagens e curso padrão.
  - Reseta filtros com esses valores, aplica min/max configuráveis e usa mensagens do config para hints/erros.
  - Botão de início rápido aplica overrides de filtros/label/hint e desabilita sem curso padrão ou se desativado no config.
- **\*.png**
  - Biblioteca de imagens de placas (centenas),
  - Usadas quando `Questao.imagem_arquivo` está preenchido.

---

## Importação SENATRAN 2025

- **extractor.py**
  - Usa **PyMuPDF (fitz)** para abrir PDF e extrair texto por página em `PageText`.

- **normalizer.py**
  - Limpa rodapés conhecidos,
  - Normaliza quebras de linha,
  - Remove vazios.

- **parser.py**
  - Regex específicas do PDF,
  - Detecta início de questão, dificuldade, código de placa,
  - Alternativa correta, comentário e incorretas,
  - Máquina de estados acumula linhas em `ParsedQuestion`,
  - Normaliza dificuldade e marca alternativa correta.

- **persist.py / report.py**
  - Vazios (ganchos futuros).

- **Banco_SENATRAN.pdf**
  - PDF de referência.

- **import_senatran_pdf.py**
  - Comando:
    ```bash
    python manage.py import_senatran_pdf <pdf> --curso --documento \
      [--ano --pages A-B --dry-run --strict-modulo --max-errors]
    ```
  - Resolve curso/documento,
  - Mapeia página → módulo via faixas (`CursoModulo.pagina_inicio/fim`),
  - Executa extractor/normalizer/parser,
  - Monta `import_hash`,
  - Upsert de `Questao` e recriação de `Alternativa`,
  - Contabiliza estatísticas e imprime resumo.

- **seed_modulos_senatran2025.py**
  - Cria/atualiza o curso **“Primeira Habilitação”**
  - Oito módulos (4 conteúdo, 4 simulados),
  - Com ordens e faixas de página.

---

## Outros arquivos

- **apps.py**
  - `AppConfig` do app.

- **tests.py**
  - Stub vazio.

- `__init__.py`
  - Vazios.

- `.venv/` e `__pycache__/`
  - Artefatos locais (não relevantes ao código-fonte).
