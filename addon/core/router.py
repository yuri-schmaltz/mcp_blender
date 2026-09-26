import inspect
import logging
import time
import traceback

import bpy

try:
    if __package__:
        from ..utils.metrics import metrics
    else:
        from addon.utils.metrics import metrics
except ImportError:
    # Fallback caso a importação falhe
    class DummyMetrics:
        def inc(self, name):
            pass

        def observe(self, name, value):
            pass

    metrics = DummyMetrics()

logger = logging.getLogger("BlenderMCP.Router")

_COMMAND_REGISTRY = {}


def mcp_command(name=None, read_only=False):
    """
    Decorator to register an MCP command handler.
    :param name: Optional explicit command name. Defaults to the function name.
    :param read_only: If True, skips pushing an undo step in Blender.
    """

    def decorator(func):
        cmd_name = name if name else func.__name__
        _COMMAND_REGISTRY[cmd_name] = {"func": func, "read_only": read_only}
        return func

    return decorator


def execute_command(command: dict):
    """
    Executes a registered command by its type.
    """
    cmd_type = command.get("type")
    params = command.get("params", {})

    if not cmd_type:
        return {"status": "error", "message": "Command type missing"}

    # Temporary fallback/intercept for execute_code and list_tools that are special
    # We will register them manually or directly intercept them here if they don't use the decorator yet.
    cmd_info = _COMMAND_REGISTRY.get(cmd_type)

    if not cmd_info:
        return {"status": "error", "message": f"Unknown command type: {cmd_type}"}

    try:
        func = cmd_info["func"]

        # Inject scene if the handler expects it
        sig = inspect.signature(func)
        if "scene" in sig.parameters and "scene" not in params:
            params["scene"] = bpy.context.scene

        start_time = time.time()
        result = func(**params)
        duration = time.time() - start_time

        # Metric tracking (Wave 4)
        metrics.inc(f"cmd_{cmd_type}_count")
        metrics.observe(f"cmd_{cmd_type}_duration", duration)
        logger.info(f"MCP Command '{cmd_type}' took {duration:.3f}s")

        # Undo history
        if not cmd_info["read_only"]:
            try:
                msg = f"MCP: {cmd_type}"
                if params:
                    first_val = next(iter(params.values()))
                    msg += f" ({str(first_val)[:20]})"
                bpy.ops.ed.undo_push(message=msg)
            except Exception as e:
                logger.debug(f"Failed to push undo step: {e}")

        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Error executing {cmd_type}: {e}")
        traceback.print_exc()

        # PEP 678 & Diagnostic Context Enrichment (Python 3.11+)
        ctx_mode = "UNKNOWN"
        active_obj_name = None
        selected_count = 0
        scene_name = None

        try:
            ctx = getattr(bpy, "context", None)
            if ctx is not None:
                ctx_mode = getattr(ctx, "mode", "UNKNOWN")
                active_obj = getattr(ctx, "active_object", None)
                if active_obj is not None:
                    active_obj_name = getattr(active_obj, "name", None)
                selected_objs = getattr(ctx, "selected_objects", [])
                selected_count = len(selected_objs) if selected_objs is not None else 0
                scene = getattr(ctx, "scene", None)
                if scene is not None:
                    scene_name = getattr(scene, "name", None)
        except Exception:
            pass

        diag_note = (
            f"[Blender Context: mode={ctx_mode}, active_object={active_obj_name}, "
            f"selected_count={selected_count}, scene={scene_name}]"
        )
        if hasattr(e, "add_note"):
            try:
                e.add_note(diag_note)
            except Exception:
                pass

        return {
            "status": "error",
            "message": str(e),
            "diagnostic": {
                "command": cmd_type,
                "context_mode": ctx_mode,
                "active_object": active_obj_name,
                "selected_count": selected_count,
                "scene": scene_name,
                "notes": getattr(e, "__notes__", [diag_note]),
            },
        }


def get_registered_commands():
    return list(_COMMAND_REGISTRY.keys())
