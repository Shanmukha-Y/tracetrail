"""Test local telemetry guards. These inputs are test data, not model evidence."""

import socket
from pathlib import Path

import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import var_child_runnable_config
from langchain_core.tracers.context import tracing_v2_callback_var
from langsmith.utils import tracing_is_enabled

from tracetrail.telemetry import (
    local_context,
    new_local_trace_collector,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def network_forbidden(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("A local-only test tried to connect to the network.")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-only-secret-never-used")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://example.invalid")
    yield attempts
    assert attempts == []


def test_local_context_disables_ambient_and_inherited_tracing(network_forbidden):
    inherited_callback = object()
    token = tracing_v2_callback_var.set(inherited_callback)
    config_token = var_child_runnable_config.set({"callbacks": [inherited_callback]})
    try:
        collector = new_local_trace_collector()
        with local_context():
            assert tracing_is_enabled() is False
            assert tracing_v2_callback_var.get() is None
            assert var_child_runnable_config.get() is None
            assert (
                RunnableLambda(lambda number: number + 1).invoke(
                    4, config={"callbacks": [collector]}
                )
                == 5
            )
        assert tracing_v2_callback_var.get() is inherited_callback
        assert var_child_runnable_config.get()["callbacks"] == [inherited_callback]
        assert len(collector.traced_runs) == 1
    finally:
        var_child_runnable_config.reset(config_token)
        tracing_v2_callback_var.reset(token)
