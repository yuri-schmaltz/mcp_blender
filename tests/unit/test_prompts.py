import pytest
from src.blender_mcp.server import (
    asset_creation_strategy,
    studio_lighting_setup,
    procedural_geometry_pipeline,
    print3d_preparation_pipeline,
    spatial_layout_composition,
)


def test_asset_creation_strategy_prompt():
    prompt = asset_creation_strategy()
    assert "AQUISIÇÃO DE ASSETS" in prompt
    assert "BlenderKit" in prompt


def test_studio_lighting_setup_prompt():
    prompt = studio_lighting_setup(style="automotive")
    assert "automotive" in prompt
    assert "setup_product_studio" in prompt


def test_procedural_geometry_pipeline_prompt():
    prompt = procedural_geometry_pipeline(effect="wireframe")
    assert "wireframe" in prompt
    assert "create_geometry_nodes_tree" in prompt


def test_print3d_preparation_pipeline_prompt():
    prompt = print3d_preparation_pipeline()
    assert "check_mesh_integrity" in prompt
    assert "auto_repair_mesh" in prompt


def test_spatial_layout_composition_prompt():
    prompt = spatial_layout_composition()
    assert "snap_to_ground" in prompt
    assert "place_object_on_top" in prompt
