"""Bounded model planning choices and explicit dispositions, without tool calls."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tracetrail.store import Query

_Id = Annotated[str, Field(min_length=1, max_length=100)]
_Reference = Annotated[str, Field(min_length=1, max_length=512)]
_CANDIDATE_QUERY_LIMIT = 20


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClaimPlan(StrictModel):
    claim_id: _Id
    evidence_refs: list[_Reference] = Field(max_length=6)
    open_question: str = Field(max_length=300)
    candidate_ids: list[_Id] = Field(max_length=4)
    attempt_ids: list[_Id] = Field(max_length=4)


class PivotDisposition(StrictModel):
    pivot_ids: list[_Id] = Field(min_length=1, max_length=20)
    disposition: Literal["deferred", "not_relevant", "tested_under_recorded_scope"]
    reason: str = Field(min_length=1, max_length=300)
    attempt_ids: list[_Id] = Field(max_length=20)


class Decision(StrictModel):
    ledger: list[ClaimPlan] = Field(max_length=12)
    action: Literal["query_events", "get_event", "finish"]
    rationale: str = Field(max_length=1000)
    claim_id: str = Field(max_length=100)
    candidate_id: _Id | None
    continuation_id: _Id | None
    query: Query | None
    identifier: Annotated[str, Field(min_length=1, max_length=4096)] | None
    dispositions: list[PivotDisposition] = Field(max_length=20)


def _decision(decision: dict | Decision) -> Decision:
    # Revalidate models too: model_copy/model_construct can bypass Pydantic bounds.
    value = decision.model_dump() if isinstance(decision, Decision) else decision
    return Decision.model_validate(value)


def _catalog(coverage: dict) -> tuple[dict, dict]:
    if not isinstance(coverage, dict):
        raise ValueError("Invalid planning catalog")
    result = []
    all_ids = set()
    for name in ("candidates", "continuations"):
        entries = coverage.get(name, [])
        if not isinstance(entries, list):
            raise ValueError("Invalid planning catalog")
        by_id = {}
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("id"), str)
                or not entry["id"].strip()
                or entry["id"] in all_ids
                or not isinstance(entry.get("query"), dict)
            ):
                raise ValueError("Invalid planning catalog")
            all_ids.add(entry["id"])
            by_id[entry["id"]] = entry
        result.append(by_id)
    return result[0], result[1]


def materialize_query(decision: dict | Decision, coverage: dict) -> Query:
    """Materialize exactly one model choice; never choose a replacement search.

    A candidate uses its observed filter with the frozen limit of 20. A
    continuation preserves its actual earlier query scope and page limit.
    A custom query retains the model's validated Query fields.
    """
    chosen = _decision(decision)
    if chosen.action != "query_events" or chosen.identifier is not None or chosen.dispositions:
        raise ValueError("The decision is not an exclusive query action")
    if (
        sum(
            value is not None
            for value in (chosen.candidate_id, chosen.continuation_id, chosen.query)
        )
        != 1
    ):
        raise ValueError("Choose exactly one query source")
    candidates, continuations = _catalog(coverage)
    if chosen.candidate_id is not None:
        if chosen.candidate_id not in candidates:
            raise ValueError("Unknown planning candidate")
        return Query.model_validate(
            {**candidates[chosen.candidate_id]["query"], "limit": _CANDIDATE_QUERY_LIMIT}
        )
    if chosen.continuation_id is not None:
        if chosen.continuation_id not in continuations:
            raise ValueError("Unknown planning continuation")
        return Query.model_validate(continuations[chosen.continuation_id]["query"])
    assert chosen.query is not None
    return Query.model_validate(chosen.query.model_dump())


def _successful_attempt(entry: dict) -> bool:
    output = entry.get("result")
    if not (
        isinstance(entry.get("args"), dict)
        and isinstance(output, dict)
        and "error" not in output
        and type(output.get("matched")) is int
        and output["matched"] >= 0
        and type(output.get("truncated")) is bool
        and (
            isinstance(output.get("records"), list)
            or isinstance(output.get("returned_citations"), list)
        )
    ):
        return False
    try:
        Query.model_validate(entry["args"])
    except ValidationError:
        return False
    return True


def _duplicates(values: list[str]) -> bool:
    return len(values) != len(set(values))


def validate_decision(
    decision: dict | Decision,
    evidence: list[dict],
    history: list[dict],
    hypotheses: list[dict],
    remaining_queries: int,
    coverage: dict,
) -> list[str]:
    """Validate planning references and accounting, without semantic judgments.

    ``tested_under_recorded_scope`` requires an actual successful query that
    used each candidate's filter. Additional filters and time bounds remain in
    history; this disposition never means comprehensive investigation.
    """
    try:
        chosen = _decision(decision)
    except (ValidationError, TypeError, ValueError):
        return ["invalid_decision_shape"]
    try:
        candidates, continuations = _catalog(coverage)
    except ValueError:
        return ["invalid_planning_catalog"]
    errors = []
    if not isinstance(hypotheses, list) or any(
        not isinstance(item, dict)
        or not isinstance(item.get("claim_id"), str)
        or not item["claim_id"].strip()
        for item in hypotheses
    ):
        errors.append("invalid_requested_hypotheses")
        requested = []
    else:
        requested = [item["claim_id"] for item in hypotheses]
        if _duplicates(requested):
            errors.append("duplicate_requested_claim_id")
    known_claims = set(requested)
    known_refs = set()
    if not isinstance(evidence, list):
        errors.append("invalid_returned_evidence")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
                errors.append("invalid_returned_evidence")
            elif item["ref"] in known_refs:
                errors.append("duplicate_returned_evidence_ref")
            else:
                known_refs.add(item["ref"])
    if not isinstance(history, list):
        errors.append("invalid_query_history")
        attempts = {}
    else:
        attempts = {
            f"Q{index}": entry
            for index, entry in enumerate(history)
            if isinstance(entry, dict) and entry.get("name") == "query_events"
        }
    ledger_claims = [entry.claim_id for entry in chosen.ledger]
    if _duplicates(ledger_claims):
        errors.append("duplicate_ledger_claim_id")
    if set(ledger_claims) != known_claims:
        errors.append("claim_ledger_coverage")
    for entry in chosen.ledger:
        for values, known, duplicate_code, unknown_code in (
            (
                entry.evidence_refs,
                known_refs,
                "duplicate_ledger_evidence_ref",
                "unknown_ledger_evidence_ref",
            ),
            (
                entry.candidate_ids,
                candidates,
                "duplicate_ledger_candidate_id",
                "unknown_ledger_candidate_id",
            ),
            (
                entry.attempt_ids,
                attempts,
                "duplicate_ledger_attempt_id",
                "unknown_ledger_attempt_id",
            ),
        ):
            if _duplicates(values):
                errors.append(duplicate_code)
            if any(value not in known for value in values):
                errors.append(unknown_code)
    valid_budget = type(remaining_queries) is int and remaining_queries >= 0
    if not valid_budget:
        errors.append("invalid_remaining_query_budget")
    if chosen.action in ("query_events", "get_event"):
        if not valid_budget or remaining_queries <= 0:
            errors.append("query_budget_exhausted")
        if chosen.claim_id not in known_claims:
            errors.append("unknown_action_claim_id")
        if chosen.dispositions:
            errors.append("tool_action_must_not_have_dispositions")
    if chosen.action == "query_events":
        if chosen.identifier is not None:
            errors.append("query_action_must_not_have_identifier")
        if (
            sum(
                value is not None
                for value in (chosen.candidate_id, chosen.continuation_id, chosen.query)
            )
            != 1
        ):
            errors.append("exclusive_query_source_required")
        if chosen.candidate_id is not None and chosen.candidate_id not in candidates:
            errors.append("unknown_action_candidate_id")
        if chosen.continuation_id is not None and chosen.continuation_id not in continuations:
            errors.append("unknown_action_continuation_id")
        if not errors:
            try:
                materialize_query(chosen, coverage)
            except (ValidationError, ValueError):
                errors.append("invalid_materialized_query")
    elif chosen.action == "get_event":
        if chosen.identifier is None or not chosen.identifier.strip():
            errors.append("get_event_identifier_required")
        if any(
            value is not None
            for value in (chosen.candidate_id, chosen.continuation_id, chosen.query)
        ):
            errors.append("get_event_must_not_request_query")
    else:
        if any(
            value is not None
            for value in (
                chosen.candidate_id,
                chosen.continuation_id,
                chosen.query,
                chosen.identifier,
            )
        ):
            errors.append("finish_must_not_request_tool")
        visible = set(candidates) | set(continuations)
        disposed = []
        for disposition in chosen.dispositions:
            disposed.extend(disposition.pivot_ids)
            if not disposition.reason.strip():
                errors.append("blank_pivot_disposition_reason")
            if _duplicates(disposition.attempt_ids):
                errors.append("duplicate_disposition_attempt_id")
            if any(attempt_id not in attempts for attempt_id in disposition.attempt_ids):
                errors.append("unknown_disposition_attempt_id")
            if disposition.disposition == "tested_under_recorded_scope":
                for pivot_id in disposition.pivot_ids:
                    if pivot_id in continuations:
                        errors.append("pending_continuation_cannot_be_tested")
                        continue
                    if pivot_id not in candidates:
                        continue
                    query = candidates[pivot_id]["query"]
                    if not any(
                        attempt_id in attempts
                        and _successful_attempt(attempts[attempt_id])
                        and all(
                            attempts[attempt_id]["args"].get(field) == value
                            for field, value in query.items()
                        )
                        for attempt_id in disposition.attempt_ids
                    ):
                        errors.append("tested_pivot_requires_matching_successful_attempt")
        if _duplicates(disposed):
            errors.append("duplicate_pivot_disposition")
        if any(pivot_id not in visible for pivot_id in disposed):
            errors.append("unknown_disposition_pivot_id")
        if set(disposed) != visible:
            errors.append("finish_disposition_coverage")
    return list(dict.fromkeys(errors))
