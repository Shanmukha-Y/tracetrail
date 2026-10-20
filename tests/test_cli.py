"""CLI security regressions with test-only clients and reports; no inference."""

import json
import os
import socket
import stat
from types import SimpleNamespace

import pytest

from tracetrail import cli


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A CLI regression test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def fake_session(monkeypatch, tmp_path):
    """Fake model lifecycle requests and isolate the process lock from real runs."""
    constructed = []
    clients = []
    original_open = os.open

    def isolated_open(path, flags, mode=0o777, **kwargs):
        if str(path) == "/tmp/tracetrail-ollama.lock":
            path = tmp_path / "test-only-ollama.lock"
        return original_open(path, flags, mode, **kwargs)

    class FakeClient:
        def __init__(self, **kwargs):
            constructed.append(kwargs)
            self.cleanup_error = None
            self.calls = []
            clients.append(self)

        def ps(self):
            return SimpleNamespace(models=[])

        def generate(self, **kwargs):
            self.calls.append(kwargs)
            if self.cleanup_error is not None:
                raise self.cleanup_error

    monkeypatch.setattr(cli.os, "open", isolated_open)
    monkeypatch.setattr(cli.ollama, "Client", FakeClient)
    monkeypatch.setattr(cli, "verify_local_weights", lambda name: {"name": name, "test_only": True})
    return constructed, clients


def test_model_session_blocks_redirects_proxies_and_ambient_credentials(monkeypatch, fake_session):
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-secret-never-used")
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid:3128")
    constructed, clients = fake_session
    with cli.model_session(cli.MODELS[0]) as info:
        assert info["test_only"] is True
    transport = constructed[0]
    assert transport["host"] == "http://127.0.0.1:11434"
    assert transport["trust_env"] is False
    assert transport["follow_redirects"] is False
    assert transport["headers"] == {"Authorization": "local-only-no-auth"}
    assert "synthetic-test-secret-never-used" not in str(transport)
    assert clients[0].calls == [{"model": cli.MODELS[0], "prompt": "", "keep_alive": 0}]


def test_private_atomic_writer_ignores_predictable_temporary_symlink(tmp_path, monkeypatch):
    destination = tmp_path / "private-result.json"
    destination.write_text("previous complete result")
    victim = tmp_path / "unrelated.txt"
    victim.write_text("must remain intact")
    predictable_temp = destination.with_suffix(destination.suffix + ".tmp")
    predictable_temp.symlink_to(victim)
    original_dump = json.dump
    checked = []

    def inspect_private_write(data, stream, **kwargs):
        assert stat.S_IMODE(os.fstat(stream.fileno()).st_mode) == 0o600
        assert destination.read_text() == "previous complete result"
        checked.append(True)
        return original_dump(data, stream, **kwargs)

    monkeypatch.setattr(cli.json, "dump", inspect_private_write)
    cli.write_json(destination, {"test_only": True, "value": "synthetic private result"})
    assert checked == [True]
    assert json.loads(destination.read_text())["test_only"] is True
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert victim.read_text() == "must remain intact"
    assert predictable_temp.is_symlink()
    assert list(tmp_path.glob(".tracetrail-*")) == []


def test_failed_serialization_preserves_previous_result_and_removes_temporary_file(tmp_path):
    destination = tmp_path / "private-result.json"
    destination.write_text("previous complete result")
    with pytest.raises(ValueError):
        cli.write_json(destination, {"invalid_test_only_value": float("nan")})
    assert destination.read_text() == "previous complete result"
    assert list(tmp_path.glob(".tracetrail-*")) == []
