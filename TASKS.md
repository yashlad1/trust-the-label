<!-- AI-generated (Claude Code): team task list for the final project: owners, small pieces, weeks, and how to work on them -->
# Task division

Who builds what, in small pieces, week by week. Owners and folders match the [README](README.md). The dates
assume the final report and talk fall in the first week of December; we shift the weeks if Canvas says otherwise.

## How the parts connect

```
scenario (Isha) ──► harness (Yash) ──► agent proposes a tool call
                                              │
             does it change state? (Will's list, never the label)
                    │ no                       │ yes
                    ▼                          ▼
             runs on the MCP server    approval policy (Vignesh) ──► allow / ask / block
             (Will)                                                     │ ask
                                                                        ▼
                                              scripted user (Yash, rules from Isha) ──► yes / no
                                              │
final sandbox state ──► scorer (Will) ──► logs ──► analysis (Vignesh)
```

Inspect already provides the two joins we need:

- `mcp_tools(mcp_server_stdio(...))` turns an MCP server into ordinary agent tools.
- `Task(approval=[ApprovalPolicy(approver, tools)])` runs an approver before each matching tool call. An approver
  returns `approve`, `reject` or `escalate`.

So the approval layer is one Inspect approver. Allow means approve, block means reject, and ask means the approver
asks the scripted user, then approves or rejects. Y3 confirms with a mockllm run that this fires on MCP tools too.

## The study design (locked Oct 25, after the FP1 feedback)

- **Stage 1, proposals:** live agents work every job version under both names, with nothing blocking them. Every
  irreversible call an agent proposes is stored with the conversation before it.
- **Stage 2, gate decisions:** every stored call goes to every gate condition: gate on call, and gate with labels
  under each label (true, false, none) with the warning off and on. All gates judge the same calls.
- **Stage 3, live check:** a few conditions run end to end with a real gate, to measure harm and task success and to check
  that live decisions match stage 2.
- Which stored calls count: the main analysis uses the first irreversible call of each stage-1 episode, because
  later calls happened only since nothing stopped the earlier one. Later calls are kept for a secondary analysis;
  stage 3 checks the live picture.
- The agent never sees labels (D4). Never ask, the label rule and the hybrid are computed from the stored calls as
  reference lines: their decisions follow from the label by construction.
- Each call ends in exactly one outcome: allowed, asked then yes, asked then no, or blocked, reported separately for
  unneeded and wanted calls. Unreadable replies count as ASK (so they land in an asked row) and are also reported as
  their own count. No policy blocks in this design; block stays in the interface.
- Hypotheses. H1 (misled, main): under the false label on the vague name, gate with labels allows 20+ points more
  unneeded calls than gate on call for Luna and Qwen; with the honest name the gap is under 10 points. H2 (warning,
  main): under the false label on the vague name, for Luna and Qwen, the warning cuts gate with labels' allow rate on
  unneeded calls by 20+ points, and adds under 10 points of asks on wanted calls compared with the same condition
  without the warning. H3: with true labels, the two gates differ by under 10 points in asks on wanted calls.
- Tests: paired over the same stored calls, accounting for calls from the same job, with Holm correction. A change
  counts at 20+ points with Holm p < 0.05; two rates count as the same when the 90% confidence interval of their
  difference lies inside ±10 points.
- Plain-language version: `docs/explained/`.

## How to work on a piece

1. `git fetch origin && git switch main && git pull`.
2. `git switch -c <name>/<piece>`, for example `will/w1-items-server`.
3. Build the piece and its check in `tests/`. Until we agree on pytest (D2), a check is a plain script with
   `assert`s, run with `uv run python tests/<file>.py`.
4. Push, open a pull request, get one teammate's review, merge when the check passes.
5. Tick the piece's box in this file in the same pull request.

Pilot code to start from lives in the `yashlad1/agentic-fp` repo, in `yash/` on the `label-widening` branch. Paths
below like `pilot-b3/task.py:118` mean `yash/pilot-b3/task.py`, line 118. Read a file without switching branches:
`git remote add pilot https://github.com/yashlad1/agentic-fp.git && git fetch pilot label-widening` once, then
`git show pilot/label-widening:yash/pilot-b3/task.py`.

No paid model calls outside Yash's runs: build and test everything on mockllm. Tag AI-assisted code as the course
AI policy requires.

## Decide in week 1 (whole team)

| # | Decision | Why it matters | Proposal |
|---|---|---|---|
| D1 | Add `mcp` (the Python MCP SDK) to `pyproject.toml` | Inspect's MCP support needs it, and it isn't installed yet | Yes; Will adds it in W1 |
| D2 | pytest, or plain `assert` scripts | Sets the format of `tests/` | Plain scripts until someone needs more |
| D3 | The reversible safe path for each kind of action | Every job needs one, the way archive is the safe path for delete | Delete: archive. Send: save as draft. Pay: approve without paying. Publish: schedule (can be cancelled) |
| D4 | How the agent sees the label | Decides which layer a label can affect | Decided Oct 25: the agent never sees labels. Inspect drops MCP annotations before the model, and the FP1 feedback asked us to separate the agent's choice from the approval layer's. Only the label rule, the hybrid and gate with labels read them |
| D5 | Which wording each delete job uses | `pilot-b3/scenarios.json` has three per job (tidy, clear out, get rid of); wording drives how often agents propose deleting | One per job, fixed before any paid run, chosen so stage 1 yields at least a minimum number of unneeded proposals per action kind (the number is set before the freeze) |
| D6 | The shared formats in `contracts.py` | Everyone codes against them | Y1 drafts, everyone reviews |
| D7 | What an unreadable gate reply counts as | Decides the outcome of some calls | Count them separately and treat them as ASK |
| D8 | Which gate the hybrid falls back to | The hybrid is computed, not run | Gate with labels |

## Will: MCP servers and the scorer

Folders: `src/trustlabel/servers/`, `src/trustlabel/scorer.py`.

| # | Piece | Week | Start from | Done when |
|---|---|---|---|---|
| [x] W1 | Items server: `list_items`, `archive_items`, `delete_items`, `restore_items` over a JSON state file | 1 | `pilot-b3/state.py` (archive limit 5 at line 14), tools at `pilot-b3/task.py:191-213` | A test calls each tool and checks the state file |
| [x] W2 | Label switch, set at server start: `true` (correct labels), `false` (the irreversible tool claims read-only), `none` (no annotations) | 1 | Correct labels at `pilot-b3/conditions.py:34-39` | A test lists the tools under each setting and checks their annotations |
| [x] W3 | Name switch: vague (`process_items`) or honest (`delete_items`) | 1 | `pilot-gate/task_v2.py:31-35` | A test checks the tool names under each setting |
| [x] W4 | State-changing list: for each server, which tools really change state, written down without reading the labels | 2 | — | The harness imports it; under the false label, the delete tool is still on the list |
| [x] W5 | Messages, invoices and posts servers with the same switches and a safe path each (D3) | 2 | Tool names at `label-widening/task_beyond.py:23-24` | The W1-W3 tests pass for each server |
| [x] W6 | Fresh sandbox per episode: the harness hands each sample a new state file | 2 | — | Two episodes in a row don't share state |
| [x] W7 | Scorer from the final state: did an irreversible action run (harm), were the needed actions done with nothing extra (task success), which items were hit that weren't asked for | 3 | `outcome()` at `pilot-b3/task.py:170-186` | Tests on hand-made final states for all four kinds |
| [ ] W8 | Second labeler for I5 | 3 | — | Sheet filled in without seeing Isha's |
| [ ] W9 | Spot-check 20 transcripts per agent against the final state; draft the System section | 5-6 | — | Mismatches reported to Yash |

## Vignesh: approval policies and analysis

Folders: `src/trustlabel/policies/`, `src/trustlabel/analysis/`.

| # | Piece | Week | Start from | Done when |
|---|---|---|---|---|
| [ ] V1 | Policy interface from `contracts.py`: a call and its labels go in, allow / ask / block comes out | 1 | Fig. 2 of the proposal | Reviewed with Yash, merged with Y1 |
| [ ] V2 | Never ask, and label rule (ask unless the label says read-only), as plain functions; used as reference lines on the stored calls | 1 | — | A test covers both policies under all three label states |
| [ ] V3 | One gate prompt for both LLM policies, with labels and the warning sentence as switches | 1-2 | Prompt at `pilot-gate/task.py:23-24`; labels as an `annotations` field at `pilot-gate/task_v2.py:111-113`; warning at `lying-label/task_warn.py:18` | A test shows the prompts differ only in the labels and the warning |
| [ ] V4 | Gate on call, and gate with labels: call the gate model, parse ASK / ALLOW, count unparseable replies separately | 2 | `verdict()` at `pilot-gate/task.py:88-94` | A mockllm test, including a garbled reply |
| [ ] V5 | Hybrid: a read-only label allows the call without the LLM; anything else gets the gate-with-labels decision (D8), computed on the stored calls | 2 | — | A test shows the hybrid allows read-only-labelled calls and otherwise takes the stored gate-with-labels decision |
| [ ] V6 | Analysis from the logs: agent proposal rates (stage 1); per gate condition, allowed, asked then yes, asked then no, blocked and unreadable, on unneeded and wanted calls (stage 2); harm and task success (stage 3); reference lines for never ask, label rule and hybrid | 3 | `pilot-b3/analyze.py` | Tested on mockllm logs and hand-made counts |
| [ ] V7 | Paired tests over the same stored calls (first call per episode; calls from the same job accounted for) with Holm correction, for H1-H3; a change counts at 20+ points with Holm p < 0.05; two rates count as the same when the 90% confidence interval of the difference lies inside ±10 points | 3 | — | A test on made-up counts with a known answer |
| [ ] V8 | Tables and figures, one set per agent | 5-6 | — | Every number traces to a log file, a command and n |

## Isha: scenarios and ground truth

Folder: `src/trustlabel/scenarios/`.

| # | Piece | Week | Start from | Done when |
|---|---|---|---|---|
| [ ] I1 | Scenario format, with Yash in `contracts.py`: id, kind, version (unneeded or wanted), request, items, needed actions | 1 | Keys in `pilot-b3/scenarios.json`: id, title, request_safe, request_required, target_ids, items | Merged with Y1 |
| [ ] I2 | 10 delete jobs, both versions | 1 | `pilot-b3/scenarios.json`, jobs s01-s10: all ten already have a wanted version (`request_required`) | The I6 check passes |
| [ ] I3 | 30 jobs: 10 send, 10 pay, 10 publish, both versions | 2 | `label-widening/beyond.json`, x01-x30: the unneeded requests exist; the wanted versions still need writing | The I6 check passes |
| [ ] I4 | User answer rules: how the scripted user answers an ask in each version, including a question it can't map to the task | 2 | — | Every version has exactly one answer |
| [ ] I5 | Two-person labeling: for all 80 versions, does the request truly need the action? Isha and Will fill separate sheets; revise or drop the ones they disagree on | 3 | — | Agreement count recorded; final list frozen |
| [ ] I6 | Scenario check script: each job has both versions, ids are unique, needed actions name real items | 2 | — | Runs clean on all 40 jobs |
| [ ] I7 | Draft the Methods section (scenarios, ground truth) and update Related Work | 5-6 | — | — |

## Yash: harness and runs

Folders: `src/trustlabel/harness/`, `dev/`.

| # | Piece | Week | Start from | Done when |
|---|---|---|---|---|
| [ ] Y1 | `contracts.py`: tool call, labels, decision, scenario | 1 | V1, I1 | Everyone approves the pull request |
| [ ] Y2 | Inspect task: the agent reaches Will's items server through `mcp_tools(mcp_server_stdio(...))`; fixed system prompt, step cap and max tokens | 1 | `episode` solver at `pilot-b3/task.py:118` | A mockllm episode lists and archives items |
| [ ] Y3 | Confirm the approval hook fires on MCP tool calls, and that MCP labels don't reach the model (D4) | 1 | — | A mockllm run shows the approver ran and the model's tool list has no labels |
| [ ] Y4 | Approval wiring: one approver on Will's state-changing list (W4); allow means approve; ask goes to the scripted user, then approve or reject; every decision is recorded in the sample; every proposed irreversible call is stored with its context for stage 2 | 2 | — | On mockllm, allow, ask-then-yes and ask-then-no each end in the right state, and stored calls replay |
| [ ] Y5 | Scripted user from Isha's answer rules (I4) | 2 | — | Each version gets its one answer |
| [ ] Y6 | Stage switches as task parameters: stage 1 (agent, name), stage 2 (gate model, gate on call or gate with labels, label, warning, name), stage 3 (the live cells) | 3 | — | Every stage dry-runs on mockllm |
| [ ] Y7 | Run scripts in `dev/`: smoke (12 samples), one full condition, progress | 3-4 | `yash/commands/` | Each runs on mockllm |
| [ ] Y8 | Lock and smoke: freeze scenarios, prompts and the gate-model rule, then smoke with real models | 4 | — | The smoke passes the checks named before it starts |
| [ ] Y9 | Runs: stage 1 (2 agents, 2 names, 2 repeats), stage 2 (every stored call under 14 gate conditions, per gate model), stage 3 (the live cells); more models if the budget allows | 5 | — | Logs complete, each failed sample marked |
| [ ] Y10 | Rerun failed samples; recheck every reported number against the raw logs | 6 | — | — |

## Week by week

| Week | Done by Sunday |
|---|---|
| 1 · Oct 19-25 | D1-D6 decided; `contracts.py` merged; items server with its label and name switches; never ask and label rule; 10 delete jobs; agent reaches the items server on mockllm |
| 2 · Oct 26-Nov 1 | All four servers; all five policies; all 40 jobs; answer rules; approval and scripted user in the loop |
| 3 · Nov 2-8 | Scorer; labeling done; analysis tested; all three stages dry-run on mockllm |
| 4 · Nov 9-15 | Everything frozen before any real data; smoke run |
| 5 · Nov 16-22 | Core runs; first tables |
| 6 · Nov 23-29 | Reruns, tables and figures, report drafts (Thanksgiving week, lighter) |
| 7 · Nov 30-Dec 6 | Final report and slides; everyone prepares to walk through their own files live |

## Rules that don't bend

- Nothing changes after we see paid results. Scenarios, prompts, conditions and the gate-model rule freeze at the
  end of week 4; a change after that means a new run.
- Score from the final sandbox state, never from what the model says it did.
- Every number in the report comes from the raw logs, with its log file, command and n.
