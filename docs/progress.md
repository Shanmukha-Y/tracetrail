# Progress and release checks

The repository stays private until the release checks pass. Workflow Sentinel is complete and was not changed.

## Implemented

- Local CloudTrail JSON ingestion with exact record citations, indexed queries, and explicit budgets.
- LangChain Ollama structured output and read-only evidence tools.
- A stateful LangGraph investigation with bounded query and model calls.
- Observed field validation, hypothesis status, cited timelines, raw failure retention, and private local files.
- Three installed local model tags, sequential inference, raw remote-routing checks, proxy and redirect guards, and no ambient credential use.
- Real local graph traces and genuine offline LangSmith SDK evaluation with blocked HTTP.
- Preserved earlier synthetic suites and a frozen two-case v4 suite with field support annotations.
- CI for lint, formatting, and tests without inference or hosted tracing.

## October 15: selected-record facts and temporal context

Protocol v5 separates model decisions from exact field extraction. The model
selects records, finding statuses, citations, and limitations. After a valid
selection, code copies typed JSON fields from those selected returned records.
The code does not select additional events, use annotations, change findings,
or infer approval, intent, success, or state. The output marks these facts as
`selected-record-projection-v1`. Conclusions and narrative remain semantically
unverified.

The model receives evidence in UTC timestamp order and a separate table of
signed seconds from the seed. Negative values precede the seed. Citation aliases
remain stable in discovery order. This is timestamp assistance, not a claim of
causality or a verified temporal conclusion.

The projection preserves exact types, empty values, whole arrays, and missing
versus null API fields. It fails explicitly on ambiguous paths or limit errors.
The limits are 2,000 observations, one million bytes of compact ASCII-escaped
JSON, depth 32, and 512 characters per field path. Invalid selections receive no
extracted facts. The model cannot supply its own observation values through the
new wire schema.

The fresh `tracetrail-synthetic-v4` suite was reviewed and frozen before v5
inference. It has one development and one held-out case. All records are
invented, with native UTC timestamps. The earlier suites remain unchanged and
are exposed regression material. The new manifest SHA-256 is
`25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16`.

The [v5 protocol](../evaluation/protocol-v5.json) records source and schema
hashes, projection rules, prompts, models, and budgets. Its SHA-256 is
`91adcc1f7e70d6793cc4a9a83f68396177385896789fe5dcb74b907f788b005b`.
The prompt SHA-256 is
`2f26e74763277a642ad5df16652a97c42693ad1fca01532a90d369652768f7c6`.
All methods and models use the same extraction, chronology, report schema,
three-query budget, and decoding settings. V5 changes these parts together.

Local disk traces and genuine offline LangSmith SDK evaluation are the intended
integration. No account, credential, hosted project, upload destination, server,
or deployment is required. Hosted LangSmith is outside scope and is not a
release blocker.

### Reporting-only ablation

A replay of the eight saved v4 suite-v3 outputs replaced only observations with
selected-record projection. Findings, statuses, citations, selections, histories,
and inference timings stayed identical. This made no inference calls and is not
new v5 model evidence. Strict annotation failures fell from 31 to 17 of 32.

| Earlier group | Original support | Reporting-only projected support |
| --- | --- | --- |
| Qwen adaptive | 12.5% | 62.5% |
| Qwen fixed | 0% | 0% |
| Gemma adaptive | 0% | 62.5% |
| Mistral adaptive | 0% | 62.5% |

The saved artifact is `local-results/reporting-ablation-v4.json`, SHA-256
`43e3caec1b8a4e617c1c190f5aab0c3a68f80ced7c0ea6a75446af259426e67d`.
This isolates a mechanical extraction benefit. It does not show improved model
reasoning, query planning, or citation selection.

### Actual exposed-case Qwen regression

Four real v5 investigations completed on the two exposed v3 cases. The offline
SDK replay verified all four outputs and produced 88 feedback items with
uploads and new inference disabled. Actual inference traces contain nine model
spans and nine tool spans. Saved metrics and feedback recomputed exactly.

| Qwen adaptive | V4 actual | V4 reporting-only projection | V5 actual |
| --- | --- | --- | --- |
| Mean exact support | 12.5% | 62.5% | 75% |
| Mean recall | 87.5% | 87.5% | 75% |
| Mean status accuracy | 75% | 75% | 75% |

V5 fixed-search mean support remained 0% and recall remained 37.5%. Adaptive
v5 averaged 1.5 queries and 95.34 seconds; fixed averaged three queries and
38.73 seconds. Higher support primarily reflects extracted fields. It does not
establish a temporal reasoning fix. The adaptive development report still
refuted missing caller history while saying it could not be verified. Another
finish decision contained a query and said it would execute it, but returned
`action=finish`. The graph honored that action and left the later denied request
unretrieved. These failures remain visible.

Regression raw results SHA-256:
`c02f6f7f2c01e770146aa33c1c5fdfd4e7518c635395a2feb77ded9610220f07`.
Offline SDK artifact SHA-256:
`7e74fd9bf06dc0c1cac5da41f8257db72938b59156697ac85fabd1532440bff8`.

### Fresh comparison and CLI validation

Eight real investigations completed on the fresh v4 suite. There was one run
per model, method, and case cell. Each group below contains two cases, one per
split. Precision was 100% in every group. The unchanged scorer and frozen
annotations recomputed exactly. The numeric results and hashes are saved in
[results-v5.json](../evaluation/results-v5.json).

| Model and method | Mean recall | Mean exact support | Mean status accuracy | Strict annotation failures | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 87.5% | 62.5% | 87.5% | 3/8 | 2 | 4 | 110.83 |
| Qwen fixed | 50% | 25% | 50% | 6/8 | 3 | 1 | 34.88 |
| Gemma adaptive | 100% | 75% | 100% | 2/8 | 3 | 4 | 138.16 |
| Mistral adaptive | 62.5% | 37.5% | 62.5% | 5/8 | 3 | 4 | 80.13 |

The split rows remain separate in the numeric artifact. Qwen adaptive retrieved
all four relevant development records, with 75% support and 100% status
accuracy. On the held-out case it retrieved three of four relevant records,
with 50% support and 75% status accuracy. It again refuted missing caller
history while saying that history could not be verified. Its correct ordering
of the development case across midnight does not establish a general temporal
reasoning fix. These cases are now exposed for future development.

Sixteen of 32 fresh findings failed strict annotations. Every failure included
a missing required citation. Eight also had a status mismatch, and 12 lacked
required field observations; these counts overlap. Required facts from
unselected or unretrieved events remain missing. All emitted projected facts
resolved exactly, but exact values do not verify finding meaning. This failure
count is not a count of proven hallucinations. The sample is too small for a
model ranking or a reliability claim.

Fresh inference traces contain 26 model spans and 22 tool spans. The genuine
offline SDK replay evaluated all eight outputs and produced 176 feedback items,
with uploads and new inference disabled. The Qwen weight digest matches the
preserved v4 baseline. Effective digests were constant within each model's
batch. All frozen source, schema, prompt, and manifest hashes matched after
the runs. No source or prompt changes were made during the comparison.

Fresh raw results SHA-256:
`81b39950761798f8d49cef49555338d648695918670c7c015cd3b5641e71744f`.
Offline SDK artifact SHA-256:
`c4b87252c549f3e2ae3318ea485f3817d87474defbfc6592a123c3745c3a26a2`.

The real CLI demo used `dev-midnight-role-change` from the same manifest. It
completed in 120.52 seconds with four model calls and two queries. It selected
all four relevant events and emitted 113 exact observations. Precision, recall,
and status accuracy were 100%; strict annotated support was 75%. This separate
demonstration is not an additional benchmark cell. Its saved raw artifact is
`local-results/demo-v5.json`, SHA-256
`3c43cfa0d2842afedae2252cb058d9795deee3e4b8e44447d687a3654bb59a16`.

This increment made 13 actual local investigations in total: four exposed-case
regressions, eight fresh comparisons, and one demo. Their trace trees contain
39 model spans and 33 tool spans. The 12 comparison outputs received 264 real
offline SDK feedback items. Raw logs, model responses, and trace trees remain
in ignored local files with mode `0600`. Only the synthetic fixtures, numeric
summaries, protocol fingerprints, and artifact hashes are versioned. Ollama had
no loaded models after the final demo.

Local verification passed Ruff lint, formatting, and all 292 tests. Tests use
clearly separated mocks where needed; capability evidence above comes from
actual Ollama calls. Exact-commit CI is available in the repository
[Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

### Remaining release checks

- Improve finding-specific citation selection without adding citations from
  annotations or repairing failed model decisions after the fact.
- Distinguish missing evidence from refutation, and retain contradictory
  statuses, narrative, and unused-query failures as evidence.
- Test premature finish decisions and temporal reasoning on more independent
  cases, with repeated runs and manual semantic review.
- Keep reporting gains separate from retrieval, planning, and reasoning gains.
  Local SDK evaluation is complete; hosted credentials are not a blocker.

## October 14: protocol v4 and suite v3

The October 14 source defined `tracetrail-v4`. Its planner receives an inventory of
observed candidate filters and actual attempted query scopes. The model still
chooses its queries. The inventory does not supply answer annotations or force
a search. The prompt distinguishes use of a caller key from use of a returned
temporary key, and use of a key from the event that issued it. It also asks the
model to consider changed source addresses and context outside a one-hour
window. Pagination and every follow-up query share the three-query budget.

All four earlier cases have now been inspected. Their original development and
held-out labels remain in the preserved artifacts. They are exposed cases for
future protocol changes and cannot provide an untouched held-out test of v4.
Their outputs and failures remain available; they are not replaced by later
results.

The new frozen suite is `tracetrail-synthetic-v3`, in
`evaluation/cases-v3.json`. It contains one development case,
`dev-caller-and-child-pivot`, and one held-out case,
`heldout-issued-key-chain`. Its manifest SHA-256 is
`6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d`.
The manifest and source fixture hashes were checked before the v4 comparison.
The fixture files, annotations, and earlier suites remain separate.

V4 uses a 3,200-token output allowance for every model and method. Its prompt
allows up to 32 field observations, and its schema accepts up to 40. The
query budget remains three. V4 changes instructions, query capabilities, and
output allowance together. Any difference from v3 therefore has several
possible causes and cannot isolate the effect of the coverage inventory.

The frozen protocol is recorded in [protocol-v4.json](../evaluation/protocol-v4.json).
Its file SHA-256 is
`2ef24248b2bcc5607444dbb200139f90dc8aa356e3400e0b359daa5f723125b1`.
The frozen prompt SHA-256 is
`1592e44d335c044e5f06b6ddfc0a0fbdb62431b42adee86e5f0240811ab37db2`.
The file records the source, schemas, tool-query schema, model tags, manifest
hashes, decoding settings, and budgets used by the comparison.

Final local source verification passed Ruff checks, formatting, and all 220
tests. CI status tied to each commit is available in the
repository [Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

The local SDK evaluation uses saved inference outputs with
`upload_results=False` and a client transport that blocks API requests. It does
not run a second model or create a hosted experiment. No hosted LangSmith UI or
licensed local server is configured. See [the evaluation guide](../evaluation/README.md)
for the comparison contract and limits.

### Exposed-case Qwen regression

All eight v4 Qwen investigations completed: adaptive and fixed search on each
of the four exposed v2 cases. There was one real inference run per cell. The
audit recomputed all saved metrics from the frozen records and verified the
offline SDK feedback against them. These are regression results. The original
held-out labels do not make those inspected cases fresh tests of v4.

| Protocol | Method | Mean precision | Mean recall | Mean exact support | Strict annotation failures | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v3, preserved | adaptive | 100.00% | 66.25% | 30.00% | 15/21 findings | 1.00 | 3.00 | 86.23 |
| v4 | adaptive | 95.00% | 60.00% | 46.67% | 11/21 findings | 1.00 | 3.00 | 103.04 |
| v3, preserved | fixed | 95.83% | 90.00% | 46.67% | 12/21 findings | 3.00 | 1.00 | 60.59 |
| v4 | fixed | 95.83% | 95.00% | 50.83% | 11/21 findings | 3.00 | 1.00 | 72.18 |

Each mean covers all four cases. Exact support is the per-case mean of findings
that pass all fixed annotation requirements. The failure column is the total
count across 21 findings per group; it is not a count of failed investigations
or proven semantic hallucinations.

V4 adaptive support increased on these exposed cases, while precision and
recall decreased and latency increased. Adaptive search still used one query
per case and missed context. The coverage gap remains. Fixed search had higher
v4 recall and exact support. This regression does not establish an adaptive
advantage, and its composite changes cannot isolate the inventory's effect.

Both v4 maintenance reports also marked persistent disruption as refuted based
on a prior `StartLogging` request. They acknowledged that `GetTrailStatus` had
`responseElements=null`. Those records do not establish the actual trail state,
so this remains a semantic error even though each report passed structural and
field-value validation. The fresh-suite review below records a further semantic
error.

The real investigation trace trees contain 16 model spans and 16 query-tool
spans. The genuine offline LangSmith SDK evaluation replayed all eight saved
outputs and produced 176 feedback items. Its artifact records
`upload_results=false` and `inference_rerun=false`, and its source hash matches
the raw results. The replay did not produce new inference. The client transport
blocks hosted API access.

The local files are `regression-v4-suite-v2.json`,
`regression-v4-suite-v2.audit-summary.json`, and
`regression-v4-suite-v2.langsmith-local.json`. They remain in ignored
`local-results/` with the earlier artifacts. Raw results SHA-256:
`e3277416799b390db76a8fced5b490c11ce19bd6d7815db045b834638f43da11`.
Offline SDK artifact SHA-256:
`a2c6d4195438a023e402a7f92f6bd7ac6eb2f6281f3374d441d6a13bc755673e`.

### Fresh v3 suite with frozen protocol v4

All eight investigations completed with valid report structure and field
observations: three adaptive models on two cases, plus the fixed-search Qwen
control. The source, schema, protocol, prompt, and fixture hashes matched the
frozen comparison. There was one actual local inference run per cell.

| Model | Method | Mean precision | Mean recall | Mean exact support | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 100.00% | 87.50% | 12.50% | 2.00 | 4.00 | 147.27 |
| `qwen3.8:27b-q4_K_M` | fixed | 58.33% | 37.50% | 0.00% | 3.00 | 1.00 | 70.54 |
| `gemma4:31b-it-q4_K_M` | adaptive | 100.00% | 100.00% | 0.00% | 3.00 | 4.00 | 165.19 |
| `mistral-small3.2:24b` | adaptive | 100.00% | 100.00% | 0.00% | 3.00 | 4.00 | 109.34 |

The splits remain separate below. Each split contains only one case, with one
inference run per model and method. Precision and recall are shown as P/R.

| Model | Method | Development P/R | Development exact support | Held-out P/R | Held-out exact support |
| --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 75.00% | 25.00% |
| `qwen3.8:27b-q4_K_M` | fixed | 50.00% / 25.00% | 0.00% | 66.67% / 50.00% | 0.00% |
| `gemma4:31b-it-q4_K_M` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 100.00% | 0.00% |
| `mistral-small3.2:24b` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 100.00% | 0.00% |

Adaptive search retrieved more relevant evidence than the frozen fixed-search
Qwen control on these two cases. Report support remained weak: 31 of 32
findings failed strict annotation requirements, mostly because of omitted
required fields or citations, with some wrong statuses. This is not a finding
of 31 semantic hallucinations. Gemma and Mistral had correct fixed status labels
for all claims, but their fields and citations did not meet the complete support
contract. Correct labels and high recall did not establish supported reports.

Human review of the Qwen development report confirmed that it recovered all
four relevant records and emitted 15 exact observations. It still refuted the
caller timing claim incorrectly: `AssumeRole` occurred 3.5 hours after
`GetCallerIdentity`, so the claim that it occurred more than one hour later was
supported. The fixed control retrieved one relevant record and selected a
noise record, giving 50.00% precision and 25.00% recall on that case. This review
shows why exact observed fields need correct reasoning and complete support.

The Qwen held-out investigation stopped after two queries and missed the later
denied `DeleteBucket` request. Its 75.00% recall left that sensitive activity
outside the returned evidence, despite an observed temporary-key link that
could support a further pivot.

These two cases do not establish a model winner, broad adaptive advantage, or
production reliability. The exposed-case coverage gap also remains. The v3
suite was frozen before these v4 runs; its outputs have now been inspected and
are exposed for future changes. No prompt or fixture changes were made during
the frozen comparison.

The fresh investigation trace trees contain 26 real model spans and 22 query-tool
spans. The genuine local LangSmith SDK evaluation replayed all eight outputs and
produced 176 feedback items. The saved source hash, recomputed metrics, and SDK
feedback matched. `upload_results=false` and `inference_rerun=false` remain
explicit in the artifact. No hosted trace or experiment was created.

The local raw result is `comparison-v4-suite-v3.json`, with SHA-256
`d87bd8c0ee3760c5f63b468a62db65cf9533ac71ab8251d997f1716b05f11c5e`.
The local SDK artifact is `comparison-v4-suite-v3.langsmith-local.json`, with
SHA-256 `9872f96272d9aff383b3af1ab6781ea03bf3a9317ac9c8fe22a23a3a041f7ee5`.
Versioned numeric results, including every split and cell, are in
[results-v4.json](../evaluation/results-v4.json). Raw records, responses, and
trace trees remain in ignored private local files.

### Actual CLI demonstration and validation totals

The CLI demonstration completed with exit code 0 using real local Qwen
inference. It took 158.14 seconds, made four model calls and two query calls,
and retrieved all four relevant records. Precision and recall were 100.00%,
while exact support was 0.00%. Completion confirms the CLI execution path; it
does not establish report correctness. Its saved file is
`local-results/demo-v4.json`, with SHA-256
`645606a3e56c6a1ea0bad8f24d9470af07abd53c37678526dd1333c96bc18269`.

October 14 validation recorded 17 actual investigations: eight exposed-case
regression runs, eight fresh-suite runs, and this CLI demonstration. Their trace
trees contain 46 real model spans and 40 query-tool spans. Offline SDK evaluation
replayed the 16 comparison outputs and produced 352 feedback items. These counts
exclude the preserved October 13 runs and their earlier SDK evaluations.

## October 13 actual model runs

Development probe `local-results/probe-v1.json` used the real Qwen model. The adaptive report reached the 2,400-token output limit and failed parsing. The fixed report was invalid because it represented absent `errorCode` fields as null observations. The evidence and raw outputs are retained. These failures are separate from later comparisons.

The development comparison in `local-results/development-v2.json` recorded eight real runs. Four reports were valid and four were invalid. The offline LangSmith SDK evaluated all eight with uploads disabled. Earlier trace JSON omitted nested spans because the SDK excludes `child_runs` by default; actual model and tool histories remain in those files. Later protocols use a recursive trace serializer.

The citation format supplied to models was then changed to short local aliases. Each report alias resolves to the original file hash and record index. The final stored report uses full citations. This change reduces output length and does not relax field or citation validation.

The measured October 13 protocol was `tracetrail-v3`. The first real Qwen adaptive run completed with no validation errors. Its local trace has 3 model spans and 1 query-tool span. The observation schema distinguishes absent fields from fields with a JSON null. The October 13 comparison used the corrected `tracetrail-synthetic-v2` suite with the same frozen `tracetrail-v3` prompt and budgets. The older v1 comparison was stopped while waiting for the model lock; its 13 completed cell records remain intact, and it is not a complete benchmark. No prompt changes were made from held-out outputs during that comparison. All 16 corrected-suite investigations completed with valid reports: three models across four cases, plus a Qwen fixed-search control for each case. The actual local trace trees contain 46 model spans and 34 query-tool spans. The offline LangSmith SDK evaluated all 16 saved outputs and produced 352 feedback items with uploads disabled. These counts were verified from the saved JSON, including matching source hashes. This was a working private first increment, not a public release. Raw model outputs, logs, and traces stay in the ignored local results directory.

## October 13 frozen comparison results

One run was recorded per model, method, and case. Each group has four cases:
two development and two held out. Means below include every final-suite run.
The October 13 reports passed structural and field-value validation; this does not
mean every conclusion passed the stricter evidence-support annotations.

| Model | Method | Valid reports | Mean precision | Mean recall | Mean annotation support | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 4/4 | 100.0% | 66.2% | 30.0% | 1.00 | 86.2 |
| `qwen3.8:27b-q4_K_M` | fixed | 4/4 | 95.8% | 90.0% | 46.7% | 3.00 | 60.6 |
| `gemma4:31b-it-q4_K_M` | adaptive | 4/4 | 100.0% | 78.8% | 42.5% | 1.75 | 104.4 |
| `mistral-small3.2:24b` | adaptive | 4/4 | 86.7% | 82.5% | 55.8% | 2.75 | 85.5 |

Annotation support is a per-case mean of fixed propositions that pass all
status, citation, and field requirements. It does not score free prose.
Qwen's adaptive flow used one follow-up query per case and missed context.
The same-model fixed search retrieved more relevant context and had higher
annotation support here. This small suite does not establish a model winner
or prove that adaptive investigation improves quality.

Development and held-out support remain separate:

| Model | Method | Development support (2 cases) | Held-out support (2 cases) |
| --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 26.7% | 33.3% |
| `qwen3.8:27b-q4_K_M` | fixed | 26.7% | 66.7% |
| `gemma4:31b-it-q4_K_M` | adaptive | 26.7% | 58.3% |
| `mistral-small3.2:24b` | adaptive | 45.0% | 66.7% |

Raw reports, model outputs, query transcripts, and SDK trace trees remain in
ignored `local-results/` files with `0600` permissions. They were not pushed.
The local files are `comparison-v3-suite-v2.json`,
`comparison-v3-suite-v2.summary.json`, and
`comparison-v3-suite-v2.langsmith-local.json`.

Result bytes SHA-256: `2ddeddc0ccfa5bfed5808272e9b0a47c1f70b3384d7f5d4bbc20b7aa3f2c7d27`.

Frozen prompt SHA-256: `130be495ef3ec09a4188db8e7c7e29d173003b70ce677b335cb25e4c1451683a`.

## CloudTrail fixture review

Independent review against official AWS documentation found incorrect STS read-only flags, credential issuance dates, and a read-only GetTrailStatus response in v1. The separate v2 suite corrects these fields. Its maintenance hypotheses keep trail state uncertain, since ordinary CloudTrail logs omit that API response. V1 fixtures, annotations, hashes, and results remain intact. These corrections came from AWS documentation, not held-out model outputs. See [the evidence guide](cloudtrail.md).

The v2 manifest hash is `c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446`.

## Release checks still open

- Inspect actual model failures and compare held-out performance without changing the frozen suite or prompt in response to held-out results.
- Expand independently authored cases and human evidence-support review before making a reliability claim.
- Evaluate response stability with repeated runs. One run per cell does not measure variance.
- Inspect free-text limitations for unsupported language. Automated support scoring applies to fixed propositions and exact field observations.
- Add licensed public simulation data only after license and privacy checks. Label it as simulation.
- Improve large-file performance and evidence selection for records that exceed the model prompt budget.
- Broader release review remains separate from CI. Lint, formatting, and all 147 tests passed for the October 13 source increment. Final local v4 source verification passed Ruff checks, formatting, and all 220 tests. CI status tied to each commit is available in the repository [Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

Local disk traces and offline LangSmith SDK evaluation are the intended integration. Hosted and self-hosted platform UI deployments are outside this local-only project. No credential, server, or upload setup is needed.

## Support metric interpretation

The `unsupported_claims` counter reports failures of the strict field and citation annotations. A missing required observation or citation can fail this check even when the status label is correct. It is not a count of proven semantic hallucinations. The scorer does not evaluate planner reasons or narrative limitations. Development-only human review found incomplete search windows, premature finishes, and language that overstated what an absent API error establishes. These remain release risks.
