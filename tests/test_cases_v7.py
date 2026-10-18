"""Frozen v7 source tests. Constructed reports are not model capability evidence."""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
from collections import defaultdict
from pathlib import Path

import pytest

from tracetrail.claims import finding_citations, validate_finding_links
from tracetrail.evaluation import load_cases
from tracetrail.facts import project_observations
from tracetrail.store import CloudTrailStore, Query
from tracetrail.support_evaluation import score_claim_support

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/cases-v7.json"
MANIFEST_SHA256 = "56c128e29c8e3588f9cd4fbac83759538db9e20143df91a54e2fb425456fc75a"
FIXTURE_HASHES = {
    "dev-role-duration-direction.json": (
        "5c99627759dc58f068947e55dd7134df51dfcaa1ad06c78f10ff26549769202b"
    ),
    "dev-kms-returned-key.json": (
        "fa10d3462917061fc3c98655eda34bf977615b50e2020e083e52e658e5de6c9e"
    ),
    "heldout-topic-label-denial.json": (
        "84d8379fca6d9cfc01e8197e5d6f2363eea34fe9e55125743dd63494e14eb756"
    ),
    "heldout-retention-removal-chain.json": (
        "b6cb113522f36b6b8399e3959ccde19a0970048da0776885bcaa28f41c3d5574"
    ),
}
MISSING = object()


@pytest.fixture(scope="module")
def cases():
    return load_cases(MANIFEST)


def _field(record, path):
    value = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def _constructed_test_report(case):
    """Build an annotation-derived unit input, never an inference result."""
    evidence = [
        {
            "ref": f"sha256:{case['fixture_sha256']}/Records/{index}",
            "event_id": record["eventID"],
            "record": copy.deepcopy(record),
        }
        for index, record in enumerate(case["_fixture_records"])
    ]
    refs = {item["event_id"]: item["ref"] for item in evidence}
    hypotheses = {item["claim_id"]: item for item in case["hypotheses"]}
    selected = [refs[event_id] for event_id in case["relevant_event_ids"]]
    findings = []
    for annotation in case["annotations"]:
        fields = defaultdict(list)
        for atom in annotation["required_observations"]:
            if atom["field"] not in fields[refs[atom["event_id"]]]:
                fields[refs[atom["event_id"]]].append(atom["field"])
        role = {"supported": "supports", "refuted": "contradicts", "uncertain": "context"}[
            annotation["expected_status"]
        ]
        links = [
            {"citation": ref, "fields": paths[start : start + 6], "role": role}
            for ref, paths in fields.items()
            for start in range(0, len(paths), 6)
        ]
        finding = {
            **hypotheses[annotation["claim_id"]],
            "status": annotation["expected_status"],
            "evidence_links": links,
            "rationale": "Constructed test-only annotation support, not model output.",
            "missing_evidence": ["Independent evidence needed to resolve this test proposition."]
            if annotation["expected_status"] == "uncertain"
            else [],
        }
        finding["citations"] = finding_citations(finding)
        findings.append(finding)
    return {
        "status": "completed",
        "test_only": True,
        "findings": findings,
        "observations": project_observations(evidence, selected),
        "evidence": evidence,
        "selected_event_refs": selected,
        "tool_history": [
            {
                "name": "query_events",
                "args": {},
                "result": {"records": copy.deepcopy(evidence)},
            }
        ],
        "query_count": 1,
        "model_calls": 0,
        "duration_seconds": 0,
        "failures": [],
    }


def test_frozen_catalog_hashes_splits_and_provenance(cases):
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_SHA256
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["suite_id"] == "tracetrail-synthetic-v7"
    assert "Entirely invented" in manifest["data_origin"]
    assert "no private data" in manifest["data_origin"]
    assert manifest["fixture_license"] == "MIT (same as repository)"
    assert "before the first fresh model inference" in manifest["freeze_policy"]
    assert "Keep these original labels after future exposure" in manifest["split_policy"]
    assert [case["split"] for case in cases] == ["development", "development", "heldout", "heldout"]
    assert len({case["id"] for case in cases}) == 4
    assert sum(len(case["_fixture_records"]) for case in cases) == 20
    assert sum(len(case["relevant_event_ids"]) for case in cases) == 15
    assert sum(len(case["hypotheses"]) for case in cases) == 16
    assert (
        sum(
            len(annotation["required_observations"])
            for case in cases
            for annotation in case["annotations"]
        )
        == 51
    )
    assert {Path(case["fixture"]).name for case in cases} == set(FIXTURE_HASHES)
    for case in cases:
        source = Path(case["_fixture_path"])
        assert source.parent == ROOT / "fixtures/v7"
        expected = FIXTURE_HASHES[source.name]
        assert case["fixture_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest() == expected
        assert case["_manifest_sha256"] == MANIFEST_SHA256
        assert case["_suite_id"] == manifest["suite_id"]
        assert len(case["hypotheses"]) == len(case["annotations"]) == 4


def test_required_atoms_resolve_to_exact_typed_source_values(cases):
    for case in cases:
        records = {record["eventID"]: record for record in case["_fixture_records"]}
        assert case["seed_event_id"] in records
        relevant = set(case["relevant_event_ids"])
        assert relevant <= records.keys()
        assert {a["claim_id"] for a in case["annotations"]} == {
            h["claim_id"] for h in case["hypotheses"]
        }
        for annotation in case["annotations"]:
            required_ids = set(annotation["required_event_ids"])
            assert required_ids <= relevant
            assert annotation["expected_status"] in {"supported", "refuted", "uncertain"}
            atoms = annotation["required_observations"]
            assert {atom["event_id"] for atom in atoms} == required_ids
            for atom in atoms:
                present = atom.get("present", True)
                assert type(present) is bool
                actual = _field(records[atom["event_id"]], atom["field"])
                if present:
                    assert actual is not MISSING
                    assert type(actual) is type(atom["value"])
                    assert actual == atom["value"]
                else:
                    assert actual is MISSING and atom["value"] is None


def test_source_identifiers_are_invented_and_addresses_are_documentation_only(cases):
    networks = [
        ipaddress.ip_network(network)
        for network in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
    ]
    for case in cases:
        source = json.dumps(case["_fixture_records"])
        assert "secretAccessKey" not in source and "sessionToken" not in source
        for record in case["_fixture_records"]:
            identity = record["userIdentity"]
            assert record["recipientAccountId"] == identity["accountId"] == "000000000000"
            assert record["eventID"].startswith("70000000-")
            assert "TraceTrail-synthetic-v7-fixture" in record["userAgent"]
            assert "SYNTHETICV7" in identity["accessKeyId"]
            assert record["eventTime"].endswith("Z")
            address = ipaddress.ip_address(record["sourceIPAddress"])
            assert any(address in network for network in networks)


@pytest.mark.parametrize("case_index", range(4))
def test_constructed_explicit_links_meet_the_complete_annotation_contract(cases, case_index):
    case = cases[case_index]
    report = _constructed_test_report(case)
    assert report["test_only"] is True and report["model_calls"] == 0
    for finding in report["findings"]:
        assert len(finding["evidence_links"]) <= 6
        assert all(1 <= len(link["fields"]) <= 6 for link in finding["evidence_links"])
        assert (
            validate_finding_links(finding, report["evidence"], report["selected_event_refs"]) == []
        )
    metrics = score_claim_support(case, report)
    assert metrics["process_valid"] is True
    assert metrics["process_valid_supported_claim_rate"] == 1
    assert metrics["process_valid_required_atom_coverage"] == 1
    assert metrics["observation_projection_used_for_support"] is False


@pytest.mark.parametrize("case_index", range(4))
def test_global_projection_cannot_replace_a_missing_claim_field_link(cases, case_index):
    case = cases[case_index]
    report = _constructed_test_report(case)
    projected = copy.deepcopy(report["observations"])
    finding = report["findings"][0]
    link = next(item for item in finding["evidence_links"] if len(item["fields"]) > 1)
    removed_field = link["fields"].pop()
    assert any(
        atom["citation"] == link["citation"] and atom["field"] == removed_field
        for atom in report["observations"]
    )
    metrics = score_claim_support(case, report)
    assert report["observations"] == projected
    assert metrics["process_valid"] is True
    assert metrics["process_valid_supported_claim_count"] == 3
    assert metrics["process_valid_supported_claim_rate"] == 0.75
    assert metrics["raw_covered_atom_count"] == metrics["required_atom_count"] - 1
    assert metrics["process_valid_required_atom_coverage"] < 1
    claim = next(item for item in metrics["per_claim"] if item["claim_id"] == finding["claim_id"])
    assert claim["raw_supported"] is False
    assert claim["reasons"] == ["missing_or_wrong_claim_field_support"]


@pytest.mark.parametrize("case_index", range(4))
def test_observed_credential_pivots_reach_exact_gold_within_three_queries(cases, case_index):
    """Local tool reachability only; no assertion that a model chose this path."""
    case = cases[case_index]
    store = CloudTrailStore.load(case["_fixture_path"])
    seed = store.get(case["seed_event_id"])
    found = {seed["event_id"]}
    query_count = 0
    if seed["record"]["eventName"] == "AssumeRole":
        issuer = seed
        temporary = seed["record"]["responseElements"]["credentials"]["accessKeyId"]
    else:
        temporary = seed["record"]["userIdentity"]["accessKeyId"]
        issuers = store.query(Query(issued_access_key=temporary))["records"]
        query_count += 1
        assert len(issuers) == 1
        issuer = issuers[0]
        found.add(issuer["event_id"])
    original = issuer["record"]["userIdentity"]["accessKeyId"]
    assert original != temporary
    for observed_key in (original, temporary):
        records = store.query(Query(access_key=observed_key))["records"]
        query_count += 1
        found.update(item["event_id"] for item in records)
    assert query_count <= 3
    assert found == set(case["relevant_event_ids"])
