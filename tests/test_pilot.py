"""Test-only pilot runners and metadata. No inference or network capability evidence."""

import hashlib
import importlib.metadata
import json
import os
import shutil
import socket
import stat
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


def test_first_stage_exact_order_and_explicit_stage_expansion(setup_pilot):
    s = setup_pilot
    assert pilot.run_pilot(s["protocol"], s["output"]) == 1
    first = document(s)
    assert len(first["runs"]) == 10
    assert [r["pilot"]["cell"] for r in first["runs"]] == first["plan"][:10]
    assert [r["strategy"] for r in first["runs"][:4]] == ["adaptive", "fixed", "fixed", "adaptive"]
    assert len({r["case_id"] for r in first["runs"]}) == 1
    assert first["runtime_gate"]["max_total_runs"] == 40
    assert first["runtime_gate"]["projected_forty_seconds_with_overhead"] == 48
    gate = deepcopy(first["runtime_gate"])
    assert pilot.run_pilot(s["protocol"], s["output"], stage=2, resume=True) == 1
    second = document(s)
    assert len(second["runs"]) == 20
    assert second["runtime_gate"] == gate
    assert second["runs"][:10] == first["runs"]
    assert pilot.run_pilot(s["protocol"], s["output"], stage=3, resume=True) == 0
    final = document(s)
    assert len(final["runs"]) == len(s["calls"]) == 40
    assert final["runs"][:20] == second["runs"]
    assert final["status"] == "completed"
    assert final["overall_wall_seconds"] == 40
    assert len({r["pilot"]["cell"]["cell_id"] for r in final["runs"]}) == 40
    assert {r["pilot"]["cell"]["repeat"] for r in final["runs"]} == {1, 2}
    assert len({r["model_history"][0]["output"] for r in final["runs"]}) == 40


def test_new_stage_three_and_expansion_before_ten_are_rejected(setup_pilot):
    s = setup_pilot
    with pytest.raises(ValueError, match="start with stage 1"):
        pilot.run_pilot(s["protocol"], s["output"], stage=3)
    pilot.run_pilot(s["protocol"], s["output"], max_runs=3)
    before = s["output"].read_bytes()
    with pytest.raises(ValueError, match="ten-cell"):
        pilot.run_pilot(s["protocol"], s["output"], stage=2, resume=True)
    assert s["output"].read_bytes() == before
    assert len(s["calls"]) == 3


def test_cumulative_max_runs_and_no_overwrite(setup_pilot):
    s = setup_pilot
    pilot.run_pilot(s["protocol"], s["output"], max_runs=2)
    before = s["output"].read_bytes()
    with pytest.raises(FileExistsError):
        pilot.run_pilot(s["protocol"], s["output"])
    assert s["output"].read_bytes() == before
    pilot.run_pilot(s["protocol"], s["output"], max_runs=4, resume=True)
    assert len(s["calls"]) == len(document(s)["runs"]) == 4


@pytest.mark.parametrize(
    "field", ["prompt_sha256", "schema_sha256", "protocol", "source_sha256", "case_manifest"]
)
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


def test_frozen_fixture_drift_and_heldout_selection_rejected(setup_pilot):
    s = setup_pilot
    manifest = s["root"] / s["frozen"]["case_manifest"]["path"]
    data = json.loads(manifest.read_text())
    (s["root"] / data["cases"][0]["fixture"]).write_text('{"Records":[]}')
    with pytest.raises(ValueError, match="Fixture hash mismatch"):
        pilot.run_pilot(s["protocol"], s["output"])
    assert not s["calls"]


def test_source_drift_between_cells_preserves_attempts(setup_pilot, monkeypatch):
    s = setup_pilot
    fake_run = s["fake_run"]

    def drift(*args):
        result = fake_run(*args)
        (s["root"] / "src/tracetrail/__init__.py").write_text("# Test-only source drift\n")
        return result

    monkeypatch.setattr(pilot, "_run_case", drift)
    with pytest.raises(ValueError, match="source hash mismatch"):
        pilot.run_pilot(s["protocol"], s["output"])
    assert len(s["calls"]) == len(document(s)["runs"]) == 1


def test_resume_rejects_payload_tampering_and_changed_protocol(setup_pilot):
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


def test_digest_mismatch_before_inference_and_after_output_preserves_failure(
    setup_pilot, monkeypatch
):
    s = setup_pilot
    monkeypatch.setattr(
        pilot,
        "_model_info",
        lambda name: {"name": name, "listed_digests": ["wrong"], "remote_routing": False},
    )
    pilot.run_pilot(s["protocol"], s["output"], max_runs=1)
    assert not s["calls"]
    assert document(s)["runs"][0]["status"] == "failed"
    assert "frozen local inventory" in document(s)["runs"][0]["error"]


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


@pytest.mark.parametrize("issue", ["slow", "foreign", "missing_rss", "missing_model"])
def test_runtime_or_measurement_gate_blocks_repeat_two(setup_pilot, monkeypatch, issue):
    s = setup_pilot
    fake_run = s["fake_run"]
    s["clock"]["seconds"] = 120 if issue == "slow" else 1

    def measured(*args):
        result = fake_run(*args)
        resources = result["model_info"]["resources"]
        if issue == "foreign":
            resources["foreign_model_observed"] = True
        if issue == "missing_rss":
            resources["rss_complete_sample_count"] = 1
        if issue == "missing_model":
            resources["matching_model_sample_count"] = 0
        return result

    monkeypatch.setattr(pilot, "_run_case", measured)
    pilot.run_pilot(s["protocol"], s["output"])
    assert document(s)["runtime_gate"]["max_total_runs"] == 20
    pilot.run_pilot(s["protocol"], s["output"], stage=3, resume=True)
    assert len(s["calls"]) == 20
    assert document(s)["target_runs"] == 20


def test_keyboard_interrupt_preserves_attempt_and_does_not_retry(setup_pilot, monkeypatch):
    s = setup_pilot
    monkeypatch.setattr(
        pilot, "_run_case", lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    assert pilot.run_pilot(s["protocol"], s["output"]) == 1
    first = document(s)["runs"][0]
    assert first["failures"][0]["phase"] == "pilot_interrupted"
    monkeypatch.setattr(pilot, "_run_case", s["fake_run"])
    pilot.run_pilot(s["protocol"], s["output"], max_runs=2, resume=True)
    assert document(s)["runs"][0] == first
    assert len(s["calls"]) == 1


def test_started_attempt_saved_before_runner_and_killed_attempt_not_repeated(
    setup_pilot, monkeypatch
):
    s = setup_pilot

    def killed(*args):
        assert document(s)["runs"][-1]["status"] == "running"
        raise SystemExit("Test-only process death")

    monkeypatch.setattr(pilot, "_run_case", killed)
    with pytest.raises(SystemExit):
        pilot.run_pilot(s["protocol"], s["output"])
    monkeypatch.setattr(pilot, "_run_case", s["fake_run"])
    pilot.run_pilot(s["protocol"], s["output"], max_runs=2, resume=True)
    first = document(s)["runs"][0]
    assert first["status"] == "failed"
    assert first["inference_calls_unknown"] is True
    assert first["pilot"]["wall_seconds_unknown"] is True
    assert len(s["calls"]) == 1


def test_atomic_writer_private_and_failed_serialization_preserves_previous(tmp_path, monkeypatch):
    path = tmp_path / "private.json"
    pilot._write(path, {"previous": True}, create=True)
    before = path.read_bytes()
    dump = pilot.json.dump

    def private_dump(data, stream, **kwargs):
        assert stat.S_IMODE(os.fstat(stream.fileno()).st_mode) == 0o600
        assert path.read_bytes() == before
        return dump(data, stream, **kwargs)

    monkeypatch.setattr(pilot.json, "dump", private_dump)
    with pytest.raises(ValueError):
        pilot._write(path, {"test_only_nan": float("nan")})
    assert path.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".tracetrail-pilot-*"))
    with pytest.raises(FileExistsError):
        pilot._write(path, {"overwrite": True}, create=True)


def test_output_lock_and_symlinks_prevent_duplicate_writers(setup_pilot):
    s = setup_pilot
    with pilot._output_lock(s["output"]), pytest.raises(ValueError, match="Another pilot"):
        pilot.run_pilot(s["protocol"], s["output"])
    victim = s["root"] / "private-victim.json"
    victim.write_text("Unrelated data")
    s["output"].symlink_to(victim)
    with pytest.raises(ValueError, match="symbolic link"):
        pilot.run_pilot(s["protocol"], s["output"])
    assert victim.read_text() == "Unrelated data"
    assert not s["calls"]


def test_lazy_actual_runner_enables_resource_measurement(monkeypatch):
    from tracetrail import cli

    seen = []
    monkeypatch.setattr(cli, "run_case", lambda *args, **kwargs: seen.append((args, kwargs)) or {})
    assert pilot._run_case({"test_only": True}, Path("/test-only"), "test-only", "adaptive") == {}
    assert seen[0][1] == {"measure_resources": True}


def test_another_imported_checkout_is_rejected(setup_pilot, monkeypatch):
    from tracetrail import agent

    monkeypatch.setattr(agent, "__file__", "/test-only-other-checkout/src/tracetrail/agent.py")
    with pytest.raises(ValueError, match="exact imported runtime checkout"):
        pilot.run_pilot(setup_pilot["protocol"], setup_pilot["output"])
    assert not setup_pilot["calls"]


def test_package_and_server_version_drift_rejected(setup_pilot, monkeypatch):
    s = setup_pilot
    frozen = deepcopy(s["frozen"])
    frozen["versions"]["langsmith"] = "test-only-wrong-version"
    s["protocol"].write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match="package version mismatch"):
        pilot.run_pilot(s["protocol"], s["output"])
    s["protocol"].write_text(json.dumps(s["frozen"]))
    real_fake_metadata = pilot._model_info

    def wrong_server(name):
        return {**real_fake_metadata(name), "ollama_version": "wrong-server"}

    monkeypatch.setattr(pilot, "_model_info", wrong_server)
    pilot.run_pilot(s["protocol"], s["output"], max_runs=1)
    assert not s["calls"]
    assert document(s)["runs"][0]["status"] == "failed"


def test_resource_issue_after_stage_one_blocks_repeat_two_without_changing_gate(
    setup_pilot, monkeypatch
):
    s = setup_pilot
    pilot.run_pilot(s["protocol"], s["output"])
    gate = deepcopy(document(s)["runtime_gate"])
    fake_run = s["fake_run"]

    def interference(*args):
        result = fake_run(*args)
        result["model_info"]["resources"]["foreign_model_observed"] = True
        return result

    monkeypatch.setattr(pilot, "_run_case", interference)
    assert pilot.run_pilot(s["protocol"], s["output"], stage=3, resume=True) == 1
    data = document(s)
    assert len(data["runs"]) == 20
    assert data["runtime_gate"] == gate
    assert data["repeat_two_safety_block"]["resource_measurement_issues"] == [
        "foreign_model_observed"
    ]


def test_soft_wall_ceiling_stops_new_launch_and_records_overrun(setup_pilot):
    s = setup_pilot
    s["clock"]["seconds"] = 5500
    assert pilot.run_pilot(s["protocol"], s["output"]) == 1
    data = document(s)
    assert len(s["calls"]) == 1
    assert data["overall_wall_overrun_seconds"] == 100
    assert data["overall_wall_ceiling_is_soft"] is True
    assert data["runs"][0]["pilot"]["wall_exceeds_agent_deadline"] is True
    assert data["invocations"][-1]["stop_reason"] == "overall_wall_ceiling_reached"


def test_resume_identity_and_cell_plan_mutations_rejected(setup_pilot):
    s = setup_pilot
    pilot.run_pilot(s["protocol"], s["output"], max_runs=1)
    saved = document(s)
    for field in ("frozen_identity", "plan"):
        modified = deepcopy(saved)
        if field == "plan":
            modified[field][0]["model"] = "test-only-wrong-model"
        else:
            modified[field]["protocol_sha256"] = "test-only-wrong-hash"
        s["output"].write_text(json.dumps(modified))
        with pytest.raises(ValueError, match="identical frozen protocol"):
            pilot.run_pilot(s["protocol"], s["output"], resume=True)
    assert len(s["calls"]) == 1
