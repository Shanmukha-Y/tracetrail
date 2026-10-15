"""Projection tests use constructed evidence, never model capability results."""

import json
import socket
from copy import deepcopy

import pytest

from tracetrail.facts import chronological_context, project_observations
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


def test_facts_resolve_to_selected_record_and_preserve_scalar_json_types():
    item = evidence(
        requestParameters={
            "boolean": True,
            "integer": 1,
            "float": 1.0,
            "null": None,
            "string": "1",
            "zero": -0.0,
        }
    )
    observations = project_observations([item], [item["ref"]])
    assert all(obs["citation"] == item["ref"] for obs in observations)
    for obs in observations:
        value = item["record"]
        try:
            for part in obs["field"].split("."):
                value = value[part]
        except KeyError:
            assert obs["present"] is False and obs["value"] is None
        else:
            assert obs["present"] is True
            assert type(obs["value"]) is type(value)
            assert obs["value"] == value
    fields = by_field(observations)
    assert fields["requestParameters.boolean"]["value"] is True
    assert type(fields["requestParameters.integer"]["value"]) is int
    assert type(fields["requestParameters.float"]["value"]) is float
    assert json.dumps(fields["requestParameters.zero"]["value"]) == "-0.0"


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


def test_arrays_and_empty_containers_remain_whole_exact_values():
    resources = [{"ARN": "arn:aws:s3:::synthetic/example", "flags": [True, 1, None]}, "literal"]
    item = evidence(resources=resources, requestParameters={}, additionalEventData=[])
    fields = by_field(project_observations([item], [item["ref"]]))
    assert fields["resources"]["value"] == resources
    assert fields["requestParameters"]["value"] == {}
    assert fields["additionalEventData"]["value"] == []
    assert all(
        fields[name]["present"] is True
        for name in ("resources", "requestParameters", "additionalEventData")
    )
    assert not any(name.startswith("resources.") for name in fields)


def test_projection_copies_only_selected_records_without_selecting_hidden_context():
    selected = evidence("selected")
    unselected = evidence("unselected", requestParameters={"hidden": "DO_NOT_PROJECT"})
    unselected["annotations"] = [{"expected_status": "NO_GOLD_LOOKUP"}]
    observations = project_observations([selected, unselected], [selected["ref"]])
    assert {item["citation"] for item in observations} == {"selected"}
    assert "DO_NOT_PROJECT" not in json.dumps(observations)
    assert "NO_GOLD_LOOKUP" not in json.dumps(observations)


def test_projected_containers_are_deep_copies_and_inputs_remain_unchanged():
    item = evidence(resources=[{"nested": [True, {"value": "original"}]}])
    before = deepcopy(item)
    fields = by_field(project_observations([item], [item["ref"]]))
    fields["resources"]["value"][0]["nested"][1]["value"] = "changed"
    assert item == before


def test_nested_dictionary_projection_order_is_deterministic():
    first = evidence(requestParameters={"z": 2, "a": {"z": 3, "b": 1}})
    second = evidence(requestParameters={"a": {"b": 1, "z": 3}, "z": 2})
    before = deepcopy(first)
    observations = project_observations([first], [first["ref"]])
    assert observations == project_observations([second], [second["ref"]])
    assert [item["field"] for item in observations] == sorted(
        item["field"] for item in observations
    )
    assert first == before


@pytest.mark.parametrize(
    "selected_refs", [["unknown"], ["synthetic-ref", "synthetic-ref"], [None], [{}]]
)
def test_unknown_duplicate_or_invalid_selected_citations_fail(selected_refs):
    with pytest.raises(ValueError):
        project_observations([evidence()], selected_refs)


def test_duplicate_evidence_citations_fail_even_when_no_record_is_selected():
    items = [evidence("same"), evidence("same", eventName="DifferentActivity")]
    with pytest.raises(ValueError, match="unique"):
        project_observations(items, [])
    with pytest.raises(ValueError, match="unique"):
        chronological_context(items, "same")


@pytest.mark.parametrize("bad_key", ["", "literal.dot", 1])
def test_ambiguous_dictionary_keys_fail_instead_of_inventing_paths(bad_key):
    item = evidence(requestParameters={bad_key: "exact but ambiguous"})
    with pytest.raises(ValueError, match="ambiguous dots"):
        project_observations([item], [item["ref"]])


def test_dotted_and_empty_keys_inside_whole_arrays_remain_unambiguous_values():
    resources = [{"a.b": 1, "": 2, "nested": [{"also.dotted": {"": True}}]}]
    item = evidence(resources=resources)
    fields = by_field(project_observations([item], [item["ref"]]))
    assert fields["resources"]["present"] is True
    assert fields["resources"]["value"] == resources
    assert not any(name.startswith("resources.") for name in fields)


@pytest.mark.parametrize("length", [512, 513])
def test_emitted_field_paths_match_the_observation_schema_limit(length):
    prefix = "requestParameters."
    key = "x" * (length - len(prefix))
    item = evidence(requestParameters={key: "exact"})
    if length == 513:
        with pytest.raises(ValueError, match="512 characters"):
            project_observations([item], [item["ref"]])
    else:
        fields = by_field(project_observations([item], [item["ref"]]))
        assert fields[prefix + key]["value"] == "exact"
        assert len(prefix + key) == 512


def test_plain_slashes_and_numeric_dictionary_keys_are_preserved():
    item = evidence(requestParameters={"a/b": {"0": "exact"}, "~": "literal"})
    fields = by_field(project_observations([item], [item["ref"]]))
    assert fields["requestParameters.a/b.0"]["value"] == "exact"
    assert fields["requestParameters.~"]["value"] == "literal"


def test_observation_cap_raises_without_returning_silently_partial_facts():
    item = evidence()
    complete = project_observations([item], [item["ref"]])
    assert len(project_observations([item], [item["ref"]], max_observations=len(complete))) == len(
        complete
    )
    with pytest.raises(ValueError, match="observation count limit"):
        project_observations([item], [item["ref"]], max_observations=len(complete) - 1)


def test_serialized_byte_cap_is_exact_including_unicode_and_array_punctuation():
    item = evidence(requestParameters={"unicode": 'é\n"'})
    complete = project_observations([item], [item["ref"]])
    size = len(json.dumps(complete, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    assert project_observations([item], [item["ref"]], max_bytes=size) == complete
    with pytest.raises(ValueError, match="byte limit"):
        project_observations([item], [item["ref"]], max_bytes=size - 1)
    with pytest.raises(ValueError, match="byte limit"):
        project_observations([], [], max_bytes=1)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "100"])
@pytest.mark.parametrize("name", ["max_observations", "max_bytes"])
def test_projection_limits_must_be_positive_integers(name, limit):
    with pytest.raises(ValueError, match="positive integers"):
        project_observations([], [], **{name: limit})


@pytest.mark.parametrize("container", ["dict", "list"])
def test_depth_limit_applies_inside_dictionaries_and_whole_arrays(container):
    nested = "leaf"
    for _ in range(32):
        nested = {"child": nested} if container == "dict" else [nested]
    item = evidence(requestParameters=nested)
    with pytest.raises(ValueError, match="maximum depth"):
        project_observations([item], [item["ref"]])


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), b"bytes", (1, 2), {1, 2}])
def test_non_json_or_non_finite_values_fail_without_coercion(invalid):
    item = evidence(requestParameters={"invalid": invalid})
    with pytest.raises(ValueError):
        project_observations([item], [item["ref"]])


def test_chronological_context_uses_utc_instants_and_signed_seed_deltas():
    items = [
        evidence("seed", eventTime="2026-01-01T10:00:00Z"),
        evidence("later", eventTime="2026-01-01T06:30:00-04:00", eventName="LaterActivity"),
        evidence("earlier", eventTime="2026-01-01T12:30:00+03:00", eventName="EarlierActivity"),
    ]
    before = deepcopy(items)
    rows = chronological_context(items, "seed")
    assert rows == [
        {
            "citation": "earlier",
            "event_time_utc": "2026-01-01T09:30:00+00:00",
            "event_name": "EarlierActivity",
            "seconds_from_seed": -1800.0,
        },
        {
            "citation": "seed",
            "event_time_utc": "2026-01-01T10:00:00+00:00",
            "event_name": "SyntheticActivity",
            "seconds_from_seed": 0.0,
        },
        {
            "citation": "later",
            "event_time_utc": "2026-01-01T10:30:00+00:00",
            "event_name": "LaterActivity",
            "seconds_from_seed": 1800.0,
        },
    ]
    assert items == before
    assert all("event_time_utc" not in item["record"] for item in items)
    assert not any(
        key in row for row in rows for key in ("intent", "caused_by", "success", "status")
    )


def test_equal_utc_instants_sort_by_citation_without_discovery_order_bias():
    first = evidence("ref-b", eventTime="2026-01-01T11:00:00+01:00")
    second = evidence("ref-a", eventTime="2026-01-01T10:00:00Z")
    rows = chronological_context([first, second], "ref-b")
    assert [row["citation"] for row in rows] == ["ref-a", "ref-b"]
    assert all(row["seconds_from_seed"] == 0 for row in rows)


@pytest.mark.parametrize("seed", ["missing", "", None, {}])
def test_chronological_context_requires_an_actual_seed_citation(seed):
    with pytest.raises(ValueError, match="seed citation"):
        chronological_context([evidence()], seed)


@pytest.mark.parametrize("event_time", [None, 123, "bad time", "2026-01-01", "2026-01-01T10:00:00"])
def test_bad_or_naive_event_times_fail_instead_of_sorting_as_strings(event_time):
    with pytest.raises(ValueError, match="eventTime"):
        chronological_context([evidence(eventTime=event_time)], "synthetic-ref")


def test_bad_unselected_record_is_not_read_during_projection():
    unselected = {"ref": "unselected", "record": {"ambiguous.key": object()}}
    observations = project_observations([evidence(), unselected], ["synthetic-ref"])
    assert {item["citation"] for item in observations} == {"synthetic-ref"}
