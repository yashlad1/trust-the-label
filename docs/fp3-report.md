# FP3 report: where it is and what's left

## Where the report is
- The report is a Word file on Yash's OneDrive, shared with the four of us by name.
- Open it from the invite email Yash sent.

## How to edit
- Edit directly in the shared Word file, with Track Changes off.
- Claude sessions never edit it. They work on a separate copy.
- Yash merges their changes in with Word's Review > Compare > Combine.

## What fills each section
Pilot Study:
- Setup paragraph: #127 (Isha).
- Table 5: #130 (Yash).
- Table 6 and the stage-1 rates: #113 and #114 (Vignesh).
- Figure 2: #131 (Yash).
- Stage-3 table: merged, #123 (Will).
- Swap paragraph: merged, #126 (Will).

Readiness assessment:
- Parser check: merged, #128 (Isha).
- The rest: #120 (Yash).

Plan for FP4:
- Table 7, and time and tokens: #119 (Yash).

Appendix:
- Table A1, the condition settings: in the shared report (added Nov 21).

Table style for every table:
- docs/table-style.md (#129).

## What still needs doing

### Still from the Nov 15 pilot, to be replaced when its piece lands
- **Pilot Study, opening paragraph (#127, Isha):** "The pilot ran all three stages once, end to end, on November 15, 2026..."
- **Pilot Study, Primary measures, the stage-1 sentence (#114, Vignesh):** "In stage 1, gpt-oss-120b proposed an irreversible call in 83% (10/12) of unneeded..."
- **Pilot Study, Table 6 (#113, Vignesh):** the table and its caption "Table 6. Pilot stage 2, vague tool name, the call's own request..."
- **Pilot Study, the paragraph on Table 6's first two rows (#113, Vignesh):** "The first two rows of Table 6 use exactly the same prompt text..."
- **Pilot Study, the sentence after the stage-3 table (#113, Vignesh):** "These are pilot rates on 15 to 20 calls per stage-2 cell and 12 episodes per stage-3 cell."

### Still to write
- **Readiness assessment, beyond the parser bullet (#120):** the section now holds only "A person read 24 of the gate's replies blind: the reader and the parser agree on 16 of 24..."; the rest (every condition ran correctly, unreliable jobs, floor and ceiling effects, fixes before the full run) is not written.
- **Plan for FP4, Table 7 as the full run ran it (#119):** "Table 7. The full experiment."
- **Plan for FP4, the Time and cost paragraph (#119):** the paragraph "Time and cost." is empty; it needs time and tokens per sample from the full run.

### To confirm
- **Final report and talk date, Plan for FP4, Order:** "The final report and talk follow in the first week of December." The date comes from TASKS.md's assumption, not from Canvas; confirm it against Canvas.
- **Table number, Pilot Study, the stage-3 table:** "Table 6b. Harm, task success and extra changes in the pilot's live runs..." Renumber once all tables are in.
- **Caption style, every table:** the new Tables 5 and 6b have a bold title above; the older tables (1 to 4, 6, 7) have an italic caption below. Pick one style.
- **Transcript check (#8), Evaluation checks:** "The check of live-loop transcripts against the scorer (#8) is still open."
- **README ask-first row:** the README row for the stage-2 ask-first rows is in #135; merge it before submitting, so the report's line "the repository's README gives the command for every condition" is true.

## When a piece's pull request merges
- Its "For the report" part goes into the shared Word file.
- Its line here is updated.
