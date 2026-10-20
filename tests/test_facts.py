"""Projection tests use constructed evidence, never model capability results."""

import socket

import pytest

from tracetrail.facts import project_observations
from tracetrail.store import CloudTrailStore


@pytest.fixture(autouse=True)
def no_hidden_reads_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Fact helpers must only read their supplied arguments")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(CloudTrailStore, "load", forbidden)
    monkeypatch.setattr(CloudTrailStore, "get", forbidden)
    monkeypatch.setattr(CloudTrailStore, "query", forbidden)


def evidence(ref="synthetic-ref", **changes):
    record = {
        "eventID": "synthetic-event",
        "eventName": "SyntheticActivity",
        "eventTime": "2026-01-01T10:00:00Z",
        "userIdentity": {"accessKeyId": "SYNTHETIC_KEY", "type": "AssumedRole"},
        "requestParameters": {"enabled": True},
        "responseElements": None,
    }
    record.update(changes)
    return {"ref": ref, "event_id": record["eventID"], "record": record}


def by_field(observations):
    return {item["field"]: item for item in observations}


def test_missing_api_envelope_fields_are_distinct_from_explicit_nulls():
    item = evidence(errorCode=None, errorMessage="", responseElements=None)
    item["record"].pop("requestParameters")
    fields = by_field(project_observations([item], [item["ref"]]))
    assert fields["errorCode"]["present"] is True
    assert fields["errorCode"]["value"] is None
    assert fields["errorMessage"]["present"] is True
    assert fields["errorMessage"]["value"] == ""
    assert fields["responseElements"]["present"] is True
    assert fields["responseElements"]["value"] is None
    assert fields["requestParameters"]["present"] is False
    assert fields["requestParameters"]["value"] is None
    missing = evidence()
    missing_fields = by_field(project_observations([missing], [missing["ref"]]))
    assert missing_fields["errorCode"]["present"] is False
    assert missing_fields["errorMessage"]["present"] is False
