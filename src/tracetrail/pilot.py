"""Staged, resumable local model pilot. This module never pulls model weights."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

PILOT_ID = "tracetrail-model-pilot-v1"
_CEILING = 5400
_OVERHEAD = 1.2


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _read(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    result = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique,
        parse_constant=invalid_constant,
    )
    if not isinstance(result, dict):
        raise ValueError("Pilot documents must contain a JSON object")
    return result


def _relative(root: Path, value: str) -> Path:
    if not isinstance(value, str) or Path(value).is_absolute():
        raise ValueError("Frozen paths must be relative to the repository")
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Frozen paths must stay within the repository")
    return path


def _runtime():
    # The runner imports this module only when explicitly invoked. Keeping cli
    # lazy also permits the main CLI to expose this runner without an import cycle.
    from tracetrail import agent
    from tracetrail.planning import ClaimPlan, Decision, PivotDisposition
    from tracetrail.store import Query

    schemas = {
        "claim_plan": ClaimPlan,
        "decision": Decision,
        "evidence_link": agent.EvidenceLink,
        "materialized_analysis": agent.Analysis,
        "model_finding": agent.FindingSelection,
        "model_report_selection": agent.ReportSelection,
        "pivot_disposition": PivotDisposition,
        "query": Query,
    }
    return agent, schemas


def _run_case(case, root, model, strategy):
    from tracetrail.cli import run_case

    return run_case(case, root, model, strategy, measure_resources=True)


def _score(case, result):
    from tracetrail.cli import score_result

    score_result(case, result)


def _model_info(name):
    from tracetrail.local_model import verify_local_weights

    return verify_local_weights(name)


def verify_protocol(protocol_path: Path) -> tuple[dict, Path, list[dict]]:
    """Check the whole frozen local input before launching any model call."""
    from tracetrail.evaluation import load_cases

    protocol_path = protocol_path.resolve()
    root = protocol_path.parent.parent
    frozen = _read(protocol_path)
    if frozen.get("protocol_id") != PILOT_ID:
        raise ValueError("Unsupported pilot protocol")
    agent, schemas = _runtime()
    import tracetrail

    expected_package = root / "src" / "tracetrail"
    if any(
        Path(value).resolve().parent != expected_package
        for value in (__file__, agent.__file__, tracetrail.__file__)
    ):
        raise ValueError("The protocol must belong to this exact imported runtime checkout")
    if frozen.get("protocol") != agent.PROTOCOL:
        raise ValueError("Frozen model settings do not match the runtime")
    prompt = hashlib.sha256((agent.SYSTEM + agent.PLAN + agent.FINAL).encode()).hexdigest()
    if frozen.get("prompt_sha256") != prompt:
        raise ValueError("Frozen prompt does not match the runtime")
    actual_schemas = {name: _canonical(cls.model_json_schema()) for name, cls in schemas.items()}
    if frozen.get("schema_sha256") != actual_schemas:
        raise ValueError("Frozen schemas do not match the runtime")
    sources = frozen.get("source_sha256")
    runtime_sources = {
        path.relative_to(root).as_posix() for path in (root / "src" / "tracetrail").rglob("*.py")
    }
    if (
        not isinstance(sources, dict)
        or not runtime_sources
        or not runtime_sources <= sources.keys()
    ):
        raise ValueError("The protocol must pin every Python runtime source")
    for relative, digest in sources.items():
        if _sha(_relative(root, relative)) != digest:
            raise ValueError(f"Frozen source hash mismatch: {relative}")
    installed_sources = {
        "src/tracetrail/" + path.relative_to(Path(__file__).parent).as_posix(): path
        for path in Path(__file__).parent.rglob("*.py")
    }
    if not installed_sources.keys() <= sources.keys():
        raise ValueError("The protocol must pin the installed Python runtime sources")
    for relative, path in installed_sources.items():
        if _sha(path) != sources[relative]:
            raise ValueError(f"Installed runtime source hash mismatch: {relative}")
    for relative, digest in frozen.get("dependency_sha256", {}).items():
        if _sha(_relative(root, relative)) != digest:
            raise ValueError(f"Frozen dependency hash mismatch: {relative}")
    versions = frozen.get("versions", {})
    required_packages = {
        "langchain",
        "langchain-core",
        "langchain-ollama",
        "langgraph",
        "langsmith",
        "ollama",
        "pydantic",
    }
    if not isinstance(versions, dict) or not required_packages <= versions.keys():
        raise ValueError("The protocol must pin every model integration package version")
    for package, version in versions.items():
        if importlib.metadata.version(package) != version:
            raise ValueError(f"Frozen package version mismatch: {package}")
    for key in ("model_inventory", "semantic_rubric"):
        if key in frozen:
            entry = frozen[key]
            if _sha(_relative(root, entry["path"])) != entry["sha256"]:
                raise ValueError(f"Frozen {key} hash mismatch")
    manifest = frozen.get("case_manifest", {})
    manifest_path = _relative(root, manifest.get("path"))
    if manifest_path.parent != root / "evaluation" or _sha(manifest_path) != manifest.get("sha256"):
        raise ValueError("Frozen case manifest hash or location mismatch")
    cases = {case["id"]: case for case in load_cases(manifest_path)}
    pilot = frozen.get("pilot", {})
    case_ids = pilot.get("case_ids", [])
    models = pilot.get("models", [])
    if (
        not isinstance(case_ids, list)
        or len(case_ids) != 2
        or len(set(case_ids)) != 2
        or any(case_id not in cases for case_id in case_ids)
        or any(cases[case_id]["split"] != "development" for case_id in case_ids)
        or pilot.get("repeats") != 2
    ):
        raise ValueError("The pilot requires two exposed development cases and two repeats")
    if not isinstance(models, list) or len(models) != 5:
        raise ValueError("The pilot requires exactly five pinned models")
    names = []
    for model in models:
        name = model.get("name")
        listed = model.get("listed_digests")
        digest = model.get("digest")
        if (
            name not in agent.MODELS
            or not isinstance(digest, str)
            or not digest
            or not isinstance(listed, list)
            or not listed
            or any(not isinstance(value, str) or not value for value in listed)
            or len(set(listed)) != len(listed)
            or digest not in listed
            or not isinstance(model.get("ollama_version"), str)
            or not model["ollama_version"]
        ):
            raise ValueError("Every pilot model needs an approved tag and pinned local digests")
        names.append(name)
    if len(set(names)) != 5:
        raise ValueError("Pilot model tags must be unique")
    gate = frozen.get("runtime_gate", {})
    if (
        gate.get("overall_wall_seconds", _CEILING) != _CEILING
        or gate.get("overhead_factor", _OVERHEAD) != _OVERHEAD
    ):
        raise ValueError(
            "The pilot runtime gate must retain the 90-minute ceiling and 20% overhead"
        )
    return frozen, root, [cases[case_id] for case_id in case_ids]


def plan_cells(frozen: dict) -> list[dict]:
    """Return a fixed 40-cell schedule; ordering never depends on model quality."""
    cells = []
    for repeat in (1, 2):
        for case_index, case_id in enumerate(frozen["pilot"]["case_ids"]):
            stage = case_index + 1 if repeat == 1 else 3
            for model_index, model in enumerate(frozen["pilot"]["models"]):
                strategies = ("adaptive", "fixed")
                if (model_index + case_index + repeat - 1) % 2:
                    strategies = tuple(reversed(strategies))
                for strategy in strategies:
                    cells.append(
                        {
                            "cell_id": f"r{repeat}-c{case_index + 1}-m{model_index + 1}-{strategy}",
                            "plan_index": len(cells) + 1,
                            "stage": stage,
                            "case_index": case_index + 1,
                            "model_index": model_index + 1,
                            "case_id": case_id,
                            "model": model["name"],
                            "strategy": strategy,
                            "repeat": repeat,
                        }
                    )
    return cells


@contextmanager
def _output_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.pilot.lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another pilot invocation owns this output") from exc
        yield
    finally:
        os.close(fd)


def _write(path: Path, data: dict, *, create: bool = False):
    if path.is_symlink():
        raise ValueError("Pilot output cannot be a symbolic link")
    fd, temporary = tempfile.mkstemp(prefix=".tracetrail-pilot-", suffix=".json", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if create:
            os.link(temporary_path, path)  # Atomic, and refuses an existing destination.
        else:
            temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _resource_issues(result: dict) -> list[str]:
    resources = result.get("model_info", {}).get("resources", {})
    if not isinstance(resources, dict):
        return ["resource_measurements_missing"]
    issues = []
    if resources.get("status") != "completed":
        issues.append("resource_measurements_not_complete")
    count = resources.get("sample_count", 0)
    if not isinstance(count, int) or count <= 0:
        issues.append("resource_samples_missing")
    if resources.get("error_count", 0):
        issues.append("resource_measurement_errors")
    if resources.get("foreign_model_observed"):
        issues.append("foreign_model_observed")
    if resources.get("ollama_sample_count") != count:
        issues.append("ollama_samples_incomplete")
    if resources.get("rss_complete_sample_count") != count:
        issues.append("process_rss_samples_incomplete")
    if not resources.get("matching_model_sample_count", 0):
        issues.append("matching_model_samples_missing")
    if resources.get("sample_limit_reached"):
        issues.append("resource_sampling_limit_reached")
    maxima = resources.get("sampled_maxima", {})
    for key in (
        "ollama_reported_size_bytes",
        "ollama_reported_size_vram_bytes",
        "listener_process_tree_rss_sum_bytes",
    ):
        value = maxima.get(key) if isinstance(maxima, dict) else None
        if type(value) is not int or value < 0:
            issues.append(f"missing_or_invalid_{key}")
    if result.get("pilot", {}).get("wall_seconds_unknown"):
        issues.append("interrupted_attempt_wall_time_unknown")
    if result.get("pilot_model_identity", {}).get("verified") is not True:
        issues.append("runtime_model_identity_not_verified")
    return issues


def _gate(data: dict) -> None:
    if data["runtime_gate"] is not None or len(data["runs"]) < 10:
        return
    first = data["runs"][:10]
    seconds = sum(run["pilot"]["wall_seconds"] for run in first)
    issues = sorted({issue for run in first for issue in _resource_issues(run)})
    forty = _OVERHEAD * 4 * seconds
    data["runtime_gate"] = {
        "recorded_at": _utc(),
        "based_on_plan_indices": list(range(1, 11)),
        "first_ten_wall_seconds": seconds,
        "projected_twenty_seconds_with_overhead": _OVERHEAD * 2 * seconds,
        "projected_forty_seconds_with_overhead": forty,
        "overhead_factor": _OVERHEAD,
        "overall_wall_ceiling_seconds": _CEILING,
        "soft_launch_ceiling_seconds": _CEILING,
        "overall_wall_ceiling_is_soft": True,
        "resource_measurement_issues": issues,
        "foreign_model_observed": "foreign_model_observed" in issues,
        "external_process_isolation_guaranteed": False,
        "max_total_runs": 40 if forty <= _CEILING and not issues else 20,
        "decision_basis": "first-ten-runtime-only; no quality-based expansion",
    }


def _validate_saved(data: dict, identity: dict, plan: list[dict]) -> None:
    if data.get("frozen_identity") != identity or data.get("plan") != plan:
        raise ValueError("Resume requires the identical frozen protocol and cell plan")
    runs = data.get("runs")
    if not isinstance(runs, list) or len(runs) > len(plan):
        raise ValueError("Saved pilot runs are invalid")
    for expected, run in zip(plan, runs, strict=False):
        if not isinstance(run, dict) or run.get("pilot", {}).get("cell") != expected:
            raise ValueError("Saved pilot cells must form the exact ordered plan prefix")
        seconds = run["pilot"].get("wall_seconds")
        if (
            not isinstance(seconds, (int, float))
            or isinstance(seconds, bool)
            or not math.isfinite(seconds)
            or seconds < 0
            or run.get("test_only") is not False
        ):
            raise ValueError("Saved pilot cell timing or inference labeling is invalid")
        payload = {key: value for key, value in run.items() if key != "pilot"}
        if run.get("status") != "running" and run["pilot"].get("result_sha256") != _canonical(
            payload
        ):
            raise ValueError("Saved pilot result payload hash mismatch")
    gate = data.get("runtime_gate")
    if len(runs) >= 10 and gate is not None:
        reconstructed = {"runs": runs[:10], "runtime_gate": None}
        _gate(reconstructed)
        expected_gate = reconstructed["runtime_gate"]
        if {k: v for k, v in gate.items() if k != "recorded_at"} != {
            k: v for k, v in expected_gate.items() if k != "recorded_at"
        }:
            raise ValueError("The saved first-stage runtime gate does not match its cells")
    elif gate is not None:
        raise ValueError("A runtime gate cannot precede the first ten cells")
    if len(runs) > 10 and gate is None:
        raise ValueError("Later cells require the saved first-stage runtime gate")
    if len(runs) > 20 and gate["max_total_runs"] != 40:
        raise ValueError("Repeat two was not authorized by the saved runtime gate")


def _failure(case: dict, cell: dict, phase: str, exc: BaseException) -> dict:
    return {
        "case_id": case["id"],
        "split": case["split"],
        "fixture_sha256": case["fixture_sha256"],
        "model": cell["model"],
        "strategy": cell["strategy"],
        "status": "failed",
        "test_only": False,
        "failures": [{"phase": phase, "error_type": type(exc).__name__}],
        "error": str(exc),
        "inference_completed": False,
    }


def _execute(case, root, cell, model) -> dict:
    info = _model_info(model["name"])
    if (
        info.get("name") != model["name"]
        or set(info.get("listed_digests", [])) != set(model["listed_digests"])
        or model["digest"] not in info.get("listed_digests", [])
        or info.get("remote_routing") is not False
        or info.get("ollama_version") != model["ollama_version"]
    ):
        raise ValueError("Installed model metadata differs from the frozen local inventory")
    result = _run_case(case, root, cell["model"], cell["strategy"])
    if not isinstance(result, dict):
        raise ValueError("The actual case runner did not return a result object")
    loaded = result.get("model_info", {}).get("loaded_models", [])
    effective = [entry.get("digest") for entry in loaded if entry.get("model") == model["name"]]
    identity_valid = effective == [model["digest"]]
    listed_valid = set(result.get("model_info", {}).get("listed_digests", [])) == set(
        model["listed_digests"]
    )
    result["pilot_model_identity"] = {
        "expected_runtime_digest": model["digest"],
        "observed_runtime_digests": effective,
        "listed_digests_match": listed_valid,
        "verified": identity_valid and listed_valid,
    }
    if not identity_valid or not listed_valid:
        result["failures"].append(
            {"phase": "pilot_model_identity", "error_type": "FrozenModelIdentityMismatch"}
        )
        result["status"] = "invalid"
        _score(case, result)
    return result


def run_pilot(
    protocol_path: str | Path,
    output_path: str | Path,
    *,
    stage: int = 1,
    max_runs: int | None = None,
    resume: bool = False,
) -> int:
    """Run only the requested cumulative stage. Failed attempts are never retried."""
    if type(stage) is not int or stage not in (1, 2, 3):
        raise ValueError("Pilot stage must be 1, 2 or 3")
    if max_runs is not None and (type(max_runs) is not int or not 1 <= max_runs <= 40):
        raise ValueError("max_runs must be a cumulative cell limit from 1 to 40")
    protocol_path = Path(protocol_path).resolve()
    requested = Path(output_path).expanduser()
    if requested.is_symlink():
        raise ValueError("Pilot output cannot be a symbolic link")
    output_path = requested.resolve()
    frozen, root, cases = verify_protocol(protocol_path)
    if not output_path.is_relative_to(root / "local-results"):
        raise ValueError("Pilot output must stay in the ignored local-results directory")
    protected = {protocol_path, _relative(root, frozen["case_manifest"]["path"])}
    protected.update(_relative(root, name) for name in frozen["source_sha256"])
    protected.update(_relative(root, name) for name in frozen.get("dependency_sha256", {}))
    protected.update(_relative(root, case["fixture"]) for case in cases)
    protected.update(
        _relative(root, frozen[key]["path"])
        for key in ("model_inventory", "semantic_rubric")
        if key in frozen
    )
    if output_path in protected:
        raise ValueError("Pilot output cannot replace a frozen input")
    plan = plan_cells(frozen)
    identity = {
        "protocol_id": PILOT_ID,
        "protocol_sha256": _sha(protocol_path),
        "plan_sha256": _canonical(plan),
    }
    case_map = {case["id"]: case for case in cases}
    models = {model["name"]: model for model in frozen["pilot"]["models"]}
    with _output_lock(output_path):
        if output_path.exists():
            if not resume:
                raise FileExistsError("Pilot output exists; use a new path or explicit --resume")
            data = _read(output_path)
            _validate_saved(data, identity, plan)
            if (
                data.get("protocol") != frozen["protocol"]
                or data.get("case_manifest_path") != frozen["case_manifest"]["path"]
                or data.get("case_manifest_sha256") != frozen["case_manifest"]["sha256"]
                or data.get("suite_id") != cases[0]["_suite_id"]
                or data.get("test_only") is not False
                or data.get("evaluation") != {"primary_scorer": "claim-support-v1"}
            ):
                raise ValueError("Saved pilot envelope differs from the frozen experiment")
        elif resume:
            raise FileNotFoundError("There is no pilot output to resume")
        else:
            if stage != 1:
                raise ValueError(
                    "A new pilot must start with stage 1; expansion needs explicit resume"
                )
            data = {
                "schema_version": "1",
                "pilot_id": PILOT_ID,
                "experiment_id": str(uuid4()),
                "created_at": _utc(),
                "frozen_identity": identity,
                "suite_id": cases[0]["_suite_id"],
                "case_manifest_path": frozen["case_manifest"]["path"],
                "case_manifest_sha256": frozen["case_manifest"]["sha256"],
                "selected_cases": [case["id"] for case in cases],
                "protocol_path": protocol_path.relative_to(root).as_posix(),
                "protocol": frozen["protocol"],
                "evaluation": {"primary_scorer": "claim-support-v1"},
                "test_only": False,
                "exposed_development_only": True,
                "plan": plan,
                "runs": [],
                "runtime_gate": None,
                "invocations": [],
            }
            _write(output_path, data, create=True)
        if stage > 1 and len(data["runs"]) < 10:
            raise ValueError("Complete the ten-cell first stage before requesting expansion")
        # A killed process leaves a recorded attempt. Preserve it rather than
        # silently repeating inference whose completion cannot be established.
        for run in data["runs"]:
            if run.get("status") == "running":
                run["status"] = "failed"
                run["failures"] = [
                    {"phase": "pilot_interrupted", "error_type": "IncompleteRecordedAttempt"}
                ]
                run["inference_completed"] = False
                run["inference_calls_unknown"] = True
                run["pilot"]["wall_seconds_unknown"] = True
                _score(case_map[run["pilot"]["cell"]["case_id"]], run)
                run["pilot"]["result_sha256"] = _canonical(
                    {key: value for key, value in run.items() if key != "pilot"}
                )
        invocation = {"started_at": _utc(), "stage": stage, "max_runs": max_runs}
        data["invocations"].append(invocation)
        limit = (10, 20, 40)[stage - 1]
        if max_runs is not None:
            limit = min(limit, max_runs)
        stopped = None
        while len(data["runs"]) < limit:
            _gate(data)
            gate = data["runtime_gate"]
            if len(data["runs"]) >= 20 and (gate is None or gate["max_total_runs"] < 40):
                stopped = "repeat_two_blocked_by_recorded_runtime_gate"
                break
            if len(data["runs"]) >= 20:
                issues = sorted({issue for run in data["runs"] for issue in _resource_issues(run)})
                if issues:
                    data["repeat_two_safety_block"] = {
                        "recorded_at": _utc(),
                        "resource_measurement_issues": issues,
                    }
                    stopped = "repeat_two_blocked_by_resource_measurements"
                    break
            elapsed = sum(run["pilot"]["wall_seconds"] for run in data["runs"])
            if elapsed >= _CEILING:
                stopped = "overall_wall_ceiling_reached"
                break
            # Check source and fixture drift again before every actual attempt.
            current, _, _ = verify_protocol(protocol_path)
            if current != frozen or _sha(protocol_path) != identity["protocol_sha256"]:
                raise ValueError("Frozen protocol changed during the pilot")
            cell = plan[len(data["runs"])]
            case = case_map[cell["case_id"]]
            print(
                f"Running {cell['cell_id']} | {cell['model']} | "
                f"{cell['case_id']} | {cell['strategy']}",
                file=sys.stderr,
                flush=True,
            )
            started = _utc()
            placeholder = _failure(case, cell, "pilot_started", RuntimeError("Attempt in progress"))
            placeholder["status"] = "running"
            placeholder["pilot"] = {"cell": cell, "started_at": started, "wall_seconds": 0.0}
            data["runs"].append(placeholder)
            _write(output_path, data)
            began = time.monotonic()
            interrupted = False
            try:
                result = _execute(case, root, cell, models[cell["model"]])
            except (Exception, KeyboardInterrupt) as exc:
                interrupted = isinstance(exc, KeyboardInterrupt)
                result = _failure(
                    case, cell, "pilot_interrupted" if interrupted else "pilot_runner", exc
                )
                if interrupted:
                    result["inference_calls_unknown"] = True
                _score(case, result)
            wall = time.monotonic() - began
            if result.get("test_only") is not False:
                raise ValueError("Pilot output must be actual inference, not a test-only report")
            result["pilot"] = {
                "cell": cell,
                "started_at": started,
                "finished_at": _utc(),
                "wall_seconds": wall,
                "run_deadline_seconds": frozen["protocol"]["run_deadline_seconds"],
                "wall_exceeds_agent_deadline": wall > frozen["protocol"]["run_deadline_seconds"],
                "result_sha256": _canonical(result),
            }
            data["runs"][-1] = result
            _gate(data)
            _write(output_path, data)
            if interrupted:
                stopped = "interrupted"
                break
        _gate(data)
        data["overall_wall_seconds"] = sum(run["pilot"]["wall_seconds"] for run in data["runs"])
        data["soft_launch_ceiling_seconds"] = _CEILING
        data["overall_wall_ceiling_is_soft"] = True
        data["overall_wall_overrun_seconds"] = max(0.0, data["overall_wall_seconds"] - _CEILING)
        invocation["finished_at"] = _utc()
        invocation["stop_reason"] = stopped or "requested_cumulative_limit_reached"
        data["target_runs"] = (data["runtime_gate"] or {}).get("max_total_runs", 40)
        data["attempted_all_target_cells"] = len(data["runs"]) == data["target_runs"]
        data["status"] = (
            "completed"
            if len(data["runs"]) == data["target_runs"]
            and all(r["status"] == "completed" for r in data["runs"])
            else "incomplete"
        )
        _write(output_path, data)
        return int(data["status"] != "completed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stage", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--max-runs", type=int, help="Cumulative attempted-cell limit, at most 40")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_pilot(
            args.protocol, args.output, stage=args.stage, max_runs=args.max_runs, resume=args.resume
        )
    except (OSError, ValueError) as exc:
        print(f"Pilot stopped: {exc}", file=sys.stderr)
        return 1
    print(args.output.resolve())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
