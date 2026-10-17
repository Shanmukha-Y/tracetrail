"""Graph behavior with test-only models. These tests are not inference evidence."""

import json
from collections import deque
from copy import deepcopy
from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

import tracetrail.agent as agent
from tracetrail.agent import (
    Analysis,
    Decision,
    FindingSelection,
    Observation,
    ReportSelection,
    investigate,
    validate_analysis,
)
from tracetrail.store import CloudTrailStore, Query


@dataclass(frozen=True)
class TestOnlyParseFailure:
    """Represent a failed schema parse without a real model call."""

    __test__ = False
    raw_content: str


class TestOnlyModel:
    """Return queued structured responses. No model or network is called."""

    __test__ = False

    def __init__(self, responses):
        self.responses = deque(responses)
        self.calls = []

    def with_structured_output(self, schema, *, method, include_raw):
        assert method == "json_schema"
        assert include_raw is True
        owner = self

        class TestOnlyInvoker:
            def invoke(self, messages, config=None):
                owner.calls.append({"schema": schema, "messages": messages, "config": config})
                if not owner.responses:
                    raise AssertionError("Test-only response queue exhausted")
                response = owner.responses.popleft()
                if isinstance(response, Exception):
                    raise response
                if isinstance(response, TestOnlyParseFailure):
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

        return TestOnlyInvoker()


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


def analysis_for(store, event_ids=("seed",)):
    """Construct a materialized report for direct validator tests only."""
    selection = selection_for(store, event_ids)
    return {
        **selection,
        "findings": materialized_findings(selection),
        "observations": [
            {
                "citation": ref,
                "field": "eventName",
                "value": store.get(ref)["record"]["eventName"],
                "present": True,
            }
            for ref in selection["selected_event_refs"]
        ],
    }


def materialized_errors(store, report):
    validated = Analysis.model_validate(report).model_dump(mode="json")
    return validate_analysis(validated, store.records, HYPOTHESES)


def run_test_graph(store, responses, *, strategy="adaptive"):
    model = TestOnlyModel(responses)
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


def test_test_only_graph_stops_at_three_tools_and_four_model_calls(evidence_store):
    report = selection_for(evidence_store, ("seed", "earlier", "later"))
    result, model = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL, "limit": 20}),
            decision("get_event", identifier="later"),
            decision("query_events", query={"event_name": "StopLogging", "limit": 20}),
            report,
            decision("query_events", query={"event_name": "StartLogging"}),
        ],
    )
    assert result["status"] == "completed"
    assert result["query_count"] == 3
    assert result["model_calls"] == 4
    assert len(result["tool_history"]) == 3
    assert [call["schema"] for call in model.calls] == [
        Decision,
        Decision,
        Decision,
        ReportSelection,
    ]
    assert len(model.responses) == 1
    assert len(result["evidence"]) == 3
    assert len({item["ref"] for item in result["evidence"]}) == 3
    assert result["failures"] == []


def test_test_only_model_graph_records_real_store_tool_span(evidence_store):
    result, model = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL}),
            decision(),
            selection_for(evidence_store),
        ],
    )

    def all_traces(traces):
        for trace in traces:
            yield trace
            yield from all_traces(trace.get("child_runs", []))

    tool_spans = [
        trace
        for trace in all_traces(result["local_traces"])
        if trace["run_type"] == "tool" and trace["name"] == "query_events"
    ]
    assert len(tool_spans) == 1
    span = tool_spans[0]
    assert span["inputs"]["principal"] == PRINCIPAL
    assert span["outputs"]["output"] == result["tool_history"][0]["result"]
    assert span["outputs"]["output"]["matched"] == 3
    assert span["error"] is None
    assert span["start_time"] <= span["end_time"]
    assert result["trace_storage"] == "local-only"
    # A test-only model has no real model execution span. The tool did execute.
    assert not any(trace["run_type"] == "llm" for trace in all_traces(result["local_traces"]))


def test_test_only_finish_uses_exact_seed_citations_and_observations(evidence_store):
    report = selection_for(evidence_store)
    result, model = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "completed"
    assert result["query_count"] == 0
    assert result["model_calls"] == 2
    assert result["findings"] == materialized_findings(report)
    observed = {item["field"]: item for item in result["observations"]}
    assert observed["eventName"]["value"] == "StopLogging"
    assert observed["userIdentity.accessKeyId"]["value"] == "SYNTHETIC_KEY"
    assert all(
        item["citation"] == report["selected_event_refs"][0] for item in result["observations"]
    )
    assert result["timeline"][0]["citation"] == evidence_store.get("seed")["ref"]
    assert [call["schema"] for call in model.calls] == [Decision, ReportSelection]
    assert result["failures"] == []


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


@pytest.mark.parametrize("value,valid", [(1, False), (True, True)])
def test_materialized_observation_checks_exact_boolean(evidence_store, value, valid):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "requestParameters.enabled",
            "value": value,
        }
    ]
    errors = materialized_errors(evidence_store, report)
    assert bool(errors) is not valid
    if not valid:
        assert errors[0]["code"] == "unsupported_observation"
    assert evidence_store.get("seed")["record"]["requestParameters"]["enabled"] is True


@pytest.mark.parametrize("field,replacement", [("checked", 0), ("count", True)])
def test_materialized_nested_observation_rejects_wrong_json_type(
    evidence_store, field, replacement
):
    original = evidence_store.get("seed")["record"]["requestParameters"]["settings"]
    altered = deepcopy(original)
    altered["flags"][0][field] = replacement
    assert altered == original
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "requestParameters.settings",
            "value": altered,
        }
    ]
    errors = materialized_errors(evidence_store, report)
    assert any(error["code"] == "unsupported_observation" for error in errors)
    assert evidence_store.get("seed")["record"]["requestParameters"]["settings"] == original


def test_materialized_nested_observation_accepts_exact_json_types(evidence_store):
    report = analysis_for(evidence_store)
    exact = evidence_store.get("seed")["record"]["requestParameters"]["settings"]
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "requestParameters.settings",
            "value": exact,
        }
    ]
    assert materialized_errors(evidence_store, report) == []


def test_materialized_observations_distinguish_missing_and_null(evidence_store):
    ref = evidence_store.get("seed")["ref"]
    report = analysis_for(evidence_store)
    report["observations"] = [
        {"citation": ref, "field": "errorCode", "value": None, "present": False},
        {"citation": ref, "field": "responseElements", "value": None, "present": True},
    ]
    assert materialized_errors(evidence_store, report) == []
    assert "errorCode" not in evidence_store.get("seed")["record"]
    assert evidence_store.get("seed")["record"]["responseElements"] is None


@pytest.mark.parametrize(
    "field,present,value",
    [
        ("errorCode", True, None),
        ("responseElements", False, None),
        ("eventName", False, None),
        ("errorCode", False, "AccessDenied"),
    ],
)
def test_materialized_observation_rejects_wrong_presence(evidence_store, field, present, value):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": field,
            "value": value,
            "present": present,
        }
    ]
    assert any(
        error["code"] == "unsupported_observation"
        for error in materialized_errors(evidence_store, report)
    )


def test_materialized_missing_field_requires_absence_flag(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "errorCode",
            "value": None,
        }
    ]
    assert any(
        error["code"] == "unsupported_observation"
        for error in materialized_errors(evidence_store, report)
    )


def test_materialized_absence_cannot_use_unknown_citation(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": "E99",
            "field": "errorCode",
            "value": None,
            "present": False,
        }
    ]
    assert any(
        error["code"] == "unsupported_observation"
        for error in materialized_errors(evidence_store, report)
    )


@pytest.mark.parametrize("present", [0, 1, "false", "true", None, [], {}])
def test_observation_presence_rejects_non_boolean_values(present):
    with pytest.raises(ValidationError):
        Observation.model_validate(
            {"citation": "E0", "field": "errorCode", "value": None, "present": present}
        )


def test_test_only_changed_hypothesis_is_preserved_as_invalid(evidence_store):
    report = selection_for(evidence_store)
    report["findings"][0]["statement"] = "The credentials were stolen."
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert {"phase": "validation", "code": "changed_statement", "claim_id": "intent"} in result[
        "failures"
    ]
    assert result["findings"][0]["statement"] == "The credentials were stolen."
    assert result["evidence"][0] == evidence_store.get("seed")


@pytest.mark.parametrize("unknown", ["sha256:" + "0" * 64 + "/Records/999", "E99"])
def test_test_only_unknown_citations_are_invalid_and_do_not_create_timeline(
    evidence_store, unknown, monkeypatch
):
    projection_calls = []

    def forbidden_projection(*args, **kwargs):
        projection_calls.append(True)
        raise AssertionError("Invalid selection must not reach fact projection")

    monkeypatch.setattr(agent, "project_observations", forbidden_projection)
    report = selection_for(evidence_store)
    report["selected_event_refs"] = [unknown]
    report["findings"][0]["evidence_links"][0]["citation"] = unknown
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    codes = {failure["code"] for failure in result["failures"]}
    assert "unknown_citation" in codes
    assert result["observations"] == []
    assert result["timeline"] == []
    assert result["selected_event_refs"] == [unknown]
    assert projection_calls == []


def test_wire_schema_excludes_model_observations():
    assert "observations" not in ReportSelection.model_json_schema()["properties"]
    assert "citations" not in FindingSelection.model_json_schema()["properties"]
    assert "evidence_links" in FindingSelection.model_json_schema()["properties"]
    assert "observations" in Analysis.model_json_schema()["properties"]
    assert Analysis.model_fields["observations"].metadata[0].max_length == 2000


@pytest.mark.parametrize(
    "observations", [[], [{"citation": "E0", "field": "eventName", "value": "FabricatedEvent"}]]
)
def test_model_supplied_observations_fail_schema_without_fallback(evidence_store, observations):
    malicious = {**selection_for(evidence_store), "observations": observations}
    with pytest.raises(ValidationError):
        ReportSelection.model_validate(malicious)
    result, model = run_test_graph(
        evidence_store, [decision(), malicious, selection_for(evidence_store)]
    )
    assert result["status"] == "failed"
    assert result["observations"] == []
    assert result["findings"] == []
    assert result["timeline"] == []
    assert result["model_calls"] == 2
    assert {"phase": "report", "error_type": "ValueError"} in result["failures"]
    assert json.loads(result["model_history"][-1]["output"]) == malicious
    assert len(model.responses) == 1


@pytest.mark.parametrize("cap", ["max_projected_observations", "max_projected_bytes"])
def test_projection_budget_failure_is_invalid_and_preserves_selection(
    evidence_store, monkeypatch, cap
):
    monkeypatch.setitem(agent.PROTOCOL, cap, 1)
    selection = selection_for(evidence_store)
    result, model = run_test_graph(
        evidence_store, [decision(), selection, selection_for(evidence_store)]
    )
    assert result["status"] == "invalid"
    assert result["observations"] == []
    assert result["findings"] == materialized_findings(selection)
    assert result["selected_event_refs"] == selection["selected_event_refs"]
    assert {
        "phase": "validation",
        "code": "observation_projection_failed",
        "error_type": "ValueError",
    } in result["failures"]
    assert result["model_calls"] == 2
    assert json.loads(result["model_history"][-1]["output"]) == selection
    assert len(model.responses) == 1


def test_known_finding_citation_must_also_be_selected(evidence_store, monkeypatch):
    projection_calls = []

    def forbidden_projection(*args, **kwargs):
        projection_calls.append(True)
        raise AssertionError("An unselected finding citation must block projection")

    monkeypatch.setattr(agent, "project_observations", forbidden_projection)
    selection = selection_for(evidence_store)
    selection["findings"][0]["evidence_links"][0]["citation"] = evidence_store.get("earlier")["ref"]
    result, _ = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL}),
            decision(),
            selection,
        ],
    )
    assert result["status"] == "invalid"
    assert {
        "phase": "validation",
        "code": "unselected_finding_citation",
        "claim_id": "intent",
    } in result["failures"]
    assert result["observations"] == []
    assert projection_calls == []


def test_projection_keeps_only_selected_record_facts(evidence_store):
    result, _ = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL}),
            decision(),
            selection_for(evidence_store),
        ],
    )
    ref = evidence_store.get("seed")["ref"]
    assert result["status"] == "completed"
    assert len(result["evidence"]) == 3
    assert result["selected_event_refs"] == [ref]
    assert {item["citation"] for item in result["observations"]} == {ref}
    facts = {item["field"]: item for item in result["observations"]}
    assert facts["eventName"]["value"] == "StopLogging"
    assert facts["requestParameters.enabled"]["value"] is True
    assert facts["errorCode"] == {
        "citation": ref,
        "field": "errorCode",
        "present": False,
        "value": None,
    }
    assert facts["responseElements"] == {
        "citation": ref,
        "field": "responseElements",
        "present": True,
        "value": None,
    }
    assert validate_analysis(result, result["evidence"], HYPOTHESES) == []


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
        evidence_store, [decision(), TestOnlyParseFailure(raw), selection_for(evidence_store)]
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


def test_test_only_model_exception_is_preserved_without_retry(evidence_store):
    result, model = run_test_graph(
        evidence_store,
        [decision(), RuntimeError("Test-only report exception"), selection_for(evidence_store)],
    )
    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["model_calls"] == 2
    assert {"phase": "report", "error_type": "RuntimeError"} in result["failures"]
    assert result["model_history"][-1]["error_type"] == "RuntimeError"
    assert len(model.responses) == 1


def test_unexpected_report_validator_exception_cannot_complete_partial_report(
    evidence_store, monkeypatch
):
    def broken_validator(*args, **kwargs):
        raise RuntimeError("Test-only unexpected validator failure")

    monkeypatch.setattr(agent, "validate_analysis", broken_validator)
    selection = selection_for(evidence_store)
    result, model = run_test_graph(
        evidence_store, [decision(), selection, selection_for(evidence_store)]
    )
    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["observations"] == []
    assert result["selected_event_refs"] == []
    assert result["timeline"] == []
    assert result["limitations"] == []
    assert result["evidence"] == [evidence_store.get("seed")]
    assert {"phase": "report", "error_type": "RuntimeError"} in result["failures"]
    assert json.loads(result["model_history"][-1]["output"]) == selection
    assert result["model_history"][-1]["phase"] == "report"
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


def test_test_only_missing_tool_arguments_are_invalid_without_tool_execution(evidence_store):
    result, _ = run_test_graph(
        evidence_store,
        [decision("query_events"), selection_for(evidence_store)],
    )
    assert result["status"] == "invalid"
    assert result["tool_history"] == []
    assert any(f["phase"] == "planning_validation" for f in result["failures"])
    assert result["query_count"] == 0


def test_test_only_timeline_orders_instants_with_timezone_offsets(evidence_store):
    report = selection_for(evidence_store, ("later", "seed", "earlier"))
    result, _ = run_test_graph(
        evidence_store,
        [decision("query_events", query={"principal": PRINCIPAL}), decision(), report],
    )
    assert result["status"] == "completed"
    assert [row["event_id"] for row in result["timeline"]] == ["earlier", "seed", "later"]
    assert result["timeline"][1]["source_ip"] is None
    for row in result["timeline"]:
        source = evidence_store.get(row["citation"])
        assert row["event_id"] == source["event_id"]
        assert row["event_time"] == source["record"]["eventTime"]


def test_test_only_fixed_search_handles_seed_without_optional_source_ip(evidence_store):
    result, model = run_test_graph(
        evidence_store, [selection_for(evidence_store)], strategy="fixed"
    )
    assert result["status"] == "completed"
    assert result["query_count"] == 3
    assert result["model_calls"] == 1
    assert [call["schema"] for call in model.calls] == [ReportSelection]
    assert result["timeline"][0]["source_ip"] is None
    assert result["failures"] == []
    for call in result["tool_history"]:
        Query.model_validate(call["args"])


@pytest.mark.parametrize("fault", ["missing", "duplicate"])
def test_analysis_requires_each_supplied_hypothesis_once(evidence_store, fault):
    report = analysis_for(evidence_store)
    if fault == "missing":
        report["findings"].pop()
    else:
        report["findings"].append(deepcopy(report["findings"][0]))
    errors = validate_analysis(report, evidence_store.records, HYPOTHESES)
    assert any(error["code"] == "claim_coverage" for error in errors)


@pytest.mark.parametrize("forbidden_field", ["citations", "observations"])
def test_model_finding_forbids_legacy_fields_and_preserves_raw(evidence_store, forbidden_field):
    malicious = selection_for(evidence_store)
    malicious["findings"][0][forbidden_field] = []
    with pytest.raises(ValidationError):
        ReportSelection.model_validate(malicious)
    result, model = run_test_graph(
        evidence_store, [decision(), malicious, selection_for(evidence_store)]
    )
    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["observations"] == []
    assert json.loads(result["model_history"][-1]["output"]) == malicious
    assert {"phase": "report", "error_type": "ValueError"} in result["failures"]
    assert result["model_calls"] == 2
    assert len(model.responses) == 1


@pytest.mark.parametrize("unknown", ["E99", "sha256:" + "0" * 64 + "/Records/999"])
def test_unknown_finding_link_is_invalid_without_replacing_it(evidence_store, unknown):
    selection = selection_for(evidence_store)
    selection["findings"][0]["evidence_links"][0]["citation"] = unknown
    result, _ = run_test_graph(evidence_store, [decision(), selection])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unknown_evidence_link_citation" for error in result["failures"])
    assert result["findings"][0]["citations"] == [unknown]
    assert result["observations"] == []
    assert json.loads(result["model_history"][-1]["output"]) == selection


@pytest.mark.parametrize(
    "field",
    [
        "requestParameters.missing",
        "responseElements.trailStatus",
        "sourceIPAddress",
        "requestParameters.settings.flags.0.checked",
    ],
)
def test_unresolved_field_link_blocks_projection(evidence_store, monkeypatch, field):
    projected = []

    def forbidden_projection(*args, **kwargs):
        projected.append(True)
        raise AssertionError("Invalid field links must block fact projection")

    monkeypatch.setattr(agent, "project_observations", forbidden_projection)
    selection = selection_for(evidence_store)
    selection["findings"][0]["evidence_links"][0]["fields"] = [field]
    result, _ = run_test_graph(evidence_store, [decision(), selection])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unresolved_evidence_link_field" for error in result["failures"])
    assert result["findings"][0]["evidence_links"][0]["fields"] == [field]
    assert result["observations"] == []
    assert projected == []
    assert json.loads(result["model_history"][-1]["output"]) == selection


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


def test_top_level_api_absence_and_whole_array_can_be_linked(evidence_store):
    selection = selection_for(evidence_store)
    selection["findings"][0]["evidence_links"][0]["fields"] = [
        "errorCode",
        "responseElements",
        "requestParameters.settings.flags",
    ]
    result, _ = run_test_graph(evidence_store, [decision(), selection])
    assert result["status"] == "completed"
    assert result["findings"] == materialized_findings(selection)
    facts = {item["field"]: item for item in result["observations"]}
    assert facts["errorCode"]["present"] is False
    assert facts["responseElements"]["present"] is True
    assert facts["responseElements"]["value"] is None
    assert facts["requestParameters.settings.flags"]["value"] == [{"checked": False, "count": 1}]


def test_selected_but_unlinked_records_do_not_pad_finding_citations(evidence_store):
    selection = selection_for(evidence_store, ("seed", "earlier", "later"))
    selection["findings"][0]["evidence_links"] = selection["findings"][0]["evidence_links"][:1]
    result, _ = run_test_graph(
        evidence_store,
        [
            decision("query_events", query={"principal": PRINCIPAL}),
            decision(),
            selection,
        ],
    )
    assert result["status"] == "completed"
    assert len(result["selected_event_refs"]) == 3
    assert result["findings"][0]["citations"] == [evidence_store.get("seed")["ref"]]
    assert result["findings"][1]["citations"] == selection["selected_event_refs"]
    assert json.loads(result["model_history"][-1]["output"]) == selection
