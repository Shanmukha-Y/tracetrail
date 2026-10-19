# Local model cohort

Qwen is the reference model for TraceTrail. Mistral and three Gemma sizes provide
additional local comparison points. Parameter labels, file sizes and advertised
features describe the deployments; investigation quality is established through
saved runs, source review and each experiment's frozen measurement contract.

The table records the local inventory captured on 2026-10-19 with Ollama 0.40.0
on an Apple M4 Max with 48 GiB of unified memory. All five main model files use
`Q4_K_M` quantization. Package bytes are the selected local model-list record's
size, including its packaged components. The
[sanitized inventory](../evaluation/model-inventory-pilot-v1.json) records the
selected artifacts, runner identities and metadata hashes.

| Exact tag and official registry page | Local GGUF family and parameter label | Package bytes | Model context limit | Selected runner |
| --- | --- | ---: | ---: | --- |
| [qwen3.8:27b-q4_K_M](https://ollama.com/library/qwen3.8:27b-q4_K_M) | `qwen35`, 27.3B | 17,741,872,132 | 262,144 | `ggml` |
| [mistral-small3.2:24b](https://ollama.com/library/mistral-small3.2:24b) | `mistral3`, 24.0B | 15,177,404,711 | 131,072 | `llamacpp` |
| [gemma4:31b-it-q4_K_M](https://ollama.com/library/gemma4:31b-it-q4_K_M) | `gemma4`, 30.7B | 20,385,458,234 | 262,144 | `llamacpp` |
| [gemma4:e2b-it-q4_K_M](https://ollama.com/library/gemma4:e2b-it-q4_K_M) | `gemma4`, 4.6B | 4,587,156,505 | 131,072 | `llamacpp` |
| [gemma4:12b-it-q4_K_M](https://ollama.com/library/gemma4:12b-it-q4_K_M) | `gemma4`, 11.9B | 8,021,618,941 | 262,144 | `llamacpp` |

Tags can resolve to different artifacts over time. These are the expected local
runtime digests from that inventory:

```text
qwen3.8:27b-q4_K_M
  sha256:25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e
mistral-small3.2:24b
  sha256:57bbe3480604be532b76a11087b4028a73e251a22c34380527281039a3967a06
gemma4:31b-it-q4_K_M
  sha256:17ba34c06c801ba22f6047bab21ced9429c6d43e0e42ecf339b0f3e5a61e8d97
gemma4:e2b-it-q4_K_M
  sha256:b37049369adfe3d2b653af0ab301a062ca5cbe96ace6aa0d3f2559ee9b563fc2
gemma4:12b-it-q4_K_M
  sha256:6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b
```

Mistral has two listed local runner records under the same tag. The selected
`llamacpp` record above is distinct from its `ggml` alternative. Run metadata
identifies the resolved model and runner so those variants remain distinguishable.

Google describes Gemma E2B as a dense model with 2.3B effective parameters and
5.1B including embeddings. Its per-layer embeddings explain the word
“effective”; it is not the active-expert count of a mixture-of-experts model.
The installed GGUF separately reports 4,647,450,147 parameters and the label
4.6B. Keep the publisher's architecture description and the installed artifact's
metadata separate; the numerical difference is not reconciled here. Google
describes 12B Unified as an encoder-free dense model with 11.95B parameters.
See the [Gemma model card](https://ai.google.dev/gemma/docs/core/model_card_4).

Downloaded bytes are distinct from runtime memory. Loaded weights, projectors,
draft models, KV cache, context length and backend buffers contribute to memory
use. Projectors and draft models can use different precision from the main
weights. TraceTrail loads one model at a time on the loopback-only Ollama
service. The comparison context is 16,384 tokens, below the table's model
limits; the inventory does not measure operation at maximum context. See
[Ollama's context guidance](https://docs.ollama.com/context-length).

The shared generation controls are temperature 0, seed 42, context 16,384,
maximum output 3,200 tokens and thinking disabled where supported. Prompts,
tools, cases, query budgets and scorers are frozen within each comparison.
Model training, tokenizers, templates and runners still differ.

All three installed Gemma packages declare `draft_num_predict: 3`. Their draft
components and packaged defaults are recorded alongside model identity.
An explicit override must survive the complete client and server path before
it can be described as applied. In the pinned ChatOllama integration, an
explicit per-call options dictionary replaces the generated options dictionary,
so it must include every shared control. The Ollama Python SDK accepts an
options mapping, while its typed `Options` class lacks `draft_num_predict`.
See the [Ollama parameter reference](https://docs.ollama.com/modelfile),
[ChatOllama 1.1.0 source](https://github.com/langchain-ai/langchain/blob/langchain-ollama%3D%3D1.1.0/libs/partners/ollama/langchain_ollama/chat_models.py#L694-L763)
and [Ollama Python 0.6.3 types](https://github.com/ollama/ollama-python/blob/v0.6.3/ollama/_types.py#L97-L143).
Packaged drafting and runner differences remain deployment factors when
interpreting measured latency, even with equal generation controls.

The registry and model cards advertise tool or function-calling capabilities.
Those advertisements do not measure strict schema fidelity, correct query
choice, complete evidence links or sound conclusions. Ollama's JSON-schema
output mechanism supplies structure; source-bound support and semantic review
test other properties. See [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

The installed licence texts for all five exact tags were checked from local
model-show snapshots and identify Apache 2.0. Their hashes are recorded in the
[sanitized inventory](../evaluation/model-inventory-pilot-v1.json). This repository
contains model references and application code; it does not redistribute model
weights. Local model use is permitted by the licence. Redistributing weights
or derived model files requires the licence copy, applicable retained notices,
modification notices and any required NOTICE attribution. Referencing a model
by tag does not itself redistribute its weights or require relicensing an
independent application. Google explicitly separates Gemma 4 from the older
Gemma agreement. See [Apache 2.0](https://ai.google.dev/gemma/apache_2)
and the [Gemma terms distinction](https://ai.google.dev/gemma/terms).
