# Runbook Operacional - Blender MCP

Procedimentos para operação, execução, testes contínuos e diagnósticos do **Blender MCP**.

---

## 1. Inicialização e Modos de Operação

### Execução Padrão
1. Inicie o Blender com o addon habilitado.
2. Inicie o servidor interno através do ícone da barra de status ou painel `MCP` lateral.
3. No terminal (ou através de um cliente MCP como Cursor/Claude):
   ```bash
   uv run blender-mcp
   ```

### Execução com Interface Gráfica de Configuração (PySide6)
Permite configurar variáveis de ambiente, portas e níveis de log de forma visual:
```bash
uv run blender-mcp-gui
```

### Execução com Logging Detalhado
Para depurar chamadas de ferramentas e payloads de comandos:
```bash
export BLENDER_MCP_LOG_LEVEL=DEBUG
export BLENDER_MCP_LOG_HANDLER=file
uv run blender-mcp
```
Os registros serão gravados em `blender_mcp.log`.

---

## 2. Rotinas de Verificação de Qualidade

Execute a suíte antes de qualquer merge ou release:

```bash
# 1. Testes de unidade e integração
uv run pytest -m "not visual"

# 2. Teste específico de ponta a ponta (requer Blender instalado no sistema)
uv run pytest tests/e2e/test_e2e_addon_server.py

# 3. Verificação de integridade da barra de status e toggle
uv run pytest tests/unit/test_statusbar.py
```

---

## 3. Procedimento de Release

1. **Atualizar Versão**:
   - Atualizar a versão em `pyproject.toml`
   - Atualizar a versão em `blender_manifest.toml`
   - Atualizar a versão em `__init__.py` (`bl_info["version"]`)
2. **Atualizar Changelog**:
   - Registrar as novas adições e correções em `CHANGELOG.md`
3. **Executar Testes**:
   - Garantir 100% de testes aprovados em ambiente limpo (`uv sync && uv run pytest -m "not visual"`).
4. **Empacotamento**:
   - Gerar os pacotes de distribuição com `uv build`.
