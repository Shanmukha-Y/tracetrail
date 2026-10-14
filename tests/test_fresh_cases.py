"""Fresh fixture and scorer checks, without model inference or canned answers."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import ipaddress
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from tracetrail.evaluation import load_cases, score_run
from tracetrail.store import CloudTrailStore, Query

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/cases-v3.json"
MANIFEST_SHA256 = "6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d"
PRIOR_MANIFEST_HASHES = {
    "cases.json": "2271b38c065aea28868f5b1578a2b9368ed5f82f684afb02bdf05d8b68a012e7",
    "cases-v2.json": "c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446",
}


def _constructed_report(case: dict) -> dict:
    """A scorer unit-test object derived from annotations, not a model report."""
    evidence = [
        {
            "ref": f"sha256:{case['fixture_sha256']}/Records/{index}",
            "event_id": record["eventID"],
            "record": copy.deepcopy(record),
        }
        for index, record in enumerate(case["_fixture_records"])
    ]
    refs = {item["event_id"]: item["ref"] for item in evidence}
    annotations = {a["claim_id"]: a for a in case["annotations"]}
    findings = [
        {
            "claim_id": h["claim_id"],
            "statement": h["statement"],
            "status": annotations[h["claim_id"]]["expected_status"],
            "citations": [refs[e] for e in annotations[h["claim_id"]]["required_event_ids"]],
        }
        for h in case["hypotheses"]
    ]
    observations = [
        {
            "citation": refs[o["event_id"]],
            "field": o["field"],
            "present": o.get("present", True),
            "value": copy.deepcopy(o["value"]),
        }
        for annotation in case["annotations"]
        for o in annotation["required_observations"]
    ]
    observations = list({json.dumps(o, sort_keys=True): o for o in observations}.values())
    return {
        "findings": findings,
        "observations": observations,
        "evidence": evidence,
        "selected_event_refs": [refs[e] for e in case["relevant_event_ids"]],
        "query_count": 1,
        "model_calls": 0,
        "duration_seconds": 0,
        "tool_history": [{"name": "query_events", "args": {}, "result": {"records": evidence}}],
        "failures": [],
        "test_only": True,
    }


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_v3_manifest_and_prior_suites_keep_frozen_hashes():
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256
    cases = load_cases(MANIFEST)
    assert [c["split"] for c in cases] == ["development", "heldout"]
    assert all(c["_suite_id"] == "tracetrail-synthetic-v3" for c in cases)
    for name, expected_hash in PRIOR_MANIFEST_HASHES.items():
        path = ROOT / "evaluation" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
        load_cases(path)
    prior_ids = {
        r["eventID"]
        for name in PRIOR_MANIFEST_HASHES
        for case in load_cases(ROOT / "evaluation" / name)
        for r in case["_fixture_records"]
    }
    assert all(r["eventID"] not in prior_ids for c in cases for r in c["_fixture_records"])


@pytest.mark.parametrize("case_index", range(2))
def test_fresh_exact_annotated_report_passes_every_fixed_claim(case_index):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    assert len(case["hypotheses"]) <= 4
    assert len(case["relevant_event_ids"]) <= 6
    assert len(report["observations"]) <= 24
    metrics = score_run(case, report)
    assert metrics["supported_annotation_rate"] == 1
    assert metrics["unsupported_claims"] == 0
    assert metrics["insufficient_evidence_handling"] == 1
    assert metrics["relevant_event_precision"] == 1
    assert metrics["relevant_event_recall"] == 1


def test_read_only_response_and_session_issuance_fields_match_cloudtrail():
    docs_networks = [
        ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
    ]
    for case in load_cases(MANIFEST):
        records = case["_fixture_records"]
        assert len(records) == 6
        assert len(json.dumps({"Records": records}).encode()) < 20_000
        issued = {}
        for record in records:
            assert record["recipientAccountId"] == "000000000000"
            assert record["userIdentity"]["accountId"] == "000000000000"
            assert any(ipaddress.ip_address(record["sourceIPAddress"]) in n for n in docs_networks)
            if record["eventName"] == "AssumeRole":
                assert record["readOnly"] is True
                credentials = record["responseElements"]["credentials"]
                assert "secretAccessKey" not in credentials
                issued[credentials["accessKeyId"]] = record["eventTime"]
            elif record["readOnly"]:
                assert record["responseElements"] is None
            if record["eventName"] == "GetObject":
                assert record["eventCategory"] == "Data"
                assert record["managementEvent"] is False
        for record in records:
            identity = record["userIdentity"]
            if identity["type"] == "AssumedRole":
                created = identity["sessionContext"]["attributes"]["creationDate"]
                assert created == issued[identity["accessKeyId"]]
                assert _time(created) <= _time(record["eventTime"])


def test_invented_principal_ids_are_valid_and_distinct_for_distinct_roles():
    role_ids = {}
    for case in load_cases(MANIFEST):
        records = case["_fixture_records"]
        returned_principals = {
            r["responseElements"]["credentials"]["accessKeyId"]: r["responseElements"][
                "assumedRoleUser"
            ]["assumedRoleId"]
            for r in records
            if r["eventName"] == "AssumeRole"
        }
        for record in records:
            identity = record["userIdentity"]
            if identity["type"] == "IAMUser":
                assert re.fullmatch(r"AIDA[A-Z0-9]{17}", identity["principalId"])
                continue
            issuer = identity["sessionContext"]["sessionIssuer"]
            assert re.fullmatch(r"AROA[A-Z0-9]{17}", issuer["principalId"])
            assert identity["principalId"].split(":", 1)[0] == issuer["principalId"]
            assert identity["principalId"] == returned_principals[identity["accessKeyId"]]
            role_ids[issuer["arn"]] = issuer["principalId"]
    assert len(role_ids) == 2
    assert len(set(role_ids.values())) == 2


@pytest.mark.parametrize(
    ("case_index", "claim_id", "field", "event_name"),
    [
        (0, "returned_key_join", "eventTime", "AssumeRole"),
        (0, "logging_activity", "readOnly", "GetTrailStatus"),
        (0, "caller_source_change", "userIdentity.userName", "GetCallerIdentity"),
        (1, "issuer_join", "eventTime", "AssumeRole"),
        (1, "original_caller_context", "eventTime", "ListBuckets"),
    ],
)
def test_required_temporal_identity_and_readonly_observations_cannot_be_omitted(
    case_index, claim_id, field, event_name
):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    event = next(
        e
        for e in report["evidence"]
        if e["record"]["eventName"] == event_name and e["event_id"] in case["relevant_event_ids"]
    )
    report["observations"] = [
        o
        for o in report["observations"]
        if not (o["citation"] == event["ref"] and o["field"] == field)
    ]
    finding = next(f for f in score_run(case, report)["per_finding"] if f["claim_id"] == claim_id)
    assert finding["annotation_supported"] is False
    assert "missing_or_wrong_required_observation" in finding["reasons"]


def test_development_caller_context_precedes_fixed_window_and_child_changes_ip():
    case = load_cases(MANIFEST)[0]
    records = case["_fixture_records"]
    seed = next(r for r in records if r["eventID"] == case["seed_event_id"])
    assert seed["eventName"] == "AssumeRole"
    key = seed["userIdentity"]["accessKeyId"]
    previous = next(r for r in records if r["eventName"] == "GetCallerIdentity")
    assert previous["userIdentity"]["accessKeyId"] == key
    assert _time(previous["eventTime"]) < _time(seed["eventTime"]) - timedelta(hours=1)
    assert previous["sourceIPAddress"] != seed["sourceIPAddress"]
    returned_key = seed["responseElements"]["credentials"]["accessKeyId"]
    children = [r for r in records if r["userIdentity"]["accessKeyId"] == returned_key]
    assert {r["eventName"] for r in children} == {"StopLogging", "GetTrailStatus"}
    assert all(r["sourceIPAddress"] != seed["sourceIPAddress"] for r in children)
    status = next(r for r in children if r["eventName"] == "GetTrailStatus")
    assert status["responseElements"] is None


def test_heldout_data_seed_can_find_issuer_then_original_caller_with_real_queries():
    """These are real local log queries; no agent or model capability is asserted."""
    case = load_cases(MANIFEST)[1]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])["record"]
    assert seed["eventName"] == "GetObject"
    key = seed["userIdentity"]["accessKeyId"]
    assert key.startswith("ASIA")
    issuer_records = store.query(Query(issued_access_key=key))["records"]
    assert len(issuer_records) == 1
    issuer = issuer_records[0]["record"]
    assert issuer["eventName"] == "AssumeRole"
    assert issuer["sourceIPAddress"] != seed["sourceIPAddress"]
    assert _time(issuer["eventTime"]) < _time(seed["eventTime"])
    original = store.query(Query(access_key=issuer["userIdentity"]["accessKeyId"]))["records"]
    previous = next(e["record"] for e in original if e["record"]["eventName"] == "ListBuckets")
    assert _time(previous["eventTime"]) < _time(issuer["eventTime"])
    assert previous["sourceIPAddress"] != issuer["sourceIPAddress"]
    children = store.query(Query(access_key=key))["records"]
    failed = next(e["record"] for e in children if e["record"]["eventName"] == "DeleteBucket")
    assert failed["errorCode"] == "AccessDenied"
    assert _time(seed["eventTime"]) < _time(failed["eventTime"])


@pytest.mark.parametrize("case_index", range(2))
def test_distractors_have_other_keys_and_principals_and_lower_precision(case_index):
    case = load_cases(MANIFEST)[case_index]
    relevant = [r for r in case["_fixture_records"] if r["eventID"] in case["relevant_event_ids"]]
    noise = [r for r in case["_fixture_records"] if r["eventID"] not in case["relevant_event_ids"]]
    relevant_keys = {r["userIdentity"]["accessKeyId"] for r in relevant}
    relevant_principals = {r["userIdentity"]["arn"] for r in relevant}
    assert len(noise) == 2
    assert all(r["userIdentity"]["accessKeyId"] not in relevant_keys for r in noise)
    assert all(r["userIdentity"]["arn"] not in relevant_principals for r in noise)
    report = _constructed_report(case)
    report["selected_event_refs"] = [e["ref"] for e in report["evidence"]]
    assert score_run(case, report)["relevant_event_precision"] == 4 / 6


@pytest.mark.parametrize("case_index", range(2))
def test_approval_claim_is_uncertain_even_with_real_session_name(case_index):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    finding = next(f for f in report["findings"] if f["claim_id"].startswith("approved_"))
    assert finding["status"] == "uncertain"
    finding["status"] = "supported"
    assert score_run(case, report)["unsupported_claims"] == 1


def test_missing_original_caller_record_does_not_support_joined_history():
    case = load_cases(MANIFEST)[1]
    report = _constructed_report(case)
    previous = next(
        e
        for e in report["evidence"]
        if e["record"]["eventName"] == "ListBuckets" and e["event_id"] in case["relevant_event_ids"]
    )
    report["evidence"] = [e for e in report["evidence"] if e["ref"] != previous["ref"]]
    report["tool_history"][0]["result"]["records"] = report["evidence"]
    report["observations"] = [o for o in report["observations"] if o["citation"] != previous["ref"]]
    metrics = score_run(case, report)
    assert metrics["relevant_event_recall"] == 3 / 4
    unsupported = [f for f in metrics["per_finding"] if not f["annotation_supported"]]
    assert {f["claim_id"] for f in unsupported} == {"original_caller_context"}


def test_denied_delete_cannot_score_as_success():
    case = load_cases(MANIFEST)[1]
    report = _constructed_report(case)
    finding = next(f for f in report["findings"] if f["claim_id"] == "deletion_succeeded")
    assert finding["status"] == "refuted"
    finding["status"] = "supported"
    assert score_run(case, report)["unsupported_claims"] == 1


def test_v3_builder_reproduces_frozen_outputs_without_touching_other_files(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "fresh_fixture_builder_test_only", ROOT / "fixtures/build_synthetic_v3.py"
    )
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    (tmp_path / "evaluation").mkdir()
    prior_marker = tmp_path / "evaluation/cases-v2.json"
    prior_marker.write_text("preserve existing prior suite bytes\n")
    before = prior_marker.read_bytes()
    builder.build()
    assert (tmp_path / "evaluation/cases-v3.json").read_bytes() == MANIFEST.read_bytes()
    for case in load_cases(tmp_path / "evaluation/cases-v3.json"):
        assert (tmp_path / case["fixture"]).read_bytes() == (ROOT / case["fixture"]).read_bytes()
    builder.build()
    assert prior_marker.read_bytes() == before
    assert (tmp_path / "evaluation/cases-v3.json").read_bytes() == MANIFEST.read_bytes()
