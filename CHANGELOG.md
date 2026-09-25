# Changelog

All notable changes to this project are documented here. The format is
loosely based on [Keep a Changelog](https://keepachangelog.com/) and the
project follows [Semantic Versioning](https://semver.org/) where
practical.

## [Unreleased]

Nothing yet.

## [2.14.0] — 2026-09-25

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
