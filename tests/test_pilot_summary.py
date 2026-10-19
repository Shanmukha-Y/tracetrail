"""Test-only summary inputs. These are not recorded model experiments."""

import importlib.util
import json
import socket
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

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
def test_only_inputs(tmp_path):
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


def test_summary_exports_review_classifications_without_private_text_or_values(test_only_inputs):
    reviews, _, _ = load_test_review(test_only_inputs)
    serialized = json.dumps(reviews)
    assert "TEST-ONLY PRIVATE REVIEW TEXT" not in serialized
    assert "TEST-ONLY PRIVATE VALUE" not in serialized
    assert reviews["test-only-cell"]["claims"][0]["source_references"] == [
        {
            "citation": "sha256:" + "a" * 64 + "/Records/0",
            "fields": ["userIdentity.accessKeyId"],
        }
    ]


def test_preserved_draft_provenance_exports_count_and_hash_without_draft_text(test_only_inputs):
    canary = "TESTONLY_PRIVATE_PRELIMINARY_DRAFT_91BD"
    history = [
        {"reason": canary, "draft": {"text": canary}},
        {"reason": canary, "cell_id": canary},
    ]
    test_only_inputs["document"]["rows"][0]["stage1_draft_history"] = history
    reviews, fingerprints, _ = load_test_review(test_only_inputs)
    assert fingerprints[0]["preserved_stage1_drafts"] == [
        {
            "cell_id": "test-only-cell",
            "draft_count": 2,
            "history_sha256": summary.canonical(history),
        }
    ]
    assert canary not in json.dumps({"reviews": reviews, "fingerprints": fingerprints}, default=str)
    assert reviews["test-only-cell"]["material_prose_flag_count"] == 0
    assert all(
        c["outcome"] == "source_limited_unknown" for c in reviews["test-only-cell"]["claims"]
    )


def test_preserved_draft_provenance_refuses_non_list_history(test_only_inputs):
    canary = "TESTONLY_PRIVATE_MALFORMED_DRAFT_F182"
    test_only_inputs["document"]["rows"][0]["stage1_draft_history"] = {"reason": canary}
    with pytest.raises(summary.SummaryError, match="draft history must be a list") as caught:
        load_test_review(test_only_inputs)
    assert canary not in str(caught.value)


@pytest.mark.parametrize("fault", ["cell_hash", "missing_claim", "duplicate_claim", "protocol"])
def test_summary_refuses_stale_or_incomplete_primary_review(test_only_inputs, fault):
    document = test_only_inputs["document"]
    if fault == "cell_hash":
        document["rows"][0]["cell_result_sha256"] = "0" * 64
    elif fault == "missing_claim":
        document["rows"][0]["claim_reviews"].pop()
    elif fault == "duplicate_claim":
        document["rows"][0]["claim_reviews"][-1] = deepcopy(document["rows"][0]["claim_reviews"][0])
    else:
        document["pilot_protocol_sha256"] = "0" * 64
    with pytest.raises(summary.SummaryError):
        load_test_review(test_only_inputs)


def test_summary_refuses_unreviewable_slots_labeled_as_readable_claims(test_only_inputs):
    test_only_inputs["document"]["rows"][0]["report_available"] = False
    with pytest.raises(summary.SummaryError, match="unreviewable"):
        load_test_review(test_only_inputs)


def test_summary_binds_a_separately_locked_stage_file_and_rejects_later_change(
    test_only_inputs,
):
    stage_path = test_only_inputs["path"].with_name("test-only-returned-stage.json")
    stage_path.write_text(json.dumps({"cell_id": "test-only-cell", "cell_result_sha256": "b" * 64}))
    row = test_only_inputs["document"]["rows"][0]
    row["returned_evidence_stage_path"] = stage_path.name
    row["returned_evidence_stage_sha256"] = summary.sha(stage_path)
    _, fingerprints, inputs = load_test_review(test_only_inputs)
    assert inputs[stage_path] == row["returned_evidence_stage_sha256"]
    assert fingerprints[0]["separately_locked_stages"][0]["cell_id"] == "test-only-cell"
    stage_path.write_text('{"cell_id":"different-test-only-cell"}')
    with pytest.raises(summary.SummaryError, match="separately locked"):
        load_test_review(test_only_inputs)


def test_missing_basis_labels_preserve_all_requested_slots_without_false_classification():
    row = {
        "semantic_review": {
            "report_available": False,
            "claims": [
                {"outcome": "unreviewable_report", "declared_basis": None} for _ in range(4)
            ],
            "material_prose_flag_count": 0,
        }
    }
    counts = summary.semantic_counts([row])
    assert counts["requested_claim_slots"] == 4
    assert counts["outcome_counts"]["unreviewable_report"] == 4
    assert counts["declared_basis_counts"] == {"not_recorded": 4}
    json.dumps(counts, sort_keys=True)


def test_numeric_row_redacts_secret_shaped_labels_and_rejects_non_numeric_metrics(
    test_only_inputs,
):
    canary = "AKIA_TESTONLY_PRIVATE_SCOPE_7D4F"
    reviews, _, _ = load_test_review(test_only_inputs)
    run = deepcopy(test_only_inputs["run"])
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


def test_runtime_gate_redacts_unknown_issue_labels_and_never_copies_string_values():
    canary = "sk_test_PRIVATE_SCOPE_9C8A"
    public = summary.public_runtime_gate(
        {
            "resource_measurement_issues": ["foreign_model_observed", canary],
            "first_ten_wall_seconds": canary,
            "max_total_runs": canary,
            "unrecognized_scope": canary,
        }
    )
    assert canary not in json.dumps(public)
    assert public["resource_measurement_issues"] == [
        "foreign_model_observed",
        "other_recorded_resource_issue",
    ]
    assert public["redacted_resource_issue_count"] == 1
    assert public["first_ten_wall_seconds"] is None
    assert public["max_total_runs"] is None


def test_review_field_path_canary_is_refused_without_echoing_private_scope(test_only_inputs):
    canary = "userIdentity.AKIA_TESTONLY_PRIVATE_SCOPE_913"
    claim = test_only_inputs["document"]["rows"][0]["claim_reviews"][0]
    claim["source_checks"][0]["fields"][0]["path"] = canary
    with pytest.raises(summary.SummaryError) as caught:
        load_test_review(test_only_inputs)
    assert canary not in str(caught.value)
    assert "frozen source schema" in str(caught.value)


def test_secondary_assessment_canaries_are_counted_as_unclassified_not_published(
    test_only_inputs,
):
    canary = "TESTONLY_PRIVATE_LABEL_C8A1"
    primary, _, _ = load_test_review(test_only_inputs)
    original_claims = test_only_inputs["document"]["rows"][0]["claim_reviews"]
    document = {
        "frozen_protocol_sha256": "c" * 64,
        "review_protocol_sha256": "d" * 64,
        "rows": [
            {
                "cell_id": "test-only-cell",
                "cell_result_sha256": "b" * 64,
                "claim_reviews": [
                    {
                        "claim_id": claim["claim_id"],
                        "original_primary_review": claim,
                        "secondary_assessment": canary if index == 0 else "agree",
                    }
                    for index, claim in enumerate(original_claims)
                ],
                "prose_reviews": [{"assessment": canary}],
            }
        ],
    }
    path = test_only_inputs["path"].with_name("test-only-secondary.json")
    path.write_text(json.dumps(document))
    public, _ = summary.secondary_metadata(
        [path], primary, {"test-only-cell": test_only_inputs["run"]}, "c" * 64, "d" * 64
    )
    value = {key: item for key, item in public[0].items() if key != "path"}
    assert canary not in json.dumps(value)
    assert value["unclassified_assessment_count"] == 2
    assert value["disagreement_count"] == 0
    assert value["claim_assessments"]["agree"] == 3


@pytest.mark.parametrize("last_assessment", ["agree_material_error", "TESTONLY_UNKNOWN_ASSESSMENT"])
def test_secondary_fingerprint_binds_document_not_final_assessment(
    test_only_inputs, last_assessment
):
    primary, _, _ = load_test_review(test_only_inputs)
    original_claims = test_only_inputs["document"]["rows"][0]["claim_reviews"]
    document = {
        "frozen_protocol_sha256": "c" * 64,
        "review_protocol_sha256": "d" * 64,
        "rows": [
            {
                "cell_id": "test-only-cell",
                "cell_result_sha256": "b" * 64,
                "claim_reviews": [
                    {
                        "claim_id": claim["claim_id"],
                        "original_primary_review": claim,
                        "secondary_assessment": "agree",
                    }
                    for claim in original_claims
                ],
                "prose_reviews": [{"assessment": last_assessment}],
            }
        ],
    }
    path = test_only_inputs["path"].with_name("test-only-secondary-fingerprint.json")
    path.write_text(json.dumps(document))
    public, inputs = summary.secondary_metadata(
        [path], primary, {"test-only-cell": test_only_inputs["run"]}, "c" * 64, "d" * 64
    )
    assert public[0]["sha256"] == inputs[path] == summary.sha(path)
    assert public[0]["sha256"] not in public[0]["redacted_assessment_sha256"]


def test_explicit_prose_adjudication_adds_a_separate_view_without_public_quotes(test_only_inputs):
    quote = "TESTONLY_PRIVATE_MODEL_QUOTE_6B0A"
    primary_row = test_only_inputs["document"]["rows"][0]
    primary_row["material_prose_errors"] = [{"quote": quote}]
    reviews, _, _ = load_test_review(test_only_inputs)
    resolution_path = test_only_inputs["path"].with_name("test-only-resolution.json")
    entry = {
        "cell_id": "test-only-cell",
        "cell_result_sha256": "b" * 64,
        "material_prose_index": 0,
        "adjudicated_material": False,
        "quote": quote,
        "assessment": "TESTONLY_PRIVATE_ROOT_JUDGMENT_C91",
    }
    resolution_path.write_text(json.dumps({"rows": [entry]}))
    fingerprints, _ = summary.apply_prose_resolutions(
        [resolution_path], reviews, {"test-only-cell": test_only_inputs["run"]}, "c" * 64
    )
    review = reviews["test-only-cell"]
    assert review["material_prose_flag_count"] == 1
    assert review["primary_material_prose_error_count"] == 1
    assert review["adjudicated_material_prose_error_count"] == 0
    assert fingerprints[0]["primary_counts_changed"] is False
    run = deepcopy(test_only_inputs["run"])
    run.update(
        {
            "fixture_sha256": "a" * 64,
            "claim_support_metrics": {
                key: False if key == "process_valid" else 0 for key in summary.NUMERIC_KEYS
            },
            "metrics": {},
        }
    )
    run["pilot"]["wall_seconds"] = 1
    public = summary.numeric_row(run, review, summary.NUMERIC_KEYS)
    assert quote not in json.dumps(public)
    assert entry["assessment"] not in json.dumps(public)
    public_fingerprint = {k: v for k, v in fingerprints[0].items() if k != "path"}
    assert quote not in json.dumps(public_fingerprint)
    counts = summary.semantic_counts([public])
    assert counts["primary_runs_with_material_prose_errors"] == 1
    assert counts["adjudicated_runs_with_material_prose_errors"] == 0
    assert counts["requested_claim_slots"] == 4


@pytest.mark.parametrize("fault", ["index", "quote", "hash", "duplicate", "boolean"])
def test_prose_adjudication_refuses_forged_or_duplicate_bindings(test_only_inputs, fault):
    quote = "TESTONLY exact primary quote"
    test_only_inputs["document"]["rows"][0]["material_prose_errors"] = [{"quote": quote}]
    reviews, _, _ = load_test_review(test_only_inputs)
    entry = {
        "cell_id": "test-only-cell",
        "cell_result_sha256": "b" * 64,
        "material_prose_index": 0,
        "adjudicated_material": False,
        "quote": quote,
    }
    if fault == "index":
        entry["material_prose_index"] = 1
    elif fault == "quote":
        entry["quote"] += " altered"
    elif fault == "hash":
        entry["cell_result_sha256"] = "0" * 64
    elif fault == "boolean":
        entry["adjudicated_material"] = 0
    entries = [entry, deepcopy(entry)] if fault == "duplicate" else [entry]
    path = test_only_inputs["path"].with_name("test-only-resolution.json")
    path.write_text(json.dumps({"resolutions": entries}))
    with pytest.raises(summary.SummaryError):
        summary.apply_prose_resolutions(
            [path], reviews, {"test-only-cell": test_only_inputs["run"]}, "c" * 64
        )


@pytest.mark.parametrize("value", [True, -1, 1.5, float("inf"), 10**1000, "TESTONLY_PRIVATE_COUNT"])
def test_public_primary_counts_require_bounded_finite_integers(value):
    with pytest.raises(summary.SummaryError):
        summary.public_metrics({"finding_count": value}, ("finding_count",))


def test_summary_refuses_incomplete_batch_before_publication(tmp_path):
    protocol = tmp_path / "protocol.json"
    raw = tmp_path / "raw.json"
    sdk = tmp_path / "sdk.json"
    audit = tmp_path / "audit.json"
    protocol.write_text(
        json.dumps(
            {
                "protocol_id": summary.PILOT_ID,
                "evaluation": {"numeric_metric_keys": summary.NUMERIC_KEYS},
            }
        )
    )
    raw.write_text(json.dumps({"pilot_id": summary.PILOT_ID, "target_runs": 20, "runs": []}))
    sdk.write_text("{}")
    audit.write_text("{}")
    args = SimpleNamespace(protocol=protocol, raw=raw, sdk=sdk, verification=audit)
    with pytest.raises(summary.SummaryError, match="Every target assignment"):
        summary.build(args)


def test_repeat_content_hash_ignores_runtime_metadata_but_preserves_failed_wire_output():
    run = {
        "status": "failed",
        "started_at": "TEST-ONLY CLOCK A",
        "local_traces": [{"id": "TEST-ONLY UUID A"}],
        "model_history": [
            {"phase": "report", "output": "TEST-ONLY malformed report A", "duration_seconds": 1}
        ],
    }
    changed = deepcopy(run)
    changed["started_at"] = "TEST-ONLY CLOCK B"
    changed["local_traces"][0]["id"] = "TEST-ONLY UUID B"
    changed["model_history"][0]["duration_seconds"] = 2
    assert summary.content_hash(changed) == summary.content_hash(run)
    changed["model_history"][0]["output"] = "TEST-ONLY malformed report B"
    assert summary.content_hash(changed) != summary.content_hash(run)


def test_summary_write_cannot_replace_existing_file_or_symbolic_link(tmp_path):
    existing = tmp_path / "preserved.json"
    existing.write_text('{"preserved":true}')
    link = tmp_path / "link.json"
    link.symlink_to(existing)
    for path in (existing, link):
        with pytest.raises(summary.SummaryError):
            summary.write_exclusive(path, {"replacement": True})
    assert existing.read_text() == '{"preserved":true}'
