"""Check model-authored evidence links, without judging or repairing claims."""

from __future__ import annotations

_ABSENCE_FIELDS = frozenset({"errorCode", "errorMessage", "requestParameters", "responseElements"})
_ROLES = frozenset({"supports", "contradicts", "context"})


def finding_citations(finding: dict) -> list[str]:
    """Return exactly the string references chosen in links, deduplicated in order.

    Unknown and otherwise invalid string references remain visible. Validation
    is separate; this function never substitutes or selects evidence records.
    """
    if not isinstance(finding, dict) or not isinstance(finding.get("evidence_links"), list):
        return []
    citations = []
    seen = set()
    for link in finding["evidence_links"]:
        if not isinstance(link, dict) or not isinstance(link.get("citation"), str):
            continue
        citation = link["citation"]
        if citation not in seen:
            citations.append(citation)
            seen.add(citation)
    return citations


def _resolves(record: dict, field: str) -> bool:
    value = record
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return field in _ABSENCE_FIELDS and field not in record
        value = value[part]
    return True


def validate_finding_links(
    finding: dict, evidence: list[dict], selected_refs: list[str]
) -> list[dict]:
    """Check bounded link structure and source presence, not semantic support.

    A declared supporting or contradicting role is a model judgment. Resolving
    its field paths does not establish that the evidence entails the statement.
    This function returns only errors and never changes the supplied finding.
    """
    if not isinstance(finding, dict):
        return [{"code": "invalid_finding", "claim_id": None}]
    claim_id = finding.get("claim_id")
    claim_id = claim_id if isinstance(claim_id, str) else None
    errors = []

    def error(code: str, *, citation: str | None = None, field: str | None = None) -> None:
        item = {"code": code, "claim_id": claim_id}
        if citation is not None:
            item["citation"] = citation
        if field is not None:
            item["field"] = field
        errors.append(item)

    rationale = finding.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 600:
        error("invalid_finding_rationale")

    missing = finding.get("missing_evidence")
    valid_missing = False
    if not isinstance(missing, list) or len(missing) > 4:
        error("invalid_missing_evidence")
    if isinstance(missing, list):
        for entry in missing[:4]:
            if not isinstance(entry, str) or not entry.strip() or len(entry) > 300:
                error("invalid_missing_evidence_entry")
            else:
                valid_missing = True
    status = finding.get("status")
    if status not in ("supported", "refuted", "uncertain"):
        error("invalid_finding_status")
    elif status == "uncertain" and not valid_missing:
        error("missing_uncertainty")

    records = {}
    duplicate_refs = set()
    if not isinstance(evidence, list):
        error("invalid_evidence")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("ref"), str):
                error("invalid_evidence")
                continue
            ref = item["ref"]
            if ref in records:
                duplicate_refs.add(ref)
            records[ref] = item.get("record")
    if not isinstance(selected_refs, list):
        error("invalid_selected_references")
        selected = set()
    else:
        selected = {ref for ref in selected_refs if isinstance(ref, str)}

    links = finding.get("evidence_links")
    if not isinstance(links, list) or len(links) > 6:
        error("invalid_evidence_links")
    roles = set()
    seen_links = set()
    for link in links[:6] if isinstance(links, list) else []:
        if not isinstance(link, dict):
            error("invalid_evidence_link")
            continue
        citation = link.get("citation")
        valid_citation = isinstance(citation, str) and bool(citation.strip())
        identifier = citation if isinstance(citation, str) else None
        record = None
        if not valid_citation:
            error("invalid_evidence_link_citation")
        elif citation not in records:
            error("unknown_evidence_link_citation", citation=citation)
        elif citation in duplicate_refs:
            error("ambiguous_evidence_link_citation", citation=citation)
        elif citation not in selected:
            error("unselected_evidence_link_citation", citation=citation)
        elif not isinstance(records[citation], dict):
            error("invalid_evidence_link_record", citation=citation)
        else:
            record = records[citation]

        role = link.get("role")
        if not isinstance(role, str) or role not in _ROLES:
            error("invalid_evidence_link_role", citation=identifier)
        else:
            roles.add(role)
        fields = link.get("fields")
        if not isinstance(fields, list) or not 1 <= len(fields) <= 6:
            error("invalid_evidence_link_fields", citation=identifier)
        valid_fields = []
        seen_fields = set()
        for field in fields[:6] if isinstance(fields, list) else []:
            if (
                not isinstance(field, str)
                or not field.strip()
                or len(field) > 512
                or not all(field.split("."))
            ):
                error("invalid_evidence_link_field", citation=identifier)
                continue
            if field in seen_fields:
                error("duplicate_evidence_link_field", citation=identifier, field=field)
            seen_fields.add(field)
            valid_fields.append(field)
            if record is not None and not _resolves(record, field):
                error("unresolved_evidence_link_field", citation=identifier, field=field)
        if valid_citation and isinstance(role, str) and role in _ROLES and valid_fields:
            signature = (citation, role, tuple(sorted(set(valid_fields))))
            if signature in seen_links:
                error("duplicate_evidence_link", citation=identifier)
            seen_links.add(signature)
    if status == "supported" and "supports" not in roles:
        error("missing_supporting_evidence")
    if status == "refuted" and "contradicts" not in roles:
        error("missing_contradicting_evidence")
    return errors
