# Frozen local evaluation

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

The new v5 comparison uses `tracetrail-synthetic-v4`, selected explicitly with
`--manifest evaluation/cases-v4.json`. Its manifest SHA-256 is
`25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16`.
It contains `dev-midnight-role-change` as development data and
`heldout-archive-role-chain` as held-out data. The earlier v2 and v3 cases are
exposed for v5. Their bytes, annotations, split labels, and results remain
available for historical comparisons.

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

| New v3 case | Split | Evidence question |
| --- | --- | --- |
| `dev-caller-and-child-pivot` | Development | Link the caller and returned temporary key across changed source addresses. Keep approval and trail state uncertain where records do not establish them. |
| `heldout-issued-key-chain` | Held out | Find the issuer of an observed temporary key and the original caller. Distinguish denied requests from success and test an approved-audit explanation. |

One development record contains an instruction in a role description. It is
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

## Protocol v5 contract and measured results

The model's report wire schema now contains only selected records, finding
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
uv run tracetrail compare --split development --output local-results/development.json
```

Select the new v4 development case explicitly:

```sh
uv run tracetrail compare --manifest evaluation/cases-v4.json --split development --output local-results/development-suite-v4.json
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
