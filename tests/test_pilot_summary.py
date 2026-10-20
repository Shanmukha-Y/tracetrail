"""Test-only summary inputs. These are not recorded model experiments."""

import importlib.util
import json
import socket
from copy import deepcopy
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/summarize_model_pilot_v1.py"
SPEC = importlib.util.spec_from_file_location("test_only_pilot_summary", SCRIPT)
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Test-only summary validation attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)


@pytest.fixture
def summary_inputs(tmp_path):
    """A small review binding fixture, never passed to public full-batch export."""
    case = {
        "id": "test-only-case",
        "fixture_sha256": "a" * 64,
        "_record_count": 1,
        "hypotheses": [{"claim_id": f"claim-{i}"} for i in range(4)],
        "annotations": [
            {"claim_id": f"claim-{i}", "expected_status": "uncertain"} for i in range(4)
        ],
    }
    run = {
        "case_id": case["id"],
        "strategy": "adaptive",
        "status": "invalid",
        "findings": [{"claim_id": f"claim-{i}", "status": "uncertain"} for i in range(4)],
        "pilot": {
            "cell": {"cell_id": "test-only-cell", "repeat": 1, "model": "test-only:model"},
            "result_sha256": "b" * 64,
        },
    }
    claims = [
        {
            "claim_id": f"claim-{i}",
            "emitted_status": "uncertain",
            "evidence_warrant": "unresolved",
            "declared_basis": "absent",
            "availability": "insufficient_full_source",
            "full_source_truth": "uncertain",
            "outcome": "source_limited_unknown",
            "reason": "TEST-ONLY PRIVATE REVIEW TEXT",
            "source_checks": [
                {
                    "ref": "sha256:" + "a" * 64 + "/Records/0",
                    "fields": [
                        {"path": "userIdentity.accessKeyId", "value": "TEST-ONLY PRIVATE VALUE"}
                    ],
                }
            ],
        }
        for i in range(4)
    ]
    document = {
        "pilot_protocol_sha256": "c" * 64,
        "review_protocol_sha256": "d" * 64,
        "rows": [
            {
                "cell_id": "test-only-cell",
                "cell_result_sha256": "b" * 64,
                "case_id": case["id"],
                "strategy": "adaptive",
                "repeat": 1,
                "process_status": "invalid",
                "report_available": True,
                "claim_reviews": claims,
            }
        ],
    }
    path = tmp_path / "test-only-review.json"
    return {
        "case": case,
        "run": run,
        "document": document,
        "path": path,
        "protocol": {"semantic_rubric": {"sha256": "d" * 64}},
    }


def load_test_review(data):
    data["path"].write_text(json.dumps(data["document"]))
    return summary.load_primary_reviews(
        [data["path"]],
        {"runs": [data["run"]]},
        data["protocol"],
        "c" * 64,
        "e" * 64,
        {data["case"]["id"]: data["case"]},
        data["path"].parent,
    )


@pytest.mark.parametrize("fault", ["cell_hash"])
def test_summary_refuses_stale_cell_review_hash(summary_inputs, fault):
    document = summary_inputs["document"]
    if fault == "cell_hash":
        document["rows"][0]["cell_result_sha256"] = "0" * 64
    elif fault == "missing_claim":
        document["rows"][0]["claim_reviews"].pop()
    elif fault == "duplicate_claim":
        document["rows"][0]["claim_reviews"][-1] = deepcopy(document["rows"][0]["claim_reviews"][0])
    else:
        document["pilot_protocol_sha256"] = "0" * 64
    with pytest.raises(summary.SummaryError):
        load_test_review(summary_inputs)


def test_numeric_row_redacts_secret_shaped_labels_and_rejects_non_numeric_metrics(
    summary_inputs,
):
    canary = "AKIA_TESTONLY_PRIVATE_SCOPE_7D4F"
    reviews, _, _ = load_test_review(summary_inputs)
    run = deepcopy(summary_inputs["run"])
    run.update(
        {
            "status": canary,
            "fixture_sha256": "a" * 64,
            "claim_support_metrics": {
                key: False if key == "process_valid" else 0 for key in summary.NUMERIC_KEYS
            },
            "metrics": {
                "relevant_event_precision": canary,
                "relevant_event_recall": 2,
                "relevant_true_positives": True,
                "relevant_event_count": canary,
            },
            "model_info": {
                "resources": {
                    "status": canary,
                    "sample_count": canary,
                    "sampled_maxima": {key: canary for key in summary.MAXIMA},
                }
            },
            "failures": [
                {"phase": canary, "error_type": canary, "code": canary, "message": canary}
            ],
        }
    )
    run["pilot"]["wall_seconds"] = 1
    public = summary.numeric_row(run, reviews["test-only-cell"], summary.NUMERIC_KEYS)
    assert canary not in json.dumps(public)
    assert public["status"] == "other_recorded_run_status"
    assert public["memory"]["status"] == "other_recorded_memory_status"
    assert all(value is None for value in public["retrieval"].values())
    assert public["failures"][0]["redacted_label_count"] == 3
    assert public["failures"][0]["phase"] == "other_recorded_phase"
    assert public["failures"][0]["code"] == "other_recorded_code"
    run["claim_support_metrics"]["finding_count"] = canary
    with pytest.raises(summary.SummaryError, match="integer bounds"):
        summary.numeric_row(run, reviews["test-only-cell"], summary.NUMERIC_KEYS)
