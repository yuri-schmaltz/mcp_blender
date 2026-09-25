"""Unit tests for status bar indicator draw callback and toggle operator."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add repository root to path for addon imports
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from addon.ui.operators import BLENDERMCP_OT_ToggleServer
from addon.ui.panel import draw_statusbar_mcp


def test_draw_statusbar_mcp_when_stopped():
    mock_layout = MagicMock()
    mock_row = MagicMock()
    mock_layout.row.return_value = mock_row

    class DummyHeader:
        layout = mock_layout

    context = MagicMock()
    context.scene.blendermcp_server_running = False

    header = DummyHeader()
    draw_statusbar_mcp(header, context)

    mock_layout.row.assert_called_once_with(align=True)
    mock_row.operator.assert_called_once_with(
        "blendermcp.toggle_server", text="", icon="RADIOBUT_OFF", emboss=False
    )


def test_draw_statusbar_mcp_when_running():
    mock_layout = MagicMock()
    mock_row = MagicMock()
    mock_layout.row.return_value = mock_row

    class DummyHeader:
        layout = mock_layout

    context = MagicMock()
    context.scene.blendermcp_server_running = True

    header = DummyHeader()
    draw_statusbar_mcp(header, context)

    mock_layout.row.assert_called_once_with(align=True)
    mock_row.operator.assert_called_once_with(
        "blendermcp.toggle_server", text="", icon="RADIOBUT_ON", emboss=False
    )


def test_toggle_server_operator_stops_when_running(monkeypatch):
    import bpy

    called_ops = []

    def mock_stop():
        called_ops.append("stop")
        return {"FINISHED"}

    monkeypatch.setattr(bpy.ops.blendermcp, "stop_server", mock_stop)

    context = MagicMock()
    context.scene.blendermcp_server_running = True
    context.window_manager.windows = []

    op = BLENDERMCP_OT_ToggleServer()
    res = op.execute(context)

    assert res == {"FINISHED"}
    assert "stop" in called_ops


def test_toggle_server_operator_starts_when_stopped(monkeypatch):
    import bpy

    called_ops = []

    def mock_start():
        called_ops.append("start")
        return {"FINISHED"}

    monkeypatch.setattr(bpy.ops.blendermcp, "start_server", mock_start)

    context = MagicMock()
    context.scene.blendermcp_server_running = False
    context.window_manager.windows = []

    op = BLENDERMCP_OT_ToggleServer()
    res = op.execute(context)

    assert res == {"FINISHED"}
    assert "start" in called_ops
