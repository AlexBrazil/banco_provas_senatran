# Plano de acao - Modal "Meu plano" com todos os apps

## Objetivo
Fazer o botao `Meu plano` (no Menu de Apps) abrir um modal com informacoes de acesso/limite para todos os apps, nao apenas `simulado-digital`, mantendo boa usabilidade em desktop e mobile.

## Estado atual
- Botao `Meu plano` esta em `menu/templates/menu/home.html`.
- Modal atual mostra status de 1 app (`simulado-digital`), vindo de `plano_status`.
- Status por card no menu ja existe (via `build_app_access_status`), mas sem detalhamento por limite/uso no modal.

## Escopo
- Backend: fornecer lista de status detalhado por app para leitura no modal.
- Frontend: renderizar lista completa no modal.
- Responsividade: modal maior, com rolagem interna, sem quebrar layout em mobile.
- Testes: smoke de renderizacao e acessibilidade basica.

Fora de escopo:
- Mudar regra de negocio de permissao/limite.
- Mudar catalogo de apps ou fluxo de pagamento.

---

## Requisitos funcionais
1. Modal deve listar todos os apps ativos (`AppModulo.ativo=True`).
2. Para cada app, exibir no minimo:
   - nome do app
   - status (`Liberado`, `Bloqueado pelo plano`, `Em construcao`, `Regra ausente`)
3. Quando houver limite por app:
   - mostrar limite, usados e restantes.
4. Quando app for ilimitado:
   - mostrar `Ilimitado`.
5. Manter informacao do plano atual do usuario no topo do modal.
6. Se usuario nao tiver assinatura ativa:
   - modal deve indicar sem plano ativo, sem quebra de layout.

---

## Requisitos de UX e responsividade
1. Modal com largura responsiva:
   - desktop: largura maior (ex. 720-860px).
   - mobile: `calc(100vw - 16px)` ou equivalente.
2. Conteudo do modal com `max-height` e `overflow-y: auto`.
3. Lista de apps em grid/cartoes:
   - desktop: 2 colunas.
   - tablet/mobile: 1 coluna.
4. Cada item deve ser compacto para evitar rolagem excessiva.
5. Teclado/acessibilidade:
   - manter `Esc` para fechar.
   - foco inicial no painel.
   - retorno de foco para botao ao fechar.

---

## Arquitetura proposta

### Backend
Arquivo alvo: `banco_questoes/access_control.py`
- Criar funcao nova de leitura, por exemplo:
  - `build_plan_modal_status(user) -> dict`
- Estrutura sugerida de retorno:
  - `plano_nome`, `assinatura_ativa`, `valid_until`
  - `apps`: lista com
    - `slug`, `nome`, `status_label`, `badge_class`
    - `ilimitado`
    - `limite_qtd`, `limite_periodo_label`
    - `usos`, `restantes`
    - `em_construcao`, `bloqueado_plano`, `regra_ausente`

Arquivo alvo: `menu/views.py`
- Substituir `plano_status` singular por payload do modal completo.
- Manter cards do menu como estao.

### Frontend
Arquivos alvo:
- `menu/templates/menu/home.html`
- `static/menu_app/menu.css`
- `static/menu_app/menu.js` (manter logica de abrir/fechar)

Mudancas:
- modal com cabecalho de plano + lista de apps.
- componente visual por app (card/linha) com badges e metadados.
- estilos novos para lista detalhada.

---

## Etapas de implementacao

### Etapa 1 - Payload completo do modal
- Implementar funcao agregadora no backend para todos os apps.
- Conectar view do menu para enviar esse contexto.

Aceite:
1. Home do menu renderiza sem erro com payload novo.
2. Sem regressao no status dos cards do menu.

### Etapa 2 - Template do modal com lista de apps
- Atualizar HTML do modal para renderizar todos os apps.
- Exibir plano atual e validade no topo.

Aceite:
1. Modal mostra 8 apps.
2. Status por app visivel.
3. Sem erro para usuario sem assinatura.

### Etapa 3 - Responsividade e refinamento visual
- Ajustar tamanho maximo do modal e rolagem interna.
- Grid responsivo para itens.
- Ajustar espacamentos e tipografia para mobile.

Aceite:
1. Modal usavel em 360px de largura.
2. Nenhum overflow horizontal.
3. Leitura dos itens continua clara em desktop.

### Etapa 4 - Testes
- Atualizar/adicionar testes em `menu/tests.py` para:
  - existencia de botao/modal
  - renderizacao de lista de apps no modal
  - texto de status para caso bloqueado/liberado

Aceite:
1. `manage.py check` sem erros.
2. Testes de menu cobrindo modal atualizado.

---

## Riscos e mitigacoes
1. Modal muito longo em mobile.
- Mitigacao: cards compactos + rolagem interna com `max-height`.

2. Custo de consulta por app.
- Mitigacao: montar dados em lote no backend (sem query por item em loop).

3. Inconsistencia entre badge do card e status do modal.
- Mitigacao: usar mesma fonte de verdade (`build_app_access_status` + regras detalhadas no mesmo modulo).

---

## Checklist final de aceite
1. Botao `Meu plano` abre modal com todos os apps.
2. Cada app exibe status e detalhes de limite quando aplicavel.
3. Modal funciona em desktop e mobile sem quebrar layout.
4. Fechamento por botao, clique no backdrop e tecla Esc funcionando.
5. `manage.py check` sem erros.
