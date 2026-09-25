"""3D Printing preparation tools for BlenderMCP."""

import math
import os

import bmesh
import bpy
import mathutils

from ..core.router import mcp_command


@mcp_command(name="set_exact_dimensions", read_only=False)
def set_exact_dimensions(scene, object_name, size_x=None, size_y=None, size_z=None):
    """Set the exact dimensions of an object in metric units (meters by default in Blender).
    If only some axes are provided, the object is scaled proportionally.
    Pass dimensions as floats.
    """
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]

        # Ensure object scaling is updated
        bpy.context.view_layer.update()
        current_dims = obj.dimensions.copy()

        if current_dims.x == 0 or current_dims.y == 0 or current_dims.z == 0:
            return {
                "error": f"Object '{object_name}' has zero dimension on at least one axis, cannot scale proportionately."
            }

        target_x = float(size_x) if size_x is not None else None
        target_y = float(size_y) if size_y is not None else None
        target_z = float(size_z) if size_z is not None else None

        scale_factors = []
        if target_x:
            scale_factors.append(target_x / current_dims.x)
        if target_y:
            scale_factors.append(target_y / current_dims.y)
        if target_z:
            scale_factors.append(target_z / current_dims.z)

        if not scale_factors:
            return {"error": "No new dimensions provided."}

        # Get base proportional scale
        base_scale = scale_factors[0]

        # Calculate final scale
        new_scale = obj.scale.copy()
        new_scale.x *= (target_x / current_dims.x) if target_x else base_scale
        new_scale.y *= (target_y / current_dims.y) if target_y else base_scale
        new_scale.z *= (target_z / current_dims.z) if target_z else base_scale

        obj.scale = new_scale
        bpy.context.view_layer.update()

        # Apply scale so dimensions become standard for 3D printing
        # Equivalent to Ctrl+A -> Scale
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        # Apply scale directly via matrix manipulation to avoid context context errors in headless run
        for i in range(3):
            obj.scale[i] = 1.0
            for v in obj.data.vertices:
                v.co[i] *= new_scale[i]

        bpy.context.view_layer.update()
        final_dims = obj.dimensions

        return {
            "success": True,
            "message": f"Successfully resized '{object_name}'. Scale applied.",
            "final_dimensions": {"x": final_dims.x, "y": final_dims.y, "z": final_dims.z},
        }
    except Exception as e:
        return {"error": f"Failed to set dimensions: {str(e)}"}


@mcp_command(name="apply_print_thickness", read_only=False)
def apply_print_thickness(scene, object_name, thickness_mm, offset=0.0):
    """Apply generic Solidify modifier to create printer-friendly shells.
    thickness_mm is standard millimeters. Offset determines if thickness goes inward (-1), outward (1) or center (0).
    """
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]

        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Millimeters to meters conversion (Blender's default base unit)
        thickness_meters = float(thickness_mm) / 1000.0

        mod_name = "3DPrint_Solidify"
        mod = obj.modifiers.get(mod_name)
        if not mod:
            mod = obj.modifiers.new(name=mod_name, type="SOLIDIFY")

        mod.thickness = thickness_meters
        mod.offset = float(offset)
        mod.use_even_offset = True  # Better for corners in mechanical/hard-surface models
        mod.use_quality_normals = True

        return {
            "success": True,
            "message": f"Applied {thickness_mm}mm thickness to '{object_name}'.",
            "modifier_name": mod.name,
        }
    except Exception as e:
        return {"error": f"Failed to apply thickness: {str(e)}"}


@mcp_command(name="apply_boolean_operation", read_only=False)
def apply_boolean_operation(scene, target_name, tool_name, operation="DIFFERENCE"):
    """Use a tool object to cut (DIFFERENCE), union (UNION), or intersect (INTERSECT) the target object."""
    try:
        if target_name not in scene.objects:
            return {"error": f"Target object '{target_name}' not found."}
        if tool_name not in scene.objects:
            return {"error": f"Tool object '{tool_name}' not found."}

        target_obj = scene.objects[target_name]
        tool_obj = scene.objects[tool_name]

        if operation.upper() not in ["INTERSECT", "UNION", "DIFFERENCE"]:
            return {
                "error": f"Invalid operation '{operation}'. Use INTERSECT, UNION, or DIFFERENCE."
            }

        mod_name = f"Bool_{operation.capitalize()}_{tool_name}"
        mod = target_obj.modifiers.new(name=mod_name, type="BOOLEAN")

        mod.operation = operation.upper()
        mod.object = tool_obj
        mod.solver = "EXACT"  # Usually safer for precise CAD/Hard surface models

        # Hide the tool object from viewport & render to observe the cut
        tool_obj.display_type = "WIRE"
        tool_obj.hide_render = True

        return {
            "success": True,
            "message": f"Applied {operation} boolean on '{target_name}' using '{tool_name}'. Tool is hidden in wireframe mode.",
            "modifier_name": mod.name,
        }
    except Exception as e:
        return {"error": f"Failed to apply boolean: {str(e)}"}


@mcp_command(name="export_for_printing", read_only=False)
def export_for_printing(scene, object_names=None, filepath=None):
    """Export specified objects (or all selected) directly to an STL file."""
    try:
        if not filepath:
            filepath = os.path.join(os.path.expanduser("~"), "blender_mcp_export.stl")

        # Ensure correct extension
        if not filepath.lower().endswith(".stl"):
            filepath += ".stl"

        # Select objects to export
        bpy.ops.object.select_all(action="DESELECT")
        export_count = 0

        if object_names:
            if isinstance(object_names, str):
                object_names = [object_names]
            for name in object_names:
                if name in scene.objects:
                    scene.objects[name].select_set(True)
                    export_count += 1
        else:
            # If no objects specified, export all meshes
            for obj in scene.objects:
                if obj.type == "MESH":
                    obj.select_set(True)
                    export_count += 1

        if export_count == 0:
            return {"error": "No valid mesh objects to export."}

        # Export operator (STL is built-in)
        # using use_selection=True to only export what we selected
        # ASCII=False (binary is smaller)
        bpy.ops.export_mesh.stl(
            filepath=filepath,
            use_selection=True,
            use_mesh_modifiers=True,  # Apply solidify, booleans, etc.
            ascii=False,
            # Blender uses Z-up, Y-forward for generic 3D space, which matches most slicers (Cura/PrusaSlicer) natively when exported directly
            global_scale=1.0,
        )

        return {
            "success": True,
            "message": f"Exported {export_count} objects to {filepath}",
            "filepath": filepath,
            "objects_exported": export_count,
        }

    except Exception as e:
        return {"error": f"Failed to export for printing: {str(e)}"}


@mcp_command(name="assign_print_color", read_only=False)
def assign_print_color(scene, object_name, hex_color):
    """Assign a base color to an object for multi-color 3D printing (stored in material base color)."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Validate and convert hex to RGBA
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join([c * 2 for c in hex_color])
        if len(hex_color) != 6:
            return {"error": f"Invalid hex color '{hex_color}'. Use 6-character hex (e.g. FF0000)."}

        # Convert hex to linear RGB (Blender uses linear internally)
        # Standard sRGB to Linear conversion
        srgb = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
        linear_rgb = [(c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
        rgba = (*linear_rgb, 1.0)

        # Create or update material
        mat_name = f"PrintColor_{hex_color}"
        mat = bpy.data.materials.get(mat_name)

        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True
            principled = mat.node_tree.nodes.get("Principled BSDF")
            if principled:
                principled.inputs["Base Color"].default_value = rgba
                # Make it look somewhat like plastic in viewport
                principled.inputs["Roughness"].default_value = 0.5
                principled.inputs["Specular IOR Level"].default_value = 0.5

        # Assign material to object
        if len(obj.data.materials) == 0:
            obj.data.materials.append(mat)
        else:
            obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Color #{hex_color} assigned to '{object_name}' for multi-color printing.",
            "material": mat_name,
        }
    except Exception as e:
        return {"error": f"Failed to assign print color: {str(e)}"}


@mcp_command(name="auto_layout_for_printing", read_only=False)
def auto_layout_for_printing(scene, bed_size_x=256, bed_size_y=256, padding_mm=5):
    """Automatically layout all mesh objects flat on the virtual print bed (Z=0) with spacing."""
    try:
        meshes = [obj for obj in scene.objects if obj.type == "MESH" and not obj.hide_get()]

        if not meshes:
            return {"error": "No visible meshes found to layout."}

        padding_m = padding_mm / 1000.0

        # First, ensure all objects are resting on Z=0
        for obj in meshes:
            bpy.context.view_layer.update()
            # Get the lowest point of the bounding box relative to world
            bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            lowest_z = min(corner.z for corner in bbox_corners)
            # Move the object up by the negative of its lowest Z point
            obj.location.z -= lowest_z

        # Very simple grid layout strategy (O(N^2) bounding box check if advanced, but we do simple grid)
        # We sort objects by their largest dimension purely for aesthetic/packing heuristics
        def get_max_dim(obj):
            return max(obj.dimensions.x, obj.dimensions.y)

        meshes.sort(key=get_max_dim, reverse=True)

        current_x = 0.0
        current_y = 0.0
        row_height = 0.0

        # Bed origin logic (center of bed is usually 0,0 in Bambu/Prusa)
        # So bed ranges from -bed/2 to +bed/2.
        # We start packing from bottom left:
        start_x = -(bed_size_x / 2000.0) + padding_m
        start_y = -(bed_size_y / 2000.0) + padding_m

        current_x = start_x
        current_y = start_y

        for obj in meshes:
            bpy.context.view_layer.update()
            width = obj.dimensions.x
            height = obj.dimensions.y

            # Check if it fits in current row
            if current_x + width > (bed_size_x / 2000.0):
                # Move to next row
                current_x = start_x
                current_y += row_height + padding_m
                row_height = 0.0

            # Place object (object origin might not be bounding box center, so adjust)
            # Find vector from origin to bottom-left corner of bounding box
            bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            min_x = min(corner.x for corner in bbox_corners)
            min_y = min(corner.y for corner in bbox_corners)

            offset_x = obj.location.x - min_x
            offset_y = obj.location.y - min_y

            obj.location.x = current_x + offset_x
            obj.location.y = current_y + offset_y

            current_x += width + padding_m
            row_height = max(row_height, height)

        bpy.context.view_layer.update()
        return {
            "success": True,
            "message": f"Successfully laid out {len(meshes)} objects on the bed (Z=0).",
            "objects_arranged": len(meshes),
        }
    except Exception as e:
        return {"error": f"Failed to auto-layout objects: {str(e)}"}


@mcp_command(name="export_3mf_for_multicolor", read_only=False)
def export_3mf_for_multicolor(scene, filepath=None):
    """Export the scene to a .3mf file, preserving materials for Bambu Studio/PrusaSlicer."""
    try:
        # Check if 3MF addon is enabled
        if not hasattr(bpy.ops.export_mesh, "threemf") and not hasattr(
            bpy.ops.export_scene, "threemf"
        ):
            try:
                # Try to enable the built-in 3mf addon
                import addon_utils

                addon_utils.enable("io_scene_3mf")
            except Exception as e:
                return {
                    "error": f"The io_scene_3mf addon is not enabled and couldn't be loaded: {str(e)}"
                }

        if not filepath:
            filepath = os.path.join(os.path.expanduser("~"), "blender_mcp_export.3mf")

        if not filepath.lower().endswith(".3mf"):
            filepath += ".3mf"

        # Ensure all visible meshes are selected
        bpy.ops.object.select_all(action="DESELECT")
        export_count = 0
        for obj in scene.objects:
            if obj.type == "MESH" and not obj.hide_get():
                obj.select_set(True)
                export_count += 1

        if export_count == 0:
            return {"error": "No visible mesh objects to export to 3MF."}

        # Export settings (may vary slightly between Blender versions)
        # Try new and old namespaces
        try:
            bpy.ops.export_mesh.threemf(filepath=filepath, use_selection=True)
        except AttributeError:
            try:
                bpy.ops.export_scene.threemf(filepath=filepath, use_selection=True)
            except AttributeError as e:
                return {
                    "error": f"Failed to find 3MF export operator. Ensure the 3MF add-on is active. ({str(e)})"
                }

        return {
            "success": True,
            "message": f"Exported {export_count} objects to {filepath} in 3MF format, preserving colors.",
            "filepath": filepath,
        }
    except Exception as e:
        return {"error": f"Failed to export 3MF: {str(e)}"}


@mcp_command(name="batch_export_all_formats", read_only=False)
def batch_export_all_formats(scene, base_path=None):
    """One-click batch export for all formats (STL, 3MF, Report, Studio)."""
    try:
        import os

        if not base_path:
            base_path = os.path.join(os.path.expanduser("~"), "blender_mcp_release")

        if not os.path.exists(base_path):
            os.makedirs(base_path)

        # 1. Export STL
        stl_path = os.path.join(base_path, "model.stl")
        export_for_printing(scene, filepath=stl_path)

        # 2. Export 3MF
        threemf_path = os.path.join(base_path, "model.3mf")
        export_3mf_for_multicolor(scene, filepath=threemf_path)

        # 3. Generate Report
        from .reporting_tools import generate_print_report

        report_path = os.path.join(base_path, "print_report.txt")
        generate_print_report(scene, filepath=report_path)

        # 4. Render Catalog (if studio exists)
        from .studio_tools import render_catalog_angles

        catalog_dir = os.path.join(base_path, "catalog")
        render_catalog_angles(scene, output_dir=catalog_dir)

        return {
            "success": True,
            "message": f"Successfully completed batch export to {base_path}",
            "files": ["model.stl", "model.3mf", "print_report.txt", "catalog/"],
        }
    except Exception as e:
        return {"error": f"Failed batch export: {str(e)}"}


@mcp_command(name="snap_objects_by_proximity", read_only=False)
def snap_objects_by_proximity(scene, source_name, target_name, padding_mm=0.0):
    """Align and move source object to the closest face of target object."""
    try:
        if source_name not in scene.objects or target_name not in scene.objects:
            return {"error": "One or both objects not found."}

        obj_s = scene.objects[source_name]
        obj_t = scene.objects[target_name]

        bpy.context.view_layer.update()

        # Get bounding box centers
        center_s = obj_s.matrix_world.translation
        center_t = obj_t.matrix_world.translation

        # Simple snapping: Move source to target surface along the vector between them
        direction = (center_t - center_s).normalized()

        # Raycast from source to target
        origin = center_s
        hit, loc, norm, index, obj, matrix = scene.ray_cast(
            bpy.context.view_layer.depsgraph, origin, direction
        )

        if hit:
            # Move source to hit location plus its half-dimension along normal
            half_dim = obj_s.dimensions.z / 2  # Simple assumption for now
            target_loc = loc + norm * (half_dim + (padding_mm / 1000.0))
            obj_s.location = target_loc

            # Align source Z axis to target normal
            rotation_diff = mathutils.Vector((0, 0, 1)).rotation_difference(norm)
            obj_s.rotation_euler = rotation_diff.to_euler()

            return {
                "success": True,
                "message": f"Snapped '{source_name}' to '{target_name}' surface.",
                "hit_location": list(loc),
            }
        else:
            return {
                "error": "Could not find a clear path to snap objects. Try moving them closer manually."
            }

    except Exception as e:
        return {"error": f"Failed to snap objects: {str(e)}"}


@mcp_command(name="set_clearance_tolerance", read_only=False)
def set_clearance_tolerance(scene, object_name, tolerance_mm=0.2):
    """Apply a small offset to a mesh to ensure it fits into another (positive expands, negative contracts)."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": "Object must be a mesh."}

        # Use Displace modifier for uniform surface offset
        mod_name = "MCP_Tolerance"
        mod = obj.modifiers.get(mod_name) or obj.modifiers.new(name=mod_name, type="DISPLACE")

        mod.strength = tolerance_mm / 1000.0  # Convert mm to m
        mod.mid_level = 0.0  # Offset from base surface

        return {
            "success": True,
            "message": f"Applied {tolerance_mm}mm tolerance offset to '{object_name}'.",
            "modifier": mod.name,
        }
    except Exception as e:
        return {"error": f"Failed to set tolerance: {str(e)}"}


@mcp_command(name="optimize_print_orientation", read_only=False)
def optimize_print_orientation(scene, object_name, apply_rotation=True):
    """Find the optimal 3D print orientation to minimize overhangs and z-height, placing it flat on Z=0."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        bpy.context.view_layer.update()

        # 6 canonical orientations (testing which primary axis points +Z)
        orientations = [
            (0, 0, 0),
            (180, 0, 0),
            (90, 0, 0),
            (-90, 0, 0),
            (0, 90, 0),
            (0, -90, 0),
        ]

        best_rot = orientations[0]
        best_score = float("inf")
        best_overhang_area = 0.0
        best_height = 0.0

        down_vector = mathutils.Vector((0.0, 0.0, -1.0))
        limit_angle_rad = math.radians(45.0)

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        for rot_deg in orientations:
            rot_rad = [math.radians(a) for a in rot_deg]
            rot_matrix = mathutils.Euler(rot_rad, "XYZ").to_matrix().to_3x3()

            overhang_area = 0.0
            min_z = float("inf")
            max_z = float("-inf")

            for f in bm.faces:
                w_norm = (rot_matrix @ f.normal).normalized()
                area = f.calc_area()
                dot = max(-1.0, min(1.0, w_norm.dot(down_vector)))
                if math.acos(dot) <= limit_angle_rad:
                    overhang_area += area

            for v in bm.verts:
                z = (rot_matrix @ v.co).z
                if z < min_z:
                    min_z = z
                if z > max_z:
                    max_z = z

            height = max_z - min_z
            score = (overhang_area * 100.0) + (height * 10.0)

            if score < best_score:
                best_score = score
                best_rot = rot_deg
                best_overhang_area = overhang_area
                best_height = height

        bm.free()

        if apply_rotation:
            obj.rotation_euler = mathutils.Euler([math.radians(a) for a in best_rot], "XYZ")
            bpy.context.view_layer.update()

            bbox_corners = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
            lowest_z = min(c.z for c in bbox_corners)
            obj.location.z -= lowest_z
            bpy.context.view_layer.update()

        return {
            "success": True,
            "object_name": object_name,
            "applied": apply_rotation,
            "best_orientation_euler_deg": list(best_rot),
            "estimated_overhang_area_cm2": round(best_overhang_area * 10000.0, 2),
            "estimated_z_height_mm": round(best_height * 1000.0, 2),
            "message": f"Optimized orientation: Euler rotation {best_rot} with Z-height {best_height * 1000:.1f}mm.",
        }
    except Exception as e:
        return {"error": f"Failed to optimize print orientation: {str(e)}"}


MATERIAL_TOLERANCES = {
    "PLA": {"PRESS_FIT": 0.08, "SLIDING": 0.18, "LOOSE": 0.28},
    "PETG": {"PRESS_FIT": 0.12, "SLIDING": 0.22, "LOOSE": 0.35},
    "ABS": {"PRESS_FIT": 0.15, "SLIDING": 0.28, "LOOSE": 0.40},
    "ASA": {"PRESS_FIT": 0.15, "SLIDING": 0.28, "LOOSE": 0.40},
    "TPU": {"PRESS_FIT": -0.05, "SLIDING": 0.08, "LOOSE": 0.15},
}


@mcp_command(name="apply_slicer_xy_compensation", read_only=False)
def apply_slicer_xy_compensation(
    scene,
    object_name,
    contour_compensation_mm=None,
    hole_compensation_mm=None,
    material_preset=None,
    fit_type="SLIDING",
    auto_detect_holes=True,
):
    """Apply OrcaSlicer-style X-Y contour and hole compensation directly to 3D mesh vertices.
    Preserves Z dimensions/heights while adjusting horizontal tolerances for 3D printing.
    """
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        mat_key = material_preset.upper() if material_preset else None
        fit_key = fit_type.upper() if fit_type else "SLIDING"

        if mat_key:
            if mat_key not in MATERIAL_TOLERANCES:
                return {
                    "error": f"Unknown material preset '{material_preset}'. Supported: {list(MATERIAL_TOLERANCES.keys())}"
                }
            tol = MATERIAL_TOLERANCES[mat_key].get(fit_key, 0.20)
            if contour_compensation_mm is None:
                contour_compensation_mm = -tol
            if hole_compensation_mm is None:
                hole_compensation_mm = -round(tol * 0.5, 3)
        else:
            if contour_compensation_mm is None:
                contour_compensation_mm = -0.15
            if hole_compensation_mm is None:
                hole_compensation_mm = 0.0

        contour_comp = float(contour_compensation_mm)
        hole_comp = float(hole_compensation_mm)

        contour_offset_m = contour_comp / 1000.0
        hole_offset_m = hole_comp / 1000.0

        bpy.context.view_layer.update()

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        if len(bm.faces) == 0:
            bm.free()
            return {"error": "Mesh has no geometry to compensate."}

        import mathutils.bvhtree

        face_is_hole = {}
        if auto_detect_holes and hole_comp != 0.0:
            bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.0001)
            for f in bm.faces:
                if abs(f.normal.z) >= 0.95:
                    face_is_hole[f.index] = False
                    continue
                ray_origin = f.calc_center_median() + f.normal * 0.0005
                ray_dir = f.normal
                loc, norm, idx, dist = bvh.ray_cast(ray_origin, ray_dir)
                face_is_hole[f.index] = loc is not None
        else:
            for f in bm.faces:
                face_is_hole[f.index] = False

        modified_count = 0
        for v in bm.verts:
            relevant_faces = [f for f in v.link_faces if abs(f.normal.z) < 0.9]
            if not relevant_faces:
                continue

            is_hole = sum(1 for f in relevant_faces if face_is_hole.get(f.index, False)) > (
                len(relevant_faces) / 2
            )
            offset_m = hole_offset_m if is_hole else contour_offset_m

            if abs(offset_m) < 1e-7:
                continue

            avg_2d = mathutils.Vector((0.0, 0.0))
            for f in relevant_faces:
                fn_2d = mathutils.Vector((f.normal.x, f.normal.y)).normalized()
                avg_2d += fn_2d

            if avg_2d.length < 1e-4:
                continue

            avg_dir = avg_2d.normalized()
            first_face_norm = mathutils.Vector(
                (relevant_faces[0].normal.x, relevant_faces[0].normal.y)
            ).normalized()
            cos_half = avg_dir.dot(first_face_norm)
            miter_factor = (1.0 / cos_half) if cos_half > 0.1 else 1.0

            disp = avg_dir * (offset_m * miter_factor)
            v.co.x += disp.x
            v.co.y += disp.y
            modified_count += 1

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        bpy.context.view_layer.update()

        return {
            "success": True,
            "object_name": object_name,
            "material_preset": mat_key,
            "fit_type": fit_key if mat_key else None,
            "contour_compensation_mm": contour_comp,
            "hole_compensation_mm": hole_comp,
            "vertices_compensated": modified_count,
            "z_preserved": True,
            "message": (
                f"Applied X-Y compensation to '{object_name}': "
                f"Contour: {contour_comp:+.3f}mm, Hole: {hole_comp:+.3f}mm "
                f"({modified_count} vertices updated, Z heights 100% preserved)."
            ),
        }
    except Exception as e:
        return {"error": f"Failed to apply slicer XY compensation: {str(e)}"}
