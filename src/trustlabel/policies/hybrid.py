# V5 · Hybrid, computed on the stored calls: https://github.com/yashlad1/trust-the-label/issues/16
# FP3 task 9 (fp3-tasks.html): the hybrid baseline
"""The hybrid policy, computed on the stored calls and never run live.

A read-only label allows the call without the LLM; anything else takes the call's gate-with-labels decision under
the same label and warning.
"""

from trustlabel.contracts import Decision, Labels


def hybrid(labels: Labels | None, gate_with_labels: Decision) -> Decision:
    if labels is not None and labels.read_only is True:
        return Decision("allow", "hybrid: read-only label")
    return gate_with_labels
