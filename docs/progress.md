# Progress and release checks

The repository stays private until the release checks pass. Workflow Sentinel is complete and was not changed.

## Implemented

- Local CloudTrail JSON ingestion with exact record citations, indexed queries, and explicit budgets.
- LangChain Ollama structured output and read-only evidence tools.
- A stateful LangGraph investigation with bounded query and model calls.
- Observed field validation, hypothesis status, cited timelines, raw failure retention, and private local files.
- Three installed local model tags, sequential inference, raw remote-routing checks, proxy and redirect guards, and no ambient credential use.
- Real local graph traces and genuine offline LangSmith SDK evaluation with blocked HTTP.
- Preserved four-case synthetic suites and a new two-case v3 suite with field support annotations.
- CI for lint, formatting, and tests without inference or hosted tracing.

## October 14: protocol v4 and suite v3

The source now defines `tracetrail-v4`. Its planner receives an inventory of
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

A full local LangSmith server and UI remain outside this increment. Official self-hosting requires an Enterprise add-on license. The application does not upload to a hosted service or configure a licensed deployment. Offline SDK evaluation and disk traces do not need an account or key.

## Support metric interpretation

The `unsupported_claims` counter reports failures of the strict field and citation annotations. A missing required observation or citation can fail this check even when the status label is correct. It is not a count of proven semantic hallucinations. The scorer does not evaluate planner reasons or narrative limitations. Development-only human review found incomplete search windows, premature finishes, and language that overstated what an absent API error establishes. These remain release risks.
