"""Unit tests for spatial reasoning and geometry nodes handlers."""

import types
import pytest
from unittest.mock import MagicMock, patch

from addon.handlers import spatial_tools, geometry_nodes


class TestSpatialTools:
    def test_snap_to_ground_object_not_found(self):
        scene = MagicMock()
        scene.objects.get.return_value = None
        res = spatial_tools.snap_to_ground(scene, "MissingObj")
        assert "error" in res
        assert "not found" in res["error"]

    def test_place_on_top_missing_child_or_parent(self):
        scene = MagicMock()
        scene.objects.get.side_effect = lambda name: MagicMock() if name == "Parent" else None
        res = spatial_tools.place_object_on_top(scene, "Child", "Parent")
        assert "error" in res
        assert "Child object 'Child' not found" in res["error"]

    def test_align_objects_invalid_axis(self):
        scene = MagicMock()
        res = spatial_tools.align_objects(scene, ["Obj1", "Obj2"], axis="W")
        assert "error" in res
        assert "Axis must be" in res["error"]

    def test_align_objects_insufficient_objects(self):
        scene = MagicMock()
        scene.objects.get.return_value = None
        res = spatial_tools.align_objects(scene, ["Obj1"], axis="X")
        assert "error" in res
        assert "Need at least 2 valid objects" in res["error"]


class TestGeometryNodesTools:
    def test_procedural_wire_success(self):
        scene = MagicMock()
        with patch("addon.handlers.geometry_nodes.bpy") as mock_bpy:
            mock_curve = MagicMock()
            mock_spline = MagicMock()
            pts = [MagicMock(), MagicMock(), MagicMock()]
            mock_points = MagicMock()
            mock_points.__getitem__.side_effect = lambda i: pts[i]
            mock_spline.bezier_points = mock_points
            mock_curve.splines.new.return_value = mock_spline
            mock_bpy.data.curves.new.return_value = mock_curve
            mock_obj = MagicMock()
            mock_obj.name = "Wire"
            mock_bpy.data.objects.new.return_value = mock_obj

            res = geometry_nodes.create_procedural_wire_curve(
                scene, start_point=(0, 0, 0), end_point=(1, 1, 1), name="Wire"
            )
            assert res.get("success") is True
            assert res.get("name") == "Wire"

    def test_scatter_target_missing(self):
        scene = MagicMock()
        scene.objects.get.return_value = None
        res = geometry_nodes.add_geometry_nodes_scatter(scene, "Target", "Instance")
        assert "error" in res
        assert "Target mesh 'Target' not found" in res["error"]
