"""Build fresh native-format synthetic CloudTrail cases for temporal joins.

All eventTime and credential issuance dates use UTC. The development sequence
crosses midnight. Offset-aware query-bound tests are separate from raw logs.
This script writes only v4 outputs and makes no model, AWS, or network calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "000000000000"


def _id(number: int) -> str:
    return f"40000000-0000-4000-8000-{number:012d}"


def _caller(name: str, key: str) -> dict:
    return {
        "type": "IAMUser",
        "principalId": "AIDA" + hashlib.sha256(name.encode()).hexdigest()[:17].upper(),
        "arn": f"arn:aws:iam::{ACCOUNT}:user/{name}",
        "accountId": ACCOUNT,
        "accessKeyId": key,
        "userName": name,
    }


def _session(role: str, name: str, key: str, issued: str) -> dict:
    role_id = "AROA" + hashlib.sha256(role.encode()).hexdigest()[:17].upper()
    return {
        "type": "AssumedRole",
        "principalId": f"{role_id}:{name}",
        "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/{role}/{name}",
        "accountId": ACCOUNT,
        "accessKeyId": key,
        "sessionContext": {
            "sessionIssuer": {
                "type": "Role",
                "principalId": role_id,
                "arn": f"arn:aws:iam::{ACCOUNT}:role/{role}",
                "accountId": ACCOUNT,
                "userName": role,
            },
            "attributes": {"creationDate": issued, "mfaAuthenticated": "false"},
        },
    }


def _event(
    number: int,
    when: str,
    name: str,
    source: str,
    actor: dict,
    ip: str,
    *,
    read_only: bool,
    params: dict | None = None,
    response: dict | None = None,
    error: str | None = None,
    data: bool = False,
) -> dict:
    record = {
        "eventVersion": "1.09",
        "userIdentity": actor,
        "eventTime": when,
        "eventSource": source,
        "eventName": name,
        "awsRegion": "us-east-1",
        "sourceIPAddress": ip,
        "userAgent": "aws-cli/2.31.0 TraceTrail-synthetic-v4-fixture",
        "requestParameters": params,
        "responseElements": response,
        "requestID": f"94000000-0000-4000-8000-{number:012d}",
        "eventID": _id(number),
        "readOnly": read_only,
        "eventType": "AwsApiCall",
        "managementEvent": not data,
        "recipientAccountId": ACCOUNT,
        "eventCategory": "Data" if data else "Management",
    }
    if error:
        record["errorCode"] = error
        record["errorMessage"] = "Synthetic request was denied."
    return record


def _assume(number: int, when: str, caller: dict, ip: str, child: dict, expires: str) -> dict:
    return _event(
        number,
        when,
        "AssumeRole",
        "sts.amazonaws.com",
        caller,
        ip,
        read_only=True,
        params={
            "roleArn": child["sessionContext"]["sessionIssuer"]["arn"],
            "roleSessionName": child["principalId"].split(":", 1)[1],
        },
        response={
            "credentials": {"accessKeyId": child["accessKeyId"], "expiration": expires},
            "assumedRoleUser": {"arn": child["arn"], "assumedRoleId": child["principalId"]},
        },
    )


def _obs(number: int, field: str, value: object, *, present: bool = True) -> dict:
    item = {"event_id": _id(number), "field": field, "value": value}
    if not present:
        item["present"] = False
    return item


def _annotation(
    claim: str, status: str, numbers: list[int], observations: list[dict], reason: str
) -> dict:
    return {
        "claim_id": claim,
        "expected_status": status,
        "required_event_ids": [_id(n) for n in numbers],
        "required_observations": observations,
        "reason": reason,
    }


def _development() -> tuple[dict, list[dict]]:
    key = "AKIASYNTHETICV4D0001"
    temp = "ASIASYNTHETICV4D0001"
    caller = _caller("release-auditor", key)
    issued = "2026-03-14T23:58:00Z"
    child = _session("CatalogMaintainer", "catalog-review-52", temp, issued)
    records = [
        _event(
            901,
            "2026-03-14T23:49:00Z",
            "GetCallerIdentity",
            "sts.amazonaws.com",
            caller,
            "192.0.2.64",
            read_only=True,
        ),
        _assume(902, issued, caller, "198.51.100.65", child, "2026-03-15T00:58:00Z"),
        _event(
            903,
            "2026-03-15T00:01:00Z",
            "UpdateRole",
            "iam.amazonaws.com",
            child,
            "203.0.113.66",
            read_only=False,
            params={"roleName": "CatalogReader", "description": ""},
        ),
        _event(
            904,
            "2026-03-15T00:03:00Z",
            "GetRole",
            "iam.amazonaws.com",
            child,
            "203.0.113.66",
            read_only=True,
            params={"roleName": "CatalogReader"},
        ),
        _event(
            905,
            "2026-03-15T00:02:00Z",
            "GetRole",
            "iam.amazonaws.com",
            _caller("routine-reader", "AKIASYNTHETICV4N0001"),
            "203.0.113.66",
            read_only=True,
            params={"roleName": "CatalogReader"},
        ),
        _event(
            906,
            "2026-03-14T23:49:30Z",
            "GetCallerIdentity",
            "sts.amazonaws.com",
            _caller("inventory-check", "AKIASYNTHETICV4N0002"),
            "192.0.2.64",
            read_only=True,
        ),
    ]
    case = {
        "id": "dev-midnight-role-change",
        "split": "development",
        "fixture": "fixtures/v4/dev-midnight-role-change.json",
        "seed_event_id": _id(902),
        "question": (
            "Investigate the caller and returned credentials of this role assumption. "
            "Establish the order of related requests across the UTC date boundary, "
            "describe the requested role change, and separate that request from later "
            "role state. Keep other callers at shared IP addresses separate."
        ),
        "hypotheses": [
            {
                "claim_id": "caller_before_issuance",
                "statement": (
                    "The original release-auditor key called GetCallerIdentity before it "
                    "called AssumeRole."
                ),
            },
            {
                "claim_id": "change_before_issuance",
                "statement": (
                    "The UpdateRole request occurred before the AssumeRole request "
                    "that issued its temporary access key."
                ),
            },
            {
                "claim_id": "empty_description_request",
                "statement": (
                    "The returned-key session requested an empty description for CatalogReader "
                    "through UpdateRole without a recorded API error."
                ),
            },
            {
                "claim_id": "later_role_state",
                "statement": (
                    "CatalogReader had an empty description when the later GetRole "
                    "request was made."
                ),
            },
        ],
        "relevant_event_ids": [_id(n) for n in (901, 902, 903, 904)],
        "annotations": [
            _annotation(
                "caller_before_issuance",
                "supported",
                [901, 902],
                [
                    _obs(901, "eventName", "GetCallerIdentity"),
                    _obs(902, "eventName", "AssumeRole"),
                    _obs(901, "userIdentity.userName", "release-auditor"),
                    _obs(902, "userIdentity.userName", "release-auditor"),
                    _obs(901, "userIdentity.accessKeyId", key),
                    _obs(902, "userIdentity.accessKeyId", key),
                    _obs(901, "eventTime", "2026-03-14T23:49:00Z"),
                    _obs(902, "eventTime", issued),
                ],
                "The same caller key occurs at 23:49Z and 23:58Z on the same UTC date.",
            ),
            _annotation(
                "change_before_issuance",
                "refuted",
                [902, 903],
                [
                    _obs(902, "eventName", "AssumeRole"),
                    _obs(903, "eventName", "UpdateRole"),
                    _obs(902, "responseElements.credentials.accessKeyId", temp),
                    _obs(903, "userIdentity.accessKeyId", temp),
                    _obs(902, "eventTime", issued),
                    _obs(903, "eventTime", "2026-03-15T00:01:00Z"),
                ],
                "The key was issued three minutes before the change, across midnight UTC.",
            ),
            _annotation(
                "empty_description_request",
                "supported",
                [902, 903],
                [
                    _obs(902, "eventName", "AssumeRole"),
                    _obs(902, "responseElements.credentials.accessKeyId", temp),
                    _obs(903, "userIdentity.accessKeyId", temp),
                    _obs(903, "eventName", "UpdateRole"),
                    _obs(903, "requestParameters.roleName", "CatalogReader"),
                    _obs(903, "requestParameters.description", ""),
                    _obs(903, "errorCode", None, present=False),
                ],
                "The log records an empty string in the change request and no API error.",
            ),
            _annotation(
                "later_role_state",
                "uncertain",
                [903, 904],
                [
                    _obs(903, "eventName", "UpdateRole"),
                    _obs(903, "requestParameters.roleName", "CatalogReader"),
                    _obs(903, "requestParameters.description", ""),
                    _obs(904, "eventName", "GetRole"),
                    _obs(904, "requestParameters.roleName", "CatalogReader"),
                    _obs(903, "eventTime", "2026-03-15T00:01:00Z"),
                    _obs(904, "eventTime", "2026-03-15T00:03:00Z"),
                    _obs(904, "readOnly", True),
                    _obs(904, "responseElements", None),
                ],
                "GetRole logs the request with a null response, not the role's returned state.",
            ),
        ],
        "notes": (
            "Fresh invented UTC cross-midnight development sequence. All raw timestamps "
            "use UTC Z; offset timestamp handling is tested through query bounds separately."
        ),
    }
    return case, records


def _heldout() -> tuple[dict, list[dict]]:
    key = "AKIASYNTHETICV4H0001"
    temp = "ASIASYNTHETICV4H0001"
    caller = _caller("archive-service", key)
    issued = "2026-04-02T20:00:00Z"
    child = _session("ArchiveReview", "retention-check-84", temp, issued)
    bucket = "synthetic-archive-v4"
    object_key = "retention/quarterly-example.parquet"
    records = [
        _event(
            1001,
            "2026-04-02T18:05:00Z",
            "GetBucketLocation",
            "s3.amazonaws.com",
            caller,
            "192.0.2.151",
            read_only=True,
            params={"bucketName": bucket},
        ),
        _assume(1002, issued, caller, "198.51.100.152", child, "2026-04-02T21:00:00Z"),
        _event(
            1003,
            "2026-04-02T20:04:00Z",
            "GetObject",
            "s3.amazonaws.com",
            child,
            "203.0.113.153",
            read_only=True,
            data=True,
            params={"bucketName": bucket, "key": object_key},
        ),
        _event(
            1004,
            "2026-04-02T20:06:00Z",
            "DeleteObject",
            "s3.amazonaws.com",
            child,
            "203.0.113.153",
            read_only=False,
            data=True,
            params={"bucketName": bucket, "key": object_key},
            error="AccessDenied",
        ),
        _event(
            1005,
            "2026-04-02T20:03:00Z",
            "GetObject",
            "s3.amazonaws.com",
            _caller("snapshot-reader", "AKIASYNTHETICV4N0003"),
            "203.0.113.153",
            read_only=True,
            data=True,
            params={"bucketName": bucket, "key": "retention/noise-example.parquet"},
        ),
        _event(
            1006,
            "2026-04-02T18:04:00Z",
            "GetBucketLocation",
            "s3.amazonaws.com",
            _caller("region-audit", "AKIASYNTHETICV4N0004"),
            "192.0.2.151",
            read_only=True,
            params={"bucketName": bucket},
        ),
    ]
    case = {
        "id": "heldout-archive-role-chain",
        "split": "heldout",
        "fixture": "fixtures/v4/heldout-archive-role-chain.json",
        "seed_event_id": _id(1003),
        "question": (
            "Investigate this archive object request. Find the issuing request and "
            "original caller context, follow the temporary key into later object activity, "
            "and test a retention-maintenance explanation. Distinguish denied requests "
            "from completed actions, and do not treat a session name as approval."
        ),
        "hypotheses": [
            {
                "claim_id": "original_caller_order",
                "statement": (
                    "The original archive-service key called GetBucketLocation before "
                    "the AssumeRole request."
                ),
            },
            {
                "claim_id": "issued_key_link",
                "statement": (
                    "The GetObject request used the temporary key issued by the earlier "
                    "AssumeRole request from a different source IP address."
                ),
            },
            {
                "claim_id": "object_deletion_succeeded",
                "statement": (
                    "The later DeleteObject request for the same object by that "
                    "temporary key succeeded."
                ),
            },
            {
                "claim_id": "approved_retention",
                "statement": (
                    "The object access and denied deletion were approved retention maintenance."
                ),
            },
        ],
        "relevant_event_ids": [_id(n) for n in (1001, 1002, 1003, 1004)],
        "annotations": [
            _annotation(
                "original_caller_order",
                "supported",
                [1001, 1002],
                [
                    _obs(1001, "eventName", "GetBucketLocation"),
                    _obs(1002, "eventName", "AssumeRole"),
                    _obs(1001, "userIdentity.userName", "archive-service"),
                    _obs(1002, "userIdentity.userName", "archive-service"),
                    _obs(1001, "userIdentity.accessKeyId", key),
                    _obs(1002, "userIdentity.accessKeyId", key),
                    _obs(1001, "eventTime", "2026-04-02T18:05:00Z"),
                    _obs(1002, "eventTime", issued),
                ],
                "The same original key appears in the earlier location "
                "and later issuance requests.",
            ),
            _annotation(
                "issued_key_link",
                "supported",
                [1002, 1003],
                [
                    _obs(1002, "eventName", "AssumeRole"),
                    _obs(1003, "eventName", "GetObject"),
                    _obs(1002, "responseElements.credentials.accessKeyId", temp),
                    _obs(1003, "userIdentity.accessKeyId", temp),
                    _obs(1002, "sourceIPAddress", "198.51.100.152"),
                    _obs(1003, "sourceIPAddress", "203.0.113.153"),
                    _obs(1002, "eventTime", issued),
                    _obs(1003, "eventTime", "2026-04-02T20:04:00Z"),
                ],
                "The exact returned key links the earlier issuance to the later data request.",
            ),
            _annotation(
                "object_deletion_succeeded",
                "refuted",
                [1003, 1004],
                [
                    _obs(1003, "eventName", "GetObject"),
                    _obs(1004, "eventName", "DeleteObject"),
                    _obs(1003, "userIdentity.accessKeyId", temp),
                    _obs(1004, "userIdentity.accessKeyId", temp),
                    _obs(1003, "requestParameters.bucketName", bucket),
                    _obs(1004, "requestParameters.bucketName", bucket),
                    _obs(1003, "requestParameters.key", object_key),
                    _obs(1004, "requestParameters.key", object_key),
                    _obs(1003, "eventTime", "2026-04-02T20:04:00Z"),
                    _obs(1004, "eventTime", "2026-04-02T20:06:00Z"),
                    _obs(1004, "errorCode", "AccessDenied"),
                ],
                "The later request for the same bucket and key was denied, not completed.",
            ),
            _annotation(
                "approved_retention",
                "uncertain",
                [1002, 1003, 1004],
                [
                    _obs(1002, "requestParameters.roleSessionName", "retention-check-84"),
                    _obs(1003, "eventName", "GetObject"),
                    _obs(1004, "eventName", "DeleteObject"),
                    _obs(1004, "errorCode", "AccessDenied"),
                ],
                "The supplied API records contain no approval or retention-policy evidence.",
            ),
        ],
        "notes": (
            "Fresh invented held-out archive sequence. Same-IP requests by other "
            "principals are distractors, not part of the credential chain."
        ),
    }
    return case, records


def build() -> None:
    (ROOT / "fixtures/v4").mkdir(parents=True, exist_ok=True)
    cases = []
    for case, records in (_development(), _heldout()):
        payload = (json.dumps({"Records": records}, indent=2, sort_keys=True) + "\n").encode()
        (ROOT / case["fixture"]).write_bytes(payload)
        case["fixture_sha256"] = hashlib.sha256(payload).hexdigest()
        cases.append(case)
    manifest = {
        "schema_version": "1",
        "suite_id": "tracetrail-synthetic-v4",
        "data_origin": (
            "Entirely invented fresh cases. No actual account, incident, person, "
            "private logs, or public attack sample is represented."
        ),
        "fixture_license": "MIT (same as repository)",
        "freeze_policy": (
            "Freeze reviewed manifest and fixture hashes before first inference. "
            "Preserve v1-v3 and all their results; none is a fresh held-out suite now. "
            "Do not edit this suite in place after recording results."
        ),
        "design_notes": (
            "Native UTC timestamps, including a development midnight boundary. "
            "Offset-aware time inputs are tested separately in local query tests. "
            "Exact scalar source fields support fixed propositions; approval and "
            "unlogged read-only response state remain uncertain."
        ),
        "cases": cases,
    }
    (ROOT / "evaluation/cases-v4.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
