"""BlenderMCP UI Panel - redesigned with collapsible sub-panels for better UX."""

import sys

import bpy


def _get_addon_module():
    """Load the main addon module safely using package context."""
    if __package__:
        # bl_ext.user_default.mcp_blender.addon.ui -> bl_ext.user_default.mcp_blender.addon_entry
        pkg_root = ".".join(__package__.split(".")[:3])
        entry_name = f"{pkg_root}.addon_entry"
        if entry_name in sys.modules:
            return sys.modules[entry_name]

    # Fallback to searching in sys.modules
    for name, mod in sys.modules.items():
        if name.endswith(".addon_entry") and hasattr(mod, "BlenderMCPServer"):
            return mod
    return None


# Import i18n
from ..utils import i18n

t = i18n.t


def get_prefs(context):
    """Access global addon preferences safely."""
    pkg = __package__
    if pkg and pkg.startswith("bl_ext."):
        # Extension mode: bl_ext.user_default.mcp_blender.addon.ui -> bl_ext.user_default.mcp_blender
        parts = pkg.split(".")
        root_pkg = ".".join(parts[:3]) if len(parts) >= 3 else pkg
    elif pkg:
        root_pkg = pkg.split(".")[0]
    else:
        root_pkg = "mcp_blender"

    if root_pkg in context.preferences.addons:
        return context.preferences.addons[root_pkg].preferences
    return None


# =============================================================================
# Main Panel: Connection & Status
# =============================================================================
class BLENDERMCP_PT_Panel(bpy.types.Panel):
    bl_label = "Blender MCP"
    bl_idname = "BLENDERMCP_PT_Panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP"

    def draw(self, context):
        layout = self.layout
        if layout is None:
            return
        scene = context.scene

        # --- Connection Status ---
        if scene.blendermcp_server_running:
            layout.operator("blendermcp.stop_server", text=t("btn_disconnect"), icon="CANCEL")
        else:
            status_row = layout.row()
            status_row.alert = True
            status_row.label(text=t("status_disconnected"), icon="ERROR")

            row = layout.row(align=True)
            row.scale_y = 1.4
            row.operator("blendermcp.start_server", text=t("btn_connect"), icon="PLAY")

        # --- Last Action Summary (Previously separate Status & Cache) ---
        if scene.blendermcp_last_action:
            box = layout.box()
            row = box.row()
            icon = "CHECKMARK" if scene.blendermcp_last_action_ok else "ERROR"
            row.alert = not scene.blendermcp_last_action_ok
            row.label(
                text=f"{scene.blendermcp_last_action}: {scene.blendermcp_last_action_details[:30]}...",
                icon=icon,
            )

        # --- WebUI Server Controls ---
        layout.separator()
        col = layout.column(align=True)
        prefs = get_prefs(context)
        if (
            getattr(bpy.types, "blendermcp_webui_server", None)
            and bpy.types.blendermcp_webui_server.server
        ):
            col.operator("blendermcp.stop_webui", text="Stop WebUI Server", icon="CANCEL")
            op = col.operator("blendermcp.open_url", text="Open WebUI in Browser", icon="URL")
            op.target_url = f"http://localhost:{prefs.webui_port if prefs else 8080}"
        else:
            col.operator("blendermcp.start_webui", text="Start WebUI Server", icon="WORLD_DATA")


# All panel classes in registration order
PANEL_CLASSES = [
    BLENDERMCP_PT_Panel,
]


def draw_statusbar_mcp(self, context):
    """Draw a compact, clickable status icon in the Blender status bar."""
    scene = getattr(context, "scene", None)
    if not scene:
        return

    running = getattr(scene, "blendermcp_server_running", False)
    icon = "RADIOBUT_ON" if running else "RADIOBUT_OFF"

    row = self.layout.row(align=True)
    row.operator("blendermcp.toggle_server", text="", icon=icon, emboss=False)

