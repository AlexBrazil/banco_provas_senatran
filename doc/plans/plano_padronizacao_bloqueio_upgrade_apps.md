# Plano de padronizacao - tela de bloqueio e conversao para upgrade (todos os apps)

Data: 2026-02-27
Status: em execucao (implementacao iniciada em 2026-02-27)

## Status de execucao (2026-02-27)
1. Mock comercial aprovado e refinado.
2. Inicio da implementacao tecnica:
- template real de bloqueio compartilhado em ajuste para tom comercial direto;
- integracao do fluxo de bloqueio do Simulado para usar a tela padrao compartilhada;
- preparacao de asset visual (`cnh_amor.png`) para tela de bloqueio.

## Objetivo
Padronizar a experiencia de bloqueio por plano/limite em todos os apps (incluindo Simulado Digital e Simulacao de Prova), com uma tela unica mais informativa e mais persuasiva para aumentar upgrade para plano pago.

## Resultado esperado
1. Mesmo comportamento tecnico em todos os apps quando houver bloqueio.
2. Mesmo visual, mesma linguagem e mesmos CTAs principais.
3. Aumento mensuravel na taxa de clique em upgrade e na conversao de pagamento.
4. Reducao de duvidas do usuario sobre "por que bloqueou" e "como liberar".

## Contexto atual (resumo)
- Apps com decorator `require_app_access(...)` usam bloqueio padrao (`menu/access_blocked.html`).
- Simulado Digital ainda tem fluxo proprio em pontos de erro/bloqueio (`simulado/erro.html`).
- Resultado: experiencia inconsistente entre apps e copy comercial fragmentada.

## Principios de UX e conversao
1. Clareza imediata: explicar em 1 frase por que o acesso foi bloqueado.
2. Valor antes de venda: mostrar o que o usuario desbloqueia ao pagar.
3. Acao principal unica: um CTA primario forte e sem ambiguidade.
4. Reducao de friccao: caminho curto para pagamento (1 fluxo principal).
5. Confianca: reforcar seguranca, suporte e transparencia de limite/plano.
6. Consistencia: mesmo padrao visual em desktop e mobile.
7. Linguagem de conversao direta: usar argumento de valor claro, sem prometer aprovacao garantida.

## Escopo
Incluido nesta iniciativa:
- Padrao unico de render de bloqueio para todos os apps.
- Novo template visual unificado de bloqueio.
- Padronizacao de copy por motivo de bloqueio.
- Padronizacao de CTA de upgrade e CTA secundario.
- Instrumentacao de eventos para medir conversao.

Fora de escopo nesta etapa:
- Alterar regra de negocio de limites/periodos.
- Alterar pipeline de pagamento (webhook/confirmacao).
- Experimentos multi-variavel de pricing.

## Arquitetura proposta (alto nivel)
1. Backend unico para bloqueio:
- Centralizar resposta de bloqueio em uma funcao unica (via `access_control.py`).
- Sempre retornar `403` com template padrao.

2. Template unico:
- Criar/usar um template global de bloqueio desacoplado de `simulado/base.html`.
- Simulado Digital passa a usar o mesmo template (com contexto especifico quando necessario).

3. Contrato de contexto padrao para o template:
- `app_slug`
- `app_nome`
- `motivo_bloqueio`
- `reason` (mensagem principal)
- `plano_nome`
- `limite_qtd`
- `limite_periodo_label`
- `usos`
- `restantes`
- `janela_fim`
- `show_upgrade_cta`
- `upgrade_url`
- comparativo_plano_atual (itens atuais)
- comparativo_plano_pago (itens liberados com upgrade)

## Conteudo da nova tela (estrutura recomendada)
1. Cabecalho:
- Titulo direto: "Acesso bloqueado neste momento".
- Subtitulo com motivo claro (limite/plano/assinatura).

2. Bloco "Seu status atual":
- Plano atual.
- Uso no periodo (usados/restantes).
- Data/hora de renovacao da janela (quando aplicavel).

3. Bloco "O que voce libera com o upgrade":
- Lista curta de beneficios concretos (ex.: liberar apps, aumentar/retirar limite).
- Linguagem objetiva, sem exagero.

4. CTAs:
- Primario: "Desbloquear agora com PIX".
- Secundario 1: "Voltar ao menu".

5. Rodape de confianca:
- Sinal de seguranca do pagamento.
- Tempo medio de liberacao apos confirmacao (se validado internamente).

## Padrao de copy por motivo de bloqueio
1. `limite_atingido`:
- Mensagem: "Seu limite de uso gratuito foi atingido para este aplicativo."
- Reforco: "Libere todos os aplicativos por apenas <Valor do Plano Default> e aumente suas chances de passar de primeira nas provas do DETRAN. Custa menos que um pastel."

2. `plano_sem_permissao`:
- Mensagem: "Este aplicativo nao esta incluido no seu plano gratuito."
- Reforco: "Libere todos os aplicativos por apenas <Valor do Plano Default> e continue sem bloqueios."

3. `assinatura_inativa`:
- Mensagem: "Sua assinatura esta inativa no momento."
- Reforco: "Reative agora por apenas <Valor do Plano Default> e recupere acesso aos aplicativos."

4. `regra_ausente`/`app_ausente`:
- Mensagem amigavel + instrucoes de contato.
- Sem promessas de liberacao automatica.

## Direcao visual (refino)
1. Hierarquia forte: titulo curto + status atual visivel no primeiro viewport.
2. Contraste alto no CTA primario.
3. Cards informativos com icones simples e leitura rapida.
4. Evitar parede de texto; usar blocos curtos.
5. Mobile-first: CTA primario fixo no viewport final (quando necessario).
6. Coerencia com identidade atual, sem depender de layout exclusivo do simulado.

## Plano de execucao (sem implementacao nesta etapa)

### Fase 0 - Alinhamento de negocio e copy
1. Definir promessa comercial permitida (o que pode e nao pode afirmar).
2. Definir beneficios reais por plano para exibir na tela.
3. Aprovar tom de linguagem comercial direto (objetivo, persuasivo e orientado a conversao).

Entregavel:
- Documento de copy base aprovado.

### Fase 1 - Prototipo visual
1. Wireframe desktop/mobile da tela unica.
2. Proposta de variacoes de CTA e ordem de blocos.
3. Revisao rapida com criterio de conversao.

Entregavel:
- Layout final aprovado (com estados: limite, plano, assinatura inativa).

### Fase 2 - Padronizacao tecnica
1. Definir renderer unico de bloqueio.
2. Unificar contrato de contexto para template.
3. Migrar Simulado Digital para o mesmo renderer/template.
4. Remover divergencias de template antigo para bloqueio.

Entregavel:
- Todos os apps usando o mesmo fluxo de bloqueio.

### Fase 3 - Instrumentacao e metricas
1. Registrar eventos:
- `blocked_view_opened`
- `blocked_cta_upgrade_clicked`
- `upgrade_checkout_started`
- `upgrade_checkout_paid`
2. Incluir `app_slug`, `motivo_bloqueio`, `plano_nome`, `restantes` no contexto de evento.

Entregavel:
- Base de medicao para funil de conversao.

### Fase 4 - Otimizacao orientada a dados
1. Medir baseline por 7 dias apos publicacao da tela unica.
2. Rodar 1 experimento por vez (ex.: titulo ou CTA), sem mudar tudo junto.
3. Promover apenas variacoes com ganho real de conversao.

Entregavel:
- Iteracao de copy/layout com resultado comprovado.

## KPIs de sucesso
1. CTR do CTA primario na tela de bloqueio.
2. Taxa de inicio de checkout apos bloqueio.
3. Taxa de pagamento aprovado apos bloqueio.
4. Tempo medio entre bloqueio e upgrade aprovado.
5. Queda na taxa de retorno ao menu sem acao.

## Criterios de aceite (DoD)
1. Todos os apps bloqueados mostram a mesma tela base.
2. Simulado Digital e Simulacao de Prova aderem ao mesmo padrao.
3. Resposta HTTP permanece `403` para bloqueio.
4. Contexto da tela contem dados de plano/limite quando disponiveis.
5. CTA de upgrade aponta para rota valida e consistente.
6. Layout validado em mobile e desktop.
7. Eventos de funil registrados sem erro.

## Testes recomendados
1. Usuario Free com limite esgotado em cada app.
2. Usuario com plano sem permissao para app especifico.
3. Usuario com assinatura inativa.
4. Usuario pago sem bloqueio (nao deve cair na tela).
5. Validacao visual responsiva (larguras pequenas e grandes).
6. Validacao de links e CTAs.

## Riscos e mitigacao
1. Risco: copy agressiva reduzir confianca.
- Mitigacao: foco em informacao objetiva + prova de valor real.

2. Risco: migracao do simulado quebrar contexto exibido.
- Mitigacao: contrato de contexto padrao + fallback de campos opcionais.

3. Risco: melhorar CTR sem melhorar pagamento aprovado.
- Mitigacao: otimizar funil completo (tela bloqueio -> checkout -> pagamento).

## Decisoes aprovadas (2026-02-27)
1. Comparativo "Plano atual x Plano pago": manter.
2. CTA secundario WhatsApp: remover.
3. Tom de copy: comercial direto.

Aplicacao pratica das decisoes:
- A tela deve exibir comparativo objetivo entre plano atual e plano pago.
- CTA secundario fica apenas "Voltar ao menu" (sem CTA de WhatsApp).
- Copy segue padrao comercial direto: mensagem curta de bloqueio + oferta clara + CTA forte de desbloqueio.

## Wireframe textual v1 (copy pronta para implementar)
Objetivo deste wireframe:
- Definir estrutura final da tela unica.
- Padronizar copy comercial direta.
- Reduzir ambiguidade na implementacao frontend/backend.

### Estrutura da tela (ordem dos blocos)
1. Topo de contexto
- Badge: `Acesso bloqueado`.
- Titulo: `Acesso bloqueado neste aplicativo`.
- Subtitulo dinamico por motivo (ver tabela de copy).

2. Card "Seu status atual"
- Linha 1: `App: {app_nome}`.
- Linha 2: `Plano atual: {plano_nome}`.
- Linha 3 (quando houver limite): `Uso no periodo: {usos}/{limite_qtd}`.
- Linha 4 (quando houver limite): `Restantes: {restantes}`.
- Linha 5 (quando houver): `Renova em: {janela_fim}`.

3. Card comparativo "Plano atual x Plano pago"
- Coluna A (Plano atual): lista curta com restricoes reais.
- Coluna B (Plano pago): lista curta com liberacoes reais.
- Regra: sempre mostrar 3 a 5 itens objetivos, sem promessas vagas.

4. Card "Desbloqueio imediato"
- Headline: `Libere todos os aplicativos por apenas <Valor do Plano Default>`.
- Texto de apoio: `Aumente suas chances de passar de primeira nas provas do DETRAN. Custa menos que um pastel.`
- CTA primario: `Desbloquear agora com PIX`.
- CTA secundario: `Voltar ao menu`.

5. Rodape de confianca
- Texto curto: `Seus dados e seu pagamento sao processados com seguranca.`

### Tabela de copy por motivo de bloqueio
1. `limite_atingido`
- Subtitulo: `Seu limite de uso gratuito foi atingido para este aplicativo.`
- Reforco comercial: `Libere todos os aplicativos por apenas <Valor do Plano Default> e aumente suas chances de passar de primeira nas provas do DETRAN. Custa menos que um pastel.`

2. `plano_sem_permissao`
- Subtitulo: `Este aplicativo nao esta incluido no seu plano gratuito.`
- Reforco comercial: `Libere todos os aplicativos por apenas <Valor do Plano Default>.`

3. `assinatura_inativa`
- Subtitulo: `Sua assinatura esta inativa no momento.`
- Reforco comercial: `Reative por apenas <Valor do Plano Default> e volte a estudar agora.`

4. `regra_ausente` ou `app_ausente`
- Subtitulo: `Nao foi possivel validar a regra de acesso deste app.`
- Reforco comercial: `Volte ao menu e tente novamente. Se persistir, acione o suporte.`

### Regras de UX (desktop e mobile)
1. Desktop
- Comparativo em 2 colunas.
- CTAs visiveis sem scroll longo (idealmente acima da dobra em telas comuns).

2. Mobile
- Comparativo em cards empilhados.
- CTA primario destacado e com largura total.
- CTA secundario abaixo, sem competir visualmente com o primario.

### Contrato minimo de dados para render
1. Obrigatorios
- `app_nome`, `motivo_bloqueio`, `reason`, `plano_nome`, `show_upgrade_cta`, `upgrade_url`.

2. Opcionais (quando houver)
- `limite_qtd`, `usos`, `restantes`, `janela_fim`, `comparativo_plano_atual`, `comparativo_plano_pago`.

### Criterio de pronto desta fase de copy/wireframe
1. Time de produto valida os textos por motivo.
2. Time tecnico confirma que o contrato de dados cobre todos os cenarios.
3. Layout textual aprovado para virar HTML/CSS unico.

## Ordem recomendada de rollout
1. Publicar tela unificada em 1 app piloto.
2. Validar metricas e feedback rapido.
3. Expandir para todos os apps, incluindo simulado.
4. Iniciar ciclo de otimizacao por experimentos controlados.



