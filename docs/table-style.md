# How the report's tables should look

Tables in our FP3 and final reports should be simple, clear and direct, because a table is the fastest way to get
numbers across. This page sums up how research papers and style guides lay out tables, turns that into rules for our
reports, and says how a `docs/fp3-tables/` page is laid out from now on.

## What papers and style guides do

- **One table answers one question.** Keep the main table to the comparisons that matter, and move the rest to an
  appendix. A table taking more than about a third of a page overwhelms readers. (Emory AI research practicum guide.)
- **The table stands on its own.** It has a short, specific title, plus notes that define any abbreviation or symbol,
  so a reader understands it without the text. Notes are for definitions and conventions, not for discussion. (APA 7th
  edition; Cornell results-tables tutorial.)
- **The meaning goes in the text, not under the table.** The paragraph that cites the table says what it shows. APA's
  notes hold only definitions, specific footnotes and significance markers.
- **Few lines.** There are no vertical lines and no double lines: only a line above the headers, one below them, and
  one at the bottom. White space, not lines, separates groups of rows. (booktabs, the standard LaTeX package for
  publication tables.)
- **Units go in the column header once,** like "Wall time (min)", not repeated in every cell. (booktabs; Schwabish.)
- **Numbers line up.** Numbers are right-aligned and text is left-aligned. A column keeps the same number of decimals,
  and no more than one or two. (Schwabish, "Ten Guidelines for Better Tables", 2020.)
- **Highlighting is rare,** and the note says what it means (for example, bold for the best value). (Schwabish; common
  practice in ML papers.)
- **Uncertainty sits next to the number,** as an interval or a plus-minus, and the note names the method once. (Common
  practice in ML papers; bootstrap intervals are recommended.)
- **Big tables become charts.** If a table has to be large to make its point, a figure works better. (Schwabish.)

## Our rules for the report

1. **Title:** what is measured, on what, with n, in one line. For example: "Table 6. How often each gate let an
   unneeded action through, by label (pilot, 12 unneeded actions per cell)."
2. **Columns:** only as many as the question needs. A column whose values are all the same is dropped and said once in
   the note instead (for example, "No sample failed.").
3. **Cells:** a percent with its count when n is small, like 83% (10/12), and intervals as [low, high]. Units appear
   only in the header. Use one decimal at most.
4. **Note under the table:** definitions only, in one or two short lines: what each term means, what bold means, how
   the interval was computed. There is no "how to read" line, no takeaway and no command.
5. **Meaning:** one to three short sentences in the paragraph that cites the table.
6. **Source:** the records folder and the command go in the matching `docs/fp3-tables/` page and in the appendix, not
   in the table.
7. **Layout:** three horizontal lines, no vertical lines, and right-aligned numbers. In a markdown page, right-align a
   number column with `--:`; the three-line layout is applied in the Word report.

## How a docs/fp3-tables/ page is laid out

From now on, every page in `docs/fp3-tables/` has two parts.

- **For the report.** The table in the style above, its note, and the one to three short sentences for the text that cites it.
  This is the only part that goes into the Word report.
- **Record.** Everything someone needs to check or repeat the numbers: the source folder under `records/`, the
  command, n, and the checks behind the numbers (for example, a second count that agrees). Supporting tables, such as
  averages or per-run checks, go here too.

The pages merged before this guide (`stage3.md`, `swap-limit.md` and `parser-check.md`) stay as they are. Their tables
are put into this style when the pieces go into the Word report.

## Example: Table 5, before and after

Before: a nine-row table with a column of zeros, a second table of averages, a four-line "how to read" block, a
takeaway, a source line, and a long paragraph under it.

After, in the report:

**Table 5.** The pilot's full runs at the final code (Nov 20, 2026; 9 runs, 3,384 samples).

| Stage | Model | Samples | Wall time (min) | Tokens per sample |
|---|---|--:|--:|--:|
| 1 | gpt-oss-120b (agent) | 24 | 6.4 | 5,424 |
| 1 | GLM 5.3 Flash (agent) | 24 | 2.2 | 4,154 |
| 2 | GPT-6 Luna, on gpt-oss-120b's calls | 960 | 13.8 | 1,047 |
| 2 | GPT-6 Luna, on GLM 5.3 Flash's calls | 672 | 8.8 | 1,147 |
| 2 | Nemotron 3.5 Super VL, on gpt-oss-120b's calls | 960 | 14.6 | 1,564 |
| 2 | Nemotron 3.5 Super VL, on GLM 5.3 Flash's calls | 672 | 9.4 | 1,639 |
| 3 | gpt-oss-120b with GPT-6 Luna, gate on call | 24 | 7.7 | 10,467 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, no warning | 24 | 7.8 | 10,405 |
| 3 | gpt-oss-120b with GPT-6 Luna, labels, warning | 24 | 5.0 | 9,974 |

*Note.* Smoke runs are not shown. No sample failed. Wall time runs from a run's start to its end. Tokens per sample
counts every model in the run.

And in the text that cites it:

> Every run finished, with no failed sample in the 9 full runs (3,384 samples) or the 7 smoke runs (84), and every
> answered call came from its pinned provider (Table 5). A stage-2 decision took about 5 seconds and 1,300 tokens; a
> live stage-3 episode took about 33 seconds of work and 10,300 tokens. Eight stage-2 replies (0.2%), all from
> Nemotron 3.5 Super VL, could not be read and were counted as asks.

## Sources

- [APA Style: Tables](https://apastyle.apa.org/style-grammar-guidelines/tables-figures/tables)
- [booktabs: Publication quality tables in LaTeX (CTAN)](https://ctan.org/pkg/booktabs)
- [Schwabish, Ten Guidelines for Better Tables, Journal of Benefit-Cost Analysis 11(2), 2020](https://www.cambridge.org/core/journals/journal-of-benefit-cost-analysis/article/abs/ten-guidelines-for-better-tables/74C6FD9FEB12038A52A95B9FBCA05A12), summarised at [R-bloggers](https://www.r-bloggers.com/2020/09/10-guidelines-to-better-table-design/amp)
- [Emory AI research practicum: results](https://emory.gitbook.io/ai-research-practicum/experiments/results)
- [Cornell INFO 5001: formatting results tables](https://info5001.infosci.cornell.edu/tutorials/results-tables.html)
