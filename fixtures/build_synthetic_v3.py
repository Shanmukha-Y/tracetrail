"""Build two fresh invented cases without reading or changing v1 or v2.

The cases test original caller retrieval and temporary credential joins. They
use documented CloudTrail field behavior and contain no AWS or model calls.
Freeze their manifest and fixture hashes before the first model inference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "000000000000"


def _id(number: int) -> str:
    return f"30000000-0000-4000-8000-{number:012d}"


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
        "userAgent": "aws-cli/2.31.0 TraceTrail-synthetic-v3-fixture",
        "requestParameters": params,
        "responseElements": response,
        "requestID": f"93000000-0000-4000-8000-{number:012d}",
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


def _assume(number: int, when: str, caller: dict, ip: str, session: dict, expires: str) -> dict:
    role = session["sessionContext"]["sessionIssuer"]["arn"]
    name = session["principalId"].split(":", 1)[1]
    return _event(
        number,
        when,
        "AssumeRole",
        "sts.amazonaws.com",
        caller,
        ip,
        read_only=True,
        params={"roleArn": role, "roleSessionName": name},
        response={
            "credentials": {"accessKeyId": session["accessKeyId"], "expiration": expires},
            "assumedRoleUser": {"arn": session["arn"], "assumedRoleId": session["principalId"]},
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
    key = "AKIASYNTHETICV3D0001"
    temp = "ASIASYNTHETICV3D0001"
    caller = _caller("release-helper", key)
    issued = "2026-02-03T12:00:00Z"
    child = _session("TrailOps", "change-review-18", temp, issued)
    trail = f"arn:aws:cloudtrail:us-east-1:{ACCOUNT}:trail/synthetic-v3-main"
    records = [
        _event(
            601,
            "2026-02-03T08:30:00Z",
            "GetCallerIdentity",
            "sts.amazonaws.com",
            caller,
            "192.0.2.112",
            read_only=True,
        ),
        _assume(602, issued, caller, "198.51.100.121", child, "2026-02-03T13:00:00Z"),
        _event(
            603,
            "2026-02-03T12:02:00Z",
            "StopLogging",
            "cloudtrail.amazonaws.com",
            child,
            "203.0.113.44",
            read_only=False,
            params={"name": trail},
        ),
        _event(
            604,
            "2026-02-03T12:03:00Z",
            "GetTrailStatus",
            "cloudtrail.amazonaws.com",
            child,
            "203.0.113.44",
            read_only=True,
            params={"name": trail},
        ),
        _event(
            605,
            "2026-02-03T12:01:00Z",
            "ListBuckets",
            "s3.amazonaws.com",
            _caller("inventory-bot", "AKIASYNTHETICV3N0001"),
            "198.51.100.121",
            read_only=True,
        ),
        _event(
            606,
            "2026-02-03T12:03:30Z",
            "GetTrailStatus",
            "cloudtrail.amazonaws.com",
            _caller("status-reader", "AKIASYNTHETICV3N0002"),
            "203.0.113.44",
            read_only=True,
            params={"name": f"arn:aws:cloudtrail:us-east-1:{ACCOUNT}:trail/synthetic-v3-other"},
        ),
    ]
    case = {
        "id": "dev-caller-and-child-pivot",
        "split": "development",
        "fixture": "fixtures/v3/dev-caller-and-child-pivot.json",
        "seed_event_id": _id(602),
        "question": (
            "Investigate the role assumption and its caller context. Follow the temporary "
            "credentials into later logging activity, compare source addresses, and test "
            "an approved-maintenance explanation without assuming trail state or intent."
        ),
        "hypotheses": [
            {
                "claim_id": "caller_source_change",
                "statement": (
                    "The same release-helper access key was used for GetCallerIdentity from "
                    "192.0.2.112 and for AssumeRole from 198.51.100.121 more than one hour later."
                ),
            },
            {
                "claim_id": "returned_key_join",
                "statement": (
                    "The temporary key returned by AssumeRole was used for the later "
                    "StopLogging request from 203.0.113.44."
                ),
            },
            {
                "claim_id": "logging_activity",
                "statement": (
                    "The returned-key session called StopLogging without a recorded API error "
                    "and later requested GetTrailStatus; that read-only event records "
                    "no trail status."
                ),
            },
            {
                "claim_id": "approved_change",
                "statement": ("The role assumption and logging change were approved maintenance."),
            },
        ],
        "relevant_event_ids": [_id(n) for n in (601, 602, 603, 604)],
        "annotations": [
            _annotation(
                "caller_source_change",
                "supported",
                [601, 602],
                [
                    _obs(601, "eventName", "GetCallerIdentity"),
                    _obs(602, "eventName", "AssumeRole"),
                    _obs(601, "userIdentity.accessKeyId", key),
                    _obs(602, "userIdentity.accessKeyId", key),
                    _obs(601, "userIdentity.userName", "release-helper"),
                    _obs(602, "userIdentity.userName", "release-helper"),
                    _obs(601, "sourceIPAddress", "192.0.2.112"),
                    _obs(602, "sourceIPAddress", "198.51.100.121"),
                    _obs(601, "eventTime", "2026-02-03T08:30:00Z"),
                    _obs(602, "eventTime", issued),
                ],
                "The exact original key occurs in both events, separated by "
                "three and a half hours.",
            ),
            _annotation(
                "returned_key_join",
                "supported",
                [602, 603],
                [
                    _obs(602, "eventName", "AssumeRole"),
                    _obs(602, "responseElements.credentials.accessKeyId", temp),
                    _obs(603, "userIdentity.accessKeyId", temp),
                    _obs(603, "eventName", "StopLogging"),
                    _obs(603, "sourceIPAddress", "203.0.113.44"),
                    _obs(602, "eventTime", issued),
                    _obs(603, "eventTime", "2026-02-03T12:02:00Z"),
                ],
                "The response key links the parent and child requests "
                "despite their different source addresses.",
            ),
            _annotation(
                "logging_activity",
                "supported",
                [602, 603, 604],
                [
                    _obs(602, "eventName", "AssumeRole"),
                    _obs(602, "responseElements.credentials.accessKeyId", temp),
                    _obs(603, "userIdentity.accessKeyId", temp),
                    _obs(604, "userIdentity.accessKeyId", temp),
                    _obs(603, "eventName", "StopLogging"),
                    _obs(603, "requestParameters.name", trail),
                    _obs(603, "errorCode", None, present=False),
                    _obs(604, "eventName", "GetTrailStatus"),
                    _obs(603, "eventTime", "2026-02-03T12:02:00Z"),
                    _obs(604, "eventTime", "2026-02-03T12:03:00Z"),
                    _obs(604, "readOnly", True),
                    _obs(604, "requestParameters.name", trail),
                    _obs(604, "responseElements", None),
                ],
                "The API activity is present; the GetTrailStatus response state is not logged.",
            ),
            _annotation(
                "approved_change",
                "uncertain",
                [602, 603],
                [
                    _obs(602, "eventName", "AssumeRole"),
                    _obs(602, "requestParameters.roleSessionName", "change-review-18"),
                    _obs(603, "eventName", "StopLogging"),
                ],
                "A session name and API sequence do not establish approval, ownership, or intent.",
            ),
        ],
        "notes": (
            "Invented development case for earlier caller and later child retrieval. "
            "The other callers share source addresses but not credentials or principals."
        ),
    }
    return case, records


def _heldout() -> tuple[dict, list[dict]]:
    key = "AKIASYNTHETICV3H0001"
    temp = "ASIASYNTHETICV3H0001"
    caller = _caller("audit-runner", key)
    issued = "2026-02-06T09:00:00Z"
    child = _session("DataInspect", "review-37", temp, issued)
    bucket = "synthetic-ledger-v3"
    records = [
        _event(
            701,
            "2026-02-06T07:45:00Z",
            "ListBuckets",
            "s3.amazonaws.com",
            caller,
            "192.0.2.211",
            read_only=True,
        ),
        _assume(702, issued, caller, "198.51.100.212", child, "2026-02-06T10:00:00Z"),
        _event(
            703,
            "2026-02-06T09:05:00Z",
            "GetObject",
            "s3.amazonaws.com",
            child,
            "203.0.113.213",
            read_only=True,
            data=True,
            params={"bucketName": bucket, "key": "exports/monthly-example.json"},
        ),
        _event(
            704,
            "2026-02-06T09:07:00Z",
            "DeleteBucket",
            "s3.amazonaws.com",
            child,
            "203.0.113.213",
            read_only=False,
            params={"bucketName": bucket},
            error="AccessDenied",
        ),
        _event(
            705,
            "2026-02-06T09:04:00Z",
            "GetObject",
            "s3.amazonaws.com",
            _caller("backup-reader", "AKIASYNTHETICV3N0003"),
            "203.0.113.213",
            read_only=True,
            data=True,
            params={"bucketName": bucket, "key": "exports/unrelated.json"},
        ),
        _event(
            706,
            "2026-02-06T07:44:00Z",
            "ListBuckets",
            "s3.amazonaws.com",
            _caller("inventory-bot", "AKIASYNTHETICV3N0004"),
            "192.0.2.211",
            read_only=True,
        ),
    ]
    case = {
        "id": "heldout-issued-key-chain",
        "split": "heldout",
        "fixture": "fixtures/v3/heldout-issued-key-chain.json",
        "seed_event_id": _id(703),
        "question": (
            "Investigate this object request. Find how its temporary credentials were "
            "issued, examine the original caller and later sensitive activity, and test "
            "whether the records establish an approved audit. Keep denied API requests "
            "separate from successful actions and do not infer intent from session names."
        ),
        "hypotheses": [
            {
                "claim_id": "issuer_join",
                "statement": (
                    "The GetObject request used the temporary key issued by the earlier "
                    "AssumeRole request, and the two requests used different source IP addresses."
                ),
            },
            {
                "claim_id": "original_caller_context",
                "statement": (
                    "The original audit-runner key appears in the earlier ListBuckets request "
                    "from 192.0.2.211 and in AssumeRole from 198.51.100.212."
                ),
            },
            {
                "claim_id": "deletion_succeeded",
                "statement": (
                    "The later DeleteBucket request by the same temporary key succeeded."
                ),
            },
            {"claim_id": "approved_audit", "statement": "The object access was an approved audit."},
        ],
        "relevant_event_ids": [_id(n) for n in (701, 702, 703, 704)],
        "annotations": [
            _annotation(
                "issuer_join",
                "supported",
                [702, 703],
                [
                    _obs(702, "eventName", "AssumeRole"),
                    _obs(703, "eventName", "GetObject"),
                    _obs(702, "responseElements.credentials.accessKeyId", temp),
                    _obs(703, "userIdentity.accessKeyId", temp),
                    _obs(702, "sourceIPAddress", "198.51.100.212"),
                    _obs(703, "sourceIPAddress", "203.0.113.213"),
                    _obs(702, "eventTime", issued),
                    _obs(703, "eventTime", "2026-02-06T09:05:00Z"),
                ],
                "The exact returned credential joins the records "
                "despite their different addresses.",
            ),
            _annotation(
                "original_caller_context",
                "supported",
                [701, 702],
                [
                    _obs(701, "eventName", "ListBuckets"),
                    _obs(702, "eventName", "AssumeRole"),
                    _obs(701, "userIdentity.accessKeyId", key),
                    _obs(702, "userIdentity.accessKeyId", key),
                    _obs(701, "userIdentity.userName", "audit-runner"),
                    _obs(702, "userIdentity.userName", "audit-runner"),
                    _obs(701, "sourceIPAddress", "192.0.2.211"),
                    _obs(702, "sourceIPAddress", "198.51.100.212"),
                    _obs(701, "eventTime", "2026-02-06T07:45:00Z"),
                    _obs(702, "eventTime", issued),
                ],
                "The same original caller key links the earlier request to the issuance request.",
            ),
            _annotation(
                "deletion_succeeded",
                "refuted",
                [703, 704],
                [
                    _obs(703, "userIdentity.accessKeyId", temp),
                    _obs(704, "userIdentity.accessKeyId", temp),
                    _obs(704, "eventName", "DeleteBucket"),
                    _obs(704, "errorCode", "AccessDenied"),
                    _obs(703, "eventTime", "2026-02-06T09:05:00Z"),
                    _obs(704, "eventTime", "2026-02-06T09:07:00Z"),
                ],
                "The logged DeleteBucket request was denied. No deletion success is established.",
            ),
            _annotation(
                "approved_audit",
                "uncertain",
                [702, 703],
                [
                    _obs(702, "requestParameters.roleSessionName", "review-37"),
                    _obs(703, "eventName", "GetObject"),
                    _obs(703, "requestParameters.key", "exports/monthly-example.json"),
                ],
                "The supplied records have no audit approval or actor-intent evidence.",
            ),
        ],
        "notes": (
            "Fresh held-out invented case. The seed uses a returned key from an issuer "
            "at a different address. Other principals produce similar API activity."
        ),
    }
    return case, records


def build() -> None:
    output_dir = ROOT / "fixtures/v3"
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = []
    for case, records in (_development(), _heldout()):
        payload = (json.dumps({"Records": records}, indent=2, sort_keys=True) + "\n").encode()
        (ROOT / case["fixture"]).write_bytes(payload)
        case["fixture_sha256"] = hashlib.sha256(payload).hexdigest()
        cases.append(case)
    manifest = {
        "schema_version": "1",
        "suite_id": "tracetrail-synthetic-v3",
        "data_origin": (
            "Entirely invented fresh cases; no AWS account, person, incident, or "
            "public sample is represented. v1 and v2 remain preserved prior suites."
        ),
        "fixture_license": "MIT (same as repository)",
        "freeze_policy": (
            "Freeze this manifest and fixture hashes before first inference. Do not edit "
            "them in place after recording results. Keep prior suites and failures."
        ),
        "design_notes": (
            "Small cases for earlier caller retrieval, returned-key child retrieval, and "
            "issued-key parent retrieval. Source changes and distractors are explicit "
            "record facts. Approval is not established by CloudTrail activity."
        ),
        "cases": cases,
    }
    (ROOT / "evaluation/cases-v3.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
