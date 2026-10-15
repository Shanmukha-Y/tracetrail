"""Frozen v4 case checks with local queries and scorer-only test reports."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from tracetrail.evaluation import load_cases, score_run
from tracetrail.store import CloudTrailStore, Query

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/cases-v4.json"
MANIFEST_SHA256 = "25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16"
PRIOR_MANIFEST_HASHES = {
    "cases.json": "2271b38c065aea28868f5b1578a2b9368ed5f82f684afb02bdf05d8b68a012e7",
    "cases-v2.json": "c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446",
    "cases-v3.json": "6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d",
}


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _constructed_report(case: dict) -> dict:
    """A gold-derived scorer unit-test input, not an agent or model result."""
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


def _assert_scalar_record_tree(value):
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str) and key and "." not in key
            _assert_scalar_record_tree(item)
    else:
        assert value is None or type(value) in (str, bool, int, float)


def test_v4_is_small_fresh_and_preserves_prior_suites():
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256
    cases = load_cases(MANIFEST)
    assert [c["split"] for c in cases] == ["development", "heldout"]
    assert all(c["_suite_id"] == "tracetrail-synthetic-v4" for c in cases)
    old_ids = set()
    for name, expected_hash in PRIOR_MANIFEST_HASHES.items():
        path = ROOT / "evaluation" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
        for case in load_cases(path):
            old_ids.update(r["eventID"] for r in case["_fixture_records"])
    for case in cases:
        assert len(case["_fixture_records"]) <= 8
        assert len(case["relevant_event_ids"]) == len(case["hypotheses"]) == 4
        assert len(json.dumps(case["_fixture_records"]).encode()) < 20_000
        assert all(r["eventID"] not in old_ids for r in case["_fixture_records"])
        for record in case["_fixture_records"]:
            _assert_scalar_record_tree(record)


@pytest.mark.parametrize("case_index", range(2))
def test_v4_exact_source_claims_score_complete(case_index):
    case = load_cases(MANIFEST)[case_index]
    metrics = score_run(case, _constructed_report(case))
    assert metrics["supported_annotation_rate"] == 1
    assert metrics["status_accuracy"] == 1
    assert metrics["insufficient_evidence_handling"] == 1
    assert metrics["unsupported_claims"] == 0
    assert metrics["relevant_event_precision"] == 1
    assert metrics["relevant_event_recall"] == 1


def test_utc_raw_times_issuance_readonly_and_synthetic_identity_fields():
    networks = [
        ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
    ]
    role_ids = {}
    for case in load_cases(MANIFEST):
        issued = {}
        for record in case["_fixture_records"]:
            assert record["eventTime"].endswith("Z")
            assert record["recipientAccountId"] == "000000000000"
            assert any(ipaddress.ip_address(record["sourceIPAddress"]) in n for n in networks)
            identity = record["userIdentity"]
            assert identity["accountId"] == "000000000000"
            if identity["type"] == "IAMUser":
                assert re.fullmatch(r"AIDA[A-Z0-9]{17}", identity["principalId"])
            if record["eventName"] == "AssumeRole":
                assert record["readOnly"] is True
                credentials = record["responseElements"]["credentials"]
                assert "secretAccessKey" not in credentials
                issued[credentials["accessKeyId"]] = record
            elif record["readOnly"]:
                assert record["responseElements"] is None
            if record["eventName"] in {"GetObject", "DeleteObject"}:
                assert record["eventCategory"] == "Data"
                assert record["managementEvent"] is False
            else:
                assert record["eventCategory"] == "Management"
                assert record["managementEvent"] is True
        for record in case["_fixture_records"]:
            identity = record["userIdentity"]
            if identity["type"] != "AssumedRole":
                continue
            issuer = issued[identity["accessKeyId"]]
            created = identity["sessionContext"]["attributes"]["creationDate"]
            assert created.endswith("Z")
            assert created == issuer["eventTime"]
            assert (
                _time(created)
                <= _time(record["eventTime"])
                < _time(issuer["responseElements"]["credentials"]["expiration"])
            )
            role = identity["sessionContext"]["sessionIssuer"]
            assert re.fullmatch(r"AROA[A-Z0-9]{17}", role["principalId"])
            assert identity["principalId"].split(":", 1)[0] == role["principalId"]
            assert (
                identity["principalId"]
                == issuer["responseElements"]["assumedRoleUser"]["assumedRoleId"]
            )
            role_ids[role["arn"]] = role["principalId"]
    assert len(role_ids) == len(set(role_ids.values())) == 2


def test_development_actual_order_crosses_midnight_and_refutes_reversal():
    case = load_cases(MANIFEST)[0]
    records = {
        r["eventName"]: r
        for r in case["_fixture_records"]
        if r["eventID"] in case["relevant_event_ids"]
    }
    seed = records["AssumeRole"]
    expected_offsets = {
        "GetCallerIdentity": -540,
        "AssumeRole": 0,
        "UpdateRole": 180,
        "GetRole": 300,
    }
    for name, seconds in expected_offsets.items():
        assert (
            _time(records[name]["eventTime"]) - _time(seed["eventTime"])
        ).total_seconds() == seconds
    assert records["UpdateRole"]["eventTime"][:10] != seed["eventTime"][:10]
    annotations = {a["claim_id"]: a for a in case["annotations"]}
    assert annotations["change_before_issuance"]["expected_status"] == "refuted"
    report = _constructed_report(case)
    claim = next(f for f in report["findings"] if f["claim_id"] == "change_before_issuance")
    claim["status"] = "supported"
    assert score_run(case, report)["unsupported_claims"] == 1


def test_offset_query_bounds_equal_utc_bounds_across_local_date_boundaries():
    """Real local queries test offset input; native fixture times stay UTC Z."""
    case = load_cases(MANIFEST)[0]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])["record"]
    key = seed["responseElements"]["credentials"]["accessKeyId"]
    offset = store.query(
        Query(
            access_key=key,
            start_time="2026-03-15T05:30:00+05:30",
            end_time="2026-03-14T20:03:00-04:00",
        )
    )
    utc = store.query(
        Query(access_key=key, start_time="2026-03-15T00:00:00Z", end_time="2026-03-15T00:03:00Z")
    )
    assert offset == utc
    assert [e["record"]["eventName"] for e in offset["records"]] == ["UpdateRole", "GetRole"]


@pytest.mark.parametrize("case_index", range(2))
def test_relevant_chain_is_retrievable_with_at_most_three_observed_key_queries(case_index):
    """Log-tool reachability is tested separately from actual model behavior."""
    case = load_cases(MANIFEST)[case_index]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])
    found = {seed["event_id"]}
    query_count = 0
    if seed["record"]["eventName"] == "AssumeRole":
        original = seed["record"]["userIdentity"]["accessKeyId"]
        temporary = seed["record"]["responseElements"]["credentials"]["accessKeyId"]
    else:
        temporary = seed["record"]["userIdentity"]["accessKeyId"]
        issuer = store.query(Query(issued_access_key=temporary))["records"]
        query_count += 1
        assert len(issuer) == 1
        found.update(e["event_id"] for e in issuer)
        original = issuer[0]["record"]["userIdentity"]["accessKeyId"]
    for key in (original, temporary):
        found.update(e["event_id"] for e in store.query(Query(access_key=key))["records"])
        query_count += 1
    assert query_count <= 3
    assert found == set(case["relevant_event_ids"])


def test_empty_string_null_and_absent_error_have_distinct_source_meanings():
    case = load_cases(MANIFEST)[0]
    records = [r for r in case["_fixture_records"] if r["eventID"] in case["relevant_event_ids"]]
    change = next(r for r in records if r["eventName"] == "UpdateRole")
    read = next(r for r in records if r["eventName"] == "GetRole")
    assert change["requestParameters"]["description"] == ""
    assert "errorCode" not in change
    assert "responseElements" in read and read["responseElements"] is None
    report = _constructed_report(case)
    empty = next(o for o in report["observations"] if o["field"] == "requestParameters.description")
    empty["value"] = None
    metrics = score_run(case, report)
    assert metrics["invalid_observation_count"] == 1
    assert metrics["unsupported_claims"] == 2


@pytest.mark.parametrize("case_index", range(2))
def test_same_ip_noise_has_other_principals_and_lowers_selection_precision(case_index):
    case = load_cases(MANIFEST)[case_index]
    relevant = [r for r in case["_fixture_records"] if r["eventID"] in case["relevant_event_ids"]]
    noise = [r for r in case["_fixture_records"] if r["eventID"] not in case["relevant_event_ids"]]
    keys = {r["userIdentity"]["accessKeyId"] for r in relevant}
    principals = {r["userIdentity"]["arn"] for r in relevant}
    addresses = {r["sourceIPAddress"] for r in relevant}
    assert len(noise) == 2
    assert all(r["sourceIPAddress"] in addresses for r in noise)
    assert all(r["userIdentity"]["accessKeyId"] not in keys for r in noise)
    assert all(r["userIdentity"]["arn"] not in principals for r in noise)
    report = _constructed_report(case)
    report["selected_event_refs"] = [e["ref"] for e in report["evidence"]]
    assert score_run(case, report)["relevant_event_precision"] == 4 / 6


@pytest.mark.parametrize("case_index", range(2))
def test_unlogged_state_or_approval_is_not_proved_by_activity(case_index):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    claim_id = "later_role_state" if case_index == 0 else "approved_retention"
    finding = next(f for f in report["findings"] if f["claim_id"] == claim_id)
    assert finding["status"] == "uncertain"
    finding["status"] = "supported"
    assert score_run(case, report)["unsupported_claims"] == 1


def test_v4_builder_reproduces_outputs_without_reading_or_changing_old_suites(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "case_builder_v4_test_only", ROOT / "fixtures/build_synthetic_v4.py"
    )
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    (tmp_path / "evaluation").mkdir()
    marker = tmp_path / "evaluation/cases-v3.json"
    marker.write_text("keep prior immutable fixture bytes\n")
    original = marker.read_bytes()
    builder.build()
    output = tmp_path / "evaluation/cases-v4.json"
    assert output.read_bytes() == MANIFEST.read_bytes()
    for case in load_cases(output):
        assert (tmp_path / case["fixture"]).read_bytes() == (ROOT / case["fixture"]).read_bytes()
    builder.build()
    assert marker.read_bytes() == original
    assert output.read_bytes() == MANIFEST.read_bytes()
