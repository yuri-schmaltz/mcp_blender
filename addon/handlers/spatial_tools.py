"""Spatial reasoning and placement tools for BlenderMCP."""

import bpy
import mathutils

from ..core.router import mcp_command


def _get_world_bounds(obj):
    """Return (min_vec, max_vec) in world space for an object."""
    if obj.type == "MESH" and obj.data:
        corners = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
    else:
        corners = [obj.matrix_world.translation]

    min_x = min(c.x for c in corners)
    max_x = max(c.x for c in corners)
    min_y = min(c.y for c in corners)
    max_y = max(c.y for c in corners)
    min_z = min(c.z for c in corners)
    max_z = max(c.z for c in corners)

    return mathutils.Vector((min_x, min_y, min_z)), mathutils.Vector((max_x, max_y, max_z))


@mcp_command(name="snap_to_ground", read_only=False)
def snap_to_ground(scene, name):
    """
    Adjust object's Z position so that its lowest point rests precisely on the ground (Z=0.0).
    """
    try:
        obj = scene.objects.get(name)
        if not obj:
            return {"error": f"Object '{name}' not found."}

        min_bound, _ = _get_world_bounds(obj)
        z_offset = -min_bound.z
        obj.location.z += z_offset
        bpy.context.view_layer.update()

        return {
            "success": True,
            "message": f"Snapped '{name}' to ground (shifted Z by {z_offset:.4f}).",
            "new_location": list(obj.location),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp_command(name="place_object_on_top", read_only=False)
def place_object_on_top(scene, child_name, parent_name, offset_z=0.0, center_xy=True):
    """
    Position child_name directly on top of parent_name without collision or floating.
    Optionally aligns child's XY center with parent's XY center.
    """
    try:
        child = scene.objects.get(child_name)
        parent = scene.objects.get(parent_name)

        if not child:
            return {"error": f"Child object '{child_name}' not found."}
        if not parent:
            return {"error": f"Parent object '{parent_name}' not found."}

        _, parent_max = _get_world_bounds(parent)
        child_min, child_max = _get_world_bounds(child)

        # Calculate required Z adjustment
        target_z = parent_max.z + float(offset_z)
        current_bottom_z = child_min.z
        z_diff = target_z - current_bottom_z
        child.location.z += z_diff

        # Align XY centers if requested
        if center_xy:
            parent_min, _ = _get_world_bounds(parent)
            parent_center_x = (parent_min.x + parent_max.x) / 2.0
            parent_center_y = (parent_min.y + parent_max.y) / 2.0

            child_center_x = (child_min.x + child_max.x) / 2.0
            child_center_y = (child_min.y + child_max.y) / 2.0

            child.location.x += (parent_center_x - child_center_x)
            child.location.y += (parent_center_y - child_center_y)

        bpy.context.view_layer.update()

        return {
            "success": True,
            "message": f"Placed '{child_name}' directly on top of '{parent_name}'.",
            "new_location": list(child.location),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp_command(name="align_objects", read_only=False)
def align_objects(scene, object_names, axis="X", mode="CENTER"):
    """
    Align multiple objects along a specified axis ('X', 'Y', or 'Z').
    Modes:
      - 'CENTER': Align objects to the average center coordinate.
      - 'MIN': Align all objects to the minimum boundary on that axis.
      - 'MAX': Align all objects to the maximum boundary on that axis.
    """
    try:
        axis = axis.upper()
        if axis not in ["X", "Y", "Z"]:
            return {"error": "Axis must be 'X', 'Y', or 'Z'."}

        mode = mode.upper()
        if mode not in ["CENTER", "MIN", "MAX"]:
            return {"error": "Mode must be 'CENTER', 'MIN', or 'MAX'."}

        objs = [scene.objects.get(name) for name in object_names]
        objs = [o for o in objs if o is not None]

        if len(objs) < 2:
            return {"error": "Need at least 2 valid objects to perform alignment."}

        axis_idx = {"X": 0, "Y": 1, "Z": 2}[axis]

        bounds = [_get_world_bounds(o) for o in objs]
        min_vals = [b[0][axis_idx] for b in bounds]
        max_vals = [b[1][axis_idx] for b in bounds]
        center_vals = [(mn + mx) / 2.0 for mn, mx in zip(min_vals, max_vals)]

        if mode == "MIN":
            target_val = min(min_vals)
            for o, b in zip(objs, bounds):
                diff = target_val - b[0][axis_idx]
                curr_loc = getattr(o.location, axis.lower())
                setattr(o.location, axis.lower(), curr_loc + diff)
        elif mode == "MAX":
            target_val = max(max_vals)
            for o, b in zip(objs, bounds):
                diff = target_val - b[1][axis_idx]
                curr_loc = getattr(o.location, axis.lower())
                setattr(o.location, axis.lower(), curr_loc + diff)
        else:  # CENTER
            target_val = sum(center_vals) / len(center_vals)
            for o, c in zip(objs, center_vals):
                diff = target_val - c
                curr_loc = getattr(o.location, axis.lower())
                setattr(o.location, axis.lower(), curr_loc + diff)

        bpy.context.view_layer.update()

        return {
            "success": True,
            "message": f"Aligned {len(objs)} objects on axis {axis} using mode {mode}.",
        }
    except Exception as e:
        return {"error": str(e)}
