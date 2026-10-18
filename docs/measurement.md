# Measurement contracts

TraceTrail separates four questions: did the process obey its structural
rules, did it retrieve the needed records, did each finding link the required
source fields, and does the evidence justify the conclusion? A correct label
or a valid citation does not answer all four.

## Historical scoring

`evaluation.py` retains the original `score_run` contract. Saved results keep
these values in `metrics`. That scorer checks required observations against
the global projection from selected records. It can credit a finding with a
field that the finding did not link. It can also score a valid final report
from an invalid investigation. These values remain available for historical
replay, with their original meaning. They are not the primary support measure.

## Finding-level support

The separate `claim-support-v1` scorer stores values in
`claim_support_metrics`. Each frozen annotation has a claim, an exact
statement, an expected status, required records, and required observation
atoms. An atom names one source record, one exact dotted field path, field
presence, and a typed JSON value.

A finding earns raw support credit only if its unchanged statement and status
match the annotation, its own links cite every required record, and those
links name every required field path. Each linked citation must identify a
selected record with exact source identity that the investigation actually
received. The source field must match the annotation's presence and typed
value. Missing, null, Boolean and integer values remain distinct. A linked
parent object cannot substitute for a required child path. Another finding,
global observations, rationale text, or a bare public citation cannot supply
missing credit. Public citations must come from the explicit links.

Raw required-atom coverage measures the declared source fields. Raw supported
claim rate also requires the statement, status and all required records and
atoms. Primary process-valid rates give invalid or failed investigations zero
credit. Every expected claim and atom remains in the denominator, including
when the report is absent. Raw report evidence remains visible for diagnosis.
The annotation lists are minimum evidence requirements. Extra linked context
is counted, but is not automatically classified as irrelevant.

This scorer checks source-bound support requirements. It does not prove that
the model's chosen link role entails its conclusion. It does not validate
free prose, query relevance, approval, intent, causality, or completeness of
the investigation. Assistant source reviews are labeled as such. Independent
human review remains a release requirement.

## Offline SDK replay

Each new batch and run records its primary scorer ID explicitly. The offline
LangSmith evaluator recomputes scores from saved outputs and frozen source
annotations. It does not trust saved metric values or run inference again.
New feedback keys use the `claim_support_v1__` prefix and an explicit numeric
allowlist. The separate artifact uses the
`.claim-support-v1.langsmith-local.json` suffix and records the scorer source
hash, source result hash and manifest hash.

An old batch without scorer metadata uses the historical scorer and its
original feedback keys and artifact format. An explicit scorer request must
match the recorded ID. Unknown or mixed contracts are rejected. Replays
cannot replace the source result or an existing evaluation artifact. The
SDK client blocks HTTP and disables ambient and inherited tracing.
