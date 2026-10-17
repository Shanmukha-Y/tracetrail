"""Fresh v6 source and scorer tests. No inference or network calls are used."""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import re
from datetime import datetime
from pathlib import Path

import pytest

from tracetrail.evaluation import load_cases, score_run
from tracetrail.store import CloudTrailStore, Query

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/cases-v6.json"
MANIFEST_SHA256 = "e49257ef91352b7e1686bebc79bd04f61078e0da8be39651c1495aeadf702b87"
PRIOR_HASHES = {
    "cases.json": "2271b38c065aea28868f5b1578a2b9368ed5f82f684afb02bdf05d8b68a012e7",
    "cases-v2.json": "c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446",
    "cases-v3.json": "6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d",
    "cases-v4.json": "25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16",
    "cases-v5.json": "66f704a593c5d152d82f683cded4b1fa8014f58fe05f337d0bdaef615cde3e96",
}


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _constructed_report(case):
    """An annotation-derived scorer input for unit tests, not model evidence."""
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


def test_prior_manifest_and_fixture_bytes_remain_frozen():
    for name, expected in PRIOR_HASHES.items():
        payload = (ROOT / "evaluation" / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == expected
        # Inspect only manifest paths and byte hashes, not old case content.
        for case in json.loads(payload)["cases"]:
            assert (
                hashlib.sha256((ROOT / case["fixture"]).read_bytes()).hexdigest()
                == (case["fixture_sha256"])
            )


def test_catalog_is_compact_with_small_exact_claim_support_sets():
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256
    cases = load_cases(MANIFEST)
    assert [c["split"] for c in cases] == ["development", "development", "heldout", "heldout"]
    assert sum(len(c["_fixture_records"]) for c in cases) == 20
    assert sum(len(c["relevant_event_ids"]) for c in cases) == 14
    assert sum(len(a["required_observations"]) for c in cases for a in c["annotations"]) == 43
    sizes = [len(a["required_observations"]) for c in cases for a in c["annotations"]]
    assert sizes.count(4) == 3
    for case in cases:
        assert case["_suite_id"] == "tracetrail-synthetic-v6"
        assert len(case["hypotheses"]) == len(case["annotations"]) == 4
        assert 3 <= len(case["relevant_event_ids"]) <= 4
        assert len(case["_fixture_records"]) == 5
        assert len(json.dumps(case["_fixture_records"]).encode()) < 20_000
        assert all(2 <= len(a["required_observations"]) <= 4 for a in case["annotations"])
        for record in case["_fixture_records"]:
            assert record["eventID"].startswith("60000000-")
            _assert_scalar_tree(record)


@pytest.mark.parametrize("case_index", range(4))
def test_exact_source_reports_pass_the_fixed_annotation_score(case_index):
    case = load_cases(MANIFEST)[case_index]
    metrics = score_run(case, _constructed_report(case))
    assert metrics["supported_annotation_rate"] == 1
    assert metrics["status_accuracy"] == 1
    assert metrics["unsupported_claims"] == 0
    assert metrics["insufficient_evidence_handling"] == 1
    assert metrics["relevant_event_precision"] == metrics["relevant_event_recall"] == 1


@pytest.mark.parametrize("case_index", range(4))
def test_seed_alone_cannot_establish_the_caller_or_child_join(case_index):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    seed = next(e for e in report["evidence"] if e["event_id"] == case["seed_event_id"])
    report["findings"][0]["citations"] = [seed["ref"]]
    metrics = score_run(case, report)
    assert metrics["unsupported_claims"] == 1
    assert "missing_required_citation" in metrics["per_finding"][0]["reasons"]


def test_native_api_fields_dates_credential_links_and_synthetic_addresses():
    networks = [
        ipaddress.ip_network(n) for n in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
    ]
    roles = {}
    for case in load_cases(MANIFEST):
        issued = {}
        for r in case["_fixture_records"]:
            assert r["eventTime"].endswith("Z")
            assert r["recipientAccountId"] == r["userIdentity"]["accountId"] == "000000000000"
            assert any(ipaddress.ip_address(r["sourceIPAddress"]) in n for n in networks)
            assert r["managementEvent"] is True and r["eventCategory"] == "Management"
            if r["eventName"] == "AssumeRole":
                assert r["readOnly"] is True
                credentials = r["responseElements"]["credentials"]
                assert "secretAccessKey" not in credentials
                issued[credentials["accessKeyId"]] = r
            else:
                assert r["responseElements"] is None
            if r["eventName"] == "PutRetentionPolicy":
                assert r["requestParameters"]["retentionInDays"] in {7, 14}
                assert r["requestParameters"]["logGroupName"].startswith("/synthetic/v6/")
                assert r["readOnly"] is False
            if r["eventName"] == "DeleteTopic":
                assert r["errorCode"] == "AuthorizationError"
            if r["eventName"] == "UpdateUser":
                assert r["requestParameters"]["newPath"] == "/reviewed/"
            if r["eventName"] == "GetUser":
                assert r["requestParameters"]["userName"] == "synthetic-metrics-reader"
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
            roles[role["arn"]] = role["principalId"]
    assert len(roles) == len(set(roles.values())) == 4


@pytest.mark.parametrize("case_index", range(4))
def test_observed_key_queries_recover_every_relevant_event_within_three_calls(case_index):
    """Actual local tool reachability, without asserting a model chose this path."""
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


@pytest.mark.parametrize("case_index", range(4))
def test_same_key_with_seed_ip_and_filter_loses_related_records(case_index):
    case = load_cases(MANIFEST)[case_index]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])["record"]
    key = seed["userIdentity"]["accessKeyId"]
    broad = store.query(Query(access_key=key))["records"]
    narrow = store.query(Query(access_key=key, source_ip=seed["sourceIPAddress"]))["records"]
    broad_ids = {e["event_id"] for e in broad}
    narrow_ids = {e["event_id"] for e in narrow}
    assert narrow_ids < broad_ids
    assert broad_ids - narrow_ids <= set(case["relevant_event_ids"])


@pytest.mark.parametrize("case_index", range(4))
def test_same_ip_distractors_have_other_keys_and_lower_selection_precision(case_index):
    case = load_cases(MANIFEST)[case_index]
    relevant = [r for r in case["_fixture_records"] if r["eventID"] in case["relevant_event_ids"]]
    noise = [r for r in case["_fixture_records"] if r["eventID"] not in case["relevant_event_ids"]]
    keys = {r["userIdentity"]["accessKeyId"] for r in relevant}
    arns = {r["userIdentity"]["arn"] for r in relevant}
    addresses = {r["sourceIPAddress"] for r in relevant}
    assert all(r["sourceIPAddress"] in addresses for r in noise)
    assert all(r["userIdentity"]["accessKeyId"] not in keys for r in noise)
    assert all(r["userIdentity"]["arn"] not in arns for r in noise)
    report = _constructed_report(case)
    report["selected_event_refs"] = [e["ref"] for e in report["evidence"]]
    assert score_run(case, report)["relevant_event_precision"] == len(relevant) / 5


def test_denied_request_refutes_success_without_refuting_unknown_intent():
    case = load_cases(MANIFEST)[1]
    report = _constructed_report(case)
    findings = {f["claim_id"]: f for f in report["findings"]}
    assert findings["topic_deletion_succeeded"]["status"] == "refuted"
    assert findings["malicious_intent"]["status"] == "uncertain"
    findings["malicious_intent"]["status"] = "refuted"
    assert score_run(case, report)["unsupported_claims"] == 1


@pytest.mark.parametrize(
    ("case_index", "claim_id"),
    [
        (0, "approved_retention"),
        (1, "later_topic_absence"),
        (2, "later_user_path"),
        (3, "later_logging_state"),
        (3, "approved_operations"),
    ],
)
def test_request_or_null_response_cannot_prove_state_or_business_approval(case_index, claim_id):
    case = load_cases(MANIFEST)[case_index]
    report = _constructed_report(case)
    finding = next(f for f in report["findings"] if f["claim_id"] == claim_id)
    assert finding["status"] == "uncertain"
    finding["status"] = "supported"
    assert score_run(case, report)["unsupported_claims"] == 1
