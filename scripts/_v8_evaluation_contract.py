"""Independent stored-artifact verifier. No inference, SDK replay, or semantic judge.

Claim counters below are independently derived, without importing or invoking
score_claim_support. Frozen legacy/link/planning/context helpers are reused for
their existing mechanical contracts and are identified in the output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import socket
import tempfile
from collections import Counter
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path


def no_network(*args, **kwargs):
    raise AssertionError("This verifier cannot use the network")


socket.socket.connect = no_network
socket.socket.connect_ex = no_network
socket.create_connection = no_network

from pydantic import ValidationError  # noqa: E402

from tracetrail import agent  # noqa: E402
from tracetrail.claims import validate_finding_links  # noqa: E402
from tracetrail.coverage import evidence_coverage  # noqa: E402
from tracetrail.credential_map import credential_map  # noqa: E402
from tracetrail.evaluation import load_cases, score_run  # noqa: E402
from tracetrail.facts import chronological_context, project_observations  # noqa: E402
from tracetrail.planning import (  # noqa: E402
    ClaimPlan,
    Decision,
    PivotDisposition,
    materialize_query,
    validate_decision,
)
from tracetrail.store import Query  # noqa: E402

agent.make_model = no_network

PROTOCOL_SHA = "e025493b6f2309d86c9339b4217a7bf1aedbbd51aa209d837d1e75e8f4cefcca"
PROMPT_SHA = "5d801a719e65e23a28deb1ee8088416c20fe9bb5d0c7d599098a11993ec0828a"
LEGACY_SHA = "e755383bc49e87edfceede571cf886382aec7ec3a2465637711dd8e9ba4bcce1"
SCORER_ID = "claim-support-v1"
NUMERIC_KEYS = (
    "annotated_claim_count",
    "finding_count",
    "raw_supported_claim_count",
    "raw_supported_claim_rate",
    "process_valid_supported_claim_count",
    "process_valid_supported_claim_rate",
    "required_atom_count",
    "raw_covered_atom_count",
    "raw_required_atom_coverage",
    "process_valid_covered_atom_count",
    "process_valid_required_atom_coverage",
    "correct_status_count",
    "correct_status_rate",
    "process_valid",
    "invalid_evidence_count",
    "invalid_link_count",
    "extra_declared_atom_count",
    "extra_citation_count",
    "unexpected_finding_count",
    "duplicate_claim_count",
    "missing_claim_count",
)
STRUCTURAL_PHASES = {"plan", "planning_validation", "validation", "report", "runner"}
MISSING = object()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def same(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b, strict=True))
    return a == b


def field(record, path):
    for part in path.split("."):
        if not isinstance(record, dict) or part not in record:
            return MISSING
        record = record[part]
    return record


def text(value):
    return " ".join(value.split()) if isinstance(value, str) else ""


def failed_tool(entry):
    result = entry.get("result") or {}
    return bool(
        entry.get("error")
        or entry.get("status") == "error"
        or result.get("error")
        or result.get("ok") is False
        or result.get("status") == "error"
    )


def derived_citations(finding):
    refs = []
    for link in finding.get("evidence_links", []):
        ref = link.get("citation") if isinstance(link, dict) else None
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    return refs


def independent_support(case, run):
    """Re-derive all 21 scalar counters from sources and finding-local links."""
    sources = {
        f"sha256:{case['fixture_sha256']}/Records/{i}": record
        for i, record in enumerate(case["_fixture_records"])
    }
    event_refs = {r["eventID"]: ref for ref, r in sources.items()}
    returned = {event_refs[case["seed_event_id"]]}
    for entry in run.get("tool_history", []):
        if entry.get("name") not in ("query_events", "get_event") or failed_tool(entry):
            continue
        result = entry["result"]
        for item in result.get("records", [result]):
            ref = item.get("ref")
            if (
                ref in sources
                and item.get("event_id") == sources[ref]["eventID"]
                and same(item.get("record"), sources[ref])
            ):
                returned.add(ref)
    evidence_counts = Counter(e.get("ref") for e in run.get("evidence", []))
    valid = {}
    for e in run.get("evidence", []):
        ref = e.get("ref")
        if (
            ref in returned
            and ref in sources
            and evidence_counts[ref] == 1
            and e.get("event_id") == sources[ref]["eventID"]
            and same(e.get("record"), sources[ref])
        ):
            valid[ref] = e
    invalid_evidence = len(run.get("evidence", [])) - len(valid)
    selected = run.get("selected_event_refs", [])
    selection_valid = (
        isinstance(selected, list)
        and all(isinstance(r, str) for r in selected)
        and len(set(selected)) == len(selected)
        and all(r in valid for r in selected)
    )
    valid_selected = [r for r in selected if isinstance(r, str) and r in valid]
    findings = run.get("findings", [])
    statements = {h["claim_id"]: text(h["statement"]) for h in case["hypotheses"]}
    counts = Counter(f.get("claim_id") for f in findings)
    unexpected = sum(f.get("claim_id") not in statements for f in findings)
    duplicates = sum(max(0, counts[c] - 1) for c in statements)
    missing = sum(counts[c] == 0 for c in statements)
    structural_ok = (
        selection_valid and not invalid_evidence and not (unexpected or duplicates or missing)
    )
    raw_atoms = required_atoms = raw_claims = correct_status = invalid_links = extra_atoms = (
        extra_refs
    ) = 0
    claim_rows = []
    for annotation in case["annotations"]:
        claim = annotation["claim_id"]
        found = [f for f in findings if f.get("claim_id") == claim]
        finding = found[0] if len(found) == 1 else None
        refs = derived_citations(finding or {})
        statement_ok = finding is not None and text(finding.get("statement")) == statements[claim]
        status_ok = finding is not None and finding.get("status") == annotation["expected_status"]
        correct_status += bool(statement_ok and status_ok)
        cites_ok = finding is not None and finding.get("citations") == refs
        full_errors = (
            validate_finding_links(finding, list(valid.values()), valid_selected)
            if finding is not None
            else []
        )
        if finding is not None and (not statement_ok or not cites_ok or full_errors):
            structural_ok = False
        accepted = set()
        links = (finding or {}).get("evidence_links")
        if finding is not None and (not isinstance(links, list) or len(links) > 6):
            invalid_links += 1
        else:
            signatures = set()
            for link in links or []:
                probe = {
                    "claim_id": claim,
                    "status": "uncertain",
                    "rationale": "Audit structural probe.",
                    "missing_evidence": ["No semantic judgment is made."],
                    "evidence_links": [link],
                }
                if validate_finding_links(probe, list(valid.values()), valid_selected):
                    invalid_links += 1
                    continue
                signature = (link["citation"], link["role"], tuple(sorted(link["fields"])))
                if signature in signatures:
                    invalid_links += 1
                    continue
                signatures.add(signature)
                accepted.update((link["citation"], path) for path in link["fields"])
        required = {
            (event_refs[o["event_id"]], o["field"]): o for o in annotation["required_observations"]
        }
        required_refs = {event_refs[e] for e in annotation["required_event_ids"]}
        extra_atoms += len(accepted - required.keys()) if statement_ok else 0
        extra_refs += len(set(refs) - required_refs) if finding is not None else 0
        covered = set()
        for key, expected in required.items():
            ref, path = key
            value = field(valid[ref]["record"], path) if ref in valid else MISSING
            present = expected.get("present", True)
            source_ok = (
                type(present) is bool
                and ref in valid
                and (
                    (
                        present
                        and value is not MISSING
                        and same(value, expected.get("value", MISSING))
                    )
                    or (not present and value is MISSING and expected.get("value", MISSING) is None)
                )
            )
            if (
                statement_ok
                and cites_ok
                and source_ok
                and key in accepted
                and ref in valid_selected
                and ref in refs
            ):
                covered.add(key)
        supported = bool(
            finding is not None
            and statement_ok
            and status_ok
            and cites_ok
            and not full_errors
            and required_refs <= set(refs)
            and len(covered) == len(required)
        )
        raw_atoms += len(covered)
        required_atoms += len(required)
        raw_claims += supported
        claim_rows.append(
            {
                "claim_id": claim,
                "raw_covered_atom_count": len(covered),
                "required_atom_count": len(required),
                "raw_supported": supported,
            }
        )
    recorded_failure = any(
        isinstance(f, dict) and f.get("phase") in STRUCTURAL_PHASES for f in run.get("failures", [])
    )
    process_valid = bool(
        run.get("status") == "completed" and not recorded_failure and structural_ok
    )
    count = len(case["annotations"])
    result = {
        "annotated_claim_count": count,
        "finding_count": len(findings),
        "raw_supported_claim_count": raw_claims,
        "raw_supported_claim_rate": raw_claims / count,
        "process_valid_supported_claim_count": raw_claims if process_valid else 0,
        "process_valid_supported_claim_rate": raw_claims / count if process_valid else 0.0,
        "required_atom_count": required_atoms,
        "raw_covered_atom_count": raw_atoms,
        "raw_required_atom_coverage": raw_atoms / required_atoms if required_atoms else None,
        "process_valid_covered_atom_count": raw_atoms if process_valid else 0,
        "process_valid_required_atom_coverage": (
            raw_atoms / required_atoms if process_valid else 0.0
        )
        if required_atoms
        else None,
        "correct_status_count": correct_status,
        "correct_status_rate": correct_status / count,
        "process_valid": process_valid,
        "invalid_evidence_count": invalid_evidence,
        "invalid_link_count": invalid_links,
        "extra_declared_atom_count": extra_atoms,
        "extra_citation_count": extra_refs,
        "unexpected_finding_count": unexpected,
        "duplicate_claim_count": duplicates,
        "missing_claim_count": missing,
    }
    return result, claim_rows


def walk(trace):
    yield trace
    for child in trace.get("child_runs", []):
        yield from walk(child)


def state_at(case, history):
    refs = {
        r["eventID"]: f"sha256:{case['fixture_sha256']}/Records/{i}"
        for i, r in enumerate(case["_fixture_records"])
    }
    records = {r["eventID"]: r for r in case["_fixture_records"]}
    seed = {
        "event_id": case["seed_event_id"],
        "ref": refs[case["seed_event_id"]],
        "record": records[case["seed_event_id"]],
    }
    evidence = [deepcopy(seed)]
    known = {seed["ref"]}
    for entry in history:
        if failed_tool(entry):
            continue
        result = entry["result"]
        for item in result.get("records", [result] if "ref" in result else []):
            require(
                item["event_id"] in refs
                and item["ref"] == refs[item["event_id"]]
                and same(item["record"], records[item["event_id"]]),
                "Tool returned non-source evidence",
            )
            if item["ref"] not in known:
                known.add(item["ref"])
                evidence.append(deepcopy(item))
    return seed, evidence


def compact_context(case, prefix):
    seed, evidence = state_at(case, prefix)
    aliases = {e["ref"]: f"E{i}" for i, e in enumerate(evidence)}
    compact = [{**e, "ref": aliases[e["ref"]]} for e in evidence]
    summaries = []
    for entry in prefix:
        output = entry["result"]
        summary = {k: v for k, v in output.items() if k not in ("records", "record")}
        if "records" in output:
            summary["returned_citations"] = [aliases[e["ref"]] for e in output["records"]]
        elif "ref" in output:
            summary["ref"] = aliases[output["ref"]]
        summaries.append({**entry, "result": summary})
    chronology = chronological_context(evidence, seed["ref"])
    by_ref = {e["ref"]: e for e in compact}
    coverage = evidence_coverage(compact, summaries)
    return (
        {
            "seed": {**seed, "ref": aliases[seed["ref"]]},
            "evidence": [by_ref[aliases[row["citation"]]] for row in chronology],
            "chronology": [{**row, "citation": aliases[row["citation"]]} for row in chronology],
            "tool_history": summaries,
            "coverage": coverage,
            "credential_map": credential_map(compact, coverage),
        },
        aliases,
        evidence,
    )


def resolve_decision(value, aliases):
    value = deepcopy(value)
    resolve = {alias: ref for ref, alias in aliases.items()}
    for entry in value["ledger"]:
        entry["evidence_refs"] = [resolve.get(ref, ref) for ref in entry["evidence_refs"]]
    if value["identifier"]:
        value["identifier"] = resolve.get(value["identifier"], value["identifier"])
    return value


def verify_history(case, run, protocol):
    spans = [s for root in run["local_traces"] for s in walk(root)]
    llms = sorted([s for s in spans if s["run_type"] == "llm"], key=lambda s: s["start_time"])
    tools = sorted([s for s in spans if s["run_type"] == "tool"], key=lambda s: s["start_time"])
    require(
        len(llms) == run["model_calls"] == len(run["model_history"]) <= 4,
        "Model count/budget mismatch",
    )
    require(
        len(tools) == run["query_count"] == len(run["tool_history"]) <= 3,
        "Tool count/budget mismatch",
    )
    for span, tool in zip(tools, run["tool_history"], strict=True):
        require(
            span["name"] == tool["name"] and same(span["inputs"], tool["args"]),
            "Actual tool span scope differs from history",
        )
        if not span.get("error"):
            require(
                same(span["outputs"], {"output": tool["result"]}),
                "Actual tool result differs from history",
            )
        else:
            require(bool(tool["result"].get("error")), "Actual tool failure was hidden")
    last_decision = None
    decoded_decisions = []
    report_checked = False
    for history, span in zip(run["model_history"], llms, strict=True):
        phase = history["phase"]
        require(phase in ("plan", "report"), "Unknown model phase")
        system = agent.SYSTEM + (agent.PLAN if phase == "plan" else agent.FINAL)
        require(history["input"][0] == system, "History instruction differs from freeze")
        require(
            span["inputs"]
            == {"prompts": ["System: " + system + "\nHuman: " + history["input"][1]]},
            "Actual span prompt differs from history",
        )
        outputs = span.get("outputs") or {}
        generations = outputs.get("generations")
        if generations:
            generation = generations[0][0]
            require(
                generation["text"]
                == history["output"]
                == generation["message"]["kwargs"]["content"],
                "Actual span response differs from history",
            )
            require(
                same(
                    generation["message"]["kwargs"].get("response_metadata", {}),
                    history.get("response_metadata", {}),
                ),
                "Response metadata differs",
            )
            require(
                same(
                    generation["message"]["kwargs"].get("usage_metadata"),
                    history.get("usage_metadata"),
                ),
                "Response token metadata differs",
            )
        else:
            require(
                history.get("output") is None and span.get("error"),
                "Missing actual response without recorded failure",
            )
        key = "decision" if phase == "plan" else "model_report_selection"
        require(
            canonical(span["extra"]["invocation_params"]["format"])
            == protocol["schema_sha256"][key],
            "Actual invoked schema differs from freeze",
        )
        require(
            span["extra"]["metadata"]["ls_model_name"] == run["model"], "Actual model tag differs"
        )
        representation = span["serialized"].get("repr", "")
        for setting in (
            "num_ctx=16384",
            "num_predict=3200",
            "seed=42",
            "reasoning=False",
            "http://127.0.0.1:11434",
            "'trust_env': False",
            "'follow_redirects': False",
        ):
            require(setting in representation, "Actual model configuration missing " + setting)
        payload = json.loads(history["input"][1])
        require(
            len(history["input"][1].encode()) <= protocol["protocol"]["max_prompt_payload_bytes"],
            "Payload exceeds frozen byte budget",
        )
        n = len(payload["tool_history"])
        require(
            0 <= n <= run["query_count"] and payload["remaining_queries"] == 3 - n,
            "Prompt query counters are not actual counters",
        )
        expected, aliases, evidence = compact_context(case, run["tool_history"][:n])
        for field_name, value in expected.items():
            require(same(payload[field_name], value), "Derived payload differs: " + field_name)
        require(
            payload["question"] == case["question"]
            and same(payload["hypotheses"], case["hypotheses"]),
            "Question/hypotheses differ from frozen input",
        )
        require(
            set(payload)
            == {
                "seed",
                "question",
                "hypotheses",
                "evidence",
                "chronology",
                "tool_history",
                "coverage",
                "credential_map",
                "remaining_queries",
                "previous_plan",
                "stop_reason",
            },
            "Unexpected model payload key",
        )
        previous = deepcopy(last_decision) if run["strategy"] == "adaptive" else None
        if previous:
            for entry in previous["ledger"]:
                entry["evidence_refs"] = [aliases.get(ref, ref) for ref in entry["evidence_refs"]]
            if previous["identifier"]:
                previous["identifier"] = aliases.get(previous["identifier"], previous["identifier"])
        require(same(payload["previous_plan"], previous), "Previous plan was substituted")
        if phase == "plan":
            try:
                parsed = Decision.model_validate_json(history["output"]).model_dump(mode="json")
            except (ValidationError, TypeError):
                require(
                    n == run["query_count"] and run["stop_reason"] == "plan_error",
                    "Invalid wire decision was followed by a hidden query",
                )
                continue
            decision = resolve_decision(parsed, aliases)
            decoded_decisions.append(decision)
            last_decision = decision
            catalog = evidence_coverage(evidence, run["tool_history"][:n])
            errors = validate_decision(
                decision, evidence, run["tool_history"][:n], case["hypotheses"], 3 - n, catalog
            )
            if errors:
                recorded = {
                    f.get("code")
                    for f in run["failures"]
                    if isinstance(f, dict) and f.get("phase") == "planning_validation"
                }
                require(
                    set(errors) <= recorded
                    and n == run["query_count"]
                    and run["stop_reason"] == "invalid_decision",
                    "Invalid decision was lost or executed",
                )
            elif decision["action"] == "finish":
                require(
                    n == run["query_count"] and run["stop_reason"] == "model_finish",
                    "Finish was not honored",
                )
            else:
                require(n < run["query_count"], "Selected action has no actual tool")
                tool = run["tool_history"][n]
                args = (
                    materialize_query(decision, catalog).model_dump(mode="json")
                    if decision["action"] == "query_events"
                    else {"identifier": decision["identifier"]}
                )
                require(
                    tool["name"] == decision["action"] and same(tool["args"], args),
                    "Tool differs from explicit model choice",
                )
        else:
            report_checked = True
            require(
                n == run["query_count"] and payload["stop_reason"] == run["stop_reason"],
                "Report hides terminal counters/reason",
            )
            try:
                wire = agent.ReportSelection.model_validate_json(history["output"]).model_dump(
                    mode="json"
                )
            except (ValidationError, TypeError):
                require(
                    run["status"] == "failed" and not run["findings"] and not run["observations"],
                    "Invalid report was replaced",
                )
                continue
            resolve = {alias: ref for ref, alias in aliases.items()}
            wire["selected_event_refs"] = [
                resolve.get(ref, ref) for ref in wire["selected_event_refs"]
            ]
            for finding in wire["findings"]:
                for link in finding["evidence_links"]:
                    link["citation"] = resolve.get(link["citation"], link["citation"])
                finding["citations"] = derived_citations(finding)
            if not any(isinstance(f, dict) and f.get("phase") == "report" for f in run["failures"]):
                for name in ("findings", "selected_event_refs", "limitations"):
                    require(
                        same(wire[name], run[name]),
                        "Materialized report changed raw model selection",
                    )
                errors = agent.validate_analysis(
                    {**wire, "observations": []}, evidence, case["hypotheses"]
                )
                if not errors:
                    projected = project_observations(
                        evidence,
                        wire["selected_event_refs"],
                        max_observations=protocol["protocol"]["max_projected_observations"],
                        max_bytes=protocol["protocol"]["max_projected_bytes"],
                    )
                    require(
                        same(projected, run["observations"]),
                        "Projected values differ from selected source records",
                    )
                else:
                    require(run["observations"] == [], "Invalid report received projected facts")
    require(
        same(decoded_decisions, run["decision_history"]),
        "Decision history differs from actual raw plans",
    )
    if run["strategy"] == "fixed":
        seed, _ = state_at(case, [])
        require(
            [e["args"] for e in run["tool_history"]] == agent.fixed_queries(seed),
            "Fixed control changed its frozen searches",
        )
    require(report_checked or run["status"] == "failed", "Reporting call disappeared")
    require(
        same(state_at(case, run["tool_history"])[1], run["evidence"]),
        "Final evidence is not actual returned state",
    )
    return Counter(s["run_type"] for s in spans)


def check_close(actual, expected, message):
    if isinstance(actual, bool) or isinstance(expected, bool):
        require(type(actual) is type(expected) and actual == expected, message)
    elif isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        require(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), message)
    else:
        require(actual == expected, message)


def save_private(path, document):
    require(not path.exists(), "Verification destination already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tracetrail-verification-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(document, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write("\n")
        require(not path.exists(), "Verification destination appeared during verification")
        Path(name).replace(path)
    finally:
        Path(name).unlink(missing_ok=True)
    require(path.stat().st_mode & 0o777 == 0o600, "Verification permissions are not private")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    parser.add_argument("--protocol", type=Path, default=Path("evaluation/protocol-v8.json"))
    parser.add_argument("--sdk", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path.cwd().resolve()
    raw_path = args.raw.resolve()
    sdk_path = (
        args.sdk or args.raw.with_name(args.raw.stem + ".claim-support-v1.langsmith-local.json")
    ).resolve()
    audit_path = (args.audit or args.raw.with_name(args.raw.stem + ".audit-summary.json")).resolve()
    output = (args.output or args.raw.with_name(args.raw.stem + ".verification.json")).resolve()
    require(
        output.is_relative_to(root / "local-results")
        and output.name.endswith(".verification.json"),
        "Output must be an ignored local-results/*.verification.json artifact",
    )
    require(
        output not in {raw_path, sdk_path, audit_path, args.protocol.resolve()},
        "Output collides with an input",
    )
    hashes = {str(p): sha(p) for p in (raw_path, sdk_path, audit_path, args.protocol.resolve())}
    raw, sdk, audit, protocol = [
        json.loads(p.read_bytes()) for p in (raw_path, sdk_path, audit_path, args.protocol)
    ]
    require(sha(args.protocol) == PROTOCOL_SHA, "Protocol fingerprint changed")
    require(
        protocol["prompt_sha256"]
        == PROMPT_SHA
        == hashlib.sha256((agent.SYSTEM + agent.PLAN + agent.FINAL).encode()).hexdigest(),
        "Prompt fingerprint changed",
    )
    require(sha("src/tracetrail/evaluation.py") == LEGACY_SHA, "Legacy scorer changed")
    for path, digest in protocol["source_sha256"].items():
        require(sha(path) == digest, "Frozen source changed: " + path)
    classes = {
        "decision": Decision,
        "claim_plan": ClaimPlan,
        "pivot_disposition": PivotDisposition,
        "evidence_link": agent.EvidenceLink,
        "materialized_analysis": agent.Analysis,
        "model_finding": agent.FindingSelection,
        "model_report_selection": agent.ReportSelection,
        "query": Query,
    }
    require(
        {name: canonical(cls.model_json_schema()) for name, cls in classes.items()}
        == protocol["schema_sha256"],
        "Frozen schema changed",
    )
    require(
        tuple(protocol["evaluation"]["numeric_metric_keys"]) == NUMERIC_KEYS
        and len(NUMERIC_KEYS) == 21,
        "Canonical scorer allowlist changed",
    )
    require(
        protocol["evaluation"]["primary_scorer"] == SCORER_ID
        and protocol["evaluation"]["scorer_id"] == SCORER_ID,
        "Frozen canonical scorer ID changed",
    )
    scorer_sha = sha("src/tracetrail/support_evaluation.py")
    require(scorer_sha == protocol["evaluation"]["source_sha256"], "Scorer fingerprint changed")
    manifest_path = Path(protocol["fresh_manifest"]["path"])
    require(
        raw["case_manifest_path"] == str(manifest_path)
        and sha(manifest_path)
        == raw["case_manifest_sha256"]
        == protocol["fresh_manifest"]["sha256"],
        "Fresh manifest differs",
    )
    cases = {case["id"]: case for case in load_cases(manifest_path)}
    require(
        len(cases) == 4
        and Counter(c["split"] for c in cases.values()) == {"development": 2, "heldout": 2},
        "Fresh case/split counts differ",
    )
    require(
        len(raw["selected_cases"]) == 4 and set(raw["selected_cases"]) == set(cases),
        "Fresh selection is incomplete",
    )
    expected_cells = {
        (case, model, strategy)
        for case in cases
        for model in protocol["models"]
        for strategy in (
            ["adaptive", "fixed"] if model == protocol["reference_model"] else ["adaptive"]
        )
    }
    observed_cells = [(r["case_id"], r["model"], r["strategy"]) for r in raw["runs"]]
    require(
        len(expected_cells) == len(observed_cells) == protocol["expected_fresh_runs"] == 16
        and set(observed_cells) == expected_cells,
        "Fresh cells are missing or duplicated",
    )
    require(raw["evaluation"]["primary_scorer"] == SCORER_ID, "Batch scorer ID changed")
    require(
        sdk["source_results_sha256"] == sha(raw_path)
        and sdk["status"] == "completed"
        and sdk["upload_results"] is False
        and sdk["inference_rerun"] is False,
        "SDK replay provenance differs",
    )
    require(
        sdk["evaluation"]
        == {
            "primary_scorer": SCORER_ID,
            "scorer_id": SCORER_ID,
            "source_sha256": scorer_sha,
            "stored_output_replay": True,
            "post_hoc": False,
        },
        "SDK scorer metadata differs",
    )
    for name in ("suite_id", "case_manifest_path", "case_manifest_sha256"):
        require(sdk[name] == raw[name], "SDK source metadata differs: " + name)
    sdk_rows = {row["inputs"]["result_index"]: row for row in sdk["evaluated_runs"]}
    require(
        len(sdk_rows) == len(sdk["evaluated_runs"]) == 16 and set(sdk_rows) == set(range(16)),
        "SDK rows are missing or duplicated",
    )
    require(len(audit["rows"]) == 16, "Root audit row count differs")
    total_spans = Counter()
    independent_rows = []
    for index, run in enumerate(raw["runs"]):
        case = cases[run["case_id"]]
        label = f"cell {index}: {run['model']} {run['strategy']} {run['case_id']}"
        require(
            run["split"] == case["split"]
            and run["fixture_sha256"] == case["fixture_sha256"]
            and run["test_only"] is False,
            label + " source labels differ",
        )
        require(
            run["protocol"] == raw["protocol"] == protocol["protocol"]
            and run["prompt_sha256"] == PROMPT_SHA,
            label + " protocol differs",
        )
        require(
            run["evaluation"]["primary_scorer"] == SCORER_ID
            and run["trace_storage"] == "local-only",
            label + " evaluation/trace scope differs",
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
            label + " termination counters differ",
        )
        require(
            run["stop_reason"] != "query_budget_exhausted" or run["query_count"] == 3,
            label + " false machine budget exhaustion",
        )
        total_spans.update(verify_history(case, run, protocol))
        legacy = score_run(case, run)
        require(same(legacy, run["metrics"]), label + " legacy metrics differ")
        counters, claim_rows = independent_support(case, run)
        stored = run["claim_support_metrics"]
        for key, expected in counters.items():
            check_close(stored[key], expected, label + " independent counter differs: " + key)
        require(
            stored["semantic_entailment_verified"] is False
            and stored["observation_projection_used_for_support"] is False,
            label + " scorer overclaims meaning",
        )
        for expected in claim_rows:
            actual = next(c for c in stored["per_claim"] if c["claim_id"] == expected["claim_id"])
            for key, value in expected.items():
                require(
                    actual[key] == value,
                    label + " claim counter differs: " + expected["claim_id"] + " " + key,
                )
        row = sdk_rows[index]
        expected_inputs = {
            "result_index": index,
            "case_id": run["case_id"],
            "model": run["model"],
            "strategy": run["strategy"],
        }
        require(
            row["inputs"] == expected_inputs
            and row["sdk_evaluation_trace"]["inputs"] == expected_inputs,
            label + " SDK inputs differ",
        )
        require(
            same(row["sdk_evaluation_trace"]["outputs"], {"result": run}),
            label + " SDK replayed different output",
        )
        require(not row["sdk_evaluation_trace"].get("error"), label + " SDK target failed")
        replay_meta = row["sdk_evaluation_trace"]["extra"]["metadata"]
        require(
            replay_meta["stored_output_replay"] is True and replay_meta["inference_rerun"] is False,
            label + " SDK trace replay metadata differs",
        )
        require(
            not any(s["run_type"] in ("llm", "tool") for s in walk(row["sdk_evaluation_trace"])),
            label + " SDK replay contains inference/tool calls",
        )
        feedback = row["sdk_feedback"]
        expected_feedback = {
            "claim_support_v1__" + k: v
            for k, v in counters.items()
            if isinstance(v, (bool, int, float)) and math.isfinite(float(v))
        }
        require(
            len(feedback) == len(expected_feedback) == 21, label + " SDK feedback count differs"
        )
        require(
            {f["key"]: f["score"] for f in feedback} == expected_feedback,
            label + " SDK feedback differs from independent counters",
        )
        require(
            all(not (f.get("extra") or {}).get("error") for f in feedback),
            label + " SDK feedback failed",
        )
        ar = next(r for r in audit["rows"] if r["result_index"] == index)
        require(
            same(ar["metrics"], legacy) and same(ar["claim_support_metrics"], stored),
            label + " root audit row differs",
        )
        independent_rows.append(
            {
                "result_index": index,
                "case_id": run["case_id"],
                "split": run["split"],
                "model": run["model"],
                "strategy": run["strategy"],
                "status": run["status"],
                "independent_claim_support_counters": counters,
                "per_claim": claim_rows,
            }
        )
    expected_groups = {(model, strategy) for _, model, strategy in expected_cells}
    require(
        len(audit["groups"]) == len(expected_groups) == 4
        and {(g["model"], g["strategy"]) for g in audit["groups"]} == expected_groups,
        "Root audit groups are missing or duplicated",
    )
    for group in audit["groups"]:
        members = [
            r
            for r in independent_rows
            if r["model"] == group["model"] and r["strategy"] == group["strategy"]
        ]
        require(len(members) == group["run_count"] == 4, "Root group count differs")
        require(
            group["declared_field_path_coverage"]["covered"]
            == sum(
                r["independent_claim_support_counters"]["process_valid_covered_atom_count"]
                for r in members
            )
            and group["declared_field_path_coverage"]["required"]
            == sum(r["independent_claim_support_counters"]["required_atom_count"] for r in members),
            "Root primary atom totals differ from independent source-derived counters",
        )
        for key in NUMERIC_KEYS:
            expected = sum(r["independent_claim_support_counters"][key] for r in members) / len(
                members
            )
            check_close(
                group["mean_claim_support_metrics"][key],
                expected,
                "Root group counter differs: " + key,
            )
        require(
            len(group["split_rows"]) == 2
            and {s["split"] for s in group["split_rows"]} == {"development", "heldout"},
            "Root group split rows are missing or duplicated",
        )
        for split in group["split_rows"]:
            items = [r for r in members if r["split"] == split["split"]]
            require(len(items) == split["run_count"] == 2, "Root split count differs")
            for key in NUMERIC_KEYS:
                expected = sum(r["independent_claim_support_counters"][key] for r in items) / len(
                    items
                )
                check_close(
                    split["mean_claim_support_metrics"][key],
                    expected,
                    "Root split counter differs: " + key,
                )
    for path, digest in hashes.items():
        require(sha(path) == digest, "An input changed during verification")
    for path, digest in protocol["source_sha256"].items():
        require(sha(path) == digest, "A frozen runtime source changed during verification")
    document = {
        "schema_version": "1",
        "created_at": datetime.now(UTC).isoformat(),
        "status": "verified",
        "mode": "independent-stored-output-verification",
        "new_model_calls": 0,
        "sdk_replays_performed_by_this_verifier": 0,
        "uploads_enabled": False,
        "semantic_entailment_verified": False,
        "independent_human_review": False,
        "independence": (
            "All 21 claim counters re-derived without score_claim_support; frozen "
            "legacy/link/planning/context helpers reused for their mechanical contracts."
        ),
        "protocol_sha256": PROTOCOL_SHA,
        "prompt_sha256": PROMPT_SHA,
        "scorer_source_sha256": scorer_sha,
        "verifier_sha256": sha(__file__),
        "inputs": hashes,
        "fresh_cells": len(independent_rows),
        "sdk_feedback_count": 16 * 21,
        "actual_original_span_counts": dict(total_spans),
        "status_counts": dict(Counter(r["status"] for r in independent_rows)),
        "rows": independent_rows,
    }
    save_private(output, document)
    print(
        json.dumps(
            {
                "path": str(output),
                "sha256": sha(output),
                "status": "verified",
                "fresh_cells": 16,
                "numeric_feedback": 336,
                "actual_original_span_counts": dict(total_spans),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
