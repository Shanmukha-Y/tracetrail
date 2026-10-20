"""Pure planning-contract tests with constructed data, never model evidence."""

import socket
from copy import deepcopy

import pytest

from tracetrail.planning import validate_decision
from tracetrail.store import CloudTrailStore

EVIDENCE = [{"ref": "ref-a", "record": {"eventName": "SyntheticActivity"}}]
HYPOTHESES = [
    {"claim_id": "a", "statement": "Synthetic first claim"},
    {"claim_id": "b", "statement": "Synthetic second claim"},
]


@pytest.fixture(autouse=True)
def no_hidden_reads_or_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Planning validation must not invoke tools or network requests")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(CloudTrailStore, "load", forbidden)
    monkeypatch.setattr(CloudTrailStore, "get", forbidden)
    monkeypatch.setattr(CloudTrailStore, "query", forbidden)


def catalog():
    return {
        "candidates": [
            {
                "id": "P-key",
                "query": {"access_key": "SYNTHETIC_KEY"},
                "sources": [{"citation": "ref-a", "field": "userIdentity.accessKeyId"}],
            },
            {"id": "P-principal", "query": {"principal": "synthetic-user"}},
        ],
        "continuations": [
            {
                "id": "C-next",
                "attempt_id": "Q0",
                "query": {
                    "access_key": "SYNTHETIC_KEY",
                    "principal": "synthetic-user",
                    "limit": 7,
                    "offset": 7,
                    "start_time": "2026-01-01T10:00:00Z",
                },
            }
        ],
    }


def decision(action="finish", **changes):
    result = {
        "ledger": [
            {
                "claim_id": item["claim_id"],
                "evidence_refs": ["ref-a"],
                "open_question": "",
                "candidate_ids": [],
                "attempt_ids": [],
            }
            for item in HYPOTHESES
        ],
        "action": action,
        "rationale": "Test-only planning choice",
        "claim_id": "a",
        "candidate_id": None,
        "continuation_id": None,
        "query": None,
        "identifier": None,
        "dispositions": [],
    }
    if action == "finish":
        result["dispositions"] = [
            {
                "pivot_ids": ["P-key", "P-principal", "C-next"],
                "disposition": "deferred",
                "reason": "The model elects to leave these observed searches open.",
                "attempt_ids": [],
            }
        ]
    result.update(changes)
    return result


def query_attempt(args=None, **changes):
    output = {"records": [], "matched": 0, "truncated": False, "next_offset": None}
    output.update(changes)
    return {
        "name": "query_events",
        "args": args or {"access_key": "SYNTHETIC_KEY"},
        "result": output,
    }


def errors(value, *, history=None, remaining=3, coverage=None):
    return validate_decision(
        value,
        deepcopy(EVIDENCE),
        history or [],
        deepcopy(HYPOTHESES),
        remaining,
        coverage if coverage is not None else catalog(),
    )


def test_tested_scope_needs_a_successful_matching_query_for_every_named_candidate():
    value = decision(
        dispositions=[
            {
                "pivot_ids": ["P-key", "P-principal"],
                "disposition": "tested_under_recorded_scope",
                "reason": "These filters were used under the recorded narrow scope.",
                "attempt_ids": ["Q0"],
            },
            {
                "pivot_ids": ["C-next"],
                "disposition": "deferred",
                "reason": "Page remains open.",
                "attempt_ids": [],
            },
        ]
    )
    args = {
        "access_key": "SYNTHETIC_KEY",
        "principal": "synthetic-user",
        "event_name": "GetObject",
        "start_time": "2026-01-01T10:00:00Z",
        "end_time": "2026-01-01T10:01:00Z",
        "limit": 2,
    }
    history = [query_attempt(args)]
    before = deepcopy(history)
    assert errors(value, history=history) == []
    assert history == before  # Matching does not broaden the actual search scope.
    assert "tested_pivot_requires_matching_successful_attempt" in errors(
        value, history=[query_attempt()]
    )
