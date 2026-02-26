# Manual de operacao - `corrigir_case_placas`

Este manual descreve como usar o comando `corrigir_case_placas` para corrigir divergencias de caixa alta/baixa entre nomes de imagem no banco e arquivos em `static/placas`.

---

## Objetivo
- Corrigir nomes de arquivos que diferem do banco apenas por caixa (ex.: `A-11a.png` -> `A-11A.png`).
- Evitar quebra de imagem em ambientes com filesystem case-sensitive (ex.: Linux).

---

## O que o comando faz
1. Le as questoes com `codigo_placa` preenchido.
2. Define o nome esperado da imagem por questao:
- prioridade: `imagem_arquivo`;
- fallback: `codigo_placa + ".png"`.
3. Procura arquivo correspondente em `static/placas` ignorando caixa.
4. Quando encontrar match apenas por caixa, renomeia o arquivo em 2 etapas (`origem -> temporario -> destino`) para funcionar em Windows e Linux.
5. Gera relatorio JSON com resumo da execucao (por padrao).

---

## O que o comando NAO faz
- Nao cria imagens faltantes.
- Nao altera dados do banco.
- Nao corrige nomes que diferem por mais do que caixa.
- Nao padroniza automaticamente arquivos orfaos (nao referenciados por questoes).

---

## Pre-requisitos
1. Estar na raiz do projeto:
```powershell
Set-Location "f:\Nosso_Trânsito_2026\Banco_Questoes\Simulado_Digital"
```
2. Ambiente virtual ativo ou usar o Python do `.venv`.
3. Banco PostgreSQL acessivel via `.env`.

---

## Uso rapido (recomendado)

### 1) Simular sem alterar arquivos (`dry-run`)
```powershell
.\.venv\Scripts\python.exe manage.py corrigir_case_placas --dry-run
```

### 2) Executar correcao real
```powershell
.\.venv\Scripts\python.exe manage.py corrigir_case_placas
```

### 3) Validar resultado
```powershell
.\.venv\Scripts\python.exe manage.py auditar_placas
```
Esperado apos correcao:
- `Case mismatch: 0`

---

## Parametros
- `--dry-run`
Simula os renames sem alterar arquivos.

- `--out-dir <path>`
Diretorio do relatorio de saida. Padrao: `doc/reports`.

- `--placas-dir <path>`
Sobrescreve a pasta de placas. Padrao: `<BASE_DIR>/static/placas`.

- `--write-report` / `--no-write-report`
Habilita/desabilita geracao do arquivo `placas_case_fix.json`.

---

## Relatorio gerado
Arquivo padrao:
- `doc/reports/placas_case_fix.json`

Campos principais:
- `pairs_detected`: pares detectados para ajuste de caixa.
- `actions_attempted`: tentativas de rename.
- `actions_success`: renames executados com sucesso.
- `actions_failed`: falhas no processo.
- `conflicts_count`: conflitos de mapeamento detectados.
- `successes`: lista textual dos renames aplicados.
- `failures`: lista textual das falhas.

---

## Interpretacao de saida no terminal
Exemplo:
```text
Correcao de case concluida.
Detectados: 32 | Tentativas: 32 | Sucesso: 32 | Falhas: 0 | Conflitos: 0
```

Leitura:
- `Falhas: 0` e `Conflitos: 0` indicam execucao limpa.
- Se houver falhas, consultar `placas_case_fix.json` para detalhes.

---

## Solucao de problemas
1. Erro `Pasta nao encontrada`:
- conferir `static/placas` ou informar `--placas-dir`.

2. `Conflitos > 0`:
- existem mapeamentos ambiguos de origem/destino;
- corrigir manualmente os nomes conflitantes e executar novamente.

3. `Missing` continua > 0 apos correcao:
- sao imagens realmente ausentes no diretorio;
- adicionar os arquivos faltantes e rerodar `auditar_placas`.

---

## Comandos uteis
```powershell
.\.venv\Scripts\python.exe manage.py corrigir_case_placas --help
.\.venv\Scripts\python.exe manage.py corrigir_case_placas --dry-run
.\.venv\Scripts\python.exe manage.py corrigir_case_placas
.\.venv\Scripts\python.exe manage.py auditar_placas
```
