# V8 assistant source review

This review checks model reports against the frozen synthetic source records
and actual query histories. It is an assistant review, not independent human
review. The review sidecars stay in ignored private local files, with each
reviewed row pinned by its canonical hash. The numeric summary records their
file hashes. No model report, query, status or field link was repaired.

Structural validity, selected-event retrieval, annotation support and semantic
correctness are separate. `claim-support-v1` checks each finding's own exact
source fields. Its complete-contract score also requires the fixed statement,
expected status and all required records. A missing API field path is a
provenance failure; it is not automatically a false conclusion. A correct
label can also accompany a false explanation. See the
[measurement contracts](measurement.md).

## Qwen

Three of four adaptive processes and all four fixed processes completed
structural checks. All four adaptive runs stopped after two queries with one
query left. The role-duration case already had its full relevant chain, so an
unused query alone is not an error. The other three left useful local context
untested. Mean selected-event recall was 81.25% for adaptive search and 45.83%
for fixed search. Primary required-atom support was much closer: 24/51 and
23/51. Complete primary claim contracts were 3/16 and 2/16.

The adaptive KMS report makes a definite credential-scope error. It observes
different original-caller and returned temporary keys, then supports the claim
that the seed used the issuer's caller credential by redefining it as a key
issued to that caller. This changes the meaning of the fixed claim. Issuance
does not make two exact access-key values equal. It also leaves an available
original-caller lookup unused while claiming that local queries cannot supply
the missing earlier context.

The adaptive topic process is invalid. It calls an unexecuted child-key use
pivot tested through issuance and original-caller queries. The map accurately
shows those as different directions. Validation rejects the false scope
declaration and retains the partial final report. The role-duration and topic
reports also contain false exhaustion prose while graph counters show one
query remaining. Code does not rewrite these explanations.

The fixed retention report makes another definite error: it treats an observed
`DescribeLogGroups` request as contradicting an unreturned earlier
`DescribeLogStreams` request. Both could occur. A missing query result does not
establish a contrary event or refute the claim.

Other findings correctly preserve uncertainty about approval and later state.
The fixed KMS control avoids the adaptive report's false key equivalence, while
retrieving less context. The fixed topic control distinguishes a denied write
from the later display-name state. Some correct uncertainty findings omit
required context or field links. These omissions remain support failures,
without being relabeled as confident false conclusions.

## Gemma

Two of four processes completed structural checks. Review found all 16 status
labels defensible, with 28/51 raw required atoms and 17/51 primary atoms.
Complete contracts were 2/16 raw and 1/16 primary. These labels and partial
facts do not clear invalid planning or incomplete links.

The role-duration and topic finishes falsely mark principal filters tested by
credential-only queries. The recorded queries did not execute those principal
predicates. Both processes remain invalid. The topic report also dismisses the
available child-key use lookup after seeing the seed, although one query
remains. No read was returned in that subset; this does not establish that no
further useful local query is available.

The KMS run uses three queries in the correct issuance, original-caller and
child-use directions. It retrieves the full relevant chain and correctly
leaves later key state unknown under the null read response. The response ARN
is not used as proof of key state. The retention run also retrieves its full
chain and distinguishes a deletion request from later retention state.

Missing API identity, resource-name, prefix and session-name paths limit
claim-local support. Some additional timestamp links are useful context and
are not automatically irrelevant. An empty link list for an uncertain approval
finding still omits available context. One finish disposition reason overstates observed
credential connections as established causality. Exact field validation does
not certify that phrase.

## Mistral

One of four processes completed structural checks. Eleven of 16 status labels
match the frozen annotations, but raw complete support is 1/16 and primary
complete support is 0/16. Required atoms total 15/51 raw and 5/51 primary.
The four investigations made 14 model calls and eight tool calls.

The role-duration run completes with three queries and correctly distinguishes
the original caller from the returned child key. Its sparse links omit the
required seed, action and context fields. A custom `ApprovedRoleChange` query
returns no matches, yet the final prose says approval events were not searched.
This narrow search does not establish absence of external business approval.
The uncertain approval status is appropriate, while the description of its
own query history is inaccurate.

The KMS and retention runs stop after one query because the next decision
supplies both a candidate ID and a custom query. Validation rejects that
ambiguous choice without selecting a branch or executing a replacement query.
Each leaves two queries unused. Both reports support an issuer-caller
credential claim from child-session signer and session-issuer role fields.
Those fields do not establish the issuing event's caller key. The issuer and
original-caller records were never retrieved. Careful uncertainty about later
state, and a correct request-level retention finding, remain visible alongside
these errors.

The topic report selects invented `/evidence/*` references. Its raw findings
remain available, but it has no valid selected facts or support credit. It
also says an original-caller `GetCallerIdentity` query returned no matches.
The actual query used the child session principal, with no event-name filter,
and returned two records. Same-child-key request and read records do not prove
credential issuance provenance. Its denial refutation and later-state
uncertainty are careful, but cannot clear the invalid selection or unsupported
issuer conclusion.

## Limits

These four cases and one repeat per cell do not establish a model winner,
production reliability or a general planning improvement. The observed map is
exact and exercised in actual inference, but it does not resolve premature
stopping, false scope declarations or unsupported prose. Different suites and
the new scorer also prevent a version-to-version support claim.

At the time of this October 18 review, the repository was private.
Further work needs complete finding links,
better use of unresolved local evidence, repeated independent cases and human
source review. Machine budget counters and exact source facts remain separate
from model judgments.
