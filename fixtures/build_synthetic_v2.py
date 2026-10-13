"""Create corrected v2 fixtures without changing any frozen v1 artifact.

CloudTrail treats AssumeRole as read only while retaining its response fields.
An assumed session's creationDate is its credential issuance time. Ordinary
read-only events, including GetTrailStatus, do not log API response state.
This script reads only invented v1 input and writes only versioned v2 output.
It makes no AWS, model, or network calls.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V1_MANIFEST = ROOT / "evaluation/cases.json"
V1_MANIFEST_SHA256 = "2271b38c065aea28868f5b1578a2b9368ed5f82f684afb02bdf05d8b68a012e7"


def _observation(event_id: str, field: str, value: object, *, present: bool = True) -> dict:
    observation = {"event_id": event_id, "field": field, "value": value}
    if not present:
        observation["present"] = False
    return observation


def _correct_records(records: list[dict]) -> list[dict]:
    records = copy.deepcopy(records)
    issuance: dict[str, str] = {}
    earliest_session_event: dict[str, str] = {}
    for record in records:
        identity = record.get("userIdentity", {})
        if identity.get("type") == "AssumedRole":
            key = identity["accessKeyId"]
            earliest_session_event[key] = min(
                earliest_session_event.get(key, record["eventTime"]), record["eventTime"]
            )
        if record["eventName"] == "AssumeRole":
            record["readOnly"] = True
            response = record.get("responseElements")
            if "errorCode" not in record and isinstance(response, dict):
                credentials = response.get("credentials", {})
                if credentials.get("accessKeyId"):
                    issuance[credentials["accessKeyId"]] = record["eventTime"]
        if record["eventName"] == "GetTrailStatus":
            record["readOnly"] = True
            record["responseElements"] = None
    for record in records:
        identity = record.get("userIdentity", {})
        if identity.get("type") != "AssumedRole":
            continue
        key = identity["accessKeyId"]
        # An orphan's metadata is invented at its earliest observed event.
        # No extra issuance event or claim of a discovered issuance is added.
        created = issuance.get(key, earliest_session_event[key])
        identity["sessionContext"]["attributes"]["creationDate"] = created
    return records


def _correct_maintenance(case: dict) -> None:
    statements = {h["claim_id"]: h for h in case["hypotheses"]}
    annotations = {a["claim_id"]: a for a in case["annotations"]}
    statements["logging_resumed"]["statement"] = (
        "The same temporary key called StartLogging without a recorded API error."
    )
    statements["persistent_disruption"]["statement"] = (
        "The trail was still stopped at the time of the GetTrailStatus request."
    )
    stop_id = "10000000-0000-4000-8000-000000000103"
    start_id = "10000000-0000-4000-8000-000000000105"
    status_id = "10000000-0000-4000-8000-000000000106"
    key = "ASIASYNTHETICDEV0002"
    annotations["logging_resumed"].update(
        {
            "expected_status": "supported",
            "required_event_ids": [stop_id, start_id],
            "required_observations": [
                _observation(stop_id, "userIdentity.accessKeyId", key),
                _observation(start_id, "userIdentity.accessKeyId", key),
                _observation(start_id, "eventName", "StartLogging"),
                _observation(start_id, "errorCode", None, present=False),
            ],
            "reason": (
                "The same temporary key made the stop and start requests. "
                "The start record has no API error. This does not establish later trail state."
            ),
        }
    )
    annotations["persistent_disruption"].update(
        {
            "expected_status": "uncertain",
            "required_event_ids": [start_id, status_id],
            "required_observations": [
                _observation(start_id, "eventName", "StartLogging"),
                _observation(status_id, "eventName", "GetTrailStatus"),
                _observation(status_id, "responseElements", None),
            ],
            "reason": (
                "The read-only GetTrailStatus event records the request and no response "
                "state. These requests do not establish whether the trail was still stopped."
            ),
        }
    )
    case["notes"] = (
        "Maintenance-shaped API sequence with no change-ticket evidence. "
        "GetTrailStatus has responseElements null, so no API response state is available."
    )


def build() -> None:
    v1_bytes = V1_MANIFEST.read_bytes()
    if hashlib.sha256(v1_bytes).hexdigest() != V1_MANIFEST_SHA256:
        raise ValueError("Frozen v1 manifest hash mismatch; v2 was not generated")
    manifest = copy.deepcopy(json.loads(v1_bytes))
    output_dir = ROOT / "fixtures/v2"
    output_dir.mkdir(parents=True, exist_ok=True)
    for case in manifest["cases"]:
        original_path = ROOT / case["fixture"]
        original_bytes = original_path.read_bytes()
        if hashlib.sha256(original_bytes).hexdigest() != case["fixture_sha256"]:
            raise ValueError(f"Frozen v1 fixture hash mismatch for {case['id']}")
        records = _correct_records(json.loads(original_bytes)["Records"])
        if case["id"] == "dev-maintenance":
            _correct_maintenance(case)
        payload = (json.dumps({"Records": records}, indent=2, sort_keys=True) + "\n").encode()
        destination = output_dir / original_path.name
        destination.write_bytes(payload)
        case["fixture"] = destination.relative_to(ROOT).as_posix()
        case["fixture_sha256"] = hashlib.sha256(payload).hexdigest()
    manifest["suite_id"] = "tracetrail-synthetic-v2"
    manifest["predecessor"] = {
        "suite_id": "tracetrail-synthetic-v1",
        "manifest": "evaluation/cases.json",
        "manifest_sha256": V1_MANIFEST_SHA256,
    }
    manifest["corrections"] = [
        "AssumeRole readOnly is true, including denied requests. Its response fields remain.",
        "Session creationDate matches successful AssumeRole credential issuance when supplied.",
        (
            "The orphan BackupRead session uses its earliest synthetic event time as "
            "creationDate. No issuance event is invented."
        ),
        (
            "GetTrailStatus responseElements is null. The revised claims describe "
            "StartLogging activity and keep later trail state uncertain."
        ),
    ]
    destination = ROOT / "evaluation/cases-v2.json"
    destination.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
