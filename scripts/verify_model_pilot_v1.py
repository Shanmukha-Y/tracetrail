#!/usr/bin/env python3
"""Verify stored pilot snapshots without inference, uploads, or SDK evaluation.

This verifier reuses the unchanged v8 verifier's wire/planning/source helpers.
It re-derives all 21 claim counters without calling score_claim_support. It can
inspect an ordered pilot prefix while the runner works. Use --require-sdk for
the final matching LangSmith stored-output replay.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import socket
import sys
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

sys.dont_write_bytecode = True


def denied(*args, **kwargs):
    raise AssertionError("The independent pilot verifier cannot use inference or network")


for owner, name in (
    (socket, "getaddrinfo"),
    (socket, "create_connection"),
    (socket.socket, "connect"),
    (socket.socket, "connect_ex"),
    (socket.socket, "sendto"),
):
    setattr(owner, name, denied)

OLD_PATH = Path(__file__).with_name("_v8_evaluation_contract.py")
FROZEN_PROTOCOL_SHA256 = "8fbea96221f8948ffe9303a4e41cd9decee0a353262866bbcd5cfb7c35d15643"
MODEL_ORDER = (
    "gemma4:e2b-it-q4_K_M",
    "gemma4:12b-it-q4_K_M",
    "qwen3.8:27b-q4_K_M",
    "mistral-small3.2:24b",
    "gemma4:31b-it-q4_K_M",
)
MAXIMA = (
    "ollama_reported_size_bytes",
    "ollama_reported_size_vram_bytes",
    "listener_process_tree_rss_sum_bytes",
)


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha(path):
    return digest_bytes(Path(path).read_bytes())


def canonical(value):
    return digest_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    )


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key in stored input")
            result[key] = value
        return result

    def nonfinite(value):
        raise AssertionError("Non-finite JSON value in stored input")

    content = path.read_bytes()
    value = json.loads(content, object_pairs_hook=unique, parse_constant=nonfinite)
    require(isinstance(value, dict), "Stored documents must be JSON objects")
    return value, digest_bytes(content)


def relative(root, value):
    require(isinstance(value, str) and not Path(value).is_absolute(), "Input path is not relative")
    path = (root / value).resolve()
    require(path.is_relative_to(root), "Frozen path leaves the repository")
    return path


def old_helpers():
    spec = importlib.util.spec_from_file_location("tracetrail_v8_stored_verifier", OLD_PATH)
    require(spec is not None and spec.loader is not None, "The historical verifier is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # The newer contract preserves statements exactly, including whitespace.
    # Change only this helper in memory. The historical file is never edited.
    module.text = lambda value: value if isinstance(value, str) else ""
    module.agent.make_model = denied
    return module


def plan_for(frozen):
    plan = []
    for repeat in (1, 2):
        for case_index, case_id in enumerate(frozen["pilot"]["case_ids"]):
            for model_index, model in enumerate(frozen["pilot"]["models"]):
                strategies = ["adaptive", "fixed"]
                if (model_index + case_index + repeat - 1) % 2:
                    strategies.reverse()
                for strategy in strategies:
                    plan.append(
                        {
                            "cell_id": f"r{repeat}-c{case_index + 1}-m{model_index + 1}-{strategy}",
                            "plan_index": len(plan) + 1,
                            "stage": case_index + 1 if repeat == 1 else 3,
                            "case_index": case_index + 1,
                            "model_index": model_index + 1,
                            "case_id": case_id,
                            "model": model["name"],
                            "strategy": strategy,
                            "repeat": repeat,
                        }
                    )
    return plan


def verify_freeze(root, path, frozen, old):
    agent = old.agent
    require(frozen["protocol_id"] == "tracetrail-model-pilot-v1", "Wrong pilot protocol ID")
    require(
        Path(agent.__file__).resolve() == root / "src/tracetrail/agent.py",
        "Imported runtime is from another checkout",
    )
    require(old.same(frozen["protocol"], agent.PROTOCOL), "Runtime controls differ from freeze")
    prompt = digest_bytes((agent.SYSTEM + agent.PLAN + agent.FINAL).encode())
    require(prompt == frozen["prompt_sha256"] == agent.PROMPT_SHA256, "Prompt differs from freeze")
    classes = {
        "decision": old.Decision,
        "claim_plan": old.ClaimPlan,
        "pivot_disposition": old.PivotDisposition,
        "evidence_link": agent.EvidenceLink,
        "materialized_analysis": agent.Analysis,
        "model_finding": agent.FindingSelection,
        "model_report_selection": agent.ReportSelection,
        "query": old.Query,
    }
    require(
        {name: canonical(cls.model_json_schema()) for name, cls in classes.items()}
        == frozen["schema_sha256"],
        "Runtime schema differs from freeze",
    )
    sources = frozen["source_sha256"]
    actual_python = {
        p.relative_to(root).as_posix() for p in (root / "src/tracetrail").rglob("*.py")
    }
    require(
        actual_python and actual_python <= sources.keys(),
        "Frozen runtime source inventory is incomplete",
    )
    checked = {}
    for name, expected in sources.items():
        source = relative(root, name)
        require(sha(source) == expected, "Frozen source differs: " + name)
        checked[str(source)] = expected
    require(
        set(frozen["dependency_sha256"]) == {"pyproject.toml", "uv.lock"},
        "Dependency pins are incomplete",
    )
    for name, expected in frozen["dependency_sha256"].items():
        source = relative(root, name)
        require(sha(source) == expected, "Frozen dependency differs: " + name)
        checked[str(source)] = expected
    for package, version in frozen["versions"].items():
        require(
            importlib.metadata.version(package) == version, "Installed version differs: " + package
        )
    require(
        tuple(frozen["evaluation"]["numeric_metric_keys"]) == old.NUMERIC_KEYS,
        "The 21-counter allowlist differs",
    )
    require(
        frozen["evaluation"]["primary_scorer"]
        == frozen["evaluation"]["scorer_id"]
        == "claim-support-v1",
        "Scorer identity differs",
    )
    require(
        sha(root / "src/tracetrail/support_evaluation.py") == frozen["evaluation"]["source_sha256"],
        "Scorer source differs",
    )
    for key in ("model_inventory", "semantic_rubric", "baseline_contract", "case_manifest"):
        entry = frozen[key]
        source = relative(root, entry["path"])
        require(sha(source) == entry["sha256"], "Frozen artifact differs: " + key)
        checked[str(source)] = entry["sha256"]
    inventory, _ = read(relative(root, frozen["model_inventory"]["path"]))
    inventory_by_name = {m["name"]: m for m in inventory["models"]}
    models = frozen["pilot"]["models"]
    require(
        tuple(model["name"] for model in models) == MODEL_ORDER,
        "The agreed five-model execution order differs",
    )
    for model in models:
        entry = inventory_by_name[model["name"]]
        require(
            model["digest"] == entry["expected_runtime_digest"],
            "Pinned runtime digest differs from inventory",
        )
        require(
            old.same(model["listed_digests"], entry["listed_digests"]),
            "Pinned listed digests differ from inventory",
        )
        require(model["digest"] in model["listed_digests"], "Runtime digest is not listed")
    require(frozen["pilot"]["repeats"] == 2, "The pilot repeat count differs")
    require(
        frozen["pilot"]["case_ids"] == ["dev-role-duration-direction", "dev-kms-returned-key"],
        "The exposed development cases differ",
    )
    cases = {
        case["id"]: case for case in old.load_cases(relative(root, frozen["case_manifest"]["path"]))
    }
    for case_id in frozen["pilot"]["case_ids"]:
        case = cases[case_id]
        require(case["split"] == "development", "The pilot includes a held-out case")
        checked[str(relative(root, case["fixture"]))] = case["fixture_sha256"]
    plan = plan_for(frozen)
    require(len(plan) == 40 and frozen["cell_plan"] == plan, "Frozen cell order differs")
    require(frozen["cell_plan_sha256"] == canonical(plan), "Frozen cell plan digest differs")
    return cases, plan, checked


def resource_issues(run):
    r = run.get("model_info", {}).get("resources", {})
    if not isinstance(r, dict):
        return ["resource_measurements_missing"]
    issues = []
    if r.get("status") != "completed":
        issues.append("resource_measurements_not_complete")
    count = r.get("sample_count", 0)
    if not isinstance(count, int) or count <= 0:
        issues.append("resource_samples_missing")
    if r.get("error_count", 0):
        issues.append("resource_measurement_errors")
    if r.get("foreign_model_observed"):
        issues.append("foreign_model_observed")
    if r.get("ollama_sample_count") != count:
        issues.append("ollama_samples_incomplete")
    if r.get("rss_complete_sample_count") != count:
        issues.append("process_rss_samples_incomplete")
    if not r.get("matching_model_sample_count", 0):
        issues.append("matching_model_samples_missing")
    if r.get("sample_limit_reached"):
        issues.append("resource_sampling_limit_reached")
    for key in MAXIMA:
        value = r.get("sampled_maxima", {}).get(key)
        if type(value) is not int or value < 0:
            issues.append("missing_or_invalid_" + key)
    if run.get("pilot", {}).get("wall_seconds_unknown"):
        issues.append("interrupted_attempt_wall_time_unknown")
    if run.get("pilot_model_identity", {}).get("verified") is not True:
        issues.append("runtime_model_identity_not_verified")
    return issues


def verify_gate(raw):
    runs = raw["runs"]
    gate = raw.get("runtime_gate")
    finished = [r for r in runs if r.get("status") != "running"]
    if len(finished) < 10:
        require(gate is None, "A runtime gate appeared before ten completed attempts")
        return {"available": False, "max_total_runs": None}
    require(isinstance(gate, dict), "The first-stage runtime gate is missing")
    first = runs[:10]
    seconds = sum(run["pilot"]["wall_seconds"] for run in first)
    issues = sorted({issue for run in first for issue in resource_issues(run)})
    expected = {
        "based_on_plan_indices": list(range(1, 11)),
        "first_ten_wall_seconds": seconds,
        "projected_twenty_seconds_with_overhead": 1.2 * 2 * seconds,
        "projected_forty_seconds_with_overhead": 1.2 * 4 * seconds,
        "overhead_factor": 1.2,
        "resource_measurement_issues": issues,
        "max_total_runs": 40 if 1.2 * 4 * seconds <= 5400 and not issues else 20,
    }
    for key, value in expected.items():
        require(gate.get(key) == value, "Runtime gate differs from independent calculation: " + key)
    require(gate.get("overall_wall_ceiling_is_soft") is True, "The wall cap must be labeled soft")
    require(gate.get("soft_launch_ceiling_seconds") == 5400, "The soft launch ceiling changed")
    require(len(runs) <= expected["max_total_runs"], "The recorded expansion exceeded its gate")
    return {"available": True, **expected}


def verify_resources(run, expected_digest):
    report = run.get("model_info", {}).get("resources", {})
    samples = report.get("samples")
    if not isinstance(samples, list):
        require(report.get("status") in (None, "unavailable"), "Resource samples disappeared")
        return {"status": report.get("status", "not-recorded"), "sample_count": 0}
    require(len(samples) == report["sample_count"], "Resource sample count differs")
    require(
        [s["index"] for s in samples] == list(range(len(samples))),
        "Resource sample sequence differs",
    )
    error_count = sum(len(s["errors"]) for s in samples) + len(report.get("errors", []))
    ollama_count = sum("ollama" in s for s in samples)
    rss_count = sum(bool(s.get("process_rss", {}).get("tree_complete")) for s in samples)
    matching_count = sum(s.get("ollama", {}).get("matching_model_count", 0) > 0 for s in samples)
    foreign = any(s.get("ollama", {}).get("foreign_model_count", 0) for s in samples)
    for key, value in {
        "error_count": error_count,
        "ollama_sample_count": ollama_count,
        "rss_complete_sample_count": rss_count,
        "rss_incomplete_sample_count": len(samples) - rss_count,
        "matching_model_sample_count": matching_count,
        "foreign_model_observed": bool(foreign),
    }.items():
        require(report[key] == value, "Resource aggregate differs: " + key)
    require(
        report["status"]
        == (
            "completed"
            if not error_count and rss_count == ollama_count == len(samples)
            else "partial"
        ),
        "Resource completion label differs",
    )
    models = [m for s in samples for m in s.get("ollama", {}).get("models", [])]
    require(
        all(m.get("digest") in (None, expected_digest) for m in models),
        "A resource sample observed a different target digest",
    )

    def maximum(values):
        return max((v for v in values if v is not None), default=None)

    expected = {
        "ollama_reported_size_bytes": maximum(m["size_bytes"] for m in models),
        "ollama_reported_size_vram_bytes": maximum(m["size_vram_bytes"] for m in models),
        "listener_process_tree_rss_sum_bytes": maximum(
            s["process_rss"].get("rss_sum_bytes")
            for s in samples
            if s.get("process_rss", {}).get("tree_complete")
        ),
    }
    require(report["sampled_maxima"] == expected, "Resource maxima differ from stored samples")
    for sample in samples:
        rss = sample.get("process_rss", {})
        if rss.get("tree_complete"):
            require(
                sum(p["rss_bytes"] for p in rss["processes"]) == rss["rss_sum_bytes"],
                "RSS aggregate differs from its sampled process rows",
            )
    return {
        "status": report["status"],
        "sample_count": len(samples),
        "sampled_maxima": expected,
        "foreign_model_observed": bool(foreign),
    }


def identity_for(run, model):
    info = run.get("model_info", {})
    observed = [
        entry.get("digest")
        for entry in info.get("loaded_models", [])
        if entry.get("model") == model["name"]
    ]
    listed_valid = set(info.get("listed_digests", [])) == set(model["listed_digests"])
    valid = observed == [model["digest"]] and listed_valid and info.get("remote_routing") is False
    recorded = run.get("pilot_model_identity")
    if recorded is not None:
        require(
            recorded["expected_runtime_digest"] == model["digest"],
            "Runtime identity expected pin differs",
        )
        require(
            recorded["observed_runtime_digests"] == observed, "Runtime identity observation differs"
        )
        require(
            recorded["listed_digests_match"] is listed_valid, "Runtime listed-digest claim differs"
        )
        require(recorded["verified"] is valid, "Runtime identity verification claim differs")
    else:
        require(
            run["status"] == "failed" and "model_history" not in run,
            "Runtime identity was not recorded",
        )
    if not valid:
        require(
            run["status"] != "completed", "An unverified runtime identity received completed status"
        )
    return {
        "verified": valid,
        "observed_runtime_digests": observed,
        "expected_runtime_digest": model["digest"],
        "listed_digests_match": listed_valid,
    }


def replay_tools(root, case, run, old):
    from tracetrail.store import CloudTrailStore
    from tracetrail.telemetry import local_context

    store = CloudTrailStore.load(relative(root, case["fixture"]))
    tools = {tool.name: tool for tool in store.tools()}
    for entry in run.get("tool_history", []):
        require(entry["name"] in tools, "An unavailable tool appears in history")
        with local_context():
            actual = tools[entry["name"]].invoke(entry["args"])
        if isinstance(actual, str):
            actual = json.loads(actual)
        require(
            old.same(actual, entry["result"]),
            "Read-only tool replay differs from stored source output",
        )
    return len(run.get("tool_history", []))


def token_summary(run):
    sums = Counter()
    details = []
    for history in run.get("model_history", []):
        usage = history.get("usage_metadata")
        metadata = history.get("response_metadata") or {}
        if usage is not None:
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                value = usage.get(key)
                require(type(value) is int and value >= 0, "Invalid model usage token count")
                sums[key] += value
            require(
                usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"],
                "Token total differs",
            )
            if metadata.get("prompt_eval_count") is not None:
                require(
                    metadata["prompt_eval_count"] == usage["input_tokens"],
                    "Prompt token metadata differs",
                )
            if metadata.get("eval_count") is not None:
                require(
                    metadata["eval_count"] == usage["output_tokens"],
                    "Output token metadata differs",
                )
        details.append(
            {
                "phase": history["phase"],
                "usage_metadata": usage,
                "ollama_timing_and_counts": {
                    k: metadata[k]
                    for k in (
                        "prompt_eval_count",
                        "eval_count",
                        "load_duration",
                        "prompt_eval_duration",
                        "eval_duration",
                        "total_duration",
                        "done_reason",
                    )
                    if k in metadata
                },
            }
        )
    return {"totals": dict(sums), "calls": details}


def verify_model_metadata(run, frozen, old):
    info = run["model_info"]
    require(info["name"] == run["model"], "Installed model metadata tag differs")
    require(
        info["ollama_version"] == frozen["ollama_version"],
        "Actual Ollama version differs from freeze",
    )
    require(info["remote_routing"] is False, "Actual model metadata permits remote routing")
    loaded = info.get("loaded_models", [])
    for entry in loaded:
        require(entry["model"] == run["model"], "A foreign loaded model entered the run metadata")
        require(
            entry["context_length"] == frozen["protocol"]["num_ctx"],
            "Actual loaded context differs from freeze",
        )
    for root in run["local_traces"]:
        for span in old.walk(root):
            if span["run_type"] != "llm":
                continue
            metadata = span["extra"]["metadata"]
            require(
                metadata["ls_provider"] == "ollama" and metadata["ls_model_type"] == "chat",
                "Actual model provider/type differs",
            )
            require(
                metadata["ls_temperature"] == frozen["protocol"]["temperature"],
                "Actual model temperature differs",
            )
    return deepcopy(loaded)


def verify_cell(root, case, run, cell, model, frozen, old):
    checks, errors = {}, []
    row = {
        "result_index": cell["plan_index"] - 1,
        "cell": cell,
        "status": run.get("status"),
        "checks": checks,
        "errors": errors,
    }

    def check(name, function):
        try:
            value = function()
            checks[name] = True
            return value
        except Exception as exc:
            checks[name] = False
            errors.append({"check": name, "error_type": type(exc).__name__, "message": str(exc)})
            return None

    def labels():
        require(
            run["case_id"] == case["id"] and run["split"] == case["split"] == "development",
            "Case or split label differs",
        )
        require(run["fixture_sha256"] == case["fixture_sha256"], "Fixture digest differs")
        require(
            run["model"] == cell["model"]
            and run["strategy"] == cell["strategy"]
            and run["test_only"] is False,
            "Inference assignment labels differ",
        )
        require(run["pilot"]["cell"] == cell, "Pilot cell assignment differs")
        require(
            run["pilot"]["result_sha256"]
            == canonical({k: v for k, v in run.items() if k != "pilot"}),
            "Stored result payload hash differs",
        )

    check("cell_labels_and_payload_hash", labels)
    row["runtime_identity"] = check("runtime_identity_claim", lambda: identity_for(run, model))
    has_history = "model_history" in run
    if has_history:

        def controls():
            require(
                old.same(run["protocol"], frozen["protocol"]), "Run controls differ from freeze"
            )
            require(
                run["prompt_sha256"] == frozen["prompt_sha256"], "Run prompt fingerprint differs"
            )
            require(run["trace_storage"] == "local-only", "Trace storage is not local-only")
            require(
                run["evaluation"]["primary_scorer"] == "claim-support-v1",
                "Run scorer label differs",
            )
            require(
                run["termination"]
                == {
                    "stop_reason": run["stop_reason"],
                    "queries_used": run["query_count"],
                    "query_limit": 3,
                    "queries_remaining": 3 - run["query_count"],
                    "source": "graph-counters",
                    "model_reasons_semantically_verified": False,
                },
                "Termination counters differ",
            )

        check("frozen_controls_and_termination", controls)
        spans = check(
            "actual_wire_schemas_plans_scopes_projections",
            lambda: old.verify_history(case, run, frozen),
        )
        row["actual_original_span_counts"] = dict(spans or {})
        row["runtime_loaded_models"] = check(
            "actual_model_provider_server_and_context",
            lambda: verify_model_metadata(run, frozen, old),
        )
        row["read_only_tool_replays"] = check(
            "read_only_source_tool_replay", lambda: replay_tools(root, case, run, old)
        )
        row["tokens_and_ollama_durations"] = check(
            "actual_token_metadata", lambda: token_summary(run)
        )
        row["resources"] = check(
            "resource_samples_and_aggregates", lambda: verify_resources(run, model["digest"])
        )
        row["actual_model_calls"] = run["model_calls"]
        row["actual_tool_calls"] = run["query_count"]
    else:

        def preflight():
            require(
                run["status"] == "failed" and run.get("inference_completed") is False,
                "A non-graph attempt is not labeled failed",
            )
            require(
                run.get("failures")
                and not run.get("model_calls")
                and not run.get("tool_history")
                and not run.get("local_traces"),
                "Preflight failure lost its scope",
            )

        check("honest_non_graph_failure", preflight)
        row.update(
            {
                "actual_model_calls": 0,
                "actual_tool_calls": 0,
                "actual_calls_unknown": bool(run.get("inference_calls_unknown")),
                "read_only_tool_replays": 0,
            }
        )

    def counters():
        derived, per_claim = old.independent_support(case, run)
        stored = run["claim_support_metrics"]
        require(
            set(derived) == set(old.NUMERIC_KEYS) and len(derived) == 21,
            "Independent counter allowlist differs",
        )
        for key, value in derived.items():
            old.check_close(stored[key], value, "Independent counter differs: " + key)
        require(
            stored["semantic_entailment_verified"] is False
            and stored["observation_projection_used_for_support"] is False,
            "Annotation support overclaims semantic warrant",
        )
        if not (row.get("runtime_identity") or {}).get("verified"):
            require(
                derived["process_valid"] is False
                and derived["process_valid_supported_claim_count"] == 0
                and derived["process_valid_covered_atom_count"] == 0,
                "An identity-invalid attempt earned process-valid credit",
            )
        for claim in per_claim:
            actual = next(c for c in stored["per_claim"] if c["claim_id"] == claim["claim_id"])
            for key, value in claim.items():
                require(old.same(actual[key], value), "Independent claim row differs: " + key)
        return {"numeric": derived, "per_claim": per_claim}

    row["independent_support"] = check("all_21_independent_support_counters", counters)
    check(
        "legacy_metrics",
        lambda: require(
            old.same(old.score_run(case, run), run["metrics"]), "Legacy scorer counters differ"
        ),
    )
    row["verified"] = bool(checks) and all(checks.values())
    return row


def verify_sdk(sdk, raw, raw_sha, rows, frozen, old):
    require(sdk["source_results_sha256"] == raw_sha, "SDK replay uses another raw snapshot")
    require(
        sdk["status"] == "completed"
        and sdk["upload_results"] is False
        and sdk["inference_rerun"] is False,
        "SDK replay scope/status differs",
    )
    for key in ("suite_id", "case_manifest_path", "case_manifest_sha256"):
        require(sdk[key] == raw[key], "SDK source metadata differs: " + key)
    require(
        sdk["evaluation"]
        == {
            "primary_scorer": "claim-support-v1",
            "scorer_id": "claim-support-v1",
            "source_sha256": frozen["evaluation"]["source_sha256"],
            "stored_output_replay": True,
            "post_hoc": False,
        },
        "SDK scorer identity differs",
    )
    by_index = {r["inputs"]["result_index"]: r for r in sdk["evaluated_runs"]}
    require(
        len(by_index) == len(sdk["evaluated_runs"]) == len(rows) == len(raw["runs"]),
        "SDK rows are missing or duplicated",
    )
    feedback_count = 0
    for index, run in enumerate(raw["runs"]):
        evaluated = by_index[index]
        inputs = {
            "result_index": index,
            "case_id": run["case_id"],
            "model": run["model"],
            "strategy": run["strategy"],
        }
        trace = evaluated["sdk_evaluation_trace"]
        require(evaluated["inputs"] == trace["inputs"] == inputs, "SDK inputs differ")
        require(
            old.same(trace["outputs"], {"result": run}) and not trace.get("error"),
            "SDK replayed a different or failed output",
        )
        metadata = trace["extra"]["metadata"]
        require(
            metadata["stored_output_replay"] is True and metadata["inference_rerun"] is False,
            "SDK trace replay labeling differs",
        )
        require(
            not any(span["run_type"] in ("llm", "tool") for span in old.walk(trace)),
            "SDK replay contains inference or tool executions",
        )
        counters = rows[index]["independent_support"]["numeric"]
        expected = {
            "claim_support_v1__" + key: value
            for key, value in counters.items()
            if isinstance(value, (bool, int, float)) and math.isfinite(float(value))
        }
        feedback = evaluated["sdk_feedback"]
        require(len(feedback) == len(expected) == 21, "SDK feedback count differs")
        require(
            {f["key"]: f["score"] for f in feedback} == expected,
            "SDK feedback differs from independent counters",
        )
        require(
            all(not (f.get("extra") or {}).get("error") for f in feedback), "SDK feedback failed"
        )
        feedback_count += len(feedback)
    return {
        "status": "verified",
        "feedback_count": feedback_count,
        "stored_rows": len(rows),
        "inference_rerun": False,
        "upload_results": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "raw", nargs="?", type=Path, default=Path("local-results/model-pilot-v1.json")
    )
    parser.add_argument(
        "--protocol", type=Path, default=Path("evaluation/protocol-model-pilot-v1.json")
    )
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--require-sdk", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    raw_path, protocol_path = args.raw.resolve(), args.protocol.resolve()
    output = (
        args.output
        or raw_path.with_name(
            raw_path.stem
            + "."
            + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid4().hex[:8]
            + ".verification.json"
        )
    ).resolve()
    require(
        output.is_relative_to(root / "local-results")
        and output.name.endswith(".verification.json"),
        "Verification output must be an ignored local-results/*.verification.json artifact",
    )
    require(output not in (raw_path, protocol_path), "Verification output collides with input")
    old = old_helpers()
    frozen, frozen_sha = read(protocol_path)
    require(frozen_sha == FROZEN_PROTOCOL_SHA256, "The agreed pilot freeze fingerprint differs")
    raw, raw_sha = read(raw_path)
    cases, plan, frozen_inputs = verify_freeze(root, protocol_path, frozen, old)
    frozen_inputs[str(protocol_path)] = frozen_sha
    identity = {
        "protocol_id": "tracetrail-model-pilot-v1",
        "protocol_sha256": frozen_sha,
        "plan_sha256": canonical(plan),
    }
    require(
        raw["frozen_identity"] == identity and raw["plan"] == plan,
        "Saved frozen identity or cell plan differs",
    )
    require(
        raw["case_manifest_path"] == frozen["case_manifest"]["path"]
        and raw["case_manifest_sha256"] == frozen["case_manifest"]["sha256"],
        "Saved manifest identity differs",
    )
    require(
        old.same(raw["protocol"], frozen["protocol"])
        and raw["test_only"] is False
        and raw["exposed_development_only"] is True,
        "Pilot scope labels differ",
    )
    require(isinstance(raw["runs"], list) and len(raw["runs"]) <= 40, "Invalid pilot attempt count")
    models = {m["name"]: m for m in frozen["pilot"]["models"]}
    rows, placeholders = [], []
    for index, run in enumerate(raw["runs"]):
        cell = plan[index]
        require(run["pilot"]["cell"] == cell, "Pilot cells are not an exact ordered prefix")
        wall = run["pilot"]["wall_seconds"]
        require(
            type(wall) in (int, float) and math.isfinite(wall) and wall >= 0,
            "Invalid cell wall duration",
        )
        if run.get("status") == "running":
            require(
                index == len(raw["runs"]) - 1
                and not placeholders
                and not run.get("pilot", {}).get("result_sha256"),
                "Running attempt is not the final in-flight placeholder",
            )
            require(
                wall == 0 and run["test_only"] is False and run.get("inference_completed") is False,
                "In-flight placeholder labeling differs",
            )
            placeholders.append({"cell": cell, "status": "running", "actual_calls_unknown": True})
        else:
            rows.append(
                verify_cell(
                    root, cases[cell["case_id"]], run, cell, models[cell["model"]], frozen, old
                )
            )
    gate = verify_gate(raw)
    for invocation in raw.get("invocations", []):
        require(
            type(invocation["stage"]) is int and invocation["stage"] in (1, 2, 3),
            "Invalid recorded stage invocation",
        )
    for run in raw["runs"]:
        prior = [
            invocation
            for invocation in raw["invocations"]
            if invocation["started_at"] <= run["pilot"]["started_at"]
        ]
        require(prior, "A recorded cell has no explicit stage invocation")
        invocation = prior[-1]
        limit = (10, 20, 40)[invocation["stage"] - 1]
        if invocation.get("max_runs") is not None:
            limit = min(limit, invocation["max_runs"])
        require(
            run["pilot"]["cell"]["plan_index"] <= limit,
            "A cell exceeded its recorded cumulative stage request",
        )
    if raw.get("invocations") and raw["invocations"][-1].get("finished_at"):
        require(
            raw["overall_wall_seconds"] == sum(run["pilot"]["wall_seconds"] for run in raw["runs"]),
            "Final wall accounting differs from cell durations",
        )
    sdk_path = (
        args.sdk or raw_path.with_name(raw_path.stem + ".claim-support-v1.langsmith-local.json")
    ).resolve()
    require(output != sdk_path, "Verification output collides with SDK input")
    sdk_report = {"status": "not-yet-recorded", "required": args.require_sdk}
    sdk_sha = None
    if sdk_path.exists():
        sdk, sdk_sha = read(sdk_path)
        if sdk.get("source_results_sha256") != raw_sha and not args.require_sdk:
            sdk_report = {"status": "older-raw-snapshot", "required": False, "sha256": sdk_sha}
        else:
            require(
                not placeholders and all(r["verified"] for r in rows),
                "Cannot verify SDK against an unverified/in-flight raw snapshot",
            )
            sdk_report = verify_sdk(sdk, raw, raw_sha, rows, frozen, old)
            sdk_report.update({"required": args.require_sdk, "sha256": sdk_sha})
    elif args.require_sdk:
        raise AssertionError("A matching local SDK stored-output replay is required")
    for path, expected in frozen_inputs.items():
        require(sha(path) == expected, "A frozen input changed during verification: " + path)
    totals = Counter()
    for row in rows:
        totals.update(row.get("actual_original_span_counts", {}))
    verified = all(row["verified"] for row in rows)
    token_totals = Counter()
    for row in rows:
        token_totals.update((row.get("tokens_and_ollama_durations") or {}).get("totals", {}))
    groups = []
    for model_name, strategy in sorted({(r["cell"]["model"], r["cell"]["strategy"]) for r in rows}):
        members = [
            r
            for r in rows
            if r["cell"]["model"] == model_name and r["cell"]["strategy"] == strategy
        ]
        groups.append(
            {
                "model": model_name,
                "strategy": strategy,
                "attempt_count": len(members),
                "verified_cells": sum(r["verified"] for r in members),
                "status_counts": dict(Counter(r["status"] for r in members)),
                "actual_model_calls": sum(r["actual_model_calls"] for r in members),
                "actual_tool_calls": sum(r["actual_tool_calls"] for r in members),
            }
        )
    current = sha(raw_path) == raw_sha
    require(not args.require_sdk or current, "The final raw snapshot changed during verification")
    document = {
        "schema_version": "1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "verified" if verified else "failed",
        "mode": "independent-pilot-stored-output-verification",
        "new_model_calls": 0,
        "sdk_evaluations_performed_by_this_verifier": 0,
        "uploads_enabled": False,
        "semantic_entailment_verified": False,
        "independent_human_review": False,
        "independence": (
            "21 claim counters are independently re-derived without score_claim_support. "
            "The unchanged v8 verifier's mechanical wire, schema, link, planning and "
            "projection checks are reused. Its statement normalization helper is tightened "
            "in memory to exact identity. Real source query tools are replayed read-only; "
            "no graph or model runs."
        ),
        "verifier_sha256": sha(__file__),
        "reused_verifier_sha256": sha(OLD_PATH),
        "protocol_sha256": frozen_sha,
        "prompt_sha256": frozen["prompt_sha256"],
        "frozen_inputs": frozen_inputs,
        "raw_source": {"path": str(raw_path), "sha256": raw_sha, "snapshot_still_current": current},
        "raw_pilot_status": raw.get("status"),
        "target_runs": raw.get("target_runs"),
        "attempts_recorded": len(raw["runs"]),
        "finished_attempts": len(rows),
        "in_flight": placeholders,
        "runtime_gate": gate,
        "sdk": sdk_report,
        "summary": {
            "actual_original_span_counts": dict(totals),
            "actual_model_calls": sum(r["actual_model_calls"] for r in rows),
            "actual_tool_calls": sum(r["actual_tool_calls"] for r in rows),
            "actual_calls_unknown_attempts": sum(r.get("actual_calls_unknown", False) for r in rows)
            + len(placeholders),
            "read_only_tool_replays": sum(r.get("read_only_tool_replays") or 0 for r in rows),
            "token_totals": dict(token_totals),
            "status_counts": dict(Counter(r["status"] for r in rows)),
            "verified_cells": sum(r["verified"] for r in rows),
        },
        "model_strategy_groups": groups,
        "rows": rows,
    }
    old.save_private(output, document)
    print(
        json.dumps(
            {
                "path": str(output),
                "sha256": sha(output),
                "status": document["status"],
                "finished_attempts": len(rows),
                "in_flight": len(placeholders),
                "sdk_status": sdk_report["status"],
                "summary": document["summary"],
            },
            sort_keys=True,
        )
    )
    return int(not verified)


if __name__ == "__main__":
    raise SystemExit(main())
