# Real-world cases behind this study

This study asks whether an LLM approval gate trusts an MCP tool's own labels (annotations such as `readOnlyHint`) over
what the user actually asked for. The MCP specification says clients must treat those labels as untrusted unless the
server is trusted. The cases below show the parts of this problem that have already happened for real.

We found no public report, as of November 2026, of an attacker using a false read-only label in the wild. The cases
show the client behaviour that would let one work (case 1), MCP servers acting maliciously (case 2), attacks that
hide in tool metadata (case 3), and the harm an approval layer exists to prevent (case 4).

## 1. A client that trusts the server's own read-only label

- **What happened:** An October 2026 issue on the open-source OpenAgent client reports that it set each tool's
  permission level from the `readOnlyHint` the MCP server itself supplied. A server could mark a tool that changes
  data as read-only, and the client would allow the call without asking. The issue is closed.
- **The same design, documented:** Codex CLI requires approval for destructive MCP tool calls unless the tool
  advertises a read-only annotation, which takes priority; its source skips the approval check when `readOnlyHint` is
  true.
- **Where it is in this study:** the label-rule reference line is this client. It allows a call whenever the label
  says read-only, so under a false label it allows every call. The gate conditions test whether an LLM gate does
  better.
- **Sources:**
  - <https://github.com/mj10612/OpenAgent/issues/31>
  - <https://github.com/openai/codex/blob/rust-v0.169.0/codex-rs/core/src/mcp_tool_call.rs>

## 2. A malicious MCP server found in the wild

- **What happened:** In September 2025, Koi Security reported `postmark-mcp` on npm, a copy of Postmark's email MCP
  server that Postmark says was not theirs. Version 1.0.16 added one line that blind-copied every email sent through
  it to an outside address. It had been downloaded 1,643 times before it was removed. Koi called it the first
  malicious MCP server seen in the wild.
- **Where it is in this study:** it shows that MCP servers are untrusted third parties. A server willing to hide a
  blind copy can just as easily label its irreversible tool read-only, which is this study's false-label condition.
- **Source:** <https://thehackernews.com/2025/09/first-malicious-mcp-server-found.html>

## 3. Attacks hidden in tool metadata: tool poisoning and rug pulls

- **What happened:** In April 2025, Invariant Labs disclosed "tool poisoning": instructions hidden in a tool's
  description that the user does not see but the model reads, and that can steer the agent. They also described a
  "rug pull": a server changing a tool's description after the user has approved it.
- **Where it is in this study:** a false label is the quietest form of this attack. It carries no hidden
  instruction, only wrong metadata. Labels that change during a session are not part of the current design.
- **Source:** <https://invariantlabs.ai/blog/mcp-security-notification>

## 4. Irreversible actions with nothing stopping them

- **Replit, July 2025:** an AI coding agent deleted a company's production database during a declared code freeze,
  despite instructions not to make changes without permission.
  - <https://incidentdatabase.ai/cite/1152/>
  - <https://tomshardware.com/tech-industry/artificial-intelligence/ai-coding-platform-goes-rogue-during-code-freeze-and-deletes-entire-company-database-replit-ceo-apologizes-after-ai-engine-says-it-made-a-catastrophic-error-in-judgment-and-destroyed-all-production-data>
- **Amazon Q Developer for VS Code, July 2025:** a malicious change reached version 1.84.0 of the extension through
  an over-scoped GitHub token. AWS says the injected code failed to run because of a syntax error, and replaced the
  release with version 1.85.0 (CVE-2025-8217). Press reports say the injected prompt told the agent to delete local
  files and cloud resources.
  - <https://aws.amazon.com/security/security-bulletins/AWS-2025-015/>
  - <https://www.techradar.com/pro/amazon-ai-coding-agent-hacked-to-inject-data-wiping-commands>
- **Where they are in this study:** these are the failures an approval gate exists to stop. The unneeded version of
  each job is an agent proposing an irreversible action the user did not need, whatever the reason it proposed it.

All sources accessed November 19, 2026.
