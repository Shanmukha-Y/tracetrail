#!/usr/bin/env python3
"""Freeze the agreed local pilot, without querying or invoking any model.

Run only after the repository owners declare source/tests ready:
  .venv/bin/python /tmp/tracetrail_pilot_freeze.py --root .

Required inventory is the sanitized, public snapshot. Its private precursor is
neither opened nor required. Existing output files are never overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
import tomllib
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

PILOT_ID = "tracetrail-model-pilot-v1"
INVENTORY_SHA256 = "7ec3f9f1f209e2742a1ce83fd09bdcbce4ef2fb093e46a88656511439b89c6f3"
MANIFEST_SHA256 = "56c128e29c8e3588f9cd4fbac83759538db9e20143df91a54e2fb425456fc75a"
V8_PROTOCOL_SHA256 = "e025493b6f2309d86c9339b4217a7bf1aedbbd51aa209d837d1e75e8f4cefcca"
CASE_IDS = ("dev-role-duration-direction", "dev-kms-returned-key")
# Predeclared execution order; this is not a parameter-size or intelligence rank.
MODEL_DIGESTS = {
    "gemma4:e2b-it-q4_K_M": "b37049369adfe3d2b653af0ab301a062ca5cbe96ace6aa0d3f2559ee9b563fc2",
    "gemma4:12b-it-q4_K_M": "6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b",
    "qwen3.8:27b-q4_K_M": "25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e",
    "mistral-small3.2:24b": "57bbe3480604be532b76a11087b4028a73e251a22c34380527281039a3967a06",
    "gemma4:31b-it-q4_K_M": "17ba34c06c801ba22f6047bab21ced9429c6d43e0e42ecf339b0f3e5a61e8d97",
}
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def read_json(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path.name}: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"Non-finite JSON value in {path.name}: {value}")

    result = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique,
        parse_constant=nonfinite,
    )
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return result


def relative(root: Path, path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("Frozen input paths must stay inside the repository")
    return resolved.relative_to(root).as_posix()


def input_path(root: Path, value: Path) -> Path:
    path = (root / value).resolve() if not value.is_absolute() else value.resolve()
    relative(root, path)
    if not path.is_file():
        raise ValueError(f"Required freeze input is missing: {path.name}")
    return path


def artifact(root: Path, path: Path) -> dict[str, str]:
    return {"path": relative(root, path), "sha256": sha(path)}


def source_hashes(root: Path) -> dict[str, str]:
    folder = root / "src" / "tracetrail"
    paths = sorted(folder.rglob("*.py"))
    if not paths:
        raise ValueError("No TraceTrail runtime Python sources found")
    if any(not path.resolve().is_relative_to(folder.resolve()) for path in paths):
        raise ValueError("Runtime source cannot resolve outside src/tracetrail")
    return {relative(root, path): sha(path) for path in paths}


@contextmanager
def no_network():
    """Even accidental import-time HTTP/DNS must fail before opening a connection."""

    def denied(*args, **kwargs):
        raise RuntimeError("The freeze generator cannot access the network or Ollama")

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


def installed_versions() -> dict[str, str]:
    versions = {}
    for distribution in importlib.metadata.distributions():
        name = re.sub(r"[-_.]+", "-", distribution.metadata["Name"]).lower()
        version = distribution.version
        if name in versions and versions[name] != version:
            raise ValueError(f"Conflicting installed versions: {name}")
        versions[name] = version
    return dict(sorted(versions.items()))


def model_contracts(inventory: dict) -> list[dict]:
    safety = inventory.get("safety", {})
    if (
        safety.get("loopback_only") is not True
        or safety.get("one_model_at_a_time") is not True
        or safety.get("remote_routing") is not False
        or safety.get("hosted_uploads") is not False
    ):
        raise ValueError("The public inventory does not establish local-only operation")
    entries = inventory.get("models")
    if not isinstance(entries, list) or any(not isinstance(m, dict) for m in entries):
        raise ValueError("Invalid public model inventory")
    by_name = {m.get("name"): m for m in entries}
    if len(by_name) != len(entries) or set(by_name) != set(MODEL_DIGESTS):
        raise ValueError("The inventory must contain the exact five agreed model tags")
    result = []
    for name, digest in MODEL_DIGESTS.items():
        entry = by_name[name]
        listed = entry.get("listed_digests")
        if (
            entry.get("expected_runtime_digest") != digest
            or not isinstance(listed, list)
            or not listed
            or any(not isinstance(v, str) or not _DIGEST.fullmatch(v) for v in listed)
            or len(set(listed)) != len(listed)
            or digest not in listed
        ):
            raise ValueError(f"Unexpected local digest metadata for {name}")
        records = entry.get("listed_records")
        if (
            not isinstance(records, list)
            or any(not isinstance(r, dict) for r in records)
            or [r.get("digest") for r in records] != listed
            or any(r.get("name") != name for r in records)
            or any(r.get("remote_host") or r.get("remote_model") for r in records)
            or entry.get("details", {}).get("format") != "gguf"
        ):
            raise ValueError(f"Local listed records do not match the inventory for {name}")
        for key in ("license_sha256", "template_sha256", "modelfile_sha256"):
            value = entry.get(key)
            if not isinstance(value, str) or not _DIGEST.fullmatch(value):
                raise ValueError(f"Missing model metadata fingerprint: {name}/{key}")
        # Preserve the exact list, including both Mistral aliases. Never choose
        # an effective runtime digest by taking the first listed tag record.
        result.append(
            {
                "name": name,
                "digest": digest,
                "listed_digests": list(listed),
                "ollama_version": inventory["ollama_version"],
            }
        )
    return result


def write_exclusive(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("Refusing to replace an existing frozen protocol")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".tracetrail-freeze-", suffix=".json", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Atomic and refuses an existing destination.
    finally:
        temporary.unlink(missing_ok=True)


def build(args: argparse.Namespace) -> tuple[Path, dict]:
    root = args.root.resolve()
    inventory_path = input_path(root, args.inventory)
    rubric_path = input_path(root, args.semantic_review)
    manifest_path = input_path(root, args.manifest)
    baseline_path = input_path(root, Path("evaluation/protocol-v8.json"))
    if inventory_path.parent != root / "evaluation":
        raise ValueError("Required model inventory must be the public evaluation snapshot")
    if manifest_path.parent != root / "evaluation" or rubric_path.parent != root / "evaluation":
        raise ValueError("The frozen manifest and rubric must be under evaluation")
    if sha(inventory_path) != INVENTORY_SHA256:
        raise ValueError("The public inventory changed from the approved snapshot")
    if sha(manifest_path) != MANIFEST_SHA256 or sha(baseline_path) != V8_PROTOCOL_SHA256:
        raise ValueError("Historical case manifest or v8 protocol has changed")
    inventory = read_json(inventory_path)
    baseline = read_json(baseline_path)
    models = model_contracts(inventory)
    before = source_hashes(root)
    dependency_paths = [input_path(root, Path(p)) for p in ("pyproject.toml", "uv.lock")]
    dependencies = {relative(root, p): sha(p) for p in dependency_paths}
    inputs = {
        relative(root, p): sha(p)
        for p in (inventory_path, rubric_path, manifest_path, baseline_path)
    }
    sys.path.insert(0, str(root / "src"))
    sys.dont_write_bytecode = True
    with no_network():
        from tracetrail import agent
        from tracetrail.evaluation import load_cases
        from tracetrail.pilot import PILOT_ID as runtime_pilot_id
        from tracetrail.pilot import plan_cells
        from tracetrail.planning import ClaimPlan, Decision, PivotDisposition
        from tracetrail.store import Query
        from tracetrail.support_evaluation import (
            NUMERIC_METRIC_KEYS,
            SCORER_ID,
            scorer_fingerprint,
        )

        if runtime_pilot_id != PILOT_ID or not set(MODEL_DIGESTS) <= set(agent.MODELS):
            raise ValueError("The pilot runner or model allowlist is not ready")
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
        schema_hashes = {k: canonical_sha(c.model_json_schema()) for k, c in schemas.items()}
        prompt = hashlib.sha256((agent.SYSTEM + agent.PLAN + agent.FINAL).encode()).hexdigest()
        fingerprint = scorer_fingerprint()
        if (
            agent.PROTOCOL != baseline["protocol"]
            or prompt != agent.PROMPT_SHA256
            or prompt != baseline["prompt_sha256"]
            or schema_hashes != baseline["schema_sha256"]
            or SCORER_ID != "claim-support-v1"
            or fingerprint["source_sha256"] != baseline["evaluation"]["source_sha256"]
            or list(NUMERIC_METRIC_KEYS) != baseline["evaluation"]["numeric_metric_keys"]
            or before["src/tracetrail/evaluation.py"]
            != baseline["source_sha256"]["src/tracetrail/evaluation.py"]
        ):
            raise ValueError("Prompt, settings, schemas or scoring contracts differ from v8")
        cases = {case["id"]: case for case in load_cases(manifest_path)}
        if any(
            case_id not in cases or cases[case_id]["split"] != "development" for case_id in CASE_IDS
        ):
            raise ValueError("The pilot requires the two agreed exposed development cases")
        fixtures = {
            case_id: {
                "path": cases[case_id]["fixture"],
                "sha256": cases[case_id]["fixture_sha256"],
                "split": "development",
            }
            for case_id in CASE_IDS
        }
        versions = installed_versions()
        lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
        lock_versions = {}
        for package in lock["package"]:
            lock_versions.setdefault(package["name"], set()).add(package["version"])
        document = {
            "schema_version": "1",
            "protocol_id": PILOT_ID,
            "phase": "exposed-development-model-pilot",
            "frozen_at": datetime.now(UTC).isoformat(),
            "base_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=root, text=True
            ).strip(),
            "protocol": agent.PROTOCOL,
            "prompt_sha256": prompt,
            "schema_sha256": schema_hashes,
            "source_sha256": {
                **before,
                **dependencies,
                relative(root, rubric_path): sha(rubric_path),
            },
            "dependency_sha256": dependencies,
            "versions": versions,
            "locked_package_versions": {k: sorted(v) for k, v in sorted(lock_versions.items())},
            "python_version": platform.python_version(),
            "host": inventory.get("host", {}),
            "ollama_version": inventory.get("ollama_version"),
            "model_inventory": artifact(root, inventory_path),
            "semantic_rubric": artifact(root, rubric_path),
            "baseline_contract": artifact(root, baseline_path),
            "case_manifest": artifact(root, manifest_path),
            "case_fixtures": fixtures,
            "evaluation": {
                "primary_scorer": SCORER_ID,
                **fingerprint,
                "numeric_metric_keys": list(NUMERIC_METRIC_KEYS),
                "legacy_scorer_unchanged": True,
                "semantic_correctness_verified_by_scorer": False,
            },
            "pilot": {"case_ids": list(CASE_IDS), "models": models, "repeats": 2},
            "runtime_gate": {
                "overall_wall_seconds": 5400,
                "overhead_factor": 1.2,
                "soft_launch_ceiling_seconds": 5400,
                "overall_wall_ceiling_is_soft": True,
                "in_flight_run_may_complete_after_ceiling": True,
                "first_stage_cells": 10,
                "minimum_planned_runs": 20,
                "expanded_planned_runs": 40,
                "formula": "1.2 * 4 * sum(first ten cell wall_seconds) <= 5400",
                "outcome_based_expansion": False,
                "hardware_or_incomplete_resource_measurement_blocks_repeat_two": True,
            },
            "stages": [
                {"stage": 1, "case_ids": [CASE_IDS[0]], "repeat": 1, "cells": 10},
                {"stage": 2, "case_ids": [CASE_IDS[1]], "repeat": 1, "cells": 10},
                {
                    "stage": 3,
                    "case_ids": list(CASE_IDS),
                    "repeat": 2,
                    "cells": 20,
                    "conditional": "runtime gate passes and no recorded hardware interference",
                },
            ],
            "safety": {
                "local_inference_only": True,
                "sequential_model_loading": True,
                "synthetic_records_only": True,
                "hosted_uploads": False,
                "credentials_created_or_configured": False,
                "freeze_generator_network_disabled": True,
                "model_calls_by_freeze_generator": 0,
            },
            "limitations": [
                "Both cases and all earlier outputs are exposed development data.",
                "Model tags, parameter counts, quantization and runner metadata "
                "are not intelligence rankings.",
                "Same greedy seed repeats measure observed execution stability, "
                "not independent task trials.",
                "Failed and invalid assignments remain in every declared capability denominator.",
                "Raw report support, process-valid support, status accuracy and "
                "semantic warrant are separate.",
                "Assistant reviews are not independent human review or a validated semantic judge.",
                "Two case clusters do not support reliable generalization "
                "intervals or model rankings.",
                "Adaptive and fixed use identical application templates and bounds; "
                "their actual calls and evidence differ by design.",
                "The 5400-second accumulated wall limit prevents new launches; "
                "an already-running bounded investigation may finish after it.",
            ],
            "freeze_generator_sha256": sha(Path(__file__)),
        }
        cells = plan_cells(document)
        if len(cells) != 40 or stage_counts(cells) != {1: 10, 2: 10, 3: 20}:
            raise ValueError("The runtime cell schedule does not match the agreed three stages")
        document["cell_plan"] = cells
        document["cell_plan_sha256"] = canonical_sha(cells)
    if source_hashes(root) != before:
        raise ValueError("Source changed while computing the freeze")
    for path, digest in {**inputs, **dependencies}.items():
        if sha(root / path) != digest:
            raise ValueError(f"Freeze input changed: {path}")
    for entry in fixtures.values():
        if sha(root / entry["path"]) != entry["sha256"]:
            raise ValueError("A selected fixture changed during freeze")
    output = (
        (root / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    )
    if output.parent != root / "evaluation":
        raise ValueError("Frozen protocol output must be directly under evaluation")
    return output, document


def stage_counts(cells: list[dict]) -> dict[int, int]:
    counts = {}
    for cell in cells:
        counts[cell["stage"]] = counts.get(cell["stage"], 0) + 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--inventory", type=Path, default=Path("evaluation/model-inventory-pilot-v1.json")
    )
    parser.add_argument(
        "--semantic-review", type=Path, default=Path("evaluation/pilot-semantic-review-v1.md")
    )
    parser.add_argument("--manifest", type=Path, default=Path("evaluation/cases-v7.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/protocol-pilot-v1.json"))
    args = parser.parse_args()
    try:
        output, document = build(args)
        write_exclusive(output, document)
        print(
            json.dumps(
                {
                    "path": relative(args.root.resolve(), output),
                    "sha256": sha(output),
                    "source_count": len(document["source_sha256"]),
                    "models": 5,
                    "maximum_cells": 40,
                    "model_calls_by_generator": 0,
                },
                sort_keys=True,
            )
        )
        return 0
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        print(f"Pilot freeze error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
