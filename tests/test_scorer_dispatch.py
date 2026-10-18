"""Scorer dispatch regressions. Reports are test data, not inference evidence."""

import hashlib
import json
import math
import socket
import stat
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from tracetrail import cli, support_evaluation, telemetry
from tracetrail.evaluation import load_cases, score_run
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


def test_only_report(case):
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
test_only_report.__test__ = False


def batch_for(case, *, scorer=None):
    run = test_only_report(case)
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


@pytest.mark.parametrize("requested", [None, "legacy-v1"])
def test_legacy_replay_keeps_exact_feedback_contract_and_old_artifact_envelope(
    tmp_path, case, requested
):
    batch = batch_for(case)
    # Presence of new metric-shaped data cannot select a new scorer without its ID.
    batch["runs"][0]["claim_support_metrics"] = {"sentinel_not_a_scorer_id": 99}
    source = save_batch(tmp_path, batch)
    before = source.read_bytes()

    report = telemetry.evaluate_local(source, ROOT, scorer=requested)
    path = Path(report["path"])
    document = json.loads(path.read_text())
    expected = numeric_metrics(score_run(case, batch["runs"][0]))

    assert len(expected) == 22
    assert feedback_scores(document) == expected
    assert len(document["evaluated_runs"][0]["sdk_feedback"]) == 22
    assert path.name == "test-only-results.langsmith-local.json"
    assert "evaluation" not in document
    assert document["upload_results"] is False
    assert document["inference_rerun"] is False
    assert document["source_results_sha256"] == hashlib.sha256(before).hexdigest()
    assert source.read_bytes() == before
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    replayed = document["evaluated_runs"][0]["sdk_evaluation_trace"]["outputs"]["result"]
    assert replayed == batch["runs"][0]


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


def make_invalid_metadata(batch, defect):
    if defect == "unknown_batch_id":
        batch["evaluation"]["primary_scorer"] = "unknown-test-only-scorer"
    elif defect == "unknown_run_id":
        batch["runs"][0]["evaluation"]["primary_scorer"] = "unknown-test-only-scorer"
    elif defect == "missing_batch_id":
        del batch["evaluation"]
    elif defect == "missing_run_id":
        del batch["runs"][0]["evaluation"]
    elif defect == "empty_batch_metadata":
        batch["evaluation"] = {}
    elif defect == "empty_run_metadata":
        batch["runs"][0]["evaluation"] = {}
    elif defect == "nonobject_batch_metadata":
        batch["evaluation"] = [SCORER_ID]
    elif defect == "conflicting_run_id":
        batch["runs"][0]["evaluation"]["primary_scorer"] = "legacy-v1"
    elif defect == "mixed_runs":
        extra = deepcopy(batch["runs"][0])
        del extra["evaluation"]
        batch["runs"].append(extra)
    else:
        raise AssertionError("Unknown test-only metadata defect")


@pytest.mark.parametrize(
    "defect",
    [
        "unknown_batch_id",
        "unknown_run_id",
        "missing_batch_id",
        "missing_run_id",
        "empty_batch_metadata",
        "empty_run_metadata",
        "nonobject_batch_metadata",
        "conflicting_run_id",
        "mixed_runs",
    ],
)
def test_unknown_conflicting_or_mixed_ids_reject_before_sdk_or_client(
    tmp_path, monkeypatch, case, defect
):
    batch = batch_for(case, scorer=SCORER_ID)
    make_invalid_metadata(batch, defect)
    source = save_batch(tmp_path, batch)
    before = source.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid scorer metadata reached the SDK or client")

    monkeypatch.setattr(telemetry, "evaluate", forbidden)
    monkeypatch.setattr(telemetry, "_LocalOnlyClient", forbidden)
    with pytest.raises(ValueError):
        telemetry.evaluate_local(source, ROOT)
    assert source.read_bytes() == before
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("recorded,requested", [(None, SCORER_ID), (SCORER_ID, "legacy-v1")])
def test_explicit_scorer_cannot_relabel_stored_outputs(
    tmp_path, monkeypatch, case, recorded, requested
):
    source = save_batch(tmp_path, batch_for(case, scorer=recorded))

    def forbidden(*args, **kwargs):
        raise AssertionError("A post-hoc scorer override reached evaluation")

    monkeypatch.setattr(telemetry, "evaluate", forbidden)
    monkeypatch.setattr(telemetry, "_LocalOnlyClient", forbidden)
    with pytest.raises(ValueError, match="conflict"):
        telemetry.evaluate_local(source, ROOT, scorer=requested)
    assert list(tmp_path.iterdir()) == [source]


@pytest.mark.parametrize("scorer", [None, SCORER_ID])
@pytest.mark.parametrize("collision", ["source", "source_alias", "existing_output"])
def test_replay_never_overwrites_source_or_existing_output(
    tmp_path, monkeypatch, case, scorer, collision
):
    source = save_batch(tmp_path, batch_for(case, scorer=scorer))
    source_bytes = source.read_bytes()
    if collision == "source":
        destination = source
    elif collision == "source_alias":
        destination = tmp_path / "test-only-source-alias.json"
        destination.symlink_to(source)
    else:
        destination = tmp_path / "test-only-existing-evaluation.json"
        destination.write_bytes(b"previous complete SDK artifact")
    destination_bytes = destination.read_bytes()

    def forbidden(*args, **kwargs):
        raise AssertionError("An unsafe replay destination reached evaluation")

    monkeypatch.setattr(telemetry, "evaluate", forbidden)
    monkeypatch.setattr(telemetry, "_LocalOnlyClient", forbidden)
    with pytest.raises(ValueError, match="differ|already exists"):
        telemetry.evaluate_local(source, ROOT, output_path=destination)
    assert source.read_bytes() == source_bytes
    assert destination.read_bytes() == destination_bytes


@pytest.fixture
def constructed_investigation(monkeypatch, case):
    """Replace model use only; real CLI case loading and scoring still execute."""
    report = test_only_report(case)
    original = deepcopy(report)

    @contextmanager
    def test_only_session(name):
        yield {"model": name, "test_only": True}

    monkeypatch.setattr(cli, "model_session", test_only_session)
    monkeypatch.setattr(cli, "investigate", lambda *args, **kwargs: deepcopy(report))
    return original


def test_run_case_preserves_legacy_metrics_and_adds_explicit_new_metrics(
    case, constructed_investigation
):
    result = cli.run_case(case, ROOT, cli.MODELS[1], "adaptive")
    assert result["test_only"] is True
    assert result["evaluation"]["primary_scorer"] == SCORER_ID
    assert result["metrics"] == score_run(case, result)
    assert result["claim_support_metrics"] == score_claim_support(case, result)
    for key in ("evidence", "findings", "model_history", "observations"):
        assert result[key] == constructed_investigation[key]


@pytest.mark.parametrize("runner_failure", [False, True])
def test_compare_labels_batch_and_every_run_and_keeps_both_metric_contracts(
    tmp_path, monkeypatch, case, constructed_investigation, runner_failure
):
    if runner_failure:

        def fail_case(*args, **kwargs):
            raise RuntimeError("Intentional test-only runner failure")

        monkeypatch.setattr(cli, "run_case", fail_case)
    destination = tmp_path / "test-only-comparison.json"
    exit_code = cli.main(
        [
            "compare",
            "--manifest",
            str(MANIFEST),
            "--case",
            case["id"],
            "--models",
            cli.MODELS[1],
            "--output",
            str(destination),
        ]
    )
    batch = json.loads(destination.read_text())
    assert batch["evaluation"]["primary_scorer"] == SCORER_ID
    assert len(batch["runs"]) == 1
    run = batch["runs"][0]
    assert run["evaluation"]["primary_scorer"] == SCORER_ID
    assert run["metrics"] == score_run(case, run)
    assert run["claim_support_metrics"] == score_claim_support(case, run)
    assert run["case_id"] == case["id"]
    assert run["status"] == ("failed" if runner_failure else "completed")
    assert exit_code == int(runner_failure)


def test_cli_local_evaluate_reads_recorded_id_and_accepts_matching_override(tmp_path, case):
    source = save_batch(tmp_path, batch_for(case, scorer=SCORER_ID))
    assert (
        cli.main(["local-evaluate", str(source), "--root", str(ROOT), "--scorer", SCORER_ID]) == 0
    )
    destination = source.with_name(source.stem + ".claim-support-v1.langsmith-local.json")
    document = json.loads(destination.read_text())
    assert document["evaluation"]["primary_scorer"] == SCORER_ID
    assert document["status"] == "completed"


def test_cli_local_evaluate_returns_error_for_scorer_conflict(tmp_path, case, capsys):
    source = save_batch(tmp_path, batch_for(case, scorer=SCORER_ID))
    assert (
        cli.main(["local-evaluate", str(source), "--root", str(ROOT), "--scorer", "legacy-v1"]) == 2
    )
    assert "conflict" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == [source]
