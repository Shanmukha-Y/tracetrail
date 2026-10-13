# Frozen local evaluation

The active suite is `tracetrail-synthetic-v2`, selected by `evaluation/cases-v2.json`.
Its fixtures are in `fixtures/v2/`. The v1 suite and its hashes remain available
for earlier runs. V1 includes fixture errors described in [CloudTrail semantics](../docs/cloudtrail.md).
Use v2 for new comparisons. Both suites contain two development and two held-out cases.


This suite tests investigation of a small supplied CloudTrail log window. All
accounts, identities, IP addresses, resources, and API events are invented.
The records do not describe an incident or a public attack sample. IP addresses
use documentation ranges. The fixtures use the repository's MIT license.

| Case | Split | Evidence question |
| --- | --- | --- |
| `dev-role-pivot` | Development | Link a temporary key to later actions. Test maintenance, compromise, and external transfer. |
| `dev-maintenance` | Development | Check a stop, configuration change, start, and status sequence. Keep approval separate from API facts. |
| `heldout-denied-and-missing` | Held out | Distinguish denied requests from success. Do not infer later trail state from missing records. |
| `heldout-data-access` | Held out | Link object requests to a session. Distinguish allowed and denied requests from deletion and transfer claims. |

One development record contains an instruction in a role description. It is
untrusted log data. It must not control the investigator.

`cases-v2.json` defines the questions, fixed hypotheses, relevant event IDs, and
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
`fixtures/build_synthetic_v2.py` reproduces the current bytes from the preserved
invented v1 definitions and documented AWS field corrections. It has no model, AWS, or network calls.

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

The runner records model responses, evidence, tool history, errors, versions,
hashes, budgets, and timing. The scorer does not call a model. Constructed
annotation-perfect reports and injected tool faults in `test_evaluation.py`
are unit-test inputs. They are not model results or capability evidence.

This four-case suite is too small to establish production performance. It can
expose specific failures and support a repeatable local comparison. New data,
more independent annotations, and human review are required before broader
claims can be made.
