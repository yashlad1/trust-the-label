# V7a · Paired tests with Holm correction (H1-H3): https://github.com/yashlad1/trust-the-label/issues/21
# V7b · Equivalence check (90% CI within ±10 points): https://github.com/yashlad1/trust-the-label/issues/22

from math import comb

from trustlabel.analysis.stats import holm, job_bootstrap_ci, mcnemar_p


def close(a, b):
    return abs(a - b) < 1e-12


def binom_cdf(n, k):
    return sum(comb(n, i) for i in range(k + 1)) / 2**n


# mcnemar_p: exact two-sided, worked out by hand
assert mcnemar_p(0, 0) == 1.0
assert close(mcnemar_p(5, 0), 2 / 32)
assert close(mcnemar_p(0, 5), 2 / 32)
assert mcnemar_p(3, 3) == 1.0  # 2 * 42/64 > 1, capped
assert close(mcnemar_p(1, 9), 22 / 1024)  # 2 * (1 + 10) / 1024
assert close(mcnemar_p(2, 7), 2 * binom_cdf(9, 2))
assert close(mcnemar_p(2, 7), mcnemar_p(7, 2))

# holm: sorted, times (m - rank), running max, cap at 1, input order kept
out = holm([0.01, 0.04, 0.03])  # sorted .01 .03 .04 -> .03 .06 .04 -> max .03 .06 .06
assert all(close(x, y) for x, y in zip(out, [0.03, 0.06, 0.06])), out
out = holm([0.5, 0.4, 0.01])  # sorted .01 .4 .5 -> .03 .8 .5 -> max .03 .8 .8
assert all(close(x, y) for x, y in zip(out, [0.8, 0.8, 0.03])), out
out = holm([0.6, 0.01, 0.7])  # sorted .01 .6 .7 -> .03 1.2 .7 -> cap
assert all(close(x, y) for x, y in zip(out, [1.0, 0.03, 1.0])), out

# job_bootstrap_ci: properties
assert job_bootstrap_ci([]) == (0.0, 0.0)
data = [("a", 1.0), ("a", 0.0), ("b", 1.0), ("c", 0.0), ("c", 0.0), ("d", 1.0)]
r1 = job_bootstrap_ci(data, seed=3)
assert r1 == job_bootstrap_ci(data, seed=3)
lo, hi = r1
assert lo <= hi
assert 0.0 <= lo and hi <= 1.0
lo, hi = job_bootstrap_ci([("a", 0.7), ("b", 0.7), ("b", 0.7)])
assert close(lo, 0.7) and close(hi, 0.7), (lo, hi)
lo, hi = job_bootstrap_ci([("a", 0.2), ("a", 0.9), ("b", 0.5)])
assert 0.2 <= lo <= hi <= 0.9

# one job all 1s, another all 0s: resamples range from all-0 to all-1, so wide
lo, hi = job_bootstrap_ci([("x", 1.0)] * 5 + [("y", 0.0)] * 5)
assert lo <= 0.1 and hi >= 0.9, (lo, hi)

print("ok")
