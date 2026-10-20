"""Evidence integrity, query limits, and explicit tool failures."""

import hashlib
import json

import pytest

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


@pytest.mark.parametrize("update", [{"limit": 1000}])
def test_copied_query_cannot_bypass_limit_validation(tmp_path, update):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))
    invalid_query = Query().model_copy(update=update)
    with pytest.raises(StoreError) as caught:
        store.query(invalid_query)
    assert caught.value.code == "invalid_query"


def test_file_byte_budget_rejects_oversized_input(tmp_path):
    path = write_log(tmp_path, [event()])
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(path, max_bytes=1)
    assert caught.value.code == "byte_budget_exceeded"


def test_query_tool_rejects_unknown_input_before_store_execution(tmp_path, monkeypatch):
    store = CloudTrailStore.load(write_log(tmp_path, [event()]))

    def forbidden_query(*args, **kwargs):
        pytest.fail("Invalid tool input reached the store")

    monkeypatch.setattr(store, "query", forbidden_query)
    query_tool = next(tool for tool in store.tools() if tool.name == "query_events")
    result = query_tool.invoke({"sql": "TEST_ONLY_PRIVATE_QUERY"})
    assert json.loads(result)["error"]["code"] == "invalid_tool_input"
    assert "records" not in json.loads(result)
    assert "TEST_ONLY_PRIVATE_QUERY" not in result


def test_duplicate_event_ids_fail_instead_of_resolving_ambiguously(tmp_path):
    write_log(tmp_path, [event()], "one.json")
    write_log(tmp_path, [event(eventName="DeleteTrail")], "two.json")
    with pytest.raises(StoreError) as caught:
        CloudTrailStore.load(tmp_path)
    assert caught.value.code == "duplicate_event_id"


def test_issued_access_key_reverse_pivot_distinguishes_caller_and_session(tmp_path):
    issued = "ASIA_SYNTHETIC_SESSION"
    caller = "AKIA_SYNTHETIC_CALLER"
    issuance = event(
        "issuance",
        eventName="AssumeRole",
        eventSource="sts.amazonaws.com",
        eventTime="2026-01-01T09:00:00Z",
        userIdentity={"arn": "arn:aws:iam::123456789012:user/tester", "accessKeyId": caller},
        responseElements={"credentials": {"accessKeyId": issued}},
    )
    use = event("session-use")
    use["userIdentity"]["accessKeyId"] = issued
    store = CloudTrailStore.load(write_log(tmp_path, [issuance, use]))
    reverse = store.query(Query(issued_access_key=issued))
    assert [item["event_id"] for item in reverse["records"]] == ["issuance"]
    assert reverse["records"][0]["record"] == issuance
    forward = store.query(Query(access_key=issued))
    assert [item["event_id"] for item in forward["records"]] == ["session-use"]
    assert store.query(Query(issued_access_key=caller))["matched"] == 0
    both = store.query(Query(access_key=caller, issued_access_key=issued))
    assert both["matched"] == 1
    assert both["records"][0]["event_id"] == "issuance"
    assert store.query(Query(access_key=issued, issued_access_key=issued))["matched"] == 0
    assert store.query(Query(issued_access_key="SYNTHETIC_SESSION"))["matched"] == 0


def test_pagination_is_deterministic_across_duplicate_times_and_identical_filters(tmp_path):
    records = [
        event(f"event-{index}", eventTime=f"2026-01-01T10:00:{index:02d}Z") for index in range(45)
    ]
    records += [event(f"duplicate-{index}", eventTime="2026-01-01T10:00:19Z") for index in range(5)]
    records += [
        event("outside-time", eventTime="2026-01-01T11:00:00Z"),
        event("outside-ip", sourceIPAddress="192.0.2.250"),
    ]
    path = write_log(tmp_path, records)
    store = CloudTrailStore.load(path)
    query = Query(
        source_ip="192.0.2.4",
        start_time="2026-01-01T10:00:00Z",
        end_time="2026-01-01T10:00:44Z",
        limit=20,
    )
    first = store.query(query)
    assert first["matched"] == 50
    assert len(first["records"]) == 20
    assert first["truncated"] is True
    assert first["next_offset"] == 20
    second_query = query.model_copy(update={"offset": first["next_offset"]})
    second = store.query(second_query)
    assert second["matched"] == 50
    assert len(second["records"]) == 20
    assert second["truncated"] is True
    assert second["next_offset"] == 40
    assert store.query(second_query) == second
    assert CloudTrailStore.load(path).query(second_query) == second
    third = store.query(query.model_copy(update={"offset": second["next_offset"]}))
    assert third["matched"] == 50
    assert len(third["records"]) == 10
    assert third["truncated"] is False
    assert third["next_offset"] is None
    combined = first["records"] + second["records"] + third["records"]
    expected_ids = (
        [f"event-{index}" for index in range(20)]
        + [f"duplicate-{index}" for index in range(5)]
        + [f"event-{index}" for index in range(20, 45)]
    )
    assert [item["event_id"] for item in combined] == expected_ids
    assert len({item["ref"] for item in combined}) == 50
    for item in combined:
        assert store.get(item["ref"]) == item
