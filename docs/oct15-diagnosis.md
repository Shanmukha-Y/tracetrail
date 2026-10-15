# Evidence reporting and deterministic projection

This is the review recorded before protocol v5 was implemented and evaluated.
Its recommendations are not implementation guarantees. The frozen v5 policy
projects all supported fields in selected records, with no credential redaction.
Sensitive values present in input can therefore appear in local reports and
raw traces, which use file mode `0600`. See the current
[integration contract](integrations.md) and [measured progress](progress.md).

The next reporting boundary should keep investigation and interpretation with
the model, while extracting exact observed fields mechanically from the
model-selected records. This is legitimate evidence processing when it uses
only returned data and never supplies an investigative answer. It should be
described as system-extracted observations, not improved model extraction
accuracy or verified semantic reasoning.

## What the v4 evidence shows

This review uses the preserved local files
`local-results/regression-v4-suite-v2.json` and
`local-results/comparison-v4-suite-v3.json`, with their frozen annotations.
All cases in both files are now exposed for future development. All source
records are synthetic. Neither artifact was changed or rerun for this review.

| Artifact | Findings | Passing all annotations | Failing only required observations | Other annotation failures |
| --- | --- | --- | --- | --- |
| Exposed v2 regression | 42 | 20 | 10 | 12 |
| Newer v3 comparison | 32 | 1 | 14 | 17 |

"Only required observations" means the saved finding's sole failure reason is
`missing_or_wrong_required_observation`. Existing observations have zero
invalid values in both artifacts. These are partitions of observed failures,
not simulated projection results or predicted future scores. A bounded generic
projector still has to demonstrate which facts it actually emits.

In the v3 comparison, Gemma and Mistral retrieve and select every annotated
relevant record and assign every fixed status correctly, but no finding passes
every field and citation requirement. They omit event names, usernames, times,
resource parameters, session names, or null-response context. Several findings
also omit a required linking citation. The development case needs 24 distinct
annotated facts, and the held-out case needs 21; these fit within v4's prompted
32-observation ceiling. The omissions are not forced by that ceiling alone.

Extraction does not solve the remaining problems. Qwen retrieves all relevant
development records but reverses the temporal statement: GetCallerIdentity at
08:30 precedes AssumeRole at 12:00 by three and a half hours, yet Qwen refutes
the claim that the latter occurred more than an hour later. In the held-out
case it stops with one query unused before investigating later temporary-key
use, leaving the existing denied DeleteBucket request unretrieved. The older
maintenance runs also infer later trail state from requests with no recorded
state response. These failures must remain visible.

## A defensible projection contract

The model continues to choose queries, relevant returned references, fixed
finding statements, statuses, and citations. After a valid model report,
projection receives only its validated selected records and a frozen generic
policy. It must not receive annotations, expected statuses, relevant-event
labels, case IDs, splits, or fixture-specific instructions. Evaluation code may
read annotations for scoring; the investigator and projector must not consume
them as answer guidance.

Apply projection consistently, not because a score failed. It must not add
records, repair citations, expand selection, change statements or statuses,
issue queries, or replace failed model reports. Preserve the original model
output and failures. An invalid reference or failed projection remains an
explicit failure, not a seed-based replacement investigation.

A generic policy can enumerate scalar leaves under supported CloudTrail
metadata, identity, request, and response roots. Field selection should follow
the input schema and product scope, not the current annotations' field list.
Preserve string, boolean, number, and explicit null types exactly. Exclude
credential secret material from report projection. Do not coerce values,
invent identity links, label API success, or manufacture derived source fields.

Absence requires a separate small, versioned schema checklist, such as standard
error and response fields. Do not invent absent-field checks from a claim or
search arbitrary nonexistent paths to fill a report. `present=false, value=null`
means only that the named path is absent from this supplied record. A present
JSON null remains `present=true`. Neither condition proves missing events,
approval, intent, API success, or later service state.
A present object or array is not absent; disclose it as non-scalar if the
projection policy omits it.

Freeze limits for depth, facts, records, value bytes, and total report bytes.
The current dotted-path resolver walks dictionaries, so arrays and keys that
contain literal dots need an explicit supported representation or disclosed
omission. Never shorten a value and present it as an exact observation.
Disclose skipped paths, budget truncation, and projection completeness within
the policy. A bounded projection is not an exhaustive statement about the logs.
Record the policy version and mark each observation's origin as system
extraction. Exact values still do not prove that a finding means what it says.

## Chronological evidence presentation

A chronological view is an observed-data transformation, independent of gold
labels. Sort parsed UTC event times with a stable tie-breaker, preserving the
original file-hash/index citations and existing alias bindings. Sort the
display, not the underlying source records. Reassigning aliases after each new
earlier event could change the meaning of older rationale text.

Such a view may help temporal interpretation; it does not guarantee it. If
later code computes intervals or relationships, identify them separately as
derived facts with their inputs and calculation. They are not raw JSON fields
and must not masquerade as source observations.

## Measurement and comparison rules

- Version the whole reporting contract, schemas, projection policy, display
  policy, prompts, budgets, and source hashes before new evaluation material.
  Removing model-authored observations changes output work and token use;
  this is a composite protocol change.
- Apply the same projection and limits to every model and to adaptive and
  fixed search. Keep fixed-search behavior frozen and record every query,
  model call, projection cost, failure, and end-to-end duration.
- Report retrieval/selection, model status and citation correctness, system
  extraction accuracy/completeness, and complete annotated support separately.
  The current scorer searches a global observation pool; richer system facts
  can raise support without showing that the model linked them to each claim.
- Keep the strict annotated score, but do not call its failure count a
  hallucination rate. Human review must still examine the claims and free
  prose. Mechanically correct observations are not semantic verification.
- An offline projection overlay on saved v4 reports can isolate reporting
  effects if labeled as a replay or ablation with no new inference. It is not
  an actual v5 model result. Preserve the original report and score alongside
  it; do not overwrite historical evidence.
- Actual v5 capability claims require actual inference under the frozen v5
  contract. Use the old cases as regressions and independently authored new
  cases for a later held-out check. Keep development and held-out results
  separate, preserve failures, and measure repeated-run variation before
  making reliability or model-ranking claims.

The reviewed raw SHA-256 values remain
`e3277416799b390db76a8fced5b490c11ce19bd6d7815db045b834638f43da11`
for the v2 regression and
`d87bd8c0ee3760c5f63b468a62db65cf9533ac71ab8251d997f1716b05f11c5e`
for the v3 comparison. This review recommends an architecture; it supplies no
new model performance result.
