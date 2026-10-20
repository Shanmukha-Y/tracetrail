# TraceTrail roadmap

TraceTrail is a local, read-only CloudTrail investigation experiment. The
five-model development pilot is complete. Its exposed cases do not establish
held-out reliability. See [measured progress](docs/progress.md) and the
[pilot results](docs/model-pilot-results.md).

## Current increment

The [two-case Qwen method check](docs/heldout-v9.md) has frozen inputs for eight
assignments: two fresh synthetic cases, adaptive and fixed search, and two
paired repeats. Source review passed before inference. The cases test denial,
read-only activity, wider query scopes and insufficient resource-state or
approval evidence. They are a chosen stress/control pair, not a representative
sample of incidents.

The actual run depends on exclusive sequential use of the local Ollama server.
The runner blocks while another application's model is loaded. Preserve this
boundary, the study freeze and all attempted failures. Publish results only
from recorded inference and matching local offline SDK evaluation.

## Next evidence

- Complete all frozen assignments, exact source and trace audits, and
  source-aware report review. Separate unavailable or invalid reports from
  unsupported definite conclusions.
- Expand to the [larger fresh-case study](docs/benchmark-plan.md) only after
  inspecting measured costs and limits. Freeze new cases before using them.
- Obtain independent human review before making stronger semantic reliability
  claims. Keep current assistant reviews labelled as such.
- Test any planning-schema repair on exposed development data under a separate
  freeze. It must not change this held-out study after outputs are seen.

Keep the repository public. Keep logs, raw outputs, trace trees and SDK feedback
local. Hosted LangSmith, cloud inference, live AWS, remediation, deployment,
public attack samples without licence/privacy review, and social posting are
outside this increment. Keep at most 50 collected automated test cases.
