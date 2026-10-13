# Local model, graph, and evaluation integrations

TraceTrail uses LangChain model and tool interfaces, a LangGraph investigation,
and the LangSmith Python SDK for local evaluation. Ollama inference, CloudTrail
records, execution traces, and evaluation results stay on the local computer.
TraceTrail does not upload to LangSmith or require a LangSmith account or key.

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

The SDK requires a client object even for offline feedback handling. TraceTrail
uses the real client with a transport that rejects every HTTP request, an empty
key, and no automatic batching. Both standard and newer API transports are
blocked. Tests also deny socket connections. Evaluation failures are retained
and reported in the local artifact.

## LangSmith platform limits

The [LangSmith SDK license](https://github.com/langchain-ai/langsmith-sdk/blob/main/LICENSE)
is MIT. The full LangSmith server and web UI are separate products. The
[official self-hosting guide](https://docs.langchain.com/langsmith/self-hosted)
states that self-hosting is an Enterprise add-on and requires a license.
TraceTrail does not install a server, accept service terms, set up billing, or
create credentials. A full local LangSmith UI is therefore unavailable in this
increment. Offline SDK evaluation and disk traces work without that server.
