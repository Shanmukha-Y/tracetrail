# Progress and release checks

The repository stays private until the release checks pass. Workflow Sentinel is complete and was not changed.

## Implemented

- Local CloudTrail JSON ingestion with exact record citations, indexed queries, and explicit budgets.
- LangChain Ollama structured output and read-only evidence tools.
- A stateful LangGraph investigation with bounded query and model calls.
- Observed field validation, hypothesis status, cited timelines, raw failure retention, and private local files.
- Three installed local model tags, sequential inference, raw remote-routing checks, proxy and redirect guards, and no ambient credential use.
- Real local graph traces and genuine offline LangSmith SDK evaluation with blocked HTTP.
- A frozen synthetic suite with two development cases, two held-out cases, and field support annotations.
- CI for lint, formatting, and tests without inference or hosted tracing.

## Actual model runs

Development probe `local-results/probe-v1.json` used the real Qwen model. The adaptive report reached the 2,400-token output limit and failed parsing. The fixed report was invalid because it represented absent `errorCode` fields as null observations. The evidence and raw outputs are retained. These failures are separate from later comparisons.

The development comparison in `local-results/development-v2.json` recorded eight real runs. Four reports were valid and four were invalid. The offline LangSmith SDK evaluated all eight with uploads disabled. Earlier trace JSON omitted nested spans because the SDK excludes `child_runs` by default; actual model and tool histories remain in those files. The final protocol uses a recursive trace serializer.

The citation format supplied to models was then changed to short local aliases. Each report alias resolves to the original file hash and record index. The final stored report uses full citations. This change reduces output length and does not relax field or citation validation.

The final protocol is `tracetrail-v3`. The first real Qwen adaptive run completed with no validation errors. Its local trace has 3 model spans and 1 query-tool span. The observation schema now distinguishes absent fields from fields with a JSON null. The final comparison uses the corrected `tracetrail-synthetic-v2` suite with the same frozen `tracetrail-v3` prompt and budgets. The older v1 comparison was stopped while waiting for the model lock; its 13 completed cell records remain intact, and it is not a complete benchmark. No prompt changes were made from held-out outputs. All 16 corrected-suite investigations completed with valid reports: three models across four cases, plus a Qwen fixed-search control for each case. The actual local trace trees contain 46 model spans and 34 query-tool spans. The offline LangSmith SDK evaluated all 16 saved outputs and produced 352 feedback items with uploads disabled. These counts were verified from the saved JSON, including matching source hashes. This is a working private first increment, not a public release. Raw model outputs, logs, and traces stay in the ignored local results directory.

## Frozen comparison results

One run was recorded per model, method, and case. Each group has four cases:
two development and two held out. Means below include every final-suite run.
The final reports passed structural and field-value validation; this does not
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
- Broader release review remains separate from CI. Lint, formatting, and all 147 tests passed for the source increment; the final pushed documentation commit receives the same CI checks.

A full local LangSmith server and UI remain outside this increment. Official self-hosting requires an Enterprise add-on license. The application does not upload to a hosted service or configure a licensed deployment. Offline SDK evaluation and disk traces do not need an account or key.

## Support metric interpretation

The `unsupported_claims` counter reports failures of the strict field and citation annotations. A missing required observation or citation can fail this check even when the status label is correct. It is not a count of proven semantic hallucinations. The scorer does not evaluate planner reasons or narrative limitations. Development-only human review found incomplete search windows, premature finishes, and language that overstated what an absent API error establishes. These remain release risks.
