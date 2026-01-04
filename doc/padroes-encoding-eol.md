# 📘 Padrões de Encoding e Fim de Linha  
## VS Code + PowerShell + Git  
### Projeto: **Simulado Digital**

---

## 1. Objetivo deste documento

Este documento define o **padrão oficial de encoding e fim de linha** adotado no projeto **Simulado Digital**, garantindo:

- compatibilidade entre **Windows e Linux**
- funcionamento correto em **Django, Python, HTML, JavaScript e JSON**
- ausência de erros relacionados a **acentos**, **BOM**, **CRLF/LF misto**
- histórico Git limpo e previsível
- facilidade de manutenção a longo prazo

> Todos os colaboradores **devem seguir este padrão**.

---

## 2. Padrões adotados pelo projeto

### 2.1 Encoding
- **UTF-8 sem BOM** (obrigatório)

### 2.2 Fim de linha (EOL)
- **LF (`\n`)** para todo o código e arquivos de configuração
- **CRLF (`\r\n`) apenas para scripts Windows (`.bat`, `.cmd`)**

### 2.3 Sistemas-alvo
- Desenvolvimento: **Windows**
- Execução / Deploy: **Linux**
- CI/CD: **Linux**

---

## 3. Configuração obrigatória do VS Code

Todos os desenvolvedores devem utilizar o VS Code configurado para respeitar **UTF-8** e **LF**.

### 3.1 Configurações globais recomendadas

Abrir as configurações do VS Code:

```text
Ctrl + ,
