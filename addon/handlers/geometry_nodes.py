"""Geometry Nodes and procedural modeling tools for BlenderMCP."""

import bpy
import mathutils

from ..core.router import mcp_command


@mcp_command(name="create_procedural_wire_curve", read_only=False)
def create_procedural_wire_curve(
    scene,
    start_point=(0.0, 0.0, 1.0),
    end_point=(2.0, 0.0, 1.0),
    sag=0.4,
    bevel_depth=0.015,
    name="Procedural_Wire",
):
    """
    Create a procedural catenary-like hanging wire/cable between two 3D coordinates.
    """
    try:
        p1 = mathutils.Vector(start_point)
        p2 = mathutils.Vector(end_point)
        mid = (p1 + p2) / 2.0
        mid.z -= float(sag)

        curve_data = bpy.data.curves.new(name=name, type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.bevel_depth = float(bevel_depth)
        curve_data.bevel_resolution = 4

        spline = curve_data.splines.new("BEZIER")
        spline.bezier_points.add(2)  # Total 3 points

        points = [p1, mid, p2]
        for i, pt in enumerate(points):
            bp = spline.bezier_points[i]
            bp.co = pt
            bp.handle_left_type = "AUTO"
            bp.handle_right_type = "AUTO"

        obj = bpy.data.objects.new(name, curve_data)
        scene.collection.objects.link(obj)
        bpy.context.view_layer.update()

        return {
            "success": True,
            "message": f"Created procedural wire '{obj.name}' between {start_point} and {end_point}.",
            "name": obj.name,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp_command(name="add_geometry_nodes_scatter", read_only=False)
def add_geometry_nodes_scatter(
    scene,
    target_mesh_name,
    instance_mesh_name,
    density=10.0,
    seed=0,
):
    """
    Apply a procedural Geometry Nodes modifier to scatter instances across a target mesh surface.
    Works natively on Blender 3.5+ and 4.x / 5.x.
    """
    try:
        target = scene.objects.get(target_mesh_name)
        instance = scene.objects.get(instance_mesh_name)

        if not target or target.type != "MESH":
            return {"error": f"Target mesh '{target_mesh_name}' not found."}
        if not instance:
            return {"error": f"Instance object '{instance_mesh_name}' not found."}

        # Add Geometry Nodes modifier
        mod = target.modifiers.new(name=f"Scatter_{instance.name}", type="NODES")
        node_group = bpy.data.node_groups.new(f"GN_Scatter_{instance.name}", "GeometryNodeTree")
        mod.node_group = node_group

        nodes = node_group.nodes
        links = node_group.links

        # Interface inputs / outputs
        if hasattr(node_group, "interface"):
            node_group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            node_group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        input_node = nodes.new("NodeGroupInput")
        input_node.location = (-400, 0)
        output_node = nodes.new("NodeGroupOutput")
        output_node.location = (600, 0)

        # Distribute points on faces
        dist_node = nodes.new("GeometryNodeDistributePointsOnFaces")
        dist_node.location = (-150, 100)
        dist_node.inputs["Density"].default_value = float(density)
        dist_node.inputs["Seed"].default_value = int(seed)

        # Instance on points
        inst_node = nodes.new("GeometryNodeInstanceOnPoints")
        inst_node.location = (150, 100)

        # Object info for the instance
        info_node = nodes.new("GeometryNodeObjectInfo")
        info_node.location = (-150, -150)
        info_node.inputs["Object"].default_value = instance

        # Join geometry
        join_node = nodes.new("GeometryNodeJoinGeometry")
        join_node.location = (400, 0)

        # Connect nodes
        links.new(input_node.outputs[0], dist_node.inputs["Mesh"])
        links.new(dist_node.outputs["Points"], inst_node.inputs["Points"])
        links.new(info_node.outputs["Geometry"], inst_node.inputs["Instance"])

        links.new(input_node.outputs[0], join_node.inputs["Geometry"])
        links.new(inst_node.outputs["Instances"], join_node.inputs["Geometry"])
        links.new(join_node.outputs["Geometry"], output_node.inputs[0])

        bpy.context.view_layer.update()

        return {
            "success": True,
            "message": f"Scatter modifier applied to '{target.name}' with instances of '{instance.name}' (density={density}).",
            "modifier_name": mod.name,
        }
    except Exception as e:
        return {"error": str(e)}
