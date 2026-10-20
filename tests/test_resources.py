"""Test-only resource metadata/process readers; no inference or network."""

import socket
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from tracetrail import cli

MODEL = "test-only-local-model"


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A resource test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def session_environment(monkeypatch, tmp_path):
    events = []
    original_open, original_fdopen = cli.os.open, cli.os.fdopen

    def isolated_open(path, flags, mode=0o777, **kwargs):
        if str(path) == "/tmp/tracetrail-ollama.lock":
            path = tmp_path / "test-only-lock"
        return original_open(path, flags, mode, **kwargs)

    @contextmanager
    def tracked_fdopen(*args, **kwargs):
        with original_fdopen(*args, **kwargs) as stream:
            try:
                yield stream
            finally:
                events.append("lock_close")

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False

        def ps(self):
            events.append("ps")
            return SimpleNamespace(models=[])

        def generate(self, **kwargs):
            events.append("unload")
            assert kwargs == {"model": cli.MODELS[0], "prompt": "", "keep_alive": 0}

    monkeypatch.setattr(cli.os, "open", isolated_open)
    monkeypatch.setattr(cli.os, "fdopen", tracked_fdopen)
    monkeypatch.setattr(cli.fcntl, "flock", lambda *args: events.append("lock"))
    monkeypatch.setattr(cli.ollama, "Client", Client)
    monkeypatch.setattr(cli, "verify_local_weights", lambda name: {"name": name})
    return events


def test_investigation_exception_still_stops_sampler_and_unloads(monkeypatch, session_environment):
    events = session_environment

    class Sampler:
        def __init__(self, name):
            pass

        def start(self):
            events.append("sampler_start")

        def stop(self):
            events.append("sampler_stop")
            return {"status": "completed", "error_count": 0, "samples": []}

    monkeypatch.setattr(cli, "ResourceSampler", Sampler)
    with pytest.raises(RuntimeError, match="Test-only investigation failure"):
        with cli.model_session(cli.MODELS[0], measure_resources=True):
            raise RuntimeError("Test-only investigation failure")
    assert events.index("sampler_stop") < events.index("unload") < events.index("lock_close")
