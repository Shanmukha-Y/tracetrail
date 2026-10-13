"""Frozen, field-annotated scoring for TraceTrail's synthetic cases.

This module has no model or network calls. It checks a small set of fixed
propositions. It is not a general natural-language entailment judge.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

_MISSING = object()
_STATUSES = {"supported", "uncertain", "refuted"}


def _field(record: Mapping[str, Any], field: str) -> Any:
    value: Any = record
    for part in field.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _same(left: Any, right: Any) -> bool:
    """Compare JSON values without equating booleans with integers."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _observation_matches(actual: Any, observation: Mapping[str, Any]) -> bool:
    """Check explicit field presence without conflating missing and null."""
    present = observation.get("present", True)
    if type(present) is not bool:
        return False
    value = observation.get("value", _MISSING)
    if present:
        return actual is not _MISSING and _same(actual, value)
    return actual is _MISSING and value is None


def _statement(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if callable(getattr(value, "model_dump", None)):
        return value.model_dump(mode="json")
    return {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _citation(fixture_sha256: str, index: int) -> str:
    return f"sha256:{fixture_sha256}/Records/{index}"


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    """Load and validate the manifest and every immutable fixture.

    Fixture paths are relative to the repository root, one level above the
    manifest directory. Internal keys beginning with ``_`` are for local
    scoring and must not be included in a model's input.
    """
    manifest_path = Path(path).resolve()
    root = manifest_path.parent.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1" or not isinstance(manifest.get("cases"), list):
        raise ValueError("Unsupported evaluation manifest schema")
    manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    cases: list[dict[str, Any]] = []
    case_ids: set[str] = set()
    for original in manifest["cases"]:
        case = copy.deepcopy(original)
        if not isinstance(case, dict) or not case.get("id") or case["id"] in case_ids:
            raise ValueError("Case IDs must be present and unique")
        case_ids.add(case["id"])
        if case.get("split") not in {"development", "heldout"}:
            raise ValueError(f"Invalid split for {case['id']}")
        fixture_path = (root / case["fixture"]).resolve()
        if not fixture_path.is_relative_to(root / "fixtures"):
            raise ValueError("Fixture path must stay within the repository fixtures directory")
        fixture_bytes = fixture_path.read_bytes()
        digest = hashlib.sha256(fixture_bytes).hexdigest()
        if digest != case.get("fixture_sha256"):
            raise ValueError(f"Fixture hash mismatch for {case['id']}")
        payload = json.loads(fixture_bytes)
        records = payload.get("Records") if isinstance(payload, dict) else None
        if (
            not isinstance(records, list)
            or not records
            or any(not isinstance(r, dict) for r in records)
        ):
            raise ValueError(f"Invalid CloudTrail fixture for {case['id']}")
        by_id = {record.get("eventID"): record for record in records}
        if None in by_id or len(by_id) != len(records):
            raise ValueError(f"Fixture event IDs must be present and unique for {case['id']}")
        if case.get("seed_event_id") not in by_id:
            raise ValueError(f"Unknown seed event for {case['id']}")
        relevant = case.get("relevant_event_ids", [])
        if (
            not relevant
            or len(set(relevant)) != len(relevant)
            or any(e not in by_id for e in relevant)
        ):
            raise ValueError(f"Invalid relevant event annotation for {case['id']}")
        hypotheses = case.get("hypotheses", [])
        statements = {h.get("claim_id"): h.get("statement") for h in hypotheses}
        if (
            not hypotheses
            or None in statements
            or len(statements) != len(hypotheses)
            or any(not _statement(s) for s in statements.values())
        ):
            raise ValueError(f"Invalid fixed hypotheses for {case['id']}")
        annotations = case.get("annotations", [])
        if len(annotations) != len(statements) or {a.get("claim_id") for a in annotations} != set(
            statements
        ):
            raise ValueError(
                f"Every fixed hypothesis needs exactly one annotation for {case['id']}"
            )
        for annotation in annotations:
            if annotation.get("expected_status") not in _STATUSES:
                raise ValueError(f"Invalid claim status for {case['id']}")
            ids = annotation.get("required_event_ids", [])
            if (
                not ids
                or len(set(ids)) != len(ids)
                or any(event_id not in by_id for event_id in ids)
            ):
                raise ValueError(f"Invalid claim support events for {case['id']}")
            for observation in annotation.get("required_observations", []):
                event_id = observation.get("event_id")
                field = observation.get("field")
                if event_id not in ids or not isinstance(field, str) or not field:
                    raise ValueError(f"Invalid field annotation for {case['id']}")
                actual = _field(by_id[event_id], field)
                if not _observation_matches(actual, observation):
                    raise ValueError(
                        f"Annotated field does not match the frozen source for {case['id']}"
                    )
        case["_fixture_records"] = records
        case["_fixture_path"] = str(fixture_path)
        case["_manifest_sha256"] = manifest_hash
        case["_suite_id"] = manifest.get("suite_id")
        cases.append(case)
    return cases


def _tool_error(entry: Any) -> bool:
    entry = _dict(entry)
    response = _dict(entry.get("result"))
    return bool(
        entry.get("error")
        or entry.get("status") == "error"
        or response.get("error")
        or response.get("ok") is False
        or response.get("status") == "error"
    )


def _number(value: Any, *, integer: bool = False) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value < 0 or (integer and not float(value).is_integer()):
        return None
    return int(value) if integer else float(value)


def score_run(case: Mapping[str, Any], result: Any) -> dict[str, Any]:
    """Recompute metrics from a complete local run and its frozen case.

    Findings use the manifest's fixed statements. Exact citation discovery,
    source records, claim status, and all required field observations must
    agree. A free-form or stronger statement is outside this evaluator's
    annotation scope and counts as an unsupported finding.
    Missing fields require ``present=False`` and ``value=None``. An omitted
    presence flag retains the original contract and means ``present=True``.
    """
    result = _dict(result)
    records = case.get("_fixture_records")
    if not isinstance(records, list):
        raise ValueError("Use a case returned by load_cases so source evidence can be checked")
    fixture_hash = case["fixture_sha256"]
    source = {_citation(fixture_hash, i): record for i, record in enumerate(records)}
    event_refs = {record["eventID"]: ref for ref, record in source.items()}
    history = _list(result.get("tool_history"))
    returned_refs = {event_refs[case["seed_event_id"]]}
    for raw_entry in history:
        entry = _dict(raw_entry)
        if entry.get("name") not in {"query_events", "get_event"} or _tool_error(entry):
            continue
        response = _dict(entry.get("result"))
        returned = _list(response.get("records")) if "records" in response else [response]
        for item in returned:
            item = _dict(item)
            ref = item.get("ref")
            expected = source.get(ref) if isinstance(ref, str) else None
            if (
                expected is not None
                and item.get("event_id") == expected.get("eventID")
                and _same(item.get("record"), expected)
            ):
                returned_refs.add(ref)
    evidence = [_dict(item) for item in _list(result.get("evidence"))]
    evidence_counts = Counter(
        item.get("ref") for item in evidence if isinstance(item.get("ref"), str)
    )
    valid_evidence: dict[str, dict[str, Any]] = {}
    invalid_evidence: list[str] = []
    for index, item in enumerate(evidence):
        ref = item.get("ref")
        expected = source.get(ref) if isinstance(ref, str) else None
        if (
            expected is not None
            and ref in returned_refs
            and evidence_counts[ref] == 1
            and item.get("event_id") == expected.get("eventID")
            and _same(item.get("record"), expected)
        ):
            valid_evidence[ref] = expected
        else:
            invalid_evidence.append(ref if isinstance(ref, str) else f"evidence[{index}]")

    selected_items = _list(result.get("selected_event_refs"))
    selected = {ref for ref in selected_items if isinstance(ref, str)}
    malformed_selection_count = sum(not isinstance(ref, str) for ref in selected_items)
    valid_selected = selected & valid_evidence.keys()
    relevant_refs = {event_refs[event_id] for event_id in case["relevant_event_ids"]}
    true_positives = len(valid_selected & relevant_refs)
    selected_count = len(selected) + malformed_selection_count
    precision = true_positives / selected_count if selected_count else 0.0
    recall = true_positives / len(relevant_refs)

    observations = [_dict(o) for o in _list(result.get("observations"))]
    valid_observations: list[dict[str, Any]] = []
    invalid_observation_count = 0
    for observation in observations:
        citation = observation.get("citation")
        field = observation.get("field")
        record = valid_evidence.get(citation) if isinstance(citation, str) else None
        actual = (
            _field(record, field) if record is not None and isinstance(field, str) else _MISSING
        )
        if (
            isinstance(citation, str)
            and citation in valid_selected
            and record is not None
            and isinstance(field, str)
            and bool(field)
            and _observation_matches(actual, observation)
        ):
            valid_observations.append(observation)
        else:
            invalid_observation_count += 1

    annotations = {a["claim_id"]: a for a in case["annotations"]}
    statements = {h["claim_id"]: _statement(h["statement"]) for h in case["hypotheses"]}
    findings = [_dict(f) for f in _list(result.get("findings"))]
    finding_counts = Counter(
        f.get("claim_id") for f in findings if isinstance(f.get("claim_id"), str)
    )
    per_finding: list[dict[str, Any]] = []
    correct_statuses = 0
    valid_claims: set[str] = set()
    uncertainty_correct = 0
    for index, finding in enumerate(findings):
        claim_id = finding.get("claim_id")
        annotation = annotations.get(claim_id) if isinstance(claim_id, str) else None
        reasons: list[str] = []
        if annotation is None:
            reasons.append("unannotated_claim")
        else:
            if finding_counts[claim_id] != 1:
                reasons.append("duplicate_claim")
            if _statement(finding.get("statement")) != statements[claim_id]:
                reasons.append("statement_mismatch")
            if finding.get("status") != annotation["expected_status"]:
                reasons.append("status_mismatch")
            elif (
                finding_counts[claim_id] == 1
                and _statement(finding.get("statement")) == statements[claim_id]
            ):
                correct_statuses += 1
            citations = _list(finding.get("citations"))
            if any(not isinstance(ref, str) or ref not in valid_selected for ref in citations):
                reasons.append("invalid_or_unselected_citation")
            cited = {ref for ref in citations if isinstance(ref, str)}
            required_refs = {event_refs[event_id] for event_id in annotation["required_event_ids"]}
            if not required_refs.issubset(cited):
                reasons.append("missing_required_citation")
            for expected in annotation["required_observations"]:
                ref = event_refs[expected["event_id"]]
                if not any(
                    o.get("citation") == ref
                    and o.get("field") == expected["field"]
                    and o.get("present", True) is expected.get("present", True)
                    and _same(o.get("value"), expected["value"])
                    for o in valid_observations
                ):
                    reasons.append("missing_or_wrong_required_observation")
                    break
            if not reasons:
                valid_claims.add(claim_id)
                if annotation["expected_status"] == "uncertain":
                    uncertainty_correct += 1
        per_finding.append(
            {
                "index": index,
                "claim_id": claim_id,
                "annotation_supported": not reasons,
                "reasons": reasons,
            }
        )
    unsupported = sum(not item["annotation_supported"] for item in per_finding)
    expected_uncertain = sum(a["expected_status"] == "uncertain" for a in annotations.values())
    missing = sorted(set(annotations) - finding_counts.keys())
    failures = _list(result.get("failures"))
    return {
        "case_id": case["id"],
        "split": case["split"],
        "suite_id": case.get("_suite_id"),
        "fixture_sha256": fixture_hash,
        "manifest_sha256": case.get("_manifest_sha256"),
        "relevant_event_precision": precision,
        "relevant_event_recall": recall,
        "relevant_true_positives": true_positives,
        "selected_event_count": selected_count,
        "relevant_event_count": len(relevant_refs),
        "retrieved_event_count": len(valid_evidence),
        "tool_returned_event_count": len(returned_refs),
        "invalid_evidence_count": len(invalid_evidence),
        "invalid_evidence_refs": invalid_evidence,
        "invalid_observation_count": invalid_observation_count,
        "unsupported_claims": unsupported,
        "unsupported_claim_rate": unsupported / len(findings) if findings else None,
        "finding_count": len(findings),
        "annotation_coverage": len(set(finding_counts) & annotations.keys()) / len(annotations),
        "status_accuracy": correct_statuses / len(annotations),
        "supported_annotation_rate": len(valid_claims) / len(annotations),
        "insufficient_evidence_handling": uncertainty_correct / expected_uncertain
        if expected_uncertain
        else None,
        "missing_claim_ids": missing,
        "per_finding": per_finding,
        "query_count": _number(result.get("query_count"), integer=True),
        "model_calls": _number(result.get("model_calls"), integer=True),
        "duration_seconds": _number(result.get("duration_seconds")),
        "tool_errors": sum(_tool_error(item) for item in history),
        "failure_count": len(failures),
        "run_failed": bool(failures),
    }
