#!/usr/bin/env python3
"""Publish a numeric summary from a complete, independently verified local pilot.

This script does not import the agent or scorer. It does not run inference,
queries, SDK evaluations, or network calls. Private text is read for identity
checks and content hashes but is never copied into the public summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

PILOT_ID = "tracetrail-model-pilot-v1"
NUMERIC_KEYS = (
    "annotated_claim_count",
    "finding_count",
    "raw_supported_claim_count",
    "raw_supported_claim_rate",
    "process_valid_supported_claim_count",
    "process_valid_supported_claim_rate",
    "required_atom_count",
    "raw_covered_atom_count",
    "raw_required_atom_coverage",
    "process_valid_covered_atom_count",
    "process_valid_required_atom_coverage",
    "correct_status_count",
    "correct_status_rate",
    "process_valid",
    "invalid_evidence_count",
    "invalid_link_count",
    "extra_declared_atom_count",
    "extra_citation_count",
    "unexpected_finding_count",
    "duplicate_claim_count",
    "missing_claim_count",
)
OUTCOMES = (
    "decisive_false_claim",
    "unsupported_definite_claim",
    "avoidable_uncertainty",
    "retrieval_limited_unknown",
    "source_limited_unknown",
    "warranted_decision",
    "omitted_claim",
    "unreviewable_report",
)
OUTCOME_ALIASES = {
    "correct_definite_decision": "warranted_decision",
    "correct_definite_decision_with_available_evidence": "warranted_decision",
    "correct_definite_decision_with_decisive_returned_evidence": "warranted_decision",
}
MAXIMA = (
    "ollama_reported_size_bytes",
    "ollama_reported_size_vram_bytes",
    "listener_process_tree_rss_sum_bytes",
)
STATUSES = {"supported", "refuted", "uncertain"}
AVAILABILITY = {"decisive_returned", "decisive_supplied_only", "insufficient_full_source"}
BASIS = {"adequate", "incomplete", "wrong", "absent", "unreviewable", "not_assessable"}
FIELD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN_STATUSES = {"completed", "invalid", "failed", "degraded", "incomplete"}
MEMORY_STATUSES = {"completed", "partial", "unavailable", "not_recorded"}
FAILURE_PHASES = {
    "plan",
    "planning_validation",
    "tool",
    "validation",
    "report",
    "runner",
    "unload",
    "pilot_started",
    "pilot_runner",
    "pilot_interrupted",
    "pilot_model_identity",
    "start",
    "stop",
}
FAILURE_TYPES = {
    "ValueError",
    "ValidationError",
    "TimeoutError",
    "ReadTimeout",
    "ConnectTimeout",
    "ConnectError",
    "ConnectionError",
    "ResponseError",
    "HTTPStatusError",
    "RemoteProtocolError",
    "LocalProtocolError",
    "RuntimeError",
    "OSError",
    "FileNotFoundError",
    "PermissionError",
    "KeyError",
    "TypeError",
    "IndexError",
    "AssertionError",
    "JSONDecodeError",
    "UnicodeDecodeError",
    "RecursionError",
    "KeyboardInterrupt",
    "CancelledError",
    "FrozenModelIdentityMismatch",
    "IncompleteRecordedAttempt",
    "StopIteration",
    "MemoryError",
    "TimeoutException",
    "UnsupportedProtocol",
    "StoreError",
}
FAILURE_CODES = {
    "claim_coverage",
    "finding_citation_mismatch",
    "uncited_conclusion",
    "changed_statement",
    "unselected_finding_citation",
    "unknown_citation",
    "unsupported_observation",
    "observation_projection_failed",
    "tool_exception",
    "invalid_finding",
    "invalid_finding_rationale",
    "invalid_missing_evidence",
    "invalid_missing_evidence_entry",
    "invalid_finding_status",
    "missing_uncertainty",
    "invalid_evidence",
    "invalid_selected_references",
    "invalid_evidence_links",
    "invalid_evidence_link",
    "invalid_evidence_link_citation",
    "unknown_evidence_link_citation",
    "ambiguous_evidence_link_citation",
    "unselected_evidence_link_citation",
    "invalid_evidence_link_record",
    "invalid_evidence_link_role",
    "invalid_evidence_link_fields",
    "invalid_evidence_link_field",
    "duplicate_evidence_link_field",
    "unresolved_evidence_link_field",
    "duplicate_evidence_link",
    "missing_supporting_evidence",
    "missing_contradicting_evidence",
    "invalid_requested_hypotheses",
    "duplicate_requested_claim_id",
    "invalid_returned_evidence",
    "duplicate_returned_evidence_ref",
    "invalid_query_history",
    "duplicate_ledger_claim_id",
    "claim_ledger_coverage",
    "duplicate_ledger_evidence_ref",
    "unknown_ledger_evidence_ref",
    "duplicate_ledger_candidate_id",
    "unknown_ledger_candidate_id",
    "duplicate_ledger_attempt_id",
    "unknown_ledger_attempt_id",
    "invalid_remaining_query_budget",
    "query_budget_exhausted",
    "unknown_action_claim_id",
    "tool_action_must_not_have_dispositions",
    "query_action_must_not_have_identifier",
    "exclusive_query_source_required",
    "unknown_action_candidate_id",
    "unknown_action_continuation_id",
    "invalid_materialized_query",
    "get_event_identifier_required",
    "get_event_must_not_request_query",
    "finish_must_not_request_tool",
    "blank_pivot_disposition_reason",
    "duplicate_disposition_attempt_id",
    "unknown_disposition_attempt_id",
    "pending_continuation_cannot_be_tested",
    "tested_pivot_requires_matching_successful_attempt",
    "duplicate_pivot_disposition",
    "unknown_disposition_pivot_id",
    "finish_disposition_coverage",
    "invalid_json",
    "invalid_budget",
    "invalid_path",
    "empty_input",
    "read_error",
    "byte_budget_exceeded",
    "invalid_cloudtrail",
    "event_budget_exceeded",
    "invalid_record",
    "record_budget_exceeded",
    "duplicate_event_id",
    "ambiguous_identifier",
    "invalid_identifier",
    "event_not_found",
    "invalid_query",
    "invalid_tool_input",
}
RESOURCE_ISSUES = {
    "resource_measurements_missing",
    "resource_measurements_not_complete",
    "resource_samples_missing",
    "resource_measurement_errors",
    "foreign_model_observed",
    "ollama_samples_incomplete",
    "process_rss_samples_incomplete",
    "matching_model_samples_missing",
    "resource_sampling_limit_reached",
    "interrupted_attempt_wall_time_unknown",
    "runtime_model_identity_not_verified",
    *("missing_or_invalid_" + key for key in MAXIMA),
}
SECONDARY_CLAIM_ASSESSMENTS = {
    "agree",
    "disagree_outcome",
    "disagree_declared_basis",
    "disagree_evidence_warrant",
    "disagree_availability",
    "disagree_full_source_truth",
    "disagree_emitted_status",
    "disagree_source_checks",
    "disagree_assessment",
    "not_reviewable",
}
SECONDARY_PROSE_ASSESSMENTS = {
    "agree_material_error",
    "agree_minor_wording",
    "agree_minor_error",
    "agree_no_error",
    "agree_no_material_error",
    "disagree_material_severity",
    "disagree_materiality",
    "disagree_error_classification",
    "disagree_source_basis",
    "disagree_no_error",
    "not_reviewable",
}
# Review field names must refer to the frozen synthetic source schema, not a
# reviewer-supplied token that merely resembles a dotted path.
STANDARD_ABSENT_FIELDS = {"errorCode", "errorMessage"}
PUBLIC_FIELD_PATHS = {
    "eventName",
    "eventTime",
    "eventSource",
    "sourceIPAddress",
    "eventID",
    "awsRegion",
    "userIdentity",
    "userIdentity.arn",
    "userIdentity.principalId",
    "userIdentity.type",
    "userIdentity.accessKeyId",
    "userIdentity.userName",
    "userIdentity.accountId",
    "userIdentity.sessionContext",
    "userIdentity.sessionContext.sessionIssuer",
    "userIdentity.sessionContext.sessionIssuer.arn",
    "requestParameters",
    "requestParameters.roleArn",
    "requestParameters.roleName",
    "requestParameters.roleSessionName",
    "requestParameters.maxSessionDuration",
    "requestParameters.durationSeconds",
    "requestParameters.keyId",
    "responseElements",
    "responseElements.credentials",
    "responseElements.credentials.accessKeyId",
    "responseElements.credentials.expiration",
    "responseElements.assumedRoleUser",
    "responseElements.assumedRoleUser.arn",
    "resources",
    *STANDARD_ABSENT_FIELDS,
}
PUBLIC_REVIEW_KEYS = {
    "claims",
    "report_available",
    "material_prose_flag_count",
    "prose_flags_overlapping_fixed_claims",
    "primary_review_sha256",
    "primary_review_row_sha256",
    "claim_review_sha256",
    "primary_material_prose_error_count",
    "adjudicated_material_prose_error_count",
    "prose_adjudications",
}


class SummaryError(ValueError):
    """The summary inputs do not meet the public export contract."""


def require(condition: object, message: str) -> None:
    if not condition:
        raise SummaryError(message)


def canonical(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> tuple[dict, str]:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "An input contains a duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(value):
        raise SummaryError("An input contains a non-finite JSON number")

    content = path.read_bytes()
    value = json.loads(content, object_pairs_hook=unique, parse_constant=invalid_constant)
    require(isinstance(value, dict), "Each summary input must be a JSON object")
    return value, hashlib.sha256(content).hexdigest()


def relative(root: Path, value: str) -> Path:
    require(
        isinstance(value, str) and not Path(value).is_absolute(), "A frozen path is not relative"
    )
    path = (root / value).resolve()
    require(path.is_relative_to(root), "A frozen input path leaves the repository")
    return path


def public_path(root: Path, path: Path) -> str:
    resolved = path.resolve()
    return resolved.relative_to(root).as_posix() if resolved.is_relative_to(root) else path.name


def number(
    value: object, *, upper: float | None = None, integer: bool = False
) -> int | float | None:
    if type(value) not in (int, float) or value < 0:
        return None
    ceiling = 2**63 - 1 if upper is None else upper
    if (integer and type(value) is not int) or value > ceiling or not math.isfinite(value):
        return None
    return value


def public_enum(value: object, allowed: set[str], fallback: str) -> tuple[str, str | None]:
    if isinstance(value, str) and value in allowed:
        return value, None
    return fallback, canonical(value)


def public_bool(value: object) -> bool | None:
    return value if type(value) is bool else None


def public_metrics(values: dict, keys: tuple[str, ...]) -> dict:
    result = {}
    for key in keys:
        value = values[key]
        if key == "process_valid":
            require(type(value) is bool, "A primary process flag is not boolean")
        elif key.endswith(("_rate", "_coverage")):
            require(
                value is None or number(value, upper=1) is not None,
                "A primary rate is outside its numeric bounds",
            )
        else:
            require(
                number(value, upper=50_000, integer=True) is not None,
                "A primary count is outside its integer bounds",
            )
        result[key] = value
    return result


def public_runtime_gate(gate: dict) -> dict:
    result = {
        key: number(gate.get(key))
        for key in (
            "first_ten_wall_seconds",
            "projected_twenty_seconds_with_overhead",
            "projected_forty_seconds_with_overhead",
            "overhead_factor",
            "soft_launch_ceiling_seconds",
        )
    }
    result["max_total_runs"] = (
        gate.get("max_total_runs")
        if type(gate.get("max_total_runs")) is int and gate["max_total_runs"] in (20, 40)
        else None
    )
    result["overall_wall_ceiling_is_soft"] = public_bool(gate.get("overall_wall_ceiling_is_soft"))
    result["foreign_model_observed"] = public_bool(gate.get("foreign_model_observed"))
    issues, hashes = [], []
    raw_issues = gate.get("resource_measurement_issues", [])
    for value in raw_issues if isinstance(raw_issues, list) else [raw_issues]:
        label, digest = public_enum(value, RESOURCE_ISSUES, "other_recorded_resource_issue")
        issues.append(label)
        if digest is not None:
            hashes.append(digest)
    result.update(
        {
            "resource_measurement_issues": issues,
            "redacted_resource_issue_count": len(hashes),
            "redacted_resource_issue_sha256": hashes,
        }
    )
    return result


def source_field_paths(records: list[dict]) -> set[str]:
    paths = set(STANDARD_ABSENT_FIELDS)

    def visit(value, prefix=""):
        if not isinstance(value, dict):
            return
        for key, nested in value.items():
            path = prefix + "." + key if prefix else key
            paths.add(path)
            visit(nested, path)

    for record in records:
        visit(record)
    return paths


def equal_number(actual: object, expected: object) -> bool:
    if type(actual) is bool or type(expected) is bool:
        return type(actual) is type(expected) and actual == expected
    if actual is None or expected is None:
        return actual is expected
    return (
        type(actual) in (int, float)
        and type(expected) in (int, float)
        and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12)
    )


def classification(value: object, allowed: set[str], message: str) -> str | None:
    require(value is None or value in allowed, message)
    return value


def field_refs(
    claim: dict, fixture_hash: str, record_count: int, allowed_fields: set[str] | None = None
) -> list[dict]:
    """Export only immutable references and field names, never typed values."""
    refs: dict[str, set[str]] = {}
    checks = []
    for key in ("source_checks", "full_source_checks", "first_stage_source_checks"):
        checks.extend(claim.get(key, []))
    checks.extend(claim.get("declared_links", []))
    prefix = f"sha256:{fixture_hash}/Records/"
    for check in checks:
        ref = check.get("ref", check.get("citation"))
        require(
            isinstance(ref, str) and ref.startswith(prefix),
            "A review source reference has another fixture identity",
        )
        index = ref[len(prefix) :]
        require(
            index.isdigit() and 0 <= int(index) < record_count,
            "A review source index is outside its frozen fixture",
        )
        fields = refs.setdefault(ref, set())
        for item in check.get("fields", []):
            path = item if isinstance(item, str) else item.get("path", item.get("field"))
            require(
                isinstance(path, str) and len(path) <= 512 and FIELD.fullmatch(path),
                "A review field path is invalid",
            )
            require(
                path in (allowed_fields or PUBLIC_FIELD_PATHS),
                "A review field path is outside the frozen source schema",
            )
            fields.add(path)
    return [{"citation": ref, "fields": sorted(fields)} for ref, fields in sorted(refs.items())]


def report_statuses(run: dict) -> dict[str, str | None]:
    findings = run.get("findings", [])
    if not findings:
        for history in reversed(run.get("model_history", [])):
            if history.get("phase") != "report":
                continue
            try:
                value = json.loads(history.get("output") or "null")
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("findings"), list):
                findings = value["findings"]
            break
    counts = Counter(item.get("claim_id") for item in findings if isinstance(item, dict))
    return {
        item["claim_id"]: item.get("status") if counts[item["claim_id"]] == 1 else None
        for item in findings
        if isinstance(item, dict) and isinstance(item.get("claim_id"), str)
    }


def normalize_claim(claim: dict, case: dict, run: dict) -> dict:
    outcome = OUTCOME_ALIASES.get(claim.get("outcome"), claim.get("outcome"))
    require(outcome in OUTCOMES, "A primary review has an unknown semantic outcome")
    emitted = claim.get("emitted_status")
    if emitted in ("omitted", "unreviewable", "conflicting_duplicate"):
        emitted = None
    classification(emitted, STATUSES, "A primary review emitted-status label is invalid")
    require(
        emitted == report_statuses(run).get(claim["claim_id"]),
        "A review emitted status differs from its stored report",
    )
    availability = claim.get("availability", claim.get("evidence_availability"))
    classification(availability, AVAILABILITY, "A primary review availability label is invalid")
    basis = classification(
        claim.get("declared_basis"), BASIS, "A primary review basis label is invalid"
    )
    warrant = classification(
        claim.get("evidence_warrant"),
        STATUSES | {"unresolved", "unreviewable", "not_assessable"},
        "A primary review evidence-warrant label is invalid",
    )
    full_truth = classification(
        claim.get("full_source_truth"), STATUSES, "A full-source truth label is invalid"
    )
    expected = next(
        a["expected_status"] for a in case["annotations"] if a["claim_id"] == claim["claim_id"]
    )
    require(
        full_truth == expected, "A primary review full-source label differs from the frozen rubric"
    )
    gap = claim.get("gap_type", claim.get("retrieval_gap_subtype"))
    classification(
        gap,
        {"retrieval", "context_delivery", "intrinsic_source", "none"},
        "A primary review gap label is invalid",
    )
    subtype = classification(
        claim.get("unsupported_subtype"),
        {"lucky_full_source_match", "full_source_unresolved", "source_also_unresolved"},
        "A primary review unsupported subtype is invalid",
    )
    return {
        "claim_id": claim["claim_id"],
        "emitted_status": emitted,
        "evidence_warrant": warrant,
        "declared_basis": basis,
        "availability": availability,
        "full_source_truth": full_truth,
        "outcome": outcome,
        "gap_type": gap,
        "unsupported_subtype": subtype,
        "source_references": field_refs(
            claim, case["fixture_sha256"], case["_record_count"], case.get("_field_paths")
        ),
    }


def load_primary_reviews(
    paths: list[Path],
    raw: dict,
    protocol: dict,
    protocol_sha: str,
    raw_sha: str,
    cases: dict,
    root: Path | None = None,
) -> tuple[dict, list[dict], dict]:
    runs = {run["pilot"]["cell"]["cell_id"]: run for run in raw["runs"]}
    reviews, fingerprints, inputs = {}, [], {}
    for path in paths:
        document, digest = read(path)
        inputs[path] = digest
        locked_stages = []
        preserved_stage1_drafts = []
        pins = [
            document[k]
            for k in (
                "frozen_pilot_protocol_sha256",
                "pilot_protocol_sha256",
                "frozen_protocol_sha256",
            )
            if k in document
        ]
        require(
            pins and all(pin == protocol_sha for pin in pins),
            "A review has another pilot protocol identity",
        )
        require(
            document.get("review_protocol_sha256") == protocol["semantic_rubric"]["sha256"],
            "A review has another semantic rubric",
        )
        require(
            document.get("final_batch_sha256") in (None, raw_sha),
            "A review asserts another final raw batch",
        )
        require(
            document.get("additional_inference", False) is False,
            "A primary review reports extra inference",
        )
        for row in document["rows"]:
            cell_id = row["cell_id"]
            require(
                cell_id in runs and cell_id not in reviews,
                "Primary review cells are unknown or duplicated",
            )
            run = runs[cell_id]
            cell = run["pilot"]["cell"]
            require(
                row["cell_result_sha256"] == run["pilot"]["result_sha256"],
                "A primary review is bound to another cell result",
            )
            require(
                row["case_id"] == run["case_id"]
                and row["strategy"] == run["strategy"]
                and row["repeat"] == cell["repeat"],
                "A primary review assignment differs",
            )
            require(
                row["process_status"] == run["status"], "A primary review process status differs"
            )
            require(
                document.get("model", cell["model"]) == cell["model"],
                "A primary review model differs",
            )
            require(
                type(row["report_available"]) is bool,
                "A review must explicitly label report availability",
            )
            drafts = row.get("stage1_draft_history", [])
            require(
                isinstance(drafts, list), "A preserved preliminary draft history must be a list"
            )
            if drafts:
                preserved_stage1_drafts.append(
                    {
                        "cell_id": cell_id,
                        "draft_count": len(drafts),
                        "history_sha256": canonical(drafts),
                    }
                )
            case = cases[run["case_id"]]
            expected = [h["claim_id"] for h in case["hypotheses"]]
            claims = row["claim_reviews"]
            require(
                len(claims) == len(expected) == 4
                and {c["claim_id"] for c in claims} == set(expected),
                "Each primary review needs exactly four unique fixed-claim slots",
            )
            by_claim = {c["claim_id"]: c for c in claims}
            stage = row.get("returned_evidence_stage")
            if "returned_evidence_stage_sha256" in row and stage is not None:
                require(
                    canonical(stage) == row["returned_evidence_stage_sha256"],
                    "A locked first-stage review hash differs",
                )
            if "returned_evidence_stage_path" in row:
                stage_root = root or path.resolve().parent.parent
                stage_path = relative(stage_root, row["returned_evidence_stage_path"])
                stage_document, stage_digest = read(stage_path)
                require(
                    stage_digest == row["returned_evidence_stage_sha256"]
                    and stage_document["cell_id"] == cell_id
                    and stage_document["cell_result_sha256"] == run["pilot"]["result_sha256"],
                    "A separately locked returned-evidence stage differs",
                )
                inputs[stage_path] = stage_digest
                locked_stages.append({"cell_id": cell_id, "sha256": stage_digest})
            normalized = [normalize_claim(by_claim[claim_id], case, run) for claim_id in expected]
            if not row["report_available"]:
                require(
                    all(c["outcome"] == "unreviewable_report" for c in normalized),
                    "An unavailable report must retain four unreviewable slots",
                )
            reviews[cell_id] = {
                "claims": normalized,
                "report_available": row["report_available"],
                "material_prose_flag_count": len(row.get("material_prose_errors", [])),
                "primary_material_prose_error_count": len(row.get("material_prose_errors", [])),
                "adjudicated_material_prose_error_count": len(row.get("material_prose_errors", [])),
                "prose_adjudications": [],
                "_material_prose_quotes": [
                    entry.get("quote") for entry in row.get("material_prose_errors", [])
                ],
                "prose_flags_overlapping_fixed_claims": sum(
                    error.get("duplicate_claim_id") in expected
                    for error in row.get("material_prose_errors", [])
                ),
                "primary_review_sha256": digest,
                "primary_review_row_sha256": canonical(row),
                "claim_review_sha256": {
                    claim_id: canonical(by_claim[claim_id]) for claim_id in expected
                },
            }
        fingerprints.append(
            {
                "path": path,
                "sha256": digest,
                "row_count": len(document["rows"]),
                "separately_locked_stages": locked_stages,
                "preserved_stage1_drafts": preserved_stage1_drafts,
            }
        )
    require(
        set(reviews) == set(runs), "Primary reviews do not cover every attempted cell exactly once"
    )
    return reviews, fingerprints, inputs


def apply_prose_resolutions(
    paths: list[Path], reviews: dict, runs: dict, protocol_sha: str
) -> tuple[list[dict], dict]:
    """Add an explicitly bound assistant-adjudicated view; preserve primary counts."""
    fingerprints, inputs, applied = [], {}, set()
    for path in paths:
        document, digest = read(path)
        inputs[path] = digest
        for key in (
            "pilot_protocol_sha256",
            "frozen_protocol_sha256",
            "frozen_pilot_protocol_sha256",
        ):
            if key in document:
                require(
                    document[key] == protocol_sha, "A prose resolution has another pilot protocol"
                )
        entries = document.get("resolutions", document.get("rows"))
        require(isinstance(entries, list), "A prose resolution document needs an entries list")
        changes = []
        for entry in entries:
            cell_id = entry["cell_id"]
            require(
                cell_id in reviews and cell_id in runs, "A prose resolution has an unknown cell"
            )
            require(
                entry["cell_result_sha256"] == runs[cell_id]["pilot"]["result_sha256"],
                "A prose resolution has another cell result hash",
            )
            index = entry["material_prose_index"]
            require(
                type(index) is int and 0 <= index < len(reviews[cell_id]["_material_prose_quotes"]),
                "A prose resolution flag index is invalid",
            )
            require((cell_id, index) not in applied, "A prose flag has duplicate resolutions")
            require(
                type(entry["adjudicated_material"]) is bool,
                "A prose adjudication must be an explicit boolean",
            )
            quote = reviews[cell_id]["_material_prose_quotes"][index]
            require(
                isinstance(quote, str)
                and isinstance(entry.get("quote"), str)
                and entry["quote"] == quote,
                "A prose resolution quote differs from the exact primary flag",
            )
            applied.add((cell_id, index))
            if not entry["adjudicated_material"]:
                reviews[cell_id]["adjudicated_material_prose_error_count"] -= 1
            binding = {
                "material_prose_index": index,
                "adjudicated_material": entry["adjudicated_material"],
                "resolution_entry_sha256": canonical(entry),
                "resolution_document_sha256": digest,
            }
            reviews[cell_id]["prose_adjudications"].append(binding)
            changes.append({"cell_id": cell_id, **binding})
        fingerprints.append(
            {
                "path": path,
                "sha256": digest,
                "entry_count": len(entries),
                "primary_counts_changed": False,
                "adjudicated_entries": changes,
            }
        )
    return fingerprints, inputs


def sanitize_failures(run: dict) -> list[dict]:
    result = []
    for failure in run.get("failures", []):
        item = {}
        hashes = []
        for key in ("phase", "error_type", "code"):
            value = failure.get(key)
            if value is None and isinstance(failure.get("error"), dict):
                value = failure["error"].get(key)
            if value is not None:
                allowed = {
                    "phase": FAILURE_PHASES,
                    "error_type": FAILURE_TYPES,
                    "code": FAILURE_CODES,
                }[key]
                item[key], digest = public_enum(value, allowed, "other_recorded_" + key)
                if digest is not None:
                    hashes.append({"field": key, "sha256": digest})
        if hashes:
            item["redacted_label_count"] = len(hashes)
            item["redacted_label_sha256"] = hashes
        result.append(item or {"phase": "unspecified"})
    return result


def performance(run: dict) -> dict:
    history = run.get("model_history", [])
    known = Counter()
    token_missing = load_missing = 0
    for call in history:
        usage = call.get("usage_metadata") or {}
        if all(
            number(usage.get(k), upper=2**31 - 1, integer=True) is not None
            for k in ("input_tokens", "output_tokens", "total_tokens")
        ):
            known.update({k: usage[k] for k in ("input_tokens", "output_tokens", "total_tokens")})
        else:
            token_missing += 1
        load = number((call.get("response_metadata") or {}).get("load_duration"), integer=True)
        if load is None:
            load_missing += 1
        else:
            known["load_duration_ns"] += load
    unknown = bool(run.get("inference_calls_unknown"))
    result = {
        "actual_model_calls": None
        if unknown
        else number(run.get("model_calls", 0), upper=4, integer=True),
        "actual_tool_calls": None
        if unknown
        else number(run.get("query_count", 0), upper=3, integer=True),
        "investigation_duration_seconds": number(run.get("duration_seconds")),
        "cell_wall_seconds": number(run["pilot"]["wall_seconds"]),
        "token_metadata_missing_calls": token_missing,
        "load_metadata_missing_calls": load_missing,
        "ollama_reported_load_duration_ns": known["load_duration_ns"]
        if not load_missing and not unknown
        else None,
        "known_ollama_reported_load_duration_ns": known["load_duration_ns"],
    }
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        result[key] = known[key] if not token_missing and not unknown else None
        result["known_" + key] = known[key]
    return result


def content_hash(run: dict) -> str:
    """Exclude runtime UUIDs/timestamps/traces, retaining meaningful query scopes."""
    return canonical(
        {
            "status": run["status"],
            "stop_reason": run.get("stop_reason"),
            "findings": run.get("findings", []),
            "selected_event_refs": run.get("selected_event_refs", []),
            "limitations": run.get("limitations", []),
            "decision_history": run.get("decision_history", []),
            "raw_model_outputs": [
                {key: item.get(key) for key in ("phase", "output", "error_type")}
                for item in run.get("model_history", [])
            ],
            "tools": [
                {"name": item["name"], "args": item["args"], "result": item["result"]}
                for item in run.get("tool_history", [])
            ],
        }
    )


def numeric_row(run: dict, review: dict, keys: tuple[str, ...]) -> dict:
    memory = run.get("model_info", {}).get("resources", {})
    metrics = public_metrics(run["claim_support_metrics"], keys)
    legacy = run["metrics"]
    claims = review["claims"]
    memory_status, memory_status_hash = public_enum(
        memory.get("status", "not_recorded"), MEMORY_STATUSES, "other_recorded_memory_status"
    )
    run_status, run_status_hash = public_enum(
        run["status"], RUN_STATUSES, "other_recorded_run_status"
    )
    return {
        "cell": run["pilot"]["cell"],
        "cell_result_sha256": run["pilot"]["result_sha256"],
        "fixture_sha256": run["fixture_sha256"],
        "status": run_status,
        "redacted_status_sha256": run_status_hash,
        "runtime_model_identity_verified": run.get("pilot_model_identity", {}).get("verified")
        is True,
        "claim_support_metrics": metrics,
        "retrieval": {
            key: number(
                legacy.get(key),
                upper=1 if key in ("relevant_event_precision", "relevant_event_recall") else 50_000,
                integer=key not in ("relevant_event_precision", "relevant_event_recall"),
            )
            for key in (
                "relevant_event_precision",
                "relevant_event_recall",
                "relevant_true_positives",
                "relevant_event_count",
                "selected_event_count",
                "retrieved_event_count",
                "tool_returned_event_count",
            )
        },
        "performance": performance(run),
        "memory": {
            "status": memory_status,
            "redacted_status_sha256": memory_status_hash,
            "sample_count": number(memory.get("sample_count"), upper=1000, integer=True),
            "matching_model_sample_count": number(
                memory.get("matching_model_sample_count"), upper=1000, integer=True
            ),
            "error_count": number(memory.get("error_count"), upper=3000, integer=True),
            "foreign_model_observed": public_bool(memory.get("foreign_model_observed")),
            "sample_limit_reached": public_bool(memory.get("sample_limit_reached")),
            "sampled_maxima": {
                key: number(memory.get("sampled_maxima", {}).get(key), upper=2**60, integer=True)
                for key in MAXIMA
            },
        },
        "failures": sanitize_failures(run),
        "semantic_review": {
            **{key: review[key] for key in PUBLIC_REVIEW_KEYS if key in review},
            "outcome_counts": dict(Counter(c["outcome"] for c in claims)),
            "declared_basis_counts": dict(
                Counter(c["declared_basis"] or "not_recorded" for c in claims)
            ),
        },
        "canonical_report_and_query_content_sha256": content_hash(run),
    }


def numeric_fields(row: dict) -> dict:
    result = {"claim_support." + k: v for k, v in row["claim_support_metrics"].items()}
    result.update({"retrieval." + k: v for k, v in row["retrieval"].items()})
    result.update({"performance." + k: v for k, v in row["performance"].items()})
    result.update({"memory." + k: v for k, v in row["memory"]["sampled_maxima"].items()})
    result["memory.sample_count"] = row["memory"]["sample_count"]
    result["semantic.material_prose_flag_count"] = row["semantic_review"][
        "material_prose_flag_count"
    ]
    result["semantic.primary_material_prose_error_count"] = row["semantic_review"][
        "primary_material_prose_error_count"
    ]
    result["semantic.adjudicated_material_prose_error_count"] = row["semantic_review"][
        "adjudicated_material_prose_error_count"
    ]
    return result


def statistics(values: list) -> dict:
    present = [
        int(v) if type(v) is bool else v
        for v in values
        if type(v) in (bool, int, float) and math.isfinite(v)
    ]
    return {
        "observed_count": len(present),
        "unknown_count": len(values) - len(present),
        "mean": sum(present) / len(present) if present else None,
        "min": min(present) if present else None,
        "max": max(present) if present else None,
    }


def semantic_counts(rows: list[dict]) -> dict:
    counts = Counter(c["outcome"] for r in rows for c in r["semantic_review"]["claims"])
    bases = Counter(
        c["declared_basis"] or "not_recorded" for r in rows for c in r["semantic_review"]["claims"]
    )
    return {
        "attempted_assignments": len(rows),
        "requested_claim_slots": 4 * len(rows),
        "readable_reports": sum(r["semantic_review"]["report_available"] for r in rows),
        "outcome_counts": {key: counts[key] for key in OUTCOMES},
        "declared_basis_counts": dict(bases),
        "runs_with_material_prose_flags": sum(
            r["semantic_review"]["material_prose_flag_count"] > 0 for r in rows
        ),
        "material_prose_flag_count": sum(
            r["semantic_review"]["material_prose_flag_count"] for r in rows
        ),
        "primary_material_prose_error_count": sum(
            r["semantic_review"].get(
                "primary_material_prose_error_count",
                r["semantic_review"]["material_prose_flag_count"],
            )
            for r in rows
        ),
        "adjudicated_material_prose_error_count": sum(
            r["semantic_review"].get(
                "adjudicated_material_prose_error_count",
                r["semantic_review"]["material_prose_flag_count"],
            )
            for r in rows
        ),
        "primary_runs_with_material_prose_errors": sum(
            r["semantic_review"].get(
                "primary_material_prose_error_count",
                r["semantic_review"]["material_prose_flag_count"],
            )
            > 0
            for r in rows
        ),
        "adjudicated_runs_with_material_prose_errors": sum(
            r["semantic_review"].get(
                "adjudicated_material_prose_error_count",
                r["semantic_review"]["material_prose_flag_count"],
            )
            > 0
            for r in rows
        ),
        "emitted_assertion_denominator": None,
    }


def groups_for(rows: list[dict], target: int) -> list[dict]:
    groups = []
    for model, strategy in sorted({(r["cell"]["model"], r["cell"]["strategy"]) for r in rows}):
        members = [
            r for r in rows if r["cell"]["model"] == model and r["cell"]["strategy"] == strategy
        ]
        require(len(members) == target // 10, "A model/method group is incomplete")
        numeric = [numeric_fields(row) for row in members]
        groups.append(
            {
                "model": model,
                "strategy": strategy,
                "status_counts": dict(Counter(r["status"] for r in members)),
                "all_attempts": semantic_counts(members),
                "completed_run_view": semantic_counts(
                    [r for r in members if r["status"] == "completed"]
                ),
                "numeric": {key: statistics([row[key] for row in numeric]) for key in numeric[0]},
            }
        )
    require(len(groups) == 10, "The pilot must contain all ten model/method groups")
    return groups


def pairs_for(rows: list[dict]) -> list[dict]:
    pairs = []
    for model, case_id, repeat in sorted(
        {(r["cell"]["model"], r["cell"]["case_id"], r["cell"]["repeat"]) for r in rows}
    ):
        methods = {
            r["cell"]["strategy"]: r
            for r in rows
            if (r["cell"]["model"], r["cell"]["case_id"], r["cell"]["repeat"])
            == (model, case_id, repeat)
        }
        require(set(methods) == {"adaptive", "fixed"}, "An adaptive/fixed pair is incomplete")
        a, f = (numeric_fields(methods[k]) for k in ("adaptive", "fixed"))
        outcomes = {
            method: Counter(c["outcome"] for c in row["semantic_review"]["claims"])
            for method, row in methods.items()
        }
        pairs.append(
            {
                "model": model,
                "case_id": case_id,
                "repeat": repeat,
                "adaptive_cell": methods["adaptive"]["cell"]["cell_id"],
                "fixed_cell": methods["fixed"]["cell"]["cell_id"],
                "difference": "adaptive-minus-fixed",
                "numeric_differences": {
                    key: (
                        float(a[key]) - float(f[key])
                        if type(a[key]) in (bool, int, float) and type(f[key]) in (bool, int, float)
                        else None
                    )
                    for key in a
                },
                "semantic_outcome_count_differences": {
                    key: outcomes["adaptive"][key] - outcomes["fixed"][key] for key in OUTCOMES
                },
            }
        )
    return pairs


def repeat_agreement(rows: list[dict]) -> list[dict]:
    result = []
    for model, case_id, strategy in sorted(
        {(r["cell"]["model"], r["cell"]["case_id"], r["cell"]["strategy"]) for r in rows}
    ):
        repeated = sorted(
            (
                r
                for r in rows
                if (r["cell"]["model"], r["cell"]["case_id"], r["cell"]["strategy"])
                == (model, case_id, strategy)
            ),
            key=lambda r: r["cell"]["repeat"],
        )
        if len(repeated) == 1:
            continue
        require(len(repeated) == 2, "A repeat comparison needs exactly two assignments")
        first, second = repeated
        claims = [{c["claim_id"]: c for c in r["semantic_review"]["claims"]} for r in repeated]
        result.append(
            {
                "model": model,
                "case_id": case_id,
                "strategy": strategy,
                "cells": [r["cell"]["cell_id"] for r in repeated],
                "canonical_report_and_query_content_equal": first[
                    "canonical_report_and_query_content_sha256"
                ]
                == second["canonical_report_and_query_content_sha256"],
                "requested_claim_slots_per_repeat": 4,
                "emitted_status_agreement_count": sum(
                    claims[0][key]["emitted_status"] == claims[1][key]["emitted_status"]
                    for key in claims[0]
                ),
                "primary_semantic_outcome_agreement_count": sum(
                    claims[0][key]["outcome"] == claims[1][key]["outcome"] for key in claims[0]
                ),
            }
        )
    return result


def secondary_metadata(
    paths: list[Path], primary: dict, runs: dict, protocol_sha: str, rubric_sha: str
) -> tuple[list[dict], dict]:
    result, inputs = [], {}
    for path in paths:
        document, document_sha = read(path)
        inputs[path] = document_sha
        require(
            document.get("frozen_protocol_sha256") == protocol_sha
            and document.get("review_protocol_sha256") == rubric_sha,
            "A secondary review has another frozen identity",
        )
        cells, claims, prose, disagreements = [], 0, 0, 0
        unclassified_hashes = []
        claim_assessments, prose_assessments = Counter(), Counter()
        for row in document["rows"]:
            cell_id = row["cell_id"]
            require(
                cell_id in primary and cell_id not in cells,
                "A secondary review cell is unknown or duplicated",
            )
            require(
                row["cell_result_sha256"] == runs[cell_id]["pilot"]["result_sha256"],
                "A secondary review has another cell result hash",
            )
            cells.append(cell_id)
            expected_claims = {c["claim_id"] for c in primary[cell_id]["claims"]}
            require(
                len(row["claim_reviews"]) == 4
                and {c["claim_id"] for c in row["claim_reviews"]} == expected_claims,
                "A secondary review needs four unique fixed-claim slots",
            )
            if "primary_review_row_sha256" in row:
                require(
                    row["primary_review_row_sha256"]
                    == primary[cell_id]["primary_review_row_sha256"],
                    "A secondary review uses another primary review row",
                )
            for claim in row["claim_reviews"]:
                require(
                    canonical(claim["original_primary_review"])
                    == primary[cell_id]["claim_review_sha256"][claim["claim_id"]],
                    "A secondary review uses another primary claim review",
                )
                value, assessment_sha = public_enum(
                    claim["secondary_assessment"],
                    SECONDARY_CLAIM_ASSESSMENTS,
                    "other_recorded_secondary_claim_assessment",
                )
                if assessment_sha is not None:
                    unclassified_hashes.append(assessment_sha)
                claim_assessments[value] += 1
                claims += 1
                disagreements += value.startswith("disagree_")
            for item in row.get("prose_reviews", []):
                value, assessment_sha = public_enum(
                    item["assessment"],
                    SECONDARY_PROSE_ASSESSMENTS,
                    "other_recorded_secondary_prose_assessment",
                )
                if assessment_sha is not None:
                    unclassified_hashes.append(assessment_sha)
                prose_assessments[value] += 1
                prose += 1
                disagreements += value.startswith("disagree_")
        result.append(
            {
                "path": path,
                "sha256": document_sha,
                "reviewed_cells": sorted(cells),
                "claim_assessment_count": claims,
                "claim_assessments": dict(claim_assessments),
                "prose_assessment_count": prose,
                "prose_assessments": dict(prose_assessments),
                "disagreement_count": disagreements,
                "unclassified_assessment_count": len(unclassified_hashes),
                "redacted_assessment_sha256": unclassified_hashes,
                "primary_counts_changed": False,
            }
        )
    return result, inputs


def build(args: argparse.Namespace) -> tuple[dict, dict]:
    protocol_path = args.protocol.resolve()
    root = protocol_path.parent.parent
    protocol, protocol_sha = read(protocol_path)
    raw, raw_sha = read(args.raw)
    sdk, sdk_sha = read(args.sdk)
    verification, verification_sha = read(args.verification)
    inputs = {
        protocol_path: protocol_sha,
        args.raw: raw_sha,
        args.sdk: sdk_sha,
        args.verification: verification_sha,
    }
    require(protocol["protocol_id"] == raw["pilot_id"] == PILOT_ID, "Pilot identity differs")
    keys = tuple(protocol["evaluation"]["numeric_metric_keys"])
    require(keys == NUMERIC_KEYS, "The frozen 21-counter contract differs")
    target = raw.get("target_runs")
    require(type(target) is int and target in (20, 40), "The pilot has no final 20/40-cell target")
    require(
        len(raw["runs"]) == target and raw["runtime_gate"]["max_total_runs"] == target,
        "Every target assignment must be attempted before public export",
    )
    require(
        raw["plan"] == protocol["cell_plan"]
        and raw["frozen_identity"]["protocol_sha256"] == protocol_sha,
        "The raw frozen plan identity differs",
    )
    require(raw["test_only"] is False, "Test-only batches cannot be published")
    require(
        verification["status"] == "verified"
        and verification["finished_attempts"] == verification["attempts_recorded"] == target
        and not verification["in_flight"],
        "A complete independent verification is required",
    )
    require(
        verification["protocol_sha256"] == protocol_sha
        and verification["raw_source"]["sha256"] == raw_sha,
        "Independent verification refers to another source snapshot",
    )
    require(
        verification["sdk"]["status"] == "verified" and verification["sdk"]["sha256"] == sdk_sha,
        "Independent verification has not checked this exact SDK replay",
    )
    require(
        sdk["source_results_sha256"] == raw_sha
        and sdk["status"] == "completed"
        and sdk["upload_results"] is False
        and sdk["inference_rerun"] is False,
        "The local SDK replay identity or scope differs",
    )
    for source, key in (
        (args.verifier_source, "verifier_sha256"),
        (args.reused_verifier_source, "reused_verifier_sha256"),
    ):
        expected = verification[key]
        require(
            SHA.fullmatch(expected) and sha(source) == expected,
            "An independent verifier source hash differs",
        )
        inputs[source] = expected
    for name, expected in protocol["source_sha256"].items():
        source = relative(root, name)
        require(sha(source) == expected, "A frozen source changed after verification")
        inputs[source] = expected
    manifest_path = relative(root, protocol["case_manifest"]["path"])
    manifest, manifest_sha = read(manifest_path)
    require(
        manifest_sha == raw["case_manifest_sha256"] == protocol["case_manifest"]["sha256"],
        "The case manifest identity differs",
    )
    inputs[manifest_path] = manifest_sha
    cases = {c["id"]: c for c in manifest["cases"] if c["id"] in protocol["pilot"]["case_ids"]}
    require(
        len(cases) == 2 and all(c["split"] == "development" for c in cases.values()),
        "This exporter only covers the two exposed development cases",
    )
    for case in cases.values():
        source = relative(root, case["fixture"])
        payload, fixture_sha = read(source)
        require(fixture_sha == case["fixture_sha256"], "A frozen source fixture differs")
        case["_record_count"] = len(payload["Records"])
        case["_field_paths"] = source_field_paths(payload["Records"])
        inputs[source] = fixture_sha
    checked = {r["result_index"]: r for r in verification["rows"]}
    evaluated = {r["inputs"]["result_index"]: r for r in sdk["evaluated_runs"]}
    require(
        len(checked)
        == len(verification["rows"])
        == len(evaluated)
        == len(sdk["evaluated_runs"])
        == target
        and set(checked) == set(evaluated) == set(range(target)),
        "Verification or SDK rows are missing or duplicated",
    )
    for index, run in enumerate(raw["runs"]):
        cell = protocol["cell_plan"][index]
        require(
            run["pilot"]["cell"] == cell
            and run["test_only"] is False
            and run["status"] != "running",
            "The result set has a wrong assignment or unfinished/test-only attempt",
        )
        require(
            run["pilot"]["result_sha256"]
            == canonical({k: v for k, v in run.items() if k != "pilot"}),
            "A raw result payload hash differs",
        )
        require(
            checked[index]["verified"] is True
            and checked[index]["cell"] == cell
            and all(checked[index]["checks"].values()),
            "An independent cell verification failed",
        )
        for key in keys:
            require(
                equal_number(
                    run["claim_support_metrics"][key],
                    checked[index]["independent_support"]["numeric"][key],
                ),
                "A copied primary counter differs from the independent audit",
            )
        replay = evaluated[index]
        require(
            canonical(replay["sdk_evaluation_trace"]["outputs"]) == canonical({"result": run}),
            "The SDK replay contains another stored output",
        )
        expected_feedback = {
            "claim_support_v1__" + key: run["claim_support_metrics"][key] for key in keys
        }
        require(len(replay["sdk_feedback"]) == 21, "The SDK numeric feedback count differs")
        actual_feedback = {f["key"]: f["score"] for f in replay["sdk_feedback"]}
        require(
            set(actual_feedback) == set(expected_feedback)
            and all(
                equal_number(actual_feedback[key], value)
                or (type(value) is bool and actual_feedback[key] in (int(value), float(value)))
                for key, value in expected_feedback.items()
            ),
            "The SDK feedback differs from the copied numeric counters",
        )
    reviews, review_fingerprints, review_inputs = load_primary_reviews(
        args.reviews, raw, protocol, protocol_sha, raw_sha, cases, root
    )
    inputs.update(review_inputs)
    run_map = {r["pilot"]["cell"]["cell_id"]: r for r in raw["runs"]}
    resolutions, resolution_inputs = apply_prose_resolutions(
        args.resolutions, reviews, run_map, protocol_sha
    )
    inputs.update(resolution_inputs)
    rows = [numeric_row(run, reviews[run["pilot"]["cell"]["cell_id"]], keys) for run in raw["runs"]]
    secondary, secondary_inputs = secondary_metadata(
        args.secondary_reviews,
        reviews,
        run_map,
        protocol_sha,
        protocol["semantic_rubric"]["sha256"],
    )
    inputs.update(secondary_inputs)
    for item in review_fingerprints + secondary + resolutions:
        item["path"] = public_path(root, item["path"])
    output = {
        "schema_version": "1",
        "pilot_id": PILOT_ID,
        "created_at": datetime.now(UTC).isoformat(),
        "purpose": "Verified numeric description of two exposed synthetic development cases",
        "source_fingerprints": {
            "raw": {"path": public_path(root, args.raw), "sha256": raw_sha},
            "protocol": {"path": public_path(root, protocol_path), "sha256": protocol_sha},
            "sdk_stored_output_replay": {"path": public_path(root, args.sdk), "sha256": sdk_sha},
            "independent_verification": {
                "path": public_path(root, args.verification),
                "sha256": verification_sha,
            },
            "independent_verifier_source_sha256": verification["verifier_sha256"],
            "reused_verifier_source_sha256": verification["reused_verifier_sha256"],
            "primary_reviews": review_fingerprints,
            "secondary_reviews": secondary,
            "review_resolutions": resolutions,
            "summary_exporter_source_sha256": sha(Path(__file__)),
        },
        "scope": {
            "attempted_assignments": target,
            "case_clusters": 2,
            "requested_claim_slots": 4 * target,
            "repeats": target // 20,
            "all_attempts_retained": True,
            "new_inference_calls_for_summary": 0,
            "new_sdk_evaluations_for_summary": 0,
            "hosted_uploads": False,
        },
        "runtime_gate": public_runtime_gate(raw["runtime_gate"]),
        "numeric_metric_keys": list(keys),
        "review_counts_label": (
            "Unchanged primary assistant classifications and explicitly bound "
            "assistant-adjudicated prose counts are separate; secondary disagreements are retained"
        ),
        "all_attempts": semantic_counts(rows),
        "completed_run_view": semantic_counts([r for r in rows if r["status"] == "completed"]),
        "groups": groups_for(rows, target),
        "paired_adaptive_minus_fixed": pairs_for(rows),
        "repeat_content_agreement": repeat_agreement(rows),
        "rows": rows,
        "limitations": [
            "Both synthetic cases and previous outputs were exposed development data; "
            "there are only two case clusters.",
            "Assistant reviews were source-aware and not blinded or independent human validation.",
            "Preserved preliminary drafts and the documented review order correction require "
            "reading the review limitations in docs/model-pilot-results.md.",
            "No confidence intervals, significance tests, intelligence claims, size trends, "
            "model winner, or generalization claim are supported.",
            "All requested claim slots remain in the denominator, including invalid, failed, "
            "omitted and unreviewable reports.",
            "The completed-run view is conditional and has a smaller denominator; "
            "it does not replace all-attempt results.",
            "Mechanical field support and assistant semantic classifications "
            "are distinct measurements.",
            "Prose flags are counts, without an emitted-assertion denominator "
            "or an implied prose error rate.",
            "Memory values are sampled accounting/RSS maxima, not OS peaks, "
            "and overlapping metrics must not be added.",
            "Ollama load_duration is per-request reported nanoseconds; "
            "wall-minus-investigation time is not pure loading time.",
            "Same-seed repeats describe execution stability, not independent task samples.",
            "Repeat content hashes exclude runtime identifiers, timestamps and traces; "
            "log times and query scopes remain meaningful content.",
            "Assistant-adjudicated prose counts apply only explicit cell/hash/index/quote/boolean "
            "resolutions; unchanged primary counts and secondary disagreements are retained.",
            "Adjudication is an assistant judgment, not independent human truth validation.",
        ],
    }
    return output, inputs


def write_exclusive(path: Path, document: dict) -> None:
    require(not path.exists() and not path.is_symlink(), "The summary destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tracetrail-summary-", suffix=".json", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--raw", type=Path, required=True)
    result.add_argument("--protocol", type=Path, required=True)
    result.add_argument("--sdk", type=Path, required=True)
    result.add_argument("--verification", type=Path, required=True)
    result.add_argument("--reviews", type=Path, nargs="+", required=True)
    result.add_argument("--secondary-reviews", type=Path, nargs="*", default=[])
    result.add_argument("--resolutions", type=Path, nargs="*", default=[])
    result.add_argument(
        "--verifier-source",
        type=Path,
        default=Path(__file__).with_name("verify_model_pilot_v1.py"),
    )
    result.add_argument(
        "--reused-verifier-source",
        type=Path,
        default=Path(__file__).with_name("_v8_evaluation_contract.py"),
    )
    result.add_argument("--output", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        document, inputs = build(args)
        output = args.output.resolve()
        root = args.protocol.resolve().parent.parent
        require(
            output.is_relative_to(root / "evaluation"),
            "Public summaries must stay under evaluation",
        )
        require(
            output not in {path.resolve() for path in inputs}, "The summary would replace an input"
        )
        for path, expected in inputs.items():
            require(sha(path) == expected, "An input changed during summary construction")
        write_exclusive(output, document)
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f"Pilot summary refused: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "path": str(output),
                "sha256": sha(output),
                "attempted_assignments": document["scope"]["attempted_assignments"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
