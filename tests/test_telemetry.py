"""Test local telemetry guards. These inputs are test data, not model evidence."""

import hashlib
import json
import shutil
import socket
from pathlib import Path
from typing import TypedDict

import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.runnables.config import var_child_runnable_config
from langchain_core.tools import tool
from langchain_core.tracers.context import tracing_v2_callback_var
from langgraph.graph import END, START, StateGraph
from langsmith.utils import tracing_is_enabled

from tracetrail.telemetry import (
    LocalOnlyViolation,
    _LocalOnlyClient,
    evaluate_local,
    local_context,
    new_local_trace_collector,
    save_collected_traces,
    status,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def network_forbidden(monkeypatch):
    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("A local-only test tried to connect to the network.")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-only-secret-never-used")
    monkeypatch.setenv("LANGSMITH_ENDPOINT", "https://example.invalid")
    yield attempts
    assert attempts == []


def test_local_context_disables_ambient_and_inherited_tracing(network_forbidden):
    inherited_callback = object()
    token = tracing_v2_callback_var.set(inherited_callback)
    config_token = var_child_runnable_config.set({"callbacks": [inherited_callback]})
    try:
        collector = new_local_trace_collector()
        with local_context():
            assert tracing_is_enabled() is False
            assert tracing_v2_callback_var.get() is None
            assert var_child_runnable_config.get() is None
            assert (
                RunnableLambda(lambda number: number + 1).invoke(
                    4, config={"callbacks": [collector]}
                )
                == 5
            )
        assert tracing_v2_callback_var.get() is inherited_callback
        assert var_child_runnable_config.get()["callbacks"] == [inherited_callback]
        assert len(collector.traced_runs) == 1
    finally:
        var_child_runnable_config.reset(config_token)
        tracing_v2_callback_var.reset(token)


def test_guarded_client_rejects_all_transports(network_forbidden):
    client = _LocalOnlyClient()
    try:
        operations = (
            lambda: client.request_with_retries("GET", "/info"),
            lambda: client.session.request("GET", "https://example.invalid"),
            lambda: client._get_langsmith_api(),
            lambda: client._get_langsmith_api_sync(),
            lambda: client.create_run("test", {}, "chain"),
            lambda: client.update_run("test"),
        )
        for operation in operations:
            with pytest.raises(LocalOnlyViolation):
                operation()
    finally:
        client.close()


def test_trace_collector_saves_real_sdk_spans(tmp_path, network_forbidden):
    collector = new_local_trace_collector()
    nested = RunnableLambda(lambda value: {"value": value})
    with local_context():
        RunnableLambda(lambda value: nested.invoke(value)).invoke(
            "test-only", config={"callbacks": [collector]}
        )
    saved = save_collected_traces(collector, tmp_path / "trace.json")
    document = json.loads(Path(saved["path"]).read_text())
    assert saved["trace_count"] == 1
    assert document["uploads_enabled"] is False
    assert document["traces"][0]["outputs"] == {"value": "test-only"}
    children = document["traces"][0]["child_runs"]
    assert len(children) == 1
    assert children[0]["outputs"] == {"value": "test-only"}
    assert Path(saved["path"]).stat().st_mode & 0o777 == 0o600


def test_status_never_exposes_key(network_forbidden):
    document = status()
    assert document["environment_presence"]["LANGSMITH_API_KEY"] is True
    assert "test-only-secret-never-used" not in json.dumps(document)
    assert document["requires_api_key"] is False


def test_graph_tool_and_nested_runnable_spans_saved(tmp_path, network_forbidden):
    class TestState(TypedDict):
        value: int

    @tool
    def increment(number: int) -> int:
        """Increment a test value without any external action."""
        return number + 1

    nested = RunnableLambda(lambda number: number * 2, name="Test-only nested chain")

    def node(state: TestState) -> TestState:
        doubled = nested.invoke(state["value"])
        return {"value": increment.invoke({"number": doubled})}

    builder = StateGraph(TestState)
    builder.add_node("test_node", node)
    builder.add_edge(START, "test_node")
    builder.add_edge("test_node", END)
    collector = new_local_trace_collector()
    with local_context():
        assert builder.compile().invoke({"value": 2}, config={"callbacks": [collector]}) == {
            "value": 5
        }
    saved = save_collected_traces(collector, tmp_path / "graph-trace.json")
    document = json.loads(Path(saved["path"]).read_text())
    root = document["traces"][0]
    graph_node = next(child for child in root["child_runs"] if child["name"] == "test_node")
    child_names = {child["name"] for child in graph_node["child_runs"]}
    assert {"Test-only nested chain", "increment"}.issubset(child_names)
    tool_span = next(child for child in graph_node["child_runs"] if child["name"] == "increment")
    assert tool_span["run_type"] == "tool"
    assert tool_span["inputs"] == {"number": 4}
    assert tool_span["outputs"] == {"output": 5}


def _test_batch(manifest_path=ROOT / "evaluation" / "cases.json"):
    from tracetrail.evaluation import load_cases

    manifest = json.loads(manifest_path.read_text())
    case = load_cases(manifest_path)[0]
    # An intentionally failed, test-only run. No inference result is fabricated.
    run = {
        "case_id": case["id"],
        "model": "test-only-no-inference",
        "strategy": "adaptive",
        "fixture_sha256": case["fixture_sha256"],
        "evidence": [],
        "selected_event_refs": [],
        "observations": [],
        "findings": [],
        "tool_history": [],
        "model_history": [],
        "query_count": 0,
        "model_calls": 0,
        "duration_seconds": 0,
        "status": "failed",
        "failures": ["Intentional test-only failure without model inference."],
    }
    return {
        "suite_id": manifest["suite_id"],
        "case_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "runs": [run],
    }, case


def test_real_langsmith_offline_evaluation_no_upload(tmp_path, network_forbidden):
    from tracetrail.evaluation import score_run

    batch, case = _test_batch()
    result_path = tmp_path / "test-only-results.json"
    result_path.write_text(json.dumps(batch))
    report = evaluate_local(result_path, ROOT)
    document = json.loads(Path(report["path"]).read_text())
    assert document["status"] == "completed"
    assert document["upload_results"] is False
    assert document["inference_rerun"] is False
    assert len(document["evaluated_runs"]) == 1
    row = document["evaluated_runs"][0]
    assert row["sdk_evaluation_trace"]["outputs"]["result"]["status"] == "failed"
    feedback = {item["key"]: item["score"] for item in row["sdk_feedback"]}
    expected = score_run(case, batch["runs"][0])
    assert feedback["relevant_event_recall"] == expected["relevant_event_recall"]


def test_offline_evaluation_rejects_changed_input_hash(tmp_path):
    batch, _ = _test_batch()
    batch["case_manifest_sha256"] = "0" * 64
    result_path = tmp_path / "test-only-results.json"
    result_path.write_text(json.dumps(batch))
    with pytest.raises(ValueError, match="case manifest"):
        evaluate_local(result_path, ROOT)


def test_offline_evaluation_uses_recorded_versioned_manifest(tmp_path, network_forbidden):
    fixture_root = tmp_path / "test-only-suite"
    shutil.copytree(ROOT / "fixtures", fixture_root / "fixtures")
    manifest_path = fixture_root / "evaluation" / "cases-test-version.json"
    manifest_path.parent.mkdir()
    manifest = json.loads((ROOT / "evaluation" / "cases.json").read_text())
    manifest["suite_id"] = "tracetrail-test-only-versioned-suite"
    manifest_path.write_text(json.dumps(manifest))
    batch, _ = _test_batch(manifest_path)
    batch["case_manifest_path"] = "evaluation/cases-test-version.json"
    result_path = tmp_path / "test-only-versioned-results.json"
    result_path.write_text(json.dumps(batch))
    report = evaluate_local(result_path, fixture_root)
    document = json.loads(Path(report["path"]).read_text())
    assert document["suite_id"] == manifest["suite_id"]
    assert document["case_manifest_path"] == batch["case_manifest_path"]
    assert document["case_manifest_sha256"] == batch["case_manifest_sha256"]
    assert document["status"] == "completed"


@pytest.mark.parametrize(
    "manifest_name",
    ["../evaluation/cases.json", "/tmp/cases.json", "fixtures/dev-role-pivot.json", {}],
)
def test_offline_evaluation_rejects_manifest_outside_evaluation(tmp_path, manifest_name):
    batch, _ = _test_batch()
    batch["case_manifest_path"] = manifest_name
    result_path = tmp_path / "test-only-results.json"
    result_path.write_text(json.dumps(batch))
    with pytest.raises(ValueError, match="relative path under evaluation"):
        evaluate_local(result_path, ROOT)
