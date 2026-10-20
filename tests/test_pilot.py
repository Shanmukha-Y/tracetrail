"""Test-only pilot runners and metadata. No inference or network capability evidence."""

import hashlib
import importlib.metadata
import json
import shutil
import socket
from copy import deepcopy
from pathlib import Path

import pytest

from tracetrail import pilot


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A pilot unit test attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def setup_pilot(tmp_path, monkeypatch):
    source_root = Path(pilot.__file__).resolve().parents[2]
    root = tmp_path / "test-only-repository"
    shutil.copytree(source_root / "src", root / "src")
    (root / "evaluation").mkdir()
    original = json.loads((source_root / "evaluation/cases-v7.json").read_text())
    original["cases"] = [c for c in original["cases"] if c["split"] == "development"]
    for case in original["cases"]:
        destination = root / case["fixture"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / case["fixture"], destination)
    manifest = root / "evaluation/cases-test-only.json"
    manifest.write_text(json.dumps(original))
    agent, schemas = pilot._runtime()
    import tracetrail

    # These tests execute copied frozen sources in an isolated test repository.
    # Module filenames are stand-ins only; every inference entry point is fake.
    monkeypatch.setattr(pilot, "__file__", str(root / "src/tracetrail/pilot.py"))
    monkeypatch.setattr(agent, "__file__", str(root / "src/tracetrail/agent.py"))
    monkeypatch.setattr(tracetrail, "__file__", str(root / "src/tracetrail/__init__.py"))
    names = [
        "gemma4:e2b-it-q4_K_M",
        "gemma4:12b-it-q4_K_M",
        "qwen3.8:27b-q4_K_M",
        "mistral-small3.2:24b",
        "gemma4:31b-it-q4_K_M",
    ]
    models = [
        {
            "name": name,
            "digest": f"test-only-digest-{i}",
            "listed_digests": [f"test-only-digest-{i}"],
            "ollama_version": "test-only-ollama-version",
        }
        for i, name in enumerate(names)
    ]
    frozen = {
        "protocol_id": pilot.PILOT_ID,
        "protocol": deepcopy(agent.PROTOCOL),
        "prompt_sha256": hashlib.sha256(
            (agent.SYSTEM + agent.PLAN + agent.FINAL).encode()
        ).hexdigest(),
        "schema_sha256": {
            name: pilot._canonical(cls.model_json_schema()) for name, cls in schemas.items()
        },
        "source_sha256": {
            path.relative_to(root).as_posix(): pilot._sha(path)
            for path in (root / "src").rglob("*.py")
        },
        "case_manifest": {
            "path": manifest.relative_to(root).as_posix(),
            "sha256": pilot._sha(manifest),
        },
        "pilot": {
            "case_ids": [case["id"] for case in original["cases"]],
            "models": models,
            "repeats": 2,
        },
        "runtime_gate": {"overall_wall_seconds": 5400, "overhead_factor": 1.2},
        "versions": {
            name: importlib.metadata.version(name)
            for name in (
                "langchain",
                "langchain-core",
                "langchain-ollama",
                "langgraph",
                "langsmith",
                "ollama",
                "pydantic",
            )
        },
    }
    protocol = root / "evaluation/protocol-test-only.json"
    protocol.write_text(json.dumps(frozen))
    output = root / "local-results/test-only-pilot.json"
    calls = []
    reports = []
    model_map = {model["name"]: model for model in models}
    clock = {"now": 0.0, "seconds": 1.0}

    def metadata(name):
        return {
            "name": name,
            "listed_digests": model_map[name]["listed_digests"],
            "remote_routing": False,
            "ollama_version": "test-only-ollama-version",
        }

    def fake_run(case, actual_root, model, strategy):
        """Clearly test-only implementation, never a capability measurement."""
        assert actual_root == root
        assert case["split"] == "development"
        calls.append((case["id"], model, strategy))
        clock["now"] += clock["seconds"]
        result = {
            "case_id": case["id"],
            "split": "development",
            "fixture_sha256": case["fixture_sha256"],
            "model": model,
            "strategy": strategy,
            "status": "completed",
            "failures": [],
            "test_only": False,
            "model_calls": 1,
            "query_count": 0,
            "model_history": [
                {"output": f"Test-only raw report number {len(calls)}; no model called"}
            ],
            "model_info": {
                "listed_digests": model_map[model]["listed_digests"],
                "loaded_models": [{"model": model, "digest": model_map[model]["digest"]}],
                "resources": {
                    "status": "completed",
                    "sample_count": 2,
                    "error_count": 0,
                    "foreign_model_observed": False,
                    "ollama_sample_count": 2,
                    "matching_model_sample_count": 1,
                    "rss_complete_sample_count": 2,
                    "sampled_maxima": {
                        "ollama_reported_size_bytes": 10,
                        "ollama_reported_size_vram_bytes": 8,
                        "listener_process_tree_rss_sum_bytes": 12,
                    },
                },
            },
        }
        reports.append(deepcopy(result))
        return result

    def fake_score(case, result):
        result["metrics"] = {"test_only_scorer": True}
        result["claim_support_metrics"] = {"process_valid": result["status"] == "completed"}
        result["evaluation"] = {"primary_scorer": "claim-support-v1"}

    monkeypatch.setattr(pilot, "_model_info", metadata)
    monkeypatch.setattr(pilot, "_run_case", fake_run)
    monkeypatch.setattr(pilot, "_score", fake_score)
    monkeypatch.setattr(pilot.time, "monotonic", lambda: clock["now"])
    return {
        "root": root,
        "protocol": protocol,
        "output": output,
        "frozen": frozen,
        "calls": calls,
        "reports": reports,
        "clock": clock,
        "fake_run": fake_run,
    }


def document(setup):
    return json.loads(setup["output"].read_text())


@pytest.mark.parametrize("field", ["source_sha256"])
def test_freeze_mismatch_stops_before_any_calls(setup_pilot, field):
    s = setup_pilot
    value = deepcopy(s["frozen"])
    if field == "protocol":
        value[field]["temperature"] = 1
    elif isinstance(value[field], dict):
        key = next(iter(value[field]))
        value[field][key] = "not-the-frozen-value"
    else:
        value[field] = "not-the-frozen-value"
    s["protocol"].write_text(json.dumps(value))
    with pytest.raises((ValueError, FileNotFoundError)):
        pilot.run_pilot(s["protocol"], s["output"])
    assert s["calls"] == []
    assert not s["output"].exists()


def test_resume_rejects_tampered_recorded_payload(setup_pilot):
    s = setup_pilot
    pilot.run_pilot(s["protocol"], s["output"], max_runs=1)
    data = document(s)
    data["runs"][0]["model_history"][0]["output"] = "Tampered test-only output"
    s["output"].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="payload hash"):
        pilot.run_pilot(s["protocol"], s["output"], resume=True)
    assert len(s["calls"]) == 1


def test_failures_and_invalid_reports_are_preserved_and_never_retried(setup_pilot, monkeypatch):
    s = setup_pilot
    fake_run = s["fake_run"]
    attempts = []

    def failures(*args):
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError("Test-only inference runner error")
        result = fake_run(*args)
        result["status"] = "invalid"
        result["failures"] = [{"phase": "validation", "error_type": "TestOnlyInvalidReport"}]
        return result

    monkeypatch.setattr(pilot, "_run_case", failures)
    pilot.run_pilot(s["protocol"], s["output"], max_runs=2)
    first = document(s)["runs"]
    assert [r["status"] for r in first] == ["failed", "invalid"]
    assert first[0]["error"] == "Test-only inference runner error"
    assert first[0]["test_only"] is False
    pilot.run_pilot(s["protocol"], s["output"], max_runs=3, resume=True)
    assert len(attempts) == 3
    assert document(s)["runs"][:2] == first


def test_effective_digest_mismatch_invalidates_and_rescores_original_output(
    setup_pilot, monkeypatch
):
    s = setup_pilot
    fake_run = s["fake_run"]

    def mismatch(*args):
        result = fake_run(*args)
        result["model_info"]["loaded_models"][0]["digest"] = "wrong-effective-digest"
        return result

    monkeypatch.setattr(pilot, "_run_case", mismatch)
    pilot.run_pilot(s["protocol"], s["output"], max_runs=1)
    result = document(s)["runs"][0]
    assert result["status"] == "invalid"
    assert result["model_history"] == s["reports"][0]["model_history"]
    assert result["claim_support_metrics"]["process_valid"] is False
    assert result["pilot_model_identity"]["verified"] is False
