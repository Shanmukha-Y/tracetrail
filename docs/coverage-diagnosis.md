# Coverage diagnosis of the saved v3 comparison

Qwen's adaptive investigations stopped before retrieving useful identity and
credential context. Fixed search retrieved more of that context, but retrieving
records did not ensure the report selected them or supplied the fields and
citations required by the frozen annotations. Neither method established a
later trail state from the maintenance API requests.

This diagnosis reviews the eight `qwen3.8:27b-q4_K_M` adaptive and fixed runs in
`local-results/comparison-v3-suite-v2.json`. It uses the corrected
[v2 manifest](../evaluation/cases-v2.json), its synthetic fixtures, and
`score_run`. Every saved Qwen score recomputed exactly. The reports are valid
under structural and observed-value validation; this is separate from passing
the stricter annotations. All existing Qwen observations match their source
records, and there are no invalid evidence records or tool execution errors.
No inference was rerun for this diagnosis.

All four cases are now exposed development material. Their historical
`development` and `heldout-*` labels remain in the frozen artifacts, but these
cases cannot provide an untouched held-out evaluation for changes informed by
this review. Every source record is invented; none represents a real incident.

## Retrieval and selection are separate gaps

"Retrieved" includes the initial seed lookup and records returned by successful
saved evidence-tool calls. Each record was checked against the frozen source.
"Selected" means the valid references in `selected_event_refs`, which also
drive the report timeline. A missed relevant record is partitioned into one
that was never retrieved, or one that was retrieved but omitted from selection.

For compact event-ID display, append the three-digit code below to
`10000000-0000-4000-8000-000000000`. For example, `001` is the full ID
`10000000-0000-4000-8000-000000000001`. The manifest contains the full IDs.

| Case | Method | Relevant selected / required | Never retrieved IDs | Retrieved but omitted IDs | Recall |
| --- | --- | --- | --- | --- | --- |
| `dev-role-pivot` | adaptive | 3 / 5 | `001`, `002` | none | 60% |
| `dev-role-pivot` | fixed | 3 / 5 | `001` | `002` | 60% |
| `dev-maintenance` | adaptive | 4 / 5 | `101` | none | 80% |
| `dev-maintenance` | fixed | 5 / 5 | none | none | 100% |
| `heldout-denied-and-missing` | adaptive | 1 / 2 | `202` | none | 50% |
| `heldout-denied-and-missing` | fixed | 2 / 2 | none | none | 100% |
| `heldout-data-access` | adaptive | 3 / 4 | `301` | none | 75% |
| `heldout-data-access` | fixed | 4 / 4 | none | none | 100% |

Across cases, adaptive selected 11 of 16 annotated relevant records: five were
never retrieved and none were retrieved then omitted. Fixed selected 14 of 16:
one was never retrieved and one was retrieved then omitted. These pooled counts
are different from the per-case mean recall, which is 66.25% for adaptive and
90% for fixed. All adaptive selections have 100% precision. Fixed maintenance
also selects the unannotated `DescribeTrails` event `102`, giving that case
83.33% precision; fixed's per-case mean precision is 95.83%.

The five distinct missed IDs resolve to these exact fixture locations:

| ID code | Synthetic fixture | Citation array index | Context |
| --- | --- | --- | --- |
| `001` | [dev-role-pivot.json](../fixtures/v2/dev-role-pivot.json) | `Records/0` | Prior-day `ListBuckets` by the same IAM key, with a different source IP |
| `002` | [dev-role-pivot.json](../fixtures/v2/dev-role-pivot.json) | `Records/1` | `GetCallerIdentity` immediately before the role assumption |
| `101` | [dev-maintenance.json](../fixtures/v2/dev-maintenance.json) | `Records/0` | `AssumeRole` issuance for the maintenance session |
| `202` | [heldout-denied-and-missing.json](../fixtures/v2/heldout-denied-and-missing.json) | `Records/1` | Denied `AssumeRole` using the seed IAM key |
| `301` | [heldout-data-access.json](../fixtures/v2/heldout-data-access.json) | `Records/0` | `AssumeRole` returning the key used by the object requests |

Full citations are `sha256:<fixture_sha256>/Records/<index>`; the manifest fixes
each fixture hash. A citation resolves supplied file bytes, not AWS authenticity
or completeness of the supplied log window.

## Why the saved searches missed context

Every Qwen adaptive run used one of the three allowed follow-up queries and
then chose `finish`, leaving two queries unused. This does not mean every run
must spend its full budget. It shows that the finish decision did not recognize
the remaining evidence paths in these records.

- Role-pivot queried only the returned temporary key. That follows its later
  actions but omits the originating IAM key's earlier activity. Fixed's one-hour
  seed window excludes the prior-day `001` record. Fixed retrieves `002`, but
  the report omits it, so widening retrieval alone would not resolve selection.
- Maintenance adaptive searches from the stop onward using the temporary key
  and role issuer. This retrieves the stop/update/start/status requests but
  excludes the earlier IAM-user issuance event `101`.
- Denied-and-missing adaptive combines the IAM key with
  `session_issuer="sts.amazonaws.com"`. The tool matches a session-issuer ARN;
  this string is an API service source. Neither relevant IAM-user record has
  that issuer. The zero-match result is a query-scope result, but the agent
  finishes and says no role-pivot event was found. The existing denied request
  is not missing from the supplied fixture.
- Data-access adaptive queries the `DataAudit` role-session issuer to look for
  the issuance. This finds assumed-role object requests, but the IAM-user
  `AssumeRole` record stores the target in `requestParameters.roleArn` and the
  issued key in `responseElements.credentials.accessKeyId`. It has no
  `sessionIssuer`. The current store only indexes the key used to sign a request,
  not the returned key, so this query cannot retrieve `301`.

## Citation, field, and status failures

The following counts are per-claim requirement atoms. A field or event required
by two claims counts twice. "Claims / atoms" gives the affected-claim count and
the number of missing requirements out of all requirements for the case.
Dimensions overlap: one finding may lack both a citation and a field and also
have the wrong status. They must not be added to estimate hallucinations.

| Case | Method | Missing citation claims / atoms | Missing field claims / atoms | Status errors | Strict annotation failures |
| --- | --- | --- | --- | --- | --- |
| role-pivot | adaptive | 3 / 5 of 9 | 3 / 4 of 11 | 0 | 4 / 6 |
| role-pivot | fixed | 3 / 5 of 9 | 3 / 4 of 11 | 0 | 4 / 6 |
| maintenance | adaptive | 2 / 4 of 9 | 2 / 2 of 12 | 1 | 4 / 5 |
| maintenance | fixed | 2 / 3 of 9 | 4 / 4 of 12 | 1 | 4 / 5 |
| denied-and-missing | adaptive | 2 / 2 of 5 | 1 / 2 of 5 | 1 | 2 / 4 |
| denied-and-missing | fixed | 0 / 0 of 5 | 0 / 0 of 5 | 0 | 0 / 4 |
| data-access | adaptive | 2 / 2 of 8 | 5 / 5 of 10 | 1 | 5 / 6 |
| data-access | fixed | 1 / 1 of 8 | 4 / 4 of 10 | 0 | 4 / 6 |

Across the eight reports, 22 of 62 citation atoms are missing, affecting 15
claim instances. Twenty-five of 76 required field atoms are omitted, affecting
22 claim instances. There are four status errors and 27 of 42 strict annotation
failures. All field failures are omissions: existing values and presence flags
are correct. No finding IDs or fixed statements are missing or mismatched.

The exact omissions explain why better retrieval is insufficient:

- In both role-pivot reports, the uncertain approval, compromise, and transfer
  findings have empty citations. Missing citation IDs are approval `003,004`,
  compromise `001,003`, and transfer `005`. Missing fields are
  `004.requestParameters.name`, `003.requestParameters.roleSessionName`, and
  `001.sourceIPAddress` and `003.sourceIPAddress`. The stop resource and later
  source IP were already available in retrieved records.
- Maintenance adaptive omits `103` from the stop/start linkage citations and
  `101,104,105` from approval citations. Its missing fields are
  `103.userIdentity.sessionContext.sessionIssuer.userName` and
  `101.requestParameters.roleSessionName`. Fixed also omits `103` from the
  linkage citations; approval cites `101` but omits `104,105`. Its missing fields
  additionally include `103.userIdentity.accessKeyId` and
  `106.responseElements`. Fixed selected every relevant record but still fails
  four of five annotations.
- Denied adaptive omits `202` from the pivot and compromise citations, and
  omits that record's `eventName` and `errorCode` observations. Fixed meets every
  annotation for this case.
- Data-access adaptive omits `301` from session-link and approval citations.
  Missing fields are `301.responseElements.credentials.accessKeyId`,
  `301.requestParameters.roleSessionName`, `304.eventName`, and `302.eventName`
  required by two claims. Fixed supplies the returned key but omits the other
  four field atoms; its approval finding also omits the already-selected `302`
  citation.

Both maintenance reports mark `persistent_disruption` as **refuted** where the
v2 annotation expects **uncertain**. They have the `GetTrailStatus` record with
null `responseElements` and infer later logging state from the earlier
`StartLogging` request without a recorded API error. The supplied records do
not establish that state. Adaptive denied-and-missing marks `pivot_succeeded`
uncertain instead of refuted, and adaptive data-access marks `session_link`
uncertain instead of supported; both depend on the unretrieved records above.
See [CloudTrail evidence semantics](cloudtrail.md).

The scorer verifies fixed statements, annotated status, provenance, and exact
field observations. It does not judge planner reasons or free-text limitations.
For example, the adaptive role-pivot finish reason calls stopping logging
before a read "inconsistent with routine maintenance," despite having no
approval context. Such language needs human review even when the corresponding
fixed finding remains uncertain. Strict annotation failure is not a count of
proven semantic hallucinations.

## General fixes to test next

These are implementation hypotheses, not validated improvements:

1. Track searched scope, retrieved records, selected records, and unresolved
   evidence paths separately. A finish decision should explain why additional
   bounded queries have little value. Zero matches, a restrictive filter, or a
   truncated result must not be treated as evidence that a record is absent
   from the entire supplied corpus.
2. Support credential links in both directions: the key used to sign a request,
   the key returned by an issuance event, the target role, and the later
   assumed-role issuer are different fields. Query descriptions and input
   checks should keep those meanings distinct. Use observed identities and
   bounded context searches rather than fixture-specific event sequences.
3. Make temporal coverage explicit, including lookback limits and remaining
   uncertainty outside the searched window. Allow a justified expansion within
   the same budget rather than assuming a fixed one-hour window is sufficient.
4. Preserve relevant retrieved context in the report, with an explanation for
   omissions. Extract chosen atomic field values directly from cited records
   and connect each finding to its evidence; valid JSON and correct values
   alone do not prove complete support. Runtime logic must not receive gold
   relevant-event IDs, annotation requirements, or expected status labels.
5. Review claim status against the kind of evidence actually present. A
   request, a denied request, returned credentials, and a returned state value
   support different conclusions. Keep intent, approval, and unobserved later
   state uncertain; review free-text rationales separately from fixed findings.
6. Preserve this comparison and version future prompts or tools. Author new
   independent cases before another release-quality evaluation, compare
   adaptive and fixed methods under frozen shared budgets, and repeat runs to
   measure variation. All current cases remain regression data, not fresh
   held-out evidence.

## Reproduction fingerprints

The reviewed source checkout was `af6536b1329fa719c46a8f030e7e3518e157a3b9`.
The saved protocol is `tracetrail-v3`, suite `tracetrail-synthetic-v2`, with
temperature 0, seed 42, three follow-up queries, and 2,400 output tokens per
model call. Raw reports and traces stay in the ignored local results directory.

- Raw comparison SHA-256:
  `2ddeddc0ccfa5bfed5808272e9b0a47c1f70b3384d7f5d4bbc20b7aa3f2c7d27`
- Manifest SHA-256:
  `c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446`
- Prompt SHA-256:
  `130be495ef3ec09a4188db8e7c7e29d173003b70ce677b335cb25e4c1451683a`

This small, single-run synthetic comparison diagnoses concrete failures. It
does not establish a model winner, a reliable investigation success rate, or
release readiness.
