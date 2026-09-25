import json
import urllib.error
import urllib.request

from ..core.router import mcp_command
from ..utils.helpers import get_addon_prefs as get_prefs
from .scene_tools import get_viewport_screenshot


def _get_ollama_models(base_url):
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


@mcp_command(name="analyze_viewport_visuals", read_only=True)
def analyze_viewport_visuals(
    scene,
    prompt="Describe the current 3D scene from the viewport's perspective. Check for any floating objects, overlapping geometries, clipping, or incorrect physical alignments.",
    model="moondream",
):
    """
    Captures a screenshot of the active 3D viewport and uses a local vision model (e.g. moondream via Ollama)
    to perform a visual critique.
    """
    try:
        screenshot_res = get_viewport_screenshot(scene, max_size=800, filepath=None, format="png")
        if "error" in screenshot_res:
            return {"error": f"Failed to capture screenshot: {screenshot_res['error']}"}

        img_base64 = screenshot_res["image_base64"]

        # 4. Resolve preferences and URL
        prefs = get_prefs()
        if not prefs:
            return {"error": "Preferences not found"}

        provider = prefs.llm_provider
        base_url = prefs.llm_base_url

        if provider == "OLLAMA":
            if not base_url:
                base_url = "http://127.0.0.1:11434"

            # Query Ollama API
            url = f"{base_url.rstrip('/')}/api/generate"
            payload = {"model": model, "prompt": prompt, "images": [img_base64], "stream": False}

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    response_text = res_data.get("response", "")
                    return {"status": "success", "analysis": response_text, "model_used": model}
            except urllib.error.HTTPError as he:
                error_msg = he.read().decode("utf-8")
                if "not found" in error_msg.lower() or he.code == 404:
                    installed = _get_ollama_models(base_url)
                    return {
                        "error": f"Ollama vision model '{model}' not found. Please run 'ollama pull {model}' on the host machine. Installed models: {installed}"
                    }
                return {"error": f"Ollama HTTP Error {he.code}: {error_msg}"}
        else:
            return {
                "error": "Visual critic currently requires local Ollama (e.g. moondream or llava). Please configure Ollama in Blender MCP preferences."
            }

    except Exception as e:
        return {"error": str(e)}

