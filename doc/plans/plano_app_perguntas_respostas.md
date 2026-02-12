# Plano de implementacao - App `perguntas-respostas`

## Objetivo
Entregar o app `perguntas-respostas` como modo de estudo rapido usando a mesma base de dados do `simulado-digital`, com:
- exibicao de pergunta + alternativa correta + comentario;
- modo manual e modo automatico;
- controle de progresso para priorizar questoes ineditas por contexto de estudo;
- repeticao por "menos recentemente estudadas" quando ineditas acabarem.

---

## Decisoes ja fechadas
- Repeticao apos acabar ineditas: `menos recentemente estudadas`.
- Escopo do registro de estudo: `usuario + questao + modulo/filtro`.
- Config JSON obrigatoria do app: `tempo_min`, `tempo_max`, `tempo_default`, `qtd_default` (default 30).

---

## Restricao obrigatoria (isolamento do `simulado-digital`)
- Nao alterar nada do app `simulado-digital`.
- Se alguma necessidade do `perguntas-respostas` exigir adaptacao, criar implementacao exclusiva no proprio app.
- Reuso de codigo do `simulado-digital` so e permitido quando nao exigir nenhuma mudanca no codigo existente.

---

## Escopo funcional (MVP)
1. Tela inicial com:
- Inicio rapido (inclui quantidade de questoes, default 30).
- Montar estudo com filtros (similar ao simulado).
2. Tela de estudo:
- Enunciado.
- Imagem/placa (quando houver).
- Alternativa correta.
- Comentario.
3. Modos:
- Manual: botoes `Avancar` e `Retornar`.
- Automatico: avancar apos `tempo_entre_questoes`.
4. Persistencia por aluno:
- `tempo_entre_questoes` escolhido na UI dentro de faixa minima/maxima do JSON.
5. Leitura automatica PT-BR (navegador):
- Usa `speechSynthesis`.
- Se houver imagem/placa: primeira frase sintetizada deve orientar observacao da tela.

Fora de escopo inicial:
- Exportacao de historico.
- Estatisticas avancadas por desempenho.
- Sincronizacao entre dispositivos em tempo real.

---

## Regras didaticas e de selecao
1. Ordem principal:
- seguir ordem natural do banco (curso/modulo/numero_no_modulo), sem randomizacao.
2. Prioridade:
- primeiro questoes ineditas no contexto selecionado.
3. Quando ineditas acabarem:
- repetir as menos recentemente estudadas no mesmo contexto.
4. Contexto de estudo:
- definido por modulo/filtros escolhidos na sessao.

---

## Modelagem de dados proposta
Criar modelo dedicado ao historico do app (ex.: `PerguntaRespostaEstudo`):
- `usuario` (FK auth user)
- `questao` (FK Questao)
- `contexto_hash` (char/indexado, derivado de modulo/filtros)
- `contexto_json` (json com filtros aplicados para auditoria)
- `primeiro_estudo_em` (datetime)
- `ultimo_estudo_em` (datetime)
- `vezes_estudada` (int)

Restricao sugerida:
- unique (`usuario`, `questao`, `contexto_hash`)

Observacao:
- Nao reaproveitar `UsoAppJanela` para isso; ele mede acesso por limite, nao progresso didatico por questao.

Persistencia de preferencia de tempo:
- opcao A (simples): novo campo em perfil/config do usuario (se existir estrutura).
- opcao B (recomendada para baixo acoplamento): modelo proprio `PerguntaRespostaPreferenciaUsuario` com:
  - `usuario` unique
  - `tempo_entre_questoes_segundos`
  - `modo_automatico_ativo` (opcional)

---

## Configuracao JSON do app
Novo arquivo (sugestao): `config_perguntas_respostas.json`

Campos minimos:
- `tempo_min`
- `tempo_max`
- `tempo_default`
- `qtd_default`

Validacoes:
- `tempo_min <= tempo_default <= tempo_max`
- `qtd_default >= 1`

---

## UX e comportamento de voz (automatico)
1. Inicio do modo automatico deve exigir interacao explicita do usuario (restricoes de autoplay do navegador).
2. Pipeline por questao:
- cancelar fala pendente;
- se houver imagem/placa: sintetizar primeiro "Esta questao contem imagem/placa. Observe a tela.";
- pausa curta;
- ler enunciado;
- ler alternativa correta;
- ler comentario;
- aguardar tempo configurado;
- avancar automaticamente.
3. Troca manual de questao durante fala:
- cancelar locucao atual imediatamente e reiniciar pipeline da nova questao.

---

## Etapas de implementacao

### Etapa 1 - Estrutura e configuracao
- Criar loader/config do app via JSON.
- Criar URLs, view inicial e template base do app.
- Garantir protecao de acesso via `require_app_access("perguntas-respostas")`.

Aceite:
1. Rota do app abre para usuario liberado.
2. Config JSON carrega com fallback seguro.
3. Sem regressao nas rotas atuais.

### Etapa 2 - Inicio rapido + filtros
- Reaproveitar logica de selecao de questoes do simulado (adaptada para estudo).
- Incluir campo de quantidade com default do JSON.
- Persistir contexto da sessao de estudo.

Aceite:
1. Inicio rapido gera sessao com N questoes.
2. Fluxo com filtros gera sessao coerente.
3. Ordem natural do banco respeitada.

### Etapa 3 - Tela de estudo manual
- Exibir pergunta, imagem/placa, resposta certa e comentario.
- Navegacao `Avancar`/`Retornar`.
- Registrar estudo por `usuario + questao + contexto`.

Aceite:
1. Registro criado/atualizado a cada questao visitada.
2. Botoes manual funcionam sem quebrar sessao.
3. Dados corretos exibidos em todas as questoes.

### Etapa 4 - Politica de ineditas e repeticao LRU
- Selecionar primeiro ineditas do contexto.
- Ao acabar ineditas, selecionar menos recentemente estudadas.

Aceite:
1. Usuario novo recebe 100% ineditas.
2. Usuario com historico recebe ineditas restantes primeiro.
3. Sem ineditas, ordem passa a LRU por contexto.

### Etapa 5 - Modo automatico + preferencia persistente
- Implementar tempo entre questoes com slider/input.
- Respeitar `tempo_min/max/default`.
- Persistir valor por usuario.
- Implementar autoavanco.

Aceite:
1. Valor alterado persiste para novo login.
2. Autoavanco respeita tempo definido.
3. Valor fora da faixa e rejeitado/normalizado.

### Etapa 6 - Sintese de voz PT-BR
- Implementar leitura com Web Speech API.
- Tratar aviso inicial para questao com imagem/placa.
- Garantir cancelamento limpo ao navegar/trocar modo.

Aceite:
1. Leitura ocorre apos acao do usuario.
2. Questao com imagem/placa reproduz aviso antes do enunciado.
3. Nao ha sobreposicao de falas.

### Etapa 7 - Testes e validacao final
- Testes de backend (selecao, historico, LRU, persistencia de tempo).
- Testes de views/rotas.
- Checklist manual de UX (manual/automatico/voz/mobile).

Aceite:
1. `manage.py check` sem erros.
2. Testes novos passando.
3. Fluxos criticos aprovados manualmente.

---

## Riscos e mitigacoes
1. Divergencia de regras entre simulado e perguntas-respostas.
- Mitigar com servico/funcao compartilhada para selecao base de questoes.

2. Limites de voz por navegador/dispositivo.
- Mitigar com fallback visual e toggle de voz; nao bloquear estudo se voz indisponivel.

3. Crescimento de historico de estudo.
- Mitigar com indices em (`usuario`, `contexto_hash`, `ultimo_estudo_em`).

---

## Checklist de aceite do plano (global)
1. App entrega estudo rapido com resposta correta e comentario.
2. Manual e automatico funcionam com persistencia de tempo por aluno.
3. Voz PT-BR funciona com aviso inicial em questao com imagem/placa.
4. Politica de ineditas + repeticao LRU por contexto esta valida.
5. Acesso por plano e regressao dos apps existentes permanecem intactos.
