# FP3 report: where it is and what's left

## Where the report is
- The report is a Word file on Yash's OneDrive, shared with the four of us by name.
- Open it from the invite email Yash sent.

## How to edit
- Edit directly in the shared Word file, with Track Changes off.
- Claude sessions never edit it. They work on a separate copy.
- Yash merges their changes in with Word's Review > Compare > Combine.

## What fills each section
- Figure 1: in the shared report (redrawn Nov 22); source docs/figures/fp3-figure1.tex, built with pdflatex.
- Figure 2, the example call: in the shared report (added Nov 22); source docs/figures/fp3-figure2-example.tex, built with pdflatex.

Pilot Study:
- Setup paragraph: #127 (Isha).
- Table 5: merged, #130 (Yash).
- Table 6 and the stage-1 rates: #113 and #114 (Vignesh).
- Figure 3: merged, #131 (Yash).
- Stage-3 table: merged, #123 (Will).
- Swap paragraph: merged, #126 (Will).

Readiness assessment:
- Parser check: merged, #128 (Isha).
- The rest: merged, #134 (Yash).

Plan for FP4:
- Table 7, and time and tokens: merged, #133 (Yash).

Appendix:
- Table A1, the condition settings: in the shared report (added Nov 21).

Table style for every table:
- docs/table-style.md (merged, #129).

## What still needs doing

### Still from the Nov 15 pilot, to be replaced when its piece lands
- **Pilot Study, opening paragraph (#127, Isha):** "The pilot ran all three stages once, end to end, on November 15, 2026..."
- **Pilot Study, Primary measures, the stage-1 sentence (#114, Vignesh):** "In stage 1, gpt-oss-120b proposed an irreversible call in 83% (10/12) of unneeded..."
- **Pilot Study, Table 6 (#113, Vignesh):** the table and its caption "Table 6. Pilot stage 2, vague tool name, the call's own request..."
- **Pilot Study, the paragraph on Table 6's first two rows (#113, Vignesh):** "The first two rows of Table 6 use exactly the same prompt text..."
- **Pilot Study, the sentence after the stage-3 table (#113, Vignesh):** "These are pilot rates on 15 to 20 calls per stage-2 cell and 12 episodes per stage-3 cell."

### To confirm
- **Final report and talk date, Plan for FP4, Order:** "The final report and talk follow in the first week of December." The date comes from TASKS.md's assumption, not from Canvas; confirm it against Canvas.
- **Table number, Pilot Study, the stage-3 table:** "Table 6b. Harm, task success and extra changes in the pilot's live runs..." Renumber once all tables are in.
- **Caption style, every table:** the newer tables (5, 6b, 7, 8) have a bold title above; the older ones (1 to 4, 6) have an italic caption below. Pick one style.
- **Transcript check (#8), Evaluation checks:** "The check of live-loop transcripts against the scorer (#8) is still open."
- **AlignmentCheck code:** the AlignmentCheck gate's code is not on main (records/README.md), so the README and Table A1 can't give its command and "the repository's README gives the command for every condition" isn't true for those rows. Yash decides.
- **Plan for FP4, "Full experiment.":** the paragraph says the stages "run", while Table 7 says the run happened on Nov 15. Pick the tense.
- **Run counts in titles:** Table 5 says "9 runs" and Tables 7 and 8 say "11 logs" for the same kind of unit. Pick one word.
- **Table 2 note, Llama 4 Maverick:** the note says the provider pin is the host in the model's file under dev/models/, but main has no dev/models/ file for Llama 4 Maverick; its pin (Parasail, fp8, fallbacks off) is in the full run's log headers. Reword the note or add the file.

## When a piece's pull request merges
- Its "For the report" part goes into the shared Word file.
- Its line here is updated.
