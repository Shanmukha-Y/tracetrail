"""Planning graph regressions with test-only models, not inference evidence."""

import json
import socket
from collections import deque
from copy import deepcopy
from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

import tracetrail.agent as agent
from tracetrail.agent import ReportSelection, investigate
from tracetrail.planning import Decision
from tracetrail.store import CloudTrailStore, Query

PRINCIPAL = "arn:aws:iam::000000000000:user/test-only-planner"
CALLER_KEY = "SYNTHETIC_PLANNING_CALLER_KEY"
HYPOTHESES = [{"claim_id": "approval", "statement": "The observed activity had business approval."}]


class FakePlanningModel:
    """Validate each exact queued response with the real requested wire schema."""

    def __init__(self, responses):
        self.responses = deque(responses)
        self.calls = []
        self.raw_responses = []

    def with_structured_output(self, schema, *, method, include_raw):
        assert method == "json_schema"
        assert include_raw is True
        owner = self

        class FakeInvoker:
            def invoke(self, messages, config=None):
                payload = json.loads(messages[-1].content)
                owner.calls.append({"schema": schema, "payload": payload})
                if not owner.responses:
                    raise AssertionError("Test-only response queue exhausted")
                queued = owner.responses.popleft()
                response = queued(payload) if callable(queued) else deepcopy(queued)
                owner.raw_responses.append(deepcopy(response))
                raw = AIMessage(content=json.dumps(response, sort_keys=True))
                try:
                    parsed = schema.model_validate(response)
                except ValidationError as exc:
                    return {"raw": raw, "parsed": None, "parsing_error": exc}
                return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return FakeInvoker()


@dataclass
class ObservedStore:
    store: CloudTrailStore
    queries: list
    gets: list


@pytest.fixture(autouse=True)
def no_network_or_model_construction(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Planning integration tests must not call a model or network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(agent, "make_model", forbidden)


def observed_store(tmp_path, monkeypatch, *, count=3):
    """Load invented records and observe actual store reads behind real tools."""
    records = []
    for index in range(count):
        records.append(
            {
                "eventID": "seed" if index == 0 else f"record-{index}",
                "eventName": "AssumeRole" if index == 0 else "ListBuckets",
                "eventSource": "sts.amazonaws.com" if index == 0 else "s3.amazonaws.com",
                "eventTime": f"2026-01-01T10:{index:02d}:00Z",
                "userIdentity": {
                    "type": "IAMUser",
                    "arn": PRINCIPAL,
                    "accessKeyId": CALLER_KEY,
                },
                "sourceIPAddress": "192.0.2.10" if index != 2 else "192.0.2.11",
                "responseElements": (
                    {"credentials": {"accessKeyId": "SYNTHETIC_PLANNING_CHILD_KEY"}}
                    if index == 0
                    else None
                ),
            }
        )
    path = tmp_path / "planning-test-only.json"
    path.write_text(json.dumps({"Records": records}), encoding="utf-8")
    store = CloudTrailStore.load(path)
    queries, gets = [], []
    query, get = store.query, store.get

    def track_query(args):
        queries.append(args.model_dump(mode="json"))
        return query(args)

    def track_get(identifier):
        gets.append(identifier)
        return get(identifier)

    monkeypatch.setattr(store, "query", track_query)
    monkeypatch.setattr(store, "get", track_get)
    return ObservedStore(store, queries, gets)


def ledger(payload, *, candidate_ids=()):
    return [
        {
            "claim_id": "approval",
            "evidence_refs": [payload["seed"]["ref"]],
            "open_question": "These local API records do not establish business approval.",
            "candidate_ids": list(candidate_ids),
            "attempt_ids": [
                f"Q{index}"
                for index, entry in enumerate(payload["tool_history"])
                if entry["name"] == "query_events"
            ],
        }
    ]


def plan(payload, *, action, **branch):
    return {
        "ledger": ledger(payload),
        "action": action,
        "rationale": "Test-only explicit choice to examine the supplied explanation.",
        "claim_id": "approval",
        "candidate_id": None,
        "continuation_id": None,
        "query": None,
        "identifier": None,
        "dispositions": [],
        **branch,
    }


def honest_finish(payload):
    pivot_ids = [
        item["id"]
        for collection in ("candidates", "continuations")
        for item in payload["coverage"][collection]
    ]
    return plan(
        payload,
        action="finish",
        rationale="Leave the visible local pivots unsearched and keep approval uncertain.",
        dispositions=(
            [
                {
                    "pivot_ids": pivot_ids,
                    "disposition": "deferred",
                    "reason": "These scopes remain unsearched or incomplete; approval is unknown.",
                    "attempt_ids": [],
                }
            ]
            if pivot_ids
            else []
        ),
    )


def candidate_choice(payload):
    candidate = next(
        item
        for item in payload["coverage"]["candidates"]
        if item["query"] == {"access_key": CALLER_KEY}
    )
    return plan(
        payload,
        action="query_events",
        ledger=ledger(payload, candidate_ids=[candidate["id"]]),
        candidate_id=candidate["id"],
    )


def custom_choice(query):
    return lambda payload: plan(payload, action="query_events", query=deepcopy(query))


def seed_report(payload):
    """A test-only uncertain report, separate from the planning response schema."""
    ref = payload["seed"]["ref"]
    return {
        "findings": [
            {
                **HYPOTHESES[0],
                "evidence_links": [{"citation": ref, "fields": ["eventName"], "role": "context"}],
                "rationale": "The observed API activity does not establish business approval.",
                "missing_evidence": ["The business approval record was not supplied."],
                "status": "uncertain",
            }
        ],
        "selected_event_refs": [ref],
        "limitations": ["Unsearched local scopes and business approval remain open."],
    }


def run_graph(observed, responses):
    model = FakePlanningModel(responses)
    result = investigate(
        observed.store,
        "seed",
        "What can the supplied records establish about approval?",
        deepcopy(HYPOTHESES),
        model_name="test-only:planning-no-inference",
        model=model,
    )
    assert result["test_only"] is True
    return result, model


def invalid_decision(payload, defect):
    if defect == "unknown_candidate":
        return plan(payload, action="query_events", candidate_id="P_NOT_IN_THE_MENU")
    if defect == "unknown_continuation":
        return plan(payload, action="query_events", continuation_id="C_NOT_IN_THE_MENU")
    if defect == "two_query_branches":
        response = candidate_choice(payload)
        response["query"] = {"event_name": "ListBuckets", "limit": 20}
        return response
    response = honest_finish(payload)
    if defect == "missing_dispositions":
        response["dispositions"] = []
    elif defect == "unsearched_called_tested":
        response["dispositions"][0].update(
            disposition="tested_under_recorded_scope", attempt_ids=["Q0"]
        )
    elif defect == "unknown_ledger_evidence":
        response["ledger"][0]["evidence_refs"] = ["E999"]
    elif defect == "extra_schema_field":
        response["hidden_fallback_query"] = {"principal": PRINCIPAL}
    else:
        raise AssertionError("Unknown test-only defect")
    return response


@pytest.mark.parametrize("defect", ["two_query_branches", "extra_schema_field"])
def test_invalid_plan_is_preserved_without_a_query_fallback_or_repair(
    tmp_path, monkeypatch, defect
):
    observed = observed_store(tmp_path, monkeypatch)
    result, model = run_graph(
        observed, [lambda payload: invalid_decision(payload, defect), seed_report]
    )

    assert result["status"] == "invalid"
    assert result["stop_reason"] == (
        "plan_error" if defect == "extra_schema_field" else "invalid_decision"
    )
    assert result["query_count"] == 0
    assert result["model_calls"] == 2
    assert observed.queries == []
    assert observed.gets == ["seed"]
    assert result["tool_history"] == []
    assert len(result["evidence"]) == 1
    assert result["findings"][0]["status"] == "uncertain"
    assert any(
        failure["phase"] in ("plan", "planning_validation") for failure in result["failures"]
    )
    assert [call["schema"] for call in model.calls] == [Decision, ReportSelection]
    assert json.loads(result["model_history"][0]["output"]) == model.raw_responses[0]
    assert model.calls[-1]["payload"]["remaining_queries"] == 3
    assert not model.responses


def test_candidate_selection_executes_only_that_observed_filter_once(tmp_path, monkeypatch):
    observed = observed_store(tmp_path, monkeypatch)
    result, model = run_graph(observed, [candidate_choice, honest_finish, seed_report])

    assert result["status"] == "completed"
    assert result["query_count"] == 1
    assert result["model_calls"] == 3
    assert observed.queries == [Query(access_key=CALLER_KEY, limit=20).model_dump(mode="json")]
    assert observed.gets == ["seed"]
    assert len(result["tool_history"]) == 1
    assert len(result["evidence"]) == 3
    chosen = model.raw_responses[0]["candidate_id"]
    assert result["decision_history"][0]["candidate_id"] == chosen
    assert model.raw_responses[0]["query"] is None
    coverage = model.calls[1]["payload"]["coverage"]
    candidate = next(item for item in coverage["candidates"] if item["id"] == chosen)
    assert candidate["searched"] is True
    assert candidate["attempts"][0]["attempt_id"] == "Q0"
    assert candidate["attempts"][0]["args"] == observed.queries[0]
    assert len(model.calls[0]["payload"]["coverage"]["candidates"]) > 1
    assert result["failures"] == []


def test_three_query_budget_routes_to_report_without_a_fourth_plan_or_query(tmp_path, monkeypatch):
    observed = observed_store(tmp_path, monkeypatch)
    sentinel = {"this_fourth_query_must_remain_unread": True}
    result, model = run_graph(
        observed,
        [
            custom_choice({"event_name": "AssumeRole", "limit": 20}),
            custom_choice({"event_name": "ListBuckets", "limit": 20}),
            custom_choice({"event_name": "NoSuchTestOnlyEvent", "limit": 20}),
            seed_report,
            sentinel,
        ],
    )

    assert result["status"] == "completed"
    assert result["stop_reason"] == "query_budget_exhausted"
    assert result["query_count"] == 3
    assert result["model_calls"] == 4
    assert len(observed.queries) == 3
    assert len(result["tool_history"]) == 3
    assert len(result["decision_history"]) == 3
    assert [call["schema"] for call in model.calls] == [
        Decision,
        Decision,
        Decision,
        ReportSelection,
    ]
    assert model.calls[-1]["payload"]["remaining_queries"] == 0
    assert model.calls[-1]["payload"]["stop_reason"] == "query_budget_exhausted"
    assert list(model.responses) == [sentinel]
    assert result["failures"] == []
