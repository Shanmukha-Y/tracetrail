"""Constructed scorer tests only; these reports are not model capability evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re

import pytest

from tracetrail.support_evaluation import (
    NUMERIC_METRIC_KEYS,
    NUMERIC_METRICS,
    SCORER_ID,
    score_claim_support,
    scorer_source_sha256,
)


@pytest.fixture
def support_case_and_report():
    """Two explicit test-only claims, plus same-valued fields in a noise record."""
    records = [
        {
            "eventID": "test-only-seed",
            "eventTime": "2026-01-01T00:00:00Z",
            "eventName": "UpdateThing",
            "userIdentity": {"accessKeyId": "TEST_ONLY_CALLER"},
        },
        {
            "eventID": "test-only-readback",
            "eventTime": "2026-01-01T00:01:00Z",
            "eventName": "GetThing",
            "readOnly": True,
            "requestParameters": {"attempts": 1},
            "responseElements": None,
        },
        {
            "eventID": "test-only-unrelated-read",
            "eventTime": "2026-01-01T00:02:00Z",
            "eventName": "UnrelatedRead",
            "readOnly": True,
            "requestParameters": {"attempts": 1},
            "responseElements": None,
        },
    ]
    fixture_hash = hashlib.sha256(
        json.dumps({"Records": records}, sort_keys=True).encode()
    ).hexdigest()
    refs = [f"sha256:{fixture_hash}/Records/{index}" for index in range(len(records))]
    case = {
        "id": "test-only-claim-support",
        "split": "development",
        "fixture_sha256": fixture_hash,
        "seed_event_id": records[0]["eventID"],
        "relevant_event_ids": [record["eventID"] for record in records[:2]],
        "hypotheses": [
            {"claim_id": "change", "statement": "The caller made the UpdateThing request."},
            {"claim_id": "readback", "statement": "The resource was enabled at read time."},
        ],
        "annotations": [
            {
                "claim_id": "change",
                "expected_status": "supported",
                "required_event_ids": [records[0]["eventID"]],
                "required_observations": [
                    {
                        "event_id": records[0]["eventID"],
                        "field": "eventName",
                        "value": "UpdateThing",
                    },
                    {
                        "event_id": records[0]["eventID"],
                        "field": "userIdentity.accessKeyId",
                        "value": "TEST_ONLY_CALLER",
                    },
                ],
            },
            {
                "claim_id": "readback",
                "expected_status": "uncertain",
                "required_event_ids": [records[1]["eventID"]],
                "required_observations": [
                    {"event_id": records[1]["eventID"], "field": "readOnly", "value": True},
                    {
                        "event_id": records[1]["eventID"],
                        "field": "requestParameters.attempts",
                        "value": 1,
                    },
                    {
                        "event_id": records[1]["eventID"],
                        "field": "responseElements",
                        "value": None,
                    },
                    {
                        "event_id": records[1]["eventID"],
                        "field": "errorCode",
                        "present": False,
                        "value": None,
                    },
                ],
            },
        ],
        "_fixture_records": records,
        "_manifest_sha256": "0" * 64,
        "_suite_id": "test-only-support-scorer",
    }
    evidence = [
        {"ref": ref, "event_id": record["eventID"], "record": copy.deepcopy(record)}
        for ref, record in zip(refs, records, strict=True)
    ]
    report = {
        "status": "completed",
        "test_only": True,
        "findings": [
            {
                **case["hypotheses"][0],
                "status": "supported",
                "citations": [refs[0]],
                "evidence_links": [
                    {
                        "citation": refs[0],
                        "fields": ["eventName", "userIdentity.accessKeyId"],
                        "role": "supports",
                    }
                ],
                "rationale": "Constructed test-only action evidence, not model output.",
                "missing_evidence": [],
            },
            {
                **case["hypotheses"][1],
                "status": "uncertain",
                "citations": [refs[1]],
                "evidence_links": [
                    {
                        "citation": refs[1],
                        "fields": [
                            "readOnly",
                            "requestParameters.attempts",
                            "responseElements",
                            "errorCode",
                        ],
                        "role": "context",
                    }
                ],
                "rationale": "The constructed read response does not establish resource state.",
                "missing_evidence": ["A response containing the resource's actual state."],
            },
        ],
        "observations": [],
        "evidence": evidence,
        "selected_event_refs": refs[:2],
        "tool_history": [
            {
                "name": "query_events",
                "args": {},
                "result": {"records": copy.deepcopy(evidence)},
            }
        ],
        "failures": [],
        "query_count": 1,
        "model_calls": 0,
        "duration_seconds": 0,
    }
    return case, report


def _score(pair):
    return score_claim_support(*pair)


def _sync_citations(finding):
    finding["citations"] = list(
        dict.fromkeys(link["citation"] for link in finding["evidence_links"])
    )


def test_constructed_complete_claim_local_support(support_case_and_report):
    metrics = _score(support_case_and_report)
    assert SCORER_ID == "claim-support-v1"
    assert metrics["annotated_claim_count"] == 2
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["process_valid_supported_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["raw_covered_atom_count"] == 6
    assert metrics["process_valid_covered_atom_count"] == 6
    assert metrics["process_valid_supported_claim_rate"] == 1
    assert metrics["process_valid_required_atom_coverage"] == 1
    assert metrics["process_valid"] is True


def test_global_observations_alone_never_supply_claim_local_support(support_case_and_report):
    case, report = support_case_and_report
    case["hypotheses"] = case["hypotheses"][1:]
    case["annotations"] = case["annotations"][1:]
    finding = report["findings"][1]
    report["findings"] = [finding]
    finding["evidence_links"] = []
    finding["citations"] = []
    report["observations"] = [
        {"citation": report["evidence"][1]["ref"], **copy.deepcopy(observation)}
        for observation in case["annotations"][0]["required_observations"]
    ]
    metrics = _score(support_case_and_report)
    assert metrics["required_atom_count"] == 4
    assert metrics["raw_covered_atom_count"] == 0
    assert metrics["raw_supported_claim_count"] == 0


def test_global_observation_values_are_ignored(support_case_and_report):
    case, report = support_case_and_report
    before = score_claim_support(case, report)
    report["observations"] = [{"citation": {}, "field": [], "present": "false", "value": 99}]
    assert score_claim_support(case, report) == before


def test_field_link_on_another_claim_does_not_fill_the_gap(support_case_and_report):
    _, report = support_case_and_report
    report["findings"][1]["evidence_links"][0]["fields"].remove("readOnly")
    report["findings"][0]["evidence_links"].append(
        {"citation": report["evidence"][1]["ref"], "fields": ["readOnly"], "role": "context"}
    )
    _sync_citations(report["findings"][0])
    metrics = _score(support_case_and_report)
    assert metrics["raw_covered_atom_count"] == 5
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["process_valid"] is True


def test_same_value_in_another_record_does_not_supply_required_source(support_case_and_report):
    _, report = support_case_and_report
    noise_ref = report["evidence"][2]["ref"]
    report["selected_event_refs"].append(noise_ref)
    report["findings"][1]["evidence_links"][0]["citation"] = noise_ref
    _sync_citations(report["findings"][1])
    metrics = _score(support_case_and_report)
    assert metrics["raw_covered_atom_count"] == 2
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["process_valid"] is True


@pytest.mark.parametrize(
    ("field", "present", "value", "matches"),
    [
        ("readOnly", True, True, True),
        ("readOnly", True, 1, False),
        ("readOnly", True, False, False),
        ("requestParameters.attempts", True, 1, True),
        ("requestParameters.attempts", True, True, False),
        ("requestParameters.attempts", True, 1.0, False),
        ("responseElements", True, None, True),
        ("responseElements", False, None, False),
        ("responseElements", True, "null", False),
        ("errorCode", False, None, True),
        ("errorCode", True, None, False),
        ("errorCode", False, 0, False),
        ("errorCode", 0, None, False),
        ("errorCode", "false", None, False),
    ],
)
def test_required_atoms_bind_exact_json_types_and_presence(
    support_case_and_report, field, present, value, matches
):
    case, _ = support_case_and_report
    expected = next(
        observation
        for observation in case["annotations"][1]["required_observations"]
        if observation["field"] == field
    )
    expected.update(present=present, value=value)
    metrics = _score(support_case_and_report)
    assert metrics["raw_covered_atom_count"] == (6 if matches else 5)
    assert metrics["raw_supported_claim_count"] == (2 if matches else 1)


@pytest.mark.parametrize(
    "fault", ["altered_record", "wrong_event_id", "not_returned", "unselected"]
)
def test_source_binding_rejects_untrusted_evidence(support_case_and_report, fault):
    _, report = support_case_and_report
    if fault == "altered_record":
        # bool and int equality in Python must not defeat exact source validation.
        report["evidence"][1]["record"]["readOnly"] = 1
    elif fault == "wrong_event_id":
        report["evidence"][1]["event_id"] = "test-only-wrong-event"
    elif fault == "not_returned":
        report["tool_history"][0]["result"]["records"] = [report["evidence"][0]]
    else:
        report["selected_event_refs"] = report["selected_event_refs"][:1]
    metrics = _score(support_case_and_report)
    assert metrics["raw_covered_atom_count"] == 2
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["process_valid"] is False
    assert metrics["process_valid_covered_atom_count"] == 0
    assert metrics["process_valid_supported_claim_count"] == 0


def test_seed_is_evidence_without_a_tool_return(support_case_and_report):
    _, report = support_case_and_report
    report["tool_history"][0]["result"]["records"] = report["evidence"][1:]
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["raw_covered_atom_count"] == 6


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate", "reordered"])
def test_public_citations_must_equal_explicit_link_derivation(support_case_and_report, fault):
    _, report = support_case_and_report
    finding = report["findings"][0]
    if fault == "missing":
        finding["citations"] = []
    elif fault == "extra":
        finding["citations"].append(report["evidence"][1]["ref"])
    elif fault == "duplicate":
        finding["citations"] *= 2
    else:
        finding["evidence_links"].append(
            {"citation": report["evidence"][1]["ref"], "fields": ["readOnly"], "role": "context"}
        )
        _sync_citations(finding)
        finding["citations"].reverse()
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] <= 1
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0


@pytest.mark.parametrize("phase", ["plan", "validation", "report", "runner"])
def test_invalid_process_cannot_promote_an_otherwise_supported_report(
    support_case_and_report, phase
):
    _, report = support_case_and_report
    report["failures"] = [{"phase": phase, "code": "test-only-structural-failure"}]
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["raw_covered_atom_count"] == 6
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0
    assert metrics["process_valid_covered_atom_count"] == 0
    assert metrics["required_atom_count"] == 6


@pytest.mark.parametrize("phase", [[], {}])
def test_malformed_failure_phase_preserves_raw_support_but_gates_primary(
    support_case_and_report, phase
):
    _, report = support_case_and_report
    report["failures"] = [{"phase": phase}]
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["raw_covered_atom_count"] == 6
    assert metrics["annotated_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0
    assert metrics["process_valid_covered_atom_count"] == 0


def test_wrong_status_can_keep_raw_atom_credit_but_not_claim_support(support_case_and_report):
    _, report = support_case_and_report
    finding = report["findings"][0]
    finding["status"] = "uncertain"
    finding["evidence_links"][0]["role"] = "context"
    finding["missing_evidence"] = ["A test-only unresolved explanation."]
    metrics = _score(support_case_and_report)
    assert metrics["raw_covered_atom_count"] == 6
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["correct_status_count"] == 1
    assert metrics["process_valid"] is True


@pytest.mark.parametrize("fault", ["duplicate", "changed", "unexpected", "missing"])
def test_finding_coverage_cannot_be_inflated(support_case_and_report, fault):
    _, report = support_case_and_report
    if fault == "duplicate":
        report["findings"].append(copy.deepcopy(report["findings"][0]))
    elif fault == "changed":
        report["findings"][0]["statement"] += " This establishes malicious intent."
    elif fault == "unexpected":
        extra = copy.deepcopy(report["findings"][0])
        extra.update(claim_id="test-only-unexpected", statement="An invented extra claim.")
        report["findings"].append(extra)
    else:
        report["findings"] = report["findings"][:1]
    metrics = _score(support_case_and_report)
    assert metrics["annotated_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["raw_supported_claim_count"] <= 2
    assert metrics["raw_covered_atom_count"] <= 6
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0
    assert metrics["process_valid_covered_atom_count"] == 0
    if fault == "unexpected":
        assert metrics["unexpected_finding_count"] == 1
        assert metrics["raw_supported_claim_count"] == 2
    elif fault == "duplicate":
        assert metrics["duplicate_claim_count"] == 1
        assert metrics["raw_supported_claim_count"] == 1
    elif fault == "missing":
        assert metrics["missing_claim_count"] == 1
        assert metrics["raw_supported_claim_count"] == 1
    else:
        assert metrics["raw_supported_claim_count"] == 1


@pytest.mark.parametrize("suffix", [" ", "\n", "\t"])
def test_statement_comparison_preserves_whitespace(support_case_and_report, suffix):
    _, report = support_case_and_report
    report["findings"][0]["statement"] += suffix
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["raw_covered_atom_count"] == 4
    assert metrics["process_valid"] is False


@pytest.mark.parametrize("claim_id", [[], {}, ["change"], {"claim": "change"}])
def test_unhashable_claim_id_is_unexpected_and_cannot_drop_denominators(
    support_case_and_report, claim_id
):
    _, report = support_case_and_report
    report["findings"][0]["claim_id"] = claim_id
    metrics = _score(support_case_and_report)
    assert metrics["unexpected_finding_count"] == 1
    assert metrics["missing_claim_count"] == 1
    assert metrics["annotated_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["raw_supported_claim_count"] == 1
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0


@pytest.mark.parametrize("selection", [{"citation": "test-only-ref"}, ["test-only-ref"]])
def test_malformed_selection_gates_primary_credit(support_case_and_report, selection):
    _, report = support_case_and_report
    report["selected_event_refs"].append(selection)
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["process_valid"] is False
    assert metrics["process_valid_supported_claim_count"] == 0


def test_extra_valid_context_is_descriptive_not_semantic_precision(support_case_and_report):
    _, report = support_case_and_report
    noise_ref = report["evidence"][2]["ref"]
    report["selected_event_refs"].append(noise_ref)
    report["findings"][0]["evidence_links"].append(
        {"citation": noise_ref, "fields": ["readOnly"], "role": "context"}
    )
    _sync_citations(report["findings"][0])
    metrics = _score(support_case_and_report)
    assert metrics["raw_supported_claim_count"] == 2
    assert metrics["raw_covered_atom_count"] == 6
    assert metrics["extra_declared_atom_count"] == 1
    assert metrics["extra_citation_count"] == 1
    assert "semantic_precision" not in metrics
    assert metrics["process_valid"] is True


def test_empty_failed_report_retains_all_required_denominators(support_case_and_report):
    case, _ = support_case_and_report
    metrics = score_claim_support(
        case,
        {"status": "failed", "failures": [{"phase": "runner", "error_type": "TestOnlyFailure"}]},
    )
    assert metrics["annotated_claim_count"] == 2
    assert metrics["required_atom_count"] == 6
    assert metrics["finding_count"] == 0
    assert metrics["missing_claim_count"] == 2
    assert metrics["raw_supported_claim_count"] == 0
    assert metrics["raw_covered_atom_count"] == 0
    assert metrics["process_valid_supported_claim_rate"] == 0
    assert metrics["process_valid_required_atom_coverage"] == 0


def test_numeric_metric_allowlist_is_explicit_and_finite(support_case_and_report):
    metrics = _score(support_case_and_report)
    numeric_keys = set(NUMERIC_METRIC_KEYS)
    diagnostics = {
        "semantic_entailment_verified",
        "observation_projection_used_for_support",
        "recorded_structural_failure",
    }
    assert numeric_keys == set(NUMERIC_METRICS)
    assert len(numeric_keys) == 21
    assert numeric_keys <= metrics.keys()
    assert numeric_keys.isdisjoint(diagnostics)
    assert all(isinstance(metrics[key], (int, float, bool)) for key in numeric_keys)
    assert all(math.isfinite(float(metrics[key])) for key in numeric_keys)
    assert all(type(metrics[key]) is bool for key in diagnostics)
    assert re.fullmatch(r"[0-9a-f]{64}", scorer_source_sha256())


def test_scorer_preserves_case_and_report_objects(support_case_and_report):
    case, report = support_case_and_report
    before_case, before_report = copy.deepcopy(case), copy.deepcopy(report)
    score_claim_support(case, report)
    assert case == before_case
    assert report == before_report
