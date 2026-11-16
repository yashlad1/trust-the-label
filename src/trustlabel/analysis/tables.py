# V8a · Tables, one set per agent: https://github.com/yashlad1/trust-the-label/issues/23
# V8b · Figures, one set per agent: https://github.com/yashlad1/trust-the-label/issues/24
# FP3 task 18 (fp3-tasks.html): markdown tables in the team's format
"""Markdown tables in the team's format: a title that says what the number means and out of how many, a how-to-read
line, and the source (log files, command, n)."""


def table(title, head, rows, how, source):
    out = [f"**{title}**", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out + ["", f"How to read: {how}", f"Source: {source}", "", ""])
