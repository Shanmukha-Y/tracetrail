"""Constructed claim-link tests check structure, never model reasoning quality."""

import json
import socket
from copy import deepcopy

import pytest

from tracetrail.claims import finding_citations, validate_finding_links
from tracetrail.store import CloudTrailStore


@pytest.fixture(autouse=True)
def no_queries_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Claim-link validation must not fetch evidence or run a model")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(CloudTrailStore, "load", forbidden)
    monkeypatch.setattr(CloudTrailStore, "get", forbidden)
    monkeypatch.setattr(CloudTrailStore, "query", forbidden)


def evidence(ref="synthetic-ref", **changes):
    record = {
        "eventName": "StopLogging",
        "userIdentity": {"accessKeyId": "SYNTHETIC_KEY"},
        "requestParameters": {"enabled": False},
        "responseElements": None,
        "resources": [{"ARN": "arn:aws:s3:::synthetic", "literal.dot": True}],
    }
    record.update(changes)
    return {"ref": ref, "record": record}


def link(citation="synthetic-ref", fields=None, role="context"):
    return {
        "citation": citation,
        "fields": fields if fields is not None else ["eventName"],
        "role": role,
    }


def finding(**changes):
    result = {
        "claim_id": "test-only-claim",
        "statement": "This activity was approved maintenance.",
        "rationale": "The record shows an API request but no approval evidence.",
        "missing_evidence": ["Approval or change-ticket records."],
        "status": "uncertain",
        "evidence_links": [link()],
    }
    result.update(changes)
    return result


def codes(report):
    return {
        item["code"] for item in validate_finding_links(report, [evidence()], ["synthetic-ref"])
    }


@pytest.mark.parametrize(
    "status,role", [("supported", "supports"), ("refuted", "contradicts"), ("uncertain", "context")]
)
def test_required_role_and_explicit_uncertainty_accept_valid_structure(status, role):
    report = finding(status=status, evidence_links=[link(role=role)])
    assert validate_finding_links(report, [evidence()], ["synthetic-ref"]) == []


@pytest.mark.parametrize(
    "status,role,expected",
    [
        ("supported", "context", "missing_supporting_evidence"),
        ("supported", "contradicts", "missing_supporting_evidence"),
        ("refuted", "context", "missing_contradicting_evidence"),
        ("refuted", "supports", "missing_contradicting_evidence"),
    ],
)
def test_context_or_opposite_role_cannot_fill_required_evidence_role(status, role, expected):
    report = finding(status=status, evidence_links=[link(role=role)])
    before = deepcopy(report)
    assert expected in codes(report)
    assert report == before
    assert report["status"] == status


def test_uncertain_without_missing_evidence_is_rejected_without_status_repair():
    report = finding(missing_evidence=[])
    assert "missing_uncertainty" in codes(report)
    assert report["status"] == "uncertain"
    assert report["missing_evidence"] == []


def test_uncertainty_can_have_no_links_when_the_evidence_is_insufficient():
    assert codes(finding(evidence_links=[])) == set()
    assert finding_citations(finding(evidence_links=[])) == []


@pytest.mark.parametrize("value", [None, "", " \n\t", "x" * 601, 123])
def test_rationale_must_be_nonblank_and_bounded(value):
    assert "invalid_finding_rationale" in codes(finding(rationale=value))


def test_rationale_and_missing_entry_length_boundaries_are_inclusive():
    assert codes(finding(rationale="x" * 600, missing_evidence=["x" * 300])) == set()
    assert "invalid_missing_evidence_entry" in codes(finding(missing_evidence=["x" * 301]))


@pytest.mark.parametrize("missing", [None, "missing", ["a", "b", "c", "d", "e"]])
def test_missing_evidence_list_has_a_fixed_shape_and_bound(missing):
    assert "invalid_missing_evidence" in codes(finding(missing_evidence=missing))


@pytest.mark.parametrize("entry", [None, "", " \n", 1, {}, "x" * 301])
def test_invalid_missing_evidence_entries_do_not_satisfy_uncertainty(entry):
    errors = codes(finding(missing_evidence=[entry]))
    assert {"invalid_missing_evidence_entry", "missing_uncertainty"} <= errors


def test_unknown_or_unselected_citations_are_not_substituted():
    unknown = finding(evidence_links=[link("unknown")])
    assert "unknown_evidence_link_citation" in codes(unknown)
    assert finding_citations(unknown) == ["unknown"]
    unselected = finding(evidence_links=[link("other")])
    errors = validate_finding_links(unselected, [evidence(), evidence("other")], ["synthetic-ref"])
    assert {item["code"] for item in errors} == {"unselected_evidence_link_citation"}
    assert finding_citations(unselected) == ["other"]


@pytest.mark.parametrize("citation", [None, "", " \n", 1, {}])
def test_invalid_link_citations_fail_without_leaking_source_values(citation):
    report = finding(evidence_links=[link(citation)])
    assert "invalid_evidence_link_citation" in codes(report)


@pytest.mark.parametrize(
    "field",
    [
        "eventName",
        "requestParameters.enabled",
        "responseElements",
        "resources",
        "errorCode",
        "errorMessage",
    ],
)
def test_actual_null_false_whole_array_and_standard_absence_paths_resolve(field):
    assert codes(finding(evidence_links=[link(fields=[field])])) == set()


@pytest.mark.parametrize(
    "field",
    [
        "missing",
        "requestParameters.missing",
        "responseElements.errorCode",
        "userIdentity.missing",
        "resources.0.ARN",
    ],
)
def test_arbitrary_missing_paths_and_array_index_paths_are_not_observed_evidence(field):
    report = finding(evidence_links=[link(fields=[field])])
    errors = validate_finding_links(report, [evidence()], ["synthetic-ref"])
    assert errors == [
        {
            "code": "unresolved_evidence_link_field",
            "claim_id": "test-only-claim",
            "citation": "synthetic-ref",
            "field": field,
        }
    ]


def test_only_the_four_standard_top_level_absence_fields_resolve_when_missing():
    item = {"ref": "synthetic-ref", "record": {}}
    allowed = ["errorCode", "errorMessage", "requestParameters", "responseElements"]
    report = finding(evidence_links=[link(fields=allowed)])
    assert validate_finding_links(report, [item], ["synthetic-ref"]) == []
    report["evidence_links"][0]["fields"].append("userIdentity")
    assert any(
        error.get("field") == "userIdentity"
        for error in validate_finding_links(report, [item], ["synthetic-ref"])
    )


@pytest.mark.parametrize(
    "field",
    ["", " ", "requestParameters..enabled", ".eventName", "eventName.", "x" * 513, None, 123],
)
def test_blank_ambiguous_and_oversized_paths_are_rejected(field):
    assert "invalid_evidence_link_field" in codes(finding(evidence_links=[link(fields=[field])]))


def test_field_path_limit_accepts_512_characters_without_normalizing_the_path():
    path = "x" * 512
    report = finding(evidence_links=[link(fields=[path])])
    item = evidence(**{path: "exact"})
    assert validate_finding_links(report, [item], ["synthetic-ref"]) == []


@pytest.mark.parametrize("fields", [[], "eventName", None, ["eventName"] * 7])
def test_field_lists_must_have_one_to_six_entries(fields):
    report = finding(
        evidence_links=[{"citation": "synthetic-ref", "fields": fields, "role": "context"}]
    )
    assert "invalid_evidence_link_fields" in codes(report)


def test_repeated_field_paths_and_identical_links_are_not_extra_evidence():
    repeated_field = finding(evidence_links=[link(fields=["eventName", "eventName"])])
    assert "duplicate_evidence_link_field" in codes(repeated_field)
    repeated_link = finding(evidence_links=[link(), link()])
    assert "duplicate_evidence_link" in codes(repeated_link)
    reordered_link = finding(
        evidence_links=[
            link(fields=["eventName", "errorCode"]),
            link(fields=["errorCode", "eventName"]),
        ]
    )
    assert "duplicate_evidence_link" in codes(reordered_link)


def test_same_record_can_supply_distinct_roles_or_fields_without_duplicate_rejection():
    report = finding(
        evidence_links=[
            link(role="supports"),
            link(role="contradicts"),
            link(fields=["responseElements"]),
        ]
    )
    assert codes(report) == set()
    assert finding_citations(report) == ["synthetic-ref"]


@pytest.mark.parametrize("links", [None, {}, [link()] * 7])
def test_evidence_link_list_is_bounded(links):
    assert "invalid_evidence_links" in codes(finding(evidence_links=links))


@pytest.mark.parametrize("role", [None, "support", "proves", {}, 1])
def test_unknown_roles_fail_structural_validation(role):
    assert "invalid_evidence_link_role" in codes(finding(evidence_links=[link(role=role)]))


def test_public_citations_come_only_from_ordered_explicit_link_references():
    report = finding(
        evidence_links=[link("second"), link("first"), link("second", role="supports")],
        citations=["not-authoritative"],
        selected_event_refs=["also-not-authoritative"],
    )
    assert finding_citations(report) == ["second", "first"]
    assert "not-authoritative" not in finding_citations(report)


def test_error_reports_do_not_return_record_values_or_rationale_text():
    item = evidence(requestParameters={"secret": "SYNTHETIC_SECRET_NEVER_RETURN"})
    report = finding(
        rationale="MODEL_TEXT_NEVER_RETURN" * 50,
        missing_evidence=[{"value": "MALFORMED_TEXT_NEVER_RETURN"}],
        evidence_links=[link(fields=["requestParameters.absent"])],
    )
    encoded = json.dumps(validate_finding_links(report, [item], ["synthetic-ref"]))
    for value in (
        "SYNTHETIC_SECRET_NEVER_RETURN",
        "MODEL_TEXT_NEVER_RETURN",
        "MALFORMED_TEXT_NEVER_RETURN",
    ):
        assert value not in encoded
    assert '"value"' not in encoded


def test_duplicate_record_references_cannot_resolve_to_an_arbitrary_record():
    report = finding()
    errors = validate_finding_links(
        report, [evidence(), evidence(eventName="Other")], ["synthetic-ref"]
    )
    assert {item["code"] for item in errors} == {"ambiguous_evidence_link_citation"}


def test_structurally_valid_links_do_not_certify_entailment_or_repair_status():
    """A deliberately wrong semantic judgment remains outside this validator."""
    report = finding(
        statement="Logging stayed disabled for hours.",
        status="refuted",
        rationale="The observed request is treated as a contradiction in this test.",
        missing_evidence=[],
        evidence_links=[link(role="contradicts")],
    )
    before = deepcopy(report)
    assert codes(report) == set()
    assert report == before
    assert report["status"] == "refuted"


def test_validation_never_mutates_findings_sources_or_selections():
    report, items, selected = finding(), [evidence()], ["synthetic-ref"]
    before = deepcopy((report, items, selected))
    assert validate_finding_links(report, items, selected) == []
    assert (report, items, selected) == before
