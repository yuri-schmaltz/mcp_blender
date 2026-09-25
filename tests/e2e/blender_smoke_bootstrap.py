"""Bootstrap script executed by Blender for smoke integration tests.

Starts the addon socket server on a dynamic port and keeps Blender alive
long enough for the pytest process to run MCP socket commands.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import time
import traceback
from pathlib import Path


def _prepare_imports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> None:
    _prepare_imports()
    import bpy  # type: ignore

    # In --background mode Blender does not drive the event loop, so bpy.app.timers don't fire.
    # Pump timers inline.
    _orig_timer_register = bpy.app.timers.register
    def _pumped_register(func, *, first_interval=0.0, persistent=False):
        try:
            func()
        except Exception:
            traceback.print_exc()
        class _Handle: pass
        return _Handle()
    bpy.app.timers.register = _pumped_register

    repo_root = Path(__file__).resolve().parents[2]
    port = int(os.getenv("BLENDER_MCP_SMOKE_PORT", "9876"))

    addon_id = "blender_mcp_smoke"

    # Install addon in user scripts dir so addon_utils and preferences recognize it
    version_dir = ".".join(str(n) for n in bpy.app.version[:2])
    user_scripts = Path(os.environ.get("HOME", "~")) / ".config" / "blender" / version_dir / "scripts"
    target = user_scripts / "addons" / "modules" / addon_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    shutil.copy(repo_root / "__init__.py", target / "__init__.py")
    shutil.copy(repo_root / "addon.py", target / "addon.py")
    shutil.copy(repo_root / "blender_manifest.toml", target / "blender_manifest.toml")
    shutil.copytree(repo_root / "addon", target / "addon")

    import addon_utils
    addon_utils.modules_refresh()
    import importlib
    importlib.invalidate_caches()
    sys.modules.pop(addon_id, None)

    for kw in ("refresh_handled", "refresh"):
        try:
            addon_utils.enable(addon_id, default_set=False, persistent=False, **{kw: True})
            break
        except TypeError:
            pass

    try:
        bpy.ops.preferences.addon_enable(module=addon_id)
    except Exception:
        pass

    try:
        if addon_id in bpy.context.preferences.addons:
            prefs = bpy.context.preferences.addons[addon_id].preferences
            if prefs:
                prefs.allow_code_execution = True

        addon_mod = sys.modules[addon_id]._addon_mod
        server_cls = getattr(addon_mod, "SocketBlenderMCPServer", None) or getattr(addon_mod, "BlenderMCPServer")
        srv = server_cls(host="127.0.0.1", port=port, client_timeout=30.0)
        srv.command_executor = addon_mod.execute_command
        srv.start()

        print(f"BLENDERMCP_SMOKE_READY:{port}", flush=True)

        # Keep server running until terminated
        while srv.running:
            time.sleep(0.2)
    except Exception as exc:  # pragma: no cover - executed in Blender process
        print(f"BLENDERMCP_SMOKE_ERROR:{exc}", flush=True)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
