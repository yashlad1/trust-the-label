# V2a · never_ask policy: https://github.com/yashlad1/trust-the-label/issues/11
# V2b · label_rule policy: https://github.com/yashlad1/trust-the-label/issues/12
# FP3 task 8 (fp3-tasks.html): never_ask and label_rule
"""The rule policies, as plain functions; reference lines on the stored calls."""

from trustlabel.contracts import Decision, GateInput


async def never_ask(g: GateInput) -> Decision:
    """Allow every call."""
    return Decision("allow", "never ask")


async def label_rule(g: GateInput) -> Decision:
    """Allow a call whose label says read-only; ask about everything else. 
    
    On our labels, which never set openWorldHint, this is the decision Codex CLI makes in its Auto and Writes tool-approval modes (openai/codex, codex-rs/core/src/mcp_tool_call.rs, requires_mcp_tool_approval, tag rust-v0.169.0)."""
    read_only = g.labels is not None and g.labels.read_only is True
    return Decision("allow" if read_only else "ask", "label rule")
