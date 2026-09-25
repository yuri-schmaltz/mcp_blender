# Guia de Troubleshooting - Blender MCP

Este documento reúne soluções para problemas comuns de conexão, inicialização e execução do **Blender MCP**.

---

## 1. Conexão Recusada ou Servidor Desconectado

### Sintoma
- O cliente MCP (Cursor, Claude, LM Studio) relata: `Connection refused on localhost:9876` ou `Failed to connect to Blender`.
- O ícone na barra de status do Blender está desligado (⚪).

### Soluções
1. **Verifique se o Addon está ativo**:
   - No Blender, vá em **Edit > Preferences > Add-ons** e verifique se o **Blender MCP** está marcado como ativo.
2. **Inicie o Servidor no Blender**:
   - Clique no ícone de círculo na **Barra de Status** inferior do Blender ou abra o painel lateral (`N > MCP`) e clique em **Start Server**.
   - O ícone deve mudar para verde/ativo (🟢).
3. **Verifique a Porta Utilizada**:
   - Por padrão a porta é `9876`. Se estiver ocupada por outro processo:
     - No Blender: altere a porta no painel do MCP.
     - No cliente MCP: configure a variável de ambiente `BLENDER_PORT=<nova_porta>`.

---

## 2. Dependências ou Erro de Inicialização do `uv`

### Sintoma
- O comando `uv run blender-mcp` relata erro de comando não encontrado.

### Soluções
- Instale o `uv` via terminal:
  - **Linux/macOS**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Certifique-se de que o diretório de instalação do `uv` (`~/.local/bin` ou `%USERPROFILE%\.local\bin`) está no seu `PATH`.
- Execute `uv sync` na raiz do projeto para criar o ambiente virtual com todas as dependências.

---

## 3. Limpeza de Cache de Modelos e Texturas

### Sintoma
- Texturas do Poly Haven ou modelos baixados corrompidos.

### Soluções
Execute o snippet Python no console interativo do Blender:

```python
from addon.utils.cache import AssetCache
cache = AssetCache()
cache.clear()
print("Cache limpo com sucesso!")
```

Ou clique no botão **Clear Cache** dentro do painel lateral do addon (`View3D > Sidebar > MCP`).

---

## 4. Diagnóstico Completo via MCP

Você pode invocar o diagnóstico integrado via terminal para verificar a integridade da comunicação:

```bash
uv run blender-mcp --doctor
```

O comando irá checar a resolução do host, disponibilidade da porta e prontidão da API `bpy`.
