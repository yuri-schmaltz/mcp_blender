"""Local AI 3D Mesh Generation & Importer for BlenderMCP.

Connects to local native 3D generation servers (such as TripoSR, Trellis,
or Hunyuan3D running on local ports like 8000/8080/7860) or imports
synthesized 3D assets directly into Blender with automatic ground placement.
"""

import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from contextlib import suppress

import bpy

from ..core.router import mcp_command
from ..utils.helpers import get_addon_prefs


@mcp_command(name="import_generated_mesh", read_only=False)
def import_generated_mesh(
    scene,
    filepath,
    name=None,
    snap_ground=True,
    scale=(1.0, 1.0, 1.0),
    location=(0.0, 0.0, 0.0),
):
    """
    Import an AI-generated 3D model (.glb, .gltf, or .obj) from local disk into the scene.
    Automatically applies scaling, positioning, and optional ground snapping.
    """
    try:
        if not os.path.exists(filepath):
            return {"error": f"File '{filepath}' not found on disk."}

        ext = os.path.splitext(filepath)[1].lower()

        # Deselect current objects
        bpy.ops.object.select_all(action="DESELECT")

        if ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=filepath)
        elif ext == ".obj":
            if hasattr(bpy.ops.wm, "obj_import"):
                bpy.ops.wm.obj_import(filepath=filepath)
            else:
                bpy.ops.import_scene.obj(filepath=filepath)
        else:
            return {"error": f"Unsupported 3D file format '{ext}'. Must be .glb, .gltf, or .obj."}

        imported_objs = [obj for obj in bpy.context.selected_objects]
        if not imported_objs:
            return {"error": "Failed to import 3D mesh: no objects loaded."}

        primary_obj = imported_objs[0]
        if name:
            primary_obj.name = name

        # Apply scale and location
        primary_obj.scale = scale
        primary_obj.location = location
        bpy.context.view_layer.update()

        # Optional snap to ground
        if snap_ground and primary_obj.type == "MESH":
            from .spatial_tools import snap_to_ground
            snap_to_ground(scene, primary_obj.name)

        return {
            "success": True,
            "message": f"Successfully imported AI mesh '{primary_obj.name}'.",
            "name": primary_obj.name,
            "location": list(primary_obj.location),
            "scale": list(primary_obj.scale),
        }
    except Exception as e:
        return {"error": f"Import failed: {str(e)}"}


@mcp_command(name="generate_mesh_local_ai", read_only=False)
def generate_mesh_local_ai(
    scene,
    prompt=None,
    image_path=None,
    api_url="http://127.0.0.1:8000/generate",
    name="AI_Generated_Model",
    snap_ground=True,
    timeout=120,
):
    """
    Trigger a local native 3D generative model endpoint (TripoSR / Trellis / Hunyuan3D)
    running locally on your GPU, downloads the synthesized .glb/.obj to a temporary path,
    and imports it into the current Blender scene.
    """
    try:
        if not prompt and not image_path:
            return {"error": "Provide at least a text prompt or a local image_path for 3D generation."}

        payload = {
            "name": name,
        }
        if prompt:
            payload["prompt"] = prompt
        if image_path:
            if not os.path.exists(image_path):
                return {"error": f"Image path '{image_path}' not found."}
            payload["image_path"] = os.path.abspath(image_path)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as err:
            return {
                "error": (
                    f"Could not connect to local 3D AI endpoint at {api_url}: {err.reason}. "
                    "Ensure your local TripoSR, Trellis, or Hunyuan3D server is started."
                )
            }

        mesh_filepath = result_json.get("filepath") or result_json.get("model_path")
        if not mesh_filepath or not os.path.exists(mesh_filepath):
            return {
                "error": f"Local AI model completed, but returned mesh path '{mesh_filepath}' was not found.",
                "response": result_json,
            }

        # Import the model
        return import_generated_mesh(scene, filepath=mesh_filepath, name=name, snap_ground=snap_ground)

    except Exception as e:
        return {"error": f"Local AI 3D generation failed: {str(e)}"}
