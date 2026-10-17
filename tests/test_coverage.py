"""Observed-only inventory tests; no model, store searches, or inference results."""

import json
import socket
from copy import deepcopy
from hashlib import sha256

import pytest

from tracetrail.coverage import evidence_coverage
from tracetrail.store import CloudTrailStore, Query


def test_finish_accounting_ids_are_exactly_visible_candidates_and_pending_pages():
    result = evidence_coverage(
        [evidence()],
        [query({"access_key": "SYNTHETIC_CALLER_KEY"}, matched=12, truncated=True, next_offset=10)],
    )
    expected = [entry["id"] for entry in result["candidates"] + result["continuations"]]
    assert result["finish_accounting_ids"] == expected
    assert len(expected) == len(set(expected))
    assert result["continuations"]
    searched = next(c for c in result["candidates"] if c["searched"])
    assert searched["id"] in result["finish_accounting_ids"]
    compact = evidence_coverage(
        [{**evidence(), "ref": "E0"}],
        [query({"access_key": "SYNTHETIC_CALLER_KEY"}, matched=12, truncated=True, next_offset=10)],
    )
    assert compact["finish_accounting_ids"] == expected


@pytest.fixture(autouse=True)
def no_network_or_store_searches(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Coverage must not make network requests or evidence searches")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(CloudTrailStore, "query", forbidden)
    monkeypatch.setattr(CloudTrailStore, "get", forbidden)
    monkeypatch.setattr(CloudTrailStore, "load", forbidden)


def evidence(ref="synthetic-ref-1", **changes):
    record = {
        "eventID": "test-only-event",
        "eventSource": "sts.amazonaws.com",
        "userIdentity": {
            "type": "AssumedRole",
            "arn": "arn:aws:sts::000000000000:assumed-role/TestRole/test",
            "principalId": "SYNTHETIC_ROLE:test",
            "userName": "synthetic-user",
            "accessKeyId": "SYNTHETIC_CALLER_KEY",
            "sessionContext": {"sessionIssuer": {"arn": "arn:aws:iam::000000000000:role/TestRole"}},
        },
        "responseElements": {"credentials": {"accessKeyId": "SYNTHETIC_RETURNED_KEY"}},
        "requestParameters": {"roleArn": "arn:aws:iam::000000000000:role/NextRole"},
        "sourceIPAddress": "192.0.2.12",
    }
    record.update(changes)
    return {"ref": ref, "event_id": record["eventID"], "record": record}


def candidate(report, field, value):
    return next(item for item in report["candidates"] if item["query"] == {field: value})


def query(args, **changes):
    output = {"records": [], "matched": 0, "truncated": False, "next_offset": None}
    output.update(changes)
    return {"name": "query_events", "args": deepcopy(args), "result": output}


def test_inventory_derives_only_exact_observed_pivot_fields():
    report = evidence_coverage([evidence()], [])
    assert report["candidate_count"] == 9
    assert report["candidates_truncated"] is False
    caller = candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    returned = candidate(report, "access_key", "SYNTHETIC_RETURNED_KEY")
    reverse = candidate(report, "issued_access_key", "SYNTHETIC_CALLER_KEY")
    assert caller["sources"] == [
        {"citation": "synthetic-ref-1", "field": "userIdentity.accessKeyId"}
    ]
    assert returned["sources"] == [
        {"citation": "synthetic-ref-1", "field": "responseElements.credentials.accessKeyId"}
    ]
    assert reverse["sources"] == caller["sources"]
    assert all(
        item["attempts"] == [] and item["searched"] is False for item in report["candidates"]
    )
    assert report["continuations"] == []
    assert {next(iter(item["query"])) for item in report["candidates"][:3]} == {
        "access_key",
        "issued_access_key",
    }
    assert "complete" not in report and "covered" not in report


def test_unknown_fields_secrets_and_gold_labels_never_become_candidates():
    item = evidence(
        eventSource="NEVER_AN_ISSUER",
        hiddenRecord={"userIdentity": {"accessKeyId": "HIDDEN_KEY"}},
        relevant_event_ids=["GOLD_EVENT_ID"],
        expected_status="GOLD_ANSWER",
    )
    item["record"]["responseElements"]["credentials"].update(
        secretAccessKey="PRIVATE_SECRET", sessionToken="PRIVATE_TOKEN"
    )
    item["record"]["responseElements"]["accessKey"] = {"accessKeyId": "UNSUPPORTED_ISSUANCE_PATH"}
    item["annotations"] = [{"claim_id": "HIDDEN_LABEL"}]
    report = evidence_coverage([item], [])
    encoded = json.dumps(report)
    for marker in (
        "NEVER_AN_ISSUER",
        "HIDDEN_KEY",
        "GOLD_EVENT_ID",
        "GOLD_ANSWER",
        "PRIVATE_SECRET",
        "PRIVATE_TOKEN",
        "UNSUPPORTED_ISSUANCE_PATH",
        "HIDDEN_LABEL",
    ):
        assert marker not in encoded
    assert candidate(report, "session_issuer", "arn:aws:iam::000000000000:role/NextRole")[
        "sources"
    ] == [{"citation": "synthetic-ref-1", "field": "requestParameters.roleArn"}]


def test_history_records_do_not_expand_inventory_without_observed_evidence():
    hidden = evidence("hidden-ref", sourceIPAddress="198.51.100.200")
    history = [query({}, records=[hidden], matched=1)]
    report = evidence_coverage([evidence()], history)
    assert all(item["query"] != {"source_ip": "198.51.100.200"} for item in report["candidates"])
    assert "hidden-ref" not in json.dumps(report)


@pytest.mark.parametrize("identity_type", ["IAMUser", None, "assumedrole"])
def test_reverse_issuance_search_is_offered_only_for_observed_assumed_role(identity_type):
    item = evidence()
    item["record"]["userIdentity"]["type"] = identity_type
    report = evidence_coverage([item], [])
    assert candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    assert all("issued_access_key" not in item["query"] for item in report["candidates"])


def test_successful_narrowed_query_preserves_all_scope_filters():
    scope = {
        "access_key": "SYNTHETIC_CALLER_KEY",
        "principal": "synthetic-user",
        "event_name": "StopLogging",
        "start_time": "2026-01-01T10:00:00Z",
        "end_time": "2026-01-01T10:01:00Z",
        "limit": 2,
        "offset": 7,
    }
    report = evidence_coverage([evidence()], [query(scope)])
    item = candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    assert item["searched"] is True
    assert item["attempts"] == [
        {
            "attempt_id": "Q0",
            "tool_index": 0,
            "args": scope,
            "successful": True,
            "matched": 0,
            "truncated": False,
            "error": None,
            "next_offset": None,
        }
    ]
    assert item["has_successful_scoped_attempt"] is True
    assert item["has_successful_unbounded_first_page"] is False
    assert candidate(report, "principal", "synthetic-user")["searched"] is True
    assert candidate(report, "issued_access_key", "SYNTHETIC_CALLER_KEY")["searched"] is False
    assert report["continuations"] == []


def test_get_event_does_not_count_as_searching_related_activity():
    item = evidence()
    history = [{"name": "get_event", "args": {"identifier": item["ref"]}, "result": item}]
    report = evidence_coverage([item], history)
    assert all(not item["searched"] and not item["attempts"] for item in report["candidates"])


def test_failed_matching_query_preserves_error_without_marking_searched():
    scope = {"access_key": "SYNTHETIC_CALLER_KEY", "limit": 20}
    error = {"code": "tool_exception", "type": "RuntimeError"}
    history = [{"name": "query_events", "args": scope, "result": {"error": error}}]
    report = evidence_coverage([evidence()], history)
    item = candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    assert item["searched"] is False
    assert item["attempts"][0]["error"] == error
    assert item["attempts"][0]["args"] == scope
    assert item["attempts"][0]["matched"] is None
    assert report["continuations"] == []


def test_error_after_success_does_not_erase_prior_successful_attempt():
    args = {"source_ip": "192.0.2.12"}
    history = [
        query(args),
        {"name": "query_events", "args": args, "result": {"error": {"code": "x"}}},
    ]
    item = candidate(evidence_coverage([evidence()], history), "source_ip", "192.0.2.12")
    assert item["searched"] is True
    assert len(item["attempts"]) == 2
    assert item["attempts"][1]["error"] == {"code": "x"}


@pytest.mark.parametrize(
    "output",
    [
        {},
        {"error": None},
        {"matched": True, "truncated": False, "records": []},
        {"matched": 0, "truncated": None, "records": []},
        {"matched": 0, "truncated": False},
        {"matched": -1, "truncated": False, "records": []},
    ],
)
def test_malformed_results_do_not_mark_candidate_searched(output):
    history = [{"name": "query_events", "args": {"source_ip": "192.0.2.12"}, "result": output}]
    item = candidate(evidence_coverage([evidence()], history), "source_ip", "192.0.2.12")
    assert item["searched"] is False
    assert len(item["attempts"]) == 1


def test_raw_and_compact_tool_results_have_identical_inventory_status():
    args = {"access_key": "SYNTHETIC_CALLER_KEY", "limit": 1}
    raw = query(args, records=[evidence()], matched=3, truncated=True, next_offset=1)
    compact = deepcopy(raw)
    compact["result"].pop("records")
    compact["result"]["returned_citations"] = ["E0"]
    assert evidence_coverage([evidence()], [raw]) == evidence_coverage([evidence()], [compact])


def test_continuation_keeps_actual_query_scope_and_observed_next_offset():
    args = {
        "principal": "synthetic-user",
        "event_name": "GetObject",
        "limit": 2,
        "offset": 4,
        "start_time": "2026-01-01T10:00:00Z",
    }
    history = [query(args, matched=12, truncated=True, next_offset=6)]
    report = evidence_coverage([evidence()], history)
    continuation = report["continuations"][0]
    assert continuation == {
        "id": continuation["id"],
        "attempt_id": "Q0",
        "tool_index": 0,
        "original_args": args,
        "next_offset": 6,
        "query": {**args, "offset": 6},
    }
    assert continuation["id"].startswith("C")
    item = candidate(report, "principal", "synthetic-user")
    assert item["searched"] is True
    assert item["attempts"][0]["truncated"] is True
    assert item["attempts"][0]["next_offset"] == 6


@pytest.mark.parametrize("next_offset", [None, False, True, "2", 0, -1])
def test_null_or_invalid_pagination_never_invents_a_continuation(next_offset):
    args = {"access_key": "SYNTHETIC_CALLER_KEY", "offset": 0}
    report = evidence_coverage(
        [evidence()], [query(args, matched=3, truncated=True, next_offset=next_offset)]
    )
    assert report["continuations"] == []
    item = candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    assert item["attempts"][0]["truncated"] is True
    assert item["attempts"][0]["next_offset"] == next_offset


def test_completed_page_and_failed_query_never_get_continuation_suggestions():
    args = {"source_ip": "192.0.2.12"}
    history = [
        query(args, next_offset=2),
        query(args, matched=4, truncated=True, next_offset=2, error={"code": "x"}),
    ]
    assert evidence_coverage([evidence()], history)["continuations"] == []


def test_candidate_order_ids_and_sources_are_deterministic_and_deduplicated():
    first = evidence("ref-a")
    second = evidence("ref-b")
    before = evidence_coverage([first, second, first], [])
    after = evidence_coverage([second, first], [])
    assert before == after
    item = candidate(before, "access_key", "SYNTHETIC_CALLER_KEY")
    assert item["sources"] == [
        {"citation": "ref-a", "field": "userIdentity.accessKeyId"},
        {"citation": "ref-b", "field": "userIdentity.accessKeyId"},
    ]
    extra = evidence("ref-c", sourceIPAddress="192.0.2.99")
    expanded = evidence_coverage([extra, second, first], [])
    assert candidate(expanded, "access_key", "SYNTHETIC_CALLER_KEY")["id"] == item["id"]
    assert len({item["id"] for item in before["candidates"]}) == before["candidate_count"]


def test_inventory_limit_prioritizes_observed_keys_and_reports_truncation():
    items = [
        evidence(f"ref-{i}", userIdentity={"accessKeyId": f"SYNTHETIC_KEY_{i:02d}"})
        for i in range(20)
    ]
    report = evidence_coverage(items, [])
    assert len(report["candidates"]) == report["candidate_limit"] == 16
    assert report["candidate_count"] > 16
    assert report["candidates_truncated"] is True
    assert all(next(iter(item["query"])) == "access_key" for item in report["candidates"])


def test_non_string_null_nested_and_unqueryable_values_are_ignored():
    item = evidence(
        userIdentity={"accessKeyId": None, "arn": {}, "principalId": False, "userName": " "},
        responseElements={"credentials": {"accessKeyId": ["NESTED_KEY"]}},
        requestParameters={"roleArn": "a" * 2049},
        sourceIPAddress=42,
    )
    report = evidence_coverage([item, {"record": {}}, {"ref": "x", "record": None}], [])
    assert report["candidates"] == []
    assert report["candidate_count"] == 0


def test_inventory_and_scopes_are_independent_copies():
    item = evidence()
    history = [
        query({"access_key": "SYNTHETIC_CALLER_KEY"}, matched=5, truncated=True, next_offset=2)
    ]
    original_item, original_history = deepcopy(item), deepcopy(history)
    report = evidence_coverage([item], history)
    found = candidate(report, "access_key", "SYNTHETIC_CALLER_KEY")
    found["sources"][0]["citation"] = "changed"
    found["attempts"][0]["args"]["access_key"] = "changed"
    report["continuations"][0]["query"]["access_key"] = "changed"
    report["continuations"][0]["original_args"]["access_key"] = "changed-origin"
    assert item == original_item
    assert history == original_history


def test_catalog_explains_supported_filters_without_changing_stable_pivot_ids():
    report = evidence_coverage([evidence()], [])
    kinds = {
        "access_key": "credential_use",
        "issued_access_key": "credential_issuance",
        "principal": "principal_activity",
        "session_issuer": "role_session_activity",
        "source_ip": "source_activity",
    }
    for item in report["candidates"]:
        field = next(iter(item["query"]))
        expected_id = (
            "P"
            + sha256(
                json.dumps(item["query"], sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()[:12]
        )
        assert item["id"] == expected_id
        assert item["kind"] == kinds[field]
        assert item["local_query_supported"] is True
        assert item["filter_meaning"]
        assert item["has_successful_scoped_attempt"] is False
        assert item["has_successful_unbounded_first_page"] is False
    uses = candidate(report, "access_key", "SYNTHETIC_RETURNED_KEY")
    assert "userIdentity.accessKeyId" in uses["filter_meaning"]
    issuer = candidate(report, "issued_access_key", "SYNTHETIC_CALLER_KEY")
    assert "responseElements.credentials.accessKeyId" in issuer["filter_meaning"]


def test_attempt_ids_refer_to_actual_history_indices_including_failures_and_gets():
    history = [
        {"name": "get_event", "args": {"identifier": "x"}, "result": evidence()},
        query({"access_key": "UNRELATED_KEY"}),
        query({"access_key": "SYNTHETIC_CALLER_KEY"}, error={"code": "failed"}),
        query({"access_key": "SYNTHETIC_CALLER_KEY", "event_name": "StopLogging"}),
    ]
    item = candidate(evidence_coverage([evidence()], history), "access_key", "SYNTHETIC_CALLER_KEY")
    assert [a["attempt_id"] for a in item["attempts"]] == ["Q2", "Q3"]
    assert [a["successful"] for a in item["attempts"]] == [False, True]
    assert item["searched"] is item["has_successful_scoped_attempt"] is True
    assert item["has_successful_unbounded_first_page"] is False


@pytest.mark.parametrize(
    "scope",
    [
        {"start_time": "2026-01-01T10:00:00Z"},
        {"end_time": "2026-01-01T11:00:00Z"},
        {"event_name": "GetObject"},
        {"source_ip": "192.0.2.12"},
        {"offset": 1},
    ],
)
def test_time_and_additional_filters_or_later_pages_are_not_unbounded_first_page(scope):
    history = [query({"access_key": "SYNTHETIC_CALLER_KEY", **scope})]
    item = candidate(evidence_coverage([evidence()], history), "access_key", "SYNTHETIC_CALLER_KEY")
    assert item["has_successful_scoped_attempt"] is True
    assert item["has_successful_unbounded_first_page"] is False


def test_unbounded_first_page_can_still_be_truncated_and_uses_query_defaults():
    args = Query(access_key="SYNTHETIC_CALLER_KEY", limit=1).model_dump(mode="json")
    item = candidate(
        evidence_coverage([evidence()], [query(args, matched=2, truncated=True, next_offset=1)]),
        "access_key",
        "SYNTHETIC_CALLER_KEY",
    )
    assert item["has_successful_unbounded_first_page"] is True
    assert item["attempts"][0]["truncated"] is True
    assert "complete" not in item and "covered" not in item


def test_executed_continuation_is_suppressed_with_null_defaults_and_equivalent_utc_bounds():
    args = {
        "access_key": "SYNTHETIC_CALLER_KEY",
        "start_time": "2026-01-01T12:00:00+02:00",
        "limit": 2,
    }
    first = query(args, matched=6, truncated=True, next_offset=2)
    following_args = Query(**args, offset=2).model_dump(mode="json")
    following = query(following_args, matched=6, truncated=True, next_offset=4)
    report = evidence_coverage([evidence()], [first, following])
    assert len(report["continuations"]) == 1
    pending = report["continuations"][0]
    assert pending["attempt_id"] == "Q1"
    assert pending["original_args"] == following_args
    assert pending["query"] == {**following_args, "offset": 4}


def test_continuation_ids_are_stable_across_default_null_serialization_and_history_indices():
    sparse = {"access_key": "SYNTHETIC_CALLER_KEY"}
    full = Query(**sparse).model_dump(mode="json")
    first = evidence_coverage(
        [evidence()], [query(sparse, matched=12, truncated=True, next_offset=10)]
    )
    other = evidence_coverage(
        [evidence()],
        [
            {"name": "get_event", "args": {}, "result": {}},
            query(full, matched=12, truncated=True, next_offset=10),
        ],
    )
    a, b = first["continuations"][0], other["continuations"][0]
    assert a["id"] == b["id"]
    assert a["attempt_id"] == "Q0" and b["attempt_id"] == "Q1"
    assert a["original_args"] == sparse and b["original_args"] == full


@pytest.mark.parametrize(
    "difference",
    [
        {"limit": 1},
        {"event_name": "GetObject"},
        {"start_time": "2026-01-01T10:00:00Z"},
        {"end_time": "2026-01-01T11:00:00Z"},
        {"offset": 3},
    ],
)
def test_other_successful_scopes_do_not_suppress_a_pending_continuation(difference):
    args = {"access_key": "SYNTHETIC_CALLER_KEY", "limit": 2}
    history = [
        query(args, matched=4, truncated=True, next_offset=2),
        query({**args, "offset": 2, **difference}),
    ]
    pending = evidence_coverage([evidence()], history)["continuations"]
    assert len(pending) == 1
    assert pending[0]["query"] == {**args, "offset": 2}


def test_failed_continuation_remains_pending_and_duplicate_origins_are_deduplicated():
    args = {"access_key": "SYNTHETIC_CALLER_KEY", "limit": 2}
    history = [
        query(args, matched=4, truncated=True, next_offset=2),
        query(Query(**args).model_dump(mode="json"), matched=4, truncated=True, next_offset=2),
        query({**args, "offset": 2}, error={"code": "failure"}),
    ]
    pending = evidence_coverage([evidence()], history)["continuations"]
    assert len(pending) == 1
    assert pending[0]["attempt_id"] == "Q0"
    assert pending[0]["original_args"] == args


@pytest.mark.parametrize("bad_scope", [{"limit": True}, {"offset": None}, {"unknown": "x"}])
def test_invalid_query_scopes_are_preserved_as_attempts_but_cannot_claim_success(bad_scope):
    args = {"access_key": "SYNTHETIC_CALLER_KEY", **bad_scope}
    item = candidate(
        evidence_coverage([evidence()], [query(args, matched=4, truncated=True, next_offset=2)]),
        "access_key",
        "SYNTHETIC_CALLER_KEY",
    )
    assert item["attempts"][0]["attempt_id"] == "Q0"
    assert item["attempts"][0]["args"] == args
    assert item["attempts"][0]["successful"] is False
    assert item["has_successful_scoped_attempt"] is item["searched"] is False
