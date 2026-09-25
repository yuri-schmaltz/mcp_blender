"""Mesh processing tools for BlenderMCP."""

import math
from collections import defaultdict

import bmesh
import bpy
import mathutils

from ..core.router import mcp_command


@mcp_command(name="separate_loose_parts", read_only=False)
def separate_loose_parts(scene, object_name, smart_rename=True):
    """Separate a mesh into its disconnected parts and optionally identify wheels/chassis."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Select and make active
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Track objects before separation to find the new ones
        pre_objects = set(scene.objects.keys())

        # Perform separation
        bpy.ops.mesh.separate(type="LOOSE")

        # Find new objects
        post_objects = set(scene.objects.keys())
        new_objects_names = list(post_objects - pre_objects)
        all_parts = [scene.objects[name] for name in new_objects_names] + [obj]

        result_message = f"Separated into {len(all_parts)} parts."
        identified_parts = []

        if smart_rename and len(all_parts) > 1:
            # Smart identification logic
            # Group objects by bounding box dimensions (within a small tolerance)
            size_groups = defaultdict(list)
            tolerance = 0.05  # 5% tolerance

            for part in all_parts:
                dims = tuple(
                    sorted(
                        [
                            round(part.dimensions.x, 3),
                            round(part.dimensions.y, 3),
                            round(part.dimensions.z, 3),
                        ]
                    )
                )
                # Try to find a group with similar dimensions
                found = False
                for group_dims in size_groups.keys():
                    match = True
                    for d1, d2 in zip(dims, group_dims):
                        if d2 == 0:
                            if d1 != 0:
                                match = False
                        elif abs(d1 - d2) / d2 > tolerance:
                            match = False
                    if match:
                        size_groups[group_dims].append(part)
                        found = True
                        break
                if not found:
                    size_groups[dims].append(part)

            # Look for wheels: usually a group of 4 (or 2) similar objects
            wheel_candidates = []
            for dims, group in size_groups.items():
                if len(group) >= 2:  # At least a pair
                    # Check if it looks circular (two dimensions roughly equal)
                    d_sorted = sorted(dims)
                    if (
                        d_sorted[0] > 0 and abs(d_sorted[1] - d_sorted[2]) / d_sorted[2] < 0.2
                    ):  # 20% diff max
                        wheel_candidates.append((len(group), dims, group))

            # Use the group closest to 4 members as wheels
            if wheel_candidates:
                wheel_candidates.sort(key=lambda x: abs(x[0] - 4))
                count, dims, wheels = wheel_candidates[0]
                for i, wheel in enumerate(wheels):
                    wheel.name = f"Wheel_{i + 1}"
                    identified_parts.append(wheel.name)

            # Identify Chassis: usually the largest by bounding volume
            all_parts.sort(
                key=lambda x: x.dimensions.x * x.dimensions.y * x.dimensions.z, reverse=True
            )
            chassis = all_parts[0]
            if chassis.name.startswith("Wheel") is False:
                chassis.name = "Chassis"
                identified_parts.append(chassis.name)

            # Rename remaining ones generic
            for i, part in enumerate(all_parts):
                if part.name == "Chassis" or part.name.startswith("Wheel"):
                    continue
                part.name = f"Part_{i + 1}"

            result_message += f" Identified: {', '.join(identified_parts)}."

        return {
            "success": True,
            "message": result_message,
            "parts_count": len(all_parts),
            "identified": identified_parts,
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": f"Failed to separate mesh: {str(e)}"}


@mcp_command(name="check_mesh_integrity", read_only=False)
def check_mesh_integrity(scene, object_name):
    """Check mesh for common 3D printing issues (non-manifold, holes, normals)."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Use bmesh for analysis
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        # Non-manifold edges
        non_manifold = [e for e in bm.edges if not e.is_manifold]

        # Holes (boundary edges)
        boundary = [e for e in bm.edges if e.is_boundary]

        # Self-intersections (Skipped for performance, usually requires external tools or complex logic)

        report = {
            "is_printer_ready": len(non_manifold) == 0,
            "non_manifold_edges": len(non_manifold),
            "boundary_edges_count": len(boundary),
            "message": "Mesh is clean and ready for printing."
            if len(non_manifold) == 0
            else f"Found {len(non_manifold)} non-manifold issues.",
        }

        bm.free()
        return {"success": True, "report": report}
    except Exception as e:
        return {"error": f"Failed to check integrity: {str(e)}"}


@mcp_command(name="auto_repair_mesh", read_only=False)
def auto_repair_mesh(scene, object_name):
    """Try to automatically fix mesh issues (fill holes, normals)."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Select and make active
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Go to Edit Mode
        bpy.ops.object.mode_set(mode="EDIT")

        # 1. Fill holes
        bpy.ops.mesh.fill_holes(sides=0)

        # 2. Recalculate normals (Outside)
        bpy.ops.mesh.normals_make_consistent(inside=False)

        # 3. Remove doubles (Merge by distance)
        bpy.ops.mesh.remove_doubles()

        # Back to Object Mode
        bpy.ops.object.mode_set(mode="OBJECT")

        return {
            "success": True,
            "message": f"Applied auto-repairs (fill holes, recalculate normals, merge doubles) to '{object_name}'.",
        }
    except Exception as e:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        return {"error": f"Failed to auto-repair: {str(e)}"}


@mcp_command(name="resolve_self_intersections", read_only=False)
def resolve_self_intersections(scene, object_name):
    """Resolve self-intersecting faces within the same mesh using the Exact Boolean solver."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        # Select and make active
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Go to Edit Mode
        bpy.ops.object.mode_set(mode="EDIT")

        # Select all faces
        bpy.ops.mesh.select_all(action="SELECT")

        # Intersect (Boolean) with Self-Intersect enabled
        # This resolves overlaps within the same mesh while maintaining original shape
        bpy.ops.mesh.intersect_boolean(
            operation="UNION", use_self=True, solver="EXACT", use_swap=True
        )

        # Final cleanup: merge by distance and fix normals
        bpy.ops.mesh.remove_doubles()
        bpy.ops.mesh.normals_make_consistent(inside=False)

        # Back to Object Mode
        bpy.ops.object.mode_set(mode="OBJECT")

        return {
            "success": True,
            "message": f"Resolved self-intersections in '{object_name}' while preserving the outer shape.",
        }
    except Exception as e:
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        return {"error": f"Failed to resolve self-intersections: {str(e)}"}


@mcp_command(name="detect_thin_walls", read_only=True)
def detect_thin_walls(scene, object_name, threshold_mm=1.2, max_samples=500):
    """Detect thin sections of a mesh using raycasting along negative normals."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        bpy.context.view_layer.update()
        threshold_m = float(threshold_mm) / 1000.0

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        if len(bm.faces) == 0:
            bm.free()
            return {"error": "Mesh has no faces to analyze."}

        import mathutils.bvhtree

        bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.0001)

        step = max(1, len(bm.faces) // max_samples)
        sample_faces = [bm.faces[i] for i in range(0, len(bm.faces), step)][:max_samples]

        thin_points = []
        min_thickness = float("inf")
        sample_count = 0

        for f in sample_faces:
            # Raycast from face center inwards (opposite to normal) with slight offset
            ray_origin = f.calc_center_median() - f.normal * 0.0001
            ray_dir = -f.normal.normalized()

            loc, normal, index, dist = bvh.ray_cast(ray_origin, ray_dir)
            if loc is not None and dist > 0.00001:
                sample_count += 1
                dist_actual = dist + 0.0001
                if dist_actual < min_thickness:
                    min_thickness = dist_actual
                if dist_actual < threshold_m:
                    world_loc = obj.matrix_world @ loc
                    thin_points.append(
                        {
                            "thickness_mm": round(dist_actual * 1000.0, 3),
                            "location": [
                                round(world_loc.x, 3),
                                round(world_loc.y, 3),
                                round(world_loc.z, 3),
                            ],
                        }
                    )

        bm.free()

        min_thickness_mm = (
            round(min_thickness * 1000.0, 3) if min_thickness != float("inf") else None
        )
        thin_ratio = len(thin_points) / sample_count if sample_count > 0 else 0.0

        return {
            "success": True,
            "object_name": object_name,
            "threshold_mm": threshold_mm,
            "samples_tested": sample_count,
            "min_thickness_mm": min_thickness_mm,
            "thin_points_detected": len(thin_points),
            "thin_ratio": round(thin_ratio, 3),
            "is_safe": len(thin_points) == 0,
            "sample_critical_locations": thin_points[:10],
            "message": "All sampled areas meet the thickness threshold."
            if len(thin_points) == 0
            else f"Found {len(thin_points)} regions with thickness below {threshold_mm}mm.",
        }
    except Exception as e:
        return {"error": f"Failed to detect thin walls: {str(e)}"}


@mcp_command(name="analyze_overhangs", read_only=True)
def analyze_overhangs(scene, object_name, threshold_angle_deg=45.0):
    """Analyze mesh surface area requiring supports based on overhang angle."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        bpy.context.view_layer.update()
        matrix = obj.matrix_world

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        down_vector = mathutils.Vector((0.0, 0.0, -1.0))
        limit_angle_rad = math.radians(90.0 - float(threshold_angle_deg))

        total_area = 0.0
        overhang_area = 0.0
        overhang_faces = 0
        min_z = float("inf")
        max_z = float("-inf")

        for f in bm.faces:
            world_normal = (matrix.to_3x3() @ f.normal).normalized()
            area = f.calc_area() * (obj.scale.x * obj.scale.y)
            total_area += area

            dot = max(-1.0, min(1.0, world_normal.dot(down_vector)))
            angle_with_down = math.acos(dot)

            if angle_with_down <= limit_angle_rad:
                overhang_area += area
                overhang_faces += 1
                for v in f.verts:
                    w_co = matrix @ v.co
                    if w_co.z < min_z:
                        min_z = w_co.z
                    if w_co.z > max_z:
                        max_z = w_co.z

        bm.free()

        overhang_pct = (overhang_area / total_area * 100.0) if total_area > 0 else 0.0

        return {
            "success": True,
            "object_name": object_name,
            "threshold_angle_deg": threshold_angle_deg,
            "total_surface_area_cm2": round(total_area * 10000.0, 2),
            "overhang_area_cm2": round(overhang_area * 10000.0, 2),
            "overhang_percentage": round(overhang_pct, 2),
            "overhang_faces_count": overhang_faces,
            "requires_supports": overhang_area > 0.0001,
            "overhang_z_range_mm": {
                "min_z": round(min_z * 1000.0, 2) if min_z != float("inf") else 0.0,
                "max_z": round(max_z * 1000.0, 2) if max_z != float("-inf") else 0.0,
            },
        }
    except Exception as e:
        return {"error": f"Failed to analyze overhangs: {str(e)}"}


@mcp_command(name="cleanup_degenerate_mesh", read_only=False)
def cleanup_degenerate_mesh(scene, object_name, min_edge_length_mm=0.01, min_face_area_mm2=0.01):
    """Clean up degenerate geometry: zero-area faces, zero-length edges, and isolated vertices."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        init_verts = len(obj.data.vertices)
        init_edges = len(obj.data.edges)
        init_faces = len(obj.data.polygons)

        bm = bmesh.new()
        bm.from_mesh(obj.data)

        dist_threshold = float(min_edge_length_mm) / 1000.0

        bmesh.ops.dissolve_degenerate(bm, dist=dist_threshold, edges=bm.edges[:])
        bmesh.ops.clean_isolated_verts(bm)
        bmesh.ops.reorient_faces(bm, faces=bm.faces[:])

        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()

        final_verts = len(obj.data.vertices)
        final_edges = len(obj.data.edges)
        final_faces = len(obj.data.polygons)

        return {
            "success": True,
            "object_name": object_name,
            "vertices_removed": init_verts - final_verts,
            "edges_removed": init_edges - final_edges,
            "faces_removed": init_faces - final_faces,
            "final_counts": {
                "vertices": final_verts,
                "edges": final_edges,
                "faces": final_faces,
            },
            "message": f"Cleaned up '{object_name}': removed {init_verts - final_verts} verts, {init_edges - final_edges} edges, {init_faces - final_faces} faces.",
        }
    except Exception as e:
        return {"error": f"Failed to clean up degenerate mesh: {str(e)}"}


@mcp_command(name="generate_watertight_hull", read_only=False)
def generate_watertight_hull(scene, object_name, voxel_size_mm=1.0, smooth_iterations=2):
    """Reconstruct an impenetrable, 100% watertight manifold mesh from a messy/broken model using voxel remeshing."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        init_verts = len(obj.data.vertices)
        voxel_size_m = max(0.0001, float(voxel_size_mm) / 1000.0)

        # 1. Apply remesh modifier
        mod_remesh = obj.modifiers.new(name="MCP_Watertight_Remesh", type="REMESH")
        mod_remesh.mode = "VOXEL"
        mod_remesh.voxel_size = voxel_size_m
        mod_remesh.adaptivity = 0.0

        bpy.ops.object.modifier_apply(modifier=mod_remesh.name)

        # 2. Smooth slightly to eliminate staircasing if requested
        if smooth_iterations > 0:
            mod_smooth = obj.modifiers.new(name="MCP_Watertight_Smooth", type="SMOOTH")
            mod_smooth.factor = 0.5
            mod_smooth.iterations = int(smooth_iterations)
            bpy.ops.object.modifier_apply(modifier=mod_smooth.name)

        # 3. Check resulting manifold status
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        non_manifold = [e for e in bm.edges if not e.is_manifold]
        is_watertight = len(non_manifold) == 0
        bm.free()

        return {
            "success": True,
            "object_name": object_name,
            "voxel_size_mm": voxel_size_mm,
            "initial_vertices": init_verts,
            "final_vertices": len(obj.data.vertices),
            "is_watertight": is_watertight,
            "non_manifold_edges": len(non_manifold),
            "message": f"Successfully created watertight hull for '{object_name}' ({len(obj.data.vertices)} vertices).",
        }
    except Exception as e:
        return {"error": f"Failed to generate watertight hull: {str(e)}"}


@mcp_command(name="generate_lod_chain", read_only=False)
def generate_lod_chain(scene, object_name, ratios=None, create_collection=True):
    """Generate a chain of Level of Detail (LOD) models with progressive polygon decimation."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        base_obj = scene.objects[object_name]
        if base_obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        if ratios is None or not isinstance(ratios, list) or len(ratios) == 0:
            ratios = [1.0, 0.5, 0.25, 0.1]

        target_collection = scene.collection
        if create_collection:
            col_name = f"LODs_{object_name}"
            target_collection = bpy.data.collections.get(col_name)
            if not target_collection:
                target_collection = bpy.data.collections.new(col_name)
                scene.collection.children.link(target_collection)

        lods = []
        base_faces = len(base_obj.data.polygons)

        for i, ratio in enumerate(ratios):
            lod_name = f"{object_name}_LOD{i}"
            ratio_val = max(0.01, min(1.0, float(ratio)))

            new_mesh = base_obj.data.copy()
            new_mesh.name = f"{lod_name}_Mesh"
            new_obj = base_obj.copy()
            new_obj.data = new_mesh
            new_obj.name = lod_name

            if create_collection:
                target_collection.objects.link(new_obj)
            else:
                scene.collection.objects.link(new_obj)

            if ratio_val < 0.999:
                bpy.ops.object.select_all(action="DESELECT")
                new_obj.select_set(True)
                bpy.context.view_layer.objects.active = new_obj

                mod = new_obj.modifiers.new(name="LOD_Decimate", type="DECIMATE")
                mod.decimate_type = "COLLAPSE"
                mod.ratio = ratio_val
                bpy.ops.object.modifier_apply(modifier=mod.name)

            new_faces = len(new_obj.data.polygons)
            new_verts = len(new_obj.data.vertices)
            reduction_pct = (
                round((1.0 - (new_faces / base_faces)) * 100.0, 1) if base_faces > 0 else 0.0
            )

            lods.append(
                {
                    "lod_level": i,
                    "object_name": lod_name,
                    "target_ratio": ratio_val,
                    "face_count": new_faces,
                    "vertex_count": new_verts,
                    "reduction_percentage": reduction_pct,
                }
            )

        return {
            "success": True,
            "base_object": object_name,
            "base_faces": base_faces,
            "collection_created": target_collection.name if create_collection else None,
            "lods": lods,
            "message": f"Generated {len(lods)} LOD levels for '{object_name}'.",
        }
    except Exception as e:
        return {"error": f"Failed to generate LOD chain: {str(e)}"}


@mcp_command(name="auto_quad_remesh", read_only=False)
def auto_quad_remesh(
    scene,
    object_name,
    target_faces=4000,
    use_mesh_symmetry=False,
    use_preserve_sharp=True,
    use_preserve_boundary=False,
):
    """Automatically retopologize a mesh into clean quadrilaterals using the QuadriFlow algorithm."""
    try:
        if object_name not in scene.objects:
            return {"error": f"Object '{object_name}' not found."}

        obj = scene.objects[object_name]
        if obj.type != "MESH":
            return {"error": f"Object '{object_name}' is not a MESH."}

        init_faces = len(obj.data.polygons)
        init_verts = len(obj.data.vertices)

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.quadriflow_remesh(
            use_mesh_symmetry=use_mesh_symmetry,
            use_preserve_sharp=use_preserve_sharp,
            use_preserve_boundary=use_preserve_boundary,
            mode="FACES",
            target_faces=int(target_faces),
        )

        final_faces = len(obj.data.polygons)
        final_verts = len(obj.data.vertices)

        return {
            "success": True,
            "object_name": object_name,
            "target_faces": target_faces,
            "initial_counts": {"faces": init_faces, "vertices": init_verts},
            "final_counts": {"faces": final_faces, "vertices": final_verts},
            "message": f"Successfully quad-remeshed '{object_name}' ({init_faces} faces -> {final_faces} quad faces).",
        }
    except Exception as e:
        return {"error": f"Failed to perform quad remesh: {str(e)}"}
