# Front-end comparison scatter plots: methodology (for paper)

## Purpose

We plot pairwise comparisons between SMTParser and each of the six other front-ends (Z3, cvc5, smt-switch, pysmt, ANT4, jSMT) for three metrics: **parsing time (ms)**, **peak RSS (MB)**, and **structural size (nodes)**. Each figure shows one metric and one competitor; there are 18 figures in total (3 metrics × 6 competitors).

## Data source

- **Input**: the benchmark result table with one row per (benchmark instance, parser). Each row includes: benchmark file path, parser name, status (`ok`, `timeout`, or `fail`), and the metric values (e.g. `time_ms`, `memory_kb`, `ast_nodes`).
- **Instance-level**: Every point in the plot corresponds to one benchmark instance. We do not aggregate over instances (e.g. no per-theory or global medians in the plot).

## Axes and reference line

- **Horizontal axis (x)**: value of the metric for **SMTParser** on that instance.
- **Vertical axis (y)**: value of the same metric for the **other parser** (e.g. Z3, cvc5) on the same instance.
- **Diagonal**: the dashed line **y = x**. Points above the line indicate that the other parser has a larger value than SMTParser on that instance; points below indicate SMTParser has a larger value. For time and RSS, “below the line” means SMTParser is slower or uses more memory; for node count, “below” means SMTParser produces a larger IR.

## Point types

1. **Successful runs (both parsers ok)**  
   For each benchmark instance where **both** SMTParser and the other parser finished successfully (`status = ok`), we plot one point at **(SMTParser value, other parser value)**. These are drawn as solid circles (blue in the script).

2. **Timeout runs**  
   If exactly one parser timed out on an instance, we still represent that instance, but the timed-out side is placed at the **upper end of the axis** so that:
   - If **SMTParser** timed out and the other parser succeeded: we plot a point at **(boundary, other parser value)**, i.e. the x-coordinate is set to a value near the right edge of the plot (slightly inward so the marker is not clipped).
   - If the **other parser** timed out and SMTParser succeeded: we plot **(SMTParser value, boundary)**, i.e. the y-coordinate is set near the top edge.
   - If **both** timed out: we plot **(boundary, boundary)** (upper-right region).  
   These timeout cases are drawn as **cross markers (×)** in black, to distinguish them from successful-run points. The “boundary” is chosen as a fraction of the axis maximum (slightly below the maximum) so that markers remain fully visible.

   Instances where either parser had status `fail` (non-timeout failure) are not included in the plot.

## Scale and axis range

- **Log scale**: Both axes use a **logarithmic scale** (base 10) so that the wide range of values (e.g. milliseconds to seconds, or small to large node counts) is readable.
- **Axis limits**: The minimum and maximum of each axis are determined from the data:
  - From all “ok vs ok” points we take the minimum and maximum over both coordinates, add a small margin (2% of range), and use that to set the initial axis range.
  - If the computed minimum would be ≤ 0 (invalid for log scale), the lower limit is set to the larger of a tiny positive constant and 1% of the axis maximum, so that empty decades (e.g. 10^0–10^1) are not shown when the data do not extend that low (e.g. for time and RSS).
  - The upper limit is extended if necessary so that any “timeout at boundary” points (and the non-boundary coordinate of partial timeouts) lie within the plot.

## Metrics

- **Time**: parsing time in milliseconds (ms), as reported in the benchmark table.
- **RSS**: peak resident set size. The table stores memory in KiB; we convert to MB (divide by 1024) for the plot.
- **Nodes**: structural size as the number of nodes in the IR (integer), as reported in the benchmark table.

## Summary

Each scatter plot compares SMTParser (x-axis) with one other front-end (y-axis) on a single metric, at the level of individual benchmark instances. Successful runs are shown as dots on the (x, y) pair; timeouts are shown as crosses, with the timed-out parser’s coordinate placed near the corresponding axis maximum. The diagonal y = x and the log scale make it easy to see whether SMTParser is better (e.g. faster or smaller) or worse on each instance, and how many instances fall on each side of the line.
