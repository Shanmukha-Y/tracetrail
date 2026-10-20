"""Scorer dispatch regressions. Reports are test data, not inference evidence."""

import hashlib
import json
import math
import socket
import stat
from copy import deepcopy
from pathlib import Path

import pytest

from tracetrail import cli, support_evaluation, telemetry
from tracetrail.evaluation import load_cases
from tracetrail.support_evaluation import (
    NUMERIC_METRIC_KEYS,
    SCORER_ID,
    score_claim_support,
    scorer_fingerprint,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/cases-v6.json"


@pytest.fixture(autouse=True)
def no_network_or_ollama(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Scorer dispatch tests must not use a network or Ollama client")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(cli.ollama, "Client", forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-only-scorer-secret-never-used")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://example.invalid")
    yield
    assert attempts == []


@pytest.fixture
def case():
    return load_cases(MANIFEST)[0]


def make_report(case):
    """Construct an unsupported report without invoking or impersonating a model."""
    return {
        "case_id": case["id"],
        "split": case["split"],
        "fixture_sha256": case["fixture_sha256"],
        "model": "test-only:no-inference",
        "strategy": "adaptive",
        "status": "completed",
        "test_only": True,
        "evidence": [],
        "selected_event_refs": [],
        "observations": [],
        "findings": [
            {
                **hypothesis,
                "status": "uncertain",
                "citations": [],
                "evidence_links": [],
                "rationale": "Test-only unsupported report for scorer dispatch.",
                "missing_evidence": ["No supporting records were supplied to this test report."],
            }
            for hypothesis in case["hypotheses"]
        ],
        "tool_history": [],
        "model_history": [{"output": "Test-only constructed response; no inference occurred."}],
        "query_count": 0,
        "model_calls": 0,
        "duration_seconds": 0,
        "failures": [],
    }


# This is a test-data factory, not a pytest test function.


def batch_for(case, *, scorer=None):
    run = make_report(case)
    batch = {
        "suite_id": case["_suite_id"],
        "case_manifest_path": "evaluation/cases-v6.json",
        "case_manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "runs": [run],
    }
    if scorer is not None:
        metadata = {"primary_scorer": scorer, "test_only_note": "Additional metadata is allowed."}
        batch["evaluation"] = deepcopy(metadata)
        run["evaluation"] = deepcopy(metadata)
    return batch


def save_batch(tmp_path, batch, name="test-only-results.json"):
    source = tmp_path / name
    source.write_text(json.dumps(batch, sort_keys=True))
    return source


def numeric_metrics(metrics, *, allowed=None, prefix=""):
    return {
        prefix + key: value
        for key, value in metrics.items()
        if (allowed is None or key in allowed)
        and isinstance(value, (int, float, bool))
        and math.isfinite(float(value))
    }


def feedback_scores(document):
    rows = document["evaluated_runs"]
    assert len(rows) == 1
    feedback = rows[0]["sdk_feedback"]
    assert len({item["key"] for item in feedback}) == len(feedback)
    return {item["key"]: item["score"] for item in feedback}


def test_claim_support_replay_has_only_prefixed_allowlisted_feedback_and_fingerprint(
    tmp_path, monkeypatch, case
):
    batch = batch_for(case, scorer=SCORER_ID)
    run = batch["runs"][0]
    run["metrics"] = {"stored_legacy_score_must_not_be_trusted": 999}
    run["claim_support_metrics"] = {"stored_new_score_must_not_be_trusted": 999}
    source = save_batch(tmp_path, batch)
    before = source.read_bytes()
    expected = numeric_metrics(
        score_claim_support(case, run),
        allowed=NUMERIC_METRIC_KEYS,
        prefix="claim_support_v1__",
    )
    actual_scorer = support_evaluation.score_claim_support

    def with_unallowlisted_numbers(case, result):
        return {
            **actual_scorer(case, result),
            "unexpected_numeric_must_not_be_feedback": 42,
            "unexpected_boolean_must_not_be_feedback": True,
        }

    monkeypatch.setattr(support_evaluation, "score_claim_support", with_unallowlisted_numbers)
    report = telemetry.evaluate_local(source, ROOT, scorer=SCORER_ID)
    path = Path(report["path"])
    document = json.loads(path.read_text())

    assert document["status"] == "completed"
    assert path.name == "test-only-results.claim-support-v1.langsmith-local.json"
    assert feedback_scores(document) == expected
    assert expected
    assert all(key.startswith("claim_support_v1__") for key in feedback_scores(document))
    assert document["evaluation"] == {
        "primary_scorer": SCORER_ID,
        **scorer_fingerprint(),
        "stored_output_replay": True,
        "post_hoc": False,
    }
    fingerprint = scorer_fingerprint()
    assert fingerprint["scorer_id"] == SCORER_ID
    assert (
        fingerprint["source_sha256"]
        == hashlib.sha256(Path(support_evaluation.__file__).read_bytes()).hexdigest()
    )
    assert document["upload_results"] is False
    assert document["inference_rerun"] is False
    assert source.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
