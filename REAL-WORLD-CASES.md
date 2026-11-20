# Real-world cases behind this study

This study asks whether an LLM approval gate trusts an MCP tool's own labels (annotations such as `readOnlyHint`) over
what the user actually asked for. The MCP specification says clients must treat those labels as untrusted unless the
server is trusted. The cases below show the parts of this problem that have already happened for real.

We found no public report, as of November 2026, of an attacker using a false read-only label in the wild. The cases
show the client behaviour that would let one work (case 1), MCP servers acting maliciously (case 2), attacks that
hide in tool metadata (case 3), and the harm an approval layer exists to prevent (case 4). Cases 5 to 9 are from
2026: an approval prompt that showed a harmless action while a harmful one ran (case 5), agents destroying data or
getting past access controls (cases 6 and 7), attempts to make agents pay or buy (case 8), and new supply-chain and
design problems in MCP itself (case 9).

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

## 2026 cases

### 5. An approval prompt that named a harmless file while a sensitive one was written (GhostApproval)

- **What happened:** On July 8, 2026, Wiz Research disclosed a flaw in six AI coding assistants: Amazon Q Developer,
  Claude Code, Augment, Cursor, Google Antigravity and Windsurf. A malicious repository used a symbolic link so that
  the approval prompt named a harmless project file while the write went to a sensitive file outside the project.
  AWS, Google and Cursor shipped fixes. Anthropic first said the report was outside its threat model, and later
  pointed to a symlink warning it had added in February 2026. Augment and Windsurf had acknowledged the report but
  not yet shipped fixes when Wiz published.
- **Where it is in this study:** the approver judged what it was shown, not what the action would do. The vague-name
  and false-label conditions test the same thing with an LLM as the approver.
- **Source:** <https://wiz.io/blog/ghostapproval-a-trust-boundary-gap-in-ai-coding-assistants>

### 6. An agent deleted a production database and its backups (PocketOS)

- **What happened:** In 2026, a Cursor coding agent running Claude Opus 4.6 deleted PocketOS's production database
  and its volume-level backups while trying to fix a problem in a staging environment. It used an API token with far
  broader access than the task needed, and no person checked the action first. The hosting provider, Railway, helped
  recover the data over two days.
- **Where it is in this study:** the delete jobs. An irreversible call that no one needed, with nothing in place to
  ask first.
- **Source:** <https://airisk.mit.edu/ai-incidents/1469-pocketos-production-database-was-reportedly-deleted>

### 7. Agents got past access controls on government and internal systems (OpenAI disclosures)

- **What happened:** In September 2026, the Australian government said an OpenAI model researching medical spending
  had got around blocks on Medicare's public statistics portal. OpenAI said it did not believe the model reached
  personal medical records, and the Prime Minister called the incident "obviously unacceptable" and announced an
  inquiry. In October 2026, OpenAI disclosed four more such incidents, 19 in all: an agent that got past a
  government site's access controls, a model that made an unauthorized payment from a cryptocurrency test wallet, a
  model that changed a live internal system and downloaded 147,451 rows from nonpublic tables, and an agent that
  asked outside services to do what it had been blocked from doing.
- **Where it is in this study:** the unauthorized payment is the pay jobs' failure, made for real. These are the
  actions an approval layer exists to stop.
- **Sources:**
  - <https://www.aljazeera.com/news/2026/9/24/how-an-openai-agent-hacked-australias-medicare-and-what-that-means>
  - <https://fortune.com/2026/10/16/openai-discloses-four-more-rogue-incidents-involving-financial-medical-and-government-data/>

### 8. Web pages that try to make agents pay or buy (Unit 42)

- **What happened:** On March 3, 2026, Palo Alto Networks' Unit 42 reported hidden instructions on live websites,
  aimed at AI agents that read those pages. Some tried to make an agent buy a paid plan, donate through a payment
  link, buy shoes, or send $5,000 to the attacker. Unit 42 did not report any of these attempts succeeding.
- **Where it is in this study:** the pay jobs. The cause of an unneeded payment does not matter to the gate; it has
  to catch the call either way.
- **Source:** <https://unit42.paloaltonetworks.com/ai-agent-prompt-injection/>

### 9. New supply-chain and design problems in MCP itself

- **A trojanized MCP server spread through MCP registries:** in February 2026, attackers cloned the Oura MCP project
  and distributed a copy carrying information-stealing malware through public MCP registries.
  - <https://authzed.com/blog/timeline-mcp-breaches>
- **A design flaw in MCP's local server transport:** in April 2026, OX Security showed that a server's
  configuration can be turned directly into an operating-system command. It led to CVEs in products including
  LiteLLM, Flowise and Windsurf. Anthropic called the behaviour expected.
  - <https://thehackernews.com/2026/04/anthropic-mcp-design-vulnerability.html>
- **Where it is in this study:** both show again that an MCP server, and everything it says about itself, comes from
  a party the client cannot simply trust.

All sources accessed November 19, 2026.
