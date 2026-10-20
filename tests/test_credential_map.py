"""Observed credential context only; no model or store capability evidence."""

import socket

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
