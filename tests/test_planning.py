"""Pure planning-contract tests with constructed data, never model evidence."""

import json
import socket
from copy import deepcopy

import pytest
from pydantic import ValidationError

from tracetrail.planning import Decision, materialize_query, validate_decision
from tracetrail.store import CloudTrailStore, Query

EVIDENCE = [{"ref": "ref-a", "record": {"eventName": "SyntheticActivity"}}]
HYPOTHESES = [
    {"claim_id": "a", "statement": "Synthetic first claim"},
    {"claim_id": "b", "statement": "Synthetic second claim"},
]


@pytest.fixture(autouse=True)
def no_hidden_reads_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Planning validation must not invoke tools or network requests")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(CloudTrailStore, "load", forbidden)
    monkeypatch.setattr(CloudTrailStore, "get", forbidden)
    monkeypatch.setattr(CloudTrailStore, "query", forbidden)


def catalog():
    return {
        "candidates": [
            {
                "id": "P-key",
                "query": {"access_key": "SYNTHETIC_KEY"},
                "sources": [{"citation": "ref-a", "field": "userIdentity.accessKeyId"}],
            },
            {"id": "P-principal", "query": {"principal": "synthetic-user"}},
        ],
        "continuations": [
            {
                "id": "C-next",
                "attempt_id": "Q0",
                "query": {
                    "access_key": "SYNTHETIC_KEY",
                    "principal": "synthetic-user",
                    "limit": 7,
                    "offset": 7,
                    "start_time": "2026-01-01T10:00:00Z",
                },
            }
        ],
    }


def decision(action="finish", **changes):
    result = {
        "ledger": [
            {
                "claim_id": item["claim_id"],
                "evidence_refs": ["ref-a"],
                "open_question": "",
                "candidate_ids": [],
                "attempt_ids": [],
            }
            for item in HYPOTHESES
        ],
        "action": action,
        "rationale": "Test-only planning choice",
        "claim_id": "a",
        "candidate_id": None,
        "continuation_id": None,
        "query": None,
        "identifier": None,
        "dispositions": [],
    }
    if action == "finish":
        result["dispositions"] = [
            {
                "pivot_ids": ["P-key", "P-principal", "C-next"],
                "disposition": "deferred",
                "reason": "The model elects to leave these observed searches open.",
                "attempt_ids": [],
            }
        ]
    result.update(changes)
    return result


def query_attempt(args=None, **changes):
    output = {"records": [], "matched": 0, "truncated": False, "next_offset": None}
    output.update(changes)
    return {
        "name": "query_events",
        "args": args or {"access_key": "SYNTHETIC_KEY"},
        "result": output,
    }


def errors(value, *, history=None, remaining=3, coverage=None):
    return validate_decision(
        value,
        deepcopy(EVIDENCE),
        history or [],
        deepcopy(HYPOTHESES),
        remaining,
        coverage if coverage is not None else catalog(),
    )


def test_zero_query_finish_is_allowed_with_explicit_complete_visible_accounting():
    value = decision()
    before = deepcopy(value)
    assert errors(value) == []
    assert errors(value, remaining=0) == []
    assert value == before


def test_decision_schema_requires_explicit_nullable_branches_and_array_accounting():
    schema = Decision.model_json_schema()
    assert set(schema["required"]) == set(schema["properties"])
    for name in ("candidate_id", "continuation_id", "query", "identifier"):
        assert {"type": "null"} in schema["properties"][name]["anyOf"]
        assert "default" not in schema["properties"][name]
    for name in ("ledger", "dispositions"):
        assert schema["properties"][name]["type"] == "array"
        assert "anyOf" not in schema["properties"][name]


@pytest.mark.parametrize(
    "field", ("candidate_id", "continuation_id", "query", "identifier", "dispositions")
)
def test_omitted_branch_fields_are_rejected_without_inference_or_fallback(field):
    value = decision("query_events", candidate_id="P-key")
    value.pop(field)
    before = deepcopy(value)
    assert errors(value) == ["invalid_decision_shape"]
    with pytest.raises(ValidationError):
        materialize_query(value, catalog())
    assert value == before


def test_explicit_all_null_query_branch_is_still_rejected_without_selection():
    value = decision("query_events")
    assert errors(value) == ["exclusive_query_source_required"]
    with pytest.raises(ValueError, match="exactly one query source"):
        materialize_query(value, catalog())


def test_empty_catalog_needs_no_fabricated_dispositions_or_queries():
    assert errors(decision(dispositions=[]), coverage={"candidates": [], "continuations": []}) == []


def test_candidate_query_materializes_only_its_observed_filter_with_limit_twenty():
    coverage = catalog()
    value = decision("query_events", candidate_id="P-key")
    before = deepcopy((value, coverage))
    assert errors(value, coverage=coverage) == []
    query = materialize_query(value, coverage)
    assert query == Query(access_key="SYNTHETIC_KEY", limit=20)
    assert (value, coverage) == before


def test_custom_query_preserves_model_scope_limit_and_offset():
    scope = {
        "principal": "synthetic-user",
        "source_ip": "192.0.2.5",
        "limit": 3,
        "offset": 2,
        "start_time": "2026-01-01T05:00:00-05:00",
    }
    value = decision("query_events", query=scope)
    assert errors(value) == []
    assert materialize_query(value, catalog()) == Query.model_validate(scope)


def test_continuation_preserves_the_exact_existing_query_filters_and_page_size():
    value = decision("query_events", continuation_id="C-next")
    coverage = catalog()
    before = deepcopy(coverage)
    assert errors(value) == []
    assert materialize_query(value, coverage) == Query.model_validate(
        coverage["continuations"][0]["query"]
    )
    assert materialize_query(value, coverage).limit == 7
    assert materialize_query(value, coverage).offset == 7
    assert coverage == before


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"candidate_id": "P-key", "query": {"event_name": "StopLogging"}},
        {"candidate_id": "P-key", "continuation_id": "C-next"},
        {"continuation_id": "C-next", "query": {}},
    ],
)
def test_query_actions_need_exactly_one_source_without_fallback(changes):
    value = decision("query_events", **changes)
    assert "exclusive_query_source_required" in errors(value)
    with pytest.raises(ValueError):
        materialize_query(value, catalog())


@pytest.mark.parametrize(
    "field,expected",
    [
        ("candidate_id", "unknown_action_candidate_id"),
        ("continuation_id", "unknown_action_continuation_id"),
    ],
)
def test_unknown_catalog_choices_are_rejected_not_replaced(field, expected):
    value = decision("query_events", **{field: "unknown"})
    assert expected in errors(value)
    with pytest.raises(ValueError):
        materialize_query(value, catalog())


@pytest.mark.parametrize(
    "action,extra",
    [
        ("query_events", {"query": {}}),
        ("get_event", {"identifier": "event-to-look-up"}),
    ],
)
def test_tool_calls_require_remaining_budget_and_a_requested_claim(action, extra):
    value = decision(action, **extra)
    assert "query_budget_exhausted" in errors(value, remaining=0)
    assert "unknown_action_claim_id" in errors({**value, "claim_id": "unknown"})


def test_get_event_does_not_require_the_identifier_to_have_been_retrieved_already():
    assert errors(decision("get_event", identifier="new-exact-event-id")) == []


@pytest.mark.parametrize("identifier", [None, " "])
def test_get_event_requires_a_nonblank_identifier(identifier):
    assert "get_event_identifier_required" in errors(decision("get_event", identifier=identifier))


@pytest.mark.parametrize("action", ["query_events", "get_event"])
def test_tool_actions_cannot_also_supply_finish_dispositions(action):
    value = decision(
        action,
        query={} if action == "query_events" else None,
        identifier="id" if action == "get_event" else None,
        dispositions=decision()["dispositions"],
    )
    assert "tool_action_must_not_have_dispositions" in errors(value)


def test_action_specific_arguments_are_mutually_exclusive():
    assert "query_action_must_not_have_identifier" in errors(
        decision("query_events", query={}, identifier="id")
    )
    assert "get_event_must_not_request_query" in errors(
        decision("get_event", identifier="id", candidate_id="P-key")
    )
    for extra in (
        {"query": {}},
        {"candidate_id": "P-key"},
        {"continuation_id": "C-next"},
        {"identifier": "id"},
    ):
        assert "finish_must_not_request_tool" in errors(decision(**extra))


@pytest.mark.parametrize("fault", ["missing", "extra", "duplicate"])
def test_ledger_covers_exactly_the_requested_claims_once(fault):
    value = decision()
    if fault == "missing":
        value["ledger"].pop()
    elif fault == "extra":
        value["ledger"][0]["claim_id"] = "unknown"
    else:
        value["ledger"].append(deepcopy(value["ledger"][0]))
    expected = "duplicate_ledger_claim_id" if fault == "duplicate" else "claim_ledger_coverage"
    assert expected in errors(value)


@pytest.mark.parametrize(
    "field,unknown,expected",
    [
        ("evidence_refs", "unknown", "unknown_ledger_evidence_ref"),
        ("candidate_ids", "C-next", "unknown_ledger_candidate_id"),
        ("attempt_ids", "Q9", "unknown_ledger_attempt_id"),
    ],
)
def test_ledger_references_have_exact_domains(field, unknown, expected):
    value = decision()
    value["ledger"][0][field] = [unknown]
    assert expected in errors(value)


@pytest.mark.parametrize(
    "field,item,expected",
    [
        ("evidence_refs", "ref-a", "duplicate_ledger_evidence_ref"),
        ("candidate_ids", "P-key", "duplicate_ledger_candidate_id"),
        ("attempt_ids", "Q0", "duplicate_ledger_attempt_id"),
    ],
)
def test_duplicate_ledger_references_are_not_extra_evidence(field, item, expected):
    value = decision()
    value["ledger"][0][field] = [item, item]
    assert expected in errors(value, history=[query_attempt()])


def test_attempt_ids_follow_actual_tool_indices_and_exclude_exact_record_lookups():
    history = [{"name": "get_event", "args": {"identifier": "id"}, "result": {}}, query_attempt()]
    value = decision()
    value["ledger"][0]["attempt_ids"] = ["Q1"]
    assert errors(value, history=history) == []
    value["ledger"][0]["attempt_ids"] = ["Q0"]
    assert "unknown_ledger_attempt_id" in errors(value, history=history)


def test_tested_scope_needs_a_successful_matching_query_for_every_named_candidate():
    value = decision(
        dispositions=[
            {
                "pivot_ids": ["P-key", "P-principal"],
                "disposition": "tested_under_recorded_scope",
                "reason": "These filters were used under the recorded narrow scope.",
                "attempt_ids": ["Q0"],
            },
            {
                "pivot_ids": ["C-next"],
                "disposition": "deferred",
                "reason": "Page remains open.",
                "attempt_ids": [],
            },
        ]
    )
    args = {
        "access_key": "SYNTHETIC_KEY",
        "principal": "synthetic-user",
        "event_name": "GetObject",
        "start_time": "2026-01-01T10:00:00Z",
        "end_time": "2026-01-01T10:01:00Z",
        "limit": 2,
    }
    history = [query_attempt(args)]
    before = deepcopy(history)
    assert errors(value, history=history) == []
    assert history == before  # Matching does not broaden the actual search scope.
    assert "tested_pivot_requires_matching_successful_attempt" in errors(
        value, history=[query_attempt()]
    )


@pytest.mark.parametrize(
    "result",
    [
        {"error": {"code": "test-only-error"}},
        {},
        {"records": [], "matched": True, "truncated": False},
    ],
)
def test_failed_or_malformed_results_cannot_justify_a_tested_disposition(result):
    value = decision()
    value["dispositions"] = [
        {
            "pivot_ids": ["P-key"],
            "disposition": "tested_under_recorded_scope",
            "reason": "Attempted.",
            "attempt_ids": ["Q0"],
        },
        {
            "pivot_ids": ["P-principal", "C-next"],
            "disposition": "deferred",
            "reason": "Open.",
            "attempt_ids": [],
        },
    ]
    history = [query_attempt()]
    history[0]["result"] = result
    assert "tested_pivot_requires_matching_successful_attempt" in errors(value, history=history)


def test_compact_successful_query_results_are_equivalent_to_raw_history():
    value = decision(
        dispositions=[
            {
                "pivot_ids": ["P-key"],
                "disposition": "tested_under_recorded_scope",
                "reason": "Scoped.",
                "attempt_ids": ["Q0"],
            },
            {
                "pivot_ids": ["P-principal", "C-next"],
                "disposition": "deferred",
                "reason": "Open.",
                "attempt_ids": [],
            },
        ]
    )
    raw = query_attempt()
    compact = deepcopy(raw)
    compact["result"]["returned_citations"] = compact["result"].pop("records")
    assert errors(value, history=[raw]) == errors(value, history=[compact]) == []


def test_pending_continuations_cannot_be_marked_tested_even_with_an_actual_query_id():
    value = decision(
        dispositions=[
            {
                "pivot_ids": ["P-key", "P-principal", "C-next"],
                "disposition": "tested_under_recorded_scope",
                "reason": "Test-only mistaken accounting.",
                "attempt_ids": ["Q0"],
            }
        ]
    )
    history = [query_attempt({"access_key": "SYNTHETIC_KEY", "principal": "synthetic-user"})]
    assert "pending_continuation_cannot_be_tested" in errors(value, history=history)


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("missing", "finish_disposition_coverage"),
        ("duplicate", "duplicate_pivot_disposition"),
        ("unknown", "unknown_disposition_pivot_id"),
        ("attempt", "unknown_disposition_attempt_id"),
    ],
)
def test_finish_pivot_accounting_is_exact_without_rewriting_dispositions(fault, expected):
    value = decision()
    if fault == "missing":
        value["dispositions"][0]["pivot_ids"].pop()
    elif fault == "duplicate":
        value["dispositions"][0]["pivot_ids"].append("P-key")
    elif fault == "unknown":
        value["dispositions"][0]["pivot_ids"].append("unknown")
    else:
        value["dispositions"][0]["attempt_ids"] = ["Q9"]
    before = deepcopy(value)
    assert expected in errors(value)
    assert value == before


def test_deferred_reasons_are_model_judgments_and_do_not_trigger_semantic_repair():
    value = decision()
    value["dispositions"][0]["disposition"] = "not_relevant"
    value["dispositions"][0]["reason"] = "The model judges these local filters irrelevant."
    assert errors(value) == []
    value["dispositions"][0]["reason"] = " \n"
    assert "blank_pivot_disposition_reason" in errors(value)


@pytest.mark.parametrize("where", ["decision", "ledger", "disposition", "query"])
def test_all_planning_schema_layers_forbid_extra_fields(where):
    value = decision("query_events", query={}) if where == "query" else decision()
    target = {
        "decision": value,
        "ledger": value["ledger"][0],
        "disposition": value["dispositions"][0] if value["dispositions"] else {},
        "query": value.get("query"),
    }[where]
    target["unexpected"] = "synthetic-extra"
    with pytest.raises(ValidationError):
        Decision.model_validate(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("ledger", [decision()["ledger"][0]] * 13),
        ("rationale", "x" * 1001),
        ("claim_id", "x" * 101),
        ("dispositions", decision()["dispositions"] * 21),
    ],
)
def test_decision_schema_enforces_frozen_list_and_text_bounds(field, value):
    assert errors(decision(**{field: value})) == ["invalid_decision_shape"]


def test_model_copy_cannot_bypass_nested_query_limits():
    value = Decision.model_validate(decision("query_events", query={}))
    altered = value.model_copy(update={"query": Query().model_copy(update={"limit": 1000})})
    assert errors(altered) == ["invalid_decision_shape"]
    with pytest.raises(ValueError):
        materialize_query(altered, catalog())


def test_error_codes_do_not_echo_log_values_or_model_prose():
    value = decision()
    value["ledger"][0]["evidence_refs"] = ["SYNTHETIC_SECRET_REF"]
    value["dispositions"][0]["reason"] = "MODEL_TEXT_NOT_AN_ERROR_MESSAGE"
    encoded = json.dumps(errors(value))
    assert "SYNTHETIC_SECRET_REF" not in encoded
    assert "MODEL_TEXT_NOT_AN_ERROR_MESSAGE" not in encoded


def test_duplicate_catalog_ids_do_not_choose_a_record_arbitrarily():
    coverage = catalog()
    coverage["candidates"].append({"id": "P-key", "query": {"access_key": "different"}})
    assert errors(decision(), coverage=coverage) == ["invalid_planning_catalog"]
    with pytest.raises(ValueError):
        materialize_query(decision("query_events", candidate_id="P-key"), coverage)
