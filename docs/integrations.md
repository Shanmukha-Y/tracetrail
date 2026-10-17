# Local model, graph, and evaluation integrations

TraceTrail uses LangChain model and tool interfaces, a LangGraph investigation,
and the LangSmith Python SDK for local evaluation. Ollama inference, CloudTrail
records, execution traces, and evaluation results stay on the local computer.
TraceTrail does not upload to LangSmith or require a LangSmith account or key.
Local trace files and offline SDK evaluation are the project's intended
LangSmith integration. Hosted tracing and a server UI are outside its scope.

## Verified package versions

The installed package metadata, signatures, version-tagged implementations,
and current official guides were checked again on 2026-10-17. Installed
versions match `uv.lock`. Every active dependency requirement of the packages
below is satisfied in the Python 3.11 environment; no upgrade was performed.
These are the relevant declared constraints, not a claim that the pins are the
newest available releases:

| Package | Version | Relevant dependency constraints |
| --- | --- | --- |
| [langchain](https://pypi.org/project/langchain/1.4.5/) | 1.4.5 | langchain-core >=1.6.10,<2; langgraph >=1.2.11,<1.3; pydantic >=2.7.4,<3 |
| [langchain-core](https://pypi.org/project/langchain-core/1.6.10/) | 1.6.10 | langsmith >=0.3.45,<1; pydantic >=2.7.4,<3 |
| [langchain-ollama](https://pypi.org/project/langchain-ollama/1.1.0/) | 1.1.0 | langchain-core >=1.2.21,<2; ollama >=0.6.1,<1 |
| [langgraph](https://pypi.org/project/langgraph/1.2.15/) | 1.2.15 | langchain-core >=1.4.7,<2; langgraph-checkpoint >=4.3,<5; pydantic >=2.7.4 |
| [langgraph-checkpoint](https://pypi.org/project/langgraph-checkpoint/4.3.0/) | 4.3.0 | langchain-core >=0.2.38 |
| [langsmith](https://pypi.org/project/langsmith/0.14.8/) | 0.14.8 | pydantic >=2,<3; Python >=3.10 |
| [ollama](https://pypi.org/project/ollama/0.6.3/) | 0.6.3 | pydantic >=2.9 |
| [pydantic](https://pypi.org/project/pydantic/2.14.1/) | 2.14.1 | Python >=3.10 |

The tested runtime uses Python 3.11. Compatible metadata does not prove model
quality. The stored inference results and tests provide separate evidence.

## LangChain and Ollama

`ChatOllama` is provided by `langchain-ollama`. The integration supports structured
output and tool calls. TraceTrail uses `with_structured_output` with a Pydantic
schema, `method="json_schema"`, and `include_raw=True`. This preserves the actual
response and any parsing error. The model must still supply valid evidence.
See the [official ChatOllama guide](https://docs.langchain.com/oss/python/integrations/chat/ollama)
and the [pinned implementation](https://github.com/langchain-ai/langchain/blob/langchain-ollama%3D%3D1.1.0/libs/partners/ollama/langchain_ollama/chat_models.py).

The pinned method binds the Pydantic JSON schema as Ollama's `format`, then
validates the response with a Pydantic parser. With `include_raw=True`, its
result contains `raw`, `parsed`, and `parsing_error`. The parser-error capture
does not call the model again. TraceTrail rejects a missing parsed response or
parsing error and preserves the original output. JSON format and reference
validation still do not establish semantic correctness.

The configured Ollama endpoint is `http://127.0.0.1:11434`. TraceTrail checks that
each model uses installed local weights. It loads models in sequence. It does
not use a hosted model provider. Model names, settings, prompts, tools, cases,
and investigation budgets are recorded so comparisons can use the same inputs.

## LangGraph

The investigation uses `StateGraph`, state fields, nodes, and conditional edges.
The graph is compiled before invocation. Query and model-call limits bound its
loop. Errors and incomplete investigations remain in the output. The official
[Graph API guide](https://docs.langchain.com/oss/python/langgraph/graph-api)
describes this state and node interface.

The graph's `TypedDict` state does not replace explicit validation of a model
decision. State keys overwrite by default unless a reducer is declared. V7
retains the current decision separately from its history. The explicit
`recursion_limit=12` is a top-level invocation config key; it bounds graph
supersteps, not evidence queries or elapsed time. Application query and model
budgets remain separate. See the official
[recursion-limit contract](https://docs.langchain.com/oss/python/langgraph/graph-api#recursion-limit).

## V7 planning contract

V7 adds `claim-ledger-and-explicit-pivot-choice-v1` in
[`planning.py`](../src/tracetrail/planning.py). Before choosing an action, the
model supplies one ledger entry for every requested claim: returned evidence
references, an `open_question`, candidate IDs, and actual query attempt IDs.
These fields record the model's assessment. Empty questions and reference
lists do not certify that a claim has been resolved.

The catalog reads only returned evidence and actual query history. Candidate
entries include source citations and field paths, the filter's meaning, and
whether that query filter is supported locally. A supported filter does not
promise a matching record. `searched` and `has_successful_scoped_attempt` mean
that a query containing the exact filter succeeded under its recorded AND
filters, time bounds, and page. `has_successful_unbounded_first_page` excludes
additional and time filters but still describes one bounded page. None of
these flags establishes exhaustive coverage of an identity or incident.

For `query_events`, the model chooses exactly one source: a `candidate_id`, a
`continuation_id`, or a custom `query`. Selecting a candidate executes its exact
observed filter with limit 20. A continuation retains its originating query
scope and page limit. A custom query retains the model's validated fields;
its limit may be below the maximum. Materialization never chooses a replacement
filter, combines candidates, or performs an additional search. `get_event`
requires an identifier and excludes query-source arguments.

Every decision must explicitly include `candidate_id`, `continuation_id`,
`query`, and `identifier`. These four branch fields are required and nullable:
an unused field must be JSON null, not omitted. `dispositions` is also a
required array. Query and event-lookup actions supply an empty array. Schema
validation rejects omissions; code does not infer a choice from an absent
branch field.

A `finish` decision cannot also request a tool. It accounts for every visible
candidate and pending continuation with model-authored dispositions:
`deferred`, `not_relevant`, or `tested_under_recorded_scope`. Grouping IDs is
allowed. A tested disposition requires an actual successful matching query
attempt; a pending continuation cannot be called tested. A scoped attempt
may still omit evidence outside its filters or page. The capped catalog can
also omit candidates, and its truncation remains visible.

For finish, all four branch fields are null. The catalog supplies
`finish_accounting_ids`, the exact list of its visible candidate and pending
continuation IDs. This includes candidates already queried. Every listed ID
must occur exactly once in `dispositions.pivot_ids`; grouping is allowed, but
omission or repetition is invalid. The list does not assign dispositions or
select another query. Already queried scope does not imply complete coverage.

Early finish with unused queries is allowed. The validator checks ledger
coverage, known references and IDs, duplicates, branch arguments, budget
availability, and the recorded query behind a tested disposition. It does not
decide whether a candidate matters, a gap is closed, a deferral is justified,
or the model's rationale is true. Runtime code reads no answer annotations,
forces no query sequence, and repairs no finding or status. The fixed-search
control retains its original queries and does not acquire a model planner.

`decision_history`, original `model_history`, actual `tool_history`, and
`stop_reason` preserve the process. An invalid planning decision stops further
searches and is recorded as a failure; no retry or substituted query occurs.
The graph can still make its existing final reporting call. If that report's
selection and links validate, it can contain exact projected facts and ordinary
unchanged scorer metrics. The investigation remains `invalid` because its
planning process failed. If reporting itself fails to produce an analysis,
the investigation is `failed`. A valid report does not erase an invalid plan,
and a scorer value does not certify process validity.

The bounds remain three evidence queries, at most four model calls, and 3,200
output tokens per call. The ledger uses an existing planning call, rather than
an extra reflection call. The reporting prompt and schema, exact fact
projection, and annotation scorer retain the v6 contract described below.
Planning instructions, catalog presentation, decision schema, and validation
change together; their effect requires frozen prospective inference, not an
assumption from structural tests. See the [planning diagnosis](oct17-diagnosis.md).

## Reporting contract retained from v6

Protocol v6 asks the model for a `ReportSelection` with selected event
references, findings, and narrative limitations. Each `FindingSelection`
contains the unchanged hypothesis statement, `evidence_links`, a brief
`rationale`, `missing_evidence`, and a status. Each link names a citation,
one to six exact field paths, and a `supports`, `contradicts`, or `context`
role. A finding can contain at most six links. The wire schema forbids both
separate finding `citations` and model-supplied `observations`.

Code resolves aliases and derives each finding's public `citations` only from
its explicit links, with duplicates removed in order. It does not add other
selected records or supply missing links. Unknown or unselected citations,
unresolved field paths, duplicate links, blank rationales, and invalid gaps
produce validation errors. Supported findings require a `supports` link, and
refuted findings require a `contradicts` link. Uncertain findings require at
least one nonblank missing-evidence entry. Whole arrays can be linked by their
field path; array element indexing and absent nested paths do not resolve.
The only linkable absent fields are the four top-level API envelope fields
listed below.

These checks verify structure and source presence. They do not establish that
a declared role entails the full hypothesis. The model authors the role,
rationale, gap, and status; code does not repair those judgments. The raw wire
response remains in the history. Invalid selections do not receive projected
facts, an automatic retry, or a replacement model report.

`project_observations()` reads only the selected records that were already
returned by evidence tools, including the supplied seed. It applies generic
JSON rules equally to all methods and models. It does not query more records,
select relevant events, change statuses, or read evaluation labels. The saved
`observation_source` is `selected-record-projection-v1`. `validation_scope`
separates exact record validation from findings and narrative that are not
semantically verified.

Projection includes every supported root field in each selected JSON record.
It applies no credential redaction or field allowlist. Sensitive values present
in the input can appear in the `0600` report files and raw execution traces.
Handle those local files according to their contents; local storage does not
remove sensitive data.

Nonempty objects produce dotted field paths. Arrays remain whole typed JSON
values, and empty objects remain `{}`. Actual JSON null is preserved with
`present=true`. Missing top-level `errorCode`, `errorMessage`,
`requestParameters`, and `responseElements` receive `present=false` and
`value=null`. These four generic absence rules do not infer API success or
trail state.

Projection permits at most 2,000 observations and 1,000,000 bytes for the compact
ASCII-escaped JSON observation array. Nesting depth is at most 32, and field
paths are at most 512 characters. Empty or dotted keys in traversed objects
would create ambiguous paths and are rejected. Objects inside whole array
values retain their original keys because they are not traversed as paths.
Unknown or duplicate selections, invalid JSON values, and limit violations
reject projection. The report becomes invalid with an explicit error; the
application does not return silently truncated facts.

Chronological context sorts returned evidence by observed UTC timestamps and
records signed `seconds_from_seed`. Negative offsets precede the seed; positive
offsets follow it. Aliases stay attached to their original citations when the
presentation order changes. This derived time context supplies neither
causality nor a conclusion about a fixed hypothesis.

The unchanged model budget is three evidence queries, at most four model calls,
and 3,200 output tokens per call. Projection makes no inference call and uses
no case-specific fields or expected answers. A structurally valid report with
exact field values can still have a wrong status or unsupported narrative.
The [frozen v6 protocol](../evaluation/protocol-v6.json) records the source,
schema, prompt, and v5 suite hashes. The [v6 evaluation](../evaluation/README.md)
records 16 actual investigations and 16 offline SDK replays with 352 feedback
items. Thirteen reports completed; three invalid Mistral reports remain in the
scores. Link structure did not prevent premature stopping or incorrect
approval conclusions. The preserved v5 results describe the earlier contract
without model-authored field links.

## Local traces

`local_context()` disables automatic LangSmith tracing with
`tracing_context(enabled=False, parent=False)`. It also clears inherited
LangChain tracing callbacks and runnable configuration for the context. The
original context is restored when the call finishes. These controls apply even
when `LANGSMITH_TRACING` or `LANGCHAIN_TRACING_V2` is enabled in the shell.
The [official tracing guide](https://docs.langchain.com/langsmith/trace-without-env-vars)
documents the tracing context override.

The graph passes a real `RunCollectorCallbackHandler` to its invocation.
`local_traces` contains the captured graph, tool, and model execution spans.
These are SDK trace records saved on disk. They do not imply a remote trace or
a LangSmith UI session. Local JSON writes use an atomic replacement and file
permissions of `0600`.

The trace serializer includes `child_runs` recursively. The SDK's default
`model_dump()` excludes that field. Only artifacts with the nested `child_runs`
tree contain the full saved span hierarchy. Earlier raw artifacts retain their
actual `model_history` and `tool_history`, but their omitted nested spans cannot
be recovered from the saved JSON.

## Offline LangSmith evaluation

Run this after a local comparison:

```sh
uv run tracetrail local-evaluate local-results/comparison.json
```

The command calls the genuine SDK `evaluate()` function with local `Example`
objects, `upload_results=False`, `disable_evaluator_tracing=True`, and
`max_concurrency=0`. This offline feature is marked beta in the
[official 0.14.8 SDK source](https://github.com/langchain-ai/langsmith-sdk/blob/v0.14.8/python/langsmith/evaluation/_runner.py).

The installed signature supports all three options. Zero concurrency means
sequential evaluation. Disabling evaluator tracing suppresses evaluator spans;
it does not disable target tracing. The SDK uses local target tracing when
uploads are disabled. It still invokes the target function, so TraceTrail's
stored-output target is what prevents new inference. These flags alone are
not a transport sandbox; the blocked client and context controls below remain
necessary. The evaluator-tracing option was introduced in the official
[0.13.0 release](https://github.com/langchain-ai/langsmith-sdk/releases/tag/v0.13.0).

The target replays stored inference outputs. It does not make new model calls.
The evaluator recomputes the annotation metrics against the frozen local
fixture records. It checks evidence support, required field observations, and
expected claim status. It does not accept a citation merely because the
citation exists. The case manifest and fixture hashes must match the stored
run. The output file ends in `.langsmith-local.json` and contains real SDK
evaluation traces and feedback. Its replay timestamps describe evaluation,
while the original model execution timestamps remain in the stored result.

Evaluation selects the `case_manifest_path` recorded in the result batch. The
path must be relative to the repository root and stay under `evaluation/`.
Older batches without this field use `evaluation/cases.json`. The evaluator
does not move a historical result to a newer suite or substitute new fixture
records when the original hashes differ.

The SDK requires a client object even for offline feedback handling. TraceTrail
uses the real client with a transport that rejects every HTTP request, an empty
key, and no automatic batching. Both standard and newer API transports are
blocked. Tests also deny socket connections. Evaluation failures are retained
and reported in the local artifact.

## LangSmith SDK and platform UI

The [LangSmith SDK license](https://github.com/langchain-ai/langsmith-sdk/blob/main/LICENSE)
is MIT. The LangSmith server and web UI are separate products. The
[official self-hosting guide](https://docs.langchain.com/langsmith/self-hosted)
checked on 2026-10-13 describes self-hosting as an Enterprise add-on that
requires a license. That server is outside TraceTrail's local scope.

TraceTrail's disk traces and offline SDK evaluation work without a server,
account, API key, hosted project, or export destination. Credentials, billing,
and server setup are not requirements or release blockers for this project.
Logs, trace records, and evaluation feedback stay local.
