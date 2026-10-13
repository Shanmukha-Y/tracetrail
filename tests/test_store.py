"""Evidence integrity, query limits, and explicit tool failures."""

import hashlib
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from tracetrail.store import CloudTrailStore, Query, StoreError


def event(event_id="event-1", **changes):
    record = {
        "eventID": event_id,
        "eventName": "CreateAccessKey",
        "eventSource": "iam.amazonaws.com",
        "eventTime": "2026-01-01T10:00:00Z",
        "sourceIPAddress": "192.0.2.4",
        "userIdentity": {
            "arn": "arn:aws:sts::123456789012:assumed-role/AuditRole/test",
            "principalId": "ROLEID:test",
            "userName": "tester",
            "accessKeyId": "ASIA_SYNTHETIC_TEST",
            "sessionContext": {
                "sessionIssuer": {"arn": "arn:aws:iam::123456789012:role/AuditRole"}
            },
        },
        "requestParameters": {"userName": "synthetic-user", "nested": [1, {"value": "exact"}]},
    }
    record.update(changes)
    return record


def write_log(tmp_path, records, name="trail.json"):
    path = tmp_path / name
    path.write_text(json.dumps({"Records": records}, indent=2), encoding="utf-8")
    return path


def test_citations_resolve_to_exact_original_record_and_are_stable(tmp_path):
    original = event()
    path = write_log(tmp_path, [original])
    expected_ref = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}/Records/0"
    store = CloudTrailStore.load(path)
    assert store.get("event-1") == {"ref": expected_ref, "event_id": "event-1", "record": original}
    assert store.get(expected_ref) == store.get("event-1")
    assert CloudTrailStore.load(path).get("event-1")["ref"] == expected_ref
    modified = store.get("event-1")
    modified["record"]["requestParameters"]["nested"][1]["value"] = "modified"
    visible_records = store.records
    visible_records.clear()
    assert store.get(expected_ref)["record"] == original


def test_file_content_change_changes_citation(tmp_path):
    path = write_log(tmp_path, [event()])
    old_ref = CloudTrailStore.load(path).get("event-1")["ref"]
    path.write_text(path.read_text() + "\n")
    new_ref = CloudTrailStore.load(path).get("event-1")["ref"]
    assert new_ref != old_ref


def test_directory_load_order_is_deterministic_and_query_is_chronological(tmp_path):
    write_log(tmp_path, [event("later", eventTime="2026-01-01T11:00:00Z")], "a.json")
    write_log(tmp_path, [event("earlier", eventTime="2026-01-01T09:00:00Z")], "b.json")
    (tmp_path / "ignored.txt").write_text("not a log")
    store = CloudTrailStore.load(tmp_path)
    assert [item["event_id"] for item in store.records] == ["later", "earlier"]
    assert [item["event_id"] for item in store.query(Query())["records"]] == ["earlier", "later"]


@pytest.mark.parametrize(
    "principal", ["arn:aws:sts::123456789012:assumed-role/AuditRole/test", "ROLEID:test", "tester"]
)
def test_principal_pivots_match_each_exact_identity_field(tmp_path, principal):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))
    assert store.query(Query(principal=principal))["matched"] == 1
    assert store.query(Query(principal=principal.lower()))["matched"] == (
        1 if principal == principal.lower() else 0
    )
    assert store.query(Query(principal="AuditRole"))["matched"] == 0


def test_all_filters_are_combined_and_timezone_bounds_are_inclusive(tmp_path):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))
    query = Query(
        principal="tester",
        source_ip="192.0.2.4",
        event_name="CreateAccessKey",
        access_key="ASIA_SYNTHETIC_TEST",
        session_issuer="arn:aws:iam::123456789012:role/AuditRole",
        start_time="2026-01-01T05:00:00-05:00",
        end_time="2026-01-01T10:00:00Z",
    )
    assert store.query(query)["matched"] == 1
    assert store.query(query.model_copy(update={"source_ip": "192.0.2.5"}))["matched"] == 0
    assert store.query(Query(start_time="2026-01-01T10:00:01Z"))["matched"] == 0


def test_query_reports_total_count_and_truncation(tmp_path):
    records = [event(f"event-{index}") for index in range(25)]
    store = CloudTrailStore.load(write_log(tmp_path, records))
    output = store.query(Query(event_name="CreateAccessKey", limit=20))
    assert len(output["records"]) == 20
    assert output["matched"] == 25
    assert output["truncated"] is True
    assert store.query(Query(source_ip="192.0.2.250")) == {
        "records": [],
        "matched": 0,
        "truncated": False,
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0},
        {"limit": 21},
        {"limit": True},
        {"limit": "10"},
        {"principal": ""},
        {"source_ip": " "},
        {"principal": "a" * 2049},
        {"start_time": "2026-01-01T10:00:00"},
        {"start_time": 1700000000},
        {"start_time": "2026-01-02T10:00:00Z", "end_time": "2026-01-01T10:00:00Z"},
        {"sql": "SELECT * FROM events"},
    ],
)
def test_query_rejects_invalid_bounds_and_unknown_fields(kwargs):
    with pytest.raises(ValidationError):
        Query(**kwargs)


def test_copied_query_cannot_bypass_limit_validation(tmp_path):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))
    invalid_query = Query().model_copy(update={"limit": 1000})
    with pytest.raises(StoreError) as caught:
        store.query(invalid_query)
    assert caught.value.code == "invalid_query"


def test_event_id_cannot_shadow_an_existing_citation(tmp_path):
    path = write_log(tmp_path, [event("first")], "one.json")
    citation = CloudTrailStore.load(path).get("first")["ref"]
    write_log(tmp_path, [event(citation)], "two.json")
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path)
    assert caught.value.code == "ambiguous_identifier"


def test_duplicate_event_ids_fail_instead_of_resolving_ambiguously(tmp_path):
    write_log(tmp_path, [event()], "one.json")
    write_log(tmp_path, [event(eventName="DeleteTrail")], "two.json")
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path)
    assert caught.value.code == "duplicate_event_id"


@pytest.mark.parametrize(
    "document",
    [
        [],
        {},
        {"Records": {}},
        {"Records": [None]},
        {"Records": [event(eventID="")]},
        {"Records": [event(eventName=5)]},
        {"Records": [event(eventTime="2026-01-01")]},
        {"Records": [event(userIdentity=[])]},
        {"Records": [event(userIdentity={"sessionContext": {"sessionIssuer": []}})]},
    ],
)
def test_malformed_cloudtrail_is_rejected(tmp_path, document):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(document))
    with pytest.raises(StoreError):
        CloudTrailStore.load(path)


@pytest.mark.parametrize(
    "content", ["{", '{"Records": [], "Records": []}', '{"Records": [], "bad": NaN}']
)
def test_invalid_json_is_rejected(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content)
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(path)
    assert caught.value.code == "invalid_json"


def test_ingestion_budgets_are_enforced(tmp_path):
    path = write_log(tmp_path, [event("one"), event("two")])
    for limits, code in [
        ({"max_bytes": 1}, "byte_budget_exceeded"),
        ({"max_events": 1}, "event_budget_exceeded"),
        ({"max_record_bytes": 1}, "record_budget_exceeded"),
        ({"max_bytes": 0}, "invalid_budget"),
    ]:
        with pytest.raises(StoreError) as caught:
            CloudTrailStore.load(path, **limits)
        assert caught.value.code == code


def test_total_directory_byte_budget_and_symlink_rejection(tmp_path):
    path = write_log(tmp_path, [event("one")], "one.json")
    write_log(tmp_path, [event("two")], "two.json")
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path, max_bytes=len(path.read_bytes()))
    assert caught.value.code == "byte_budget_exceeded"
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(link)
    assert caught.value.code == "invalid_path"


def test_missing_input_and_empty_directory_are_explicit(tmp_path):
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path / "missing.json")
    assert caught.value.code == "invalid_path"
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path)
    assert caught.value.code == "empty_input"


def test_tools_expose_real_store_and_structured_failures(tmp_path):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))
    tools = {tool.name: tool for tool in store.tools()}
    output = tools["query_events"].invoke({"principal": "tester", "limit": 1})
    assert output["matched"] == 1
    assert (
        tools["get_event"].invoke({"identifier": output["records"][0]["ref"]})["record"] == event()
    )
    missing = tools["get_event"].invoke({"identifier": "absent"})
    assert missing["error"]["code"] == "event_not_found"
    invalid = json.loads(tools["query_events"].invoke({"limit": 99}))
    assert invalid["error"]["code"] == "invalid_tool_input"
    assert "records" not in invalid
    unknown = json.loads(tools["query_events"].invoke({"sql": "private input"}))
    assert unknown["error"]["code"] == "invalid_tool_input"
    assert "private input" not in json.dumps(unknown)
    with pytest.raises(StoreError) as caught:
        store.get("absent")
    assert caught.value.code == "event_not_found"


def test_query_outputs_cannot_mutate_store(tmp_path):
    original = event()
    store = CloudTrailStore.load(write_log(tmp_path, [original]))
    result = store.query(Query())
    result["records"][0]["record"]["userIdentity"].clear()
    assert store.get("event-1")["record"] == deepcopy(original)
