# Five-model local development pilot

On October 19, 2026, TraceTrail ran 40 actual local investigations: five pinned
model deployments, two exposed synthetic development cases, adaptive and fixed
search within every model, and two paired repeats. Qwen is the reference.
The cases target credential direction, changed addresses, time scope and
source-limited conclusions. They are not fresh held-out or real incident data.
See the [frozen protocol](../evaluation/protocol-model-pilot-v1.json),
[exact deployments](model-cohort.md), [reproduction guide](model-pilot.md), and
[checked per-cell numeric results](../evaluation/results-model-pilot-v1.json).

Twenty-two processes passed structural checks; 18 remain invalid. All 40 raw
reports are readable and all 160 requested claim slots remain in the review.
The batch status is `incomplete`, while `attempted_all_target_cells` is true.
No failed assignment was replaced. The model calls, failures, exact records,
raw outputs, traces and reviews remain in private local artifacts; public
summaries bind their hashes without copying those contents.

## Process, support and cost

There were 90 original Ollama model calls and 94 read-only tool calls. Recorded
usage totals 556,936 input and 60,852 output tokens. All calls have usage and
load metadata. Accumulated investigation time was 4,047.33 seconds; accumulated
whole-cell wall time was 4,057.82 seconds, or 67.63 minutes. The difference
includes session overhead and is not pure loading time. Ollama separately
reported 161.49 seconds of summed per-request `load_duration`, already within
the investigation times. Tokenizers, runners, templates and packaged Gemma
drafting differ, so equal application controls do not isolate model size.

Every row below includes all four assigned runs for that model and method.
Primary support counts only a valid process and each finding's own exact
required links. There are six complete primary claim contracts out of 160,
and 124 covered primary atoms out of 520. A correct semantic conclusion can
still have incomplete declared support. Invalid processes earn zero primary
credit while retaining all denominators.

| Model and method | Valid processes | Selected precision / recall | Primary claim contracts | Primary atoms | Mean queries / model calls | Mean investigation / cell seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Gemma E2B adaptive | 0/4 | 100.00% / 29.17% | 0/16 | 0/52 | 0.00 / 2.00 | 15.65 / 15.90 |
| Gemma E2B fixed | 0/4 | 100.00% / 41.67% | 0/16 | 0/52 | 3.00 / 1.00 | 11.63 / 11.87 |
| Gemma 12B adaptive | 2/4 | 100.00% / 87.50% | 0/16 | 10/52 | 2.00 / 4.00 | 130.52 / 130.79 |
| Gemma 12B fixed | 4/4 | 100.00% / 41.67% | 2/16 | 20/52 | 3.00 / 1.00 | 35.05 / 35.31 |
| Qwen 27B adaptive | 4/4 | 100.00% / 87.50% | 2/16 | 32/52 | 2.00 / 4.00 | 218.89 / 219.20 |
| Qwen 27B fixed | 4/4 | 100.00% / 41.67% | 2/16 | 22/52 | 3.00 / 1.00 | 68.01 / 68.28 |
| Mistral 24B adaptive | 2/4 | 100.00% / 75.00% | 0/16 | 10/52 | 2.00 / 3.50 | 144.44 / 144.70 |
| Mistral 24B fixed | 0/4 | 0.00% / 0.00% | 0/16 | 0/52 | 3.00 / 1.00 | 44.32 / 44.58 |
| Gemma 31B adaptive | 2/4 | 100.00% / 100.00% | 0/16 | 18/52 | 2.50 / 4.00 | 278.88 / 279.15 |
| Gemma 31B fixed | 4/4 | 100.00% / 41.67% | 0/16 | 12/52 | 3.00 / 1.00 | 64.43 / 64.67 |

Selected precision and recall describe the report's selected source records,
not query-retrieval recall. Mistral fixed returned useful records but selected
unresolvable JSON pointers, so its selected-event scores are zero. Adaptive
E2B executed no query after invalid planning. Its short runtime measures a
fast failure, not efficient investigation. All 94 recorded tool results
replayed against the exact source, with no recorded tool exception. This
pilot does not empirically establish recovery from tool errors.

## Source-based claim judgments

These are source-aware assistant assessments under the
[predeclared review rules](../evaluation/pilot-semantic-review-v1.md), separate
from the mechanical scorer. Each row has 16 requested slots, including invalid
but readable reports. Warranted definite decisions exclude uncertainty; proper
abstentions are split by whether the missing evidence exists elsewhere in the
supplied source. There are no omitted or unreviewable slots in this batch.

| Model and method | Warranted definite | False definite | Unsupported definite | Avoidable uncertainty | Retrieval-limited unknown | Source-limited unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Gemma E2B adaptive | 0 | 0 | 4 | 0 | 8 | 4 |
| Gemma E2B fixed | 2 | 2 | 4 | 0 | 4 | 4 |
| Gemma 12B adaptive | 6 | 2 | 0 | 2 | 2 | 4 |
| Gemma 12B fixed | 2 | 2 | 0 | 0 | 8 | 4 |
| Qwen 27B adaptive | 8 | 2 | 0 | 0 | 2 | 4 |
| Qwen 27B fixed | 2 | 0 | 0 | 0 | 10 | 4 |
| Mistral 24B adaptive | 8 | 2 | 0 | 0 | 2 | 4 |
| Mistral 24B fixed | 2 | 0 | 0 | 0 | 10 | 4 |
| Gemma 31B adaptive | 12 | 0 | 0 | 0 | 0 | 4 |
| Gemma 31B fixed | 2 | 0 | 0 | 0 | 10 | 4 |

The totals are 44 warranted definite decisions, 10 false definite decisions,
8 unsupported definite decisions, 2 avoidable uncertainties, 56 retrieval-limited
unknowns and 40 source-limited unknowns. Do not collapse these into accuracy:
an abstention can be sound on returned evidence while the investigation still
misses a reachable record. The ten false decisions repeat the same KMS
caller-key proposition in five model/method configurations. They are not ten
independent incidents. The conditional completed-run view has 22 reports and
88 slots: 28 warranted definite, 6 false definite, 32 retrieval-limited unknown
and 22 source-limited unknown. It does not replace all-attempt results.

All three models above 20B, Gemma 12B and E2B have distinct failure profiles on
these cases. The results do not measure general intelligence or establish a
size trend or winner. Gemma 31B adaptive has the warranted credential decisions
on these two cases, but half its processes fail scope accounting and none
satisfy a complete primary claim contract. Qwen completes every process but
still makes the KMS semantic error. Parsing success, retrieval, explicit
support and sound interpretation are different properties.

## Concrete evidence checks

Record indices below are zero-based. The public numeric results retain exact
fixture hashes and per-claim record/field references. The fixture contains
invented credentials and account `000000000000`.

- **Caller versus issued credential:** Qwen adaptive marks
  `seed_uses_issuer_caller` supported even after receiving KMS records 1 and 2.
  Record 1's `userIdentity.accessKeyId` is the original AKIA key;
  `responseElements.credentials.accessKeyId` is an ASIA key. Record 2 is signed
  by that returned ASIA key. Equality to the returned key does not satisfy the
  literal proposition about the issuer event's caller key. The rationale
  reinterprets the proposition as ancestry. Its citations resolve, but its
  conclusion is false. Gemma 12B adaptive makes the same false comparison
  despite having the issuer; E2B fixed, Gemma 12B fixed and Mistral adaptive
  assert it without retrieving the issuer. See the
  [KMS source](../fixtures/v7/dev-kms-returned-key.json).
- **Lucky labels without evidence:** E2B adaptive supports role
  `caller_context` and `issued_child` on the seed alone, after zero queries.
  The complete fixture happens to support those statements, but the model
  has neither target event. Correct labels are unsupported conclusions in
  this run, rather than evidence of investigation.
- **Avoidable uncertainty:** Gemma 12B adaptive has both role signers but
  leaves `same_caller_credential` uncertain because the IDs share a suffix.
  Their actual AKIA and ASIA values differ. The returned data settles this
  signing-key comparison. See role records 1 and 2 in the
  [role source](../fixtures/v7/dev-role-duration-direction.json).
- **False search descriptions:** Qwen's role planner says
  “No remaining budget to query them.” Graph counters show two queries used
  and one remaining. Its fixed role report denies a principal search that
  actually ran. Mistral adaptive says it did not search approval records,
  although its third query attempted the narrow invented event name
  `ApprovedRoleChange`. That weak zero-result search does not establish
  approval absence, but the claim that no attempt occurred is false.
- **Returned evidence is not a tested broader filter:** Gemma 31B's role
  planner marks principal and ARN pivots tested by access-key-only queries.
  Those predicates differ. It retrieves all relevant role records, yet its
  finish accounting is invalid. Code preserves the failure and does not
  manufacture the missing searches.
- **Intrinsic source limits:** The KMS `DescribeKey` record has JSON-null
  `responseElements`. An earlier `EnableKey` affected-key ARN does not observe
  state at the later read. Role session labels and requested duration likewise
  do not establish business approval. All 40 final statuses for these
  source-limited claims remain uncertain; other prose can still overstate state.

Resolve the exact issuer record locally without model inference:

```sh
uv run tracetrail resolve fixtures/v7/dev-kms-returned-key.json \
  sha256:fa10d3462917061fc3c98655eda34bf977615b50e2020e083e52e658e5de6c9e/Records/1
```

## Paired method differences and repeat stability

The table averages the two repeat differences within each case. Positive
recall or warranted-decision differences favor adaptive on that measurement;
positive seconds mean more elapsed cell time. These are descriptive paired
values from two chosen case clusters, without intervals or significance tests.

| Model and case | Selected-recall difference, percentage points | Warranted-decision difference | Mean cell-seconds difference |
| --- | --- | --- | --- |
| Gemma E2B, role | +0.00 pp | +0 to +0 | +3.75 |
| Gemma E2B, KMS | -25.00 pp | -1 to -1 | +4.31 |
| Gemma 12B, role | +66.67 pp | +2 to +2 | +100.19 |
| Gemma 12B, KMS | +25.00 pp | +0 to +0 | +90.77 |
| Qwen 27B, role | +66.67 pp | +3 to +3 | +140.10 |
| Qwen 27B, KMS | +25.00 pp | +0 to +0 | +161.73 |
| Mistral 24B, role | +100.00 pp | +3 to +3 | +116.86 |
| Mistral 24B, KMS | +50.00 pp | +0 to +0 | +83.37 |
| Gemma 31B, role | +66.67 pp | +3 to +3 | +238.18 |
| Gemma 31B, KMS | +50.00 pp | +2 to +2 | +190.77 |

More returned or selected evidence does not guarantee better reasoning. On
KMS, several adaptive deployments add time and retrieve the issuer yet gain
no warranted definite decision over fixed search. The fixed baseline is the
same three seed-field filters within one hour of the seed on each side; it is
not an optimized search system. Both methods retain the same three-query
budget and report contract; adaptive also spends model calls on planning.

All 20 model/case/method repeat pairs have identical canonical report, planning
and query content, including raw model output. Runtime identifiers, timestamps,
trace objects and top-level failure lists are excluded from that hash;
meaningful log times and query scopes remain. A separate comparison found
identical failure lists in all 20 pairs. Requested statuses agree on 80/80 compared slots and
semantic outcomes on 80/80. This is same-seed execution stability on one Mac,
including stable failures, not independent task replication or generalization.

## Sampled memory

The Mac has 48 GiB unified memory. All 40 resource records completed, with
3,693 samples, 3,525 reporting the target model loaded, zero read errors and
no observed foreign loaded model. The table gives the range of per-run sampled
maxima over eight runs per model. GiB means bytes divided by 1,073,741,824.

| Model | Ollama reported size sampled maxima range, GiB | Ollama size_vram sampled maxima range, GiB | Process-tree RSS sampled maxima range, GiB | Runs with complete resource records |
| --- | --- | --- | --- | --- |
| Gemma E2B | 0.29 to 0.29 | 0.29 to 0.29 | 4.90 to 5.11 | 8/8 |
| Gemma 12B | 1.32 to 1.32 | 1.32 to 1.32 | 9.57 to 12.94 | 8/8 |
| Qwen 27B | 17.13 to 17.13 | 17.13 to 17.13 | 17.94 to 20.79 | 8/8 |
| Mistral 24B | 16.10 to 16.10 | 16.10 to 16.10 | 16.76 to 19.94 | 8/8 |
| Gemma 31B | 2.63 to 2.63 | 2.63 to 2.63 | 23.68 to 29.70 | 8/8 |

Ollama's `size` and `size_vram` fields are server accounting, not measured peak
VRAM or a complete memory requirement. In this setup the Gemma `llamacpp`
runner reports only 0.29, 1.32 and 2.63 GiB, despite much larger installed model
packages and process RSS. This discrepancy is not reconciled. Do not interpret
those small numbers as weight residency, or use them to rank memory efficiency
across runners. RSS can count shared mappings more than once; it is not an OS
peak. The views overlap on unified memory and must never be added. Sampling
can miss brief peaks. The process lock does not isolate other applications or
measure thermal throttling. Instrumented latency is specific to this machine.

## Review provenance and limitations

Every primary review covers all four requested claims. A second assistant
checked all 28 reports flagged under the prospective rule and five prespecified
unflagged samples: 33 reports and 132 slots. It agreed with all 132 primary
claim outcomes and retained ten prose-severity disagreements. This selected
agreement is not a reliability estimate or independent human validation.

Primary reviews retain 82 material-prose flags across 24 reports. Assistant
adjudication downgrades ten wording flags, leaving 72 flags across 22 reports.
Both views remain public numerically; original private judgments and exact
quotes are unchanged. These are flag counts with no emitted-assertion
denominator, and some overlap requested claims or related prose. Do not add
them to false-claim counts or describe them as a prose error rate. The ten
downgrades concern temporal, returned-set scope and credential-chain wording;
explicit false budget and executed-scope claims remain material.

One review-order deviation affects `r1-c2-m1-adaptive`, the first E2B adaptive
KMS report. An append script applied fixed-report draft wording before target
inspection. The original draft remains preserved. The actual target input and
report were then inspected, corrected returned-evidence judgments were locked,
and only then was the complete source reopened. A second assistant read both
E2B KMS reports and actual inputs before consulting the primary labels; its
eight claim outcomes agree with the final reviews. This correction does not
restore blinding. The public summary identifies the retained draft count and
history hash. No model output, runtime, fixture or mechanical score changed.
Two earlier full-source enum tokens were normalized as documented metadata;
the secondary review preserves both original and normalized snapshots.

The cases, rubric and prior outputs were known to the reviewing assistants.
Assistant source judgments need independent human review. Two exposed synthetic
case clusters cannot establish general incident-response reliability. No
private logs, live AWS access, attack execution, remediation, hosted model
inference or LangSmith upload was used.

## Artifact verification and next scope

The frozen runtime passed 703 tests before inference. Final reporting and
integrity tests bring the checked suite to 734 passing tests, with lint and
formatting passing. These test-only mocks verify code behavior and remain
separate from actual model capability evidence.

The genuine LangSmith SDK replay evaluated 40 stored outputs with
`upload_results=False`, producing 840 prefixed feedback items and no new model
or tool calls. Its replay outputs match the original batch. The separate
portable auditor re-derived all 21 primary counters, checked wire inputs,
model/version identity, sources, aliases, projections, resource arithmetic and
actual trace trees, and replayed all 94 queries locally. Those verification
replays do not count as model investigation work. The separate metric
implementation verifies the defined contract; it does not validate the
semantic rubric as independent research.

| Artifact | SHA-256 |
| --- | --- |
| Frozen protocol | `8fbea96221f8948ffe9303a4e41cd9decee0a353262866bbcd5cfb7c35d15643` |
| Original private batch | `6c4faf86e2a374e0636850350372029ae8fe400ef120a91af10a0d8d36afb60d` |
| Private SDK replay | `4085b9aab0920d6faaca0ca105a3a6c53b79ae29d3b6dfc4fca369416bfff95a` |
| Private separate audit | `edb2075cafcc76fdf7a59d4a4d84d5f96a8927df78ead36ecd3785fb1a7a8995` |
| Public numeric summary | `427119be39d68ac530ee7299269f900d8ff1a56dbff328a68c293029d9afe69e` |

The first-ten gate selected 40 from runtime and resource availability, before
later results: 1,002.80 seconds gave a 4,813.44-second forecast with 20 percent
allowance. Answer quality did not affect expansion. The final 4,057.82-second
cell total stayed below the soft 5,400-second launch ceiling.

The [proposed next study](benchmark-plan.md) uses eight fresh synthetic cases
with both methods and all five models: 80 core runs, at most 100 with two
preselected paired repeat cases. At this pilot's cost mix and an added
20 percent allowance, those estimates are 162.31 and 202.89 minutes. They are
forecasts, not executed work or guarantees; larger inputs or fewer fast
failures can raise cost. Any planning-schema change gets a separate exposed-data
comparison before a new runtime and fresh held-out suite are frozen.
