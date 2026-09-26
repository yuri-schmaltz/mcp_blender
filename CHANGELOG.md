# Changelog

All notable changes to this project are documented here. The format is
loosely based on [Keep a Changelog](https://keepachangelog.com/) and the
project follows [Semantic Versioning](https://semver.org/) where
practical.

## [Unreleased]

Nothing yet.

## [2.18.0] — 2026-09-26

**Comprehensive Modernization: PEP 678 Diagnostic Notes, MCP Prompts, Modern WebUI Dashboard & Telemetry.**

### Added
- **PEP 678 Diagnostic Notes (`addon/core/router.py`)**: Contexto de execução enriquecido nas exceções (modo atual do Blender, objeto ativo, contagem de seleções, cena ativa) para autorecuperação cirúrgica dos modelos LLM.
- **Dynamic MCP Prompts (`src/blender_mcp/server.py`)**:
  - `studio_lighting_setup`: fluxo de iluminação profissional de 3 pontos e produto.
  - `procedural_geometry_pipeline`: pipeline de Geometry Nodes não destrutivo.
  - `print3d_preparation_pipeline`: fluxo de validação dimensional, reparo manifold e layout para impressão 3D.
  - `spatial_layout_composition`: enquadramento e assentamento espacial.
- **WebUI Modernization & Health Telemetry (`addon/webui_server.py`, `addon/ui/web/index.html`)**:
  - Novo endpoint `/api/status` fornecendo telemetria em tempo real (versão do Blender, Python, contagem de ferramentas e estado de renderização).
  - Badges de telemetria ao vivo integradas ao cabeçalho da interface WebUI.

### Changed
- **Error Handling**: Formato de resposta de erro enriquecido com objeto `diagnostic` estruturado sem quebrar compatibilidade reversa.

**Modern Python Base Upgrade (Python >=3.11, targeting 3.12+).**

### Changed
- **Python Runtime Baseline**: Elevada a versão mínima do Python de `>=3.10` para `>=3.11` (alinhado com o padrão de extensões do Blender 4.2 LTS / 5.2+).
- **Linter & Tooling Upgrades**: Ruff, MyPy e Black reconfigurados para `py312`, aproveitando melhorias de performance do compilador CPython adaptativo e tipagem nativa moderna.
- **AsyncIO & Event Loop**: Benefício direto das otimizações de `asyncio` e parsing de JSON do Python 3.12+ na camada FastMCP.

## [2.16.0] — 2026-09-25

**Native Local AI 3D Mesh Generation & Importer Pipeline (TripoSR, Trellis, Hunyuan3D).**

### Added
- **Local AI 3D Mesh Handlers (`addon/handlers/ai_3d_generator.py`)**:
  - `import_generated_mesh`: importa malhas geradas localmente (`.glb`, `.gltf`, `.obj`) com suporte automático a escala, rotação e assentamento no chão (`snap_ground`).
  - `generate_mesh_local_ai`: dispara a sintetização de malhas 3D em endpoints locais de GPU (TripoSR, Trellis ou Hunyuan3D) e importa diretamente para o Blender sem passos manuais.
- **FastMCP Integration**: Ferramentas expostas diretamente para clientes LLM em `src/blender_mcp/server.py` e catalogadas em `addon/tool_schemas.py`.

## [2.15.0] — 2026-09-25

**Semantic Spatial Placement, Procedural Geometry Nodes & System Prompt Presets.**

### Added
- **Spatial Reasoning Tools (`addon/handlers/spatial_tools.py`)**:
  - `snap_to_ground`: assenta automaticamente o ponto mais baixo do objeto rente ao chão (`Z=0.0`).
  - `place_object_on_top`: posiciona o objeto filho perfeitamente sobre o topo do objeto pai usando bounding boxes mundiais sem colisões ou flutuação.
  - `align_objects`: alinha múltiplos objetos por eixos (`X`, `Y`, `Z`) e modos (`CENTER`, `MIN`, `MAX`).
- **Procedural Geometry Nodes (`addon/handlers/geometry_nodes.py`)**:
  - `add_geometry_nodes_scatter`: dispersão procedural de instâncias através de nó `GeometryNodeDistributePointsOnFaces` e `GeometryNodeInstanceOnPoints`.
  - `create_procedural_wire_curve`: criação procedural de curvas de cabos/fios com curvatura física realista entre dois pontos 3D.
- **System Prompt Generator**:
  - Novo operador `blendermcp.copy_system_prompt` nas preferências (`Clients & Diagnostics`) para carregar o modelo no LM Studio / Claude com diretrizes exatas de automação do Blender.
- **FastMCP Server Registration**:
  - Todas as novas ferramentas espaciais e procedurais expostas na camada FastMCP em `src/blender_mcp/server.py` e catalogadas em `addon/tool_schemas.py`.

**Status bar integration, UI streamlining, built-in chat removal & author consolidation.**

### Added
- **Status Bar Integration**: Indicador de status compacto e elegante no rodapé do Blender (`bpy.types.STATUSBAR_HT_header`) exibindo `RADIOBUT_ON` quando ativo e `RADIOBUT_OFF` quando inativo.
- **Toggle Operator (`blendermcp.toggle_server`)**: Alternância de ligar/desligar o servidor MCP com um único clique diretamente na barra de status, com redesenho forçado imediato da UI (`STATUSBAR` e `VIEW_3D`).
- **Unit Test Coverage**: Adicionado [`tests/unit/test_statusbar.py`](file:///home/yuri/Documentos/blender_mcp/tests/unit/test_statusbar.py), elevando a suíte para 186 testes com 100% de sucesso.
- **Robust Documentation**: Reestruturação e modernização de [`README.md`](file:///home/yuri/Documentos/blender_mcp/README.md), [`CONTRIBUTING.md`](file:///home/yuri/Documentos/blender_mcp/CONTRIBUTING.md), [`docs/TROUBLESHOOTING.md`](file:///home/yuri/Documentos/blender_mcp/docs/TROUBLESHOOTING.md) e [`docs/RUNBOOK.md`](file:///home/yuri/Documentos/blender_mcp/docs/RUNBOOK.md).

### Changed
- **Button Renaming**: Botão principal alterado de `"Connect to LLM"` para `"Start Server"` (com suporte multilíngue em inglês e português).
- **Author & License Consolidation**: Licença MIT e metadados (`pyproject.toml`, `blender_manifest.toml`, `__init__.py`) atribuídos exclusivamente a Yuri Schmaltz.

### Removed
- **Built-in AI Chat**: Removido sub-painel de chat interno e excluído `addon/handlers/llm_handler.py`.
- **Dependencies Cleaned**: Removido `litellm` e mais de 25 dependências transitivas pesadas, eliminando potenciais alertas de segurança e reduzindo drasticamente o tamanho do pacote.
- **Redundant Labels**: Removido o texto `"Connected · Port 9876"` do painel lateral.

## [2.13.0] — 2026-09-24

**Dependency security resolution & packaging release.**

### Security
- **`litellm>=1.84.0`** — fecha as 15 vulnerabilidades restantes adiadas na v2.12.1 (auth bypass, SSTI e RCE). Todas as dependências agora estão alinhadas com o baseline de segurança.
- Atualizado o comando de fallback de instalação runtime no Blender ([`addon/utils/helpers.py`](file:///home/yuri/Documentos/blender_mcp/addon/utils/helpers.py)) para exigir `requests>=2.32.4` e `litellm>=1.84.0`.

### Packaging & Compatibility
- **Extension Packaging**: geração validada do pacote de extensão padrão do Blender via [`scripts/package_extension.py`](file:///home/yuri/Documentos/blender_mcp/scripts/package_extension.py) gerando `dist/mcp_blender_2.13.0.zip`.
- **Test Fix**: corrigido mock de `bpy.types.AddonPreferences` nos testes unitários ([`tests/unit/test_upstream_bug_fixes.py`](file:///home/yuri/Documentos/blender_mcp/tests/unit/test_upstream_bug_fixes.py)). 165/165 testes unitários passando.

## [2.12.1] — 2026-07-15

**Security patch.** Bumps de lower-bound em dependências para fechar
15 das 29 vulnerabilidades reportadas pelo Dependabot. Sem mudança de
código, sem breaking change. 165/165 testes passando.

### Security (resolved via dep bumps)

- **`requests>=2.32.4`** — fecha `.netrc` credentials leak
  ([GHSA-9hjg-9r4m-mvj7](https://github.com/advisories/GHSA-9hjg-9r4m-mvj7))
  e outras 7 moderate. Resolve: 8 vulnerabilidades.
- **`mcp[cli]>=1.23.0,<2.0.0`** — fecha DNS rebinding protection que
  não vinha habilitada por default
  ([GHSA-9h52-p55h-vw2f](https://github.com/advisories/GHSA-9h52-p55h-vw2f))
  e mais 2 high/DoS. Resolve: 3 vulnerabilidades.
- **`pytest>=9.0.3`** — fecha vulnerable tmpdir handling
  ([GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g)).
  Resolve: 1 vulnerabilidade.
- **`black>=26.3.1`** — fecha arbitrary file write via unsanitized
  cache filename
  ([GHSA-3936-cmfr-pm3m](https://github.com/advisories/GHSA-3936-cmfr-pm3m))
  e mais 2 moderate. Resolve: 3 vulnerabilidades.

### Deferred

- **`litellm>=1.84.0`** — 15 vulnerabilidades restantes (3 high em auth
  bypass, várias em SSTI/RCE) ficam para `v2.13.0`. É um salto de 92
  minor versions com mudanças de API; vai como release dedicado.

### Notes

- Sem mudança de código, sem mudança de protocolo
- 165/165 unit tests passando após o bump
- Ver `DEPENDABOT_TRIAGE.md` no repo para análise completa

[2.12.1]: https://github.com/yuri-schmaltz/mcp-blender/compare/v2.12.0...v2.12.1

## [2.12.0] — 2026-07-15

**Hardening release.** All changes are opt-in via environment
variables; single-user loopback setups behave exactly as before. No
protocol break.

### Security
- **Token authentication** on the socket protocol: when
  `BLENDER_MCP_TOKEN` is set, the addon rejects every command whose
  `X-BlenderMCP-Token` header does not match (constant-time
  comparison). Both sides opt in together; no breaking change for
  existing single-user loopback setups.
- **Hard payload cap** (`BLENDER_MCP_MAX_PAYLOAD_BYTES`, default 4 MiB):
  the addon refuses commands larger than the cap, protecting Blender
  from runaway clients. The cap is enforced on the wire *before* JSON
  parsing.
- **Public-bind guard**: the CLI refuses to bind to a non-loopback
  address unless `BLENDER_MCP_ALLOW_PUBLIC_BIND=1` (or the matching
  `--allow-public-bind` flag) is set. Refused by default.

### Fixed
- `addon/handlers/scene_tools.py::get_scene_info` no longer crashes on
  Blender 3.5+: the removed `scene.objects.active` is replaced with a
  defensive helper that prefers the modern
  `bpy.context.view_layer.objects.active` and falls back to the legacy
  attribute when needed.
- `__init__.py::BlenderMCPPreferences.bl_idname` is now resolved via a
  three-step fallback (`__package__` → `blender_manifest.toml` `id` →
  directory name of `__init__.py`). Resolves the
  `preferences is None` issue under legacy flat installs.

### Added
- New CLI flags: `--version`, `--check-config`, `--allow-public-bind`,
  and a section-prefixed `--doctor` (`[OK]`, `[WARN]`, `[FAIL]`).
- `PLAN.md` documenting the hardening roadmap and the rationale for
  each change.
- `SECURITY.md` rewritten with a concrete threat model and a
  hardening checklist.
- `.github/ISSUE_TEMPLATE/bug.yml` and `feature.yml`.
- `.pre-commit-config.yaml` with ruff, format, and a fast pytest gate.
- `tests/unit/test_transport_safety.py` (15 tests) and
  `tests/unit/test_addon_transport_safety.py` (8 tests) for the
  shared safety helpers.
- `tests/unit/test_upstream_bug_fixes.py` (7 tests) for the two
  Blender 4.x compat fixes.
- `tests/e2e/headless_runner.py`, `smoke_security.py`, and
  `test_headless_round_trip.py` exercising the new hardening against
  a real Blender 5.1.2 process. The harness transparently handles
  the user-addons path change (4.x uses ``scripts/addons``,
  5.0+ uses ``scripts/addons/modules``) and the renamed
  ``addon_utils.enable`` keyword.

### Changed
- `pyproject.toml`: fixed broken `modelcontextprotocol/...` URLs,
  added `Yuri Schmaltz` to the `authors` list, kept `Upstream` URL
  pointing at the canonical `ahujasid/blender-mcp`.
- `.env.example`: documented every env var the project actually reads,
  with new entries for the hardening knobs.

## [2.11.0] — Upstream baseline

Inherited from `ahujasid/blender-mcp` v2.11.0. See upstream CHANGELOG
for the full list of features inherited unchanged.

[2.12.0]: https://github.com/yuri-schmaltz/mcp-blender/compare/v2.11.0...v2.12.0
[2.11.0]: https://github.com/yuri-schmaltz/mcp-blender/releases/tag/v2.11.0
