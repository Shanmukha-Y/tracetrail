"""Credential-context graph regressions with constructed wire responses only."""

import json
import socket
from collections import deque
from copy import deepcopy

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

import tracetrail.agent as agent
from tracetrail.agent import ReportSelection, investigate
from tracetrail.planning import Decision
from tracetrail.store import CloudTrailStore

SIGNER = "SYNTHETIC_CONTEXT_SIGNER"
RETURNED = "SYNTHETIC_CONTEXT_RETURNED"
HIDDEN = "SYNTHETIC_CONTEXT_UNQUERIED_KEY"
CANARY = "ANNOTATION_CANARY_NOT_A_CREDENTIAL"
HYPOTHESES = [{"claim_id": "approval", "statement": "The observed activity had approval."}]


class FakeWireModel:
    """Run exact queued JSON through the production wire schemas, without inference."""

    def __init__(self, responses):
        self.responses = deque(responses)
        self.calls = []
        self.raw_responses = []

    def with_structured_output(self, schema, *, method, include_raw):
        assert method == "json_schema" and include_raw is True
        owner = self

        class Invoker:
            def invoke(self, messages, config=None):
                payload = json.loads(messages[-1].content)
                owner.calls.append({"schema": schema, "payload": payload})
                assert owner.responses, "Test-only response queue exhausted"
                queued = owner.responses.popleft()
                response = queued(payload) if callable(queued) else deepcopy(queued)
                owner.raw_responses.append(deepcopy(response))
                raw = AIMessage(content=json.dumps(response, sort_keys=True))
                try:
                    parsed = schema.model_validate(response)
                except ValidationError as exc:
                    return {"raw": raw, "parsed": None, "parsing_error": exc}
                return {"raw": raw, "parsed": parsed, "parsing_error": None}

        return Invoker()


@pytest.fixture(autouse=True)
def prohibit_inference_and_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Credential-context integration tests must remain local test doubles")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(agent, "make_model", forbidden)


def observed_store(tmp_path, monkeypatch):
    """Source includes earlier context and an unqueried, unrelated credential."""
    parent = {
        "type": "IAMUser",
        "arn": "arn:aws:iam::000000000000:user/test-only-context",
        "accessKeyId": SIGNER,
    }
    records = [
        {
            "eventID": "seed",
            "eventName": "AssumeRole",
            "eventSource": "sts.amazonaws.com",
            "eventTime": "2026-01-01T10:00:00Z",
            "sourceIPAddress": "192.0.2.10",
            "userIdentity": parent,
            "responseElements": {"credentials": {"accessKeyId": RETURNED}},
            "annotations": {"expected_status": CANARY, "required_key": HIDDEN},
        },
        {
            "eventID": "child-use",
            "eventName": "ListBuckets",
            "eventSource": "s3.amazonaws.com",
            "eventTime": "2026-01-01T10:05:00Z",
            "sourceIPAddress": "198.51.100.11",
            "userIdentity": {
                "type": "AssumedRole",
                "arn": "arn:aws:sts::000000000000:assumed-role/Context/session",
                "accessKeyId": RETURNED,
            },
            "responseElements": None,
        },
        {
            "eventID": "earlier-parent-use",
            "eventName": "ListRoles",
            "eventSource": "iam.amazonaws.com",
            "eventTime": "2026-01-01T06:00:00Z",
            "sourceIPAddress": "203.0.113.12",
            "userIdentity": deepcopy(parent),
            "responseElements": None,
        },
        {
            "eventID": "unrelated-hidden",
            "eventName": "GetCallerIdentity",
            "eventSource": "sts.amazonaws.com",
            "eventTime": "2026-01-01T10:01:00Z",
            "sourceIPAddress": "203.0.113.13",
            "userIdentity": {"type": "IAMUser", "accessKeyId": HIDDEN},
            "responseElements": None,
        },
    ]
    path = tmp_path / "credential-context-test-only.json"
    path.write_text(json.dumps({"Records": records}), encoding="utf-8")
    store = CloudTrailStore.load(path)
    queries, gets = [], []
    real_query, real_get = store.query, store.get

    def query(args):
        queries.append(args.model_dump(mode="json"))
        return real_query(args)

    def get(identifier):
        gets.append(identifier)
        return real_get(identifier)

    monkeypatch.setattr(store, "query", query)
    monkeypatch.setattr(store, "get", get)
    return store, queries, gets


def plan(payload, action, **branch):
    return {
        "ledger": [
            {
                "claim_id": "approval",
                "evidence_refs": [payload["seed"]["ref"]],
                "open_question": "Approval needs external context in this test-only response.",
                "candidate_ids": [],
                "attempt_ids": [],
            }
        ],
        "action": action,
        "rationale": "Test-only explicit action; never a measured model result.",
        "claim_id": "approval",
        "candidate_id": None,
        "continuation_id": None,
        "query": None,
        "identifier": None,
        "dispositions": [],
        **branch,
    }


def finish(payload, *, rationale="Leave any unsearched local scope open."):
    ids = payload["coverage"]["finish_accounting_ids"]
    return plan(
        payload,
        "finish",
        rationale=rationale,
        dispositions=(
            [
                {
                    "pivot_ids": ids,
                    "disposition": "deferred",
                    "reason": "Test-only deliberate deferral; no completeness claim.",
                    "attempt_ids": [],
                }
            ]
            if ids
            else []
        ),
    )


def report(payload, *, limitation="The test-only report leaves approval unknown."):
    ref = payload["seed"]["ref"]
    return {
        "findings": [
            {
                **HYPOTHESES[0],
                "evidence_links": [{"citation": ref, "fields": ["eventName"], "role": "context"}],
                "rationale": "The observed API activity does not establish business approval.",
                "missing_evidence": ["External approval evidence was not supplied."],
                "status": "uncertain",
            }
        ],
        "selected_event_refs": [ref],
        "limitations": [limitation],
    }


def run(store, responses, *, strategy="adaptive"):
    model = FakeWireModel(responses)
    result = investigate(
        store,
        "seed",
        "What does the observed evidence establish about approval?",
        deepcopy(HYPOTHESES),
        model_name="test-only:credential-context-no-inference",
        strategy=strategy,
        model=model,
    )
    assert result["test_only"] is True
    return result, model


def mapped_keys(payload):
    return {entry["key"]: entry for entry in payload["credential_map"]["keys"]}


def test_initial_map_uses_only_observed_credential_fields_and_exact_aliases(tmp_path, monkeypatch):
    store, queries, gets = observed_store(tmp_path, monkeypatch)
    result, model = run(store, [finish, report])

    assert result["status"] == "completed"
    assert queries == [] and gets == ["seed"]
    assert [c["schema"] for c in model.calls] == [Decision, ReportSelection]
    for call in model.calls:
        payload = call["payload"]
        keys = mapped_keys(payload)
        assert set(keys) == {SIGNER, RETURNED}
        assert keys[SIGNER]["signer_occurrences"] == [
            {
                "citation": "E0",
                "field": "userIdentity.accessKeyId",
                "user_identity_type": {
                    "field": "userIdentity.type",
                    "present": True,
                    "value": "IAMUser",
                },
            }
        ]
        assert keys[SIGNER]["returned_occurrences"] == []
        assert keys[RETURNED]["signer_occurrences"] == []
        assert keys[RETURNED]["returned_occurrences"] == [
            {
                "citation": "E0",
                "field": "responseElements.credentials.accessKeyId",
                "recorded_caller": {
                    "key": SIGNER,
                    "citation": "E0",
                    "field": "userIdentity.accessKeyId",
                },
            }
        ]
        encoded = json.dumps(payload["credential_map"], sort_keys=True)
        assert CANARY not in encoded and HIDDEN not in encoded
        assert "annotations" not in encoded and "expected_status" not in encoded
        assert "required_event_ids" not in encoded and "eventName" not in encoded
