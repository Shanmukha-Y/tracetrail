# Per-finding evidence links and uncertainty

This diagnosis reviews the eight actual v5 runs preserved in
`local-results/comparison-v5-suite-v4.json`, against the frozen v4 case
annotations. All source records are synthetic, and all reviewed cases are now
exposed for future development. No inference was rerun and the artifact was
not changed. Its SHA-256 is
`81b39950761798f8d49cef49555338d648695918670c7c015cd3b5641e71744f`.

## What failed

Of 32 fixed findings, 16 fail at least one strict annotation requirement. All
16 include `missing_required_citation`; 12 also include
`missing_or_wrong_required_observation`, and eight include `status_mismatch`.
These reasons overlap and are not a hallucination count.

Only four failing findings are citation-only omissions: all required records
were selected, and their statuses and required fields pass. Twelve failing
findings require at least one record that was never retrieved. Six omit at
least one available selected citation; two of those also have a retrieval gap.
Across the 16 failures there are 22 missing claim/source citation requirements:
15 refer to never-retrieved records and seven to selected but uncited records.
The shared citation failure therefore does not imply a citation-only repair
would solve all 16 findings.

Seven of the eight status mismatches use cautious `uncertain` labels after
incomplete retrieval. They still fail the end-to-end task because the supplied
corpus contains the evidence the investigation should have found, but they
are not equivalent to asserting an unsupported answer. The remaining mismatch
is a clear overclaim: Qwen adaptive refutes a prior-caller-history proposition
because its earlier record was not returned. Absence from retrieved context
does not contradict the proposition.

## Where the report contract loses the evidence chain

The v5 projector supplies exact fields globally from model-selected records.
It does not show which fields establish each finding. A structurally valid
finding can cite one real record while omitting a linking record needed for
the composite statement. For example:

- Qwen supports the empty-description request using the role-update action
  at record `/2`, but omits selected issuance record `/1`, which establishes
  the returned-key session relationship.
- Gemma refutes successful deletion using the denied deletion at `/3`, but
  omits selected read record `/2`, needed for the stated same-object context.
- Gemma correctly leaves approval uncertain but cites `/2` and `/3` without
  selected issuance record `/1`, which supplies the session-name context.

Record indexes here are zero-based within their respective synthetic fixture;
the saved reports retain full file-hash/index citations. These are concrete
citation-support gaps, including findings whose status is correct.

The strict scorer checks annotated statuses, required citation subsets, and
required fields in a global observation pool. It does not check whether a
finding's explanation entails its statement. It also does not penalize every
extra valid citation. Citing all selected records would satisfy some subset
checks without demonstrating a relevant evidence chain.

## A defensible v6 contract

Require the model to declare bounded evidence links for each finding: an
actual selected-record reference, exact field paths, an evidence role such as
support, contradiction, or context, and a brief rationale. Ask for unresolved
components or missing evidence before the status decision. Distinguish context
not searched, scoped searches without matches, absent or null fields, and
external evidence unavailable in the supplied logs.

Public finding citations may be derived mechanically from those explicit
model-authored links. The application must not choose additional references,
change status, expand selected records, issue hidden queries, or use case
annotations to close a missing link. Refutation should identify contradictory
evidence; missing retrieved context alone warrants uncertainty. A schema can
require that declaration but cannot guarantee the declaration is truthful.

Mechanical validation can check reference membership, field existence and
exact values, bounded output, and consistency of the declared structure.
Incorrect or incomplete outputs must remain visible as failures. These checks
do not guarantee semantic entailment, relevance, or complete coverage of a
compound statement. Avoid blanket minimum citation counts and a rule to cite
every selected record.

## Measurement boundaries

Keep the historical strict scorer unchanged. Report a separate descriptive
measure of annotation-required field paths appearing in the model's explicit
links, scoped to the corresponding finding and source record. Measure these
requirements independently of the global projected observation pool, and
disclose denominators and unavailable reports. Field-path coverage is an
annotation-coverage measure, not proof that the model used a field correctly
or that its rationale follows from it.

Separate retrieval and selection gaps, citation-support gaps, status accuracy,
reasoning conditional on retrieved evidence, and deterministic extraction.
Preserve raw outputs, failed reports, and existing scores. Freeze the new
prompt, schema, sources, and equal budgets before prospective model runs;
previously exposed cases serve as regressions. Actual capability claims need
actual inference under that frozen contract. Any reporting-only replay must
be labeled as an ablation, not a new model result.
