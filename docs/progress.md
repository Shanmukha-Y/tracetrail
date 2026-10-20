# Progress and release checks

TraceTrail is an experimental portfolio project. The reliability checks below remain open. The user authorized public repository access on October 19, 2026. Workflow Sentinel is complete and was not changed.

Dated instructions to keep the repository private describe earlier checkpoints.
The October 19 publication authorization supersedes those access restrictions;
it does not close the reliability checks.

## Implemented

- Local CloudTrail JSON ingestion with exact record citations, indexed queries, and explicit budgets.
- LangChain Ollama structured output and read-only evidence tools.
- A stateful LangGraph investigation with bounded query and model calls.
- Observed field validation, hypothesis status, cited timelines, raw failure retention, and private local files.
- Five approved local model tags, sequential inference, raw remote-routing checks, proxy and redirect guards, and no ambient credential use.
- Real local graph traces and genuine offline LangSmith SDK evaluation with blocked HTTP.
- Preserved earlier synthetic suites and a frozen two-case v4 suite with field support annotations.
- CI for lint, formatting, and tests without inference or hosted tracing.

## October 20: automated test limit

The collected suite is reduced from 734 cases in 23 modules to 50 cases in
16 modules, including parameter variants. Forty-seven existing cases remain;
687 old cases were removed and three focused checks were added. Root
`conftest.py` counts items before deselection and fails collection above 50.
No test was disabled, excluded, moved or merged into a scenario loop.
The [inventory and coverage tradeoffs](test-coverage.md) name the retained
boundaries and the direct regression coverage that was dropped.

All 50 cases pass, with lint and formatting passing. Production code,
dependencies, scripts, fixtures, protocols and model evidence match all
73 original file hashes. The existing auditor verified the saved 40-cell
pilot and its SDK replay again, including the original 90 model calls and
94 tool calls. The audit made 94 separate read-only source-query replays,
with no new inference or SDK evaluation. Its private verification SHA-256 is
`512e1e2904851d95947c35c5851a86405096ef6c96e665bbd5157a617eaa63f2`.
Earlier test counts below describe the earlier revisions. No new benchmark
was run. Workflow Sentinel was not changed.

## October 19: matched local model pilot

The user requested comparisons across deployments with different capabilities.
The cohort now adds `gemma4:e2b-it-q4_K_M` and `gemma4:12b-it-q4_K_M`
to Qwen 27B, Mistral 24B and Gemma 31B. Both new models were downloaded from
the official registry after licence, storage and hardware checks. The other
three weights were reused. All five exact local licence texts identify Apache
2.0. See the [public inventory](../evaluation/model-inventory-pilot-v1.json)
and [deployment notes](model-cohort.md). Parameter size is not an intelligence
ranking.

The [pilot protocol](../evaluation/protocol-model-pilot-v1.json) was frozen
before inference at 21:54:59 UTC. Its SHA-256 is
`8fbea96221f8948ffe9303a4e41cd9decee0a353262866bbcd5cfb7c35d15643`.
It pins 18 runtime, dependency and rubric inputs, eight schemas, the unchanged
v8 prompt, all five effective weight digests and listed variants, package and
server versions, and the two exposed v7 development cases. The historical
scorer and the primary `claim-support-v1` scorer are unchanged. A tagged
planning-action schema is deferred so it cannot confound this comparison.
The frozen runtime passed 703 tests, lint and formatting before inference.

The staged runner saves each assigned attempt with a unique cell identity,
atomic private writes and a canonical payload hash. Resume checks the same
source, schema, dependencies, model identities and ordered plan. It preserves
failures and interrupted attempts. Both methods run within every model;
method order is counterbalanced across cases and repeats.

Optional sampling records separate Ollama allocation accounting and macOS
process-tree RSS. It has bounded reads and sample counts, a joined worker
before unload, explicit gaps and foreign-model flags. These are sampled
maxima with overlapping memory views, not measured peak VRAM or a total formed
by adding RSS and reported GPU allocation. Resource errors do not rewrite the
raw investigation result.

The first ten actual cells took 1,002.8001 seconds. The predeclared formula
`1.2 * 4 * S` forecast 4,813.4403 seconds for 40 cells. Required measurements
were complete and no foreign model was observed, so the recorded gate selected
40. The first ten remain in the analysis. Their immutable local snapshot is
`local-results/model-pilot-v1.stage1.json`, SHA-256
`42c89705c4709769d0dcf4e5425c106af2a7f76cadb088a62d1aa7150e6d964b`.
Expansion uses runtime and measurement availability, not answer quality.
The 5,400-second accumulated wall limit stops new launches; an in-flight
bounded run may finish after it. See the [pilot guide](model-pilot.md).

The [semantic review rules](../evaluation/pilot-semantic-review-v1.md) were
frozen before these outputs. They separate returned-evidence warrant, exact
declared support, full-source truth, retrieval gaps, avoidable uncertainty,
and material prose. Assistant second checks preserve disagreements. These
known synthetic cases and same-seed repeats do not supply independent human
validation, generalization intervals or a model winner.

All 40 assigned investigations finished, using 90 actual Ollama model calls
and 94 read-only tool calls. The accumulated whole-cell wall time was
4,057.8170 seconds, or 67.63 minutes. Twenty-two processes passed structural
checks; 18 remain invalid. The batch status remains `incomplete` because of
those failures, while `attempted_all_target_cells` is true. There were no
replacement attempts. All five models were unloaded after use; the final
Ollama process list contained no loaded model.

The real offline LangSmith SDK evaluated all 40 saved outputs and emitted
840 prefixed feedback values, with uploads disabled and no inference rerun.
The separate auditor verified all cells, original trace counts, exact sources,
wire inputs, query replays, resource accounting and all 21 primary counters.
Its 94 source-query replays are verification work, outside the original
agent's 94 tool calls. Final code checks passed 734 tests, lint and formatting.
Tests use marked mocks and are separate from these actual model measurements.

Final raw SHA-256:
`6c4faf86e2a374e0636850350372029ae8fe400ef120a91af10a0d8d36afb60d`.
Final SDK SHA-256:
`4085b9aab0920d6faaca0ca105a3a6c53b79ae29d3b6dfc4fca369416bfff95a`.
Final independent verification SHA-256:
`edb2075cafcc76fdf7a59d4a4d84d5f96a8927df78ead36ecd3785fb1a7a8995`.

All 160 fixed-claim slots received source-aware assistant reviews. One early
E2B adaptive KMS preliminary draft was applied before target inspection; its
history is preserved, corrected returned-evidence judgments were locked before
the full-source check, and a second assistant rechecked both KMS reports.
The [pilot guide](model-pilot.md) and
[results review](model-pilot-results.md) disclose this procedure deviation.
No model output, source fixture, runtime or mechanical score was changed.

The [checked public numeric summary](../evaluation/results-model-pilot-v1.json)
has SHA-256
`427119be39d68ac530ee7299269f900d8ff1a56dbff328a68c293029d9afe69e`.
It separates 44 warranted definite decisions, 10 false definite decisions,
8 unsupported definite decisions, 2 avoidable uncertainties, 56 retrieval-limited
unknowns and 40 source-limited unknowns. Only 6/160 findings satisfy the complete
primary own-link contract; 124/520 required atoms receive primary credit.
The second assistant checked 33 selected reports and 132 slots, retaining ten
prose-severity disagreements. Primary and adjudicated prose counts remain
separate; they have no emitted-assertion denominator.

All 20 canonical repeat-content pairs matched. A separate comparison also
found identical failure lists in each pair.
The memory records have 3,693 samples and no read errors or foreign model.
Gemma's server-reported `size` and `size_vram` are much smaller than package
bytes and RSS; this unresolved runner-accounting discrepancy is explicit in
the results and is not described as low true residency or peak VRAM.
The proposed eight-fresh-case follow-up is 80 core runs, or at most 100 with
preselected repeats. Pilot-derived forecasts with 20 percent allowance are
162.31 and 202.89 minutes. This follow-up has not run or been scheduled.

## October 18: credential context and finding-level measurement

The [v7 source review](v7-evidence-review.md) exposed premature stopping,
credential-scope confusion and false budget explanations. It also showed a
measurement gap: globally projected fields could credit a finding that never
linked them. V8 preserves every historical scorer value and adds the separate
[claim-support-v1 contract](measurement.md).

The observed credential map groups exact signer and returned-key occurrences
from already returned records. It copies literal identity types, exact paths,
existing lookup IDs and actual complete query scopes. It never scans hidden
records, predicts matches, chooses a query or supplies a claim conclusion.
Limits and omissions are explicit. A short planning addition asks the model
which available lookup could observe a missing relation. Existing schemas,
tools, budgets, query-scope guards and failure policy stay unchanged.
Machine termination counters are separate from unverified model reasons.

### Development and freeze

One already exposed v6-suite case, `heldout-directory-path`, received actual
Qwen adaptive and fixed runs. Its original split name remains historical;
it was development evidence for this increment. The adaptive run remained
invalid after two queries, with one unused. It retrieved 75% of relevant
events, but falsely marked a child-use scope tested. Its raw new score was
2/4 complete claim contracts and 7/11 atoms; primary credit was zero.
The fixed run completed with 50% recall, zero complete contracts and 5/11
primary atoms. Durations were 208.07 and
67.54 seconds. This failed exposed
check does not show a planning improvement. Both outputs and all errors remain.

The candidate's genuine offline SDK replay produced 42 prefixed feedback
items from two saved outputs, with no new inference or uploads. Its raw,
SDK and audit artifacts were saved before the sole later source change:
a scorer guard for malformed, non-string saved failure phases. The guard
preserves raw support but makes primary validity fail closed. It does not
change ordinary runtime output or planning. All 13 candidate source files
remain in a byte-verified private archive. The final suite and runtime were
frozen after the guard and 644 passing tests, before any fresh inference.

Final protocol SHA-256: `e025493b6f2309d86c9339b4217a7bf1aedbbd51aa209d837d1e75e8f4cefcca`.
Final prompt SHA-256: `5d801a719e65e23a28deb1ee8088416c20fe9bb5d0c7d599098a11993ec0828a`.
Fresh manifest SHA-256: `56c128e29c8e3588f9cd4fbac83759538db9e20143df91a54e2fb425456fc75a`.
The independent v7 suite contains 20 invented records, 15 relevant records,
16 hypotheses and 51 exact typed required atoms. Separate assistant reviews
checked source semantics, privacy, annotations and reachability within three
queries. Both splits were frozen before inference; neither tuned this run.

### Fresh comparison and review

The October 18 v8 comparison ran 16 actual local investigations on four new synthetic cases, with two cases per split and one repeat per cell. 10 processes completed structural checks. All failures remain in the denominators.

| Model and method | Valid processes | Mean raw selected-event precision / recall | Complete primary claim contracts | Primary required atoms | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 3/4 | 100.00% / 81.25% | 3/16 | 24/51 | 2.00 | 214.93 |
| Qwen fixed | 4/4 | 100.00% / 45.83% | 2/16 | 23/51 | 3.00 | 62.73 |
| Gemma adaptive | 2/4 | 100.00% / 93.75% | 1/16 | 17/51 | 2.50 | 267.29 |
| Mistral adaptive | 1/4 | 75.00% / 50.00% | 0/16 | 5/51 | 2.00 | 133.29 |

Primary support uses the new finding-level contract. It counts only a corresponding finding's explicit source links in a valid process. All 204 required atoms remain in the denominator; 69 receive primary credit. Complete claim contracts additionally require the fixed statement, status and all required records and atoms. These counts are not a semantic accuracy or hallucination measure. Legacy metrics remain separately available. Selected-event precision and recall are raw means that include invalid processes. Primary claim and atom credit is process-gated.

The credential map does not establish a planning improvement. Source review found early stopping, false query-scope and budget explanations, incomplete field links, and semantic errors. The [assistant evidence review](v8-evidence-review.md) separates these failures from correct uncertainty. It is not independent human review. Four cases cannot establish a model winner, a broad adaptive advantage, or production reliability. The fixed control is three seed searches within one hour on each side of the seed. See [v8 results](../evaluation/results-v8.json) and the [evaluation guide](../evaluation/README.md). Earlier results and reviews remain preserved.


| Model and method | Split | Valid processes | Mean raw selected-event precision / recall | Complete primary claim contracts | Primary required atoms | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | development | 2/2 | 100.00% / 87.50% | 1/8 | 16/26 | 2.00 | 216.01 |
| Qwen adaptive | heldout | 1/2 | 100.00% / 75.00% | 2/8 | 8/25 | 2.00 | 213.84 |
| Qwen fixed | development | 2/2 | 100.00% / 41.67% | 1/8 | 11/26 | 3.00 | 64.96 |
| Qwen fixed | heldout | 2/2 | 100.00% / 50.00% | 1/8 | 12/25 | 3.00 | 60.49 |
| Gemma adaptive | development | 1/2 | 100.00% / 100.00% | 0/8 | 9/26 | 2.50 | 278.98 |
| Gemma adaptive | heldout | 1/2 | 100.00% / 87.50% | 1/8 | 8/25 | 2.50 | 255.59 |
| Mistral adaptive | development | 1/2 | 100.00% / 75.00% | 0/8 | 5/26 | 2.00 | 144.35 |
| Mistral adaptive | heldout | 0/2 | 50.00% / 25.00% | 0/8 | 0/25 | 2.00 | 122.23 |

The local audit recomputed legacy and finding-level scores, actual
model and tool spans, wire schemas and prompts, source identities, exact
projections, credential maps, budgets and SDK feedback. A separate verifier
derived all 21 claim counters without calling the new scorer. Raw report
materialization matches alias-resolved model output; no missing links,
references, statuses or queries were repaired. See the numeric summary for
per-cell and split values, effective weight digests and artifact hashes.

Fresh raw SHA-256: `79c716bef1ea6d5a0e319d4645f029c941dbc5c92ad1f3b270e677bf0237dbce`.
Fresh SDK SHA-256: `57e328f1912fa3485d73936472c58406557f4db29525dfccde83fcd15685dab1`.
Independent verification SHA-256: `569383acffda8d15fd8065a3586abc351bd5e33b421c6307a0c490b353f045cb`.

The genuine offline SDK evaluated 16 fresh saved outputs and two development
outputs: 378 prefixed numeric feedback items.
Each replay trace preserves its exact input and saved output. Replay trees
contain no model or tool calls. Original investigation traces retain actual
inference and read-only tool use. Hosted export remains disabled; no account,
credential, terms, licensed server or paid API was configured.

The separate CLI demo ran `dev-role-duration-direction` with actual Qwen
adaptive inference. Its status is `completed`, with
2 queries,
4 model calls and
206.24 seconds. It is an additional
repeat, not a benchmark cell. Reproduce it with:

```sh
uv run tracetrail demo --manifest evaluation/cases-v7.json \
  --case dev-role-duration-direction --output local-results/demo-v8.json
```

All 19 investigations used actual sequential local
Ollama calls: 59 model spans and 45 tool
spans. Raw outputs, trace trees, SDK feedback and source reviews remain in
ignored private files. Numeric summaries, invented fixtures and fingerprints
are versioned. Ruff and all 644 local tests pass. Unit-test models are separate
from these actual capability results.

### Remaining release checks

- Improve credential-direction reasoning and use of available local context.
  The observed map alone does not resolve these failures.
- Reduce premature stopping, false tested-scope claims and false budget prose
  without hidden searches, minimum-query rules or benchmark branches.
- Require complete finding-level links while preserving the distinction
  between annotation support and semantic correctness.
- Add independent cases, repeated runs and human source review. All current
  cases are exposed for future work informed by these results.
- Keep the project labeled experimental while these reliability checks remain open.
  Offline LangSmith works; hosted export stays
  disabled and is not needed for the local scope.

## October 17: explicit planning choices and query scope

The [preserved failure diagnosis](oct17-diagnosis.md) identifies early finish
as a model choice: all four v6 Qwen adaptive runs stopped after one query with
two queries unused. Observed local pivots were available. Other runs described
principal or resource constraints that their actual filters did not execute.
The graph had honored those decisions, rather than exhausting its tools.

Protocol v7 adds a model-authored ledger for every supplied claim before each
action. The model names returned evidence, an open question, relevant observed
pivots, and actual query attempts. It explicitly chooses one candidate filter,
one pending continuation, a custom query, or an event lookup. Required nullable
branch fields and mechanical validation reject omitted or conflicting choices.
Code never infers a query from a rationale or ledger.

The observed-only catalog now gives each filter its meaning and each actual
query an attempt ID. It retains complete AND filters, time bounds, errors and
page scopes. A successful scoped attempt does not establish complete coverage.
Pending continuation IDs disappear only after that exact normalized scope was
successfully executed. The catalog is capped at 16 candidates. Its candidate
count and truncation flag disclose omissions. Its `finish_accounting_ids` list
contains every visible candidate and pending page, including queried candidates.

An early finish must account for these IDs, with model-authored reasons for
deferral, irrelevance, or testing under an actual recorded scope. Zero-query
finishes remain allowed. Exhausting the graph's query budget has a separate
stop reason and needs no extra planner call. No minimum search count, hidden
query, status repair, annotation lookup, or retry was added.

These checks establish references and executable scope. They do not certify
the ledger, relevance, gap completeness, disposition reasons, or conclusions.
An invalid planner stops further searches and preserves its raw output. The
bounded final report is still attempted. Its selection can validate and yield
exact facts, while overall process status remains invalid. Ordinary historical
scorer metrics can therefore be nonzero for an invalid process. Primary valid
process field coverage gives those runs zero credit.

### Exposed development and frozen inputs

Three actual Qwen adaptive-versus-fixed batches used only the older v5
`dev-key-lifecycle` case. They are development evidence, with one run per cell.
All failures remain preserved.

| Adaptive development candidate | Process | Queries / calls | Selected recall | Raw strict support | Raw status accuracy |
| --- | --- | --- | --- | --- | --- |
| Optional branch fields | Invalid | 0 / 2 | 25% | 0% | 25% |
| Required nullable branches | Invalid | 2 / 4 | 100% | 75% | 100% |
| Explicit finish accounting list | Invalid | 2 / 4 | 100% | 75% | 100% |

The first model named the useful child-key pivot in its ledger and rationale
but omitted the executable choice. Making nullable branch fields required
removed that omission path. The next run retrieved the four-record chain but
omitted three finish dispositions. The final candidate supplied an explicit
accounting list. Qwen still omitted one ID and called principal and issuer
filters tested by key queries that did not execute those predicates. Validation
preserved both errors. Its ledger also marked the later-state question closed
while its report correctly left that state uncertain. Structure does not prove
reasoning or an honest scope judgment.

The final adaptive duration was 207.30 seconds. All three fixed runs used three
queries and one call, with 25% recall, 25% raw status accuracy and zero strict
support. The final fixed duration was 52.79 seconds. Exact report facts and
matching labels do not erase the adaptive process failures. These exposed
results establish neither a successful planning fix nor general improvement.

Each batch received a real offline SDK evaluation: six saved-output replays,
132 numeric feedback items, no new replay inference and no uploads. Original
execution traces contain 13 model spans and 13 tool spans. Byte-verified source
snapshots preserve both earlier candidate implementations locally.

The final [v7 protocol](../evaluation/protocol-v7.json) freezes 11 source files,
eight schemas, the prompt, budgets, models and independent v6 suite. Its SHA-256
is `b00bb95ecb13990607c9cc4713c9628bf812cbf738b17537bb9a8acf6cbd8c18`.
The final prompt SHA-256 is
`544041d360b9a675be55254c61d2582314d6bbb7f61a521e39c028b0797c302e`.
The reporting instructions, report schemas, exact fact projection, fixed
queries and historical scorer remain unchanged. Reporting context now includes
the latest plan and the richer catalog. The change does not isolate the effect
of each planning feature.

The independently authored v6 suite has four invented cases, two per split:
20 records, 14 relevant records, 16 hypotheses and 43 exact required observation
atoms. Independent assistant review checked current AWS semantics, evidence support and
tool reachability. Its final manifest SHA-256 is
`e49257ef91352b7e1686bebc79bd04f61078e0da8be39651c1495aeadf702b87`.
Its development split was not used to tune v7. All new cases and runtime inputs
were frozen before fresh inference. Earlier fixture bytes remain unchanged.
Different suites have different propositions and annotation requirements, so
their support percentages cannot establish a version-to-version improvement.

### Fresh comparison

All 16 frozen fresh cells ran with actual local Ollama calls. Ten processes
completed; six are invalid and remain in every denominator. The comparison
CLI returned nonzero for these invalid results. Each group has four cases,
two per split, with one run per cell.

| Model and method | Valid processes | Mean selected precision | Mean selected recall | Mean raw strict support | Mean raw status accuracy | Mean queries | Mean calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 3/4 | 100% | 87.50% | 81.25% | 100% | 2 | 4 | 199.29 |
| Qwen fixed | 4/4 | 91.67% | 50% | 18.75% | 50% | 3 | 1 | 49.55 |
| Gemma adaptive | 3/4 | 100% | 70.83% | 56.25% | 87.50% | 1.5 | 3.5 | 200.82 |
| Mistral adaptive | 0/4 | 66.67% | 54.17% | 31.25% | 100% | 2.25 | 4 | 148.34 |

These are means across all four cells, including invalid processes. Recall
measures the valid selected evidence set, rather than everything returned by
tools. Raw strict support and status accuracy can be nonzero in an invalid
process. All Mistral status labels match, but none of its processes validates.
That is not a successful investigation or evidence of reliable reasoning.
The fixed comparator is the frozen one-hour seed-filter baseline; this study
does not compare every possible fixed-search approach. Adaptive used fewer
queries here but more model calls and time.

| Model and method | Development raw support | Held-out raw support | Primary valid-process declared fields |
| --- | --- | --- | --- |
| Qwen adaptive | 100% | 62.50% | 23/43 |
| Qwen fixed | 12.50% | 25% | 17/43 |
| Gemma adaptive | 50% | 62.50% | 17/43 |
| Mistral adaptive | 0% | 62.50% | 0/43 |

Thirty-four of 64 findings fail the unchanged strict annotations. Primary
field-path coverage is 57/172 required claim/source/path atoms. Invalid
processes retain their denominators and receive zero primary credit. The
metric checks explicit field declarations in the corresponding finding; it
does not use global projected facts or rationales, and ignores role meaning.
It measures source-path coverage, not semantic entailment. Retained exact
facts from a valid report inside an invalid process remain inspectable locally.

The [Qwen assistant source review](v7-evidence-review.md) records concrete
counterexamples. The directory investigation marks credential uses tested
through an issuance query. The topic investigation claims no budget remains
while one query is unused. The trail investigation recovers the caller and
issuer but skips an available child-key query for a later status request.
Correct status labels do not repair these omissions or scope assertions.
Gemma also leaves useful queries unused, and one malformed ledger ID stops
its topic investigation before any search. Null read responses and normal
empty write responses require API-specific interpretation.

Assistant review classifies Mistral's failures separately. Retention retrieves
the chain but invents `/evidence/*` report selections instead of using supplied
aliases. Topic falsely marks pivots tested, misses issuance, and leaves two
uncertainty gaps empty. The held-out runs mark unexecuted caller searches
tested and substitute child activity for original-caller evidence. Matching
whole-corpus status labels do not establish these explanations. All reviews
are assistant-generated source checks; no independent human review was done.

The offline SDK evaluated all 16 saved runs with 352 matching numeric feedback
items, no upload and no replay inference. Original execution traces contain
50 model spans and 35 tool spans. Source, schema, prompt, manifest and actual
invocation fingerprints match the freeze. The [scalar artifact](../evaluation/results-v7.json)
records all cells and split rows, source artifact hashes, costs, invalid
processes and effective loaded weight digests. Full raw reports, SDK traces,
assistant review sidecars and earlier candidate source snapshots remain in
ignored local files with `0600` permissions. They are not pushed.

Fresh raw results SHA-256:
`830b9f4cfa63d86a9803585724b1692328329042b5863156babd5125aa3a660e`.
Fresh SDK artifact SHA-256:
`72fe231b57d92d1e67d5b8e6d41bc4ffa188b13e9a7dc6bea6ac44c6c0a85c9c`.
No fresh-output changes were made to runtime code, prompts, schemas or cases.
All cases are now exposed for later work informed by this study. Independent
human review, repeat stability and broader release checks remain open.

### CLI demonstration and final local checks

Reproduce the separate actual Qwen demonstration with:

```sh
uv run tracetrail demo --manifest evaluation/cases-v6.json \
  --case dev-retention-chain --output local-results/demo-v7.json
```

It completed with two queries, four model calls, three selected relevant
records and 83 exact projected observations in 204.69 seconds. Its selected
precision, recall, status accuracy and strict support were all 100% on this
single exposed demonstration case. This repeat is separate from the frozen
benchmark and does not measure general reliability. Its raw artifact SHA-256
is `b2286395b302d83c68373515ee49ff7ca43816e3d0b77af61dceb72ffa10e1fe`.

Across the three exposed batches, fresh matrix and separate demonstration,
23 actual investigations contain 67 model-call spans and 50 tool-call spans.
Twenty-two saved outputs received offline SDK evaluation with 484 numeric
feedback items. The demonstration has original execution traces but was not
replayed into the SDK evaluator. No replay invoked a model or uploaded data.
The listener was observed at `127.0.0.1:11434`; no models remained loaded after
the demonstration. No weights were downloaded and no credentials were created.

Final local verification passed all 518 tests, Ruff lint, formatting and
whitespace checks. These checks cover software behavior and failure handling;
they do not clear the observed model reasoning failures or release gates.
The scalar artifact SHA-256 is
`e4167007203fbad6ea178324af67fd00ca608f1a70421eb4685ad58fabadd40e`.

## October 16: claim-level evidence links

The [failure diagnosis](oct16-diagnosis.md) distinguishes report omissions from
retrieval limits. In the preserved v5 fresh comparison, four of 16 strict
failures were citation-only omissions. Twelve required unretrieved records.
Six omitted an available selected citation, including two with a retrieval gap.
Seven status mismatches were cautious uncertainty after incomplete retrieval;
one Qwen finding incorrectly refuted earlier caller activity because it had
not retrieved the caller record. These counts describe the preserved evidence,
not a new model result.

Protocol v6 requires a model-authored evidence basis for each fixed claim. The
model chooses links to returned records, exact field paths, and the role of each
link: support, contradiction, or context. It supplies a brief rationale and
specific missing evidence before its status. Public finding citations are
only the ordered unique references in these links. Code does not add records,
fill citation gaps, select a status, or repair a failed model report.

The link validator checks selected-record references, field presence, bounded
nonblank explanations, duplicate links, and structural status requirements.
A supported finding needs a declared supporting link; a refuted finding needs
a declared contradicting link. Uncertainty needs a specific evidence gap.
Only the four standard top-level API envelope fields may be linked when absent.
An arbitrary missing nested path is not accepted as observed evidence. The
roles, rationale, and claim meaning remain model judgments. A resolving field
path does not establish relevance, contradiction, or entailment.

The model budget, exact fact projection, temporal context, local models, fixed
search, and annotation scorer remain unchanged. Both search methods and every
model use the same reporting contract. V6 changes its wire schema, instructions,
and structural validation together. No gain can be attributed to one part
without a separate experiment. The new contract does not guarantee retrieval
of missing context, completeness of finding citations, or semantic correctness.

### Frozen protocol and development checks

The independently authored `tracetrail-synthetic-v5` suite has four invented
cases, two per split: 18 records, 14 relevant records, 16 fixed hypotheses, and
96 required field observations. Its manifest SHA-256 is
`66f704a593c5d152d82f683cded4b1fa8014f58fe05f337d0bdaef615cde3e96`.
Independent review checked source types, timestamps, identities, CloudTrail
semantics, and tool reachability within three queries. Reachability is a tool
check, not a model result. New API annotation choices are documented in
[CloudTrail semantics](cloudtrail.md#v5-annotation-semantics).

The final [v6 protocol](../evaluation/protocol-v6.json) records ten source
hashes, six schemas, the prompt, budgets, and fresh manifest. Its SHA-256 is
`062030719ddd94ec17eb42518051c5f819475719eb5a92f500c72e42e6f8b456`.
The final prompt SHA-256 is
`4335bc9f8c85cce8502b6c4858ab64863c7b982cbe93fed1783de7583ca23db9`.
All source and prompt changes ended before fresh inference started.

Two actual Qwen comparisons used only the exposed development case from v4.
The first candidate omitted available linking citations. Its adaptive support
was 50%, with 100% recall and status accuracy. A general component checklist
was then added to the prompt: actor and credential provenance, action and
target, event relationships, time, and resulting state. It supplies no case
answers. The candidate and final prompts are distinct; both outputs remain
preserved. No fresh-case outputs were used to make this change.

| Exposed development check | Adaptive support | Fixed support | Adaptive field links | Fixed field links |
| --- | --- | --- | --- | --- |
| Earlier candidate | 50% | 25% | 21/30 | 11/30 |
| Final frozen protocol | 75% | 25% | 25/30 | 12/30 |

Each row has one actual run per method. Final adaptive recall and status
accuracy were 100%; fixed recall and status accuracy were 50%. Final durations
were 144.31 and 60.25 seconds. Adaptive used two queries and four calls; fixed
used three queries and one call. These exposed development results do not
establish an independent improvement or a general reasoning fix.

The final adaptive report still omitted an issuer citation from an action
claim, even though its rationale discussed the provenance. A later-state
finding passed the unchanged strict scorer through global projected facts,
while its model-authored read link omitted required response and read-only
paths. Strict support and explicit field-path coverage measure different
properties. Neither proves narrative entailment.

Each two-run batch received a genuine offline SDK replay with 44 numeric
feedback items. Across both batches, original inference traces contain ten
model spans and ten tool spans. Uploads and new replay inference were disabled.
All metrics, schema invocations, source references, and projected facts matched.

Candidate raw results SHA-256:
`15d6f49b6ef10fdc65e0364a99510c2054164206fbe587a77fef99c81b3a3623`.
Candidate SDK artifact SHA-256:
`42f75443b7a7959a852dd5354a6f540fd54562face572d4bee0794f17a4630eb`.
Final development raw results SHA-256:
`a4d446e9a28de5263d383df09ef4c708663a0b78ca1956979404c8b3323674db`.
Final development SDK artifact SHA-256:
`7339546efb1ced9a2e670a6803da82ac85ab829424749bf345432a3c20465717`.

### Fresh comparison and final validation

All 16 fresh investigations finished under the frozen final protocol. There
was one run per model, method, and case cell, with four cases per group and two
cases per split. Thirteen reports completed structural validation. Three
Mistral reports are invalid and remain in the denominators. The CLI returned
nonzero for those invalid reports. The [numeric summary](../evaluation/results-v6.json)
preserves cell and split rows, counts, model weight digests, and artifact hashes.

| Model and method | Valid reports | Mean selected-event precision | Mean selected-event recall | Mean strict support | Mean raw status accuracy | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 4/4 | 100% | 64.58% | 56.25% | 75% | 1 | 3 | 100.44 |
| Qwen fixed | 4/4 | 70.83% | 43.75% | 12.5% | 56.25% | 3 | 1 | 64.71 |
| Gemma adaptive | 4/4 | 95% | 91.67% | 75% | 100% | 2.25 | 3.75 | 154.52 |
| Mistral adaptive | 1/4 | 50% | 43.75% | 18.75% | 81.25% | 3 | 4 | 96.24 |

These precision and recall values measure the validated selected report set,
not just records returned by tools. Raw status accuracy can count a matching
label in an invalid report. For example, Mistral's network labels all match,
but its selected references are invented `/evidence/*` paths instead of supplied
aliases. That report has no valid selection and receives no projected facts.
The three invalid outputs were not repaired, retried, or omitted.

Thirty-eight of 64 findings fail strict annotations. This is not a hallucination
count. The unchanged strict scorer checks fixed statements, statuses, required
citations, and global projected facts. It does not verify that a rationale or
declared evidence role entails the statement. A full-source status can also be
correct by chance when the report lacks a required credential-issuance record.

The separate explicit field-link audit checks only exact required paths named
for the corresponding finding and source. It gives no credit from rationale
text or global projected facts. Invalid reports retain their required atoms
and earn zero primary credit. Required atoms are unique claim/source/path
requirements; they are not counts of correct model conclusions.

| Model and method | Explicit required field links |
| --- | --- |
| Qwen adaptive | 43/96 |
| Qwen fixed | 20/96 |
| Gemma adaptive | 44/96 |
| Mistral adaptive | 15/96 |

The primary total is 122/384; the three invalid reports retain 74 required
atoms with zero credit. Thirteen valid reports have exact projected facts.
The invalid reports have no projected facts. These results neither measure
model field extraction accuracy nor certify relevance or entailment.

Manual review preserves important failures. Every fresh Qwen adaptive run
stops after one query, leaving two queries and observed-key pivots unused.
One Qwen report and Mistral's valid publication report refute approval using an
upload denial. A denial contradicts successful upload, not business approval
of the attempt. Mistral also refutes caller history from an incomplete time
window; the missing contradiction-role guard rejects that report. Two other
Mistral outputs have invalid selected references. No reference or status was
silently corrected. Other failures include missing issuer links, confusing
caller filters with target parameters, and query rationales narrower than the
actual filters. No blanket citation padding was found. Gemma's extra same-key
read is useful resource context despite its fixed relevance-annotation penalty.

The genuine offline SDK replay evaluated all 16 outputs and produced 352 numeric
feedback items, with uploads and new inference disabled. All saved metrics
recomputed exactly. The original fresh trace trees contain 47 model spans and
37 tool spans, matching the recorded counters. All ten source hashes, six
schemas, actual invoked prompts and schemas, and the frozen manifest match.
Effective weight digests were constant within each model and match the earlier
installed baseline. Qwen's runtime backend is not recorded in these artifacts;
this limits runtime comparisons. No model winner, broad adaptive advantage,
cross-suite improvement, or production reliability claim follows from four
synthetic cases and one run per cell.

Fresh raw results SHA-256:
`c7eee979197141a84287391810ac42df226a8ad06ef270f267772a7ca80c1be2`.
Fresh SDK artifact SHA-256:
`da013dc3040441efb472e94f8bd157afe2e06c440f6a185676fbb53ad6bdf6cb`.
Full local audit SHA-256:
`150980a539b9ac4f2cdaec1e8004ae7f3b37c14ed7dce4b5cf74ae6299890b98`.

The separate documented CLI demo ran `dev-key-lifecycle` with actual Qwen
inference. It completed in 105.39 seconds with three model calls, one query,
and 90 exact projected observations. Precision was 100%, recall 75%, strict
support 50%, and raw status accuracy 75%. Its limitations and two strict
failures remain in the saved output. This repeat is not another benchmark
cell. Raw demo SHA-256:
`b113b84ed1ee4f1a900b4ce7968976d9827947ed05d198b084f3315370226ae5`.

This increment made 21 actual local investigations: two initial candidate
runs, two final development runs, 16 fresh runs, and one demo. Nineteen use
the final frozen protocol. Across all 21 investigations, original traces
contain 60 model spans and 48 tool spans. The 20 comparison outputs received 440 real offline SDK
feedback items. Raw investigation outputs, trace trees, SDK feedback, and
audit details remain in ignored local files with mode `0600`. Invented
fixtures, protocols, numeric summaries, and hashes are versioned. Ollama had
no loaded models after the demo. Local SDK evaluation requires no hosted
account, credential, export, or server setup.

Ruff lint, formatting, and all 398 local tests pass. Unit-test models remain
explicitly separate from the actual capability evidence above. Exact-commit
CI is available in the repository
[Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

### Remaining release checks

- Improve model use of available local pivots and query scope without hidden
  searches, benchmark-specific branches, or minimum-query score padding.
- Reduce invalid reference generation and missing model-authored evidence
  chains without repairing failed outputs after the fact.
- Distinguish approval from API success, and missing context from contradiction.
  Valid references and correct raw labels remain insufficient.
- Test more independent cases and repeated runs, with manual semantic review.
  Keep every exposed case and failure available for later regressions.
- Keep the repository private. Local LangSmith SDK work is complete; hosted
  credentials or a licensed UI are not release requirements.

## October 15: selected-record facts and temporal context

Protocol v5 separates model decisions from exact field extraction. The model
selects records, finding statuses, citations, and limitations. After a valid
selection, code copies typed JSON fields from those selected returned records.
The code does not select additional events, use annotations, change findings,
or infer approval, intent, success, or state. The output marks these facts as
`selected-record-projection-v1`. Conclusions and narrative remain semantically
unverified.

The model receives evidence in UTC timestamp order and a separate table of
signed seconds from the seed. Negative values precede the seed. Citation aliases
remain stable in discovery order. This is timestamp assistance, not a claim of
causality or a verified temporal conclusion.

The projection preserves exact types, empty values, whole arrays, and missing
versus null API fields. It fails explicitly on ambiguous paths or limit errors.
The limits are 2,000 observations, one million bytes of compact ASCII-escaped
JSON, depth 32, and 512 characters per field path. Invalid selections receive no
extracted facts. The model cannot supply its own observation values through the
new wire schema.

The fresh `tracetrail-synthetic-v4` suite was reviewed and frozen before v5
inference. It has one development and one held-out case. All records are
invented, with native UTC timestamps. The earlier suites remain unchanged and
are exposed regression material. The new manifest SHA-256 is
`25514d27f154f01662a8f0657f11806c6273189d3d37155c6e6eff6b9d91af16`.

The [v5 protocol](../evaluation/protocol-v5.json) records source and schema
hashes, projection rules, prompts, models, and budgets. Its SHA-256 is
`91adcc1f7e70d6793cc4a9a83f68396177385896789fe5dcb74b907f788b005b`.
The prompt SHA-256 is
`2f26e74763277a642ad5df16652a97c42693ad1fca01532a90d369652768f7c6`.
All methods and models use the same extraction, chronology, report schema,
three-query budget, and decoding settings. V5 changes these parts together.

Local disk traces and genuine offline LangSmith SDK evaluation are the intended
integration. No account, credential, hosted project, upload destination, server,
or deployment is required. Hosted LangSmith is outside scope and is not a
release blocker.

### Reporting-only ablation

A replay of the eight saved v4 suite-v3 outputs replaced only observations with
selected-record projection. Findings, statuses, citations, selections, histories,
and inference timings stayed identical. This made no inference calls and is not
new v5 model evidence. Strict annotation failures fell from 31 to 17 of 32.

| Earlier group | Original support | Reporting-only projected support |
| --- | --- | --- |
| Qwen adaptive | 12.5% | 62.5% |
| Qwen fixed | 0% | 0% |
| Gemma adaptive | 0% | 62.5% |
| Mistral adaptive | 0% | 62.5% |

The saved artifact is `local-results/reporting-ablation-v4.json`, SHA-256
`43e3caec1b8a4e617c1c190f5aab0c3a68f80ced7c0ea6a75446af259426e67d`.
This isolates a mechanical extraction benefit. It does not show improved model
reasoning, query planning, or citation selection.

### Actual exposed-case Qwen regression

Four real v5 investigations completed on the two exposed v3 cases. The offline
SDK replay verified all four outputs and produced 88 feedback items with
uploads and new inference disabled. Actual inference traces contain nine model
spans and nine tool spans. Saved metrics and feedback recomputed exactly.

| Qwen adaptive | V4 actual | V4 reporting-only projection | V5 actual |
| --- | --- | --- | --- |
| Mean exact support | 12.5% | 62.5% | 75% |
| Mean recall | 87.5% | 87.5% | 75% |
| Mean status accuracy | 75% | 75% | 75% |

V5 fixed-search mean support remained 0% and recall remained 37.5%. Adaptive
v5 averaged 1.5 queries and 95.34 seconds; fixed averaged three queries and
38.73 seconds. Higher support primarily reflects extracted fields. It does not
establish a temporal reasoning fix. The adaptive development report still
refuted missing caller history while saying it could not be verified. Another
finish decision contained a query and said it would execute it, but returned
`action=finish`. The graph honored that action and left the later denied request
unretrieved. These failures remain visible.

Regression raw results SHA-256:
`c02f6f7f2c01e770146aa33c1c5fdfd4e7518c635395a2feb77ded9610220f07`.
Offline SDK artifact SHA-256:
`7e74fd9bf06dc0c1cac5da41f8257db72938b59156697ac85fabd1532440bff8`.

### Fresh comparison and CLI validation

Eight real investigations completed on the fresh v4 suite. There was one run
per model, method, and case cell. Each group below contains two cases, one per
split. Precision was 100% in every group. The unchanged scorer and frozen
annotations recomputed exactly. The numeric results and hashes are saved in
[results-v5.json](../evaluation/results-v5.json).

| Model and method | Mean recall | Mean exact support | Mean status accuracy | Strict annotation failures | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen adaptive | 87.5% | 62.5% | 87.5% | 3/8 | 2 | 4 | 110.83 |
| Qwen fixed | 50% | 25% | 50% | 6/8 | 3 | 1 | 34.88 |
| Gemma adaptive | 100% | 75% | 100% | 2/8 | 3 | 4 | 138.16 |
| Mistral adaptive | 62.5% | 37.5% | 62.5% | 5/8 | 3 | 4 | 80.13 |

The split rows remain separate in the numeric artifact. Qwen adaptive retrieved
all four relevant development records, with 75% support and 100% status
accuracy. On the held-out case it retrieved three of four relevant records,
with 50% support and 75% status accuracy. It again refuted missing caller
history while saying that history could not be verified. Its correct ordering
of the development case across midnight does not establish a general temporal
reasoning fix. These cases are now exposed for future development.

Sixteen of 32 fresh findings failed strict annotations. Every failure included
a missing required citation. Eight also had a status mismatch, and 12 lacked
required field observations; these counts overlap. Required facts from
unselected or unretrieved events remain missing. All emitted projected facts
resolved exactly, but exact values do not verify finding meaning. This failure
count is not a count of proven hallucinations. The sample is too small for a
model ranking or a reliability claim.

Fresh inference traces contain 26 model spans and 22 tool spans. The genuine
offline SDK replay evaluated all eight outputs and produced 176 feedback items,
with uploads and new inference disabled. The Qwen weight digest matches the
preserved v4 baseline. Effective digests were constant within each model's
batch. All frozen source, schema, prompt, and manifest hashes matched after
the runs. No source or prompt changes were made during the comparison.

Fresh raw results SHA-256:
`81b39950761798f8d49cef49555338d648695918670c7c015cd3b5641e71744f`.
Offline SDK artifact SHA-256:
`c4b87252c549f3e2ae3318ea485f3817d87474defbfc6592a123c3745c3a26a2`.

The real CLI demo used `dev-midnight-role-change` from the same manifest. It
completed in 120.52 seconds with four model calls and two queries. It selected
all four relevant events and emitted 113 exact observations. Precision, recall,
and status accuracy were 100%; strict annotated support was 75%. This separate
demonstration is not an additional benchmark cell. Its saved raw artifact is
`local-results/demo-v5.json`, SHA-256
`3c43cfa0d2842afedae2252cb058d9795deee3e4b8e44447d687a3654bb59a16`.

This increment made 13 actual local investigations in total: four exposed-case
regressions, eight fresh comparisons, and one demo. Their trace trees contain
39 model spans and 33 tool spans. The 12 comparison outputs received 264 real
offline SDK feedback items. Raw logs, model responses, and trace trees remain
in ignored local files with mode `0600`. Only the synthetic fixtures, numeric
summaries, protocol fingerprints, and artifact hashes are versioned. Ollama had
no loaded models after the final demo.

Local verification passed Ruff lint, formatting, and all 292 tests. Tests use
clearly separated mocks where needed; capability evidence above comes from
actual Ollama calls. Exact-commit CI is available in the repository
[Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

### Remaining release checks

- Improve finding-specific citation selection without adding citations from
  annotations or repairing failed model decisions after the fact.
- Distinguish missing evidence from refutation, and retain contradictory
  statuses, narrative, and unused-query failures as evidence.
- Test premature finish decisions and temporal reasoning on more independent
  cases, with repeated runs and manual semantic review.
- Keep reporting gains separate from retrieval, planning, and reasoning gains.
  Local SDK evaluation is complete; hosted credentials are not a blocker.

## October 14: protocol v4 and suite v3

The October 14 source defined `tracetrail-v4`. Its planner receives an inventory of
observed candidate filters and actual attempted query scopes. The model still
chooses its queries. The inventory does not supply answer annotations or force
a search. The prompt distinguishes use of a caller key from use of a returned
temporary key, and use of a key from the event that issued it. It also asks the
model to consider changed source addresses and context outside a one-hour
window. Pagination and every follow-up query share the three-query budget.

All four earlier cases have now been inspected. Their original development and
held-out labels remain in the preserved artifacts. They are exposed cases for
future protocol changes and cannot provide an untouched held-out test of v4.
Their outputs and failures remain available; they are not replaced by later
results.

The new frozen suite is `tracetrail-synthetic-v3`, in
`evaluation/cases-v3.json`. It contains one development case,
`dev-caller-and-child-pivot`, and one held-out case,
`heldout-issued-key-chain`. Its manifest SHA-256 is
`6a1a27484de6015f001c1c9d4dd05c7d5f25dda185dd0063935d5c3abb71053d`.
The manifest and source fixture hashes were checked before the v4 comparison.
The fixture files, annotations, and earlier suites remain separate.

V4 uses a 3,200-token output allowance for every model and method. Its prompt
allows up to 32 field observations, and its schema accepts up to 40. The
query budget remains three. V4 changes instructions, query capabilities, and
output allowance together. Any difference from v3 therefore has several
possible causes and cannot isolate the effect of the coverage inventory.

The frozen protocol is recorded in [protocol-v4.json](../evaluation/protocol-v4.json).
Its file SHA-256 is
`2ef24248b2bcc5607444dbb200139f90dc8aa356e3400e0b359daa5f723125b1`.
The frozen prompt SHA-256 is
`1592e44d335c044e5f06b6ddfc0a0fbdb62431b42adee86e5f0240811ab37db2`.
The file records the source, schemas, tool-query schema, model tags, manifest
hashes, decoding settings, and budgets used by the comparison.

Final local source verification passed Ruff checks, formatting, and all 220
tests. CI status tied to each commit is available in the
repository [Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

The local SDK evaluation uses saved inference outputs with
`upload_results=False` and a client transport that blocks API requests. It does
not run a second model or create a hosted experiment. No hosted LangSmith UI or
licensed local server is configured. See [the evaluation guide](../evaluation/README.md)
for the comparison contract and limits.

### Exposed-case Qwen regression

All eight v4 Qwen investigations completed: adaptive and fixed search on each
of the four exposed v2 cases. There was one real inference run per cell. The
audit recomputed all saved metrics from the frozen records and verified the
offline SDK feedback against them. These are regression results. The original
held-out labels do not make those inspected cases fresh tests of v4.

| Protocol | Method | Mean precision | Mean recall | Mean exact support | Strict annotation failures | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v3, preserved | adaptive | 100.00% | 66.25% | 30.00% | 15/21 findings | 1.00 | 3.00 | 86.23 |
| v4 | adaptive | 95.00% | 60.00% | 46.67% | 11/21 findings | 1.00 | 3.00 | 103.04 |
| v3, preserved | fixed | 95.83% | 90.00% | 46.67% | 12/21 findings | 3.00 | 1.00 | 60.59 |
| v4 | fixed | 95.83% | 95.00% | 50.83% | 11/21 findings | 3.00 | 1.00 | 72.18 |

Each mean covers all four cases. Exact support is the per-case mean of findings
that pass all fixed annotation requirements. The failure column is the total
count across 21 findings per group; it is not a count of failed investigations
or proven semantic hallucinations.

V4 adaptive support increased on these exposed cases, while precision and
recall decreased and latency increased. Adaptive search still used one query
per case and missed context. The coverage gap remains. Fixed search had higher
v4 recall and exact support. This regression does not establish an adaptive
advantage, and its composite changes cannot isolate the inventory's effect.

Both v4 maintenance reports also marked persistent disruption as refuted based
on a prior `StartLogging` request. They acknowledged that `GetTrailStatus` had
`responseElements=null`. Those records do not establish the actual trail state,
so this remains a semantic error even though each report passed structural and
field-value validation. The fresh-suite review below records a further semantic
error.

The real investigation trace trees contain 16 model spans and 16 query-tool
spans. The genuine offline LangSmith SDK evaluation replayed all eight saved
outputs and produced 176 feedback items. Its artifact records
`upload_results=false` and `inference_rerun=false`, and its source hash matches
the raw results. The replay did not produce new inference. The client transport
blocks hosted API access.

The local files are `regression-v4-suite-v2.json`,
`regression-v4-suite-v2.audit-summary.json`, and
`regression-v4-suite-v2.langsmith-local.json`. They remain in ignored
`local-results/` with the earlier artifacts. Raw results SHA-256:
`e3277416799b390db76a8fced5b490c11ce19bd6d7815db045b834638f43da11`.
Offline SDK artifact SHA-256:
`a2c6d4195438a023e402a7f92f6bd7ac6eb2f6281f3374d441d6a13bc755673e`.

### Fresh v3 suite with frozen protocol v4

All eight investigations completed with valid report structure and field
observations: three adaptive models on two cases, plus the fixed-search Qwen
control. The source, schema, protocol, prompt, and fixture hashes matched the
frozen comparison. There was one actual local inference run per cell.

| Model | Method | Mean precision | Mean recall | Mean exact support | Mean queries | Mean model calls | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 100.00% | 87.50% | 12.50% | 2.00 | 4.00 | 147.27 |
| `qwen3.8:27b-q4_K_M` | fixed | 58.33% | 37.50% | 0.00% | 3.00 | 1.00 | 70.54 |
| `gemma4:31b-it-q4_K_M` | adaptive | 100.00% | 100.00% | 0.00% | 3.00 | 4.00 | 165.19 |
| `mistral-small3.2:24b` | adaptive | 100.00% | 100.00% | 0.00% | 3.00 | 4.00 | 109.34 |

The splits remain separate below. Each split contains only one case, with one
inference run per model and method. Precision and recall are shown as P/R.

| Model | Method | Development P/R | Development exact support | Held-out P/R | Held-out exact support |
| --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 75.00% | 25.00% |
| `qwen3.8:27b-q4_K_M` | fixed | 50.00% / 25.00% | 0.00% | 66.67% / 50.00% | 0.00% |
| `gemma4:31b-it-q4_K_M` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 100.00% | 0.00% |
| `mistral-small3.2:24b` | adaptive | 100.00% / 100.00% | 0.00% | 100.00% / 100.00% | 0.00% |

Adaptive search retrieved more relevant evidence than the frozen fixed-search
Qwen control on these two cases. Report support remained weak: 31 of 32
findings failed strict annotation requirements, mostly because of omitted
required fields or citations, with some wrong statuses. This is not a finding
of 31 semantic hallucinations. Gemma and Mistral had correct fixed status labels
for all claims, but their fields and citations did not meet the complete support
contract. Correct labels and high recall did not establish supported reports.

Human review of the Qwen development report confirmed that it recovered all
four relevant records and emitted 15 exact observations. It still refuted the
caller timing claim incorrectly: `AssumeRole` occurred 3.5 hours after
`GetCallerIdentity`, so the claim that it occurred more than one hour later was
supported. The fixed control retrieved one relevant record and selected a
noise record, giving 50.00% precision and 25.00% recall on that case. This review
shows why exact observed fields need correct reasoning and complete support.

The Qwen held-out investigation stopped after two queries and missed the later
denied `DeleteBucket` request. Its 75.00% recall left that sensitive activity
outside the returned evidence, despite an observed temporary-key link that
could support a further pivot.

These two cases do not establish a model winner, broad adaptive advantage, or
production reliability. The exposed-case coverage gap also remains. The v3
suite was frozen before these v4 runs; its outputs have now been inspected and
are exposed for future changes. No prompt or fixture changes were made during
the frozen comparison.

The fresh investigation trace trees contain 26 real model spans and 22 query-tool
spans. The genuine local LangSmith SDK evaluation replayed all eight outputs and
produced 176 feedback items. The saved source hash, recomputed metrics, and SDK
feedback matched. `upload_results=false` and `inference_rerun=false` remain
explicit in the artifact. No hosted trace or experiment was created.

The local raw result is `comparison-v4-suite-v3.json`, with SHA-256
`d87bd8c0ee3760c5f63b468a62db65cf9533ac71ab8251d997f1716b05f11c5e`.
The local SDK artifact is `comparison-v4-suite-v3.langsmith-local.json`, with
SHA-256 `9872f96272d9aff383b3af1ab6781ea03bf3a9317ac9c8fe22a23a3a041f7ee5`.
Versioned numeric results, including every split and cell, are in
[results-v4.json](../evaluation/results-v4.json). Raw records, responses, and
trace trees remain in ignored private local files.

### Actual CLI demonstration and validation totals

The CLI demonstration completed with exit code 0 using real local Qwen
inference. It took 158.14 seconds, made four model calls and two query calls,
and retrieved all four relevant records. Precision and recall were 100.00%,
while exact support was 0.00%. Completion confirms the CLI execution path; it
does not establish report correctness. Its saved file is
`local-results/demo-v4.json`, with SHA-256
`645606a3e56c6a1ea0bad8f24d9470af07abd53c37678526dd1333c96bc18269`.

October 14 validation recorded 17 actual investigations: eight exposed-case
regression runs, eight fresh-suite runs, and this CLI demonstration. Their trace
trees contain 46 real model spans and 40 query-tool spans. Offline SDK evaluation
replayed the 16 comparison outputs and produced 352 feedback items. These counts
exclude the preserved October 13 runs and their earlier SDK evaluations.

## October 13 actual model runs

Development probe `local-results/probe-v1.json` used the real Qwen model. The adaptive report reached the 2,400-token output limit and failed parsing. The fixed report was invalid because it represented absent `errorCode` fields as null observations. The evidence and raw outputs are retained. These failures are separate from later comparisons.

The development comparison in `local-results/development-v2.json` recorded eight real runs. Four reports were valid and four were invalid. The offline LangSmith SDK evaluated all eight with uploads disabled. Earlier trace JSON omitted nested spans because the SDK excludes `child_runs` by default; actual model and tool histories remain in those files. Later protocols use a recursive trace serializer.

The citation format supplied to models was then changed to short local aliases. Each report alias resolves to the original file hash and record index. The final stored report uses full citations. This change reduces output length and does not relax field or citation validation.

The measured October 13 protocol was `tracetrail-v3`. The first real Qwen adaptive run completed with no validation errors. Its local trace has 3 model spans and 1 query-tool span. The observation schema distinguishes absent fields from fields with a JSON null. The October 13 comparison used the corrected `tracetrail-synthetic-v2` suite with the same frozen `tracetrail-v3` prompt and budgets. The older v1 comparison was stopped while waiting for the model lock; its 13 completed cell records remain intact, and it is not a complete benchmark. No prompt changes were made from held-out outputs during that comparison. All 16 corrected-suite investigations completed with valid reports: three models across four cases, plus a Qwen fixed-search control for each case. The actual local trace trees contain 46 model spans and 34 query-tool spans. The offline LangSmith SDK evaluated all 16 saved outputs and produced 352 feedback items with uploads disabled. These counts were verified from the saved JSON, including matching source hashes. This was a working private first increment, not a public release. Raw model outputs, logs, and traces stay in the ignored local results directory.

## October 13 frozen comparison results

One run was recorded per model, method, and case. Each group has four cases:
two development and two held out. Means below include every final-suite run.
The October 13 reports passed structural and field-value validation; this does not
mean every conclusion passed the stricter evidence-support annotations.

| Model | Method | Valid reports | Mean precision | Mean recall | Mean annotation support | Mean queries | Mean seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 4/4 | 100.0% | 66.2% | 30.0% | 1.00 | 86.2 |
| `qwen3.8:27b-q4_K_M` | fixed | 4/4 | 95.8% | 90.0% | 46.7% | 3.00 | 60.6 |
| `gemma4:31b-it-q4_K_M` | adaptive | 4/4 | 100.0% | 78.8% | 42.5% | 1.75 | 104.4 |
| `mistral-small3.2:24b` | adaptive | 4/4 | 86.7% | 82.5% | 55.8% | 2.75 | 85.5 |

Annotation support is a per-case mean of fixed propositions that pass all
status, citation, and field requirements. It does not score free prose.
Qwen's adaptive flow used one follow-up query per case and missed context.
The same-model fixed search retrieved more relevant context and had higher
annotation support here. This small suite does not establish a model winner
or prove that adaptive investigation improves quality.

Development and held-out support remain separate:

| Model | Method | Development support (2 cases) | Held-out support (2 cases) |
| --- | --- | --- | --- |
| `qwen3.8:27b-q4_K_M` | adaptive | 26.7% | 33.3% |
| `qwen3.8:27b-q4_K_M` | fixed | 26.7% | 66.7% |
| `gemma4:31b-it-q4_K_M` | adaptive | 26.7% | 58.3% |
| `mistral-small3.2:24b` | adaptive | 45.0% | 66.7% |

Raw reports, model outputs, query transcripts, and SDK trace trees remain in
ignored `local-results/` files with `0600` permissions. They were not pushed.
The local files are `comparison-v3-suite-v2.json`,
`comparison-v3-suite-v2.summary.json`, and
`comparison-v3-suite-v2.langsmith-local.json`.

Result bytes SHA-256: `2ddeddc0ccfa5bfed5808272e9b0a47c1f70b3384d7f5d4bbc20b7aa3f2c7d27`.

Frozen prompt SHA-256: `130be495ef3ec09a4188db8e7c7e29d173003b70ce677b335cb25e4c1451683a`.

## CloudTrail fixture review

Independent review against official AWS documentation found incorrect STS read-only flags, credential issuance dates, and a read-only GetTrailStatus response in v1. The separate v2 suite corrects these fields. Its maintenance hypotheses keep trail state uncertain, since ordinary CloudTrail logs omit that API response. V1 fixtures, annotations, hashes, and results remain intact. These corrections came from AWS documentation, not held-out model outputs. See [the evidence guide](cloudtrail.md).

The v2 manifest hash is `c30eb66718886e6a3d80efe1f034bf913634c9e839873e6fcb30d8f222e90446`.

## Release checks still open

- Inspect actual model failures and compare held-out performance without changing the frozen suite or prompt in response to held-out results.
- Expand independently authored cases and human evidence-support review before making a reliability claim.
- Evaluate response stability with repeated runs. One run per cell does not measure variance.
- Inspect free-text limitations for unsupported language. Automated support scoring applies to fixed propositions and exact field observations.
- Add licensed public simulation data only after license and privacy checks. Label it as simulation.
- Improve large-file performance and evidence selection for records that exceed the model prompt budget.
- Broader release review remains separate from CI. Final local v7 verification passed lint, formatting, and all 518 tests. Earlier source checks remain recorded in their dated sections. CI status tied to each commit is available in the repository [Actions workflow](https://github.com/Shanmukha-Y/tracetrail/actions/workflows/ci.yml).

Local disk traces and offline LangSmith SDK evaluation are the intended integration. Hosted and self-hosted platform UI deployments are outside this local-only project. No credential, server, or upload setup is needed.

## Support metric interpretation

The `unsupported_claims` counter reports failures of the strict field and citation annotations. A missing required observation or citation can fail this check even when the status label is correct. It is not a count of proven semantic hallucinations. The scorer does not evaluate planner reasons or narrative limitations. Development-only assistant source review found incomplete search windows, premature finishes, and language that overstated what an absent API error establishes. These remain release risks.
