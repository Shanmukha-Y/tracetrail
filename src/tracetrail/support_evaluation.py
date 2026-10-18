"""Versioned claim-local annotation support, without model or network calls.

Only a finding's own explicit field links can supply its required atoms. Values
are checked in exact returned source records, never borrowed from the global
observation projection. This measures a frozen annotation contract, not whether
free text, evidence roles, relevance judgments, or conclusions are semantically
true. Raw report measurements and process-valid primary credit are separate.

The historical ``evaluation.score_run`` and its SDK feedback remain unchanged.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from tracetrail.claims import finding_citations, validate_finding_links

SCORER_ID = "claim-support-v1"
NUMERIC_METRIC_KEYS = (
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
# Both names are explicit allowlists, rather than discovery of numeric diagnostics.
NUMERIC_METRICS = NUMERIC_METRIC_KEYS
_MISSING = object()
_STRUCTURAL_FAILURE_PHASES = {"plan", "planning_validation", "validation", "report", "runner"}


def scorer_source_sha256() -> str:
    """Fingerprint this definition; freeze its dependency hashes in the protocol too."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def scorer_fingerprint() -> dict[str, str]:
    return {"scorer_id": SCORER_ID, "source_sha256": scorer_source_sha256()}


def _dict(value: Any) -> dict:
    if isinstance(value, Mapping):
        return dict(value)
    if callable(getattr(value, "model_dump", None)):
        return value.model_dump(mode="json")
    return {}


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _same(left: Any, right: Any) -> bool:
    """Preserve JSON types, including bool versus int and int versus float."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float) and not math.isfinite(left):
        return False
    return bool(left == right)


def _field(record: dict, path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _statement(value: Any) -> str:
    # Runtime preserves the supplied statement exactly; even whitespace edits
    # must not earn this newer contract's fixed-statement support.
    return value if isinstance(value, str) else ""


def _tool_failed(entry: dict, response: dict) -> bool:
    return bool(
        entry.get("error")
        or entry.get("status") == "error"
        or response.get("error")
        or response.get("ok") is False
        or response.get("status") == "error"
    )


def _returned_evidence(case: Mapping, result: dict) -> tuple[dict, int]:
    """Require file/index identity, event ID, typed record identity and actual return."""
    records = case.get("_fixture_records")
    if not isinstance(records, list) or not records:
        raise ValueError("Use a case loaded with immutable fixture records")
    if any(not isinstance(r, dict) or not isinstance(r.get("eventID"), str) for r in records):
        raise ValueError("Invalid immutable fixture records")
    if len({r["eventID"] for r in records}) != len(records):
        raise ValueError("Fixture event IDs must be unique")
    source = {
        f"sha256:{case['fixture_sha256']}/Records/{index}": record
        for index, record in enumerate(records)
    }
    event_refs = {record["eventID"]: ref for ref, record in source.items()}
    if case.get("seed_event_id") not in event_refs:
        raise ValueError("Unknown fixture seed")
    returned = {event_refs[case["seed_event_id"]]}
    for raw in _list(result.get("tool_history")):
        entry = _dict(raw)
        response = _dict(entry.get("result"))
        if entry.get("name") not in {"query_events", "get_event"} or _tool_failed(entry, response):
            continue
        items = _list(response["records"]) if "records" in response else [response]
        for raw_item in items:
            item = _dict(raw_item)
            ref = item.get("ref")
            expected = source.get(ref) if isinstance(ref, str) else None
            if (
                expected is not None
                and item.get("event_id") == expected["eventID"]
                and _same(item.get("record"), expected)
            ):
                returned.add(ref)
    evidence = [_dict(item) for item in _list(result.get("evidence"))]
    counts = Counter(e.get("ref") for e in evidence if isinstance(e.get("ref"), str))
    valid = {}
    invalid = 0
    for item in evidence:
        ref = item.get("ref")
        expected = source.get(ref) if isinstance(ref, str) else None
        if (
            expected is not None
            and counts[ref] == 1
            and ref in returned
            and item.get("event_id") == expected["eventID"]
            and _same(item.get("record"), expected)
        ):
            valid[ref] = item
        else:
            invalid += 1
    return valid, invalid


def _link_atoms(finding: dict, evidence: list[dict], selected: list[str]) -> tuple[set, int]:
    """Count valid explicit declarations; duplicates cannot inflate atom coverage."""
    links = finding.get("evidence_links")
    if not isinstance(links, list) or len(links) > 6:
        return set(), 1
    atoms = set()
    seen = set()
    invalid = 0
    for link in links:
        probe = {
            "claim_id": finding.get("claim_id"),
            "status": "uncertain",
            "rationale": "Structural field-link check only.",
            "missing_evidence": ["This check does not judge claim meaning."],
            "evidence_links": [link],
        }
        if validate_finding_links(probe, evidence, selected):
            invalid += 1
            continue
        signature = (link["citation"], link["role"], tuple(sorted(link["fields"])))
        if signature in seen:
            invalid += 1
            continue
        seen.add(signature)
        atoms.update((link["citation"], field) for field in link["fields"])
    return atoms, invalid


def score_claim_support(case: Mapping[str, Any], result: Any) -> dict[str, Any]:
    """Score fixed claims from their corresponding model-authored field links.

    Atom coverage requires a unique, unchanged fixed claim, its own exact link,
    selected genuinely returned source identity, and the annotated typed value
    and presence. Status correctness is an additional whole-claim requirement.
    Source values are checked, not claimed to have been written by the model.

    Global ``observations`` are deliberately never consulted. Invalid process
    rows retain raw report measurements and all expected denominators, while
    process-valid primary numerators become zero. This does not execute or
    repair queries, findings, citations, statuses, or projected facts.

    The process gate checks completed status, recorded structural failures and
    the report references checked here. It does not rerun planning validation;
    the frozen protocol audit verifies actual decisions and tool scopes.
    """
    result = _dict(result)
    annotations = case.get("annotations")
    hypotheses = case.get("hypotheses")
    if not isinstance(annotations, list) or not annotations or not isinstance(hypotheses, list):
        raise ValueError("Fixed hypotheses and annotations are required")
    annotation_ids = [a["claim_id"] for a in annotations]
    statements = {h["claim_id"]: _statement(h["statement"]) for h in hypotheses}
    if len(set(annotation_ids)) != len(annotation_ids) or set(annotation_ids) != set(statements):
        raise ValueError("Every fixed claim needs one annotation")
    valid, invalid_evidence = _returned_evidence(case, result)
    event_refs = {
        record["eventID"]: f"sha256:{case['fixture_sha256']}/Records/{index}"
        for index, record in enumerate(case["_fixture_records"])
    }
    selected_items = result.get("selected_event_refs")
    selected = [v for v in _list(selected_items) if isinstance(v, str)]
    valid_selected = [ref for ref in selected if ref in valid]
    selection_valid = (
        isinstance(selected_items, list)
        and len(selected) == len(selected_items) == len(set(selected))
        and len(valid_selected) == len(selected)
    )
    evidence = list(valid.values())
    findings = [_dict(f) for f in _list(result.get("findings"))]
    counts = Counter(f.get("claim_id") for f in findings if isinstance(f.get("claim_id"), str))
    unexpected = sum(
        not isinstance(f.get("claim_id"), str) or f["claim_id"] not in statements for f in findings
    )
    duplicates = sum(n - 1 for claim, n in counts.items() if claim in statements and n > 1)
    missing = [claim for claim in annotation_ids if counts[claim] == 0]
    structural_reasons = []
    if not selection_valid:
        structural_reasons.append("invalid_selection")
    if invalid_evidence:
        structural_reasons.append("invalid_evidence")
    if unexpected or duplicates or missing:
        structural_reasons.append("claim_coverage")
    per_claim = []
    raw_supported = raw_covered = required_total = correct_status = invalid_links = 0
    extra_atoms = extra_citations = 0
    for annotation in annotations:
        claim = annotation["claim_id"]
        matches = [f for f in findings if f.get("claim_id") == claim]
        finding = matches[0] if len(matches) == 1 else None
        reasons = []
        if finding is None:
            reasons.append("missing_claim" if not matches else "duplicate_claim")
        statement_matches = (
            finding is not None and _statement(finding.get("statement")) == (statements[claim])
        )
        status_matches = (
            finding is not None and finding.get("status") == annotation["expected_status"]
        )
        if finding is not None and not statement_matches:
            reasons.append("statement_mismatch")
            structural_reasons.append("changed_statement")
        if finding is not None and not status_matches:
            reasons.append("status_mismatch")
        correct_status += bool(statement_matches and status_matches)
        atoms, link_count = _link_atoms(finding or {}, evidence, valid_selected)
        invalid_links += link_count if finding is not None else 0
        link_errors = (
            validate_finding_links(finding, evidence, valid_selected) if finding is not None else []
        )
        citations = finding_citations(finding or {})
        citations_exact = finding is not None and finding.get("citations") == citations
        if link_errors:
            reasons.append("invalid_finding_links")
            structural_reasons.append("invalid_finding_links")
        if finding is not None and not citations_exact:
            reasons.append("citations_not_derived_from_links")
            structural_reasons.append("citations_not_derived_from_links")
        required_refs = {event_refs[e] for e in annotation["required_event_ids"]}
        missing_refs = required_refs - set(citations)
        if missing_refs:
            reasons.append("missing_required_citation")
        expected_atoms = {}
        for expected in annotation["required_observations"]:
            key = (event_refs[expected["event_id"]], expected["field"])
            previous = expected_atoms.get(key)
            if previous is not None and not _same(previous, expected):
                raise ValueError("Conflicting required atom annotations")
            expected_atoms[key] = expected
        extra_atoms += len(atoms - expected_atoms.keys()) if statement_matches else 0
        extra_citations += len(set(citations) - required_refs) if finding is not None else 0
        atom_results = []
        covered = 0
        for (ref, field), expected in expected_atoms.items():
            actual = _field(valid[ref]["record"], field) if ref in valid else _MISSING
            present = expected.get("present", True)
            source_matches = (
                ref in valid
                and type(present) is bool
                and (
                    (
                        present
                        and actual is not _MISSING
                        and _same(actual, expected.get("value", _MISSING))
                    )
                    or (
                        not present
                        and actual is _MISSING
                        and expected.get("value", _MISSING) is None
                    )
                )
            )
            linked = (ref, field) in atoms and ref in valid_selected and ref in citations
            matched = bool(statement_matches and citations_exact and linked and source_matches)
            covered += matched
            atom_results.append(
                {
                    "citation": ref,
                    "field": field,
                    "present": present,
                    "linked": linked,
                    "source_matches": bool(source_matches),
                    "covered": matched,
                }
            )
        if covered != len(expected_atoms):
            reasons.append("missing_or_wrong_claim_field_support")
        supported = not reasons
        raw_supported += supported
        raw_covered += covered
        required_total += len(expected_atoms)
        per_claim.append(
            {
                "claim_id": claim,
                "reasons": reasons,
                "raw_supported": supported,
                "required_atom_count": len(expected_atoms),
                "raw_covered_atom_count": covered,
                "missing_required_citations": sorted(missing_refs),
                "link_errors": link_errors,
                "atoms": atom_results,
            }
        )
    failures = result.get("failures", [])
    recorded_structural_failure = not isinstance(failures, list) or any(
        not isinstance(_dict(f).get("phase"), str)
        or _dict(f)["phase"] in _STRUCTURAL_FAILURE_PHASES
        for f in _list(failures)
    )
    process_valid = (
        result.get("status") == "completed"
        and not recorded_structural_failure
        and not structural_reasons
    )
    expected_count = len(annotations)
    return {
        "scorer_id": SCORER_ID,
        "annotated_claim_count": expected_count,
        "finding_count": len(findings),
        "raw_supported_claim_count": raw_supported,
        "raw_supported_claim_rate": raw_supported / expected_count,
        "process_valid_supported_claim_count": raw_supported if process_valid else 0,
        "process_valid_supported_claim_rate": raw_supported / expected_count
        if process_valid
        else 0.0,
        "required_atom_count": required_total,
        "raw_covered_atom_count": raw_covered,
        "raw_required_atom_coverage": raw_covered / required_total if required_total else None,
        "process_valid_covered_atom_count": raw_covered if process_valid else 0,
        "process_valid_required_atom_coverage": (
            raw_covered / required_total if process_valid else 0.0
        )
        if required_total
        else None,
        "correct_status_count": correct_status,
        "correct_status_rate": correct_status / expected_count,
        "process_valid": process_valid,
        "invalid_evidence_count": invalid_evidence,
        "invalid_link_count": invalid_links,
        "extra_declared_atom_count": extra_atoms,
        "extra_citation_count": extra_citations,
        "unexpected_finding_count": unexpected,
        "duplicate_claim_count": duplicates,
        "missing_claim_count": len(missing),
        "process_invalid_reasons": sorted(set(structural_reasons)),
        "recorded_structural_failure": recorded_structural_failure,
        "per_claim": per_claim,
        "semantic_entailment_verified": False,
        "observation_projection_used_for_support": False,
    }
