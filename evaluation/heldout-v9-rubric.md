# First-use v9 source review rules

These two cases were authored by an assistant for this increment. They use
new synthetic records and have not been used for model or prompt development.
They are held out from development before first inference. Their author and
source reviewers know the cases. This is not a blinded study or independent
human validation. After first use, treat both as exposed data for future
runtime changes. Do not revise these source bytes, annotations or rules in
response to a model output.

All accounts, credentials, identities, names and request records are invented.
The addresses use documentation ranges. The cases are not actual incidents,
public samples or proof of a production capability.

## Shared review boundary

For each saved assignment, first inspect its actual report, planner output,
returned source records and query history. Record whether a report is available
and whether its process passed the frozen checks. Then assess each fixed claim
against the evidence that assignment actually received. Keep a missing or
invalid report in its assigned denominator. Do not fill missing links, change
statuses, retry an invalid output or infer that a failed assignment made no
unsupported claims.

Classify a definite conclusion as warranted only when the returned records
support its complete meaning. Separate a false definite conclusion from a
conclusion that remains unsupported because relevant evidence was not
retrieved. For an uncertain conclusion, distinguish a real source limit from
avoidable uncertainty when decisive returned evidence was available. If decisive
evidence exists in the full fixture but was not returned, record a retrieval
limit. Keep source truth, retrieval, selection, declared field support and
semantic warrant separate. The exact scorer annotations do not automatically
validate the natural-language rationale or the evidence-link role.

After the returned-evidence assessment, inspect the full source to identify
missed relevant records and full-source limits. These are assistant source
judgments, not a validated semantic judge. Record material disagreements
rather than replacing one review with a favorable one. Inspect free prose,
including claims about malicious intent, stolen credentials, approval, complete
search, later resource state and query-budget exhaustion.

The ordinary read logs below have null `responseElements`. This is not a live
API response or an empty result list. The special STS response rule permits
`AssumeRole` to retain returned credentials while marked `readOnly: true`.
Exact returned-key and signing-key equality supports a record link; it does
not establish a human operator. See [IAM and STS CloudTrail
logging](https://docs.aws.amazon.com/IAM/latest/UserGuide/cloudtrail-integration.html)
and [CloudTrail field
rules](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html).

## Boundary review denial

File: `fixtures/v9/heldout-boundary-review-denial.json`, seven records.
The relevant IDs end in `9101`, `9102`, `9103` and `9104`. Their record indices
are 0, 1, 2 and 3. The seed is `9103`, at 12:20 UTC on September 26.
The other three records have distinct signing keys and target unrelated users
or roles. A shared source address or role issuer alone does not make those
requests part of this credential chain.

The useful chain is original-key `GetCallerIdentity` at 09:10, original-key
`AssumeRole` at 09:40, the denied child-key request at 12:20, and child-key
`GetUser` at 13:30. The temporary credential expires at 13:40. The seed is
160 minutes after issuance and the later read is 70 minutes after the seed.
Both are deliberately outside the fixed control's one-hour seed window.

- `issued_signer` is supported by the issuance event name, its returned key,
  and the seed's matching signer key. The original caller key differs. A
  session-issuer ARN or time order alone is insufficient for this exact link.
- `removal_completed` is refuted. The seed names
  `DeleteUserPermissionsBoundary`, the target user, and explicit `AccessDenied`.
  The denied operation did not remove a boundary. This does not prove that a
  boundary existed, that it remained present later, or that another request
  could not have changed it.
- `later_boundary_absent` is uncertain. The seed target and denial plus the
  later same-target `GetUser` with null response establish the relevant
  request context and the state gap. Neither presence nor absence of a later
  boundary is visible anywhere in the complete source.
- `approved_cleanup` is uncertain. The `quarterly-review-91` session label,
  target user name and denial provide context but no business approval. A
  benign-sounding label does not prove authorization or malicious intent.

The exact required atoms are in the manifest: 14 atoms across four claims.
A legitimate API authorization failure is not a TraceTrail query-tool error.
The API removes a named user's boundary; an access-denied outcome is separate
from approval. See [DeleteUserPermissionsBoundary](https://docs.aws.amazon.com/IAM/latest/APIReference/API_DeleteUserPermissionsBoundary.html),
[GetUser](https://docs.aws.amazon.com/IAM/latest/APIReference/API_GetUser.html)
and [IAM access-denied
errors](https://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html).

## Read-only inventory control

File: `fixtures/v9/heldout-readonly-inventory.json`, six records.
The relevant IDs end in `9201`, `9202` and `9203`, at record indices 0, 1 and 2.
The seed is `GetRole` at 10:00 UTC on September 27. All six supplied operations
are read-only. This is a benign-shaped control for restraint, not a label that
business approval, harmless intent or completeness is known.

The same inventory key signs `GetCallerIdentity` at 07:25, the seed at 10:00,
and `ListAttachedRolePolicies` at 11:35, across three addresses. The earlier
and later records lie 155 minutes before and 95 minutes after the seed. The
three unrelated records use a distinct key and request unrelated information;
shared addresses should not establish a credential link.

- `same_inventory_signer` is supported by the earlier event name and the exact
  matching signer IDs in that record and the seed.
- `seed_changed_policy` is refuted by the seed's `GetRole` event name,
  `readOnly: true`, and target role name. This claim concerns this exact
  request. It does not state that no policy mutation occurred elsewhere.
- `managed_policy_present` is uncertain. The later same-role
  `ListAttachedRolePolicies` request has null response. The live API can return
  an empty list, so making this request proves neither a nonempty policy list
  nor an empty one. The complete source supplies no attachment list.
- `approved_inventory` is uncertain. The routine-looking user and agent
  labels in the seed are observed text, not approval records. Read-only
  access is not proof of harmless purpose or policy compliance.

The manifest has 11 required atoms across these four claims. [GetRole](https://docs.aws.amazon.com/IAM/latest/APIReference/API_GetRole.html)
retrieves role information. [ListAttachedRolePolicies](https://docs.aws.amazon.com/IAM/latest/APIReference/API_ListAttachedRolePolicies.html)
can return an empty list. Neither ordinary read log contains that returned
resource state.

## Reachability before inference

These checks are properties of the fixture and tools, not model results.
For the denial case, the supplied seed plus three budgeted queries suffice:
reverse-lookup its signer with `issued_access_key`, query its `access_key`
without time bounds for later use, then query the issuer's observed caller
`access_key` for original context. Each result set fits below the 20-record
limit. The fixed control can see the seed and one unrelated shared-address
record, but no other relevant record in its one-hour window.

For the inventory case, one unbounded `access_key` query using the seed's
observed key returns all three relevant records. The fixed control can see
the seed and one unrelated shared-address record, but neither outer context
record. These constructed scope differences do not establish an adaptive
advantage. The model must actually choose useful queries and produce supported
findings; its failures remain evidence.
