"""Read-only CloudTrail evidence with bounded, exact-match query tools."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class StoreError(ValueError):
    """An input or evidence lookup failed without changing any log file."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Query(BaseModel):
    """All supplied filters must match. Time bounds include both endpoints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    principal: str | None = Field(
        default=None, description="Exact userIdentity ARN, principalId, or userName."
    )
    source_ip: str | None = Field(default=None, description="Exact sourceIPAddress value.")
    event_name: str | None = Field(default=None, description="Exact CloudTrail eventName.")
    access_key: str | None = Field(default=None, description="Exact userIdentity accessKeyId.")
    session_issuer: str | None = Field(
        default=None, description="Exact sessionContext sessionIssuer ARN."
    )
    start_time: datetime | None = Field(
        default=None, description="Inclusive ISO 8601 start time with a timezone."
    )
    end_time: datetime | None = Field(
        default=None, description="Inclusive ISO 8601 end time with a timezone."
    )
    limit: int = Field(
        default=10, ge=1, le=20, strict=True, description="Maximum returned records, from 1 to 20."
    )

    @field_validator("principal", "source_ip", "event_name", "access_key", "session_issuer")
    @classmethod
    def nonempty_filter(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or len(value) > 2048):
            raise ValueError("Filters must contain 1 to 2048 characters.")
        return value

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def timestamp_input(cls, value: Any) -> Any:
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Time bounds must be ISO 8601 strings or datetime values.")
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("Time bounds must include a timezone.")
            return value.astimezone(UTC)
        return None

    @model_validator(mode="after")
    def ordered_times(self) -> Query:
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise ValueError("start_time must be at or before end_time.")
        return self


class _GetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(
        min_length=1, max_length=4096, description="Exact eventID or sha256 citation reference."
    )


def _error(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}}


def _validation_error(error: ValidationError) -> str:
    # BaseTool validation handlers return strings. Keep a JSON error contract and
    # do not echo input values, which could contain private log data.
    details = "; ".join(
        f"{'.'.join(str(part) for part in item['loc']) or 'query'}: {item['msg']}"
        for item in error.errors(include_input=False)
    )
    return json.dumps(_error("invalid_tool_input", details))


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("invalid_json", "JSON objects must not contain duplicate keys.")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise StoreError("invalid_json", "JSON must not contain NaN or Infinity values.")


def _event_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("eventTime must be a string.")
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("eventTime must include a timezone.")
    return timestamp.astimezone(UTC)


class CloudTrailStore:
    """An in-memory snapshot of local CloudTrail JSON files.

    Citations have the form ``sha256:<file digest>/Records/<zero-based index>``.
    Record outputs are copies, so a caller cannot change stored evidence.
    """

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_ref: dict[str, dict[str, Any]] = {}
        self._times: dict[str, datetime] = {}
        self._indexes: dict[str, dict[str, set[str]]] = {
            field: {}
            for field in ("principal", "source_ip", "event_name", "access_key", "session_issuer")
        }

    @property
    def records(self) -> list[dict[str, Any]]:
        return deepcopy(self._records)

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        max_bytes: int = 32 * 1024 * 1024,
        max_events: int = 50_000,
        max_record_bytes: int = 1024 * 1024,
    ) -> CloudTrailStore:
        """Load a file or a directory of JSON files within explicit budgets."""
        for name, value in (
            ("max_bytes", max_bytes),
            ("max_events", max_events),
            ("max_record_bytes", max_record_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise StoreError("invalid_budget", f"{name} must be a positive integer.")
        source = Path(path).expanduser()
        if source.is_symlink():
            raise StoreError("invalid_path", "Input paths must not be symbolic links.")
        if source.is_file():
            files = [source]
        elif source.is_dir():
            files = sorted(
                (
                    candidate
                    for candidate in source.rglob("*")
                    if candidate.is_file() and candidate.suffix.lower() == ".json"
                ),
                key=lambda candidate: candidate.relative_to(source).as_posix(),
            )
            if not files:
                raise StoreError("empty_input", "The input directory has no JSON files.")
        else:
            raise StoreError("invalid_path", "Input must be an existing file or directory.")

        store = cls()
        bytes_read = 0
        for file in files:
            if file.is_symlink():
                raise StoreError("invalid_path", "Input files must not be symbolic links.")
            try:
                with file.open("rb") as stream:
                    raw = stream.read(max_bytes - bytes_read + 1)
            except OSError as exc:
                raise StoreError("read_error", f"Cannot read {file.name}.") from exc
            bytes_read += len(raw)
            if bytes_read > max_bytes:
                raise StoreError(
                    "byte_budget_exceeded", f"Input exceeds the {max_bytes} byte budget."
                )
            digest = hashlib.sha256(raw).hexdigest()
            try:
                document = json.loads(
                    raw.decode("utf-8"),
                    object_pairs_hook=_object_without_duplicates,
                    parse_constant=_reject_constant,
                )
            except (ValueError, UnicodeDecodeError, RecursionError) as exc:
                raise StoreError("invalid_json", f"{file.name} is not valid UTF-8 JSON.") from exc
            if not isinstance(document, dict) or not isinstance(document.get("Records"), list):
                raise StoreError("invalid_cloudtrail", f"{file.name} must contain a Records array.")
            if len(store._records) + len(document["Records"]) > max_events:
                raise StoreError(
                    "event_budget_exceeded", f"Input exceeds the {max_events} event budget."
                )
            for index, record in enumerate(document["Records"]):
                location = f"{file.name}/Records/{index}"
                if not isinstance(record, dict):
                    raise StoreError("invalid_record", f"{location} must be an object.")
                for field in ("eventID", "eventName", "eventSource"):
                    if not isinstance(record.get(field), str) or not record[field].strip():
                        raise StoreError(
                            "invalid_record", f"{location} requires a nonempty {field} string."
                        )
                identity = record.get("userIdentity", {})
                if not isinstance(identity, dict):
                    raise StoreError(
                        "invalid_record", f"{location} userIdentity must be an object."
                    )
                context = identity.get("sessionContext", {})
                if not isinstance(context, dict) or not isinstance(
                    context.get("sessionIssuer", {}), dict
                ):
                    raise StoreError(
                        "invalid_record", f"{location} session identity fields must be objects."
                    )
                try:
                    timestamp = _event_time(record.get("eventTime"))
                except (ValueError, TypeError) as exc:
                    raise StoreError(
                        "invalid_record",
                        f"{location} requires an ISO 8601 eventTime with a timezone.",
                    ) from exc
                if (
                    len(
                        json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode(
                            "utf-8"
                        )
                    )
                    > max_record_bytes
                ):
                    raise StoreError(
                        "record_budget_exceeded",
                        f"{location} exceeds the {max_record_bytes} byte record budget.",
                    )
                event_id = record["eventID"]
                ref = f"sha256:{digest}/Records/{index}"
                if event_id in store._by_id:
                    raise StoreError(
                        "duplicate_event_id",
                        "Input contains duplicate eventID values; evidence would be ambiguous.",
                    )
                if event_id in store._by_ref or ref in store._by_id or event_id == ref:
                    raise StoreError(
                        "ambiguous_identifier", "An eventID conflicts with an evidence citation."
                    )
                evidence = {"ref": ref, "event_id": event_id, "record": record}
                store._records.append(evidence)
                store._by_id[event_id] = evidence
                store._by_ref[ref] = evidence
                store._times[ref] = timestamp
                pivots = {
                    "principal": [
                        identity.get(field) for field in ("arn", "principalId", "userName")
                    ],
                    "source_ip": [record.get("sourceIPAddress")],
                    "event_name": [record.get("eventName")],
                    "access_key": [identity.get("accessKeyId")],
                    "session_issuer": [context.get("sessionIssuer", {}).get("arn")],
                }
                for field, values in pivots.items():
                    for value in values:
                        if isinstance(value, str):
                            store._indexes[field].setdefault(value, set()).add(ref)
        return store

    def get(self, identifier: str) -> dict[str, Any]:
        """Resolve an eventID or a complete citation to the original record."""
        if not isinstance(identifier, str) or not identifier:
            raise StoreError("invalid_identifier", "identifier must be a nonempty string.")
        evidence = self._by_id.get(identifier) or self._by_ref.get(identifier)
        if evidence is None:
            raise StoreError("event_not_found", "No record matches this eventID or citation.")
        return deepcopy(evidence)

    def query(self, query: Query) -> dict[str, Any]:
        """Return matching evidence in time order and report any truncation."""
        if not isinstance(query, Query):
            raise StoreError("invalid_query", "query must be a validated Query object.")
        # Pydantic model_copy and model_construct can bypass field validation.
        # Enforce the bounds again at the evidence access boundary.
        try:
            query = Query.model_validate(query.model_dump())
        except ValidationError as exc:
            raise StoreError(
                "invalid_query", "Query fields must satisfy all filter limits."
            ) from exc
        candidates: set[str] | None = None
        for field, index in self._indexes.items():
            value = getattr(query, field)
            if value is not None:
                refs = index.get(value, set())
                candidates = refs.copy() if candidates is None else candidates.intersection(refs)
        if candidates is None:
            candidates = set(self._by_ref)
        matches = [
            ref
            for ref in candidates
            if (query.start_time is None or self._times[ref] >= query.start_time)
            and (query.end_time is None or self._times[ref] <= query.end_time)
        ]
        matches.sort(key=lambda ref: (self._times[ref], ref))
        return {
            "records": [deepcopy(self._by_ref[ref]) for ref in matches[: query.limit]],
            "matched": len(matches),
            "truncated": len(matches) > query.limit,
        }

    def tools(self) -> list[BaseTool]:
        """Create LangChain tools that have no AWS, shell, or write access."""

        def query_events(**kwargs: Any) -> dict[str, Any]:
            try:
                return self.query(Query.model_validate(kwargs))
            except ValidationError as exc:
                return json.loads(_validation_error(exc))
            except StoreError as exc:
                return _error(exc.code, str(exc))

        def get_event(identifier: str) -> dict[str, Any]:
            try:
                return self.get(identifier)
            except StoreError as exc:
                return _error(exc.code, str(exc))

        return [
            StructuredTool.from_function(
                func=query_events,
                name="query_events",
                description=(
                    "Query local CloudTrail evidence. All supplied filters must match exactly. "
                    "principal matches userIdentity ARN, principalId, or userName. "
                    "session_issuer matches the session issuer ARN. "
                    "Time bounds are inclusive and require a timezone. "
                    "Returns original records with citations, total matched count, "
                    "and truncation status. "
                    "Use a limit from 1 to 20. Empty results mean no match in these loaded logs."
                ),
                args_schema=Query,
                handle_validation_error=_validation_error,
            ),
            StructuredTool.from_function(
                func=get_event,
                name="get_event",
                description=(
                    "Get one exact local CloudTrail record by eventID "
                    "or a complete sha256 citation. "
                    "Returns a structured error if absent."
                ),
                args_schema=_GetInput,
                handle_validation_error=_validation_error,
            ),
        ]
