# Planos e assinaturas (guia rapido atualizado)

Este guia descreve como funcionam `Plano`, `Assinatura` e o controle por app (`AppModulo` / `PlanoPermissaoApp` / `UsoAppJanela`).

---

## 1) Modelo atual de acesso

No estado atual do projeto, o acesso e controlado em duas camadas:

1. Assinatura ativa do usuario
- modelo `Assinatura`
- valida status e validade temporal (`valid_until`)

2. Regra por app do plano
- modelos `AppModulo` + `PlanoPermissaoApp`
- define se cada app esta liberado e qual limite por app se houver

Consumo:
- modelo `UsoAppJanela` registra uso por usuario + app + janela.

---

## 2) Campos do Plano

Modelo: `Plano`

- `nome`
- `limite_qtd`
- `limite_periodo` (`DIARIO`, `SEMANAL`, `MENSAL`, `ANUAL`)
- `validade_dias`
- `ciclo_cobranca` (`MENSAL`, `ANUAL`, `NAO_RECORRENTE`)
- `preco`
- `ativo`

Importante no contexto atual:
- os limites globais do `Plano` nao sao suficientes para o V2 por app;
- no V2, a regra efetiva por modulo fica em `PlanoPermissaoApp`;
- no seed padrao, o plano Free ainda fornece limite base do app `simulado-digital`.

---

## 3) Campos da Assinatura

Modelo: `Assinatura`

Campos principais:
- `usuario`
- `plano`
- `status` (`ATIVO`, `EXPIRADO`, `PAUSADO`)
- `inicio`
- `valid_until`

Snapshots:
- `nome_plano_snapshot`
- `limite_qtd_snapshot`
- `limite_periodo_snapshot`
- `validade_dias_snapshot`
- `ciclo_cobranca_snapshot`
- `preco_snapshot`

Observacao importante:
- no V2 por app, limites de acesso devem vir de `PlanoPermissaoApp`, nao do snapshot global da assinatura;
- snapshots continuam uteis para trilha comercial/historica.

---

## 4) Regras por app (core do V2)

### 4.1 `AppModulo`
- catalogo persistido dos apps.
- slug canonico do simulado: `simulado-digital`.

### 4.2 `PlanoPermissaoApp`
- chave: (`plano`, `app_modulo`) unica.
- campos de regra:
  - `permitido` (bool)
  - `limite_qtd` (null = ilimitado)
  - `limite_periodo` (ou null)

### 4.3 `UsoAppJanela`
- contador por usuario/app/janela.
- usado para bloqueio quando `limite_qtd` esta definido.

---

## 5) Simulado e legado

- Simulado usa regra V2 do app `simulado-digital`.
- `SimuladoUso` (legado) permanece apenas para dual-write opcional/observabilidade.
- dual-write legado depende de `APP_ACCESS_DUAL_WRITE=1`.

---

## 6) Seed oficial de apps e permissoes

Comando:

```powershell
Set-Location "f:\\Nosso_Trânsito_2026\\Banco_Questoes\\Simulado_Digital"
.\.venv\Scripts\python.exe manage.py seed_apps_menu_access
```

O que garante:
- 8 apps em `AppModulo`;
- permissoes Free e Aprova DETRAN em `PlanoPermissaoApp`;
- migracao de slug legado `simulado-provas` -> `simulado-digital`.

---

## 7) Configuracao recomendada de planos (padrao do projeto)

Free:
- permitido somente `simulado-digital`;
- limite vindo do plano Free (ex.: 3/DIARIO).

Aprova DETRAN:
- 8 apps permitidos;
- sem limite por app (`limite_qtd=null`, `limite_periodo=null`).

---

## 8) Criar/ajustar assinatura manualmente (admin)

Passos:
1. Confirmar que o `Plano` desejado existe e esta ativo.
2. Criar/editar `Assinatura` do usuario com `status=ATIVO`.
3. Garantir `inicio` e `valid_until` coerentes com a regra comercial.
4. Confirmar que o plano da assinatura possui regras em `PlanoPermissaoApp`.

Sem regra em `PlanoPermissaoApp`:
- o app correspondente pode bloquear (comportamento esperado de seguranca).

---

## 9) Checklist de deploy (acesso por app)

1. Aplicar migrations.
2. Rodar `seed_apps_menu_access`.
3. Validar no admin:
  - 8 `AppModulo`;
  - regras Free e Aprova DETRAN em `PlanoPermissaoApp`.
4. Validar flags de ambiente conforme rollout.
5. Smoke test:
  - usuario Free;
  - usuario Aprova DETRAN;
  - menu + simulado + checkout PIX.
