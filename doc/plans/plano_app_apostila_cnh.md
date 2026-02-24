# Plano de implementacao - app apostila_cnh (v1 detalhado)

## Objetivo
Construir o app `apostila_cnh` com experiencia de leitura de PDF otimizada, progresso de leitura e busca por palavra-chave, integrado ao controle de acesso por plano ja existente no projeto.

Este plano foi montado para permitir execucao por etapas pequenas, com validacao pratica em cada etapa e continuidade em outro chat sem perda de contexto.

---

## Fontes usadas para este plano
1. Estudo tecnico em PDF informado pelo usuario (viabilidade e abordagem tecnica).
2. `doc/description_project.md` (estado atual do sistema).
3. `doc/planos_assinaturas.md` (modelo de plano/assinatura/consumo por app).
4. Estado atual do codigo local (`apostila_cnh` como placeholder protegido por `require_app_access`).
5. `doc/manual_operacao_pdf_apostila_cnh.md` (operacao de upload/ingestao de PDF em storage privado).

### Consulta complementar sob demanda
- Documento de referencia complementar:
  - `cod/plans/Estudo de Viabilidade Técnica - apostila CNH.pdf`
  - `doc/manual_operacao_pdf_apostila_cnh.md`
- Regra de uso:
  - consultar este documento sempre que houver duvida tecnica de UX/performance do leitor (PDF.js, Range Requests, navegacao, zoom, estrategia de memoria);
  - consultar o manual operacional sempre que houver duvida sobre rotina de insercao/troca/reindexacao de PDF;
  - em caso de conflito, priorizar as decisoes de negocio ja fechadas neste plano e registrar a divergencia no checkpoint.

---

## Regras de negocio e premissas

### Regra principal de consumo
- Consumo de credito sera por acesso ao app: cada abertura do `apostila_cnh` conta 1 credito.
- Implementacao recomendada:
  - Rota de entrada do app com `consume=True`.
  - Rotas internas de navegacao, busca e progresso com `consume=False`.

### Regras herdadas do projeto
- Controle de acesso por app: `Assinatura` + `PlanoPermissaoApp` + `UsoAppJanela`.
- Decorator padrao: `require_app_access("apostila-cnh", consume=...)`.
- Bloqueio padrao e CTA de upgrade continuam centralizados em `menu/access_blocked.html`.

### Premissas tecnicas
- Banco: PostgreSQL.
- Leitura de PDF no frontend: PDF.js.
- Suporte a arquivos grandes: HTTP Range Requests.
- Busca textual: indexacao por pagina em tabela propria + busca no banco.
- PDF da apostila deve ficar em armazenamento privado (fora de `static/` e fora de URL publica direta).
- Entrega do PDF deve ocorrer apenas por endpoint protegido por autenticacao + `require_app_access`.
- TTS fica para fase 2 (fora do escopo do MVP).

---

## Escopo desta versao (MVP)

### Dentro do escopo
1. Leitor funcional da apostila com navegacao por pagina.
2. Persistencia da ultima pagina lida por usuario.
3. Busca de termos com retorno de paginas.
4. Layout responsivo (mobile e desktop) com suporte a zoom por pinca.
5. Performance minima para PDF grande via Range Requests.
6. Testes praticos por etapa + smoke tests de regressao.

### Fora do escopo (fase futura)
1. OCR para PDFs escaneados sem texto.
2. TTS (Text-to-Speech) da pagina.
3. Anotacoes, highlights e favoritos por trecho.
4. Download offline no app web.
5. Sincronizacao entre multiplos dispositivos em tempo real (alem do bookmark basico).
6. Efeito page flip 3D (desktop/tablet e mobile).

---

## Arquitetura alvo (resumo)

### Backend
- Novo conjunto de modelos no app `apostila_cnh` para documento, pagina indexada e progresso.
- Command de ingestao para extrair texto por pagina e salvar no banco.
- Endpoints para:
  - metadados do documento,
  - progresso (GET/POST),
  - busca.

### Frontend
- Viewer com PDF.js (lazy loading).
- Navegacao proxima/anterior e input de pagina.
- Busca com lista de resultados e salto de pagina.
- Debounce para salvar progresso.

### Integracao com acesso
- Entrada do app protegida e consumindo credito.
- APIs internas protegidas sem consumir credito.

---

## Modelo de dados proposto (MVP)

### `ApostilaDocumento`
Campos sugeridos:
- `id`
- `slug` (unico)
- `titulo`
- `arquivo_pdf` (path ou FileField)
- `ativo` (bool)
- `total_paginas` (int)
- `idioma` (default `pt-BR`)
- `criado_em`, `atualizado_em`

### `ApostilaPagina`
Campos sugeridos:
- `id`
- `documento` (FK)
- `numero_pagina` (int, iniciando em 1)
- `texto` (text)
- `texto_normalizado` (text opcional para busca)
- `criado_em`, `atualizado_em`

Regras:
- unique `(documento, numero_pagina)`

### `ApostilaProgressoLeitura`
Campos sugeridos:
- `id`
- `usuario` (FK auth)
- `documento` (FK)
- `ultima_pagina_lida` (int)
- `updated_at` / `criado_em`

Regras:
- unique `(usuario, documento)`

Observacao:
- Se o projeto quiser full text nativo do PostgreSQL com ranking, pode evoluir para `SearchVectorField` depois do MVP.

---

## APIs propostas (MVP)

1. `GET /apostila-cnh/api/documento/ativo/`
- Retorna titulo, total_paginas e dados do arquivo para renderizacao.

2. `GET /apostila-cnh/api/progresso/`
- Retorna ultima pagina lida do usuario para documento ativo.

3. `POST /apostila-cnh/api/progresso/`
- Recebe pagina atual e atualiza progresso (com validacoes).

4. `GET /apostila-cnh/api/busca/?q=termo`
- Retorna paginas onde o termo aparece.

Protecao sugerida:
- `require_app_access("apostila-cnh", consume=False)` nas APIs.

---

## Etapas de implementacao detalhadas

## Etapa 0 - Alinhamento funcional e contrato do app
Objetivo:
- Congelar regras funcionais antes de codigo.

Tarefas:
1. Definir o que conta como "abertura do app" (entrada via rota principal).
2. Definir comportamento para refresh (F5 nao consome novo credito).
3. Definir escopo inicial de UX (sem page flip 3D no MVP).
4. Definir documento ativo inicial no admin.

Entregaveis:
- Documento de contrato funcional (pode ser neste mesmo arquivo, secao de decisoes).

Teste pratico:
- Revisao manual entre voce e Codex (sem codigo).

Criterio de aceite:
- Nao haver ambiguidade nas regras de consumo.

Rollback:
- Nao se aplica (etapa de definicao).

---

## Etapa 1 - Estrutura de dados e admin
Objetivo:
- Criar base persistente para documento, paginas e progresso.

Tarefas:
1. Criar modelos `ApostilaDocumento`, `ApostilaPagina`, `ApostilaProgressoLeitura`.
2. Criar migrations.
3. Registrar modelos no admin com filtros e busca.
4. Adicionar constraints e indexes minimos.

Arquivos previstos:
- `apostila_cnh/models.py`
- `apostila_cnh/admin.py`
- `apostila_cnh/migrations/*`

Teste pratico:
```powershell
.\.venv\Scripts\python.exe manage.py makemigrations
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py check
```

Validacao manual:
1. Abrir `/admin/`.
2. Confirmar que os 3 modelos aparecem.
3. Criar 1 documento de teste ativo.

Criterio de aceite:
- Migrations e `check` sem erro.
- CRUD basico disponivel no admin.

Rollback:
- Reverter migration da etapa.

---

## Etapa 2 - Ingestao do PDF e indexacao por pagina
Objetivo:
- Transformar o PDF em conteudo pesquisavel por pagina.

Tarefas:
1. Configurar pasta privada para o PDF da apostila (sem exposicao publica direta por URL de arquivo).
2. Criar command de ingestao (idempotente) para extrair texto pagina a pagina.
3. Salvar `total_paginas` no documento.
4. Salvar/atualizar `ApostilaPagina` por numero de pagina.
5. Preparar estrategia para texto vazio (pagina sem texto).

Arquivos previstos:
- `apostila_cnh/management/commands/import_apostila_pdf.py`
- `apostila_cnh/services/ingestao_pdf.py` (opcional)

Teste pratico:
```powershell
.\.venv\Scripts\python.exe manage.py import_apostila_pdf --slug apostila-cnh-brasil
.\.venv\Scripts\python.exe manage.py shell
```

Validacao no shell:
- Conferir contagem de paginas inseridas.
- Conferir se primeira e ultima pagina possuem registro.
- Conferir que o arquivo PDF esta em area privada e sem rota publica direta no projeto.

Criterio de aceite:
- Ingestao completa sem duplicar paginas ao rodar 2x.

Rollback:
- Limpar registros de `ApostilaPagina` do documento e ajustar command.

---

## Etapa 3 - Rota principal do app e consumo de credito por abertura
Objetivo:
- Trocar placeholder por tela base do leitor e aplicar regra de consumo.

Tarefas:
1. Atualizar view `apostila_cnh:index` para renderizar leitor.
2. Proteger entrada com `require_app_access("apostila-cnh", consume=True)`.
3. Adicionar rotas internas de API com `consume=False`.
4. Garantir mensagens de bloqueio padrao quando sem acesso.

Arquivos previstos:
- `apostila_cnh/views.py`
- `apostila_cnh/urls.py`
- `apostila_cnh/templates/apostila_cnh/index.html`

Teste pratico:
1. Usuario com acesso: abrir `/apostila-cnh/` e validar 200.
2. Usuario sem acesso: validar bloqueio 403 com template padrao.
3. Usuario com limite baixo: abrir varias vezes e confirmar consumo por abertura.

Criterio de aceite:
- Consumo ocorre apenas na entrada do app.
- APIs internas nao consomem credito.

Rollback:
- Voltar temporariamente para placeholder atual.

---

## Etapa 4 - Leitor PDF.js com Range Requests
Objetivo:
- Garantir leitura fluida de PDF grande.

Tarefas:
1. Integrar PDF.js no template do app.
2. Expor URL do PDF ativo no contexto/API.
3. Validar suporte a `Range` no serving do arquivo.
4. Implementar renderizacao de pagina atual com proxima/anterior.

Arquivos previstos:
- `apostila_cnh/templates/apostila_cnh/index.html`
- `static/apostila_cnh/index.js`
- `static/apostila_cnh/index.css`

Teste pratico:
```powershell
curl.exe -I -H "Range: bytes=0-1023" http://127.0.0.1:8000/<url-do-pdf-ativo>
```

Validacao manual:
1. Abrir leitor em rede normal e mobile.
2. Ir para pagina 1, 10, 50 (ou limite do arquivo) sem travar o navegador.

Criterio de aceite:
- Resposta com `206 Partial Content` quando aplicavel.
- Viewer abre sem tentar baixar tudo de uma vez.

Rollback:
- Manter endpoint de metadados e desativar viewer ate ajuste de Range.

---

## Etapa 5 - Progresso de leitura (bookmark)
Objetivo:
- Retomar leitura da ultima pagina automaticamente.

Tarefas:
1. Criar API GET de progresso.
2. Criar API POST de progresso com validacao de pagina.
3. Implementar debounce no frontend (ex.: 2s parado).
4. Ao entrar no app, abrir pagina salva.

Arquivos previstos:
- `apostila_cnh/views.py`
- `apostila_cnh/urls.py`
- `static/apostila_cnh/index.js`

Teste pratico:
1. Abrir pagina 17, aguardar salvar, sair.
2. Reabrir app e validar retorno para pagina 17.
3. Repetir com outro usuario para confirmar isolamento.

Criterio de aceite:
- Progresso persiste por usuario+documento.

Rollback:
- Desativar POST de progresso sem afetar leitura basica.

---

## Etapa 6 - Busca por palavra-chave
Objetivo:
- Permitir localizar conteudo rapidamente.

Tarefas:
1. Criar endpoint de busca em `ApostilaPagina`.
2. Implementar normalizacao basica de termo.
3. Retornar lista enxuta (pagina + trecho pequeno).
4. Integrar UI de busca com salto para pagina.

Arquivos previstos:
- `apostila_cnh/views.py`
- `apostila_cnh/urls.py`
- `static/apostila_cnh/index.js`

Teste pratico:
1. Buscar termo comum (deve retornar varias paginas).
2. Buscar termo raro (deve retornar poucas paginas).
3. Buscar termo inexistente (lista vazia sem erro).

Criterio de aceite:
- Tempo de resposta aceitavel no ambiente local.
- Resultados coerentes com o texto indexado.
- Busca restrita ao documento ativo.

Rollback:
- Ocultar caixa de busca temporariamente.

---

## Etapa 7 - Reservada para fase 2 (TTS)
Objetivo:
- Reservar o espaco da etapa para implementacao futura de TTS sem impactar o cronograma do MVP.

Status:
- Fora do escopo da versao atual.

---

## Etapa 8 - Responsividade e UX de navegacao
Objetivo:
- Garantir boa usabilidade em desktop/tablet/mobile.

Tarefas:
1. Layout de 1 pagina para mobile.
2. Opcional de 2 paginas para desktop/tablet landscape.
3. Implementar zoom por pinca (pinch-to-zoom) no mobile/tablet.
4. Ajustar navegacao para coexistir com zoom:
   - com zoom ativo, priorizar arraste do conteudo;
   - sem zoom ativo, manter navegacao por toque lateral/controles.
5. Melhorar controles de navegacao (toque e teclado).
6. Garantir legibilidade e contraste.

Arquivos previstos:
- `static/apostila_cnh/index.css`
- `static/apostila_cnh/index.js`

Teste pratico:
1. Testar viewport 360x800 (mobile).
2. Testar viewport 768x1024 (tablet).
3. Testar viewport >=1366 (desktop).
4. Testar zoom por pinca (aproximar/afastar) sem travar viewer.
5. Com zoom ativo, validar que gesto de arrastar nao dispara troca acidental de pagina.

Criterio de aceite:
- Sem quebra visual.
- Navegacao previsivel em todos os formatos.
- Zoom por pinca funcional nos navegadores alvo.

Rollback:
- Fixar temporariamente em layout de 1 pagina.

---

## Etapa 9 - Performance e memoria (janela deslizante)
Objetivo:
- Evitar degradacao apos muitas trocas de pagina.

Tarefas:
1. Implementar cache limitado de paginas renderizadas.
2. Manter apenas pagina atual, anterior e proxima em memoria (janela deslizante).
3. Limpar recursos de canvas quando necessario.

Arquivos previstos:
- `static/apostila_cnh/index.js`

Teste pratico:
1. Navegar por 50+ paginas consecutivas.
2. Observar fluidez e uso de memoria no navegador.

Criterio de aceite:
- Sem queda acentuada de desempenho apos uso prolongado.

Rollback:
- Reduzir cache para apenas pagina atual e proxima.

---

## Etapa 10 - Testes automatizados (backend)
Objetivo:
- Cobrir comportamento critico do app com testes repetiveis.

Tarefas:
1. Testes de acesso e bloqueio por plano.
2. Testes de APIs (progresso e busca).
3. Testes de validacao de input (pagina invalida, termo vazio etc).
4. Teste de command de ingestao (smoke).

Arquivos previstos:
- `apostila_cnh/tests.py`

Teste pratico:
```powershell
.\.venv\Scripts\python.exe manage.py test apostila_cnh
```

Criterio de aceite:
- Suite do app verde.

Rollback:
- Marcar casos instaveis como pendentes e manter cobertura do nucleo.

---

## Etapa 11 - Integracao com menu e status do app
Objetivo:
- Preparar app para liberacao controlada no ecossistema.

Tarefas:
1. Conferir `menu/catalog.py` e seed com status coerente.
2. Definir momento de mudar `em_construcao` para `False` no `AppModulo`.
3. Validar badge no menu e rota clicavel.

Arquivos previstos:
- `menu/catalog.py` (se necessario)
- `banco_questoes/management/commands/seed_apps_menu_access.py` (se necessario)

Teste pratico:
1. Rodar seed e validar status no menu.
2. Validar acesso Free x Aprova DETRAN.

Criterio de aceite:
- Estado do menu refletindo estado real do app.

Rollback:
- Retornar `em_construcao=True` no admin/seed.

---

## Etapa 12 - Preparacao de deploy e go-live
Objetivo:
- Subir com seguranca e plano de validacao pos-deploy.

Tarefas:
1. Checklist de migracoes e seeds.
2. Validar variaveis de ambiente e caminho de PDF em producao.
3. Executar smoke test completo.
4. Monitorar logs de acesso e erros do app.

Teste pratico (pre-deploy):
```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations apostila_cnh
.\.venv\Scripts\python.exe manage.py test apostila_cnh menu
```

Criterio de aceite:
- Sem erros criticos no smoke.
- Fluxo principal funcionando para usuario real.

Rollback:
- Reverter release para placeholder do app e manter dados ingeridos.

---

## Protocolo de continuidade entre chats (obrigatorio)

Ao final de cada etapa, registrar este bloco no chat:

```text
CHECKPOINT APOSTILA_CNH
- etapa: Etapa X - <nome>
- status: concluida | parcial | bloqueada
- o_que_foi_feito:
  1) ...
  2) ...
- testes_executados:
  1) comando/acao -> resultado
  2) comando/acao -> resultado
- pendencias:
  1) ...
- decisoes_tomadas:
  1) ...
- proxima_etapa_recomendada: Etapa Y - <nome>
```

Regra de uso:
1. Novo chat sempre comeca colando o ultimo checkpoint.
2. O proximo ciclo inicia pela `proxima_etapa_recomendada`.
3. Nao avancar etapa sem criterio de aceite cumprido.
4. Quando necessario, consultar `cod/plans/Estudo de Viabilidade Técnica - apostila CNH.pdf` e registrar no checkpoint quais pontos foram usados para decisao.

---

## Checklist de regressao rapida (apos cada etapa com codigo)
1. Login funciona.
2. Menu abre e mostra cards.
3. `simulado` continua funcional.
4. `payments` continua funcional.
5. `apostila-cnh` responde conforme plano/acesso.

---

## Riscos e mitigacoes
1. Risco: PDF sem texto selecionavel.
- Mitigacao: detectar durante ingestao e marcar paginas sem texto; planejar OCR futuro.

2. Risco: consumo indevido por chamadas internas.
- Mitigacao: restringir `consume=True` somente na entrada do app.

3. Risco: lentidao em mobile.
- Mitigacao: PDF.js + Range Requests + janela deslizante de paginas.

4. Risco: busca lenta em base grande.
- Mitigacao: indexacao por pagina e evolucao para full text nativo do PostgreSQL.

5. Risco: divergencia entre estado do menu e estado real do app.
- Mitigacao: validar `AppModulo.em_construcao` antes de liberar.

---

## Decisoes definidas neste refinamento
1. Refresh (F5) na pagina inicial da apostila NAO deve contar novo consumo.
2. Busca deve ocorrer apenas no documento ativo.
3. TTS sai do MVP e fica para fase 2.
4. Page flip 3D sai do MVP e fica para fase 2.
5. PDF da apostila deve ficar em armazenamento privado e nao pode ter URL publica direta.

---

## Definicao de pronto (DoD)
1. App `apostila_cnh` deixa de ser placeholder e vira leitor funcional.
2. Consumo por abertura funciona conforme regra definida.
3. Ultima pagina lida persiste e restaura corretamente.
4. Busca funciona no fluxo principal para documento ativo.
5. Testes de backend passam e regressao rapida sem quebra nos apps existentes.
6. Plano documentado e executavel por checkpoint em multiplos chats.
