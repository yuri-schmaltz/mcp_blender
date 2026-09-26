"""Blender Extension entrypoint for Blender MCP."""
# ruff: noqa: N999

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)

_ollama_models_cache = []
_ollama_fetch_time = 0


def fetch_ollama_models_thread(base_url):
    global _ollama_models_cache, _ollama_fetch_time
    try:
        url = base_url.rstrip("/") + "/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1.0) as response:
            data = json.loads(response.read().decode())
            models = [(m["name"], m["name"], "") for m in data.get("models", [])]
            if models:
                _ollama_models_cache = models
                _ollama_fetch_time = time.time()
    except Exception:
        pass


def get_ollama_items(self, context):
    global _ollama_models_cache, _ollama_fetch_time

    base_url = self.llm_base_url if self.llm_base_url else "http://localhost:11434"

    # If cache empty, perform quick sync fetch
    if not _ollama_models_cache:
        try:
            with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=2) as response:
                data = json.load(response)
                _ollama_models_cache = [(m["name"], m["name"], "") for m in data.get("models", [])]
                _ollama_fetch_time = time.time()
        except Exception:
            pass

    # Refresh in background if stale (>60s)
    if time.time() - _ollama_fetch_time > 60:
        threading.Thread(target=fetch_ollama_models_thread, args=(base_url,), daemon=True).start()

    res = list(_ollama_models_cache)
    res.append(("MANUAL", "Type Manually...", ""))
    return res


_custom_models_cache = []
_custom_fetch_time = 0


def fetch_custom_models_thread(base_url):
    global _custom_models_cache, _custom_fetch_time
    try:
        url = base_url.rstrip("/") + "/models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=1.0) as response:
            data = json.loads(response.read().decode())
            models = [(m["id"], m["id"], "") for m in data.get("data", [])]
            if models:
                _custom_models_cache = models
                _custom_fetch_time = time.time()
    except Exception:
        pass


def get_custom_items(self, context):
    global _custom_models_cache, _custom_fetch_time
    base_url = self.llm_base_url if self.llm_base_url else "http://localhost:1234/v1"

    if time.time() - _custom_fetch_time > 10:
        _custom_fetch_time = time.time()
        threading.Thread(target=fetch_custom_models_thread, args=(base_url,), daemon=True).start()

    res = list(_custom_models_cache)
    res.append(("MANUAL", "Type Manually...", ""))
    return res


def _resolve_addon_id():
    """Return a stable id for the AddonPreferences ``bl_idname``.

    Three fallbacks, in order of preference:

    1. ``__package__`` when Blender loaded us as a real Python package
       (i.e. as an extension, where ``__package__`` is set to the
       extension id, e.g. ``"mcp_blender"``).
    2. The id declared in ``blender_manifest.toml`` when present
       alongside ``__init__.py`` (extension mode with package stripped).
    3. The directory name hosting ``__init__.py``. This covers the
       legacy flat install where ``__package__`` is the empty string
       and the addon is installed as ``<user_addons>/<name>/__init__.py``.

    The fallback chain guarantees a non-empty id, which is what
    ``bpy.context.preferences.addons[id].preferences`` needs to find us.
    """
    pkg = __package__
    if pkg:
        return pkg

    # 2. Read blender_manifest.toml next to __init__.py when present.
    manifest = Path(__file__).resolve().parent / "blender_manifest.toml"
    if manifest.is_file():
        try:
            import tomllib  # py3.11+

            with manifest.open("rb") as fh:
                data = tomllib.load(fh)
            mid = data.get("id")
            if isinstance(mid, str) and mid:
                return mid
        except Exception:
            pass  # tomllib missing or malformed manifest -- fall through.

    # 3. Legacy flat install: derive from the directory name.
    return Path(__file__).resolve().parent.name or "blender_mcp"


class BlenderMCPPreferences(bpy.types.AddonPreferences):
    bl_idname = _resolve_addon_id()

    port: IntProperty(
        name="Default Port",
        description="Default port for the BlenderMCP socket server",
        default=9876,
        min=1024,
        max=65535,
    )

    webui_port: IntProperty(
        name="WebUI Port",
        description="Port for the embedded HTML WebUI server",
        default=8080,
        min=1024,
        max=65535,
    )

    allow_code_execution: BoolProperty(
        name="Allow Remote Code Execution",
        description="WARNING: Allows the LLM to execute arbitrary Python code. Enable only if you trust the requests",
        default=False,
    )

    sketchfab_api_key: StringProperty(
        name="Sketchfab API Key",
        subtype="PASSWORD",
        description="Global Sketchfab API key",
        default="",
    )

    blenderkit_api_key: StringProperty(
        name="BlenderKit API Token",
        subtype="PASSWORD",
        description="Global BlenderKit API token",
        default="",
    )

    client_target: EnumProperty(
        name="Target Client",
        items=[
            ("lm_studio", "LM Studio", "Local LLM via LM Studio"),
            ("ollama", "Ollama", "Local LLM via Ollama"),
            ("custom", "Custom", "Generic OpenAI-compatible API"),
        ],
        default="lm_studio",
    )

    llm_provider: EnumProperty(
        name="LLM Provider",
        items=[
            ("OLLAMA", "Ollama (Local)", "Use local Ollama instance"),
            ("CUSTOM", "Custom / LM Studio (Local)", "Use any OpenAI-compatible local API"),
        ],
        default="OLLAMA",
    )

    llm_model_ollama: EnumProperty(
        name="Ollama Model",
        description="Select an installed Ollama model",
        items=get_ollama_items,
    )

    llm_model_custom_enum: EnumProperty(
        name="LM Studio / Custom Model",
        description="Select an available model from the custom server",
        items=get_custom_items,
    )

    llm_model_custom: StringProperty(
        name="Manual Model Name",
        description="Type the model name (e.g., llama3, mistral, etc.)",
        default="llama3",
    )

    llm_base_url: StringProperty(
        name="Base URL",
        description="Base URL for local providers (e.g., http://localhost:11434 for Ollama, http://localhost:1234/v1 for LM Studio)",
        default="",
    )

    llm_api_key: StringProperty(
        name="API Key",
        subtype="PASSWORD",
        description="API Key for the selected LLM Provider",
        default="",
    )

    mcp_tool_profile: EnumProperty(
        name="MCP Tool Profile",
        description="Filter tools exposed to the AI client to optimize prompt context and speed",
        items=[
            ("ALL", "Full (All Tools)", "Expose all 73 tools to the AI"),
            ("MODELING", "Modeling & Layout", "Expose only essential and modeling/transform tools"),
            (
                "MATERIALS",
                "Materials & Studio",
                "Expose only PBR materials, textures, and studio lighting tools",
            ),
            (
                "PHYSICS",
                "Mechanics & Simulation",
                "Expose only rigid body, physics constraints, and joint simulation tools",
            ),
            (
                "PRINTING",
                "3D Printing & CAD",
                "Expose only mesh analysis, repair, and 3D printing tools",
            ),
        ],
        default="ALL",
    )

    # Integration Toggles
    use_polyhaven: BoolProperty(
        name="Use Poly Haven",
        description="Enable Poly Haven asset integration",
        default=False,
    )
    use_ambientcg: BoolProperty(
        name="Use AmbientCG",
        description="Enable AmbientCG asset integration",
        default=False,
    )
    use_sketchfab: BoolProperty(
        name="Use Sketchfab",
        description="Enable Sketchfab asset integration",
        default=False,
    )
    use_blenderkit: BoolProperty(
        name="Use BlenderKit",
        description="Enable BlenderKit asset integration",
        default=False,
    )

    # Navigation tab
    active_tab: EnumProperty(
        name="Tab",
        items=[
            ("SERVER", "Server & Security", "Server port, WebUI and execution permissions", "SETTINGS", 0),
            ("ASSETS", "Integrations", "External 3D asset and material providers", "WORLD", 1),
            ("CLIENTS", "Clients & Diagnostics", "MCP client presets and troubleshooting tools", "CONSOLE", 2),
        ],
        default="SERVER",
    )

    def draw(self, context):
        layout = self.layout

        # --- Top Tab Bar ---
        row = layout.row(align=True)
        row.prop(self, "active_tab", expand=True)
        layout.separator()

        # =====================================================================
        # TAB 1: Server & Security
        # =====================================================================
        if self.active_tab == "SERVER":
            box = layout.box()
            box.label(text="Network Ports", icon="NETWORK_DRIVE")
            row = box.row(align=True)
            row.prop(self, "port", text="MCP Socket Port")
            row.prop(self, "webui_port", text="WebUI Port")

            box = layout.box()
            box.label(text="Tool Optimization", icon="TOOL_SETTINGS")
            box.prop(self, "mcp_tool_profile", text="Tool Profile")

            box = layout.box()
            box.label(text="Security & Execution", icon="LOCKED")
            box.prop(self, "allow_code_execution", text="Allow Remote Python Execution")
            if self.allow_code_execution:
                alert_box = box.box()
                alert_box.alert = True
                alert_box.label(
                    text="CAUTION: External AI models can execute arbitrary Python scripts in Blender.",
                    icon="ERROR",
                )

        # =====================================================================
        # TAB 2: Asset Integrations
        # =====================================================================
        elif self.active_tab == "ASSETS":
            box = layout.box()
            box.label(text="Asset & Material Providers", icon="ASSET_MANAGER")

            grid = box.grid_flow(columns=2, even_columns=True, even_rows=False, align=True)
            grid.prop(self, "use_polyhaven", text="Poly Haven (Free HDRIs & Textures)", icon="IMAGE_DATA")
            grid.prop(self, "use_ambientcg", text="AmbientCG (Free PBR Materials)", icon="MATERIAL")
            grid.prop(self, "use_sketchfab", text="Sketchfab (Models)", icon="MESH_MONKEY")
            grid.prop(self, "use_blenderkit", text="BlenderKit (Library)", icon="OUTLINER_OB_MESH")

            # Conditional API credentials only when enabled
            if self.use_sketchfab or self.use_blenderkit:
                box.separator()
                col = box.column(align=True)
                if self.use_sketchfab:
                    col.prop(self, "sketchfab_api_key", text="Sketchfab API Key")
                if self.use_blenderkit:
                    col.prop(self, "blenderkit_api_key", text="BlenderKit Token")

        # =====================================================================
        # TAB 3: Clients & Diagnostics
        # =====================================================================
        elif self.active_tab == "CLIENTS":
            box = layout.box()
            box.label(text="MCP Client Configuration", icon="CONSOLE")
            row = box.row(align=True)
            row.prop(self, "client_target", text="Target Client")
            row.operator("blendermcp.copy_mcp_client_config", text="Copy Config Snippet", icon="COPYDOWN")

            row_prompt = box.row()
            row_prompt.operator("blendermcp.copy_system_prompt", text="Copy Recommended System Prompt (LM Studio / Claude)", icon="TEXT")

            box = layout.box()
            box.label(text="Diagnostics & Tools", icon="INFO")
            row = box.row(align=True)
            row.operator("blendermcp.health_check", text="Run Health Check", icon="CHECKMARK")
            row.operator("blendermcp.open_logs", text="Open Logs", icon="TEXT")
            row.operator("blendermcp.clear_cache", text="Clear Cache", icon="TRASH")


# =============================================================================
# Dynamic addon module loading
# =============================================================================
def _load_addon_module():
    """Load addon.py and ensure it has the correct package context for relative imports."""
    addon_path = Path(__file__).with_name("addon.py")
    # Use the current package name if available (Blender 4.2+ Extension mode)
    pkg = __package__ if __package__ else "blender_mcp"

    spec = importlib.util.spec_from_file_location(f"{pkg}.addon_entry", addon_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load addon module from {addon_path}")

    module = importlib.util.module_from_spec(spec)
    # Crucial: set __package__ so relative imports like 'from .addon import ...' work
    module.__package__ = pkg
    # Register in sys.modules so submodules (UI, operators) can find it
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bl_info = {
    "name": "Blender MCP",
    "author": "Yuri Schmaltz",
    "version": (2, 18, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > BlenderMCP",
    "description": "Connect Blender to local LLM clients via MCP",
    "category": "Interface",
}

# Cache the loaded module to avoid re-executing on unregister
_addon_mod = None


def register():
    global _addon_mod

    # 1. Register Preferences FIRST from __init__.py (guaranteed correct __package__)
    bpy.utils.register_class(BlenderMCPPreferences)

    # 2. Load and register the rest of the addon
    print("BlenderMCP: Loading addon module...")
    _addon_mod = _load_addon_module()
    _addon_mod.register()


def unregister():
    global _addon_mod
    if _addon_mod is None:
        _addon_mod = _load_addon_module()
    _addon_mod.unregister()

    # Clean up WebUI server if running
    if hasattr(bpy.types, "blendermcp_webui_server") and bpy.types.blendermcp_webui_server:
        bpy.types.blendermcp_webui_server.stop()
        del bpy.types.blendermcp_webui_server

    # Unregister Preferences last
    if hasattr(BlenderMCPPreferences, "bl_rna"):
        bpy.utils.unregister_class(BlenderMCPPreferences)


__all__ = ["bl_info", "register", "unregister"]


if __name__ == "__main__":
    register()
