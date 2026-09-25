# Contribuindo com o Blender MCP

Obrigado por se interessar em contribuir com o **Blender MCP**! Este guia cobre as diretrizes para desenvolvimento local, execução de testes e envio de pull requests.

---

## 🛠️ Ambiente de Desenvolvimento Local

### 1. Pré-requisitos
- **Python 3.10+** instalado.
- **[uv](https://docs.astral.sh/uv/)** instalado para gerenciamento de dependências e ambientes virtuais.
- **Blender 4.2 LTS+**.

### 2. Configuração Inicial

```bash
# 1. Clone seu fork do projeto
git clone https://github.com/yuri-schmaltz/mcp_blender.git
cd mcp_blender

# 2. Sincronize o ambiente virtual e dependências
uv sync --extra gui --extra test --extra dev
```

---

## 🧪 Testes e Qualidade de Código

Antes de submeter qualquer alteração, certifique-se de que a suíte completa de testes passe sem erros:

```bash
# Executar todos os testes não-visuais
uv run pytest -m "not visual"

# Executar formatação e linters (caso utilize ruff/black)
uv run ruff check .
```

---

## 🏗️ Padrões de Código e Arquitetura

1. **Modularidade**:
   - Mantenha handlers em `addon/handlers/` utilizando o decorador `@mcp_command`.
   - Mantenha componentes de interface do usuário em `addon/ui/`.
   - Não adicione chamadas bloqueantes diretamente na thread principal do Blender.
2. **Segurança de Transporte**:
   - Todas as portas de comunicação devem validar endereços de loopback (`127.0.0.1` / `localhost`).
   - Evite bibliotecas externas pesadas que não sejam estritamente essenciais para a operação do servidor.
3. **Internacionalização**:
   - Todas as novas strings da interface de usuário devem ser registradas em `translations/en.json` e `translations/pt_BR.json`.

---

## 📬 Como Submeter Contribuições

1. Crie uma branch para sua funcionalidade ou correção:
   ```bash
   git checkout -b feature/minha-melhoria
   ```
2. Realize commits claros e concisos.
3. Certifique-se de atualizar ou adicionar testes unitários relevantes em `tests/unit/`.
4. Abra um Pull Request direcionado à branch `main` do repositório [`yuri-schmaltz/mcp_blender`](https://github.com/yuri-schmaltz/mcp_blender).
