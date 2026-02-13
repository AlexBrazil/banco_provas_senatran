# Descricao Geral do Projeto

Resumo tecnico atualizado do sistema, com foco em arquitetura, rotas, regras de acesso por app, simulado e pagamentos.

---

## 1) Visao geral

- Projeto Django 6 para preparacao de prova teorica de transito.
- Banco obrigatorio: PostgreSQL.
- Fluxo principal do usuario:
  - login/cadastro;
  - menu de apps (hub);
  - acesso ao Simulado Digital, app Perguntas e Respostas e demais apps em evolucao.
- Controle de acesso por app em producao de codigo:
  - assinatura ativa (`Assinatura`);
  - regra por app (`PlanoPermissaoApp`);
  - consumo por janela (`UsoAppJanela`).

---

## 2) Apps instalados

- `banco_questoes` (core de dominio, simulado, auth, acesso, auditoria, importacao).
- `menu` (home/hub dos apps).
- `perguntas_respostas` (app de estudo rapido com leitura e avanco automatico).
- `apostila_cnh` (placeholder).
- `simulacao_prova` (placeholder).
- `manual_pratico` (placeholder).
- `aprenda_jogando` (placeholder).
- `oraculo` (placeholder).
- `aprova_plus` (placeholder).
- `payments` (checkout PIX, polling e webhook).

---

## 3) Rotas principais

Arquivo: `config/urls.py`

- `/admin/` -> admin Django.
- `/` -> menu (`menu.urls`).
- `/menu/` -> alias com redirect para `/`.
- Auth na raiz via `banco_questoes.urls_auth`:
  - `/login/`, `/logout/`, `/registrar/`, reset de senha.
- Apps:
  - `/perguntas-respostas/`
  - `/apostila-cnh/`
  - `/simulacao-prova-detran/`
  - `/manual-aulas-praticas/`
  - `/aprenda-jogando/`
  - `/oraculo/`
  - `/aprova-plus/`
- Simulado canonico: `/simulado/` (namespace `simulado`).
- Pagamentos: `/payments/`.

---

## 4) Configuracao (settings)

Arquivo: `config/settings.py`

- `.env` carregado no inicio com `python-dotenv`.
- Variaveis obrigatorias:
  - `DJANGO_SECRET_KEY`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
- Flags relevantes:
  - `REGISTER_COOLDOWN_ENABLED`
  - `APP_ACCESS_V2_ENABLED`
  - `APP_ACCESS_DUAL_WRITE`
- Apps ja registrados no `INSTALLED_APPS`: menu + 7 placeholders + core + payments.
- Login/session:
  - `LOGIN_URL=/login/`
  - `LOGIN_REDIRECT_URL=/`
  - `LOGOUT_REDIRECT_URL=/login/`

Observacao:
- O menu e os decorators de apps usam `APP_ACCESS_V2_ENABLED`.
- O simulado ja esta em logica V2 no codigo atual (com dual-write opcional para legado).

---

## 5) Menu de apps

Arquivos:
- `menu/catalog.py`
- `menu/views.py`
- `menu/templates/menu/home.html`

Regras:
- Catalogo estatico contem `slug`, `titulo`, `descricao`, `icone`, `rota_nome`.
- Em V2, o menu usa `build_app_access_status(user)` para montar badges e clicabilidade.
- O cabecalho do menu contem o botao `Meu plano` (substituiu o antigo `Abrir Simulado`).
- O modal `Meu plano` e aberto no proprio menu (`menu/templates/menu/home.html`) e lista todos os apps ativos com:
  - status por app (`Liberado`, `Bloqueado pelo plano`, `Em construcao`, `Regra ausente`, `Sem plano ativo`);
  - limite/usados/restantes quando houver limite por app;
  - plano atual e validade da assinatura no topo.
- Status visual por card:
  - `Liberado`
  - `Bloqueado pelo plano`
  - `Em construcao`

Observacao operacional:
- no seed oficial atual (`seed_apps_menu_access`), o slug `perguntas-respostas` e semeado com `em_construcao=False`.
- manter este valor alinhado ao estado real de liberacao do app em producao.

Slug canonico do simulado no ecossistema novo:
- `simulado-digital`.

---

## 6) Modelo de dados de acesso por app

Arquivo: `banco_questoes/models.py`

Modelos novos (Fase 2):
- `AppModulo`
  - catalogo persistido de apps (`slug`, `nome`, `ordem_menu`, `rota_nome`, `em_construcao`, etc.).
- `PlanoPermissaoApp`
  - regra por plano x app (`permitido`, `limite_qtd`, `limite_periodo`).
- `UsoAppJanela`
  - contador por usuario+app+janelas de tempo.

Modelos legados ainda existentes:
- `SimuladoUso` (contador antigo do simulado, mantido para compatibilidade observavel).

Modelos de assinatura/plano:
- `Plano`
- `Assinatura`

---

## 7) Seed de acesso por app

Arquivo: `banco_questoes/management/commands/seed_apps_menu_access.py`

Objetivo:
- Popular/atualizar 8 apps em `AppModulo`.
- Garantir regras em `PlanoPermissaoApp` para:
  - plano `Free` (libera apenas `simulado-digital`, com limite vindo do plano Free),
  - plano `Aprova DETRAN` (libera todos sem limite por app).

Compatibilidade:
- Migra slug legado `simulado-provas` para `simulado-digital` (ou desativa legado se ambos existirem).

---

## 8) Controle de acesso (camada de dominio)

Arquivo: `banco_questoes/access_control.py`

Responsabilidades:
- resolver assinatura ativa;
- resolver regra por app (`get_regra_app`);
- validar e incrementar uso por app (`check_and_increment_app_use`);
- montar status para o menu (`build_app_access_status`);
- montar payload do modal `Meu plano` com todos os apps (`build_plan_modal_status`);
- decorator `require_app_access(app_slug)` para proteger views.

Uso atual:
- todos os apps de menu usam controle por decorator (`@require_app_access(...)`) em V2.
- Tela de bloqueio padrao: `menu/templates/menu/access_blocked.html`.

---

## 9) Simulado Digital (estado atual)

Arquivos:
- `banco_questoes/urls_simulado.py`
- `banco_questoes/views_simulado.py`

Fluxo:
- inicio -> config -> iniciar -> questao -> responder -> resultado.
- APIs auxiliares:
  - `simulado:api_modulos`
  - `simulado:api_stats`

Regras de acesso/consumo no codigo atual:
- decisao de acesso do simulado usa V2 (`check_and_increment_app_use` para `simulado-digital`);
- sem fallback legado na decisao;
- dual-write opcional para `SimuladoUso` quando `APP_ACCESS_DUAL_WRITE=1`.

Status de plano exibido em telas do simulado:
- calculado por regra de `PlanoPermissaoApp` + `UsoAppJanela`.
- O botao/modal `Meu plano` nao fica mais dentro do Simulado; o acesso a essa visao foi centralizado no Menu de Apps.
- O Simulado passou a exibir atalho de navegacao `Voltar para o menu`.

---

## 10) Perguntas e Respostas (estado atual)

Arquivos principais:
- `perguntas_respostas/views.py`
- `perguntas_respostas/models.py`
- `perguntas_respostas/urls.py`
- `perguntas_respostas/templates/perguntas_respostas/index.html`
- `perguntas_respostas/templates/perguntas_respostas/estudo.html`
- `static/perguntas_respostas/estudo.js`
- `config_perguntas_respostas.json`

Fluxo:
- inicio rapido e montar estudo com filtros;
- sessao de estudo com:
  - imagem (quando houver) acima do enunciado;
  - resposta correta e comentario;
  - botoes `Retornar`/`Avancar`.

Leitura e avanco automatico:
- botao unico na tela de estudo (`Iniciar leitura e avanco automatico` / `Parar ...`);
- durante automatico, `Retornar` e `Avancar` ficam inativos;
- ao sair por `Nova sessao` ou `Voltar para o menu`, a narracao e interrompida imediatamente.

Regra de selecao:
- prioriza questoes ineditas por contexto;
- quando ineditas acabam, repete por menos recentemente estudadas (LRU) no mesmo contexto.

Persistencia:
- historico por `usuario + questao + contexto_hash` em `PerguntaRespostaEstudo`;
- configuracao do app em JSON com `tempo_min`, `tempo_max`, `tempo_default`, `qtd_default`;
- UI nao expoe ajuste de tempo; tempo efetivo usa `tempo_default` com clamp interno.

---

## 11) Auth e cadastro

Arquivos:
- `banco_questoes/views_auth.py`
- `banco_questoes/forms.py`
- `banco_questoes/urls_auth.py`

Resumo:
- Login por email (`EmailAuthenticationForm`).
- Cadastro cria usuario + assinatura Free.
- Redirecionamento padrao pos-cadastro: Menu de Apps (`menu:home`), salvo quando `next` valido for informado.
- Cooldown de cadastro por IP/device quando habilitado.

---

## 12) Payments (PIX)

Arquivos:
- `payments/views.py`
- `payments/urls.py`
- `payments/models.py`
- `payments/abacatepay.py`

Fluxo:
- checkout de upgrade Free -> Aprova DETRAN;
- polling de status;
- webhook `billing.paid` com idempotencia.

Ao confirmar pagamento:
- atualiza assinatura para plano de upgrade;
- acesso aos apps reflete automaticamente pelas regras de `PlanoPermissaoApp`.

---

## 13) Front-end

- Simulado:
  - templates em `banco_questoes/templates/simulado/`
  - assets em `static/simulado/`
- Perguntas e Respostas:
  - templates em `perguntas_respostas/templates/perguntas_respostas/`
  - assets em `static/perguntas_respostas/`
- Menu:
  - template `menu/templates/menu/home.html`
  - css em `static/menu_app/menu.css`
- Checkout:
  - template `payments/templates/payments/checkout_free_pix.html`
  - css em `static/payments/checkout_free_pix.css`

---

## 14) Comandos operacionais uteis

```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations banco_questoes
.\.venv\Scripts\python.exe manage.py showmigrations perguntas_respostas
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
```

---

## 15) Observacoes de consistencia

- `description_project.md` descreve o estado atual de codigo local.
- Em deploy, garantir:
  - migrations aplicadas;
  - `seed_apps_menu_access` executado;
  - planos em uso com regras em `PlanoPermissaoApp`.
  - confirmar `AppModulo.em_construcao` dos apps liberados (especialmente `perguntas-respostas`).
