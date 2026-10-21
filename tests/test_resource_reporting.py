"""Constructed resource observations only. No model or performance evidence."""

import importlib.util
import json
import socket
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/report_heldout_v9.py"
SPEC = importlib.util.spec_from_file_location("test_only_resource_reporting", SCRIPT)
reporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reporter)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A reporting test attempted network access")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def helper():
    with reporter.FROZEN.no_network():
        return reporter.FROZEN.module(
            "test_only_resource_helpers",
            SCRIPT.with_name("verify_model_pilot_v1.py"),
        )


def resource_run():
    """Two samples from one test-only session, including before model load."""
    digest = reporter.FROZEN.DIGEST
    samples = [
        {
            "index": 0,
            "phase": "before_investigation",
            "elapsed_seconds": 0.0,
            "errors": [],
            "ollama": {"models": [], "matching_model_count": 0, "foreign_model_count": 0},
            "process_rss": {
                "tree_complete": True,
                "rss_sum_bytes": 12,
                "processes": [{"rss_bytes": 12}],
            },
        },
        {
            "index": 1,
            "phase": "before_cleanup",
            "elapsed_seconds": 1.0,
            "errors": [],
            "ollama": {
                "models": [{"digest": digest, "size_bytes": 10, "size_vram_bytes": 8}],
                "matching_model_count": 1,
                "foreign_model_count": 0,
            },
            "process_rss": {
                "tree_complete": True,
                "rss_sum_bytes": 12,
                "processes": [{"rss_bytes": 12}],
            },
        },
    ]
    return {
        "model_info": {
            "resources": {
                "status": "completed",
                "samples": samples,
                "requested_interval_seconds": 1.0,
                "read_timeout_seconds": 1.0,
                "sample_limit_reached": False,
                "sample_limit": 900,
                "sample_count": 2,
                "error_count": 0,
                "ollama_sample_count": 2,
                "rss_complete_sample_count": 2,
                "rss_incomplete_sample_count": 0,
                "matching_model_sample_count": 1,
                "foreign_model_observed": False,
                "sampled_maxima": {
                    "ollama_reported_size_bytes": 10,
                    "ollama_reported_size_vram_bytes": 8,
                    "listener_process_tree_rss_sum_bytes": 12,
                },
            }
        }
    }


def test_clean_export_retains_resource_status_without_changing_model_metrics(
    helper, tmp_path, monkeypatch
):
    result = reporter.resource_status(resource_run(), helper, reporter.FROZEN.DIGEST)
    assert result["artifact_consistency"] == "verified"
    assert result["sampling_status"] == "completed"
    assert result["measurement_eligible"] is True
    assert result["ollama_sample_gaps"] == result["rss_sample_gaps"] == 0
    assert result["matching_model_sample_count"] == 1
    assert result["observed_max_sample_gap_seconds"] == 1.0
    assert result["hardware_isolation_verified"] is False
    assert result["true_peak_memory_verified"] is False
    protocol = reporter.ROOT / "evaluation/protocol-heldout-v9.json"
    frozen = reporter.FROZEN.read(protocol)
    private_canary = "TEST_ONLY_PRIVATE_MODEL_TEXT_7D4F"
    runs, rows = [], []
    # One constructed clean-sampling workflow, using the actual eight-cell plan.
    # Repeated assignments are data, not hidden resource-condition variants.
    for cell in frozen["cell_plan"]:
        run = resource_run()
        run.update(
            test_only=True,
            private_model_text=private_canary,
            heldout={"cell": cell, "result_sha256": "test-only-payload-hash"},
        )
        runs.append(run)
        rows.append(
            {
                "cell_id": cell["cell_id"],
                "raw_result_sha256": "test-only-payload-hash",
                "status": "invalid",
                "wall_seconds": 2.5,
                "claim_support_metrics": {
                    "annotated_claim_count": 4,
                    "process_valid_supported_claim_count": 0,
                },
            }
        )
    raw = {"test_only": True, "runs": runs}
    raw_path, sdk_path = tmp_path / "test-only-raw.json", tmp_path / "test-only-sdk.json"
    raw_path.write_text(json.dumps(raw))
    sdk_path.write_text('{"test_only": true}')
    raw_sha, sdk_sha = reporter.FROZEN.sha(raw_path), reporter.FROZEN.sha(sdk_path)
    document = {
        "test_only": True,
        "planned_runs": 8,
        "attempted_runs": 8,
        "raw_sha256": raw_sha,
        "sdk_sha256": sdk_sha,
        "rows": rows,
    }
    before = deepcopy(document)

    def fake_verify(args):
        """Test-only frozen verification boundary; no SDK or inference runs."""
        return (
            frozen,
            raw,
            {
                "raw_sha256": raw_sha,
                "sdk_sha256": sdk_sha,
                "protocol_sha256": reporter.FROZEN.sha(protocol),
            },
        )

    def fake_summary(args):
        args.output.write_text(json.dumps(document))

    monkeypatch.setattr(reporter, "ROOT", tmp_path)
    monkeypatch.setattr(reporter.FROZEN, "verify_data", fake_verify)
    monkeypatch.setattr(reporter.FROZEN, "verify_protocol", lambda path: (frozen, []))
    monkeypatch.setattr(reporter.FROZEN, "summary", fake_summary)
    (tmp_path / "evaluation").mkdir()
    output = tmp_path / "evaluation/test-only-summary.json"
    metadata = reporter.summary(
        Namespace(protocol=protocol, raw=raw_path, sdk=sdk_path, output=output)
    )
    saved = json.loads(output.read_text())
    assert saved["rows"][0]["resources"] == result
    assert {key: value for key, value in saved["rows"][0].items() if key != "resources"} == (
        before["rows"][0]
    )
    assert document == before
    assert saved["test_only"] is True
    assert private_canary not in output.read_text()
    assert saved["artifact_verification_status"] == "verified"
    assert saved["measurement_review"]["measurement_eligible"] is True
    assert saved["measurement_review"]["artifact_verification_is_measurement_validity"] is False
    assert saved["measurement_review"]["rows_excluded"] == 0
    assert saved["planned_runs"] == 8
    assert len(saved["rows"]) == metadata["attempted_runs"] == 8
    assert saved["reporting_extension"]["protocol_sha256"] == reporter.FROZEN.sha(protocol)
    assert saved["reporting_extension"]["reporter_source_sha256"] == reporter.FROZEN.sha(SCRIPT)
    assert not list((tmp_path / "evaluation").glob(".heldout-resource-base-*.json"))


def test_foreign_model_observation_survives_artifact_verification(helper):
    run = resource_run()
    resource = run["model_info"]["resources"]
    resource["samples"][1]["ollama"]["foreign_model_count"] = 1
    resource["foreign_model_observed"] = True
    result = reporter.resource_status(run, helper, reporter.FROZEN.DIGEST)
    assert result["artifact_consistency"] == "verified"
    assert result["sampling_status"] == "completed"
    assert result["foreign_model_observed"] is True
    assert result["measurement_eligible"] is False


def test_unavailable_sampling_preserves_unknowns_and_hides_private_errors(helper):
    canary = "TEST_ONLY_PRIVATE_RESOURCE_ERROR_7D4F"
    run = {
        "model_info": {
            "resources": {
                "status": "unavailable",
                "error_count": 1,
                "errors": [{"phase": "start", "error_type": canary}],
            }
        }
    }
    result = reporter.resource_status(run, helper, reporter.FROZEN.DIGEST)
    assert result["artifact_consistency"] == "verified"
    assert result["sampling_status"] == "unavailable"
    assert result["measurement_eligible"] is False
    assert result["foreign_model_observed"] is None
    assert result["ollama_sample_gaps"] is None
    assert result["rss_sample_gaps"] is None
    assert result["error_count"] == 1
    assert canary not in json.dumps(result)


def test_partial_sampling_exports_read_gaps_without_claiming_no_contention(helper):
    run = resource_run()
    resource = run["model_info"]["resources"]
    sample = resource["samples"][0]
    sample.pop("ollama")
    sample["process_rss"] = {"tree_complete": False}
    sample["errors"] = [{"source": "ollama", "error_type": "TestOnlyReadFailure"}]
    resource.update(
        status="partial",
        error_count=1,
        ollama_sample_count=1,
        rss_complete_sample_count=1,
        rss_incomplete_sample_count=1,
    )
    result = reporter.resource_status(run, helper, reporter.FROZEN.DIGEST)
    assert result["artifact_consistency"] == "verified"
    assert result["sampling_status"] == "partial"
    assert result["measurement_eligible"] is False
    assert result["ollama_sample_gaps"] == result["rss_sample_gaps"] == 1
    assert result["foreign_model_observed"] is False
    assert result["foreign_model_observation_complete"] is False


def test_changed_resource_aggregate_is_rejected_before_export(helper):
    run = deepcopy(resource_run())
    run["model_info"]["resources"]["foreign_model_observed"] = True
    with pytest.raises(AssertionError, match="Resource aggregate differs"):
        reporter.resource_status(run, helper, reporter.FROZEN.DIGEST)
