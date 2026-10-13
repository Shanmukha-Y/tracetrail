"""Local transport regressions with synthetic metadata; no inference or network."""

import asyncio
import json
import socket
from copy import deepcopy
from urllib.request import ProxyHandler

import pytest

from tracetrail import agent, local_model


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A metadata regression test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


def metadata():
    return {
        "name": agent.MODELS[0],
        "model": agent.MODELS[0],
        "digest": "synthetic-test-digest",
        "size": 2_000_000_000,
        "details": {"format": "gguf"},
    }


@pytest.mark.parametrize("remote_field", ["remote_host", "remote_model"])
def test_raw_remote_tag_rejected_before_model_details(monkeypatch, remote_field):
    item = metadata()
    item[remote_field] = "synthetic-remote-routing"
    calls = []

    def fake_metadata(route, payload=None):
        calls.append(route)
        assert route == "/api/tags", "Remote aliases must fail before any detail request"
        return {"models": [item]}

    monkeypatch.setattr(local_model, "local_json", fake_metadata)
    with pytest.raises(ValueError, match="remote or cloud routing"):
        local_model.verify_local_weights(agent.MODELS[0])
    assert calls == ["/api/tags"]


@pytest.mark.parametrize("remote_field", ["remote_host", "remote_model"])
def test_remote_model_details_rejected_before_version_or_inference(monkeypatch, remote_field):
    calls = []

    def fake_metadata(route, payload=None):
        calls.append(route)
        if route == "/api/tags":
            return {"models": [metadata()]}
        assert route == "/api/show"
        assert payload == {"model": agent.MODELS[0]}
        return {"details": {"format": "gguf"}, remote_field: "synthetic-remote-routing"}

    monkeypatch.setattr(local_model, "local_json", fake_metadata)
    with pytest.raises(ValueError, match="remote or cloud routing"):
        local_model.verify_local_weights(agent.MODELS[0])
    assert calls == ["/api/tags", "/api/show"]


@pytest.mark.parametrize("changes", [{"size": 123}, {"details": {"format": "remote"}}])
def test_metadata_without_large_local_gguf_weights_is_rejected(monkeypatch, changes):
    item = {**metadata(), **changes}

    def fake_metadata(route, payload=None):
        if route == "/api/tags":
            return {"models": [item]}
        assert route == "/api/show"
        return {"details": {"format": "gguf"}}

    monkeypatch.setattr(local_model, "local_json", fake_metadata)
    with pytest.raises(ValueError, match="local GGUF weights"):
        local_model.verify_local_weights(agent.MODELS[0])


def test_local_weight_metadata_preserves_frozen_digest(monkeypatch):
    calls = []

    def fake_metadata(route, payload=None):
        calls.append((route, payload))
        if route == "/api/tags":
            return {"models": [metadata()]}
        if route == "/api/show":
            return {"details": {"format": "gguf"}}
        assert route == "/api/version"
        return {"version": "synthetic-test-version"}

    monkeypatch.setattr(local_model, "local_json", fake_metadata)
    result = local_model.verify_local_weights(agent.MODELS[0])
    assert result["listed_digests"] == ["synthetic-test-digest"]
    assert result["remote_routing"] is False
    assert calls == [
        ("/api/tags", None),
        ("/api/show", {"model": agent.MODELS[0]}),
        ("/api/version", None),
    ]


def test_metadata_transport_ignores_proxy_credentials_and_redirects(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid:3128")
    monkeypatch.setenv("HTTP_PROXY", "http://example.invalid:3128")
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-secret-never-used")
    captured = {}

    class TestOnlyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert 0 < limit <= 4 * 1024 * 1024
            return json.dumps({"models": []}).encode()

    class TestOnlyOpener:
        def open(self, request, *, timeout):
            captured["request"] = request
            assert timeout <= 10
            return TestOnlyResponse()

    def fake_opener(*handlers):
        captured["handlers"] = handlers
        return TestOnlyOpener()

    monkeypatch.setattr(local_model, "build_opener", fake_opener)
    assert local_model.local_json("/api/tags") == {"models": []}
    proxy = next(h for h in captured["handlers"] if isinstance(h, ProxyHandler))
    assert proxy.proxies == {}
    request = captured["request"]
    assert request.full_url == "http://127.0.0.1:11434/api/tags"
    assert request.get_header("Authorization") is None
    redirect = next(h for h in captured["handlers"] if isinstance(h, local_model._NoRedirect))
    with pytest.raises(ValueError, match="cannot redirect"):
        redirect.redirect_request(request, None, 307, "redirect", {}, "https://example.invalid")


def test_unknown_metadata_route_rejected_before_transport(monkeypatch):
    def forbidden_opener(*args):
        raise AssertionError("An unsupported route reached the transport")

    monkeypatch.setattr(local_model, "build_opener", forbidden_opener)
    with pytest.raises(ValueError, match="Unsupported metadata route"):
        local_model.local_json("https://example.invalid/api/tags")


def test_unapproved_model_rejected_before_preflight_or_client(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An unapproved model reached preflight or model construction")

    monkeypatch.setattr(agent, "verify_local_weights", forbidden)
    monkeypatch.setattr(agent, "ChatOllama", forbidden)
    with pytest.raises(ValueError, match="approved local model tags"):
        agent.make_model("synthetic-model:cloud")


def test_real_model_client_construction_blocks_redirects_proxies_and_ambient_key(monkeypatch):
    """Inspect real SDK transports without sending requests or running a model."""
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-secret-never-used")
    monkeypatch.setenv("HTTP_PROXY", "http://example.invalid:3128")
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid:3128")
    verified = []

    def fake_preflight(name):
        verified.append(name)
        return deepcopy(metadata())

    monkeypatch.setattr(agent, "verify_local_weights", fake_preflight)
    model = agent.make_model(agent.MODELS[0])
    try:
        assert verified == [agent.MODELS[0]]
        for client in (model._client._client, model._async_client._client):
            assert str(client.base_url).startswith("http://127.0.0.1:11434")
            assert client.follow_redirects is False
            assert client._trust_env is False
            assert client.headers["authorization"] == "local-only-no-auth"
            assert "synthetic-test-secret-never-used" not in str(client.headers)
    finally:
        model._client._client.close()
        asyncio.run(model._async_client._client.aclose())
