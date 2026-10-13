"""CLI security regressions with test-only clients and reports; no inference."""

import hashlib
import json
import os
import socket
import stat
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tracetrail import cli, telemetry


@pytest.fixture(autouse=True)
def network_forbidden(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A CLI regression test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def test_only_session(monkeypatch, tmp_path):
    """Fake model lifecycle requests and isolate the process lock from real runs."""
    constructed = []
    clients = []
    original_open = os.open

    def isolated_open(path, flags, mode=0o777, **kwargs):
        if str(path) == "/tmp/tracetrail-ollama.lock":
            path = tmp_path / "test-only-ollama.lock"
        return original_open(path, flags, mode, **kwargs)

    class TestOnlyClient:
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
    monkeypatch.setattr(cli.ollama, "Client", TestOnlyClient)
    monkeypatch.setattr(cli, "verify_local_weights", lambda name: {"name": name, "test_only": True})
    return constructed, clients


@pytest.fixture
def synthetic_case(tmp_path):
    fixture = tmp_path / "fixtures" / "test-only.json"
    fixture.parent.mkdir()
    record = {
        "eventID": "test-only-seed",
        "eventName": "StopLogging",
        "eventSource": "cloudtrail.amazonaws.com",
        "eventTime": "2026-01-01T10:00:00Z",
    }
    fixture.write_text(json.dumps({"Records": [record]}))
    return {
        "id": "test-only-case",
        "split": "development",
        "fixture": "fixtures/test-only.json",
        "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
        "seed_event_id": record["eventID"],
        "question": "Test-only lifecycle check",
        "hypotheses": [],
    }


def test_model_session_rejects_unapproved_tag_before_client(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("An unapproved tag reached a model client")

    monkeypatch.setattr(cli.ollama, "Client", forbidden)
    with (
        pytest.raises(ValueError, match="approved local model tags"),
        cli.model_session("synthetic-model:cloud"),
    ):
        raise AssertionError("An unapproved model session was opened")


def test_model_session_blocks_redirects_proxies_and_ambient_credentials(
    monkeypatch, test_only_session
):
    monkeypatch.setenv("OLLAMA_API_KEY", "synthetic-test-secret-never-used")
    monkeypatch.setenv("HTTPS_PROXY", "http://example.invalid:3128")
    constructed, clients = test_only_session
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


def test_unload_failure_preserves_report_and_marks_case_degraded(
    monkeypatch, test_only_session, synthetic_case, tmp_path
):
    _, clients = test_only_session
    captured = {}

    def test_only_investigation(store, seed, *args, **kwargs):
        clients[0].cleanup_error = RuntimeError("Synthetic cleanup failure")
        report = {
            "status": "completed",
            "failures": [],
            "evidence": [store.get(seed)],
            "model_history": [{"output": "Test-only raw output; no inference performed"}],
            "findings": [],
            "test_only": True,
        }
        captured["original"] = deepcopy(report)
        return report

    monkeypatch.setattr(cli, "investigate", test_only_investigation)
    monkeypatch.setattr(
        cli, "score_run", lambda case, result: {"failure_count": len(result["failures"])}
    )
    result = cli.run_case(synthetic_case, tmp_path, cli.MODELS[0], "adaptive")
    assert result["status"] == "degraded"
    assert result["evidence"] == captured["original"]["evidence"]
    assert result["model_history"] == captured["original"]["model_history"]
    assert result["failures"] == [{"phase": "unload", "error_type": "RuntimeError"}]
    assert result["metrics"]["failure_count"] == 1
    assert result["test_only"] is True


def test_direct_investigation_saves_original_report_when_unload_fails(
    monkeypatch, test_only_session, synthetic_case, tmp_path
):
    _, clients = test_only_session
    hypotheses = tmp_path / "test-only-hypotheses.json"
    hypotheses.write_text("[]")
    destination = tmp_path / "private-result.json"
    raw_output = "Test-only raw output preserved; no inference performed"

    def test_only_investigation(store, seed, *args, **kwargs):
        clients[0].cleanup_error = RuntimeError("Synthetic cleanup failure")
        return {
            "status": "completed",
            "failures": [],
            "evidence": [store.get(seed)],
            "model_history": [{"output": raw_output}],
            "test_only": True,
        }

    monkeypatch.setattr(cli, "investigate", test_only_investigation)
    exit_code = cli.main(
        [
            "investigate",
            str(tmp_path / synthetic_case["fixture"]),
            "--seed",
            synthetic_case["seed_event_id"],
            "--question",
            "Test-only cleanup check",
            "--hypotheses",
            str(hypotheses),
            "--output",
            str(destination),
        ]
    )
    result = json.loads(destination.read_text())
    assert exit_code == 1
    assert result["status"] == "degraded"
    assert result["model_history"] == [{"output": raw_output}]
    assert result["evidence"][0]["event_id"] == synthetic_case["seed_event_id"]
    assert result["failures"] == [{"phase": "unload", "error_type": "RuntimeError"}]
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600


def test_offline_evaluation_failure_is_not_cli_success(monkeypatch, tmp_path):
    monkeypatch.setattr(
        telemetry,
        "evaluate_local",
        lambda *args: {"status": "evaluation_failed", "uploads_enabled": False},
    )
    assert cli.main(["local-evaluate", str(tmp_path / "test-only-results.json")]) == 1


@pytest.mark.parametrize("status", ["failed", "invalid", "degraded"])
def test_comparison_preserves_unsuccessful_run_and_returns_failure(monkeypatch, tmp_path, status):
    manifest = Path(__file__).resolve().parents[1] / "evaluation/cases.json"
    destination = tmp_path / "test-only-comparison.json"

    def test_only_case(case, root, model, strategy):
        return {
            "status": status,
            "case_id": case["id"],
            "split": case["split"],
            "fixture_sha256": case["fixture_sha256"],
            "model": model,
            "strategy": strategy,
            "test_only": True,
            "failures": [{"phase": "test-only-failure"}],
        }

    monkeypatch.setattr(cli, "run_case", test_only_case)
    exit_code = cli.main(
        [
            "compare",
            "--manifest",
            str(manifest),
            "--case",
            "dev-role-pivot",
            "--models",
            cli.MODELS[1],
            "--output",
            str(destination),
        ]
    )
    result = json.loads(destination.read_text())
    assert exit_code == 1
    assert len(result["runs"]) == 1
    assert result["runs"][0]["status"] == status
    assert result["runs"][0]["test_only"] is True
    assert result["runs"][0]["metrics"]["annotation_coverage"] == 0
