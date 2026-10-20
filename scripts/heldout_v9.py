#!/usr/bin/env python3
"""Freeze, run and verify a small first-use Qwen method comparison.

The eight assigned attempts are fixed before inference. Failures are never
retried. Raw reports, traces and SDK feedback stay in local-results. Summary
exports contain allowlisted numbers, enums, public case IDs and fingerprints.
Assistant-authored cases and mechanical support are not human validation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import socket
import sys
import time
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

STUDY_ID = "tracetrail-heldout-v9"
MODEL = "qwen3.8:27b-q4_K_M"
DIGEST = "25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e"
CEILING = 2700
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise ValueError(message)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, "Missing stored audit helper")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def utc():
    return datetime.now(UTC).isoformat()


def read(path):
    from tracetrail.pilot import _read

    return _read(Path(path))


def relative(value):
    require(isinstance(value, str) and not Path(value).is_absolute(), "Expected relative input")
    path = (ROOT / value).resolve()
    require(path.is_relative_to(ROOT), "Input leaves the repository")
    return path


def artifact(path):
    path = Path(path).resolve()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}


@contextmanager
def no_network():
    def denied(*args, **kwargs):
        raise RuntimeError("Stored evaluation and freezing cannot access the network")

    targets = (
        (socket, "getaddrinfo"),
        (socket, "create_connection"),
        (socket.socket, "connect"),
        (socket.socket, "connect_ex"),
        (socket.socket, "sendto"),
    )
    previous = [(owner, name, getattr(owner, name)) for owner, name in targets]
    try:
        for owner, name, _ in previous:
            setattr(owner, name, denied)
        yield
    finally:
        for owner, name, value in reversed(previous):
            setattr(owner, name, value)


def plan_cells(case_ids):
    result = []
    for repeat in (1, 2):
        for index, case_id in enumerate(case_ids):
            methods = ("adaptive", "fixed") if (index + repeat) % 2 else ("fixed", "adaptive")
            for strategy in methods:
                result.append(
                    {
                        "cell_id": f"r{repeat}-c{index + 1}-{strategy}",
                        "plan_index": len(result) + 1,
                        "case_id": case_id,
                        "model": MODEL,
                        "strategy": strategy,
                        "repeat": repeat,
                    }
                )
    return result


def verify_protocol(path):
    import tracetrail
    from tracetrail import agent
    from tracetrail import pilot as pilot_runtime
    from tracetrail.evaluation import load_cases
    from tracetrail.pilot import _runtime

    path = Path(path).resolve()
    require(path.parent == ROOT / "evaluation", "Protocol must be under evaluation")
    frozen = read(path)
    expected_package = ROOT / "src/tracetrail"
    require(
        all(
            Path(value).resolve().parent == expected_package
            for value in (agent.__file__, pilot_runtime.__file__, tracetrail.__file__)
        ),
        "Imported runtime belongs to another checkout",
    )
    require(frozen["protocol_id"] == STUDY_ID, "Wrong study protocol")
    require(frozen["protocol"] == agent.PROTOCOL, "Runtime settings changed")
    require(
        frozen["prompt_sha256"] == sha_prompt(agent) == agent.PROMPT_SHA256,
        "Runtime prompt changed",
    )
    _, schemas = _runtime()
    require(
        frozen["schema_sha256"]
        == {name: canonical(cls.model_json_schema()) for name, cls in schemas.items()},
        "Runtime schemas changed",
    )
    sources = frozen["source_sha256"]
    actual_runtime = {
        p.relative_to(ROOT).as_posix() for p in (ROOT / "src/tracetrail").rglob("*.py")
    }
    require(actual_runtime <= sources.keys(), "Runtime source inventory is incomplete")
    require(SCRIPT.relative_to(ROOT).as_posix() in sources, "Runner source is not frozen")
    for name, expected in sources.items():
        require(sha(relative(name)) == expected, "Frozen source changed: " + name)
    import importlib.metadata

    for name, version in frozen["versions"].items():
        require(importlib.metadata.version(name) == version, "Installed version changed: " + name)
    for key in ("case_manifest", "semantic_rubric", "model_inventory", "baseline_contract"):
        entry = frozen[key]
        require(sha(relative(entry["path"])) == entry["sha256"], "Frozen input changed: " + key)
    cases = load_cases(relative(frozen["case_manifest"]["path"]))
    require(
        len(cases) == 2 and all(c["split"] == "heldout" for c in cases), "Need two heldout cases"
    )
    require([c["id"] for c in cases] == frozen["case_ids"], "Case order changed")
    require(
        frozen["cell_plan"] == plan_cells(frozen["case_ids"])
        and frozen["cell_plan_sha256"] == canonical(frozen["cell_plan"]),
        "Frozen assignment plan differs",
    )
    require(frozen["soft_launch_ceiling_seconds"] == CEILING, "Study launch ceiling changed")
    require(
        frozen["model"]["name"] == MODEL
        and frozen["model"]["digest"] == DIGEST
        and frozen["model"]["listed_digests"] == [DIGEST],
        "Reference model pin changed",
    )
    require(
        frozen["case_fixtures"] == {c["id"]: artifact(ROOT / c["fixture"]) for c in cases},
        "Fixture identity changed",
    )
    return frozen, cases


def sha_prompt(agent):
    return hashlib.sha256((agent.SYSTEM + agent.PLAN + agent.FINAL).encode()).hexdigest()


def private_write(path, value, *, create=False):
    from tracetrail.pilot import _write

    path = Path(path).expanduser()
    require(not path.is_symlink(), "Output cannot be a symbolic link")
    path = path.resolve()
    require(path.is_relative_to(ROOT / "local-results"), "Raw artifacts must stay in local-results")
    path.parent.mkdir(parents=True, exist_ok=True)
    _write(path, value, create=create)


def check_foreign_models():
    """Block before an assignment starts; never evict another application's model."""
    import ollama

    from tracetrail.agent import OLLAMA_URL

    client = ollama.Client(
        host=OLLAMA_URL,
        timeout=5,
        trust_env=False,
        follow_redirects=False,
        headers={"Authorization": "local-only-no-auth"},
    )
    try:
        require(
            not any(item.model != MODEL for item in client.ps().models),
            "Foreign model is loaded; preflight blocked before an attempted cell",
        )
    finally:
        client._client.close()


def freeze(args):
    with no_network():
        from tracetrail import agent
        from tracetrail.evaluation import load_cases
        from tracetrail.pilot import _runtime
        from tracetrail.support_evaluation import NUMERIC_METRIC_KEYS, scorer_fingerprint

        helper = module("heldout_freeze_helpers", SCRIPT.with_name("freeze_model_pilot_v1.py"))
        baseline_path = ROOT / "evaluation/protocol-v8.json"
        baseline = read(baseline_path)
        require(agent.PROTOCOL == baseline["protocol"], "Investigation controls differ from v8")
        require(sha_prompt(agent) == baseline["prompt_sha256"], "Prompt differs from v8")
        _, schemas = _runtime()
        schema_hashes = {n: canonical(c.model_json_schema()) for n, c in schemas.items()}
        require(schema_hashes == baseline["schema_sha256"], "Schemas differ from v8")
        manifest, rubric = args.manifest.resolve(), args.rubric.resolve()
        require(
            manifest.parent == rubric.parent == ROOT / "evaluation",
            "Manifest and rubric must be under evaluation",
        )
        cases = load_cases(manifest)
        require(
            len(cases) == 2 and all(c["split"] == "heldout" for c in cases),
            "Need two heldout cases",
        )
        inventory_path = ROOT / "evaluation/model-inventory-pilot-v1.json"
        inventory = read(inventory_path)
        models = helper.model_contracts(inventory)
        model = next(m for m in models if m["name"] == MODEL)
        require(model["digest"] == DIGEST, "Qwen inventory digest differs")
        paths = list((ROOT / "src/tracetrail").rglob("*.py")) + [
            ROOT / "pyproject.toml",
            ROOT / "uv.lock",
            SCRIPT,
            SCRIPT.with_name("freeze_model_pilot_v1.py"),
            SCRIPT.with_name("verify_model_pilot_v1.py"),
            SCRIPT.with_name("_v8_evaluation_contract.py"),
            rubric,
        ]
        cells = plan_cells([c["id"] for c in cases])
        document = {
            "schema_version": "1",
            "protocol_id": STUDY_ID,
            "phase": "frozen-synthetic-heldout-method-comparison",
            "case_split_at_freeze": "heldout",
            "frozen_at": utc(),
            "protocol": agent.PROTOCOL,
            "prompt_sha256": sha_prompt(agent),
            "schema_sha256": schema_hashes,
            "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
            "versions": helper.installed_versions(),
            "case_manifest": artifact(manifest),
            "semantic_rubric": artifact(rubric),
            "baseline_contract": artifact(baseline_path),
            "model_inventory": artifact(inventory_path),
            "model": model,
            "ollama_version": inventory["ollama_version"],
            "case_ids": [c["id"] for c in cases],
            "case_fixtures": {c["id"]: artifact(ROOT / c["fixture"]) for c in cases},
            "cell_plan": cells,
            "cell_plan_sha256": canonical(cells),
            "planned_runs": 8,
            "repeats": 2,
            "soft_launch_ceiling_seconds": CEILING,
            "in_flight_run_may_complete_after_ceiling": True,
            "outcome_based_expansion": False,
            "evaluation": {
                "primary_scorer": "claim-support-v1",
                **scorer_fingerprint(),
                "numeric_metric_keys": list(NUMERIC_METRIC_KEYS),
            },
            "returned_record_metrics": {
                "source_valid_unique_records_only": True,
                "includes_supplied_seed": True,
                "precision_empty_denominator_value": 0,
                "recall_denominator": "all frozen relevant_event_ids",
                "invalid_process_retains_raw_retrieval_metrics": True,
            },
            "limitations": [
                "Two assistant-authored synthetic case clusters, not independent human validation.",
                "Study documentation must establish first-use timing; "
                "this runner cannot certify prior exposure.",
                "Same-seed greedy repeats measure observed stability, not independent tasks.",
                "No prompt, schema, budget, tool or source repair after heldout outputs.",
                "All eight assigned cells and all requested claim slots keep their denominators.",
                "Semantic review is separate from exact mechanical annotation support.",
                "Resource sampling does not establish exclusive hardware use or true peak memory.",
            ],
            "safety": {"hosted_uploads": False, "local_only": True, "generator_model_calls": 0},
        }
        output = args.output.resolve()
        require(output.parent == ROOT / "evaluation", "Protocol output must be under evaluation")
        helper.write_exclusive(output, document)
        verify_protocol(output)
    return {"path": output.relative_to(ROOT).as_posix(), "sha256": sha(output), "planned_runs": 8}


def attempt_digest(result):
    return canonical(
        {
            **result,
            "heldout": {k: v for k, v in result["heldout"].items() if k != "attempt_sha256"},
        }
    )


def validate_saved(data, frozen, protocol_sha):
    require(
        data["frozen_identity"] == {"protocol_id": STUDY_ID, "protocol_sha256": protocol_sha}
        and data["plan"] == frozen["cell_plan"]
        and data["protocol"] == frozen["protocol"]
        and data["case_manifest_path"] == frozen["case_manifest"]["path"]
        and data["case_manifest_sha256"] == frozen["case_manifest"]["sha256"]
        and data["evaluation"] == {"primary_scorer": "claim-support-v1"}
        and data["test_only"] is False
        and data["study_id"] == STUDY_ID
        and data["case_split_at_freeze"] == "heldout"
        and data["planned_runs"] == 8,
        "Saved study identity differs",
    )
    runs = data["runs"]
    require(isinstance(runs, list) and len(runs) <= 8, "Invalid attempt count")
    for index, run in enumerate(runs):
        meta = run["heldout"]
        require(meta["cell"] == frozen["cell_plan"][index], "Attempt is not the exact plan prefix")
        wall = meta["wall_seconds"]
        require(
            type(wall) in (int, float) and math.isfinite(wall) and wall >= 0, "Invalid cell timing"
        )
        require(run["test_only"] is False, "Test-only output cannot enter this study")
        require(meta["attempt_sha256"] == attempt_digest(run), "Saved attempt metadata changed")
        if run["status"] == "running":
            require(index == len(runs) - 1 and wall == 0, "Invalid in-flight attempt")
        else:
            require(
                meta["result_sha256"]
                == canonical({k: v for k, v in run.items() if k != "heldout"}),
                "Saved attempt payload changed",
            )


def run(args):
    from tracetrail.pilot import _execute, _failure, _output_lock, _score

    frozen, cases = verify_protocol(args.protocol)
    fingerprint = sha(args.protocol)
    output = args.output.expanduser()
    require(not output.is_symlink(), "Output cannot be a symbolic link")
    output = output.resolve()
    require(output.is_relative_to(ROOT / "local-results"), "Raw output must stay in local-results")
    require(args.max_runs is None or 1 <= args.max_runs <= 8, "max-runs must be from 1 to 8")
    case_map = {c["id"]: c for c in cases}
    with _output_lock(output):
        if output.exists():
            require(args.resume, "Output exists; choose a new path or explicit resume")
            data = read(output)
            validate_saved(data, frozen, fingerprint)
        else:
            require(not args.resume, "No existing output to resume")
            data = {
                "study_id": STUDY_ID,
                "experiment_id": str(uuid4()),
                "created_at": utc(),
                "frozen_identity": {"protocol_id": STUDY_ID, "protocol_sha256": fingerprint},
                "suite_id": cases[0]["_suite_id"],
                "case_manifest_path": frozen["case_manifest"]["path"],
                "case_manifest_sha256": frozen["case_manifest"]["sha256"],
                "selected_cases": frozen["case_ids"],
                "protocol": frozen["protocol"],
                "evaluation": {"primary_scorer": "claim-support-v1"},
                "test_only": False,
                "case_split_at_freeze": "heldout",
                "planned_runs": 8,
                "plan": frozen["cell_plan"],
                "runs": [],
            }
            private_write(output, data, create=True)
        for result in data["runs"]:
            if result["status"] == "running":
                result["status"] = "failed"
                result["failures"] = [
                    {"phase": "heldout_interrupted", "error_type": "IncompleteRecordedAttempt"}
                ]
                result["inference_calls_unknown"] = True
                result["heldout"]["wall_seconds_unknown"] = True
                _score(case_map[result["case_id"]], result)
                result["heldout"]["result_sha256"] = canonical(
                    {k: v for k, v in result.items() if k != "heldout"}
                )
                result["heldout"]["attempt_sha256"] = attempt_digest(result)
        # Persist a killed attempt as a failure even if its unknown timing blocks
        # further launches. A later resume cannot silently retry that assignment.
        private_write(output, data)
        limit = args.max_runs or 8
        stop = "requested_limit_reached"
        while len(data["runs"]) < limit:
            require(
                not any(r.get("inference_calls_unknown") for r in data["runs"]),
                "Interrupted attempt has unknown calls; no further launches",
            )
            if sum(r["heldout"]["wall_seconds"] for r in data["runs"]) >= CEILING:
                stop = "soft_launch_ceiling_reached"
                break
            current, _ = verify_protocol(args.protocol)
            require(
                current == frozen and sha(args.protocol) == fingerprint,
                "Protocol changed during study",
            )
            check_foreign_models()
            cell = frozen["cell_plan"][len(data["runs"])]
            case = case_map[cell["case_id"]]
            print(f"Running {cell['cell_id']}", file=sys.stderr, flush=True)
            started = utc()
            result = _failure(case, cell, "heldout_started", RuntimeError("Attempt in progress"))
            result["status"] = "running"
            result["heldout"] = {"cell": cell, "started_at": started, "wall_seconds": 0.0}
            result["heldout"]["attempt_sha256"] = attempt_digest(result)
            data["runs"].append(result)
            private_write(output, data)
            began = time.monotonic()
            interrupted = False
            try:
                result = _execute(case, ROOT, cell, frozen["model"])
            except (Exception, KeyboardInterrupt) as exc:
                interrupted = isinstance(exc, KeyboardInterrupt)
                result = _failure(
                    case, cell, "heldout_interrupted" if interrupted else "heldout_runner", exc
                )
                # A thrown exception can follow real inference. Do not turn an
                # unavailable partial history into a claim of zero model calls.
                result["inference_calls_unknown"] = True
                _score(case, result)
            result["heldout"] = {
                "cell": cell,
                "started_at": started,
                "finished_at": utc(),
                "wall_seconds": time.monotonic() - began,
                "result_sha256": canonical(result),
            }
            result["heldout"]["attempt_sha256"] = attempt_digest(result)
            data["runs"][-1] = result
            private_write(output, data)
            if result.get("inference_calls_unknown"):
                stop = "interrupted" if interrupted else "execution_history_unknown"
                break
        data["overall_wall_seconds"] = sum(r["heldout"]["wall_seconds"] for r in data["runs"])
        data["soft_launch_ceiling_seconds"] = CEILING
        data["stop_reason"] = stop
        data["attempted_all_target_cells"] = len(data["runs"]) == 8
        data["status"] = (
            "completed"
            if len(data["runs"]) == 8 and all(r["status"] == "completed" for r in data["runs"])
            else "incomplete"
        )
        private_write(output, data)
    return {"path": str(output), "status": data["status"], "attempts": len(data["runs"])}


def _verify_data(args):
    with no_network():
        frozen, cases = verify_protocol(args.protocol)
        raw = read(args.raw)
        raw_sha = sha(args.raw)
        validate_saved(raw, frozen, sha(args.protocol))
        require(
            not any(r["status"] == "running" for r in raw["runs"]),
            "In-flight attempt cannot be finalized",
        )
        helper = module("heldout_audit_helpers", SCRIPT.with_name("verify_model_pilot_v1.py"))
        old = helper.old_helpers()
        case_map = {c["id"]: c for c in cases}
        rows = []
        for index, result in enumerate(raw["runs"]):
            cell = frozen["cell_plan"][index]
            case = case_map[cell["case_id"]]
            require(
                result["case_id"] == case["id"] and result["split"] == "heldout",
                "Case labels differ",
            )
            require(
                result["model"] == MODEL and result["strategy"] == cell["strategy"],
                "Method labels differ",
            )
            require(result["fixture_sha256"] == case["fixture_sha256"], "Fixture label differs")
            identity = helper.identity_for(result, frozen["model"])
            original_spans = {}
            replays = 0
            if "model_history" in result:
                require(result["protocol"] == frozen["protocol"], "Run controls differ")
                require(result["prompt_sha256"] == frozen["prompt_sha256"], "Run prompt differs")
                require(result["trace_storage"] == "local-only", "Trace storage differs")
                original_spans = dict(old.verify_history(case, result, frozen))
                helper.verify_model_metadata(result, frozen, old)
                replays = helper.replay_tools(ROOT, case, result, old)
                helper.verify_resources(result, DIGEST)
            else:
                require(
                    result["status"] == "failed" and result.get("inference_completed") is False,
                    "Unlabeled non-graph failure",
                )
                require(
                    not result.get("local_traces") and not result.get("model_calls"),
                    "Preflight failure contains unexplained inference",
                )
            derived, per_claim = old.independent_support(case, result)
            for key, value in derived.items():
                old.check_close(
                    result["claim_support_metrics"][key], value, "Support counter differs: " + key
                )
            require(
                old.same(result["metrics"], old.score_run(case, result)), "Legacy counters differ"
            )
            if not identity["verified"]:
                require(
                    not derived["process_valid"]
                    and derived["process_valid_supported_claim_count"] == 0,
                    "Identity-invalid report earns primary credit",
                )
            rows.append(
                {
                    "result_index": index,
                    "cell": cell,
                    "status": result["status"],
                    "independent_support": {"numeric": derived, "per_claim": per_claim},
                    "actual_original_span_counts": original_spans,
                    "read_only_tool_replays": replays,
                    "tokens": helper.token_summary(result)["totals"],
                    "verified": True,
                }
            )
        sdk_report = {"status": "not-requested"}
        if args.sdk is not None:
            sdk = read(args.sdk)
            sdk_report = helper.verify_sdk(sdk, raw, raw_sha, rows, frozen, old)
        require(sha(args.raw) == raw_sha, "Raw input changed during verification")
        verify_protocol(args.protocol)
        return (
            frozen,
            raw,
            {
                "schema_version": "1",
                "status": "verified",
                "mode": "stored-first-use-heldout-verification",
                "new_model_calls": 0,
                "sdk_evaluations_performed": 0,
                "uploads_enabled": False,
                "semantic_entailment_verified": False,
                "protocol_sha256": sha(args.protocol),
                "raw_sha256": raw_sha,
                "sdk_sha256": sha(args.sdk) if args.sdk else None,
                "planned_runs": 8,
                "finished_attempts": len(rows),
                "sdk": sdk_report,
                "rows": rows,
            },
        )


def verify_data(args):
    # Historical auditors block inference globally when imported. Restore that
    # production entry point for callers that use this helper in-process.
    from tracetrail import agent

    original_model = agent.make_model
    try:
        return _verify_data(args)
    finally:
        agent.make_model = original_model


def verify(args):
    _, _, report = verify_data(args)
    private_write(args.output, report, create=True)
    return {
        "path": str(args.output),
        "sha256": sha(args.output),
        "status": report["status"],
        "finished_attempts": report["finished_attempts"],
    }


def summary(args):
    from tracetrail.evaluation import load_cases

    require(args.sdk is not None, "Final public summary requires the real offline SDK artifact")
    frozen, raw, audit = verify_data(args)
    require(len(raw["runs"]) == 8, "Final public summary requires all eight assigned attempts")
    cases = {c["id"]: c for c in load_cases(relative(frozen["case_manifest"]["path"]))}
    rows = []
    for result, verified in zip(raw["runs"], audit["rows"], strict=True):
        case = cases[result["case_id"]]
        refs = {
            f"sha256:{case['fixture_sha256']}/Records/{i}": r
            for i, r in enumerate(case["_fixture_records"])
        }
        returned = {
            ref for ref, record in refs.items() if record["eventID"] == case["seed_event_id"]
        }
        for entry in result.get("tool_history", []):
            payload = entry.get("result") or {}
            for item in payload.get("records", [payload]):
                if item.get("ref") in refs and item.get("record") == refs[item["ref"]]:
                    returned.add(item["ref"])
        relevant = {
            ref for ref, record in refs.items() if record["eventID"] in case["relevant_event_ids"]
        }
        rows.append(
            {
                **verified["cell"],
                "status": result["status"]
                if result["status"] in ("completed", "invalid", "failed", "degraded")
                else "other",
                "raw_result_sha256": result["heldout"]["result_sha256"],
                "claim_support_metrics": verified["independent_support"]["numeric"],
                "selected_event_precision": result["metrics"]["relevant_event_precision"],
                "selected_event_recall": result["metrics"]["relevant_event_recall"],
                "returned_event_precision": len(returned & relevant) / len(returned)
                if returned
                else 0,
                "returned_event_recall": len(returned & relevant) / len(relevant),
                "returned_event_count": len(returned),
                "actual_model_calls": result.get("model_calls", 0),
                "actual_tool_calls": result.get("query_count", 0),
                "actual_calls_unknown": result.get("inference_calls_unknown", False),
                "wall_seconds": result["heldout"]["wall_seconds"],
                "investigation_seconds": result.get("duration_seconds")
                if type(result.get("duration_seconds")) in (int, float)
                else None,
                "tokens": verified["tokens"],
                "actual_original_span_counts": verified["actual_original_span_counts"],
            }
        )
    document = {
        "schema_version": "1",
        "study_id": STUDY_ID,
        "phase": frozen["phase"],
        "created_at": utc(),
        "protocol_sha256": sha(args.protocol),
        "raw_sha256": audit["raw_sha256"],
        "sdk_sha256": audit["sdk_sha256"],
        "planned_runs": 8,
        "attempted_runs": len(rows),
        "claim_slots": sum(r["claim_support_metrics"]["annotated_claim_count"] for r in rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "recorded_model_calls": sum(r["actual_model_calls"] for r in rows),
        "recorded_tool_calls": sum(r["actual_tool_calls"] for r in rows),
        "actual_calls_unknown_attempts": sum(r["actual_calls_unknown"] for r in rows),
        "overall_wall_seconds": sum(r["wall_seconds"] for r in rows),
        "sdk": audit["sdk"],
        "independent_human_review": False,
        "semantic_review_included": False,
        "limitations": frozen["limitations"],
        "rows": rows,
    }
    output = args.output.resolve()
    require(output.parent == ROOT / "evaluation", "Public numeric output must be under evaluation")
    with no_network():
        helper = module("heldout_summary_write", SCRIPT.with_name("freeze_model_pilot_v1.py"))
        helper.write_exclusive(output, document)
    return {"path": output.relative_to(ROOT).as_posix(), "sha256": sha(output), "attempted_runs": 8}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("freeze")
    command.add_argument("--manifest", type=Path, default=ROOT / "evaluation/cases-v9.json")
    command.add_argument("--rubric", type=Path, default=ROOT / "evaluation/heldout-v9-rubric.md")
    command.add_argument(
        "--output", type=Path, default=ROOT / "evaluation/protocol-heldout-v9.json"
    )
    command = sub.add_parser("run")
    command.add_argument("--protocol", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--resume", action="store_true")
    command.add_argument("--max-runs", type=int)
    for name in ("verify", "summary"):
        command = sub.add_parser(name)
        command.add_argument("--protocol", type=Path, required=True)
        command.add_argument("--raw", type=Path, required=True)
        command.add_argument("--sdk", type=Path)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = {"freeze": freeze, "run": run, "verify": verify, "summary": summary}[args.command](
            args
        )
        print(json.dumps(result, sort_keys=True))
        return int(args.command == "run" and result["status"] != "completed")
    except (ValueError, OSError, KeyError, AssertionError) as exc:
        print(f"Heldout study stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
