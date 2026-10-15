"""Deterministic facts and temporal context from already returned records only."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

_MAX_DEPTH = 32
_API_ENVELOPE_FIELDS = frozenset(
    {"errorCode", "errorMessage", "requestParameters", "responseElements"}
)


def _records_by_ref(evidence: list[dict]) -> dict[str, dict]:
    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a list of returned records")
    records = {}
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("ref"), str) or not item["ref"]:
            raise ValueError("Every evidence item requires a nonempty citation")
        if item["ref"] in records:
            raise ValueError("Evidence citations must be unique")
        records[item["ref"]] = item.get("record")
    return records


def _keys(value: dict) -> list[str]:
    if any(type(key) is not str or not key or "." in key for key in value):
        raise ValueError("Record keys must be nonempty strings without ambiguous dots")
    return sorted(value)


def _check_json(value: Any, depth: int) -> None:
    if depth > _MAX_DEPTH:
        raise ValueError("Observation projection exceeds the maximum depth of 32")
    if type(value) is dict:
        # Objects inside a whole-list value are opaque JSON, not dotted paths.
        if any(type(key) is not str for key in value):
            raise ValueError("JSON object keys must be strings")
        for key in sorted(value):
            _check_json(value[key], depth + 1)
    elif type(value) is list:
        for item in value:
            _check_json(item, depth + 1)
    elif type(value) not in (type(None), bool, int, float, str):
        raise ValueError("Record values must have JSON types")
    elif type(value) is float and not math.isfinite(value):
        raise ValueError("Record numbers must be finite JSON values")


def project_observations(
    evidence: list[dict],
    selected_refs: list[str],
    *,
    max_observations: int = 2000,
    max_bytes: int = 1_000_000,
) -> list[dict]:
    """Copy selected record fields exactly, or raise without returning partial facts.

    Dictionary fields use the existing unambiguous dotted-path contract. Lists
    are whole values; empty objects and explicit nulls are preserved. Missing
    standard API envelope fields receive explicit absence observations. The byte
    limit measures the compact, ASCII-escaped JSON observation array.
    """
    for limit in (max_observations, max_bytes):
        if type(limit) is not int or limit < 1:
            raise ValueError("Observation limits must be positive integers")
    if not isinstance(selected_refs, list):
        raise ValueError("Selected citations must be a list")
    records = _records_by_ref(evidence)
    seen = set()
    for ref in selected_refs:
        if not isinstance(ref, str) or not ref or ref not in records:
            raise ValueError("A selected citation does not resolve to returned evidence")
        if ref in seen:
            raise ValueError("Selected citations must be unique")
        if type(records[ref]) is not dict:
            raise ValueError("A selected evidence record must be a JSON object")
        seen.add(ref)

    observations: list[dict] = []
    encoded_bytes = 2  # The observation array's brackets, even when empty.
    if encoded_bytes > max_bytes:
        raise ValueError("Observation projection exceeds the byte limit")

    def emit(ref: str, path: str, present: bool, value: Any) -> None:
        nonlocal encoded_bytes
        if len(path) > 512:
            raise ValueError("Observation field paths must not exceed 512 characters")
        if len(observations) >= max_observations:
            raise ValueError("Observation projection exceeds the observation count limit")
        observation = {"citation": ref, "field": path, "present": present, "value": deepcopy(value)}
        try:
            size = len(
                json.dumps(observation, separators=(",", ":"), allow_nan=False).encode("utf-8")
            )
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError("An observation cannot be represented as bounded JSON") from exc
        encoded_bytes += size + bool(observations)
        if encoded_bytes > max_bytes:
            raise ValueError("Observation projection exceeds the byte limit")
        observations.append(observation)

    def visit(ref: str, path: str, value: Any, depth: int) -> None:
        if depth > _MAX_DEPTH:
            raise ValueError("Observation projection exceeds the maximum depth of 32")
        if type(value) is dict and value:
            for key in _keys(value):
                visit(ref, f"{path}.{key}", value[key], depth + 1)
        else:
            _check_json(value, depth)
            emit(ref, path, True, value)

    for ref in selected_refs:
        record = records[ref]
        keys = set(_keys(record)) | _API_ENVELOPE_FIELDS
        for key in sorted(keys):
            if key in record:
                visit(ref, key, record[key], 1)
            else:
                emit(ref, key, False, None)
    return observations


def _event_time(record: dict) -> datetime:
    value = record.get("eventTime")
    if not isinstance(value, str):
        raise ValueError("Temporal context requires an eventTime string")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("eventTime must include a timezone")
        return timestamp.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Temporal context requires valid timezone-aware eventTime values") from exc


def chronological_context(evidence: list[dict], seed_ref: str) -> list[dict]:
    """Derive UTC instants and signed seed-relative seconds without interpreting events."""
    records = _records_by_ref(evidence)
    if not isinstance(seed_ref, str) or not seed_ref or seed_ref not in records:
        raise ValueError("The seed citation must resolve to returned evidence")
    ordered = []
    for ref, record in records.items():
        if not isinstance(record, dict):
            raise ValueError("Temporal context requires JSON record objects")
        if not isinstance(record.get("eventName"), str) or not record["eventName"]:
            raise ValueError("Temporal context requires nonempty eventName strings")
        ordered.append((_event_time(record), ref, record["eventName"]))
    seed_time = next(timestamp for timestamp, ref, _ in ordered if ref == seed_ref)
    return [
        {
            "citation": ref,
            "event_time_utc": timestamp.isoformat(),
            "event_name": event_name,
            "seconds_from_seed": (timestamp - seed_time).total_seconds(),
        }
        for timestamp, ref, event_name in sorted(ordered, key=lambda row: (row[0], row[1]))
    ]
