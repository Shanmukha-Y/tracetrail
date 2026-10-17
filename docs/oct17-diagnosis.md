# Planning scope and premature finish

This diagnosis uses the 16 actual v6 runs preserved in
`local-results/comparison-v6-suite-v5.json`, SHA-256
`c7eee979197141a84287391810ac42df226a8ad06ef270f267772a7ca80c1be2`.
All source records are synthetic. All four cases and their outputs are now
exposed regression material. No result was changed or rerun for this review.
The measured results remain in [progress](progress.md) and the
[v6 numeric summary](../evaluation/results-v6.json).

## The missing searches were model choices

Every Qwen adaptive run finishes after one query. At the actual finish call,
the application reports two queries remaining and a catalog of 11 candidates,
ten unsearched. No catalog is truncated and no query reports a tool error.
The graph honors the model's explicit `finish`; it does not lose a requested
query or execute a search mentioned only in prose.

| Exposed case | Missing local context at finish |
| --- | --- |
| Key lifecycle | Original-caller activity remains unsearched after querying the returned temporary key's uses. The model calls earlier history out of scope despite the original-key candidate. |
| Network denial | After finding the issuer, the model leaves later DescribeSecurityGroups activity unsearched and calls the remaining scope untestable. |
| Publication denial | After finding issuance, the original-key candidate remains unsearched. The planner calls prior caller history untestable despite two remaining query slots. |
| Encryption state | Issuance is retrieved, but earlier original-caller and later temporary-key activity remain unsearched. The planner treats missing returned records as a limit of the available budget. |

Not every unsearched candidate is relevant or worth querying. The failure is
the model's unsupported claim that visible local scope cannot be tested, not
failure to spend every slot. The tools expose exact caller-key and issued-key
filters, and executed queries follow their recorded predicates. More prose
about the existing catalog alone is not a demonstrated fix.

## Query intent and executed scope diverge

Gemma's key-lifecycle investigation retrieves the relevant chain, then spends
its third query on a `principal` filter for the target user while describing
changes against that user. That filter matches calls made by the identity,
not requests targeting it. Its zero matches therefore do not test the stated
target-key question. In encryption, the rationale promises a same-key read
search, but the query filters only event name and time. Both returned reads
happen to target the same KMS key; the tool has no resource-ID predicate.
The extra read by another caller can be useful resource context and should
not automatically be labeled irrelevant because it is outside the required
annotation set. Gemma also stops the network case after one query, leaving
later read context unsearched.

Mistral's key-lifecycle query uses the target key as `access_key`, whose
meaning is the caller credential. Another search uses a one-hour lookback
that excludes the earlier caller event, then incorrectly refutes prior
activity from that scoped absence. Only context links accompany that
refutation, so the structural contradiction-role guard rejects the report.
Searching uses of an observed target credential can be legitimate; it simply
does not retrieve an action against that credential.

In encryption, Mistral searches original-caller history with an assumed-role
principal and a window excluding the original caller's event. Some rationales
also promise event-name predicates absent from the submitted queries. These
are model scope and identity mistakes. The query engine does not silently
apply the predicates the model described but omitted.

Mistral's network and encryption reports select invented `/evidence/*` paths
instead of supplied aliases. Their failures and partial findings remain
preserved, with no reference repair. All four network status labels match the
annotations, but that does not make its invalid selection a working report.

## Planning structure is not semantic verification

Qwen and the one completed Mistral publication report treat AccessDenied as a
contradiction of business approval. Denial contradicts successful upload, not
approval of the attempt. A declared `contradicts` role can pass structural
validation while carrying that false inference. Other reports support a
compound credential-provenance statement without retrieving its issuance
record, even when the resulting status happens to match the full corpus.
A planning ledger cannot certify these judgments.

## Focus of the v7 change

V7 makes model planning choices and their scope explicit within the existing
planning call. A bounded ledger covers each supplied claim with evidence
references, an open question, candidate IDs, and actual attempt IDs. The model
then chooses a candidate's exact filter, a pending continuation, a custom
query, an event lookup, or finish. The catalog supplies source paths and the
meaning of its filters; it neither searches the store nor supplies answers.

Finish excludes tool arguments and assigns every visible pivot a reasoned
disposition: deferred, not relevant, or tested under a recorded scope. The
last category requires an actual successful matching query; it does not mean
the identity or incident was exhaustively investigated. Pending pages remain
explicit gaps. Early finish remains legal, including a deliberate deferral
with budget left. There is no minimum-query rule, prescribed credential
sequence, annotation-driven query choice, or status repair.

Mechanical validation can check claim coverage, reference and attempt IDs,
exclusive action arguments, remaining budget, and a claimed scoped attempt.
It cannot verify relevance, the truth of an open question, completeness,
business intent, approval, or whether a deferral was sensible. The model can
still make a poor choice or wrongly mark a candidate not relevant.

Invalid planning stops further searches and records the process failure.
The existing final reporting call can still produce a valid selection, exact
facts, and ordinary raw scorer metrics. Those facts do not repair the failed
process: the investigation remains invalid. Reporting failures and planning
failures must remain distinguishable in audits and denominators.

The three-query, four-model-call, and 3,200-output-token limits remain. The v6
reporting contract, projection, scorer, and fixed-search control remain
separate from this planning change. V7 changes planning instructions, schema,
catalog presentation, and structural checks together, so any measured effect
cannot be assigned to one part without an ablation. Freeze independent cases
and the full protocol before prospective inference, preserve every failure,
and report retrieval, query cost, process validity, citation support, and
semantic review separately. This diagnosis supplies no new model result.
