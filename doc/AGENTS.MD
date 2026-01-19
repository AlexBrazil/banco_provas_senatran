# AGENTS.md

Instrucoes para atuacao neste repositorio. Baseado em `doc/description_project.md`.

---

## Visao geral do projeto

- Django 6 para simulados web do Banco SENATRAN 2025.
- App principal: `banco_questoes/`.
- Banco: PostgreSQL (variaveis no `.env`).
- UI: templates em `banco_questoes/templates/simulado/` e estaticos em `static/simulado/`.
- Config do simulado: `config_simulado.json` (defaults, limites, mensagens, imagens).

---

## Arquitetura e caminhos chave

- Settings e infra: `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py`.
- Modelos: `banco_questoes/models.py`.
- Views/rotas do simulado: `banco_questoes/views_simulado.py`, `banco_questoes/urls_simulado.py`.
- Templates: `banco_questoes/templates/simulado/`.
- JS/CSS: `static/simulado/`.
- Config do simulado: `config_simulado.json`, loader em `banco_questoes/simulado_config.py`.
- Importacao: `banco_questoes/importers/senatran2025/` e commands em
  `banco_questoes/management/commands/`.

---

## Regras de trabalho (obrigatorias)

- Preferir mudancas pequenas e isoladas.
- Evitar novas dependencias sem justificativa.
- Evitar alterar CSS compartilhado quando o impacto nao for claro; prefira CSS novo e especifico ou documente o reuso.
- Escopo primeiro: confirme no codigo/arquivos relevantes antes de propor solucao; se nao encontrou, pergunte.
- Se houver `content.md` dentro da secao alvo, ler e seguir antes de propor mudancas nessa area.
- Usar progressive disclosure: ler apenas arquivos/trechos necessarios; ampliar escopo so com bloqueio ou pedido explicito.
- Sem suposicoes: nao inventar endpoints, settings, modelos ou arquivos; sempre cite o caminho ao referenciar.
- Mudancas minimas: evitar refatoracoes amplas sem pedido.
- Validacao obrigatoria: quando possivel, rodar testes/checks; quando nao, declarar limitacoes.
- Impacto cruzado: evitar alterar CSS compartilhado sem verificar onde e usado.
- Em caso de duvida, listar 1-3 perguntas antes de alterar.
- Garantir que a nova versao cubra 100% dos casos de uso anteriores, salvo pedido explicito.
- Templates de pagina completa devem estender `base.html`; se nao estenderem, incluir `<meta name="viewport">` no `<head>`. Nao aplicar a fragmentos/parciais.
- Para tarefas grandes, registrar o plano em `Documentos_Ajuda/PLAN.md` ou
  `Documentos_Ajuda/plans/<tema>.md` e atualizar o status a cada etapa.

---

## Validacao sugerida

- Se aplicavel: `python manage.py check`.
- Se houver testes relevantes: `python manage.py test`.
- Quando nao for possivel executar, declarar a limitacao no retorno.
