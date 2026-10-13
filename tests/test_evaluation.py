"""Scorer unit tests with constructed reports, never model capability evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tracetrail.evaluation import load_cases, score_run

MANIFEST = Path(__file__).resolve().parents[1] / "evaluation/cases.json"


def cases():
    return load_cases(MANIFEST)


def constructed_report(case: dict) -> dict:
    """An annotation-perfect test object, not an investigation or model output."""
    records = case["_fixture_records"]
    evidence = [
        {
            "ref": f"sha256:{case['fixture_sha256']}/Records/{index}",
            "event_id": record["eventID"],
            "record": copy.deepcopy(record),
        }
        for index, record in enumerate(records)
    ]
    by_id = {item["event_id"]: item["ref"] for item in evidence}
    annotations = {a["claim_id"]: a for a in case["annotations"]}
    findings = [
        {
            "claim_id": h["claim_id"],
            "statement": h["statement"],
            "status": annotations[h["claim_id"]]["expected_status"],
            "citations": [
                by_id[event_id] for event_id in annotations[h["claim_id"]]["required_event_ids"]
            ],
        }
        for h in case["hypotheses"]
    ]
    observations = [
        {"citation": by_id[o["event_id"]], "field": o["field"], "value": copy.deepcopy(o["value"])}
        for annotation in case["annotations"]
        for o in annotation["required_observations"]
    ]
    return {
        "findings": findings,
        "observations": observations,
        "evidence": evidence,
        "selected_event_refs": [by_id[event_id] for event_id in case["relevant_event_ids"]],
        "query_count": 1,
        "model_calls": 1,
        "duration_seconds": 2.5,
        "tool_history": [{"name": "query_events", "args": {}, "result": {"records": evidence}}],
        "failures": [],
    }


@pytest.mark.parametrize("case_index", range(4))
def test_exact_annotated_reports_score_all_fixed_claims(case_index):
    case = cases()[case_index]
    result = score_run(case, constructed_report(case))
    assert result["supported_annotation_rate"] == 1
    assert result["unsupported_claims"] == 0
    assert result["annotation_coverage"] == 1
    assert result["insufficient_evidence_handling"] == 1
    assert result["relevant_event_precision"] == 1
    assert result["relevant_event_recall"] == 1


def test_valid_citation_alone_cannot_support_claim():
    case = cases()[0]
    report = constructed_report(case)
    report["observations"] = []
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == len(case["annotations"])
    assert metrics["status_accuracy"] == 1
    assert metrics["supported_annotation_rate"] == 0


def test_real_ref_with_altered_record_is_rejected():
    case = cases()[0]
    report = constructed_report(case)
    report["evidence"][3]["record"]["eventName"] = "StartLogging"
    metrics = score_run(case, report)
    assert metrics["invalid_evidence_count"] == 1
    assert metrics["unsupported_claims"] >= 1
    assert metrics["relevant_event_recall"] == 4 / 5


def test_unqueried_nonseed_record_cannot_be_cited():
    case = cases()[0]
    report = constructed_report(case)
    report["tool_history"] = []
    metrics = score_run(case, report)
    assert metrics["retrieved_event_count"] == 1
    assert metrics["invalid_evidence_count"] == len(case["_fixture_records"]) - 1
    assert metrics["supported_annotation_rate"] == 0


def test_statement_id_does_not_certify_stronger_statement():
    case = cases()[0]
    report = constructed_report(case)
    report["findings"][0]["statement"] += " This proves a hostile actor stole the credentials."
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 1
    assert metrics["status_accuracy"] == 5 / 6
    assert metrics["per_finding"][0]["reasons"] == ["statement_mismatch"]


def test_denied_request_cannot_be_reported_successful():
    case = cases()[2]
    report = constructed_report(case)
    report["findings"][0]["status"] = "supported"
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 1
    assert "status_mismatch" in metrics["per_finding"][0]["reasons"]


def test_missing_records_cannot_prove_logging_active():
    case = cases()[2]
    report = constructed_report(case)
    report["findings"][2]["status"] = "supported"
    metrics = score_run(case, report)
    assert metrics["insufficient_evidence_handling"] == 0.5
    assert metrics["unsupported_claims"] == 1


def test_wrong_observation_event_and_boolean_type_fail():
    case = cases()[1]
    report = constructed_report(case)
    matching = [o for o in report["observations"] if o["field"] == "responseElements.isLogging"]
    for observation in matching:
        observation["value"] = 1
    metrics = score_run(case, report)
    assert metrics["invalid_observation_count"] == 2
    assert metrics["unsupported_claims"] == 2


def test_extra_assertion_and_duplicate_claim_are_unsupported():
    case = cases()[0]
    report = constructed_report(case)
    report["findings"].append(
        {
            "claim_id": "invented",
            "statement": "The attacker is identified.",
            "status": "supported",
            "citations": [],
        }
    )
    report["findings"].append(copy.deepcopy(report["findings"][0]))
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 3
    assert metrics["annotation_coverage"] == 1


def test_precision_penalizes_selecting_noise_and_deduplicates_refs():
    case = cases()[0]
    report = constructed_report(case)
    report["selected_event_refs"] = [item["ref"] for item in report["evidence"]] * 2
    metrics = score_run(case, report)
    assert metrics["selected_event_count"] == 7
    assert metrics["relevant_event_precision"] == 5 / 7
    assert metrics["relevant_event_recall"] == 1


def test_empty_failed_run_does_not_earn_perfect_score():
    case = cases()[0]
    metrics = score_run(case, {"failures": [{"phase": "model", "error_type": "TimeoutError"}]})
    assert metrics["annotation_coverage"] == 0
    assert metrics["supported_annotation_rate"] == 0
    assert metrics["unsupported_claim_rate"] is None
    assert metrics["relevant_event_recall"] == 0
    assert metrics["run_failed"] is True
    assert metrics["failure_count"] == 1


def test_malformed_observation_does_not_drop_the_run():
    case = cases()[0]
    report = constructed_report(case)
    report["observations"].append({"citation": {"invented": "ref"}, "field": [], "value": 1})
    report["selected_event_refs"].append({"invented": "ref"})
    metrics = score_run(case, report)
    assert metrics["invalid_observation_count"] == 1
    assert metrics["selected_event_count"] == 6
    assert metrics["relevant_event_precision"] == 5 / 6


def test_explicit_absence_observation_is_valid():
    case = cases()[0]
    report = constructed_report(case)
    report["observations"].append(
        {
            "citation": report["evidence"][0]["ref"],
            "field": "errorCode",
            "present": False,
            "value": None,
        }
    )
    metrics = score_run(case, report)
    assert metrics["invalid_observation_count"] == 0
    assert metrics["supported_annotation_rate"] == 1


@pytest.mark.parametrize(
    ("field", "present", "value"),
    [
        ("responseElements", False, None),
        ("eventName", False, None),
        ("errorCode", True, None),
        ("errorCode", False, "AccessDenied"),
        ("errorCode", False, False),
        ("errorCode", False, 0),
        ("errorCode", "false", None),
        ("errorCode", 0, None),
        ("eventName", 1, "ListBuckets"),
        ("eventName", None, "ListBuckets"),
        ("", False, None),
    ],
)
def test_false_or_nonbool_presence_cannot_certify_an_observation(field, present, value):
    case = cases()[0]
    report = constructed_report(case)
    report["observations"].append(
        {
            "citation": report["evidence"][0]["ref"],
            "field": field,
            "present": present,
            "value": value,
        }
    )
    assert score_run(case, report)["invalid_observation_count"] == 1


def test_presence_defaults_to_true_and_null_does_not_mean_absence():
    case = cases()[0]
    report = constructed_report(case)
    citation = report["evidence"][0]["ref"]
    report["observations"].append({"citation": citation, "field": "errorCode", "value": None})
    report["observations"].append(
        {"citation": citation, "field": "responseElements", "value": None}
    )
    assert score_run(case, report)["invalid_observation_count"] == 1


def test_absence_requires_explicit_null_value():
    case = cases()[0]
    report = constructed_report(case)
    report["observations"].append(
        {"citation": report["evidence"][0]["ref"], "field": "errorCode", "present": False}
    )
    assert score_run(case, report)["invalid_observation_count"] == 1


def test_explicit_true_observations_keep_frozen_annotation_support():
    case = cases()[0]
    report = constructed_report(case)
    for observation in report["observations"]:
        observation["present"] = True
    assert score_run(case, report)["supported_annotation_rate"] == 1


def test_injected_tool_fault_is_measured_without_fabricating_evidence():
    """Fault injection is a scorer test, not an Ollama or tool capability run."""
    case = cases()[0]
    report = constructed_report(case)
    report["tool_history"] = [
        {
            "name": "query_events",
            "args": {"event_name": "StopLogging"},
            "result": {"error": {"code": "injected_test_fault"}},
        }
    ]
    report["failures"] = [{"phase": "tool", "error": {"code": "injected_test_fault"}}]
    metrics = score_run(case, report)
    assert metrics["tool_errors"] == 1
    assert metrics["failure_count"] == 1
    assert metrics["supported_annotation_rate"] == 0
    assert metrics["query_count"] == 1


def test_loader_detects_fixture_mutation(tmp_path):
    root = tmp_path
    (root / "evaluation").mkdir()
    (root / "fixtures").mkdir()
    manifest = json.loads(MANIFEST.read_text())
    manifest["cases"] = manifest["cases"][:1]
    case = manifest["cases"][0]
    (root / case["fixture"]).write_text('{"Records": []}\n')
    manifest_path = root / "evaluation/cases.json"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Fixture hash mismatch"):
        load_cases(manifest_path)


def test_loader_checks_annotation_against_raw_field(tmp_path):
    (tmp_path / "evaluation").mkdir()
    (tmp_path / "fixtures").mkdir()
    manifest = json.loads(MANIFEST.read_text())
    manifest["cases"] = manifest["cases"][:1]
    case = manifest["cases"][0]
    source = MANIFEST.parent.parent / case["fixture"]
    (tmp_path / case["fixture"]).write_bytes(source.read_bytes())
    case["annotations"][0]["required_observations"][0]["value"] = "invented"
    manifest_path = tmp_path / "evaluation/cases.json"
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Annotated field"):
        load_cases(manifest_path)
