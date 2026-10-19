# Next frozen study

This is a proposed follow-up, not an executed benchmark or scheduled job.
The current [pilot](model-pilot.md) uses two exposed development cases. Its
actual costs and source-reviewed failures guide a smaller study than a large
model-by-case-by-seed sweep.

Use eight new synthetic CloudTrail cases with the same five pinned local
models and both methods. One pass gives 80 assigned investigations. Before
inference, name two of those cases for one additional paired repeat across
all models and methods, for at most 100 runs. Select the repeat cases and a
runtime gate before any answers. Do not select repeats from favorable scores.
Estimate runtime from measured pilot cell costs, add an explicit allowance,
and report the estimate separately from executed work.

The completed pilot used 4,057.82 seconds of accumulated cell wall time for
40 runs. Scaling that cost mix gives 135.26 minutes for 80, or 169.08 minutes
for 100. A 20 percent allowance gives planning estimates of 162.31 and
202.89 minutes. These are forecasts, not completed benchmarks. New cases can
have larger inputs, and fewer fast failures can increase elapsed time.
Retain a prospective runtime gate rather than treating this estimate as a
guarantee. See the [actual pilot results](model-pilot-results.md).

Keep the input scope to local CloudTrail JSON. Cover credential issuance and
use in both directions, changed addresses and time windows, benign-looking
names, explicit denied operations, pagination, and records that cannot settle
approval or later resource state. Each case needs exact source-bound claim
annotations and an independently checked semantic rubric. An API denial in a
log is distinct from a query-tool failure; any injected tool failure needs its
own predeclared scenario and label. Verify reachability within the existing
budgets with local source checks before model runs, without crediting those
checks as model behavior.

If a tagged planning-action schema is developed, compare it with the current
schema on exposed development data under a separate controlled freeze. Keep
tool semantics, budgets and scorers fixed. Choose the final runtime before
creating and using the new held-out suite. Preserve the old protocol and every
failed result. Do not repair model statuses or supply missing evidence links.

Freeze source, prompts, schemas, dependencies, model digests and package
settings, decoding, cases, annotations, reviewers' rules and all denominators.
Keep selected-report precision and recall separate from new, explicitly frozen
returned-record precision and recall. Retain failure assignments, semantic
unavailability, query costs and complete latency. Count each case equally when
summarizing the eight case clusters; repeats of two cases must not silently
give those cases more weight.

Use per-case paired outcomes and observed repeat agreement. Eight constructed
cases remain a small, chosen sample. They cannot establish general model
intelligence or real-world incident-response reliability. Source reviews are
assistant assessments until an independent human reviewer checks them.

Keep Ollama sequential and loopback-only. Reuse the installed weights, local
LangChain/LangGraph execution and offline LangSmith SDK evaluation. Keep hosted
uploads disabled. Public incident samples can be a later extension after their
licence and privacy have been checked; no live AWS connection, attack execution,
remediation or SIEM deployment is part of this study.
