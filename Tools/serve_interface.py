"""
Local server for the GemXpert interface, with photo analysis.

    Tools/.venv/bin/python Tools/serve_interface.py            # http://127.0.0.1:8765/

Serves Prototype/Interface and adds two endpoints the page uses when it is NOT opened through claude.ai
(on claude.ai the page asks Claude through the artifact's own connection instead):

    GET  /api/photo-status    -> {"available": bool, "reason": str}
    POST /api/analyse-photo   {"prompt": str, "images": [{"mediaType": str, "data": base64}]}
                              -> {"ok": true, "value": {...}} or {"ok": false, "code": str, "message": str}

The photo goes to the Claude API (Messages API, model claude-opus-5-5) with your own credentials:
  * ANTHROPIC_API_KEY in the environment, or
  * a file Tools/local_secrets.env containing the line  ANTHROPIC_API_KEY=sk-ant-...  (git-ignored), or
  * an `ant auth login` profile.
API use is billed to that account. The key stays in this process; the browser never sees it.
Binds to 127.0.0.1 only, so nothing outside this Mac can use it.
"""
import argparse
import json
import os
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SITE = os.path.join(ROOT, "Prototype", "Interface")
SECRETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local_secrets.env")
MODEL = "claude-opus-5-5"
MAX_BODY = 25 * 1024 * 1024
MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

try:
    import anthropic
except ImportError:  # the page shows the setup step instead of failing
    anthropic = None


def load_secrets():
    """Read ANTHROPIC_* lines from Tools/local_secrets.env without overriding the real environment."""
    if not os.path.exists(SECRETS):
        return
    with open(SECRETS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = (part.strip() for part in line.split("=", 1))
            if name.startswith("ANTHROPIC_") and value and name not in os.environ:
                os.environ[name] = value.strip('"').strip("'")


def has_credentials():
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return os.path.isdir(os.path.expanduser("~/.config/anthropic"))  # an `ant auth login` profile


def photo_status():
    if anthropic is None:
        return {"available": False, "reason": "The Anthropic library isn't installed. Start the server with Tools/.venv/bin/python (see RING_SPEC.md)."}
    if not has_credentials():
        return {"available": False, "reason": "Photo analysis on this local copy needs your Anthropic API key. Put the line ANTHROPIC_API_KEY=... in Tools/local_secrets.env, then restart the local server."}
    return {"available": True, "reason": ""}


def parse_json_answer(text):
    """The prompt asks for bare JSON; accept a fenced block or surrounding prose as well."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else text[text.find("{"): text.rfind("}") + 1]
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("answer is not a JSON object")
    return value


_client = None


def analyse(prompt, images):
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    content = [{"type": "image", "source": {"type": "base64", "media_type": img["mediaType"], "data": img["data"]}} for img in images]
    content.append({"type": "text", "text": prompt})
    # Server-side fallback: if the model declines on a safety classifier, the API retries on a suitable model.
    response = _client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": content}],
    )
    if response.stop_reason == "refusal":
        return {"ok": False, "code": "refused", "message": "Claude couldn't analyse this image."}
    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return {"ok": True, "value": parse_json_answer(text)}
    except (ValueError, json.JSONDecodeError):
        return {"ok": False, "code": "invalid_json", "message": "The answer wasn't valid JSON."}


def analyse_safely(body):
    status = photo_status()
    if not status["available"]:
        return {"ok": False, "code": "local_setup", "message": status["reason"]}
    prompt, images = body.get("prompt"), body.get("images")
    if not isinstance(prompt, str) or not isinstance(images, list) or not images or len(images) > 4:
        return {"ok": False, "code": "image_rejected", "message": "Send one to four images and a prompt."}
    if any(not isinstance(i, dict) or i.get("mediaType") not in MEDIA_TYPES or not isinstance(i.get("data"), str) for i in images):
        return {"ok": False, "code": "image_rejected", "message": "Images must be JPEG, PNG, WebP or GIF."}
    try:
        return analyse(prompt, images)
    except anthropic.AuthenticationError:
        return {"ok": False, "code": "local_auth", "message": "The API key was rejected."}
    except anthropic.PermissionDeniedError:
        return {"ok": False, "code": "local_auth", "message": "The API key can't use this model."}
    except anthropic.RateLimitError:
        return {"ok": False, "code": "rate_limited", "message": "Rate limited."}
    except anthropic.BadRequestError as err:
        print("Bad request:", err.message)
        code = "local_billing" if "credit" in str(err.message).lower() else "image_rejected"
        return {"ok": False, "code": code, "message": str(err.message)}
    except anthropic.APIStatusError as err:
        print("API error:", err.status_code, err.message)
        return {"ok": False, "code": "local_error", "message": f"Claude API error {err.status_code}."}
    except anthropic.APIConnectionError:
        return {"ok": False, "code": "local_network", "message": "Couldn't reach the Claude API."}


class Handler(SimpleHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/photo-status":
            return self.send_json(photo_status())
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/analyse-photo":
            return self.send_json({"ok": False, "code": "not_found", "message": "Unknown endpoint."}, 404)
        if self.headers.get("Origin") not in (None, f"http://{self.headers.get('Host')}"):
            return self.send_json({"ok": False, "code": "forbidden", "message": "Cross-site request refused."}, 403)
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self.send_json({"ok": False, "code": "image_rejected", "message": "Photo too large."}, 413)
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return self.send_json({"ok": False, "code": "image_rejected", "message": "Request wasn't JSON."}, 400)
        self.send_json(analyse_safely(body if isinstance(body, dict) else {}))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    load_secrets()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=SITE))
    status = photo_status()
    print(f"GemXpert interface on http://127.0.0.1:{args.port}/  ·  photo analysis: "
          + ("ready" if status["available"] else "off - " + status["reason"]), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
