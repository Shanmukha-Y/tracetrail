"""Fresh v5 fixture and scorer tests, without model calls or network access."""

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
MANIFEST = ROOT / "evaluation/cases-v5.json"
MANIFEST_SHA256 = "66f704a593c5d152d82f683cded4b1fa8014f58fe05f337d0bdaef615cde3e96"
PRIOR_HASHES = {
    "cases.json": "2271b38c065aea28868f5b1578a2b9368ed5f82f684afb02bdf05d8b68a012e7",
    "cases-v2.json": "c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446",
    "cases-v3.json": "6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d",
    "cases-v4.json": "25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16",
}


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _constructed_report(case):
    """Gold-derived scorer input for tests only; never model capability evidence."""
    evidence = [
        {
            "ref": f"sha256:{case['fixture_sha256']}/Records/{i}",
            "event_id": r["eventID"],
            "record": copy.deepcopy(r),
        }
        for i, r in enumerate(case["_fixture_records"])
    ]
    refs = {e["event_id"]: e["ref"] for e in evidence}
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
        for a in case["annotations"]
        for o in a["required_observations"]
    ]
    observations = list({json.dumps(o, sort_keys=True): o for o in observations}.values())
    return {
        "findings": findings,
        "observations": observations,
        "evidence": evidence,
        "selected_event_refs": [refs[e] for e in case["relevant_event_ids"]],
        "tool_history": [{"name": "query_events", "args": {}, "result": {"records": evidence}}],
        "query_count": 1,
        "model_calls": 0,
        "duration_seconds": 0,
        "failures": [],
        "test_only": True,
    }


def _assert_scalar_tree(value):
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str) and key and "." not in key
            _assert_scalar_tree(item)
    else:
        assert value is None or type(value) in (str, bool, int, float)


def test_four_cases_are_fresh_small_and_keep_all_prior_suite_bytes():
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256
    old_ids = set()
    for name, expected in PRIOR_HASHES.items():
        path = ROOT / "evaluation" / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        for case in load_cases(path):
            old_ids.update(r["eventID"] for r in case["_fixture_records"])
    cases = load_cases(MANIFEST)
    assert [c["split"] for c in cases] == ["development", "development", "heldout", "heldout"]
    for case in cases:
        assert case["_suite_id"] == "tracetrail-synthetic-v5"
        assert len(case["hypotheses"]) == 4
        assert 3 <= len(case["relevant_event_ids"]) <= 4
        assert 1 <= len(case["_fixture_records"]) - len(case["relevant_event_ids"]) <= 2
        assert len(json.dumps(case["_fixture_records"]).encode()) < 20_000
        for record in case["_fixture_records"]:
            assert record["eventID"] not in old_ids
            _assert_scalar_tree(record)


@pytest.mark.parametrize("case_index", range(4))
def test_constructed_exact_support_reports_score_all_fixed_claims(case_index):
    case = load_cases(MANIFEST)[case_index]
    metrics = score_run(case, _constructed_report(case))
    assert metrics["supported_annotation_rate"] == 1
    assert metrics["status_accuracy"] == 1
    assert metrics["unsupported_claims"] == 0
    assert metrics["insufficient_evidence_handling"] == 1
    assert metrics["relevant_event_precision"] == 1
    assert metrics["relevant_event_recall"] == 1


@pytest.mark.parametrize("case_index", range(4))
def test_valid_noise_citation_cannot_replace_claim_specific_source(case_index):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    noise = next(e for e in report["evidence"] if e["event_id"] not in case["relevant_event_ids"])
    report["selected_event_refs"].append(noise["ref"])
    report["findings"][0]["citations"] = [noise["ref"]]
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 1
    assert "missing_required_citation" in metrics["per_finding"][0]["reasons"]


def test_exact_native_api_shapes_ids_and_credential_issuance_dates():
    networks = [
        ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
    ]
    role_ids = {}
    for case in load_cases(MANIFEST):
        issued = {}
        for r in case["_fixture_records"]:
            assert r["eventTime"].endswith("Z")
            assert r["recipientAccountId"] == "000000000000"
            assert r["userIdentity"]["accountId"] == "000000000000"
            assert any(ipaddress.ip_address(r["sourceIPAddress"]) in n for n in networks)
            if r["eventName"] == "AssumeRole":
                assert r["readOnly"] is True
                credentials = r["responseElements"]["credentials"]
                assert "secretAccessKey" not in credentials
                issued[credentials["accessKeyId"]] = r
            elif r["readOnly"]:
                assert r["responseElements"] is None
            if r["eventName"] == "DisableKey":
                assert r["responseElements"] == {"keyId": r["requestParameters"]["keyId"]}
            if r["eventName"] == "UpdateAccessKey":
                assert r["requestParameters"]["userName"] == "batch-reader"
                assert r["requestParameters"]["status"] == "Inactive"
                assert r["requestParameters"]["accessKeyId"] != r["userIdentity"]["accessKeyId"]
            if r["eventName"] == "DeleteSecurityGroup":
                assert re.fullmatch(
                    r"sg-(?:[0-9a-f]{8}|[0-9a-f]{17})", r["requestParameters"]["groupId"]
                )
                assert r["errorCode"] == "Client.UnauthorizedOperation"
            assert r["eventCategory"] == ("Data" if r["eventName"] == "PutObject" else "Management")
            assert r["managementEvent"] is (r["eventName"] != "PutObject")
        for r in case["_fixture_records"]:
            identity = r["userIdentity"]
            if identity["type"] == "IAMUser":
                assert re.fullmatch(r"AIDA[A-Z0-9]{17}", identity["principalId"])
                continue
            issuer = issued[identity["accessKeyId"]]
            role = identity["sessionContext"]["sessionIssuer"]
            assert re.fullmatch(r"AROA[A-Z0-9]{17}", role["principalId"])
            assert identity["principalId"].split(":", 1)[0] == role["principalId"]
            assert (
                identity["principalId"]
                == issuer["responseElements"]["assumedRoleUser"]["assumedRoleId"]
            )
            created = identity["sessionContext"]["attributes"]["creationDate"]
            assert created == issuer["eventTime"]
            assert (
                _time(created)
                <= _time(r["eventTime"])
                < _time(issuer["responseElements"]["credentials"]["expiration"])
            )
            role_ids[role["arn"]] = role["principalId"]
    assert len(role_ids) == len(set(role_ids.values())) == 4


@pytest.mark.parametrize("case_index", range(4))
def test_actual_local_queries_reach_all_relevant_records_within_three_queries(case_index):
    """Tool reachability test only, not evidence of a model's query choices."""
    case = load_cases(MANIFEST)[case_index]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])
    found = {seed["event_id"]}
    count = 0
    if seed["record"]["eventName"] == "AssumeRole":
        original = seed["record"]["userIdentity"]["accessKeyId"]
        temporary = seed["record"]["responseElements"]["credentials"]["accessKeyId"]
    else:
        temporary = seed["record"]["userIdentity"]["accessKeyId"]
        issuers = store.query(Query(issued_access_key=temporary))["records"]
        assert len(issuers) == 1
        found.update(e["event_id"] for e in issuers)
        original = issuers[0]["record"]["userIdentity"]["accessKeyId"]
        count += 1
    for key in (original, temporary):
        found.update(e["event_id"] for e in store.query(Query(access_key=key))["records"])
        count += 1
    assert count <= 3
    assert found == set(case["relevant_event_ids"])


@pytest.mark.parametrize(
    ("case_index", "contradicted", "unknown"),
    [
        (0, "activation_requested", "later_key_state"),
        (1, "deletion_succeeded", "later_group_absence"),
        (2, "upload_succeeded", "approved_publication"),
    ],
)
def test_direct_contradiction_is_distinct_from_no_state_or_approval_evidence(
    case_index, contradicted, unknown
):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    findings = {f["claim_id"]: f for f in report["findings"]}
    assert findings[contradicted]["status"] == "refuted"
    assert findings[unknown]["status"] == "uncertain"
    findings[unknown]["status"] = "refuted"
    assert score_run(case, report)["unsupported_claims"] == 1


def test_kms_returned_arn_is_not_key_state_or_maintenance_approval():
    case = load_cases(MANIFEST)[3]
    report = _constructed_report(case)
    for claim_id in ("later_disabled_state", "approved_maintenance"):
        finding = next(f for f in report["findings"] if f["claim_id"] == claim_id)
        assert finding["status"] == "uncertain"
        finding["status"] = "supported"
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 2


@pytest.mark.parametrize("case_index", range(4))
def test_same_ip_noise_uses_other_principals_and_decreases_precision(case_index):
    case = load_cases(MANIFEST)[case_index]
    relevant = [r for r in case["_fixture_records"] if r["eventID"] in case["relevant_event_ids"]]
    noise = [r for r in case["_fixture_records"] if r["eventID"] not in case["relevant_event_ids"]]
    keys = {r["userIdentity"]["accessKeyId"] for r in relevant}
    principals = {r["userIdentity"]["arn"] for r in relevant}
    addresses = {r["sourceIPAddress"] for r in relevant}
    assert all(r["sourceIPAddress"] in addresses for r in noise)
    assert all(r["userIdentity"]["accessKeyId"] not in keys for r in noise)
    assert all(r["userIdentity"]["arn"] not in principals for r in noise)
    report = _constructed_report(case)
    report["selected_event_refs"] = [e["ref"] for e in report["evidence"]]
    metrics = score_run(case, report)
    assert metrics["relevant_event_precision"] == len(relevant) / len(case["_fixture_records"])


def test_v5_builder_reproduces_manifest_and_fixtures_without_touching_old_files(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "fixture_builder_v5_test_only", ROOT / "fixtures/build_synthetic_v5.py"
    )
    assert spec and spec.loader
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    builder.ROOT = tmp_path
    (tmp_path / "evaluation").mkdir()
    prior = tmp_path / "evaluation/cases-v4.json"
    prior.write_text("immutable prior content\n")
    original = prior.read_bytes()
    builder.build()
    generated = tmp_path / "evaluation/cases-v5.json"
    assert generated.read_bytes() == MANIFEST.read_bytes()
    for case in load_cases(generated):
        assert (tmp_path / case["fixture"]).read_bytes() == (ROOT / case["fixture"]).read_bytes()
    builder.build()
    assert prior.read_bytes() == original
    assert generated.read_bytes() == MANIFEST.read_bytes()
