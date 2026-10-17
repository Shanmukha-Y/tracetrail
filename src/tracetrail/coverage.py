"""Observed pivot values and actual query scopes, without issuing searches."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from tracetrail.store import Query

_CANDIDATE_LIMIT = 16
_PRIORITY = {
    "access_key": 0,
    "issued_access_key": 0,
    "principal": 1,
    "session_issuer": 2,
    "source_ip": 3,
}
_FILTER_CATALOG = {
    "access_key": (
        "credential_use",
        "Exact userIdentity.accessKeyId: requests signed with this key, not its issuance.",
    ),
    "issued_access_key": (
        "credential_issuance",
        "Exact responseElements.credentials.accessKeyId: records returning this temporary key.",
    ),
    "principal": (
        "principal_activity",
        "Exact userIdentity.arn, principalId, or userName: activity of that recorded identity.",
    ),
    "session_issuer": (
        "role_session_activity",
        "Exact userIdentity.sessionContext.sessionIssuer.arn: activity of sessions of that issuer.",
    ),
    "source_ip": (
        "source_activity",
        "Exact sourceIPAddress: requests with that recorded address or service value.",
    ),
}


def _field(record: dict, path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _normalized_query(args: Any) -> dict | None:
    """Compare actual query scopes with Query's defaults and UTC normalization."""
    if not isinstance(args, dict):
        return None
    try:
        return Query.model_validate(args).model_dump(mode="json")
    except (ValidationError, TypeError, ValueError):
        return None


def _query_key(query: dict) -> str:
    return json.dumps(query, sort_keys=True, separators=(",", ":"))


def _query_digest(query: dict) -> str:
    return hashlib.sha256(_query_key(query).encode()).hexdigest()[:12]


def _successful_query(entry: dict) -> bool:
    output = entry.get("result")
    return (
        entry.get("name") == "query_events"
        and _normalized_query(entry.get("args")) is not None
        and isinstance(output, dict)
        and "error" not in output
        and type(output.get("matched")) is int
        and output["matched"] >= 0
        and type(output.get("truncated")) is bool
        and (
            isinstance(output.get("records"), list)
            or isinstance(output.get("returned_citations"), list)
        )
    )


def _unbounded_first_page(args: dict, field: str, value: str) -> bool:
    scope = _normalized_query(args)
    if scope is None or scope["offset"] != 0:
        return False
    # Limit still bounds this page. This flag says nothing about truncation,
    # completeness, other files, or records outside the loaded input.
    return all(
        actual == (value if name == field else None)
        for name, actual in scope.items()
        if name not in ("limit", "offset")
    )


def evidence_coverage(evidence: list[dict], tool_history: list[dict]) -> dict:
    """Inventory observed values and queries that used each exact filter value.

    ``searched`` and ``has_successful_scoped_attempt`` mean a query containing
    this exact candidate filter succeeded under its full recorded AND filters,
    time bounds, and pagination. They do not mean this candidate's unrestricted
    activity was searched. ``has_successful_unbounded_first_page`` excludes
    time and additional filters, but still describes only one bounded page.
    Continuations retain actual origin arguments and omit scopes already
    successfully executed after Query default and UTC normalization.
    This function only reads its arguments; it never queries the evidence store.
    """
    sources: dict[tuple[str, str], set[tuple[str, str]]] = {}

    def observe(item: dict, query_field: str, record_field: str) -> None:
        value = _field(item["record"], record_field)
        if not isinstance(value, str) or not value.strip() or len(value) > 2048:
            return
        sources.setdefault((query_field, value), set()).add((item["ref"], record_field))

    for item in evidence:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("record"), dict)
            or not isinstance(item.get("ref"), str)
            or not item["ref"]
        ):
            continue
        observe(item, "access_key", "userIdentity.accessKeyId")
        observe(item, "access_key", "responseElements.credentials.accessKeyId")
        if _field(item["record"], "userIdentity.type") == "AssumedRole":
            observe(item, "issued_access_key", "userIdentity.accessKeyId")
        for field in ("arn", "principalId", "userName"):
            observe(item, "principal", f"userIdentity.{field}")
        observe(item, "session_issuer", "userIdentity.sessionContext.sessionIssuer.arn")
        observe(item, "session_issuer", "requestParameters.roleArn")
        observe(item, "source_ip", "sourceIPAddress")

    ordered = sorted(sources, key=lambda key: (_PRIORITY[key[0]], key[0], key[1]))
    candidates = []
    for field, value in ordered[:_CANDIDATE_LIMIT]:
        query = {field: value}
        attempts = []
        searched = False
        unbounded_first_page = False
        for index, entry in enumerate(tool_history):
            if not isinstance(entry, dict) or entry.get("name") != "query_events":
                continue
            args = entry.get("args")
            if not isinstance(args, dict) or args.get(field) != value:
                continue
            output = entry.get("result")
            output = output if isinstance(output, dict) else {}
            successful = _successful_query(entry)
            attempts.append(
                {
                    "attempt_id": f"Q{index}",
                    "tool_index": index,
                    "args": deepcopy(args),
                    "successful": successful,
                    "matched": output.get("matched"),
                    "truncated": output.get("truncated"),
                    "error": deepcopy(output.get("error")),
                    "next_offset": output.get("next_offset"),
                }
            )
            searched = searched or successful
            unbounded_first_page = unbounded_first_page or (
                successful and _unbounded_first_page(args, field, value)
            )
        kind, meaning = _FILTER_CATALOG[field]
        candidates.append(
            {
                "id": "P" + _query_digest(query),
                "query": query,
                "kind": kind,
                "filter_meaning": meaning,
                "local_query_supported": True,
                "sources": [
                    {"citation": citation, "field": path}
                    for citation, path in sorted(sources[(field, value)])
                ],
                "attempts": attempts,
                "searched": searched,
                "has_successful_scoped_attempt": searched,
                "has_successful_unbounded_first_page": unbounded_first_page,
            }
        )

    continuations = []
    executed = {
        _query_key(_normalized_query(entry["args"]))
        for entry in tool_history
        if isinstance(entry, dict) and _successful_query(entry)
    }
    pending = set()
    for index, entry in enumerate(tool_history):
        if not isinstance(entry, dict) or not _successful_query(entry):
            continue
        output = entry["result"]
        next_offset = output.get("next_offset")
        previous_offset = entry["args"].get("offset", 0)
        if (
            output["truncated"] is True
            and type(next_offset) is int
            and type(previous_offset) is int
            and next_offset > previous_offset >= 0
        ):
            query = {**deepcopy(entry["args"]), "offset": next_offset}
            normalized = _normalized_query(query)
            if normalized is None:
                continue
            scope_key = _query_key(normalized)
            digest = _query_digest(normalized)
            if scope_key in executed or scope_key in pending:
                continue
            pending.add(scope_key)
            continuations.append(
                {
                    "id": "C" + digest,
                    "attempt_id": f"Q{index}",
                    "tool_index": index,
                    "original_args": deepcopy(entry["args"]),
                    "next_offset": next_offset,
                    "query": query,
                }
            )
    return {
        "candidates": candidates,
        "candidate_count": len(ordered),
        "candidate_limit": _CANDIDATE_LIMIT,
        "candidates_truncated": len(ordered) > _CANDIDATE_LIMIT,
        "continuations": continuations,
        "finish_accounting_ids": [item["id"] for item in candidates + continuations],
    }
