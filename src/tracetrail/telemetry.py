"""Local LangSmith SDK evaluation and trace storage. This module cannot upload."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests
from langchain_core.runnables.config import var_child_runnable_config
from langchain_core.tracers.context import tracing_v2_callback_var
from langchain_core.tracers.run_collector import RunCollectorCallbackHandler
from langsmith import Client, tracing_context
from langsmith.evaluation import evaluate
from langsmith.run_trees import RunTree
from langsmith.schemas import Example


class LocalOnlyViolation(RuntimeError):
    """A LangSmith operation tried to use the network."""


class _DeniedSession(requests.Session):
    """Reject HTTP before a connection or credential transmission can occur."""

    def request(self, *args: Any, **kwargs: Any) -> Any:
        raise LocalOnlyViolation("LangSmith network access is disabled in TraceTrail.")

    def send(self, *args: Any, **kwargs: Any) -> Any:
        raise LocalOnlyViolation("LangSmith network access is disabled in TraceTrail.")


class _LocalOnlyClient(Client):
    """Use the real SDK's local result handling, with no usable transport."""

    def __init__(self) -> None:
        # evaluate(upload_results=False) still needs a Client for local feedback
        # normalization. Do not resolve a user's key or endpoint for that work.
        super().__init__(
            api_urls={"http://127.0.0.1:1": ""},
            api_key="",
            workspace_id="",
            session=_DeniedSession(),
            auto_batch_tracing=False,
            tracing_mode="langsmith",
            info={},
            omit_traced_runtime_info=True,
            disable_prompt_cache=True,
        )

    def request_with_retries(self, *args: Any, **kwargs: Any) -> Any:
        raise LocalOnlyViolation("LangSmith API access is disabled in TraceTrail.")

    def _get_langsmith_api(self) -> Any:
        raise LocalOnlyViolation("LangSmith API access is disabled in TraceTrail.")

    def _get_langsmith_api_sync(self) -> Any:
        raise LocalOnlyViolation("LangSmith API access is disabled in TraceTrail.")

    def create_run(self, *args: Any, **kwargs: Any) -> Any:
        raise LocalOnlyViolation("LangSmith uploads are disabled in TraceTrail.")

    def update_run(self, *args: Any, **kwargs: Any) -> Any:
        raise LocalOnlyViolation("LangSmith uploads are disabled in TraceTrail.")


@contextmanager
def local_context() -> Iterator[None]:
    """Disable automatic uploads, including ambient and inherited tracing."""
    callback_token = tracing_v2_callback_var.set(None)
    config_token = var_child_runnable_config.set(None)
    try:
        with tracing_context(enabled=False, parent=False):
            yield
    finally:
        var_child_runnable_config.reset(config_token)
        tracing_v2_callback_var.reset(callback_token)


def status() -> dict[str, Any]:
    """Report configuration presence only. Never return a credential value."""
    names = (
        "LANGSMITH_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGSMITH_ENDPOINT",
        "LANGSMITH_WORKSPACE_ID",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
    )
    return {
        "mode": "local-only",
        "sdk_version": version("langsmith"),
        "uploads_enabled": False,
        "server_ui_available": False,
        "requires_api_key": False,
        "environment_presence": {name: bool(os.environ.get(name)) for name in names},
        "server_ui_requirement": "A separate licensed LangSmith server is not included.",
    }


def new_local_trace_collector() -> RunCollectorCallbackHandler:
    """Return a real LangChain callback that collects execution spans in memory."""
    return RunCollectorCallbackHandler()


def serialize_local_trace(run: RunTree) -> dict[str, Any]:
    """Preserve nested spans that SDK model_dump excludes by default."""
    return {
        **run.model_dump(mode="json"),
        "child_runs": [serialize_local_trace(child) for child in run.child_runs],
    }


def _write_json(destination: Path, value: dict[str, Any]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, allow_nan=False) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".tracetrail-", suffix=".json", dir=destination.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def save_collected_traces(
    collector: RunCollectorCallbackHandler, output_path: str | Path
) -> dict[str, Any]:
    """Save captured graph and model spans on disk without a LangSmith server."""
    destination = Path(output_path)
    document = {
        "schema_version": "1",
        "mode": "local-execution-traces",
        "uploads_enabled": False,
        "sdk_version": version("langsmith"),
        "traces": [serialize_local_trace(run) for run in collector.traced_runs],
    }
    _write_json(destination, document)
    return {"path": str(destination), "trace_count": len(document["traces"])}


def evaluate_local(
    results_path: str | Path,
    fixture_root: str | Path = ".",
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Score stored inference outputs with the real offline LangSmith evaluator.

    This replays stored outputs into the SDK. It makes no new model calls, does
    not publish an experiment, and preserves local SDK traces and feedback.
    """
    from tracetrail.evaluation import load_cases, score_run

    source = Path(results_path)
    root = Path(fixture_root)
    manifest_path = root / "evaluation" / "cases.json"
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    source_bytes = source.read_bytes()
    batch = json.loads(source_bytes)
    if batch.get("case_manifest_sha256") != manifest_digest:
        raise ValueError("The results do not match the current case manifest.")
    cases = {case["id"]: case for case in load_cases(manifest_path)}
    runs = batch.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("The results must contain at least one stored run.")
    manifest = json.loads(manifest_path.read_bytes())
    if batch.get("suite_id") != manifest["suite_id"]:
        raise ValueError("The results have a different evaluation suite ID.")
    for run in runs:
        case = cases.get(run.get("case_id"))
        if case is None:
            raise ValueError("A stored run has an unknown case ID.")
        if run.get("fixture_sha256") != case["fixture_sha256"]:
            raise ValueError("A stored run has a different fixture hash.")

    dataset_id = uuid4()
    examples = [
        Example(
            id=uuid4(),
            dataset_id=dataset_id,
            inputs={
                "result_index": index,
                "case_id": run["case_id"],
                "model": run["model"],
                "strategy": run["strategy"],
            },
            outputs={"annotations": cases[run["case_id"]]["annotations"]},
            metadata={"split": cases[run["case_id"]]["split"]},
        )
        for index, run in enumerate(runs)
    ]

    def stored_output(inputs: dict[str, Any]) -> dict[str, Any]:
        return {"result": runs[inputs["result_index"]]}

    def annotation_support(
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        reference_outputs: dict[str, Any],
    ) -> dict[str, Any]:
        case = cases[inputs["case_id"]]
        if reference_outputs["annotations"] != case["annotations"]:
            raise ValueError("The reference annotations changed during evaluation.")
        metrics = score_run(case, outputs["result"])
        scores = []
        for key, value in metrics.items():
            if isinstance(value, (int, float, bool)) and math.isfinite(float(value)):
                scores.append({"key": key, "score": value})
        if not scores:
            raise ValueError("The evidence scorer returned no numeric metrics.")
        return {"results": scores}

    client = _LocalOnlyClient()
    try:
        with local_context():
            experiment = evaluate(
                stored_output,
                data=examples,
                evaluators=[annotation_support],
                client=client,
                upload_results=False,
                disable_evaluator_tracing=True,
                max_concurrency=0,
                blocking=True,
                error_handling="log",
                experiment_prefix="tracetrail-local-stored-output",
                metadata={"stored_output_replay": True, "inference_rerun": False},
            )
            rows = list(experiment)
    finally:
        client.close()

    serialized_rows = []
    evaluation_failed = False
    for row in rows:
        sdk_run = row["run"]
        feedback = [item.model_dump(mode="json") for item in row["evaluation_results"]["results"]]
        if sdk_run is None or sdk_run.error or not feedback:
            evaluation_failed = True
        if any((item.get("extra") or {}).get("error") for item in feedback):
            evaluation_failed = True
        serialized_rows.append(
            {
                "inputs": row["example"].inputs,
                "sdk_evaluation_trace": (
                    serialize_local_trace(sdk_run) if sdk_run is not None else None
                ),
                "sdk_feedback": feedback,
            }
        )
    destination = (
        Path(output_path)
        if output_path is not None
        else source.with_name(source.stem + ".langsmith-local.json")
    )
    document = {
        "schema_version": "1",
        "mode": "offline-stored-output-evaluation",
        "sdk_version": version("langsmith"),
        "created_at": datetime.now(UTC).isoformat(),
        "upload_results": False,
        "inference_rerun": False,
        "source_results_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "case_manifest_sha256": manifest_digest,
        "suite_id": batch["suite_id"],
        "status": "evaluation_failed" if evaluation_failed else "completed",
        "evaluated_runs": serialized_rows,
    }
    _write_json(destination, document)
    return {
        "path": str(destination),
        "status": document["status"],
        "evaluated_run_count": len(rows),
        "uploads_enabled": False,
        "inference_rerun": False,
    }
