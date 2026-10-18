# Frozen local evaluation

## October 18 protocol v8 and finding-level support

The v7 suite has four independently authored synthetic cases, two per split,
with 20 records, 15 relevant records, 16 fixed hypotheses and 51 exact typed
required atoms. It was frozen before v8 inference. Earlier suites, including
the exposed v6 development case, retain their original bytes and labels.

The [v8 protocol](protocol-v8.json) freezes 13 source files, eight schemas,
the prompt, models, budgets, scorer source and manifest. SHA-256:
`e025493b6f2309d86c9339b4217a7bf1aedbbd51aa209d837d1e75e8f4cefcca`. Manifest SHA-256:
`56c128e29c8e3588f9cd4fbac83759538db9e20143df91a54e2fb425456fc75a`. V8 adds a returned-record credential map
and a short planning instruction. No query is forced or selected by code.
Report instructions, schemas, projection, tools, fixed searches and budgets
retain their earlier contracts. All methods share the added context.

The separate [measurement contract](../docs/measurement.md) requires each
finding's own exact links. It never credits a required atom from global
observations, another finding, rationale or bare citations. Source identity,
selection, actual return, typed value and presence must match. Raw contract
support and process-valid primary credit remain separate; invalid processes
retain every expected claim and atom and earn zero primary credit. The old
global-projection metrics remain in `metrics`; the new values use
`claim_support_metrics`. SDK dispatch is explicit, versioned and namespaced.
Complete annotation contracts do not prove semantic entailment. Selected-event precision and recall are raw means that include invalid processes. Primary claim and atom credit is process-gated.

| Model and method | Valid processes | Mean raw selected-event precision / recall | Complete primary claim contracts | Primary required atoms | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 3/4 | 100.00% / 81.25% | 3/16 | 24/51 | 2.00 | 214.93 |
| Qwen fixed | 4/4 | 100.00% / 45.83% | 2/16 | 23/51 | 3.00 | 62.73 |
| Gemma adaptive | 2/4 | 100.00% / 93.75% | 1/16 | 17/51 | 2.50 | 267.29 |
| Mistral adaptive | 1/4 | 75.00% / 50.00% | 0/16 | 5/51 | 2.00 | 133.29 |

| Model and method | Split | Valid processes | Mean raw selected-event precision / recall | Complete primary claim contracts | Primary required atoms | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | development | 2/2 | 100.00% / 87.50% | 1/8 | 16/26 | 2.00 | 216.01 |
| Qwen adaptive | heldout | 1/2 | 100.00% / 75.00% | 2/8 | 8/25 | 2.00 | 213.84 |
| Qwen fixed | development | 2/2 | 100.00% / 41.67% | 1/8 | 11/26 | 3.00 | 64.96 |
| Qwen fixed | heldout | 2/2 | 100.00% / 50.00% | 1/8 | 12/25 | 3.00 | 60.49 |
| Gemma adaptive | development | 1/2 | 100.00% / 100.00% | 0/8 | 9/26 | 2.50 | 278.98 |
| Gemma adaptive | heldout | 1/2 | 100.00% / 87.50% | 1/8 | 8/25 | 2.50 | 255.59 |
| Mistral adaptive | development | 1/2 | 100.00% / 75.00% | 0/8 | 5/26 | 2.00 | 144.35 |
| Mistral adaptive | heldout | 0/2 | 50.00% / 25.00% | 0/8 | 0/25 | 2.00 | 122.23 |

These are 10 completed and 6 invalid processes from 16 actual
local runs, one repeat per cell. Every failure is retained. Primary required
atom coverage totals 69/204. Query and latency means include
invalid runs. The [numeric results](results-v8.json) preserve separate legacy
and new metrics, per-cell and split rows, effective weights and artifact hashes.
The [assistant evidence review](../docs/v8-evidence-review.md) separates actual
semantic errors, missing retrieval, incomplete links and correct uncertainty.
It is not independent human review. There is no cross-suite, cross-scorer,
model-winner or production-reliability claim.

All 16 fresh saved outputs received genuine offline SDK evaluation with 336
prefixed feedback items, no uploads and no new replay inference. Independent
verification re-derived all 21 new counters without calling the scorer, and
checked exact raw/SDK trace identity, prompts, schemas, tool scopes, source
records, maps, projections and budgets. The exposed two-run development check
received 42 separate SDK feedback items before the final malformed-metadata
guard. Its archived source and original raw/SDK artifacts remain unchanged.

```sh
uv run tracetrail compare --manifest evaluation/cases-v7.json \
  --output local-results/comparison-v8.json
uv run tracetrail local-evaluate local-results/comparison-v8.json \
  --scorer claim-support-v1
```

The comparison returns nonzero if any process is invalid or failed, while
saving every cell. Offline replay recomputes the recorded contract and refuses
unknown/mixed IDs, source replacement and existing-artifact replacement.
Raw outputs and feedback remain in ignored private local files. See
[progress and release checks](../docs/progress.md) for the separate actual CLI
demo, preserved development failure, full hashes and remaining work.

## October 17 protocol v7 methodology and measured results

The frozen v7 study uses `tracetrail-synthetic-v6`, selected with
`--manifest evaluation/cases-v6.json`. Its manifest SHA-256 is
`e49257ef91352b7e1686bebc79bd04f61078e0da8be39651c1495aeadf702b87`.
The four synthetic cases contain 20 records, 14 relevant records, 16 fixed
hypotheses, and 43 required observation atoms. Each split has two cases.

| V6 suite case | Split | Evidence question |
| --- | --- | --- |
| `dev-retention-chain` | Development | Link earlier caller activity, role issuance, and retention requests across source addresses. Separate requested settings from business approval. |
| `dev-topic-denial` | Development | Find the issuer of a denied topic request and related activity. Separate the API outcome, later topic state, and intent. |
| `heldout-directory-path` | Held out | Recover original caller and child-request context for a user-metadata request. Separate the requested path from later user state. |
| `heldout-trail-operations` | Held out | Link logging activity, credential issuance, original caller history, and a later status request. Separate API requests from logging state and approval. |

The [frozen v7 protocol](protocol-v7.json) has file SHA-256
`b00bb95ecb13990607c9cc4713c9628bf812cbf738b17537bb9a8acf6cbd8c18`.
Its prompt SHA-256 is
`544041d360b9a675be55254c61d2582314d6bbb7f61a521e39c028b0797c302e`.
Source, schema, prompt, catalog, and manifest hashes were fixed before fresh
inference. The reporting schema and instructions, exact fact projection,
historical scorer, and fixed searches retain the v6 contract. Budgets remain
three queries, at most four model calls, and 3,200 output tokens per call.

V7 adds a model-authored ledger for every hypothesis before each action. A
decision explicitly includes the required nullable `candidate_id`,
`continuation_id`, `query`, and `identifier` fields, plus the required
`dispositions` array. Omitted fields fail validation. Unused branch fields
must be null, and `query_events` chooses exactly one candidate, continuation,
or custom query. Code materializes only that choice, without an automatic
search or replacement filter.

For finish, all four branch fields are null. Every ID in
`coverage.finish_accounting_ids` must appear exactly once in the model's
dispositions, including already queried candidates and pending pages. The
list only enumerates the visible capped catalog; it assigns no decision or
reason. The model can defer a query and finish with budget left. A tested
disposition needs an actual successful matching scope, and a pending page
cannot be called tested. Validation checks references and recorded attempts,
not whether the rationale or relevance judgment is true. Invalid plans remain
invalid even if final reporting produces exact facts and raw scorer values.

The final development check used one already exposed case from the v5 suite
with Qwen adaptive and fixed search. Two earlier candidate batches and their
failures are preserved separately. Fresh v6-suite development and held-out
outputs were not used to tune the frozen protocol. The study defines 16 cells:
adaptive runs for three models plus fixed Qwen search, once on each case.
All 16 actual runs finished: ten completed structural checks and six were
invalid. Every run remains in the denominator. Reviewed cases are now exposed
data for later protocols informed by their outputs.

### Full-suite means and primary field coverage

Each row has four runs. All mean report metrics include invalid processes and
retain the unchanged historical scorer. They do not certify a valid planning
process. Primary declared field coverage gives credit only to required paths
explicitly linked in the corresponding finding of a completed, valid process.
Invalid processes earn zero credit and keep their required-field denominators.

| Model and method | Valid processes | Mean selected-event precision | Mean selected-event recall | Mean raw strict support | Mean raw status accuracy | Primary declared field coverage |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 3/4 | 100.00% | 87.50% | 81.25% | 100.00% | 23/43 |
| Qwen fixed | 4/4 | 91.67% | 50.00% | 18.75% | 50.00% | 17/43 |
| Gemma adaptive | 3/4 | 100.00% | 70.83% | 56.25% | 87.50% | 17/43 |
| Mistral adaptive | 0/4 | 66.67% | 54.17% | 31.25% | 100.00% | 0/43 |

Combined primary coverage was 57/172 unique required combinations of a claim,
original source record, and exact field path. Duplicate links, global projected
facts, and rationale text earn no credit. This metric does not test role truth,
value correctness, relevance, or semantic entailment.

| Model and method | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- |
| Qwen adaptive | 2.00 | 4.00 | 199.29 |
| Qwen fixed | 3.00 | 1.00 | 49.55 |
| Gemma adaptive | 1.50 | 3.50 | 200.82 |
| Mistral adaptive | 2.25 | 4.00 | 148.34 |

### Development and held-out results

Each row below contains two runs and eight fixed findings. Development results
were not used to change the frozen protocol during the study. The primary
coverage denominator is 21 required atoms for development and 22 for held-out
cases, for each model and method.

| Model and method | Split | Valid processes | Mean selected-event precision | Mean selected-event recall | Mean raw strict support | Mean raw status accuracy | Primary declared field coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | Development | 2/2 | 100.00% | 100.00% | 100.00% | 100.00% | 18/21 |
| Qwen adaptive | Held out | 1/2 | 100.00% | 75.00% | 62.50% | 100.00% | 5/22 |
| Qwen fixed | Development | 2/2 | 83.33% | 50.00% | 12.50% | 50.00% | 8/21 |
| Qwen fixed | Held out | 2/2 | 100.00% | 50.00% | 25.00% | 50.00% | 9/22 |
| Gemma adaptive | Development | 1/2 | 100.00% | 66.67% | 50.00% | 87.50% | 7/21 |
| Gemma adaptive | Held out | 2/2 | 100.00% | 75.00% | 62.50% | 87.50% | 10/22 |
| Mistral adaptive | Development | 0/2 | 33.33% | 33.33% | 0.00% | 100.00% | 0/21 |
| Mistral adaptive | Held out | 0/2 | 100.00% | 75.00% | 62.50% | 100.00% | 0/22 |

### Evidence, failures, and limits

Thirty-four of 64 findings failed the raw strict scorer. That scorer uses
required atoms in the global deterministic projection, not every finding's
declared links. Raw selected-set precision and recall can describe a retained
report from an invalid process, rather than every record returned by a tool.
Raw status accuracy also counts labels in invalid processes. Mistral's 100%
status accuracy with zero valid processes illustrates why matching labels do
not establish a working investigation or sound reasoning.

The [Qwen evidence review](../docs/v7-evidence-review.md) compares its eight
saved cells against exact records. It is an assistant source review, not
independent human review. It records a key-use pivot falsely called tested by
an issuance query, voluntary finishes with one query left, missing caller or
status context, and incomplete declared links despite passing raw support.
The invalid process and its final report remain preserved; no repair or
replacement query was used.

Original inference traces contain 50 actual model spans and 35 tool spans.
The genuine local LangSmith SDK replayed all 16 outputs and produced 352
numeric feedback items with `upload_results=False` and no new inference.
The raw comparison SHA-256 is
`830b9f4cfa63d86a9803585724b1692328329042b5863156babd5125aa3a660e`.
The SDK artifact SHA-256 is
`72fe231b57d92d1e67d5b8e6d41bc4ffa188b13e9a7dc6bea6ac44c6c0a85c9c`.
These counts exclude earlier development candidates and the CLI demonstration.

The fixed control uses only the original seed identity, source address, and
caller key in a one-hour window on each side of the seed. It is a simple
baseline. There is one run per cell and only two cases per split. Cases and
annotations differ from earlier suites; these results establish no cross-suite
improvement, model winner, or production reliability. See
[results-v7.json](results-v7.json), [progress](../docs/progress.md), and
[integration details](../docs/integrations.md) for the recorded experiment and
its validation boundaries.

## Preserved suites

The CLI default remains `tracetrail-synthetic-v2`, selected by
`evaluation/cases-v2.json`, so existing commands still work. Its fixtures are in
`fixtures/v2/`. The v1 suite and its hashes remain available for earlier runs.
V1 includes fixture errors described in [CloudTrail semantics](../docs/cloudtrail.md).
Both earlier suites contain two original development and two original held-out
cases. All four have now been inspected and are exposed for future protocol
changes. Their saved split labels describe the original comparisons. They do
not provide an untouched held-out test of changed protocols. All earlier outputs and failures
remain intact.

The preserved `tracetrail-synthetic-v3` suite is selected explicitly with
`--manifest evaluation/cases-v3.json`. Its manifest SHA-256 is
`6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d`.
It contains one development and one held-out case. The manifest and fixture
hashes were checked before the v4 comparison.

The preserved protocol v5 comparison used `tracetrail-synthetic-v4`, selected with
`--manifest evaluation/cases-v4.json`. Its manifest SHA-256 is
`25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16`.
It contains `dev-midnight-role-change` as development data and
`heldout-archive-role-chain` as held-out data. The earlier v2 and v3 cases are
exposed for v5. All v2, v3, and v4 cases are now exposed for protocol v6. Their
bytes, annotations, split labels, and results remain available for historical
comparisons.

The preserved protocol v6 comparison used `tracetrail-synthetic-v5`, selected with
`--manifest evaluation/cases-v5.json`. Its manifest SHA-256 is
`66f704a593c5d152d82f683cded4b1fa8014f58fe05f337d0bdaef615cde3e96`.
The four cases contain 18 records, 14 relevant records, 16 hypotheses, and 96
required field observations. Each split has two cases. The manifest and fixture
hashes were checked before the frozen protocol comparison. The measured v6
results below retain all completed and invalid reports.

This suite tests investigation of a small supplied CloudTrail log window. All
accounts, identities, IP addresses, resources, and API events are invented.
The records do not describe an incident or a public attack sample. IP addresses
use documentation ranges. The fixtures use the repository's MIT license.

| Earlier case | Original split, now exposed | Evidence question |
| --- | --- | --- |
| `dev-role-pivot` | Development | Link a temporary key to later actions. Test maintenance, compromise, and external transfer. |
| `dev-maintenance` | Development | Check a stop, configuration change, start, and status sequence. Keep approval separate from API facts. |
| `heldout-denied-and-missing` | Held out | Distinguish denied requests from success. Do not infer later trail state from missing records. |
| `heldout-data-access` | Held out | Link object requests to a session. Distinguish allowed and denied requests from deletion and transfer claims. |

| Preserved v3 case | Original split, now exposed | Evidence question |
| --- | --- | --- |
| `dev-caller-and-child-pivot` | Development | Link the caller and returned temporary key across changed source addresses. Keep approval and trail state uncertain where records do not establish them. |
| `heldout-issued-key-chain` | Held out | Find the issuer of an observed temporary key and the original caller. Distinguish denied requests from success and test an approved-audit explanation. |

| Preserved v5 case | Original split, now exposed | Evidence question |
| --- | --- | --- |
| `dev-key-lifecycle` | Development | Link role assumption, caller history, and an access-key request. Separate requested status from later key state and distinguish callers at the same source address. |
| `dev-network-denial` | Development | Investigate a denied security-group request and its credential issuer. Separate the API outcome from later resource state and intent. |
| `heldout-publication-denial` | Held out | Link an object upload attempt to its temporary credential issuer and original caller. Separate request outcome from approved publication and distinguish same-address callers. |
| `heldout-encryption-state` | Held out | Investigate a KMS request and its credential chain. Separate the request from later key state and approval; an unlogged read response is not state evidence. |

One preserved development record contains an instruction in a role description. It is
untrusted log data. It must not control the investigator.

Each manifest defines the questions, fixed hypotheses, relevant event IDs, and
claim annotations. Each fixture has a SHA-256 hash of its exact file bytes.
`load_cases` checks those hashes and verifies each annotated field against the
source record. Citations use
`sha256:<file hash>/Records/<zero-based array index>`.

The investigator receives the question and hypothesis statements. It does not
receive relevant-event labels or claim annotations. Fields that start with `_`
in a loaded case are local scorer data and must not enter model input. Use only
development cases to change prompts, tools, and budgets. Keep held-out results
in their own report, including failures. If those results inform a change, that
suite is no longer an untouched test set for the changed version.

Do not edit this frozen suite in place after results are recorded. A later suite
must have a new ID and keep old fixtures, annotations, and results available.
`fixtures/build_synthetic_v2.py` reproduces the v2 bytes from the preserved
invented v1 definitions and documented AWS field corrections. It has no model, AWS, or network calls.

## October 16 protocol v6 contract and measured results

The [frozen v6 protocol](protocol-v6.json) has file SHA-256
`062030719ddd94ec17eb42518051c5f819475719eb5a92f500c72e42e6f8b456`.
Its frozen prompt SHA-256 is
`4335bc9f8c85cce8502b6c4858ab64863c7b982cbe93fed1783de7583ca23db9`.
Two initial development candidate runs are preserved separately. They informed
a general component instruction before the final protocol freeze and are not
fresh results for the frozen comparison.

V6 findings contain model-authored `evidence_links`, each with a selected
citation, exact field paths, and a `supports`, `contradicts`, or `context` role.
The model also supplies a brief rationale, missing-evidence gaps, and the
status of the unchanged hypothesis. The wire schema forbids separate finding
citations and observations. Public citations are derived only from explicit
links; code does not add missing evidence from the selected-record pool.

Structural validation rejects unknown or unselected link citations, unresolved
field paths, missing required support or contradiction roles, and uncertain
findings without an explicit gap. These checks establish source presence, not
semantic entailment. A valid field link can still have an incorrect role,
rationale, or status. Projection remains the same generic extraction from
selected returned records for every model and method. It supplies no gold
labels, extra evidence, status repair, or automatic retry.

The budgets remain three queries, at most four model calls, and 3,200 output
tokens per call. Local SDK evaluation and trace storage are unchanged and need
no hosted setup. Sixteen actual investigations ran under the frozen protocol.
Each group has four runs: two development cases and two held-out cases. Thirteen
reports completed; three Mistral reports were invalid. Every run remains in the
comparison denominator.

| Model | Method | Valid reports | Mean selected-event precision | Mean selected-event recall | Mean annotated support | Mean raw status accuracy | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen | adaptive | 4/4 | 100.00% | 64.58% | 56.25% | 75.00% | 1.00 | 3.00 | 100.44 |
| Qwen | fixed | 4/4 | 70.83% | 43.75% | 12.50% | 56.25% | 3.00 | 1.00 | 64.71 |
| Gemma | adaptive | 4/4 | 95.00% | 91.67% | 75.00% | 100.00% | 2.25 | 3.75 | 154.52 |
| Mistral | adaptive | 1/4 | 50.00% | 43.75% | 18.75% | 81.25% | 3.00 | 4.00 | 96.24 |

Precision and recall measure the validated selected set, not all records a tool
returned. An invalid selected pointer earns no record credit even when the
correct record was returned. Raw status accuracy counts the model's hypothesis
labels, including labels in invalid reports. It is not report validity, strict
support, or a semantic truth score. Strict support also uses global
code-projected facts. A passing finding need not contain every required field
path in its model-authored links. These are distinct evaluation boundaries.

A separate field-path audit counts each unique required combination of a
hypothesis, exact original record reference, and field path. Only a link in the
corresponding completed, valid finding earns credit. Repeated paths cannot
increase the score. Global projected facts and rationale text earn no credit.
This audit ignores the declared role and does not test value correctness,
relevance, or entailment.

| Model | Method | Required field paths explicitly linked |
| --- | --- | --- |
| Qwen | adaptive | 43/96 |
| Qwen | fixed | 20/96 |
| Gemma | adaptive | 44/96 |
| Mistral | adaptive | 15/96 |

Combined coverage was 122/384. The three invalid reports accounted for 74
required combinations and earned zero credit; their denominators remain.

Thirty-eight of 64 findings failed strict support checks. Qwen adaptive finished
after one query in all four cases and left relevant context unqueried. Qwen and
the one valid Mistral report treated an `AccessDenied` outcome as a refutation of
approval. Mistral's invalid reports included missing contradiction roles and
invalid `/evidence/...` selected references. Fixed search could match a status
without finding the credential-issuance record needed to support it. These
failures remain visible; they are not all hallucinations or parser failures.

The genuine offline LangSmith SDK evaluation replayed all 16 saved outputs and
produced 352 feedback items with `upload_results=False` and no new inference.
The raw comparison SHA-256 is
`c7eee979197141a84287391810ac42df226a8ad06ef270f267772a7ca80c1be2`.
The offline SDK artifact SHA-256 is
`da013dc3040441efb472e94f8bd157afe2e06c440f6a185676fbb53ad6bdf6cb`.
These counts exclude the separately preserved development candidates and CLI
demonstration.

There is one run per model-method-case cell and only two cases per split. The
suite and protocol differ from earlier comparisons, so these numbers establish
no cross-suite improvement, model winner, or general adaptive advantage. See
[results-v6.json](results-v6.json) and [progress](../docs/progress.md) for the
development and held-out scores, exact artifacts, and reviewed failures. The
[integration details](../docs/integrations.md) explain the bounded link contract.

## October 15 protocol v5 contract and measured results

The v5 model report wire schema contained selected records, finding
citations, unchanged hypothesis statements with statuses, and narrative
limitations. It forbids model-supplied observations. Once the selection passes
validation, generic code projects exact typed fields from the selected returned
records. The same projection applies to every model and method. It receives no
gold labels, support annotations, or additional runtime records. Projection
does not select evidence or correct conclusions.

The saved `observation_source` identifies projected values, and
`validation_scope` records that narrative and finding meaning remain
unverified. Whole arrays, empty objects, and actual nulls retain their JSON
types. The generic four API envelope absence rules and projection limits are
documented in [integration details](../docs/integrations.md). Projection errors
make a report invalid instead of silently truncating its facts.

Evidence is presented in UTC order with stable aliases and signed seconds from
the seed. These values derive from observed timestamps and do not establish
causality. The budgets remain three queries, at most four model calls, and
3,200 output tokens per call. V5 changes the wire contract, fact projection, and
chronological context together, so a comparison cannot isolate one change's
effect. A valid report does not establish semantic truth.

The [frozen v5 protocol](protocol-v5.json) has file SHA-256
`91adcc1f7e70d6793cc4a9a83f68396177385896789fe5dcb74b907f788b005b`.
Its frozen prompt SHA-256 is
`2f26e74763277a642ad5df16652a97c42693ad1fca01532a90d369652768f7c6`.
All eight fresh-suite v5 investigations completed under the frozen protocol.
Each group below has two runs: one development case and one held-out case.
Selected-record precision was 100.0% in every group.

| Model | Method | Mean recall | Mean annotated support | Mean status accuracy |
| --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 87.5% | 62.5% | 87.5% |
| `qwen3.8:27b-q4_K_M` | fixed | 50.0% | 25.0% | 50.0% |
| `gemma4:31b-it-q4_K_M` | adaptive | 100.0% | 75.0% | 100.0% |
| `mistral-small3.2:24b` | adaptive | 62.5% | 37.5% | 62.5% |

The audit recomputed every projected observation exactly. Raw model reports
contained no observations. These support scores combine code-extracted facts
with model-selected evidence, finding citations, and statuses; they do not
measure model field extraction. Sixteen of 32 findings failed strict support
checks. All 16 lacked required finding citations; eight had status mismatches,
and 12 lacked required field support. These categories overlap and cannot be
added as separate failed findings. No incorrect projected fact was found.

Qwen correctly handled the development sequence across midnight, but still
refuted a held-out caller claim because it had not retrieved the caller record.
That missing evidence called for uncertainty, not a refutation. Correctness on
one development sequence does not establish a general temporal-reasoning fix.
The suite has one case per split and one run per cell. It establishes no model
winner, broad adaptive advantage, or production reliability. All reviewed cases
are now exposed for future changes that use their outputs.

The fresh-suite offline SDK evaluation replayed eight saved outputs and
produced 176 feedback items, with uploads and new inference disabled. Including
four exposed regression runs and the real CLI demonstration, v5 validation
recorded 13 actual investigations, 39 model spans, and 33 tool spans. The 12
comparison outputs received 264 offline SDK feedback items; the demonstration
is separate from those SDK replays. Detailed split scores, artifact hashes,
and reviewed failures are in [progress](../docs/progress.md) and the versioned
[results-v5.json](results-v5.json).

## October 14 measured protocol v4

The measured v4 source gave the planner an inventory of
observed candidate filters and actual attempted query scopes. The model still
chooses its queries. It does not receive relevance labels, expected statuses,
or support annotations. The prompt distinguishes the caller key, returned
temporary keys, and the event that issued a key. It asks the model to consider
changed source addresses and context outside a one-hour window. Pagination
consumes the same three-query budget as other follow-up queries.

Every model and method uses the same 3,200-token output allowance. The report
prompt permits up to 32 observations, and the schema accepts up to 40. V4
changes instructions, query capabilities, and output allowance together.
An observed difference from v3 cannot isolate the coverage inventory's effect.

Compare the installed local models with identical frozen prompts, tool
schemas, decoding settings, cases, and budgets. Qwen is the reference model.
Compare adaptive investigation with the fixed-search Qwen control separately.
Keep model tags and weight digests, raw responses, tool transcripts, errors,
timings, prompt and protocol hashes, and local trace trees. Preserve every
attempted cell. Development and held-out results must stay separate.

The [frozen protocol file](protocol-v4.json) records source and schema hashes,
model tags, manifests, prompts, and budgets. Its file SHA-256 is
`2ef24248b2bcc5607444dbb200139f90dc8aa356e3400e0b359daa5f723125b1`.
The prompt SHA-256 is
`1592e44d335c044e5f06b6ddfc0a0fbdb62431b42adee86e5f0240811ab37db2`.

All eight exposed-case Qwen v4 regression investigations completed. Adaptive
mean recall changed from 66.25% to 60.00%, and mean exact support changed from
30.00% to 46.67%. Fixed search reached 95.00% recall and 50.83% exact support in
v4. Adaptive still used one query per case and missed context. The coverage gap
remains, and these exposed-case results do not establish an adaptive advantage.
Both methods' maintenance reports still inferred trail state from a
`StartLogging` request despite a null status response. See the complete measured
regression and preserved v3 comparison in [progress](../docs/progress.md).

The regression's actual trace trees contain 16 model spans and 16 query-tool
spans. The genuine local SDK replay evaluated eight outputs and produced 176
feedback items with `upload_results=false` and `inference_rerun=false`. Its
source hash matches raw results SHA-256
`e3277416799b390db76a8fced5b490c11ce19bd6d7815db045b834638f43da11`.

All eight fresh-suite v4 investigations completed. Gemma and Mistral adaptive
search each reached 100.00% precision and recall but 0.00% exact support. Qwen
adaptive reached 100.00% precision, 87.50% recall, and 12.50% exact support. The
fixed Qwen control reached 58.33% precision, 37.50% recall, and 0.00% exact
support. These means cover two cases, not a large test population.

In total, 31 of 32 findings for the supplied fixed propositions failed strict
support requirements. Most
failures were omitted fields or citations, with some wrong status labels.
This is not a count of 31 proven semantic hallucinations. Human review found
that Qwen recovered all four development records and emitted 15 exact
observations, but still misread the direction of the caller timing comparison.
Gemma and Mistral chose the correct fixed status labels, while their reports
omitted required evidence support. Qwen's held-out investigation stopped after
two queries and missed a later denied `DeleteBucket` request.

The fresh raw traces contain 26 real model spans and 22 query-tool spans. The
genuine offline SDK replay evaluated eight outputs and produced 176 feedback
items with uploads and new inference disabled. Its source hash and feedback
matched the saved results and recomputed metrics. Detailed development and
held-out results, source hashes, and the actual CLI demonstration are in
[progress](../docs/progress.md); versioned cell and split metrics are in
[results-v4.json](results-v4.json).

Final local source verification passed Ruff checks, formatting, and all 220
tests. CI status tied to each commit is available in the
repository [Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

The fresh cases show higher adaptive retrieval coverage than this fixed-search
control, with weak claim support. They do not establish a model winner, broad
adaptive advantage, or reliability result. One run per cell does not measure
response stability. One development case and one held-out case can expose
failures but cannot establish production performance. Their outputs are now
inspected and exposed for any later change that uses them.

## What the scorer checks

`score_run(case, result)` recomputes support from the frozen source and the
complete saved run. Each scored finding must keep the supplied hypothesis
statement, claim ID, and annotated status. For every required event, it must
give the exact citation. The required field and value observations must also
appear in the report. Booleans, numbers, nulls, and missing fields are distinct.

The source record, event ID, file hash, and array index must agree. A non-seed
record must also appear in a successful saved `query_events` or `get_event`
response. A record cannot earn support merely because its citation exists in
the fixture. Extra findings, changed statements, duplicate claims, missing
support, and unsupported status changes count as unsupported findings.

These checks test the supplied fixed propositions. They are a conservative
annotation score, not a general judge of free text. They do not score the
meaning of narrative limitations or prove that a human explanation is correct.
Human review is still needed for new claims and real log data. An unusual
address or a sensitive API request does not prove compromised credentials.
Missing approval records do not prove malicious intent. A denied stop request
does not prove that logging was active. An object request does not prove
transfer to an external destination.

| Metric | Meaning |
| --- | --- |
| Relevant-event precision | Relevant valid selected records divided by all unique selected references. Noise and invalid references lower this score. |
| Relevant-event recall | Relevant valid selected records divided by all annotated relevant records. |
| Unsupported claims | Findings that fail the fixed statement, status, citation, or field support checks. |
| Annotation coverage | Fraction of fixed claims present in the output. Empty output has zero coverage. |
| Status accuracy | Fraction of fixed claims with the exact statement and correct status. This score alone does not verify evidence support. |
| Supported annotation rate | Fraction of fixed claims that pass every support check. |
| Insufficient-evidence handling | Fraction of expected uncertain claims that pass every support check. |
| Query count | Attempted follow-up queries. The initial seed lookup is excluded. |
| Tool errors | Saved tool responses with an error. A denied AWS API event in a log is evidence, not a tool error. |
| Duration | Saved investigation wall time in seconds, including local inference. |

An empty output has no unsupported-claim rate, zero coverage, and zero recall.
Failures keep their place in the comparison. Do not drop failures or average
only completed runs. Compare models with the same frozen prompts, tools,
cases, and budgets. Report development and held-out results separately.
Compare adaptive queries with fixed queries using the same model.

## Local use

Run the scorer tests:

```sh
uv run pytest tests/test_evaluation.py
```

Run development investigations with installed local Ollama models:

```sh
uv run tracetrail compare --manifest evaluation/cases-v6.json \
  --split development --output local-results/development-suite-v6.json
```

The runner records model responses, evidence, tool history, errors, versions,
hashes, budgets, and timing. The scorer does not call a model. Constructed
annotation-perfect reports and injected tool faults in `test_evaluation.py`
are unit-test inputs. They are not model results or capability evidence.

These small synthetic suites are too small to establish production performance. They can
expose specific failures and support a repeatable local comparison. New data,
more independent annotations, and human review are required before broader
claims can be made.

## Genuine local LangSmith SDK evaluation

The local evaluator calls the real LangSmith SDK `evaluate()` function with
local examples, `upload_results=False`, and `disable_evaluator_tracing=True`.
It replays saved inference outputs and recomputes support against the manifest
recorded in the batch. It makes no new model calls. The client transport rejects
API requests. Tests also forbid socket connections while ambient tracing is
enabled. SDK trace trees and feedback are saved to private local files.

An offline SDK evaluation is not a hosted experiment or a hosted trace. Its
timestamps describe replay and scoring; the stored result retains the original
investigation timings. A full LangSmith server and UI remain separate and
unconfigured. The local SDK workflow requires no account or key. See
[integration details](../docs/integrations.md) and dated measured results in
[progress](../docs/progress.md).
