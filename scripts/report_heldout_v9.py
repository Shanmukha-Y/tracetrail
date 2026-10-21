#!/usr/bin/env python3
"""Add explicit resource observations to unchanged frozen v9 artifact reports.

This is a reporting extension added after the protocol freeze. It does not
invoke inference, run SDK evaluation, change scores, filter assignments, or
certify hardware isolation. The original runner and protocol remain unchanged.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parent.parent
REPORTER_ID = "heldout-v9-resource-report-v1"
MAXIMA = (
    "ollama_reported_size_bytes",
    "ollama_reported_size_vram_bytes",
    "listener_process_tree_rss_sum_bytes",
)
sys.dont_write_bytecode = True


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_frozen():
    path = SCRIPT.with_name("heldout_v9.py")
    spec = importlib.util.spec_from_file_location("heldout_v9_frozen_reporting", path)
    require(spec is not None and spec.loader is not None, "Frozen runner is unavailable")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


FROZEN = load_frozen()


def integer(value, name):
    require(type(value) is int and value >= 0, "Invalid resource count: " + name)
    return value


def number_or_none(value, name, *, positive=False):
    if value is None:
        return None
    require(
        type(value) in (int, float)
        and math.isfinite(value)
        and (value > 0 if positive else value >= 0),
        "Invalid resource timing: " + name,
    )
    return value


def boolean_or_none(value, name):
    require(value is None or type(value) is bool, "Invalid resource flag: " + name)
    return value


def resource_status(run, helper, expected_digest):
    """Verify existing aggregate consistency and disclose recorded sampling limits.

    Eligibility is a descriptive check of recorded sampling, not a new latency
    cutoff or an inference score. No failed or ineligible row is removed.
    """
    verified = helper.verify_resources(run, expected_digest)
    report = run.get("model_info", {}).get("resources", {})
    require(isinstance(report, dict), "Invalid resource report")
    status = verified["status"]
    require(
        status in (None, "not-recorded", "unavailable", "partial", "completed"),
        "Unknown verified resource status",
    )
    status = "not_recorded" if status in (None, "not-recorded") else status
    samples = report.get("samples")
    observed = isinstance(samples, list)
    samples = samples if observed else []
    count = len(samples)
    errors = report.get("errors", [])
    require(isinstance(errors, list), "Invalid resource error list")
    reported_errors = report.get("error_count")
    if reported_errors is not None:
        integer(reported_errors, "error_count")
    declared_foreign = boolean_or_none(report.get("foreign_model_observed"), "foreign model")
    limit_reached = boolean_or_none(report.get("sample_limit_reached"), "sample limit")
    interval = number_or_none(report.get("requested_interval_seconds"), "interval", positive=True)
    timeout = number_or_none(report.get("read_timeout_seconds"), "read timeout", positive=True)
    sample_limit = report.get("sample_limit")
    if sample_limit is not None:
        integer(sample_limit, "sample limit")
        require(sample_limit > 0, "Resource sample limit must be positive")
        if limit_reached is not None:
            require(
                limit_reached == (count >= sample_limit), "Resource sampling limit flag differs"
            )
    if observed:
        integer(report["sample_count"], "sample_count")
        for name in (
            "error_count",
            "ollama_sample_count",
            "rss_complete_sample_count",
            "rss_incomplete_sample_count",
            "matching_model_sample_count",
        ):
            integer(report[name], name)
        for sample in samples:
            require(isinstance(sample, dict), "Invalid resource sample")
            integer(sample["index"], "sample index")
            require(isinstance(sample["errors"], list), "Invalid sample error list")
            if "ollama" in sample:
                for name in ("matching_model_count", "foreign_model_count"):
                    integer(sample["ollama"].get(name, 0), name)
            if "process_rss" in sample and "tree_complete" in sample["process_rss"]:
                boolean_or_none(sample["process_rss"]["tree_complete"], "RSS completeness")
        ollama_count = sum("ollama" in sample for sample in samples)
        rss_count = sum(
            sample.get("process_rss", {}).get("tree_complete") is True for sample in samples
        )
        target_count = sum(
            sample.get("ollama", {}).get("matching_model_count", 0) > 0 for sample in samples
        )
        foreign = bool(verified["foreign_model_observed"]) if ollama_count else None
        error_count = report["error_count"]
        maxima = verified["sampled_maxima"]
    else:
        ollama_count = rss_count = target_count = None
        foreign = None
        for name in (
            "sample_count",
            "ollama_sample_count",
            "rss_complete_sample_count",
            "rss_incomplete_sample_count",
            "matching_model_sample_count",
        ):
            if name in report:
                require(integer(report[name], name) == 0, "Counts exist without resource samples")
        declared_errors = report.get("error_count")
        if declared_errors is not None:
            integer(declared_errors, "error_count")
        error_count = len(errors) if "errors" in report else None
        if error_count is not None and declared_errors is not None:
            require(declared_errors == error_count, "Resource error count differs")
        maxima = {name: None for name in MAXIMA}
    for name in MAXIMA:
        if maxima[name] is not None:
            integer(maxima[name], name)
    elapsed = [number_or_none(s.get("elapsed_seconds"), "elapsed sample") for s in samples]
    timing_complete = bool(samples) and all(value is not None for value in elapsed)
    gaps = None
    if timing_complete:
        require(
            all(a <= b for a, b in zip(elapsed, elapsed[1:], strict=False)),
            "Sample times go backwards",
        )
        gaps = max((b - a for a, b in zip(elapsed, elapsed[1:], strict=False)), default=None)
    reasons = []
    if status != "completed":
        reasons.append("sampling_not_completed")
    if not count:
        reasons.append("no_recorded_samples")
    if observed and ollama_count != count:
        reasons.append("ollama_reads_missing")
    if observed and rss_count != count:
        reasons.append("rss_reads_incomplete")
    if not target_count:
        reasons.append("target_model_not_observed")
    if error_count is None:
        reasons.append("measurement_error_count_unknown")
    elif error_count:
        reasons.append("measurement_errors_recorded")
    if foreign is True or declared_foreign is True:
        reasons.append("foreign_model_observed")
    if foreign is None:
        reasons.append("foreign_model_observation_unknown")
    if sample_limit is None:
        reasons.append("sample_limit_unknown")
    if limit_reached is True:
        reasons.append("sample_limit_reached")
    elif limit_reached is None:
        reasons.append("sample_limit_status_unknown")
    if interval is None or timeout is None or not timing_complete:
        reasons.append("sampling_timing_incomplete")
    if any(maxima[name] is None for name in MAXIMA):
        reasons.append("sampled_maxima_missing")
    if run.get("inference_calls_unknown"):
        reasons.append("inference_history_unknown")
    if run.get("heldout", {}).get("wall_seconds_unknown"):
        reasons.append("cell_wall_time_unknown")
    return {
        "artifact_consistency": "verified",
        "sampling_status": status,
        "sample_count": count,
        "error_count": error_count,
        "reported_error_count": reported_errors,
        "ollama_sample_count": ollama_count,
        "ollama_sample_gaps": count - ollama_count if observed else None,
        "rss_complete_sample_count": rss_count,
        "rss_sample_gaps": count - rss_count if observed else None,
        "matching_model_sample_count": target_count,
        "no_target_model_samples": count - target_count if observed else None,
        "foreign_model_observed": foreign,
        "reported_foreign_model_observed": declared_foreign,
        "foreign_model_observation_complete": bool(count) and ollama_count == count,
        "sample_limit_reached": limit_reached,
        "sample_limit": sample_limit,
        "requested_interval_seconds": interval,
        "read_timeout_seconds": timeout,
        "timing_complete": timing_complete,
        "observed_max_sample_gap_seconds": gaps,
        "sampled_maxima": {name: maxima[name] for name in MAXIMA},
        "measurement_eligible": not reasons,
        "eligibility_scope": "recorded_sampling_checks_only",
        "eligibility_reasons": reasons,
        "hardware_isolation_verified": False,
        "true_peak_memory_verified": False,
    }


def annotate(document, resource_rows, provenance):
    """Return an enriched report without changing any original numeric field."""
    result = deepcopy(document)
    require(len(result["rows"]) == len(resource_rows), "Resource rows do not match artifact rows")
    for row, resources in zip(result["rows"], resource_rows, strict=True):
        require("resources" not in row, "Resource status already exists")
        row["resources"] = deepcopy(resources)
    eligible = sum(row["measurement_eligible"] for row in resource_rows)
    result["artifact_verification_status"] = "verified"
    result["reporting_extension"] = deepcopy(provenance)
    result["measurement_review"] = {
        "status": "not_evaluated"
        if not resource_rows
        else "recorded_checks_passed"
        if eligible == len(resource_rows)
        else "issues_recorded",
        "measurement_eligible": bool(resource_rows) and eligible == len(resource_rows),
        "eligibility_scope": "recorded_sampling_checks_only",
        "evaluated_rows": len(resource_rows),
        "eligible_rows": eligible,
        "ineligible_rows": len(resource_rows) - eligible,
        "foreign_model_observed_rows": sum(
            r["foreign_model_observed"] is True for r in resource_rows
        ),
        "foreign_model_unknown_rows": sum(
            r["foreign_model_observed"] is None for r in resource_rows
        ),
        "reported_foreign_model_rows": sum(
            r["reported_foreign_model_observed"] is True for r in resource_rows
        ),
        "artifact_verification_is_measurement_validity": False,
        "hardware_isolation_verified": False,
        "true_peak_memory_verified": False,
        "rows_excluded": 0,
    }
    return result


def provenance(args, frozen):
    runner_path = FROZEN.SCRIPT.relative_to(FROZEN.ROOT).as_posix()
    return {
        "reporter_id": REPORTER_ID,
        "reporter_source_sha256": FROZEN.sha(SCRIPT),
        "protocol_sha256": FROZEN.sha(args.protocol),
        "frozen_runner_sha256": frozen["source_sha256"][runner_path],
        "extension_added_after_protocol_freeze": True,
        "changes_inference_or_scoring": False,
        "no_assignments_or_latency_rows_filtered": True,
        "resource_eligibility_is_descriptive_not_a_new_score": True,
        "new_model_calls": 0,
        "sdk_evaluations_performed": 0,
        "uploads_enabled": False,
    }


def reviewed(args):
    frozen, raw, audit = FROZEN.verify_data(args)
    helper = FROZEN.module(
        "heldout_resource_report_helpers", FROZEN.SCRIPT.with_name("verify_model_pilot_v1.py")
    )
    resources = [resource_status(run, helper, frozen["model"]["digest"]) for run in raw["runs"]]
    inputs_unchanged(args, audit)
    FROZEN.verify_protocol(args.protocol)
    return frozen, raw, audit, resources


def inputs_unchanged(args, audit):
    require(FROZEN.sha(args.raw) == audit["raw_sha256"], "Raw input changed during resource review")
    require(FROZEN.sha(args.protocol) == audit["protocol_sha256"], "Protocol input changed")
    if args.sdk is not None:
        require(FROZEN.sha(args.sdk) == audit["sdk_sha256"], "SDK input changed")


def verify(args):
    with FROZEN.no_network():
        frozen, raw, audit, resources = reviewed(args)
        report = annotate(audit, resources, provenance(args, frozen))
        report["attempted_runs"] = len(raw["runs"])
        report["planned_runs"] = len(frozen["cell_plan"])
        inputs_unchanged(args, audit)
        FROZEN.private_write(args.output, report, create=True)
        return {
            "path": str(args.output),
            "sha256": FROZEN.sha(args.output),
            "artifact_verification_status": report["artifact_verification_status"],
            "measurement_review": report["measurement_review"],
            "attempted_runs": len(raw["runs"]),
            "planned_runs": len(frozen["cell_plan"]),
        }


def summary(args):
    require(args.sdk is not None, "Final summary requires the real matching offline SDK artifact")
    require(not args.output.is_symlink(), "Public output cannot be a symbolic link")
    output = args.output.resolve()
    require(output.parent == ROOT / "evaluation", "Public output must be under evaluation")
    temporary = ROOT / "evaluation" / f".heldout-resource-base-{uuid4().hex}.json"
    with FROZEN.no_network():
        try:
            frozen, raw, audit, resources = reviewed(args)
            FROZEN.summary(
                argparse.Namespace(
                    protocol=args.protocol, raw=args.raw, sdk=args.sdk, output=temporary
                )
            )
            base = FROZEN.read(temporary)
            require(
                base["raw_sha256"] == audit["raw_sha256"], "Base summary uses another raw input"
            )
            require(
                base["sdk_sha256"] == audit["sdk_sha256"], "Base summary uses another SDK input"
            )
            require(len(base["rows"]) == len(raw["runs"]), "Base summary row count differs")
            for row, run in zip(base["rows"], raw["runs"], strict=True):
                require(
                    row["cell_id"] == run["heldout"]["cell"]["cell_id"]
                    and row["raw_result_sha256"] == run["heldout"]["result_sha256"],
                    "Base summary assignment differs",
                )
            report = annotate(base, resources, provenance(args, frozen))
            helper = FROZEN.module(
                "heldout_resource_report_write", FROZEN.SCRIPT.with_name("freeze_model_pilot_v1.py")
            )
            inputs_unchanged(args, audit)
            helper.write_exclusive(output, report)
        finally:
            temporary.unlink(missing_ok=True)
    return {
        "path": output.relative_to(ROOT).as_posix(),
        "sha256": FROZEN.sha(output),
        "artifact_verification_status": report["artifact_verification_status"],
        "measurement_review": report["measurement_review"],
        "attempted_runs": report["attempted_runs"],
        "planned_runs": report["planned_runs"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("verify", "summary"):
        command = sub.add_parser(name)
        command.add_argument("--protocol", type=Path, required=True)
        command.add_argument("--raw", type=Path, required=True)
        command.add_argument("--sdk", type=Path)
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = {"verify": verify, "summary": summary}[args.command](args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, AssertionError) as exc:
        print(f"Resource report stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
