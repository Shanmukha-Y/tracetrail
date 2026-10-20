# Automated test scope

The current suite collects **50 cases in 16 modules**, including every
parameter variant. It previously collected 734 cases in 23 modules at commit
`0ed8396`. The cleanup started from a clean worktree, with one writer and two
read-only coverage audits. Runtime code, dependencies, scripts, fixtures,
protocols and model measurements did not change.

Forty-seven existing cases remain. The cleanup deletes 687 old collected cases
and adds three explicit checks: a file-byte limit, unknown tool input before
store execution, and the collection limit. The first two replace individual
behaviors from deleted multi-scenario tests. Tests were not merged, moved,
skipped or filtered to meet the limit. Removed variants are no longer tested.
Test-data helpers use ordinary helper names rather than collection-disable flags.

## Retained coverage

- Local weights and approved tags; raw remote-routing metadata; real sync and
  async client construction with loopback, proxy, redirect and ambient-key
  controls; the separate model-session transport; private atomic result writes
  and preservation after a failed serialization.
- Exact source citations, immutable returned records, combined filters and UTC
  bounds, duplicate event IDs, deterministic pagination, copied-query limits,
  file-byte limits and real LangChain tool rejection of unknown input.
- Real LangGraph execution with test-only models: three queries/four calls,
  exact candidate filters, mutually exclusive branches, extra schema fields,
  tested-scope validation, parse and tool failures, alias resolution, required
  support roles and explicit uncertainty gaps.
- Caller-versus-returned credential direction and reverse lookup; graph context
  derived only from observed fields; hidden-record and answer-label canaries;
  actual JSON null versus absent fields.
- Strict claim-local scoring: a complete positive report, no credit from global
  facts, other claims or same-valued unrelated records, exact JSON types,
  altered-source rejection, fixed statements, invalid-process gating and
  retained failed-run denominators.
- Real offline LangSmith SDK replay with network forbidden, tracing-context
  isolation and source preservation; frozen-source and model-digest checks,
  failed-attempt retention, resume-payload tamper rejection, public-summary
  privacy canaries and review-hash binding; sampler cleanup on investigation
  failure.

These are behavior and integration checks, with clearly test-only models.
Record-building loops and checks over one report's fields remain. No removed
parameter matrix was converted to a loop or an omnibus test.

## Before and after inventory

| Test module | Before | Retained |
| --- | ---: | ---: |
| `test_agent.py` | 56 | 7 |
| `test_budget.py` | 0 | 1 |
| `test_cases_v4.py` | 14 | 0 |
| `test_cases_v5.py` | 23 | 0 |
| `test_cases_v6.py` | 29 | 0 |
| `test_cases_v7.py` | 15 | 0 |
| `test_claims.py` | 70 | 0 |
| `test_cli.py` | 10 | 3 |
| `test_coverage.py` | 49 | 0 |
| `test_credential_context_integration.py` | 7 | 1 |
| `test_credential_map.py` | 27 | 1 |
| `test_evaluation.py` | 41 | 0 |
| `test_facts.py` | 49 | 1 |
| `test_fresh_cases.py` | 19 | 0 |
| `test_local_model.py` | 11 | 5 |
| `test_pilot.py` | 28 | 4 |
| `test_pilot_summary.py` | 31 | 2 |
| `test_planning.py` | 58 | 1 |
| `test_planning_integration.py` | 13 | 4 |
| `test_resources.py` | 31 | 1 |
| `test_scorer_dispatch.py` | 25 | 1 |
| `test_store.py` | 64 | 8 |
| `test_support_evaluation.py` | 52 | 9 |
| `test_telemetry.py` | 12 | 1 |
| **Total** | **734** | **50** |

Dedicated historical fixture, legacy global-score, coverage-catalog and claim
validation matrices were removed. Representative claim checks remain in graph
and strict-scorer tests. The historical fixture JSON, annotations, builders,
measured results and their hashes remain intact.

## Deliberate coverage risks

This is reduced coverage, not an equivalent replacement for 734 cases. Many
malformed JSON/type/length combinations, exhaustive schema fields and failure
phases, legacy replay variants, fixture-builder regressions, graph continuation
edges, summary draft/adjudication/locked-stage boundaries,
ingestion symlink/directory edges, and sampler transport, deadline and
worker/process-accounting limits no longer have direct regression tests.
The direct LangSmith client transport matrix is gone; the retained actual SDK
replay forbids socket connections and checks that uploads remain disabled.
There is no longer a separate generic SDK span-serialization smoke test;
actual graph behavior and active offline replay remain covered. New work must
replace a lower-priority case within the budget when it changes these areas.

The existing pilot auditor was run against the saved raw batch and SDK artifact.
It checked all 40 original investigations and re-derived their counters, source
identities and traces without new model calls. This is stored-evidence
validation, not a new benchmark or a relocated test suite. Original model
results remain separate from automated test counts. Historical reports of 703
or 734 passing preflight tests describe those earlier revisions.

## Collection guard

Root `conftest.py` counts each `pytest_itemcollected` event and fails collection
above 50, including parameter cases and cases later deselected with `-k` or
`-m`. It never removes or changes items. CI still uses the ordinary complete
`pytest -q` command; collection paths and exclusions were not changed. The
focused guard test supplies collector metadata rather than generating or
nesting more tests. The complete 50-case run checks the allowed boundary.

```sh
uv run pytest --collect-only -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```
