"""Observed credential context only; no model or store capability evidence."""

import json
import socket
from copy import deepcopy

import pytest

from tracetrail.coverage import evidence_coverage
from tracetrail.credential_map import credential_map
from tracetrail.store import CloudTrailStore


@pytest.fixture(autouse=True)
def no_network_or_store_searches(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Credential context must not search or call a network service")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    for name in ("query", "get", "load"):
        monkeypatch.setattr(CloudTrailStore, name, forbidden)


def evidence(ref="record-1", caller="CALLER", returned="CHILD", identity_type="AssumedRole"):
    return {
        "ref": ref,
        "record": {
            "userIdentity": {"accessKeyId": caller, "type": identity_type},
            "responseElements": {"credentials": {"accessKeyId": returned}},
        },
    }


def query(args, **changes):
    result = {"records": [], "matched": 0, "truncated": False, "next_offset": None}
    result.update(changes)
    return {"name": "query_events", "args": deepcopy(args), "result": result}


def row(report, key):
    return next(item for item in report["keys"] if item["key"] == key)


def test_signer_returned_direction_and_same_record_connection_are_exact():
    items = [evidence(), evidence("record-2", caller="CHILD", returned=None)]
    coverage = evidence_coverage(items, [])
    result = credential_map(items, coverage)
    caller, child = row(result, "CALLER"), row(result, "CHILD")
    assert caller["returned_occurrences"] == []
    assert child["returned_occurrences"] == [
        {
            "citation": "record-1",
            "field": "responseElements.credentials.accessKeyId",
            "recorded_caller": {
                "key": "CALLER",
                "citation": "record-1",
                "field": "userIdentity.accessKeyId",
            },
        }
    ]
    assert child["signer_occurrences"][0]["citation"] == "record-2"
    assert child["lookups"]["use"]["query"] == {"access_key": "CHILD"}
    assert child["lookups"]["issuance"]["query"] == {"issued_access_key": "CHILD"}
    assert result["occurrence_count"] == result["included_occurrence_count"] == 3
    assert result["omitted_occurrence_count"] == 0


def test_no_event_name_identity_or_key_prefix_changes_direction():
    items = [evidence(caller="ASIA_LITERAL", returned="AKIA_LITERAL", identity_type="IAMUser")]
    items[0]["record"]["eventName"] = "UnrelatedLiteral"
    result = credential_map(items, evidence_coverage(items, []))
    caller = row(result, "ASIA_LITERAL")
    assert caller["signer_occurrences"][0]["user_identity_type"] == {
        "field": "userIdentity.type",
        "present": True,
        "value": "IAMUser",
    }
    assert caller["lookups"]["issuance"]["candidate_visible"] is False
    assert caller["lookups"]["issuance"]["candidate_id"] is None
    assert caller["lookups"]["issuance"]["query"] is None
    assert "temporary" not in json.dumps(result)
    assert "UnrelatedLiteral" not in json.dumps(result)


@pytest.mark.parametrize("identity_type", [None, "", "assumedrole", 7, False, {"literal": "type"}])
def test_identity_type_is_literal_and_not_inferred(identity_type):
    items = [evidence(returned=None, identity_type=identity_type)]
    result = credential_map(items, evidence_coverage(items, []))
    observed = row(result, "CALLER")["signer_occurrences"][0]["user_identity_type"]
    assert observed == {"field": "userIdentity.type", "present": True, "value": identity_type}
    assert type(observed["value"]) is type(identity_type)


def test_absent_type_differs_from_explicit_null_and_return_without_caller():
    item = evidence(returned=None)
    del item["record"]["userIdentity"]["type"]
    no_caller = evidence("record-2", caller=None, returned="ORPHAN")
    result = credential_map([item, no_caller], evidence_coverage([item, no_caller], []))
    assert row(result, "CALLER")["signer_occurrences"][0]["user_identity_type"] == {
        "field": "userIdentity.type",
        "present": False,
        "value": None,
    }
    assert row(result, "ORPHAN")["returned_occurrences"][0]["recorded_caller"] is None


def test_source_fields_only_no_secrets_gold_or_coverage_only_keys():
    item = evidence()
    item["record"].update(
        eventName="UNRELATED_EVENT",
        expected_status="GOLD_STATUS",
        hidden={"userIdentity": {"accessKeyId": "HIDDEN_KEY"}},
    )
    item["record"]["responseElements"]["credentials"].update(
        secretAccessKey="SECRET_VALUE", sessionToken="TOKEN_VALUE"
    )
    item["annotations"] = ["PRIVATE_ANNOTATION"]
    coverage = evidence_coverage([item, evidence("not-returned", "COVERAGE_ONLY", None)], [])
    result = json.dumps(credential_map([item], coverage))
    for marker in (
        "UNRELATED_EVENT",
        "GOLD_STATUS",
        "HIDDEN_KEY",
        "SECRET_VALUE",
        "TOKEN_VALUE",
        "PRIVATE_ANNOTATION",
        "COVERAGE_ONLY",
        "not-returned",
    ):
        assert marker not in result


def test_actual_attempt_ids_errors_and_full_and_time_page_scopes_are_preserved():
    items = [evidence()]
    issuance = {"issued_access_key": "CALLER", "limit": 20}
    use_scope = {
        "access_key": "CALLER",
        "source_ip": "192.0.2.20",
        "start_time": "2026-01-01T00:00:00Z",
        "end_time": "2026-01-01T00:01:00Z",
        "offset": 7,
        "limit": 2,
    }
    history = [
        {"name": "get_event", "args": {"identifier": "record-1"}, "result": items[0]},
        query(issuance),
        {"name": "query_events", "args": use_scope, "result": {"error": {"code": "test"}}},
    ]
    coverage = evidence_coverage(items, history)
    caller = row(credential_map(items, coverage), "CALLER")
    use, issued = caller["lookups"]["use"], caller["lookups"]["issuance"]
    assert issued["attempts"][0]["attempt_id"] == "Q1"
    assert issued["attempts"][0]["args"] == issuance
    assert use["attempts"][0]["attempt_id"] == "Q2"
    assert use["attempts"][0]["args"] == use_scope
    assert use["attempts"][0]["successful"] is False
    assert use["attempts"][0]["error"] == {"code": "test"}
    assert all(
        a["attempt_id"] != "Q0" for entry in caller["lookups"].values() for a in entry["attempts"]
    )


def test_issuance_attempt_does_not_become_a_use_attempt():
    items = [evidence()]
    coverage = evidence_coverage(items, [query({"issued_access_key": "CALLER"})])
    caller = row(credential_map(items, coverage), "CALLER")
    assert caller["lookups"]["issuance"]["attempts"][0]["successful"] is True
    assert caller["lookups"]["use"]["attempts"] == []
    assert caller["lookups"]["use"]["candidate_visible"] is True


def test_pending_continuations_keep_origin_scope_and_are_not_attempts():
    items = [evidence()]
    scope = {"access_key": "CALLER", "source_ip": "192.0.2.21", "limit": 2}
    history = [query(scope, matched=8, truncated=True, next_offset=2)]
    coverage = evidence_coverage(items, history)
    caller = row(credential_map(items, coverage), "CALLER")
    use, issuance = caller["lookups"]["use"], caller["lookups"]["issuance"]
    assert use["pending_continuations"] == coverage["continuations"]
    pending = use["pending_continuations"][0]
    assert pending["attempt_id"] == "Q0"
    assert pending["original_args"] == scope
    assert pending["query"] == {**scope, "offset": 2}
    assert len(use["attempts"]) == 1
    assert issuance["pending_continuations"] == []
    completed = evidence_coverage(items, [*history, query(pending["query"])])
    assert (
        row(credential_map(items, completed), "CALLER")["lookups"]["use"]["pending_continuations"]
        == []
    )


def test_pending_scope_can_exist_when_candidate_is_not_visible():
    items = [evidence()]
    coverage = evidence_coverage(
        items,
        [query({"access_key": "CHILD", "limit": 2}, matched=4, truncated=True, next_offset=2)],
    )
    coverage["candidates"] = []
    use = row(credential_map(items, coverage), "CHILD")["lookups"]["use"]
    assert use["candidate_visible"] is False
    assert use["attempts"] == []
    assert use["pending_continuations"] == coverage["continuations"]


def test_key_and_combined_occurrence_caps_disclose_total_omissions():
    items = [evidence(f"r-{i:02}", f"KEY-{i:02}", None) for i in range(18)]
    items.extend(evidence(f"repeat-{i:02}", "KEY-00", "KEY-00") for i in range(10))
    coverage = evidence_coverage(items, [])
    result = credential_map(list(reversed(items)), coverage)
    assert [item["key"] for item in result["keys"]] == [f"KEY-{i:02}" for i in range(16)]
    assert result["key_count"] == 18 and result["key_limit"] == 16
    assert result["keys_truncated"] is True and result["omitted_key_count"] == 2
    first = row(result, "KEY-00")
    assert first["occurrence_count"] == 21
    assert len(first["signer_occurrences"]) + len(first["returned_occurrences"]) == 16
    assert first["omitted_occurrence_count"] == 5
    assert result["occurrence_count"] == 38
    assert result["included_occurrence_count"] == 31
    assert result["omitted_occurrence_count"] == 7
    assert result == credential_map(items, coverage)


def test_attempt_and_continuation_caps_disclose_omissions():
    items = [evidence(returned=None)]
    history = [
        query(
            {"access_key": "CALLER", "offset": i * 2, "limit": 1},
            matched=99,
            truncated=True,
            next_offset=i * 2 + 1,
        )
        for i in range(18)
    ]
    coverage = evidence_coverage(items, history)
    use = row(credential_map(items, coverage), "CALLER")["lookups"]["use"]
    assert use["attempt_count"] == use["pending_continuation_count"] == 18
    assert len(use["attempts"]) == len(use["pending_continuations"]) == 16
    assert use["omitted_attempt_count"] == use["omitted_pending_continuation_count"] == 2
    assert [a["tool_index"] for a in use["attempts"]] == list(range(16))


def test_same_record_key_occurrences_are_unique_and_input_is_not_mutated():
    items = [evidence(identity_type={"literal": ["role"]})]
    coverage = evidence_coverage(items, [query({"access_key": "CALLER"})])
    original = deepcopy((items, coverage))
    result = credential_map([*items, deepcopy(items[0])], coverage)
    assert result["occurrence_count"] == 2
    assert (items, coverage) == original
    row(result, "CALLER")["signer_occurrences"][0]["user_identity_type"]["value"]["literal"].append(
        "changed"
    )
    row(result, "CALLER")["lookups"]["use"]["attempts"][0]["args"]["access_key"] = "changed"
    assert (items, coverage) == original


def test_raw_and_compact_citations_share_pids_without_leaking_raw_refs():
    raw = [evidence("sha256:synthetic/Records/0")]
    compact = [evidence("E0")]
    raw_map = credential_map(raw, evidence_coverage(raw, []))
    compact_map = credential_map(compact, evidence_coverage(compact, []))

    def aliases(value):
        if isinstance(value, list):
            return [aliases(item) for item in value]
        if isinstance(value, dict):
            return {
                key: "E0" if key == "citation" else aliases(item) for key, item in value.items()
            }
        return value

    assert aliases(raw_map) == compact_map
    assert "sha256:synthetic" not in json.dumps(compact_map)


@pytest.mark.parametrize("key", [None, 5, False, {}, [], "", "   ", "X" * 2049])
def test_invalid_key_values_are_ignored_without_becoming_queries(key):
    items = [evidence(caller=key, returned=key)]
    result = credential_map(items, evidence_coverage(items, []))
    assert result["keys"] == [] and result["occurrence_count"] == 0


def test_conflicting_citation_is_rejected_and_malformed_evidence_is_ignored():
    with pytest.raises(ValueError, match="one exact record"):
        credential_map([evidence(), evidence(caller="OTHER")], {})
    assert credential_map([None, {}, {"ref": "r", "record": None}], {})["keys"] == []
