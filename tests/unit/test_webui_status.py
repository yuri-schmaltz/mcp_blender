import json
import time
import urllib.request
from addon.webui_server import BlenderMCPWebUIServer


def test_webui_status_endpoint():
    server = BlenderMCPWebUIServer(port=8915)
    server.start()
    try:
        time.sleep(0.3)
        url = "http://127.0.0.1:8915/api/status"
        req = urllib.request.urlopen(url, timeout=2.0)
        data = json.loads(req.read().decode("utf-8"))
        assert data["status"] == "online"
        assert "blender_version" in data
        assert "python_version" in data
        assert "commands_registered" in data
    finally:
        server.stop()
