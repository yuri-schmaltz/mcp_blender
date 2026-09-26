"""Unit tests for local AI 3D generator handler."""

import os
from unittest.mock import MagicMock, patch

from addon.handlers import ai_3d_generator


class TestAI3DGenerator:
    def test_import_generated_mesh_missing_file(self):
        scene = MagicMock()
        res = ai_3d_generator.import_generated_mesh(scene, "/nonexistent/path/mesh.glb")
        assert "error" in res
        assert "not found on disk" in res["error"]

    def test_import_generated_mesh_unsupported_ext(self, tmp_path):
        scene = MagicMock()
        fake_file = tmp_path / "model.fbx"
        fake_file.write_text("dummy")
        res = ai_3d_generator.import_generated_mesh(scene, str(fake_file))
        assert "error" in res
        assert "Unsupported 3D file format" in res["error"]

    def test_generate_mesh_local_ai_missing_inputs(self):
        scene = MagicMock()
        res = ai_3d_generator.generate_mesh_local_ai(scene, prompt=None, image_path=None)
        assert "error" in res
        assert "Provide at least a text prompt" in res["error"]

    def test_generate_mesh_local_ai_missing_image_file(self):
        scene = MagicMock()
        res = ai_3d_generator.generate_mesh_local_ai(scene, image_path="/nonexistent/photo.png")
        assert "error" in res
        assert "not found" in res["error"]
