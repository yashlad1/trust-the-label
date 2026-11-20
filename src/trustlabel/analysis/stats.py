# V7a · Paired tests with Holm correction (H1-H3): https://github.com/yashlad1/trust-the-label/issues/21
# V7b · Equivalence check (90% CI within ±10 points): https://github.com/yashlad1/trust-the-label/issues/22

"""The statistics behind every reported difference.

Paired tests over the same stored calls, Holm correction across a report's hypotheses, and intervals from a
bootstrap that resamples jobs, because calls from one job are not independent (a job contributes many calls).

Tested on constructed counts in tests/analysis/test_stats.py, never on a partial real log.
"""

import random
from math import comb


def mcnemar_p(b, c):
    if b + c == 0:
        return 1.0
    return min(1, 2 * sum(comb(b + c, k) for k in range(min(b, c) + 1)) / 2 ** (b + c))


def holm(ps):
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, top = [0.0] * len(ps), 0.0
    for rank, i in enumerate(order):
        top = max(top, min(1, (len(ps) - rank) * ps[i]))
        adj[i] = top
    return adj


def job_bootstrap_ci(per_call: list[tuple[str, float]], level: float = 0.90, draws: int = 2000,
                     seed: int = 0) -> tuple[float, float]:
    """Confidence interval for the mean of per-call values, resampling jobs (calls from one job are not independent).
    per_call: (job id, value) per call, e.g. ask under condition a minus ask under condition b (-1, 0 or 1).
    Returns (low, high) in the values' own units."""
    if not per_call:
        return 0.0, 0.0
    rng = random.Random(seed)
    by_job: dict[str, list[float]] = {}
    for job, value in per_call:
        by_job.setdefault(job, []).append(value)
    jobs = list(by_job)
    means = []
    for _ in range(draws):
        values = [v for job in rng.choices(jobs, k=len(jobs)) for v in by_job[job]]
        means.append(sum(values) / len(values))  # pooled mean, like the point estimate (b - c) / n
    means.sort()
    return means[int((1 - level) / 2 * draws)], means[min(draws - 1, int((1 + level) / 2 * draws))]
