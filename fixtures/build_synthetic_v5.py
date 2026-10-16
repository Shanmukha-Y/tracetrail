"""Build four fresh invented CloudTrail cases for claim-specific evidence.

The output contains no actual account, private log, public sample, or attack.
The script writes only v5 files. It makes no model, AWS, or network calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = "000000000000"


def _id(number: int) -> str:
    return f"50000000-0000-4000-8000-{number:012d}"


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
    error: str | None = None,
    data: bool = False,
    response: dict | None = None,
) -> dict:
    record = {
        "eventVersion": "1.09",
        "userIdentity": actor,
        "eventTime": when,
        "eventSource": source,
        "eventName": name,
        "awsRegion": "us-east-1",
        "sourceIPAddress": ip,
        "userAgent": "aws-cli/2.31.0 TraceTrail-synthetic-v5-fixture",
        "requestParameters": params,
        "responseElements": response,
        "requestID": f"95000000-0000-4000-8000-{number:012d}",
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


def _annotation(claim: str, status: str, events: list[int], facts: list[dict], reason: str) -> dict:
    return {
        "claim_id": claim,
        "expected_status": status,
        "required_event_ids": [_id(n) for n in events],
        "required_observations": facts,
        "reason": reason,
    }


def _case(
    name: str,
    split: str,
    seed: int,
    relevant: list[int],
    question: str,
    hypotheses: list[tuple[str, str]],
    annotations: list[dict],
) -> dict:
    return {
        "id": name,
        "split": split,
        "seed_event_id": _id(seed),
        "fixture": f"fixtures/v5/{name}.json",
        "question": question,
        "hypotheses": [{"claim_id": claim, "statement": text} for claim, text in hypotheses],
        "relevant_event_ids": [_id(n) for n in relevant],
        "annotations": annotations,
        "notes": "Fresh invented records. Shared source IP addresses do not establish identity.",
    }


def _key_lifecycle() -> tuple[dict, list[dict]]:
    original = "AKIASYNTHETICV5D0001"
    temporary = "ASIASYNTHETICV5D0001"
    target = "AKIASYNTHETICV5T0001"
    caller = _caller("key-janitor", original)
    issued = "2026-05-11T11:00:00Z"
    child = _session("KeyLifecycle", "rotation-review-63", temporary, issued)
    records = [
        _event(
            1101,
            "2026-05-11T09:40:00Z",
            "GetCallerIdentity",
            "sts.amazonaws.com",
            caller,
            "192.0.2.71",
            read_only=True,
        ),
        _assume(1102, issued, caller, "198.51.100.72", child, "2026-05-11T12:00:00Z"),
        _event(
            1103,
            "2026-05-11T11:02:00Z",
            "UpdateAccessKey",
            "iam.amazonaws.com",
            child,
            "203.0.113.73",
            read_only=False,
            params={"userName": "batch-reader", "accessKeyId": target, "status": "Inactive"},
        ),
        _event(
            1104,
            "2026-05-11T11:04:00Z",
            "ListAccessKeys",
            "iam.amazonaws.com",
            child,
            "203.0.113.73",
            read_only=True,
            params={"userName": "batch-reader"},
        ),
        _event(
            1105,
            "2026-05-11T11:03:00Z",
            "ListAccessKeys",
            "iam.amazonaws.com",
            _caller("other-key-reader", "AKIASYNTHETICV5N0001"),
            "203.0.113.73",
            read_only=True,
            params={"userName": "batch-reader"},
        ),
    ]
    case = _case(
        "dev-key-lifecycle",
        "development",
        1102,
        [1101, 1102, 1103, 1104],
        "Investigate the role assumption, caller history, and target access-key request. "
        "Separate the requested status from later key state. Link each conclusion to "
        "its own records, rather than to another caller at the same IP address.",
        [
            (
                "original_caller_link",
                "The key-janitor key called GetCallerIdentity before the AssumeRole request.",
            ),
            (
                "returned_key_change",
                "The temporary key returned by AssumeRole was used for "
                "UpdateAccessKey on the batch-reader key with requested status Inactive.",
            ),
            (
                "activation_requested",
                "The recorded UpdateAccessKey request asked AWS to activate the target key.",
            ),
            (
                "later_key_state",
                "The target key was inactive when the later ListAccessKeys request was made.",
            ),
        ],
        [
            _annotation(
                "original_caller_link",
                "supported",
                [1101, 1102],
                [
                    _obs(1101, "eventName", "GetCallerIdentity"),
                    _obs(1102, "eventName", "AssumeRole"),
                    _obs(1101, "userIdentity.userName", "key-janitor"),
                    _obs(1102, "userIdentity.userName", "key-janitor"),
                    _obs(1101, "userIdentity.accessKeyId", original),
                    _obs(1102, "userIdentity.accessKeyId", original),
                    _obs(1101, "eventTime", "2026-05-11T09:40:00Z"),
                    _obs(1102, "eventTime", issued),
                ],
                "The same original key occurs in the earlier identity and later issuance requests.",
            ),
            _annotation(
                "returned_key_change",
                "supported",
                [1102, 1103],
                [
                    _obs(1102, "eventName", "AssumeRole"),
                    _obs(1102, "responseElements.credentials.accessKeyId", temporary),
                    _obs(1103, "userIdentity.accessKeyId", temporary),
                    _obs(1103, "eventName", "UpdateAccessKey"),
                    _obs(1103, "requestParameters.userName", "batch-reader"),
                    _obs(1103, "requestParameters.accessKeyId", target),
                    _obs(1103, "requestParameters.status", "Inactive"),
                ],
                "The returned signer key and the target access key have distinct roles.",
            ),
            _annotation(
                "activation_requested",
                "refuted",
                [1103],
                [
                    _obs(1103, "eventName", "UpdateAccessKey"),
                    _obs(1103, "requestParameters.accessKeyId", target),
                    _obs(1103, "requestParameters.status", "Inactive"),
                ],
                "Inactive directly contradicts a request to activate this key.",
            ),
            _annotation(
                "later_key_state",
                "uncertain",
                [1103, 1104],
                [
                    _obs(1103, "eventName", "UpdateAccessKey"),
                    _obs(1103, "requestParameters.accessKeyId", target),
                    _obs(1103, "requestParameters.userName", "batch-reader"),
                    _obs(1103, "requestParameters.status", "Inactive"),
                    _obs(1104, "eventName", "ListAccessKeys"),
                    _obs(1104, "requestParameters.userName", "batch-reader"),
                    _obs(1103, "eventTime", "2026-05-11T11:02:00Z"),
                    _obs(1104, "eventTime", "2026-05-11T11:04:00Z"),
                    _obs(1104, "readOnly", True),
                    _obs(1104, "responseElements", None),
                ],
                "The read-only log does not contain the access-key list or current statuses.",
            ),
        ],
    )
    return case, records


def _network_denial() -> tuple[dict, list[dict]]:
    original = "AKIASYNTHETICV5D0002"
    temporary = "ASIASYNTHETICV5D0002"
    caller = _caller("network-observer", original)
    issued = "2026-05-13T14:00:00Z"
    child = _session("NetworkInventory", "net-review-29", temporary, issued)
    group = "sg-00000000000000502"
    records = [
        _assume(1201, issued, caller, "192.0.2.81", child, "2026-05-13T15:00:00Z"),
        _event(
            1202,
            "2026-05-13T14:03:00Z",
            "DeleteSecurityGroup",
            "ec2.amazonaws.com",
            child,
            "198.51.100.82",
            read_only=False,
            params={"groupId": group},
            error="Client.UnauthorizedOperation",
        ),
        _event(
            1203,
            "2026-05-13T14:05:00Z",
            "DescribeSecurityGroups",
            "ec2.amazonaws.com",
            child,
            "198.51.100.82",
            read_only=True,
            params={},
        ),
        _event(
            1204,
            "2026-05-13T14:04:00Z",
            "DescribeSecurityGroups",
            "ec2.amazonaws.com",
            _caller("other-network-reader", "AKIASYNTHETICV5N0002"),
            "198.51.100.82",
            read_only=True,
            params={},
        ),
    ]
    case = _case(
        "dev-network-denial",
        "development",
        1202,
        [1201, 1202, 1203],
        "Investigate the denied security-group request and its credential issuer. "
        "Distinguish the API outcome from later resource state and from the actor's intent. "
        "Cite the records that establish each point.",
        [
            (
                "issued_key_link",
                "The DeleteSecurityGroup request used the temporary key "
                "returned by the earlier AssumeRole request.",
            ),
            ("deletion_succeeded", "The recorded DeleteSecurityGroup request succeeded."),
            (
                "later_group_absence",
                "The target security group was absent when the later "
                "DescribeSecurityGroups request was made.",
            ),
            ("malicious_intent", "The denied DeleteSecurityGroup request was a malicious action."),
        ],
        [
            _annotation(
                "issued_key_link",
                "supported",
                [1201, 1202],
                [
                    _obs(1201, "eventName", "AssumeRole"),
                    _obs(1201, "responseElements.credentials.accessKeyId", temporary),
                    _obs(1202, "userIdentity.accessKeyId", temporary),
                    _obs(1202, "eventName", "DeleteSecurityGroup"),
                    _obs(1201, "eventTime", issued),
                    _obs(1202, "eventTime", "2026-05-13T14:03:00Z"),
                ],
                "The returned credential links the issuer to the denied request.",
            ),
            _annotation(
                "deletion_succeeded",
                "refuted",
                [1202],
                [
                    _obs(1202, "eventName", "DeleteSecurityGroup"),
                    _obs(1202, "requestParameters.groupId", group),
                    _obs(1202, "errorCode", "Client.UnauthorizedOperation"),
                ],
                "The explicit authorization error contradicts success of this request.",
            ),
            _annotation(
                "later_group_absence",
                "uncertain",
                [1202, 1203],
                [
                    _obs(1202, "eventName", "DeleteSecurityGroup"),
                    _obs(1202, "requestParameters.groupId", group),
                    _obs(1202, "errorCode", "Client.UnauthorizedOperation"),
                    _obs(1203, "eventName", "DescribeSecurityGroups"),
                    _obs(1202, "eventTime", "2026-05-13T14:03:00Z"),
                    _obs(1203, "eventTime", "2026-05-13T14:05:00Z"),
                    _obs(1203, "readOnly", True),
                    _obs(1203, "responseElements", None),
                ],
                "The denied deletion and unlogged read response "
                "do not establish later group state.",
            ),
            _annotation(
                "malicious_intent",
                "uncertain",
                [1201, 1202],
                [
                    _obs(1201, "requestParameters.roleSessionName", "net-review-29"),
                    _obs(1202, "eventName", "DeleteSecurityGroup"),
                    _obs(1202, "errorCode", "Client.UnauthorizedOperation"),
                ],
                "An API name and a denial do not establish approval, "
                "ownership, or malicious intent.",
            ),
        ],
    )
    return case, records


def _publication_denial() -> tuple[dict, list[dict]]:
    original = "AKIASYNTHETICV5H0001"
    temporary = "ASIASYNTHETICV5H0001"
    caller = _caller("artifact-job", original)
    issued = "2026-06-17T16:00:00Z"
    child = _session("ReportPublisher", "publication-check-46", temporary, issued)
    bucket = "synthetic-deliveries-v5"
    object_key = "deliveries/audit-sample.txt"
    records = [
        _event(
            1301,
            "2026-06-17T14:35:00Z",
            "GetBucketLocation",
            "s3.amazonaws.com",
            caller,
            "192.0.2.91",
            read_only=True,
            params={"bucketName": bucket},
        ),
        _assume(1302, issued, caller, "198.51.100.92", child, "2026-06-17T17:00:00Z"),
        _event(
            1303,
            "2026-06-17T16:04:00Z",
            "PutObject",
            "s3.amazonaws.com",
            child,
            "203.0.113.93",
            read_only=False,
            data=True,
            params={"bucketName": bucket, "key": object_key},
            error="AccessDenied",
        ),
        _event(
            1304,
            "2026-06-17T16:03:00Z",
            "PutObject",
            "s3.amazonaws.com",
            _caller("other-delivery-job", "AKIASYNTHETICV5N0003"),
            "203.0.113.93",
            read_only=False,
            data=True,
            params={"bucketName": bucket, "key": "deliveries/unrelated.txt"},
            error="AccessDenied",
        ),
    ]
    case = _case(
        "heldout-publication-denial",
        "heldout",
        1303,
        [1301, 1302, 1303],
        "Investigate the object upload attempt, including its temporary credential issuer "
        "and original caller context. Establish the request outcome and test whether "
        "these records establish approved report publication. Keep same-IP callers separate.",
        [
            (
                "caller_context",
                "The original artifact-job key called GetBucketLocation "
                "before the AssumeRole request.",
            ),
            (
                "upload_key_link",
                "The denied PutObject request used the temporary key "
                "returned by the earlier AssumeRole request.",
            ),
            ("upload_succeeded", "The recorded PutObject request uploaded the target object."),
            ("approved_publication", "The upload attempt was approved report publication."),
        ],
        [
            _annotation(
                "caller_context",
                "supported",
                [1301, 1302],
                [
                    _obs(1301, "eventName", "GetBucketLocation"),
                    _obs(1302, "eventName", "AssumeRole"),
                    _obs(1301, "userIdentity.userName", "artifact-job"),
                    _obs(1302, "userIdentity.userName", "artifact-job"),
                    _obs(1301, "userIdentity.accessKeyId", original),
                    _obs(1302, "userIdentity.accessKeyId", original),
                    _obs(1301, "eventTime", "2026-06-17T14:35:00Z"),
                    _obs(1302, "eventTime", issued),
                ],
                "The original caller key links the earlier bucket request to the issuer.",
            ),
            _annotation(
                "upload_key_link",
                "supported",
                [1302, 1303],
                [
                    _obs(1302, "eventName", "AssumeRole"),
                    _obs(1302, "responseElements.credentials.accessKeyId", temporary),
                    _obs(1303, "userIdentity.accessKeyId", temporary),
                    _obs(1303, "eventName", "PutObject"),
                    _obs(1303, "errorCode", "AccessDenied"),
                    _obs(1302, "eventTime", issued),
                    _obs(1303, "eventTime", "2026-06-17T16:04:00Z"),
                ],
                "The returned key joins the earlier issuer and the denied data write.",
            ),
            _annotation(
                "upload_succeeded",
                "refuted",
                [1303],
                [
                    _obs(1303, "eventName", "PutObject"),
                    _obs(1303, "errorCode", "AccessDenied"),
                    _obs(1303, "requestParameters.bucketName", bucket),
                    _obs(1303, "requestParameters.key", object_key),
                ],
                "The explicit denial contradicts completion of this upload request.",
            ),
            _annotation(
                "approved_publication",
                "uncertain",
                [1302, 1303],
                [
                    _obs(1302, "requestParameters.roleSessionName", "publication-check-46"),
                    _obs(1303, "eventName", "PutObject"),
                    _obs(1303, "errorCode", "AccessDenied"),
                ],
                "Job and session names do not establish publication approval.",
            ),
        ],
    )
    return case, records


def _encryption_state() -> tuple[dict, list[dict]]:
    original = "AKIASYNTHETICV5H0002"
    temporary = "ASIASYNTHETICV5H0002"
    caller = _caller("encryption-desk", original)
    issued = "2026-06-21T08:00:00Z"
    child = _session("EncryptionOperator", "key-review-77", temporary, issued)
    key_arn = f"arn:aws:kms:us-east-1:{ACCOUNT}:key/50000000-0000-4000-8000-000000005002"
    records = [
        _event(
            1401,
            "2026-06-21T06:45:00Z",
            "ListAliases",
            "kms.amazonaws.com",
            caller,
            "192.0.2.101",
            read_only=True,
        ),
        _assume(1402, issued, caller, "198.51.100.102", child, "2026-06-21T09:00:00Z"),
        _event(
            1403,
            "2026-06-21T08:02:00Z",
            "DisableKey",
            "kms.amazonaws.com",
            child,
            "203.0.113.103",
            read_only=False,
            params={"keyId": key_arn},
            response={"keyId": key_arn},
        ),
        _event(
            1404,
            "2026-06-21T08:03:00Z",
            "DescribeKey",
            "kms.amazonaws.com",
            child,
            "203.0.113.103",
            read_only=True,
            params={"keyId": key_arn},
        ),
        _event(
            1405,
            "2026-06-21T08:02:30Z",
            "DescribeKey",
            "kms.amazonaws.com",
            _caller("other-key-auditor", "AKIASYNTHETICV5N0004"),
            "203.0.113.103",
            read_only=True,
            params={"keyId": key_arn},
        ),
    ]
    case = _case(
        "heldout-encryption-state",
        "heldout",
        1403,
        [1401, 1402, 1403, 1404],
        "Investigate the KMS request and its credential chain. Distinguish the request "
        "from later key state and from maintenance approval. Link each explanation to "
        "its own API and identity evidence; an unlogged read response is not state evidence.",
        [
            (
                "caller_context",
                "The original encryption-desk key called ListAliases "
                "before the AssumeRole request.",
            ),
            (
                "disable_request",
                "The temporary key returned by AssumeRole made the "
                "DisableKey request for the target KMS key without a recorded API error.",
            ),
            (
                "later_disabled_state",
                "The target KMS key was disabled when the later DescribeKey request was made.",
            ),
            ("approved_maintenance", "The DisableKey request was approved key maintenance."),
        ],
        [
            _annotation(
                "caller_context",
                "supported",
                [1401, 1402],
                [
                    _obs(1401, "eventName", "ListAliases"),
                    _obs(1402, "eventName", "AssumeRole"),
                    _obs(1401, "userIdentity.userName", "encryption-desk"),
                    _obs(1402, "userIdentity.userName", "encryption-desk"),
                    _obs(1401, "userIdentity.accessKeyId", original),
                    _obs(1402, "userIdentity.accessKeyId", original),
                    _obs(1401, "eventTime", "2026-06-21T06:45:00Z"),
                    _obs(1402, "eventTime", issued),
                ],
                "The original key links the earlier KMS read to the later issuer.",
            ),
            _annotation(
                "disable_request",
                "supported",
                [1402, 1403],
                [
                    _obs(1402, "eventName", "AssumeRole"),
                    _obs(1402, "responseElements.credentials.accessKeyId", temporary),
                    _obs(1403, "userIdentity.accessKeyId", temporary),
                    _obs(1403, "eventName", "DisableKey"),
                    _obs(1403, "requestParameters.keyId", key_arn),
                    _obs(1403, "responseElements.keyId", key_arn),
                    _obs(1403, "errorCode", None, present=False),
                ],
                "The returned signer key made this API request; no API error is recorded.",
            ),
            _annotation(
                "later_disabled_state",
                "uncertain",
                [1403, 1404],
                [
                    _obs(1403, "eventName", "DisableKey"),
                    _obs(1403, "requestParameters.keyId", key_arn),
                    _obs(1404, "eventName", "DescribeKey"),
                    _obs(1404, "requestParameters.keyId", key_arn),
                    _obs(1403, "eventTime", "2026-06-21T08:02:00Z"),
                    _obs(1404, "eventTime", "2026-06-21T08:03:00Z"),
                    _obs(1404, "readOnly", True),
                    _obs(1404, "responseElements", None),
                ],
                "KMS state is eventually consistent and the read response "
                "state is not logged here.",
            ),
            _annotation(
                "approved_maintenance",
                "uncertain",
                [1402, 1403],
                [
                    _obs(1402, "requestParameters.roleSessionName", "key-review-77"),
                    _obs(1403, "eventName", "DisableKey"),
                    _obs(1403, "requestParameters.keyId", key_arn),
                ],
                "The supplied records do not include approval, actor intent, "
                "or change-policy evidence.",
            ),
        ],
    )
    return case, records


def build() -> None:
    (ROOT / "fixtures/v5").mkdir(parents=True, exist_ok=True)
    cases = []
    for case, records in (
        _key_lifecycle(),
        _network_denial(),
        _publication_denial(),
        _encryption_state(),
    ):
        payload = (json.dumps({"Records": records}, indent=2, sort_keys=True) + "\n").encode()
        (ROOT / case["fixture"]).write_bytes(payload)
        case["fixture_sha256"] = hashlib.sha256(payload).hexdigest()
        cases.append(case)
    manifest = {
        "schema_version": "1",
        "suite_id": "tracetrail-synthetic-v5",
        "data_origin": "Entirely invented fresh cases, with no real account, incident, "
        "person, private log, or redistributed public sample.",
        "fixture_license": "MIT (same as repository)",
        "freeze_policy": "Freeze reviewed manifest and fixture hashes before first inference. "
        "Preserve all old suites and results. Never edit a recorded suite in place.",
        "design_notes": "Four compact cases for claim-specific credential links, direct "
        "contradictions, absent state evidence, and uncertain approval or intent. "
        "All scalar annotations resolve to actual source fields or explicit absence.",
        "cases": cases,
    }
    (ROOT / "evaluation/cases-v5.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    build()
