# Manual de operacao - insercao de PDF da apostila CNH

Este manual descreve como inserir/atualizar o PDF da apostila no sistema com seguranca, mantendo arquivo privado e indexacao por pagina.

---

## Objetivo
- Colocar um PDF da apostila no sistema.
- Garantir que o arquivo fique em storage privado (sem URL publica direta).
- Indexar texto por pagina para busca e navegacao.

---

## Pre-requisitos
1. Estar na raiz do projeto:
```powershell
Set-Location "f:\Nosso_Trânsito_2026\Banco_Questoes\Simulado_Digital"
```
2. Ambiente virtual e banco configurados.
3. Migration do app aplicada:
```powershell
.\.venv\Scripts\python.exe manage.py showmigrations apostila_cnh
```
4. Variavel opcional de storage privado (quando quiser override):
- `.env`:
```env
APOSTILA_CNH_PDF_ROOT=F:\Nosso_Trânsito_2026\Banco_Questoes\shared\private\apostila_cnh
```

Se nao definir a variavel, o padrao usado e:
- `BASE_DIR.parent/shared/private/apostila_cnh`

---

## Fluxo recomendado (via comando)

### 1) Primeiro cadastro/importacao do documento
Use quando o `slug` ainda nao existe no banco:

```powershell
.\.venv\Scripts\python.exe manage.py import_apostila_pdf `
  --slug apostila-cnh-brasil `
  --pdf-path "C:\arquivos\apostila_cnh_brasil.pdf" `
  --titulo "Apostila CNH Brasil" `
  --ativar
```

O que acontece:
1. Cria/atualiza `ApostilaDocumento`.
2. Copia o PDF para storage privado.
3. Extrai texto pagina a pagina.
4. Faz upsert em `ApostilaPagina` (sem duplicar).
5. Atualiza `total_paginas`.

### 2) Reindexar sem trocar arquivo
Use quando voce quer reprocessar o mesmo PDF:

```powershell
.\.venv\Scripts\python.exe manage.py import_apostila_pdf --slug apostila-cnh-brasil
```

### 3) Trocar para nova versao do PDF
Use quando chegou uma nova versao:

```powershell
.\.venv\Scripts\python.exe manage.py import_apostila_pdf `
  --slug apostila-cnh-brasil `
  --pdf-path "C:\arquivos\apostila_cnh_brasil_v2.pdf"
```

---

## Fluxo alternativo (via admin + comando)

### 1) Admin
1. Abrir `/admin/`.
2. Ir em `Apostila Documento`.
3. Criar/editar registro:
- `slug`
- `titulo`
- `arquivo_pdf`
- `ativo` (quando for o documento principal)

### 2) Indexacao por comando
Depois do upload no admin, rodar:

```powershell
.\.venv\Scripts\python.exe manage.py import_apostila_pdf --slug apostila-cnh-brasil
```

Sem esse passo, o arquivo pode estar salvo, mas sem indexacao completa por pagina.

---

## Validacao rapida apos importacao

1. Verificar contagem indexada:
```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apostila_cnh.models import ApostilaDocumento, ApostilaPagina; d=ApostilaDocumento.objects.get(slug='apostila-cnh-brasil'); print(d.total_paginas, ApostilaPagina.objects.filter(documento=d).count())"
```

2. Verificar primeira e ultima pagina:
```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apostila_cnh.models import ApostilaDocumento, ApostilaPagina; d=ApostilaDocumento.objects.get(slug='apostila-cnh-brasil'); print(ApostilaPagina.objects.filter(documento=d,numero_pagina=1).exists(), ApostilaPagina.objects.filter(documento=d,numero_pagina=d.total_paginas).exists())"
```

3. Verificar path privado do arquivo:
```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apostila_cnh.models import ApostilaDocumento; d=ApostilaDocumento.objects.get(slug='apostila-cnh-brasil'); print(d.arquivo_pdf.path)"
```

---

## Regras de seguranca
1. Nao colocar PDF em `static/`.
2. Nao commitar PDF no repositorio.
3. Nao expor URL direta do arquivo.
4. Entregar PDF ao frontend apenas por endpoint protegido com autenticacao + `require_app_access`.

---

## Erros comuns e acao recomendada

1. Erro: `Documento nao encontrado ... Use --pdf-path no primeiro import`
- Causa: slug inexistente sem arquivo inicial.
- Acao: repetir com `--pdf-path`.

2. Erro: `Arquivo PDF nao encontrado`
- Causa: caminho invalido.
- Acao: corrigir caminho absoluto/relativo.

3. Erro: `Arquivo informado nao e PDF`
- Causa: extensao diferente de `.pdf`.
- Acao: informar arquivo PDF valido.

4. Erro: `Arquivo PDF do documento nao foi encontrado no storage privado`
- Causa: registro aponta para arquivo removido.
- Acao: reimportar com `--pdf-path`.

---

## Comandos uteis
```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py showmigrations apostila_cnh
.\.venv\Scripts\python.exe manage.py import_apostila_pdf --slug apostila-cnh-brasil
```
