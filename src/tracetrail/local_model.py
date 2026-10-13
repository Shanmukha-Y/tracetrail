"""Verify loopback models without losing Ollama remote-routing metadata."""

from __future__ import annotations

import json
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

OLLAMA_URL = "http://127.0.0.1:11434"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Local model metadata requests cannot redirect")


def local_json(route: str, payload: dict | None = None) -> dict:
    if route not in ("/api/tags", "/api/show", "/api/version"):
        raise ValueError("Unsupported metadata route")
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(
        OLLAMA_URL + route,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with opener.open(request, timeout=10) as response:
        return json.loads(response.read(4 * 1024 * 1024))


def verify_local_weights(name: str) -> dict:
    """Reject remote models before any prompt is sent, including hidden aliases."""
    # The Python SDK currently drops remote_host and remote_model. Read raw JSON.
    matches = [m for m in local_json("/api/tags")["models"] if m.get("name") == name]
    if not matches:
        raise ValueError("The approved model tag is not installed")
    if any(m.get("remote_host") or m.get("remote_model") for m in matches):
        raise ValueError("Ollama remote or cloud routing is disabled in TraceTrail")
    show = local_json("/api/show", {"model": name})
    for record in [*matches, show]:
        if record.get("remote_host") or record.get("remote_model"):
            raise ValueError("Ollama remote or cloud routing is disabled in TraceTrail")
    if any(
        m.get("details", {}).get("format") != "gguf" or m.get("size", 0) < 1_000_000_000
        for m in matches
    ):
        raise ValueError("The approved model tag must have local GGUF weights")
    if show.get("details", {}).get("format") != "gguf":
        raise ValueError("The selected model does not report local GGUF weights")
    return {
        "name": name,
        "listed_digests": [m["digest"] for m in matches],
        "details": show.get("details", {}),
        "remote_routing": False,
        "ollama_version": local_json("/api/version").get("version"),
    }
