# Pilot semantic review v1

This is a prospective assistant review protocol for two exposed synthetic
development cases. It adds source-based judgments beside the unchanged
mechanical scores. It does not change the agent, cases, annotations, harness,
or scorers, and does not report new inference results. The cases are already
known to the project assistants. Restricted evidence review is not a claim of
blinding, independent human validation, or fresh held-out evaluation.

## Run plan and runtime gate

The core has 20 cells: five exact model tags, two cases, and adaptive and fixed
search for each model-case pair. Use `qwen3.8:27b-q4_K_M` as the reference, plus
`gemma4:31b-it-q4_K_M`, `mistral-small3.2:24b`,
`gemma4:e2b-it-q4_K_M`, and `gemma4:12b-it-q4_K_M`.
Freeze full model digests, runtime and runner versions, prompts, schemas,
tools, context, decoding options, seed, budgets, and method order before
inference. Keep the common three-query, four-model-call, 3,200-output-token
limits. Record actual calls and tokens; fixed search can use fewer model calls.
Counterbalance method order, use sequential model loading and loopback-only
inference, and record investigation duration and whole-cell wall time
separately. If measured, record Ollama's exact per-request `load_duration` as
reported. The difference between wall time and investigation duration includes
preflight, loading, cleanup and unloading; do not call it pure loading time.

Run all ten cells on the first case before applying the gate. Let `S` be the
sum of their whole-cell wall times, including failures. Forecast 20 cells as
`2 * S`, and 40 as `4 * S`, then
add 20 percent overhead. Complete 40 cells, adding one second paired repeat
for every core cell, if `1.2 * 4 * S <= 5400` seconds and no hardware
interference occurred. Otherwise complete the core 20. Hardware interference
means recorded competing heavy work, overlapping model inference, an OS
memory-pressure warning, or observed thermal throttling during the gate cells.
Record the checks and any interference. The first ten cells remain in every analysis.
Freeze the time definition and log the gate calculation. Scores, answers,
failure rates, and reviewer preferences cannot affect extension. An interrupted
or missing first-case timing leaves the extension gate unmet.

The optional repeat gives 40 cells. Greedy, same-seed repeats describe observed
stability on this machine. They are not independent samples, extra cases, or a
measure of sampling uncertainty. Preserve every attempt and failure; do not
replace a failed cell with an undisclosed successful rerun.

## Frozen source inventory

Only the two development entries of [cases-v7.json](cases-v7.json) belong to
this pilot. The manifest SHA-256 is
`56c128e29c8e3588f9cd4fbac83759538db9e20143df91a54e2fb425456fc75a`.
Both files contain five invented records with documentation-range IP addresses
and account `000000000000`. There are seven relevant records, eight fixed
hypotheses, and 26 required atoms across the two cases. No private logs or
redistributed incident samples are used.

| Case and source | Fixture SHA-256 | Relevant zero-based `Records` indices | Other records |
| --- | --- | --- | --- |
| [dev-role-duration-direction](../fixtures/v7/dev-role-duration-direction.json) | `5c99627759dc58f068947e55dd7134df51dfcaa1ad06c78f10ff26549769202b` | 0: `GetCallerIdentity`; 1: seed `AssumeRole`; 2: `UpdateRole` | 3 and 4 use different caller credentials. |
| [dev-kms-returned-key](../fixtures/v7/dev-kms-returned-key.json) | `fa10d3462917061fc3c98655eda34bf977615b50e2020e083e52e658e5de6c9e` | 0: `ListKeys`; 1: `AssumeRole`; 2: seed `EnableKey`; 3: `DescribeKey` | 4 reads the same resource from the same address with a different credential. |

A full record citation is `sha256:<fixture hash>/Records/<index>`. Record an
exact field path and typed value with each review reason. Matching an IP,
resource, event name, or role alone does not establish the same signer.
Credential links concern the recorded key IDs, not an identified human.

## Per-claim full-source rubric

These are review criteria, not extra model input or replacements for the frozen
required-atom contracts. The table uses the zero-based indices above.

| Case and claim ID | Full-source decision | Decisive comparison and semantic limit |
| --- | --- | --- |
| Role: `caller_context` | Supported | Records 0 and 1 have equal `userIdentity.accessKeyId`; record 0 is `GetCallerIdentity`. Its earlier time and different address do not break this key match. |
| Role: `issued_child` | Supported | Record 1 `responseElements.credentials.accessKeyId` equals record 2 `userIdentity.accessKeyId`; record 2 is `UpdateRole`. Do not substitute the seed caller field for its returned credential. |
| Role: `same_caller_credential` | Refuted | Records 1 and 2 have different `userIdentity.accessKeyId` values. An original caller and a related assumed session are not the same signing key. |
| Role: `approved_duration` | Uncertain | Record 1's session name and record 2's requested `maxSessionDuration: 7200` do not establish business approval. The requested target `LedgerRunnerV7` is distinct from the signing session's role. |
| KMS: `original_history` | Supported | Records 0 and 1 have equal `userIdentity.accessKeyId`; record 0 is `ListKeys`. The returned session key is a different field in record 1. |
| KMS: `seed_uses_issuer_caller` | Refuted | Record 1's caller key differs from record 2's signer key. Record 2 uses the credential returned in record 1. |
| KMS: `later_read_key` | Supported | Records 2 and 3 are `EnableKey` and `DescribeKey` with equal signer keys. The same-address read at record 4 is a different signer and cannot establish this link. |
| KMS: `key_enabled_later` | Uncertain | Records 2 and 3 request the same key ARN, but record 3 has null `responseElements`. Record 2's affected-key ARN is not a later `KeyState` observation. |

AWS defines `userIdentity.accessKeyId` as the signing credential and distinguishes
temporary sessions from their issuing identities. See the
[identity field reference](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-user-identity.html).
`AssumeRole` retains returned credential fields despite being read-only; ordinary
read-only response fields are redacted. See
[IAM and STS logging](https://docs.aws.amazon.com/IAM/latest/UserGuide/cloudtrail-integration.html).
`UpdateRole`'s duration parameter describes the requested role setting, not
approval or the lifetime of an existing session. See
[UpdateRole](https://docs.aws.amazon.com/IAM/latest/APIReference/API_UpdateRole.html).
KMS adds the affected ARN to modern `EnableKey` logs; its
[EnableKey example](https://docs.aws.amazon.com/kms/latest/developerguide/ct-enablekey.html)
and [DescribeKey example](https://docs.aws.amazon.com/kms/latest/developerguide/ct-describekey.html)
do not supply a later enabled-state observation in these fixtures.

## Review order and review record

Use opaque run IDs where possible. Review each saved result before viewing
aggregate scores or comparing models. Keep the raw artifact hash, model and
method mapping, case, repeat, process status, and reviewer identity. Name every
review as an assistant assessment. A second assistant can check reasons, but
agreement is not independent human validation. Preserve disagreements and
their source-cited resolution rather than silently replacing a first judgment.

1. Reconstruct evidence actually returned in this run. Include the seed and
   successful tool returns; exclude unreturned pages, failed tool attempts and
   records known only from the fixture. Verify the model-visible fields from
   saved inputs when truncation or context limits could matter. Treat a saved
   raw record that the model never saw as a context-delivery gap.
2. Record a first-stage judgment from that evidence, the saved finding, its
   links, rationale and caveats. Decide whether the available evidence supports,
   contradicts, or leaves the precise proposition unresolved. Separately mark
   the finding's own cited basis as adequate, incomplete, wrong, or absent.
   Available but uncited facts cannot silently repair its declared support.
3. Lock that judgment, then inspect the complete five-record source and the
   frozen annotations. Record the full-source decision, exact additional
   evidence, and whether the gap was retrieval, context delivery, or an
   intrinsic source limit. Do not rewrite the first-stage judgment with
   hindsight. The source remains a supplied window, not all AWS activity.
4. Audit material prose assertions in rationales, missing-evidence text,
   limitations, and summaries. Compare claims about query counts, remaining
   budget, time order, absence, API outcomes, resource state, actors and causal
   links with the actual run and source. A correct status does not excuse a
   conflicting confident sentence elsewhere.

For every fixed claim, save: run ID, claim ID, emitted status or omission,
first-stage evidence decision, declared-support assessment, full-source
decision, primary outcome below, exact refs and fields, and a short reason.
Keep mechanical support, process validity and semantic review in separate
columns. A failed field-link contract alone is not a false semantic claim;
a passing contract alone is not proof of sound interpretation.

## Outcome rules

Use two axes: what the report concludes, and what evidence was available.
Do not collapse all uncertainty or all confident errors into one rate.
Record the emitted status separately from evidence availability: decisive
returned evidence, decisive supplied-only evidence, or insufficient full
source. Assign exactly one primary outcome in this order: unreviewable,
omitted, definite but contradicted by full source, definite without adequate
returned evidence, uncertain despite decisive returned evidence, uncertain
with decisive supplied-only evidence, uncertain with insufficient full source,
or a correct definite decision with decisive returned evidence. A definite
decision includes both a supported proposition and a refuted proposition.

| Review outcome | Rule |
| --- | --- |
| Decisive false claim | The report asserts a proposition or its negation that exact source facts contradict. Mark whether the contradiction was returned or only present in the full source. |
| Unsupported definite claim | The report gives a definite conclusion without adequate returned support. Distinguish a lucky full-source match from a proposition that the full source also leaves unknown. Absence of support is not proof of falsity. |
| Avoidable uncertainty | The report abstains even though decisive evidence was returned and visible. It is a reasoning or reporting gap, not missing retrieval. |
| Retrieval-limited unknown | The report properly abstains on its returned evidence, while a decisive fact exists elsewhere in the supplied source. Identify the missing record and a legal observed-field pivot; do not claim the model knew that fact. |
| Source-limited unknown | The report abstains and even the full supplied source leaves the proposition unresolved. Approval and later key state can remain unknown after every relevant record is retrieved. |
| Correct definite decision with available evidence | The conclusion matches decisive returned evidence. Assess the report's own cited basis separately; this outcome does not certify its reasoning or links. |
| Omitted claim | A report exists but has no usable answer for a fixed claim. Keep the requested claim slot and record omissions or conflicting duplicates. |
| Unreviewable report | No usable report exists. Preserve the failure and all requested claim slots; do not count it as a report with no false assertions. |

Within retrieval-limited unknown, use subtype `context_delivery` for a record
returned by a tool but not visible to the model. It belongs to decisive
supplied-only evidence in the availability axis. Use subtype `retrieval` when
the needed record was not returned at all.

Use a separate prose-error flag with exact quoted text, correction and source.
Mark it material if it changes the actor, credential, action, resource, time,
state, approval, intent, causality, or a claim about the agent's search. Mark a
minor wording defect separately. If an assertion duplicates a fixed claim,
link both entries and count one underlying material error in combined counts.
Do not let verbose output increase the denominator of requested hypotheses.

For retrieval-limited unknowns, identify whether fixed scope, exhausted budget,
untested legal scope, tool failure, or early stop explains the missing evidence.
A reachable record is not evidence the agent retrieved it. An unused query
opportunity is not itself proof that a particular search would have been chosen.
Any reviewer query is labelled a local source check, outside capability evidence.

## Reporting limits and denominators

The core requests 80 fixed-claim decisions: 20 runs times four claims.
An optional complete second repeat requests 160. Retain every slot, including
failed processes, omissions and unreviewable reports. Report semantic outcomes
from invalid but readable reports with their process status. Also show a
conditional completed-run view with its smaller denominator. Never assign
zero false claims to an unavailable report.

Show per-case paired adaptive/fixed differences, claim counts, material prose
errors, failure counts, actual query cost and wall time. Report extra material
assertions as a separate audit with an explicit emitted-assertion denominator;
keep the fixed 80 or 160 requested slots unchanged. Show each repeat and paired
agreement or disagreement, rather than pooling repeats as new cases.

There are ten model-case method pairs per repeat but only two case clusters.
Do not report generalization confidence intervals, significance tests,
intelligence rankings, parameter-size trends, or a model winner. The cases are
exposed, compact and synthetic. Results can describe observed behavior and
runtime on these exact cases, and can guide a later separately frozen study.
