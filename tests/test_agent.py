"""Graph behavior with test-only models. These tests are not inference evidence."""

import json
from collections import deque
from copy import deepcopy
from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from tracetrail.agent import (
    investigate,
    validate_analysis,
)
from tracetrail.store import CloudTrailStore


@dataclass(frozen=True)
class FakeParseFailure:
    """Represent a failed schema parse without a real model call."""

    raw_content: str


class FakeModel:
    """Return queued structured responses. No model or network is called."""

    def __init__(self, responses):
        self.responses = deque(responses)
        self.calls = []

    def with_structured_output(self, schema, *, method, include_raw):
        assert method == "json_schema"
        assert include_raw is True
        owner = self

        class FakeInvoker:
            def invoke(self, messages, config=None):
                owner.calls.append({"schema": schema, "messages": messages, "config": config})
                if not owner.responses:
                    raise AssertionError("Test-only response queue exhausted")
                response = owner.responses.popleft()
                if isinstance(response, Exception):
                    raise response
                if isinstance(response, FakeParseFailure):
                    return {
                        "raw": AIMessage(content=response.raw_content),
                        "parsed": None,
                        "parsing_error": ValueError("Test-only schema failure"),
                    }
                if callable(response):
                    response = response(json.loads(messages[-1].content))
                raw = AIMessage(content=json.dumps(response, sort_keys=True))
                try:
                    parsed = schema.model_validate(response)
                except ValidationError as exc:
                    return {"raw": raw, "parsed": None, "parsing_error": exc}
                return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return FakeInvoker()


HYPOTHESES = [
    {"claim_id": "intent", "statement": "The actor disabled the trail to hide activity."},
    {"claim_id": "maintenance", "statement": "The actor performed approved maintenance."},
]
PRINCIPAL = "arn:aws:iam::123456789012:user/synthetic-operator"


@pytest.fixture
def evidence_store(tmp_path):
    """Three synthetic records with timezone offsets and optional fields."""
    common = {
        "eventSource": "cloudtrail.amazonaws.com",
        "userIdentity": {"arn": PRINCIPAL, "accessKeyId": "SYNTHETIC_KEY"},
        "responseElements": None,
        "requestParameters": {
            "enabled": True,
            "settings": {"flags": [{"checked": False, "count": 1}]},
        },
    }
    records = [
        {
            **deepcopy(common),
            "eventID": "seed",
            "eventName": "StopLogging",
            "eventTime": "2026-01-01T10:00:00Z",
        },
        {
            **deepcopy(common),
            "eventID": "later",
            "eventName": "StartLogging",
            "eventTime": "2026-01-01T06:30:00-04:00",
            "sourceIPAddress": "192.0.2.8",
        },
        {
            **deepcopy(common),
            "eventID": "earlier",
            "eventName": "GetTrailStatus",
            "eventTime": "2026-01-01T12:30:00+03:00",
            "sourceIPAddress": "192.0.2.8",
        },
    ]
    path = tmp_path / "synthetic-test-only.json"
    path.write_text(json.dumps({"Records": records}), encoding="utf-8")
    return CloudTrailStore.load(path)


def decision(action="finish", *, query=None, identifier=None):
    """Build explicit test-only plans from the visible prompt, without inference."""

    def response(payload):
        pivots = [item["id"] for item in payload["coverage"]["candidates"]]
        pivots += [item["id"] for item in payload["coverage"]["continuations"]]
        return {
            "ledger": [
                {
                    "claim_id": h["claim_id"],
                    "evidence_refs": [],
                    "open_question": "External context is unknown in this test.",
                    "candidate_ids": [],
                    "attempt_ids": [],
                }
                for h in HYPOTHESES
            ],
            "action": action,
            "rationale": "Test-only explanation check",
            "claim_id": "intent",
            "candidate_id": None,
            "continuation_id": None,
            "query": query,
            "identifier": identifier,
            "dispositions": (
                [
                    {
                        "pivot_ids": pivots,
                        "disposition": "deferred",
                        "reason": "Test-only deliberate early finish.",
                        "attempt_ids": [],
                    }
                ]
                if action == "finish" and pivots
                else []
            ),
        }

    return response


def selection_for(store, event_ids=("seed",)):
    """Construct explicit test-only wire output without model field values."""
    refs = [store.get(event_id)["ref"] for event_id in event_ids]
    return {
        "findings": [
            {
                **hypothesis,
                "evidence_links": [
                    {"citation": ref, "fields": ["eventName"], "role": "context"} for ref in refs
                ],
                "rationale": "The cited API activity does not establish intent or approval.",
                "missing_evidence": ["Intent and maintenance approval records are missing."],
                "status": "uncertain",
            }
            for hypothesis in HYPOTHESES
        ],
        "selected_event_refs": refs,
        "limitations": ["These records do not show intent or maintenance approval."],
    }


def materialized_findings(selection):
    """Expected public citations come only from the explicit test-only links."""
    return [
        {
            **deepcopy(finding),
            "citations": list(
                dict.fromkeys(link["citation"] for link in finding["evidence_links"])
            ),
        }
        for finding in selection["findings"]
    ]


def run_test_graph(store, responses, *, strategy="adaptive"):
    model = FakeModel(responses)
    result = investigate(
        store,
        "seed",
        "Why did logging stop?",
        deepcopy(HYPOTHESES),
        model_name="test-only:no-inference",
        strategy=strategy,
        model=model,
    )
    assert result["test_only"] is True
    return result, model


def test_test_only_aliases_resolve_to_exact_records_and_keep_raw_response(evidence_store):
    exact_report = selection_for(evidence_store, ("later", "seed", "earlier"))
    aliases = {
        evidence_store.get("seed")["ref"]: "E0",
        evidence_store.get("earlier")["ref"]: "E1",
        evidence_store.get("later")["ref"]: "E2",
    }
    compact_report = deepcopy(exact_report)
    compact_report["selected_event_refs"] = [
        aliases[ref] for ref in compact_report["selected_event_refs"]
    ]
    for finding in compact_report["findings"]:
        for link in finding["evidence_links"]:
            link["citation"] = aliases[link["citation"]]
    result, model = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL}),
            decision("get_event", identifier="E1"),
            decision(),
            compact_report,
        ],
    )
    assert result["status"] == "completed"
    assert result["selected_event_refs"] == exact_report["selected_event_refs"]
    assert result["findings"] == materialized_findings(exact_report)
    assert {item["citation"] for item in result["observations"]} == set(
        exact_report["selected_event_refs"]
    )
    assert validate_analysis(result, result["evidence"], HYPOTHESES) == []
    assert result["tool_history"][1]["args"]["identifier"] == evidence_store.get("earlier")["ref"]
    assert result["tool_history"][1]["result"] == evidence_store.get("earlier")
    assert json.loads(result["model_history"][-1]["output"]) == compact_report
    planner_input = json.loads(model.calls[1]["messages"][-1].content)
    assert [item["ref"] for item in planner_input["evidence"]] == ["E1", "E0", "E2"]
    assert [item["event_id"] for item in planner_input["evidence"]] == ["earlier", "seed", "later"]
    assert [row["citation"] for row in planner_input["chronology"]] == ["E1", "E0", "E2"]
    assert [row["seconds_from_seed"] for row in planner_input["chronology"]] == [-1800, 0, 1800]
    assert planner_input["seed"]["ref"] == "E0"
    for item in planner_input["evidence"]:
        assert item["record"] == evidence_store.get(item["event_id"])["record"]
    assert [row["event_id"] for row in result["timeline"]] == ["earlier", "seed", "later"]
    assert all(row["citation"].startswith("sha256:") for row in result["timeline"])
    assert result["failures"] == []


def test_prompt_contains_returned_evidence_and_no_evaluation_gold(evidence_store):
    result, model = run_test_graph(evidence_store, [decision(), selection_for(evidence_store)])
    assert result["status"] == "completed"
    for call in model.calls:
        payload = json.loads(call["messages"][-1].content)
        assert set(payload) == {
            "seed",
            "question",
            "hypotheses",
            "evidence",
            "chronology",
            "tool_history",
            "coverage",
            "credential_map",
            "remaining_queries",
            "previous_plan",
            "stop_reason",
        }
        assert payload["hypotheses"] == HYPOTHESES
        assert [item["event_id"] for item in payload["evidence"]] == ["seed"]
        assert "annotations" not in payload
        assert "relevant_event_ids" not in payload
        assert "expected_status" not in json.dumps(payload)
    assert result["evidence"] == [evidence_store.get("seed")]


def test_test_only_parse_failure_preserves_raw_output_without_canned_report(evidence_store):
    raw = "test-only invalid report: no schema object"
    result, model = run_test_graph(
        evidence_store, [decision(), FakeParseFailure(raw), selection_for(evidence_store)]
    )
    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["observations"] == []
    assert result["timeline"] == []
    assert result["limitations"] == []
    assert result["evidence"] == [evidence_store.get("seed")]
    assert {"phase": "report", "error_type": "ValueError"} in result["failures"]
    assert result["model_history"][-1]["output"] == raw
    assert result["model_history"][-1]["error_type"] == "ValueError"
    assert result["model_calls"] == 2
    assert len(model.responses) == 1


def test_test_only_failed_tool_is_visible_to_next_plan_and_final_report(evidence_store):
    result, model = run_test_graph(
        evidence_store,
        [
            decision("get_event", identifier="missing-event"),
            decision(),
            selection_for(evidence_store),
        ],
    )
    assert result["status"] == "completed"
    assert result["query_count"] == 1
    assert result["model_calls"] == 3
    failure = result["tool_history"][0]["result"]["error"]
    assert failure["code"] == "event_not_found"
    assert {"phase": "tool", "error": failure} in result["failures"]
    for call in model.calls[1:]:
        input_payload = json.loads(call["messages"][-1].content)
        assert input_payload["tool_history"][0]["result"]["error"] == failure
        exact = evidence_store.get("seed")
        assert input_payload["evidence"] == [{**exact, "ref": "E0"}]
        assert input_payload["seed"] == input_payload["evidence"][0]


@pytest.mark.parametrize(
    "status,code",
    [
        ("supported", "missing_supporting_evidence"),
        ("refuted", "missing_contradicting_evidence"),
    ],
)
def test_decisive_status_requires_explicit_support_role(evidence_store, status, code):
    selection = selection_for(evidence_store)
    selection["findings"][0]["status"] = status
    result, _ = run_test_graph(evidence_store, [decision(), selection])
    assert result["status"] == "invalid"
    assert any(error["code"] == code for error in result["failures"])
    assert result["findings"][0]["status"] == status
    assert result["findings"][0]["evidence_links"][0]["role"] == "context"
    assert result["observations"] == []


def test_uncertain_finding_requires_an_explicit_missing_evidence_gap(evidence_store):
    selection = selection_for(evidence_store)
    selection["findings"][0]["missing_evidence"] = []
    result, _ = run_test_graph(evidence_store, [decision(), selection])
    assert result["status"] == "invalid"
    assert any(error["code"] == "missing_uncertainty" for error in result["failures"])
    assert result["findings"][0]["missing_evidence"] == []
    assert result["observations"] == []
