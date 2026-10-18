"""Bounded credential occurrences and existing lookup scopes, without searches."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_KEY_LIMIT = 16
_OCCURRENCE_LIMIT = 16
_SCOPE_LIMIT = 16
_SIGNER_PATH = "userIdentity.accessKeyId"
_RETURNED_PATH = "responseElements.credentials.accessKeyId"
_TYPE_PATH = "userIdentity.type"
_ATTEMPT_FIELDS = (
    "attempt_id",
    "tool_index",
    "args",
    "successful",
    "matched",
    "truncated",
    "error",
    "next_offset",
)
_CONTINUATION_FIELDS = (
    "id",
    "attempt_id",
    "tool_index",
    "original_args",
    "next_offset",
    "query",
)


def _field(record: dict, path: str) -> tuple[bool, Any]:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False, None
        value = value[part]
    return True, value


def _key(value: Any) -> str | None:
    if isinstance(value, str) and value.strip() and len(value) <= 2048:
        return value
    return None


def _metadata(entries: list[dict], fields: tuple[str, ...], id_field: str) -> list[dict]:
    def order(entry: dict) -> tuple[int, str]:
        index = entry.get("tool_index")
        return (index if type(index) is int else -1, str(entry.get(id_field, "")))

    return [
        {field: deepcopy(entry[field]) for field in fields if field in entry}
        for entry in sorted(entries, key=order)[:_SCOPE_LIMIT]
    ]


def _lookup(key: str, field: str, coverage: dict) -> dict:
    candidates = coverage.get("candidates", [])
    candidate = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and item.get("query") == {field: key}
        ),
        None,
    )
    attempts = [
        item
        for item in (candidate.get("attempts", []) if candidate else [])
        if isinstance(item, dict)
        and isinstance(item.get("args"), dict)
        and item["args"].get(field) == key
    ]
    continuations = [
        item
        for item in coverage.get("continuations", [])
        if isinstance(item, dict)
        and isinstance(item.get("query"), dict)
        and item["query"].get(field) == key
    ]
    return {
        "candidate_visible": candidate is not None,
        "candidate_id": candidate.get("id") if candidate else None,
        "query": deepcopy(candidate["query"]) if candidate else None,
        "attempts": _metadata(attempts, _ATTEMPT_FIELDS, "attempt_id"),
        "attempt_count": len(attempts),
        "attempt_limit": _SCOPE_LIMIT,
        "omitted_attempt_count": max(0, len(attempts) - _SCOPE_LIMIT),
        "pending_continuations": _metadata(continuations, _CONTINUATION_FIELDS, "id"),
        "pending_continuation_count": len(continuations),
        "pending_continuation_limit": _SCOPE_LIMIT,
        "omitted_pending_continuation_count": max(0, len(continuations) - _SCOPE_LIMIT),
    }


def credential_map(evidence: list[dict], coverage: dict) -> dict:
    """Group exact key occurrences from already returned evidence only.

    ``coverage`` is the existing ``evidence_coverage`` catalog. No new queries,
    candidate IDs, direction guesses, claim judgments, or hidden records are
    generated. A missing candidate means it is absent from the visible catalog,
    not that its filter is unavailable. Matching continuation scopes may still
    be visible. Actual attempts retain their complete recorded AND/time/page
    scope; they do not establish exhaustive activity or semantic support.

    Keys and unique (citation, field) occurrences have stable lexical order.
    The 16-occurrence limit is combined across both directions for each key.
    Top-level omitted occurrences include all occurrences of omitted keys.
    Identity types are copied literally, including explicit null and absence.
    Malformed evidence entries and non-string/empty/oversized keys are ignored;
    conflicting records under one citation are rejected.
    """
    if not isinstance(evidence, list) or not isinstance(coverage, dict):
        raise ValueError("Credential context requires evidence and a coverage catalog")
    occurrences: dict[str, dict[tuple[str, str], dict]] = {}
    records_by_ref: dict[str, dict] = {}
    for item in evidence:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("record"), dict)
            or not isinstance(item.get("ref"), str)
            or not item["ref"]
        ):
            continue
        record, ref = item["record"], item["ref"]
        if ref in records_by_ref:
            if records_by_ref[ref] != record:
                raise ValueError("Credential citations must resolve to one exact record")
            continue
        records_by_ref[ref] = record
        caller = _key(_field(record, _SIGNER_PATH)[1])
        returned = _key(_field(record, _RETURNED_PATH)[1])
        if caller is not None:
            type_present, identity_type = _field(record, _TYPE_PATH)
            occurrences.setdefault(caller, {})[(ref, _SIGNER_PATH)] = {
                "citation": ref,
                "field": _SIGNER_PATH,
                "user_identity_type": {
                    "field": _TYPE_PATH,
                    "present": type_present,
                    "value": deepcopy(identity_type),
                },
            }
        if returned is not None:
            occurrences.setdefault(returned, {})[(ref, _RETURNED_PATH)] = {
                "citation": ref,
                "field": _RETURNED_PATH,
                "recorded_caller": (
                    {"key": caller, "citation": ref, "field": _SIGNER_PATH}
                    if caller is not None
                    else None
                ),
            }

    keys = []
    occurrence_count = sum(len(items) for items in occurrences.values())
    included_count = 0
    for key in sorted(occurrences)[:_KEY_LIMIT]:
        items = occurrences[key]
        visible = [items[source] for source in sorted(items)[:_OCCURRENCE_LIMIT]]
        included_count += len(visible)
        keys.append(
            {
                "key": key,
                "signer_occurrences": [o for o in visible if o["field"] == _SIGNER_PATH],
                "returned_occurrences": [o for o in visible if o["field"] == _RETURNED_PATH],
                "occurrence_count": len(items),
                "omitted_occurrence_count": max(0, len(items) - _OCCURRENCE_LIMIT),
                "lookups": {
                    "use": _lookup(key, "access_key", coverage),
                    "issuance": _lookup(key, "issued_access_key", coverage),
                },
            }
        )
    return {
        "keys": keys,
        "key_count": len(occurrences),
        "key_limit": _KEY_LIMIT,
        "keys_truncated": len(occurrences) > _KEY_LIMIT,
        "omitted_key_count": max(0, len(occurrences) - _KEY_LIMIT),
        "occurrence_limit_per_key": _OCCURRENCE_LIMIT,
        "occurrence_count": occurrence_count,
        "included_occurrence_count": included_count,
        "omitted_occurrence_count": occurrence_count - included_count,
    }
