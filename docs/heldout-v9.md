# First-use Qwen method check

This bounded study extends the exposed five-model pilot with two new synthetic
CloudTrail cases. Qwen is the reference model. Each case receives adaptive and
fixed search, then one predeclared paired repeat. The cases deliberately put relevant context outside the fixed control's
one-hour seed window. They are a constructed scope stress/control pair. The
eight assignments form
two case clusters. They do not represent eight independent incident samples.

The current v8 application prompt, tool semantics, report and planning schemas,
three-query budget, four-call maximum, and claim-support-v1 scorer stay fixed.
The study changes the evaluation cases and execution schedule. It does not
compare a prompt repair or establish a new model ranking. The five-model,
eight-case proposal in [the larger study plan](benchmark-plan.md) remains
separate from this smaller check.

## Before inference

The new cases are held out from model-driven prompt and runtime development.
An assistant authors them, and a separate source review checks the annotations
and query reachability before the protocol freeze. This is not independent
human validation. The investigators receive only the seed, question, and
hypotheses. Answer annotations and source-review rules are evaluation inputs
and are not supplied to the model.

The protocol pins runtime source, the study script and audit helpers,
dependencies and installed versions, prompt and schema hashes, case and
fixture bytes, the review rubric, and the expected local Qwen digest. Both
methods use identical application report controls. Adaptive planning has
additional real calls, which remain part of its cost.

Method order alternates by case and repeat. Both repeats use the same frozen
greedy seed. Agreement measures observed execution stability; it does not
supply new independent cases. All eight cells are chosen before any output.
A 2,700-second accumulated whole-cell launch limit applies regardless of
scores. An already running bounded investigation can finish after that limit.
A partial batch stays partial. Failed attempts are never replaced on resume.

The prior Qwen pilot used 287.48 seconds per paired case on average when its
mean adaptive and fixed cell times are added. Four pairs suggest about
1,150 seconds, before allowance. This is only a planning estimate from exposed
data. New case inputs and fewer fast failures can increase the actual cost.

## Pre-inference source check

A separate assistant checked all fixture bytes and annotations before any
model run. The boundary case has seven records, four relevant records, four
claims and 14 required atoms. The inventory case has six records, three
relevant records, four claims and 11 required atoms. The eight assignments
therefore contain 32 claim slots, 100 required atoms and 28 relevant-event
slots. Event IDs do not overlap earlier fixtures.

Actual source queries confirmed full relevant-record reachability in three
queries for the boundary case and one for the inventory case. Fixed search
returns the seed plus one unrelated same-address record in each case. Its
returned relevant recall is 1/4 and 1/3 respectively. These are fixture
properties checked before inference, not observed model behavior. The
[fixed source-review rules](../evaluation/heldout-v9-rubric.md) explain the
API semantics, exact annotations and uncertainty limits.

## Reproduction

Use the pinned environment and installed local Qwen weights. Reserve the server after other workloads finish. The runner refuses a foreign
loaded model and never unloads another application's model. Model residency
from `/api/ps` does not establish active generation or ownership. Process and
connection checks can add time-bound evidence, but completion needs separate
coordination or observation before normal preflight. Logs, model outputs, and trace trees stay in
ignored private local files. No hosted LangSmith project or server is used.

```sh
uv sync --frozen
uv run python scripts/heldout_v9.py freeze \
  --manifest evaluation/cases-v9.json \
  --rubric evaluation/heldout-v9-rubric.md \
  --output evaluation/protocol-heldout-v9.json
uv run python scripts/heldout_v9.py run \
  --protocol evaluation/protocol-heldout-v9.json \
  --output local-results/heldout-v9-reproduction.json
uv run tracetrail local-evaluate local-results/heldout-v9-reproduction.json
uv run python scripts/report_heldout_v9.py verify \
  --protocol evaluation/protocol-heldout-v9.json \
  --raw local-results/heldout-v9-reproduction.json \
  --sdk local-results/heldout-v9-reproduction.claim-support-v1.langsmith-local.json \
  --output local-results/heldout-v9-reproduction.verification.json
uv run python scripts/report_heldout_v9.py summary \
  --protocol evaluation/protocol-heldout-v9.json \
  --raw local-results/heldout-v9-reproduction.json \
  --sdk local-results/heldout-v9-reproduction.claim-support-v1.langsmith-local.json \
  --output evaluation/results-heldout-v9-reproduction.json
```

A committed protocol already exists after the original freeze. Reproduction
uses that file. The freeze command refuses to replace it; use a new filename
only when preparing a separately labelled study. Source or dependency changes
invalidate the original freeze instead of silently selecting new controls.

Use `run --resume` only on the same saved batch and protocol. `--max-runs N`
sets a cumulative launch count, which can save a bounded prefix. Resume checks
recorded payload hashes and never retries an attempted cell. A nonzero exit
can mean that all assignments finished with retained invalid reports. Inspect
coverage, cell status, and failures rather than rerunning until scores improve.

Offline LangSmith evaluation replays saved outputs with uploads disabled. It
makes no new inference. The stored-artifact verifier checks source records,
actual wire inputs, query transcripts, trace counts, model identity, and
independently derived primary counters. Audit query replays are separate from
the original model's tool cost and behavior.

## Resource reporting extension

Use `scripts/report_heldout_v9.py` for new verification and summary exports.
The original `scripts/heldout_v9.py` is pinned by the study freeze and remains
unchanged. Its historical verification and export commands remain available.
The extension calls those frozen checks and preserves their exact model
metrics, assignments, failures, latencies and denominators. It adds resource
reporting after verification and records a separate reporter version and
source hash, alongside the original protocol and runner hashes.

This is a reporting change after the study freeze, before any v9 inference.
It does not replace the frozen protocol or claim that the new exporter was
part of the original freeze. The original protocol SHA-256 remains
`ccbb1bc19e18d09390f7eb2d2e75bb7b27c51294e4327a909d6d814e93bccc1d`.
Every original pinned file must still pass its existing hash check. The new
reporter is outside the frozen runtime source inventory.

Artifact consistency and measurement eligibility are separate fields. Truthful
partial sampling, unavailable metadata or observed foreign models can pass
artifact verification. Exports must retain those states rather than present
verification as clean resource conditions. Each row records sampling status,
observed sample and read-gap counts, numeric error counts, target-model
observations, foreign-model flags and whether the sample limit was reached.
Missing observations remain unknown; they are not replaced with a claim of
zero errors or no contention. `sample_count=0` for unavailable data means no
stored samples, not measured zero workload. Sampling times include the observed maximum gap
when available. No new gap cutoff or latency exclusion is applied.

Eligibility describes only the recorded sampling checks. Even a clean row does
not prove exclusive hardware use, absence of activity between samples, true
peak memory, or pure inference latency. The separate memory views overlap on
unified memory and must not be added. Resource flags never change capability
scores, process validity, costs or which assignments remain in the report.

A zero-row prefix is explicitly `not_evaluated`, with measurement eligibility
false and all eight planned assignments still visible. A partial private audit
is not a completed benchmark. Public summary export still requires all eight
attempted assignments and the genuine matching offline SDK replay. Reporting
commands perform no inference or SDK evaluation; their local source-query
replays remain audit work outside the original agent tool counts.

## Interpretation

Report selected-record precision and recall separately from source-valid
returned-record coverage, including the supplied seed. A tool can return useful
records that a report omits. Keep process validity, exact declared support,
semantic warrant, and unavailable reports separate. Failed assignments retain
their original claim and evidence denominators.

Any source-aware prose review must name the returned evidence available to that
run. It must distinguish source-limited uncertainty from missed retrieval and
unsupported definite conclusions. Such reviews are assistant assessments unless
an independent human checks them. Exact typed field matches do not prove
natural-language entailment.

After first inference and inspection, these cases become exposed for future
runtime changes. Results can describe only this small constructed sample under
these controls. They cannot establish production incident-response reliability,
a broad adaptive advantage, or generalization across CloudTrail incidents.
