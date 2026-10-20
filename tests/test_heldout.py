"""Test-only study inputs and runners. No inference or capability measurements."""

import importlib.util
import json
import shutil
import socket
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import ollama
import pytest

import tracetrail
from tracetrail import agent, pilot

REPOSITORY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "test_only_heldout", REPOSITORY / "scripts/heldout_v9.py"
)
heldout = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(heldout)
REAL_FOREIGN_CHECK = heldout.check_foreign_models


@pytest.fixture
def study(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("A unit test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket.socket, "connect_ex", no_network)
    root = tmp_path / "test-only-study"
    shutil.copytree(REPOSITORY / "src", root / "src")
    shutil.copytree(REPOSITORY / "scripts", root / "scripts")
    shutil.copytree(REPOSITORY / "fixtures/v9", root / "fixtures/v9")
    (root / "evaluation").mkdir()
    for name in (
        "cases-v9.json",
        "heldout-v9-rubric.md",
        "model-inventory-pilot-v1.json",
        "protocol-v8.json",
    ):
        shutil.copyfile(REPOSITORY / "evaluation" / name, root / "evaluation" / name)
    shutil.copyfile(REPOSITORY / "pyproject.toml", root / "pyproject.toml")
    shutil.copyfile(REPOSITORY / "uv.lock", root / "uv.lock")
    # Copied source filenames stand in for this test repository only.
    # Every model call below is a clearly marked test-only replacement.
    monkeypatch.setattr(tracetrail, "__file__", str(root / "src/tracetrail/__init__.py"))
    monkeypatch.setattr(agent, "__file__", str(root / "src/tracetrail/agent.py"))
    monkeypatch.setattr(pilot, "__file__", str(root / "src/tracetrail/pilot.py"))
    monkeypatch.setattr(heldout, "ROOT", root)
    monkeypatch.setattr(heldout, "SCRIPT", root / "scripts/heldout_v9.py")
    protocol = root / "evaluation/protocol-heldout-v9.json"
    heldout.freeze(
        Namespace(
            manifest=root / "evaluation/cases-v9.json",
            rubric=root / "evaluation/heldout-v9-rubric.md",
            output=protocol,
        )
    )
    monkeypatch.setattr(heldout, "check_foreign_models", lambda: None)
    return Namespace(
        root=root,
        protocol=protocol,
        output=root / "local-results/test-only.json",
        resume=False,
        max_runs=1,
    )


def test_study_source_drift_blocks_before_any_model_or_attempt(study, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Frozen source drift reached model execution")

    monkeypatch.setattr(pilot, "_execute", forbidden)
    source = study.root / "src/tracetrail/agent.py"
    source.write_text(source.read_text() + "\n# Test-only drift\n")
    with pytest.raises(ValueError, match="Frozen source changed"):
        heldout.run(study)
    assert not study.output.exists()


def test_study_preserves_failed_attempt_and_continues_without_retry(study, monkeypatch):
    calls = []

    def fail(case, root, cell, model):
        calls.append(cell["cell_id"])
        result = pilot._failure(case, cell, "runner", RuntimeError("Test-only runner failure"))
        pilot._score(case, result)
        return result

    monkeypatch.setattr(pilot, "_execute", fail)
    heldout.run(study)
    first = heldout.read(study.output)["runs"][0]
    assert first["status"] == "failed"
    assert first["claim_support_metrics"]["annotated_claim_count"] == 4
    assert first["claim_support_metrics"]["process_valid_supported_claim_count"] == 0
    study.resume, study.max_runs = True, 2
    heldout.run(study)
    data = heldout.read(study.output)
    assert data["runs"][0] == first
    assert calls == ["r1-c1-adaptive", "r1-c1-fixed"]
    assert data["planned_runs"] == 8
    assert data["attempted_all_target_cells"] is False
    assert study.output.stat().st_mode & 0o777 == 0o600


def test_study_resume_rejects_tampered_payload_before_another_call(study, monkeypatch):
    calls = []

    def fail(*args):
        calls.append(True)
        raise RuntimeError("Test-only original failure")

    monkeypatch.setattr(pilot, "_execute", fail)
    heldout.run(study)
    data = heldout.read(study.output)
    data["runs"][0]["error"] = "Tampered test-only output"
    study.output.write_text(json.dumps(data))
    study.resume, study.max_runs = True, 2
    with pytest.raises(ValueError, match="Saved attempt"):
        heldout.run(study)
    assert calls == [True]


def test_foreign_loaded_model_blocks_before_recording_or_executing_attempt(study, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A foreign loaded model reached execution")

    class FakeLoadedClient:
        """Test-only metadata; no network or model use."""

        def __init__(self, **kwargs):
            assert kwargs["host"] == "http://127.0.0.1:11434"
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False
            assert kwargs["headers"] == {"Authorization": "local-only-no-auth"}
            self._client = SimpleNamespace(close=lambda: None)

        def ps(self):
            return SimpleNamespace(models=[SimpleNamespace(model="TEST_ONLY_OTHER_MODEL")])

    monkeypatch.setattr(pilot, "_execute", forbidden)
    monkeypatch.setattr(heldout, "check_foreign_models", REAL_FOREIGN_CHECK)
    monkeypatch.setattr(ollama, "Client", FakeLoadedClient)
    with pytest.raises(ValueError, match="Foreign model is loaded"):
        heldout.run(study)
    assert heldout.read(study.output)["runs"] == []


def test_stored_verifier_rejects_resigned_inflated_claim_denominator(study, monkeypatch):
    def failed_report(case, root, cell, model):
        result = pilot._failure(case, cell, "runner", RuntimeError("Test-only failed output"))
        pilot._score(case, result)
        return result

    monkeypatch.setattr(pilot, "_execute", failed_report)
    heldout.run(study)
    data = heldout.read(study.output)
    run = data["runs"][0]
    run["claim_support_metrics"]["annotated_claim_count"] = 5
    run["heldout"]["result_sha256"] = heldout.canonical(
        {key: value for key, value in run.items() if key != "heldout"}
    )
    run["heldout"]["attempt_sha256"] = heldout.attempt_digest(run)
    study.output.write_text(json.dumps(data))
    with pytest.raises(AssertionError, match="Support counter differs: annotated_claim_count"):
        heldout.verify_data(Namespace(protocol=study.protocol, raw=study.output, sdk=None))
