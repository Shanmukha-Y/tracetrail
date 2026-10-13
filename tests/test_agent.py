"""Graph behavior with test-only models. These tests are not inference evidence."""

import json
from collections import deque
from copy import deepcopy
from dataclasses import dataclass

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from tracetrail.agent import Analysis, Decision, Observation, investigate, validate_analysis
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
                return {
                    "raw": AIMessage(content=json.dumps(response, sort_keys=True)),
                    "parsed": schema.model_validate(response),
                    "parsing_error": None,
                }

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
    return {
        "action": action,
        "rationale": "Test-only explanation check",
        "claim_id": "intent",
        "query": query,
        "identifier": identifier,
    }


def analysis_for(store, event_ids=("seed",)):
    refs = [store.get(event_id)["ref"] for event_id in event_ids]
    return {
        "findings": [
            {
                **hypothesis,
                "status": "uncertain",
                "citations": refs,
            }
            for hypothesis in HYPOTHESES
        ],
        "observations": [
            {
                "citation": ref,
                "field": "eventName",
                "value": store.get(ref)["record"]["eventName"],
                "present": True,
            }
            for ref in refs
        ],
        "selected_event_refs": refs,
        "limitations": ["These records do not show intent or maintenance approval."],
    }


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
    report = analysis_for(evidence_store, ("seed", "earlier", "later"))
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
    assert [call["schema"] for call in model.calls] == [Decision, Decision, Decision, Analysis]
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
            analysis_for(evidence_store),
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
    report = analysis_for(evidence_store)
    result, model = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "completed"
    assert result["query_count"] == 0
    assert result["model_calls"] == 2
    assert result["findings"] == report["findings"]
    assert result["observations"] == report["observations"]
    assert result["timeline"][0]["citation"] == evidence_store.get("seed")["ref"]
    assert [call["schema"] for call in model.calls] == [Decision, Analysis]
    assert result["failures"] == []


def test_test_only_aliases_resolve_to_exact_records_and_keep_raw_response(evidence_store):
    exact_report = analysis_for(evidence_store, ("later", "seed", "earlier"))
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
        finding["citations"] = [aliases[ref] for ref in finding["citations"]]
    for observation in compact_report["observations"]:
        observation["citation"] = aliases[observation["citation"]]
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
    assert result["findings"] == exact_report["findings"]
    assert result["observations"] == exact_report["observations"]
    assert result["tool_history"][1]["args"]["identifier"] == evidence_store.get("earlier")["ref"]
    assert result["tool_history"][1]["result"] == evidence_store.get("earlier")
    assert json.loads(result["model_history"][-1]["output"]) == compact_report
    planner_input = json.loads(model.calls[1]["messages"][-1].content)
    assert [item["ref"] for item in planner_input["evidence"]] == ["E0", "E1", "E2"]
    for item in planner_input["evidence"]:
        assert item["record"] == evidence_store.get(item["event_id"])["record"]
    assert [row["event_id"] for row in result["timeline"]] == ["earlier", "seed", "later"]
    assert all(row["citation"].startswith("sha256:") for row in result["timeline"])
    assert result["failures"] == []


def test_test_only_observation_rejects_integer_for_boolean(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "requestParameters.enabled",
            "value": 1,
        }
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unsupported_observation" for error in result["failures"])
    assert result["observations"][0]["value"] == 1
    assert evidence_store.get("seed")["record"]["requestParameters"]["enabled"] is True


def test_test_only_observation_accepts_exact_boolean(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": evidence_store.get("seed")["ref"],
            "field": "requestParameters.enabled",
            "value": True,
        }
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "completed"
    assert result["failures"] == []


@pytest.mark.parametrize("field,replacement", [("checked", 0), ("count", True)])
def test_test_only_nested_observation_rejects_equal_value_with_wrong_json_type(
    evidence_store, field, replacement
):
    original = evidence_store.get("seed")["record"]["requestParameters"]["settings"]
    altered = deepcopy(original)
    altered["flags"][0][field] = replacement
    assert altered == original  # Plain Python equality would miss the nested JSON type change.
    report = analysis_for(evidence_store)
    report["observations"] = [
        {
            "citation": "E0",
            "field": "requestParameters.settings",
            "value": altered,
        }
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unsupported_observation" for error in result["failures"])
    assert result["observations"][0]["value"] == altered
    assert result["observations"][0]["citation"] == evidence_store.get("seed")["ref"]
    assert evidence_store.get("seed")["record"]["requestParameters"]["settings"] == original


def test_test_only_nested_observation_accepts_exact_json_types(evidence_store):
    report = analysis_for(evidence_store)
    exact = evidence_store.get("seed")["record"]["requestParameters"]["settings"]
    report["observations"] = [
        {"citation": "E0", "field": "requestParameters.settings", "value": exact}
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "completed"
    assert result["observations"][0]["value"] == exact
    assert result["failures"] == []


def test_test_only_observations_distinguish_absent_error_code_from_json_null(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {"citation": "E0", "field": "errorCode", "value": None, "present": False},
        {"citation": "E0", "field": "responseElements", "value": None, "present": True},
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "completed"
    assert result["failures"] == []
    by_field = {observation["field"]: observation for observation in result["observations"]}
    assert by_field["errorCode"]["present"] is False
    assert by_field["responseElements"]["present"] is True
    assert all(observation["value"] is None for observation in result["observations"])
    raw = evidence_store.get("seed")["record"]
    assert "errorCode" not in raw
    assert "responseElements" in raw and raw["responseElements"] is None


@pytest.mark.parametrize(
    "field,present,value",
    [
        ("errorCode", True, None),
        ("responseElements", False, None),
        ("eventName", False, None),
        ("errorCode", False, "AccessDenied"),
    ],
)
def test_test_only_observation_rejects_wrong_presence_or_non_null_absence(
    evidence_store, field, present, value
):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {"citation": "E0", "field": field, "value": value, "present": present}
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unsupported_observation" for error in result["failures"])
    assert result["observations"][0]["present"] is present
    assert result["observations"][0]["value"] == value


def test_test_only_missing_field_requires_explicit_absence_flag(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [{"citation": "E0", "field": "errorCode", "value": None}]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert result["observations"][0]["present"] is True
    assert any(error["code"] == "unsupported_observation" for error in result["failures"])


def test_test_only_absence_observation_cannot_use_an_unknown_citation(evidence_store):
    report = analysis_for(evidence_store)
    report["observations"] = [
        {"citation": "E99", "field": "errorCode", "value": None, "present": False}
    ]
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    assert any(error["code"] == "unsupported_observation" for error in result["failures"])


@pytest.mark.parametrize("present", [0, 1, "false", "true", None, [], {}])
def test_observation_presence_rejects_non_boolean_values(present):
    with pytest.raises(ValidationError):
        Observation.model_validate(
            {"citation": "E0", "field": "errorCode", "value": None, "present": present}
        )


def test_test_only_changed_hypothesis_is_preserved_as_invalid(evidence_store):
    report = analysis_for(evidence_store)
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
    evidence_store, unknown
):
    report = analysis_for(evidence_store)
    report["selected_event_refs"] = [unknown]
    report["findings"][0]["citations"] = [unknown]
    report["observations"][0]["citation"] = unknown
    result, _ = run_test_graph(evidence_store, [decision(), report])
    assert result["status"] == "invalid"
    codes = {failure["code"] for failure in result["failures"]}
    assert {"unknown_citation", "unsupported_observation"} <= codes
    assert result["timeline"] == []
    assert result["selected_event_refs"] == [unknown]


def test_test_only_parse_failure_preserves_raw_output_without_canned_report(evidence_store):
    raw = "test-only invalid report: no schema object"
    result, model = run_test_graph(
        evidence_store, [decision(), TestOnlyParseFailure(raw), analysis_for(evidence_store)]
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
        [decision(), RuntimeError("Test-only report exception"), analysis_for(evidence_store)],
    )
    assert result["status"] == "failed"
    assert result["findings"] == []
    assert result["model_calls"] == 2
    assert {"phase": "report", "error_type": "RuntimeError"} in result["failures"]
    assert result["model_history"][-1]["error_type"] == "RuntimeError"
    assert len(model.responses) == 1


def test_test_only_failed_tool_is_visible_to_next_plan_and_final_report(evidence_store):
    result, model = run_test_graph(
        evidence_store,
        [
            decision("get_event", identifier="missing-event"),
            decision(),
            analysis_for(evidence_store),
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


def test_test_only_missing_tool_arguments_are_recorded_then_reported(evidence_store):
    result, _ = run_test_graph(
        evidence_store,
        [decision("query_events"), decision(), analysis_for(evidence_store)],
    )
    assert result["status"] == "completed"
    assert result["tool_history"][0]["result"]["error"]["code"] == "tool_exception"
    assert {"phase": "tool", "error_type": "ValueError"} in result["failures"]
    assert result["query_count"] == 1


def test_test_only_timeline_orders_instants_with_timezone_offsets(evidence_store):
    report = analysis_for(evidence_store, ("later", "seed", "earlier"))
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
    result, model = run_test_graph(evidence_store, [analysis_for(evidence_store)], strategy="fixed")
    assert result["status"] == "completed"
    assert result["query_count"] == 3
    assert result["model_calls"] == 1
    assert [call["schema"] for call in model.calls] == [Analysis]
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
