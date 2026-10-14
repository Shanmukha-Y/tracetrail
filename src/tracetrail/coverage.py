"""Observed pivot values and actual query scopes, without issuing searches."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

_CANDIDATE_LIMIT = 16
_PRIORITY = {
    "access_key": 0,
    "issued_access_key": 0,
    "principal": 1,
    "session_issuer": 2,
    "source_ip": 3,
}


def _field(record: dict, path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _successful_query(entry: dict) -> bool:
    output = entry.get("result")
    return (
        entry.get("name") == "query_events"
        and isinstance(entry.get("args"), dict)
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


def evidence_coverage(evidence: list[dict], tool_history: list[dict]) -> dict:
    """Inventory observed values and queries that used each exact filter value.

    ``searched`` means a matching query succeeded under its recorded filters,
    time bounds, and pagination. It does not mean investigation is complete.
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
        digest = hashlib.sha256(
            json.dumps(query, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        attempts = []
        searched = False
        for index, entry in enumerate(tool_history):
            if not isinstance(entry, dict) or entry.get("name") != "query_events":
                continue
            args = entry.get("args")
            if not isinstance(args, dict) or args.get(field) != value:
                continue
            output = entry.get("result")
            output = output if isinstance(output, dict) else {}
            attempts.append(
                {
                    "tool_index": index,
                    "args": deepcopy(args),
                    "matched": output.get("matched"),
                    "truncated": output.get("truncated"),
                    "error": deepcopy(output.get("error")),
                    "next_offset": output.get("next_offset"),
                }
            )
            searched = searched or _successful_query(entry)
        candidates.append(
            {
                "id": "P" + digest[:12],
                "query": query,
                "sources": [
                    {"citation": citation, "field": path}
                    for citation, path in sorted(sources[(field, value)])
                ],
                "attempts": attempts,
                "searched": searched,
            }
        )

    continuations = []
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
            continuations.append(
                {"tool_index": index, "query": {**deepcopy(entry["args"]), "offset": next_offset}}
            )
    return {
        "candidates": candidates,
        "candidate_count": len(ordered),
        "candidate_limit": _CANDIDATE_LIMIT,
        "candidates_truncated": len(ordered) > _CANDIDATE_LIMIT,
        "continuations": continuations,
    }
