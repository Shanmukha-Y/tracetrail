"""Local command line interface and sequential comparison runner."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import tempfile
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import ollama

from tracetrail.agent import MODELS, OLLAMA_URL, PROTOCOL, investigate
from tracetrail.evaluation import load_cases, score_run
from tracetrail.local_model import verify_local_weights
from tracetrail.store import CloudTrailStore, Query


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".tracetrail-", suffix=".json", dir=path.parent)
    temp = Path(temporary)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def fresh_result_path(requested: Path) -> Path:
    if not requested.exists():
        return requested
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return requested.with_name(f"{requested.stem}-{stamp}-{uuid4().hex[:8]}{requested.suffix}")


@contextmanager
def model_session(name: str):
    """Serialize model use across TraceTrail processes; release this model after use."""
    if name not in MODELS:
        raise ValueError("Use one of the three approved local model tags")
    lock_path = Path("/tmp/tracetrail-ollama.lock")
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        client = ollama.Client(
            host=OLLAMA_URL,
            timeout=150,
            trust_env=False,
            follow_redirects=False,
            headers={"Authorization": "local-only-no-auth"},
        )
        info = verify_local_weights(name)
        # Do not pull models, change server settings, or evict another app's model.
        loaded = client.ps().models
        if any(item.model != name for item in loaded):
            raise RuntimeError(
                "Another model is loaded. Unload it before the sequential comparison"
            )
        try:
            yield info
        finally:
            try:
                info["loaded_models"] = [
                    item.model_dump(mode="json")
                    for item in client.ps().models
                    if item.model == name
                ]
            except Exception as exc:
                info["runtime_metadata_error"] = {"error_type": type(exc).__name__}
            try:
                client.generate(model=name, prompt="", keep_alive=0)
            except Exception as exc:
                info["cleanup_error"] = {"error_type": type(exc).__name__}


def run_case(case: dict, root: Path, model: str, strategy: str) -> dict:
    fixture = root / case["fixture"]
    with model_session(model) as info:
        store = CloudTrailStore.load(fixture)
        result = investigate(
            store,
            case["seed_event_id"],
            case["question"],
            case["hypotheses"],
            model_name=model,
            strategy=strategy,
        )
    result.update(
        {
            "case_id": case["id"],
            "split": case["split"],
            "fixture_sha256": case["fixture_sha256"],
            "model_info": info,
        }
    )
    if info.get("cleanup_error"):
        result["failures"].append({"phase": "unload", **info["cleanup_error"]})
        result["status"] = "degraded"
    result["metrics"] = score_run(case, result)
    return result


def compare(args: argparse.Namespace) -> int:
    args.output = fresh_result_path(args.output)
    manifest = args.manifest.resolve()
    root = manifest.parent.parent
    cases = load_cases(manifest)
    if args.split != "all":
        cases = [case for case in cases if case["split"] == args.split]
    if args.case:
        cases = [case for case in cases if case["id"] in args.case]
    if not cases:
        raise ValueError("No cases selected")
    models = args.models or list(MODELS)
    data = {
        "suite_id": json.loads(manifest.read_text())["suite_id"],
        "case_manifest_path": manifest.relative_to(root).as_posix(),
        "created_at": datetime.now(UTC).isoformat(),
        "case_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "protocol": PROTOCOL,
        "selected_cases": [case["id"] for case in cases],
        "host": {"system": platform.system(), "machine": platform.machine()},
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("langchain", "langchain-ollama", "langgraph", "langsmith")
        },
        "runs": [],
    }
    # Write after every run, so failures and interrupted comparisons remain visible.
    write_json(args.output, data)
    for model in models:
        for case in cases:
            strategies = (
                ["adaptive", "fixed"] if args.fixed_all or model == MODELS[0] else ["adaptive"]
            )
            for strategy in strategies:
                print(f"Running {case['id']} | {model} | {strategy}", file=sys.stderr, flush=True)
                try:
                    result = run_case(case, root, model, strategy)
                except Exception as exc:
                    result = {
                        "case_id": case["id"],
                        "split": case["split"],
                        "model": model,
                        "strategy": strategy,
                        "status": "failed",
                        "fixture_sha256": case["fixture_sha256"],
                        "failures": [{"phase": "runner", "error_type": type(exc).__name__}],
                        "error": str(exc),
                        "test_only": False,
                    }
                if "metrics" not in result:
                    result["metrics"] = score_run(case, result)
                data["runs"].append(result)
                write_json(args.output, data)
                print(f"Saved status={result['status']}", file=sys.stderr, flush=True)
    print(args.output.resolve())
    return int(any(run["status"] != "completed" for run in data["runs"]))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Read-only local CloudTrail investigation")
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("query", "resolve"):
        command = commands.add_parser(name)
        command.add_argument("path", type=Path)
        if name == "resolve":
            command.add_argument("identifier")
        else:
            command.add_argument("--filter", default="{}", help="Exact Query JSON object")
    demo = commands.add_parser("demo")
    demo.add_argument("--manifest", type=Path, default=Path("evaluation/cases-v2.json"))
    demo.add_argument("--case", required=True)
    demo.add_argument("--model", default=MODELS[0])
    demo.add_argument("--strategy", choices=("adaptive", "fixed"), default="adaptive")
    demo.add_argument("--output", type=Path, default=Path("local-results/demo.json"))
    run = commands.add_parser("investigate")
    run.add_argument("path", type=Path)
    run.add_argument("--seed", required=True)
    run.add_argument("--question", required=True)
    run.add_argument(
        "--hypotheses",
        required=True,
        type=Path,
        help="JSON list of {claim_id,statement}; no answer labels",
    )
    run.add_argument("--model", default=MODELS[0])
    run.add_argument("--output", type=Path, default=Path("local-results/investigation.json"))
    batch = commands.add_parser("compare")
    batch.add_argument("--manifest", type=Path, default=Path("evaluation/cases-v2.json"))
    batch.add_argument("--models", nargs="+")
    batch.add_argument("--split", choices=("all", "development", "heldout"), default="all")
    batch.add_argument("--case", action="append")
    batch.add_argument("--fixed-all", action="store_true")
    batch.add_argument("--output", type=Path, default=Path("local-results/comparison.json"))
    offline = commands.add_parser("local-evaluate")
    offline.add_argument("results", type=Path)
    offline.add_argument("--root", type=Path, default=Path("."))
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command in ("demo", "investigate"):
            args.output = fresh_result_path(args.output)
        if args.command in ("query", "resolve"):
            store = CloudTrailStore.load(args.path)
            output = (
                store.get(args.identifier)
                if args.command == "resolve"
                else store.query(Query.model_validate_json(args.filter))
            )
            print(json.dumps(output, indent=2))
            return 0
        if args.command == "compare":
            return compare(args)
        if args.command == "demo":
            manifest = args.manifest.resolve()
            cases = load_cases(manifest)
            case = next(case for case in cases if case["id"] == args.case)
            result = run_case(case, manifest.parent.parent, args.model, args.strategy)
        elif args.command == "local-evaluate":
            from tracetrail.telemetry import evaluate_local

            output = evaluate_local(args.results, args.root)
            print(json.dumps(output, indent=2, default=str))
            return int(output["status"] != "completed")
        else:
            with model_session(args.model) as info:
                result = investigate(
                    CloudTrailStore.load(args.path),
                    args.seed,
                    args.question,
                    json.loads(args.hypotheses.read_text()),
                    model_name=args.model,
                )
            result["model_info"] = info
            if info.get("cleanup_error"):
                result["failures"].append({"phase": "unload", **info["cleanup_error"]})
                result["status"] = "degraded"
        write_json(args.output, result)
        print(args.output.resolve())
        return int(result["status"] != "completed")
    except (ValueError, OSError, RuntimeError, StopIteration) as exc:
        print(f"TraceTrail error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
