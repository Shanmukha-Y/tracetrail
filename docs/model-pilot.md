# Local model pilot

This pilot compares five local model deployments on two exposed synthetic
development cases. Each model uses adaptive and fixed search. Qwen remains
the reference. The [model inventory](../evaluation/model-inventory-pilot-v1.json)
and [cohort notes](model-cohort.md) identify exact weights, sizes, runners and
package settings. Parameter count is metadata, not an intelligence score.

The [frozen protocol](../evaluation/protocol-model-pilot-v1.json) pins runtime
sources, dependencies, eight schemas, prompts, model digests, case bytes and
the [semantic review rules](../evaluation/pilot-semantic-review-v1.md). The
v8 investigation prompt, planning schema, report schema, tools, scorer and
budgets stay unchanged. This study does not test a planning-schema repair.

## Reproduce the stages

Install the pinned environment with `uv sync --frozen`. The five approved
model tags must already resolve to the pinned local weights. The runner does
not download a model or change Ollama settings. It rejects version, source,
schema and model-identity drift. Stop other model sessions before starting.

```sh
uv run python -m tracetrail.pilot \
  --protocol evaluation/protocol-model-pilot-v1.json \
  --output local-results/model-pilot-reproduction.json --stage 1
uv run python -m tracetrail.pilot \
  --protocol evaluation/protocol-model-pilot-v1.json \
  --output local-results/model-pilot-reproduction.json --stage 2 --resume
uv run python -m tracetrail.pilot \
  --protocol evaluation/protocol-model-pilot-v1.json \
  --output local-results/model-pilot-reproduction.json --stage 3 --resume
```

Stage 1 runs both methods on the first case for all five models, for ten
assigned cells. Stage 2 adds the second case, for 20. Stage 3 adds a second
paired repeat only if the saved runtime and resource gate permits it, for 40.
Each expansion requires an explicit resume. `--max-runs` sets a cumulative
attempt limit within a stage. A failed attempt is retained and never retried
on resume. New experiments refuse an existing output path. Output writes are
atomic and use private file permissions.

The first ten whole-cell wall times determine expansion. Let their sum be
`S`. The 40-cell forecast is `1.2 * 4 * S`. A forecast above 5,400 seconds,
foreign loaded models, missing model identity, or incomplete required resource
measurements blocks repeat two. Scores and answer quality do not select the
run count. The 5,400-second execution limit stops new launches; an in-flight
bounded investigation can finish after it. Investigation duration and total
cell wall time are distinct. Their difference includes session overhead and
must not be labelled pure model load time.

The command returns a nonzero status when a report is invalid or the requested
experiment is incomplete. Inspect `attempted_all_target_cells`, the exact
cell list, failures and stop reasons. A nonzero exit does not discard evidence.
Do not interpret it as permission to rerun until every cell passes.

Run `tracetrail local-evaluate` on the final saved batch to use the real
LangSmith SDK with uploads disabled. This replays outputs, recomputes the
frozen mechanical metrics and records local feedback. It makes no new model
or tool calls. It does not supply a semantic judge or hosted experiment.

The portable auditor checks saved inputs and actual trace trees, re-derives
all 21 primary counters without calling the primary scorer, and replays local
source queries. These audit replays are separate from the original model's
tool-call cost and capability evidence. It can inspect a growing ordered
prefix; require a matching SDK artifact for the final check.

```sh
uv run tracetrail local-evaluate local-results/model-pilot-reproduction.json
uv run python scripts/verify_model_pilot_v1.py \
  local-results/model-pilot-reproduction.json \
  --protocol evaluation/protocol-model-pilot-v1.json --require-sdk
```

The numeric summary exporter also checks final raw, SDK, auditor and complete
assistant-review identities before writing a new public summary. It keeps raw
model text, trace contents and source values in private local artifacts. The
public files identify exact source records and fields for the claim reviews.
Original private artifact hashes identify the measured experiment. A fresh
reproduction creates new outputs and needs new reviews bound to those outputs;
the original review sidecars cannot be reused for different cell payloads.

## What the measurements mean

Report availability, process validity, selected-event recall, exact claim
support, semantic warrant and cost are separate. Failed assignments keep their
capability denominators. An unavailable report is not a report with zero false
claims. The unchanged primary scorer checks each finding's own exact source
links and process validity. It cannot establish natural-language entailment.

The historical precision and recall fields score the report's selected records.
They are not query-retrieval recall. An invalid selection can score zero even
when tools returned useful records. `retrieved_event_count` counts source-valid
available records, including the supplied seed. The source reviews identify
missing relevant records and distinguish retrieval gaps from selection and
reasoning errors. A future protocol can freeze separate returned-record
precision and recall; this pilot keeps its existing metric contract.

Assistant source reviews check each requested claim and material prose. They
separate false definite conclusions, unsupported definite conclusions,
avoidable uncertainty, missing retrieval context and limits of the complete
source. These are assistant judgments on known cases, not independent human
validation. Reviews retain exact record and field references and disagreements.

All model and tool calls, failures and raw outputs remain in the ignored local
batch. Fixed search uses the same three seed queries for every model. Adaptive
search also makes planning calls. There is no warm-up generation, retry,
replacement report or automatic query repair. Equal application controls do
not equalize tokenizers, training, chat templates, backend runners or packaged
draft-model settings. These deployment factors limit latency comparisons.

Resource sampling observes Ollama's reported allocation bytes and the macOS
listener process tree's RSS. The recorded maxima are sampled maxima, not OS
peak memory or measured peak VRAM. RSS can count shared mappings more than
once. The two views overlap on unified memory and must never be added. Sample
counts, timing, missing reads, target-model presence and foreign-model flags
remain visible. The process lock does not control other applications.
The saved gate checks timing and recorded resource issues. It does not prove
CPU isolation or measure thermal throttling. Latencies include this sampling
instrumentation on one machine.
The measured Gemma runner's reported `size` and `size_vram` counters are much
smaller than its package bytes and process RSS. That discrepancy is unresolved;
these server counters must not be treated as actual weight residency or used
to rank memory efficiency across runners. See the
[measured resource table](model-pilot-results.md#sampled-memory).

One review-order deviation is preserved for `r1-c2-m1-adaptive`, the first
E2B adaptive KMS run. An append script applied fixed-report draft wording before
the target report was inspected. The draft remains in its private sidecar.
The returned-evidence judgments were corrected after actual target inspection
and saved before the complete source was reopened. A second assistant read
both E2B KMS reports and their actual inputs before consulting primary labels;
its eight claim judgments agreed with the final reviews. This check does not
restore blinding or supply independent human validation. No model output,
runtime, source fixture or mechanical score was changed. The public summary
identifies the retained preliminary draft by count and hash.

There are only two case clusters. Same-seed greedy repeats describe observed
execution stability, not independent task samples. Use per-case paired
differences, counts, ranges and repeat agreement. These exposed synthetic
results cannot establish generalization intervals, intelligence rankings,
a model winner or production reliability. A later held-out study needs new,
independently authored cases and a separate freeze.
