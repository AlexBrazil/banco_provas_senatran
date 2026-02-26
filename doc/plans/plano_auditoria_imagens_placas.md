# Plano - Auditoria de imagens de placas (`simulado-digital`)

## Objetivo
Criar uma rotina Python para validar se toda questao que exige placa (campo `Questao.codigo_placa`) possui imagem correspondente em `./static/placas`, e gerar um relatorio claro de faltantes.

---

## Contexto tecnico confirmado
- Model alvo: `banco_questoes.models.Questao`.
- Campo de referencia: `codigo_placa` (`CharField`, ex.: `R-14`).
- Campo auxiliar existente: `imagem_arquivo` (normalmente derivado de `codigo_placa + ".png"` no importador).
- Pasta de imagens: `static/placas`.
- Banco configurado em Django via `.env`:
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.

---

## Escopo da auditoria
1. Buscar questoes com `codigo_placa` preenchido (nao vazio).
2. Normalizar o codigo para comparacao (sem alterar regra de caixa no nome final esperado):
- `strip()`
- `upper()`
3. Montar nomes esperados de imagem (prioridade):
- `imagem_arquivo` quando estiver preenchido.
- fallback: `<codigo_placa>.png`.
4. Ler arquivos reais de `static/placas`.
5. Comparar esperado x existente com exigencia de nome exato (`case-sensitive`).
6. Gerar relatorio de:
- faltantes por questao;
- faltantes unicos por arquivo;
- inconsistencias de cadastro (ex.: `codigo_placa` preenchido e `imagem_arquivo` vazio, quando aplicavel);
- divergencias apenas de caixa alta/baixa (ex.: esperado `R-14.png`, existente `r-14.png`).

---

## Entrega tecnica proposta
Implementar um comando de management:
- Arquivo: `banco_questoes/management/commands/auditar_placas.py`
- Execucao: `python manage.py auditar_placas`

Parametros sugeridos:
- `--out-dir doc/reports`
- `--format csv,json,md` (padrao: os 3)
- `--strict-ext` (opcional; quando ativo, exige extensao exata)
- `--strict-case` (padrao ligado; exige nome identico com caixa alta/baixa exata)

Arquivos de saida sugeridos:
- `doc/reports/placas_faltantes.csv`
- `doc/reports/placas_faltantes.json`
- `doc/reports/placas_faltantes.md`

Colunas minimas do CSV:
- `questao_id`
- `modulo`
- `numero_no_modulo`
- `codigo_placa`
- `imagem_esperada`
- `imagem_cadastrada`
- `status` (`MISSING_FILE`, `CASE_MISMATCH`, `OK`, `INCONSISTENT_DATA`)

---

## Criterios de aceite
1. O comando roda sem alterar dados do banco.
2. O relatorio lista exatamente quais arquivos estao faltando.
3. O relatorio permite localizar rapidamente a questao impactada.
4. O relatorio contem um resumo final com:
- total de questoes auditadas com `codigo_placa`;
- total OK;
- total com imagem faltante;
- total com divergencia de caixa (`CASE_MISMATCH`);
- total de nomes unicos faltantes.

---

## Plano de execucao
1. Criar comando `auditar_placas.py` com consulta ORM em `Questao`.
2. Implementar normalizacao e comparacao com arquivos de `static/placas` com regra `case-sensitive`.
3. Gerar relatorios (`csv`, `json`, `md`) em `doc/reports`.
4. Rodar comando localmente e validar amostras do resultado.
5. Ajustar criterios de comparacao caso haja convencoes extras de nome.

---

## Acesso PostgreSQL - como me liberar acesso

### Opcao A (mais simples, ambiente local ja preparado)
1. Garantir que o PostgreSQL esteja ativo.
2. Conferir `.env` com `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
3. Executar teste:
- `python manage.py check`
- `python manage.py shell -c "from banco_questoes.models import Questao; print(Questao.objects.exclude(codigo_placa='').count())"`

### Opcao B (acesso remoto/restrito com usuario somente leitura)
No PostgreSQL, criar usuario de leitura:
```sql
CREATE ROLE simulado_ro WITH LOGIN PASSWORD 'defina-uma-senha-forte';
GRANT CONNECT ON DATABASE banco_questoes TO simulado_ro;
GRANT USAGE ON SCHEMA public TO simulado_ro;
GRANT SELECT ON TABLE public.banco_questoes_questao TO simulado_ro;
```

Depois, ajustar `.env` local para esse usuario:
- `DB_NAME=banco_questoes`
- `DB_USER=simulado_ro`
- `DB_PASSWORD=...`
- `DB_HOST=<host-do-postgres>`
- `DB_PORT=5432`

Se o banco estiver fora da maquina local:
- liberar IP no firewall/security group;
- ajustar `pg_hba.conf` para permitir conexao do IP cliente.

---

## Riscos e mitigacao
1. Divergencia de nomenclatura de arquivos (`.png` x outras extensoes).
- Mitigar com opcao de comparacao flexivel por prefixo (`codigo_placa.*`) e modo estrito.

2. Dados inconsistentes de importacao (`codigo_placa` sem `imagem_arquivo`).
- Mitigar exibindo categoria `INCONSISTENT_DATA` no relatorio.

3. Ambientes com caminho de estaticos diferente.
- Mitigar usando `settings.BASE_DIR / "static" / "placas"` no comando.

4. Sistema de arquivos case-insensitive (ex.: Windows) pode mascarar erro de caixa.
- Mitigar lendo a lista real de nomes da pasta e validando string exata; se so existir match por lower-case, classificar como `CASE_MISMATCH`.

---

## Resultado esperado
Com esse comando, voce tera um relatorio objetivo de imagens faltantes em `static/placas`, com rastreabilidade por questao para correcao rapida.
