"""Token-protected Windows host bridge for Codex CLI enrichment requests.

Run this process directly on the Windows host. Docker containers reach it through
host.docker.internal; the bridge never accepts a command or CLI flags from callers.
"""

import hmac
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading


MAX_REQUEST_BYTES = 500_000
REQUEST_TIMEOUT_SECONDS = float(os.getenv("CODEX_BRIDGE_TIMEOUT_SECONDS", "120"))
BRIDGE_TOKEN = os.getenv("CODEX_BRIDGE_TOKEN", "")
BRIDGE_HOST = os.getenv("CODEX_BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.getenv("CODEX_BRIDGE_PORT", "8765"))
RUN_LOCK = threading.Lock()


def _codex_command() -> str:
    configured = os.getenv("CODEX_COMMAND", "codex")
    if os.name == "nt" and configured == "codex":
        npm_command = Path(os.getenv("APPDATA", "")) / "npm" / "codex.cmd"
        if npm_command.is_file():
            return str(npm_command)
        return shutil.which("codex.cmd") or shutil.which("codex") or configured
    return shutil.which(configured) or configured


def _run_enrichment(prompt: str) -> dict:
    command = [
        _codex_command(),
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "--ignore-user-config",
        "--ignore-rules",
        prompt,
    ]
    with tempfile.TemporaryDirectory(prefix="kms-codex-") as work_dir:
        try:
            completed = subprocess.run(
                command,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Codex CLI was not found. Install it and run `codex login`.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex CLI timed out after {REQUEST_TIMEOUT_SECONDS:g} seconds") from exc

    if completed.returncode != 0:
        details = completed.stderr.strip() or "no error output"
        raise RuntimeError(f"Codex CLI exited with code {completed.returncode}: {details}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Codex CLI did not return JSON-only output") from exc
    if not isinstance(result, dict):
        raise RuntimeError("Codex CLI returned a JSON value instead of an object")
    return result


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "KmsCodexBridge/1.0"

    def do_POST(self):
        if self.path != "/enrich":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        if not BRIDGE_TOKEN:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "bridge token is not configured"})
            return
        authorization = self.headers.get("Authorization", "")
        expected = f"Bearer {BRIDGE_TOKEN}"
        if not hmac.compare_digest(authorization, expected):
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                raise ValueError("invalid request size")
            request = json.loads(self.rfile.read(content_length))
            prompt = request.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError("prompt is required")
            with RUN_LOCK:
                result = _run_enrichment(prompt)
            self._send_json(HTTPStatus.OK, result)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            print(f"Codex bridge error: {exc}", flush=True)
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    def log_message(self, format, *args):
        print(f"{self.client_address[0]} - {format % args}")

    def _send_json(self, status: HTTPStatus, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if not BRIDGE_TOKEN:
        raise SystemExit("Set CODEX_BRIDGE_TOKEN before starting the bridge.")
    server = ThreadingHTTPServer((BRIDGE_HOST, BRIDGE_PORT), BridgeHandler)
    print(f"Codex bridge listening on http://{BRIDGE_HOST}:{BRIDGE_PORT}")
    print("Keep this process on the Windows host; do not expose the port to the internet.")
    server.serve_forever()


if __name__ == "__main__":
    main()
