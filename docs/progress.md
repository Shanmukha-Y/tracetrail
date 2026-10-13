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

The final protocol is `tracetrail-v3`. The first real Qwen adaptive run completed with no validation errors. Its local trace has 3 model spans and 1 query-tool span. The observation schema now distinguishes absent fields from fields with a JSON null. The final comparison uses the corrected `tracetrail-synthetic-v2` suite with the same frozen `tracetrail-v3` prompt and budgets. The older v1 comparison was stopped while waiting for the model lock; its 13 completed cell records remain intact, and it is not a complete benchmark. No prompt changes were made from held-out outputs. All eight actual Qwen v2 investigations have completed with valid reports. Gemma and Mistral use the same four cases next. Full results will be recorded after the comparison completes. Raw model outputs, logs, and traces stay in the ignored local results directory.

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
- Confirm a clean remote commit and CI for that exact commit.

A full local LangSmith server and UI remain outside this increment. Official self-hosting requires an Enterprise add-on license. The application does not upload to a hosted service or configure a licensed deployment. Offline SDK evaluation and disk traces do not need an account or key.

## Support metric interpretation

The `unsupported_claims` counter reports failures of the strict field and citation annotations. A missing required observation or citation can fail this check even when the status label is correct. It is not a count of proven semantic hallucinations. The scorer does not evaluate planner reasons or narrative limitations. Development-only human review found incomplete search windows, premature finishes, and language that overstated what an absent API error establishes. These remain release risks.
