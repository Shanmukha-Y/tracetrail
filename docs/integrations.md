# Local model, graph, and evaluation integrations

TraceTrail uses LangChain model and tool interfaces, a LangGraph investigation,
and the LangSmith Python SDK for local evaluation. Ollama inference, CloudTrail
records, execution traces, and evaluation results stay on the local computer.
TraceTrail does not upload to LangSmith or require a LangSmith account or key.
Local trace files and offline SDK evaluation are the project's intended
LangSmith integration. Hosted tracing and a server UI are outside its scope.

## Verified package versions

The package metadata and official interfaces were checked on 2026-10-13.
`uv.lock` records the full dependency set. These direct versions satisfy each
other's declared version constraints:

| Package | Version | Relevant dependency constraints |
| --- | --- | --- |
| [langchain](https://pypi.org/project/langchain/1.4.5/) | 1.4.5 | langchain-core >=1.6.10,<2; langgraph >=1.2.11,<1.3 |
| [langchain-core](https://pypi.org/project/langchain-core/1.6.10/) | 1.6.10 | langsmith >=0.3.45,<1 |
| [langchain-ollama](https://pypi.org/project/langchain-ollama/1.1.0/) | 1.1.0 | langchain-core >=1.2.21,<2; ollama >=0.6.1,<1 |
| [langgraph](https://pypi.org/project/langgraph/1.2.15/) | 1.2.15 | langchain-core >=1.4.7,<2 |
| [langsmith](https://pypi.org/project/langsmith/0.14.8/) | 0.14.8 | Python >=3.10 |
| [ollama](https://pypi.org/project/ollama/0.6.3/) | 0.6.3 | pydantic >=2.9 |

The tested runtime uses Python 3.11. Compatible metadata does not prove model
quality. The stored inference results and tests provide separate evidence.

## LangChain and Ollama

`ChatOllama` is provided by `langchain-ollama`. The integration supports structured
output and tool calls. TraceTrail uses `with_structured_output` with a Pydantic
schema, `method="json_schema"`, and `include_raw=True`. This preserves the actual
response and any parsing error. The model must still supply valid evidence.
See the [official ChatOllama guide](https://docs.langchain.com/oss/python/integrations/chat/ollama)
and the [pinned implementation](https://github.com/langchain-ai/langchain/blob/langchain-ollama%3D%3D1.1.0/libs/partners/ollama/langchain_ollama/chat_models.py).

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

## Model selection and exact record facts

Protocol v5 asks the model for a `ReportSelection`: findings with unchanged
hypothesis statements and statuses, finding citations, selected event
references, and narrative limitations. Its wire schema forbids `observations`.
The raw model response remains in the history. Code validates citation
resolution, selected finding citations, statement identity, and claim coverage
before extracting field values. Invalid selections do not receive projected
facts or a replacement model report.

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
