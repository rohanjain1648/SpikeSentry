"""Validation on labeled synthetic series.

Generates Poisson-like request counts per window, injects spikes of known size at
known windows, then measures precision/recall of:
  * robust  - median/MAD z-score (what traffic_watch uses)
  * meanstd - classic mean/stddev z-score (baseline for comparison)
Deterministic (fixed seed). Run: python evaluate.py
"""
import math
import random
import statistics
import sys

from traffic_watch import flag_counts


def poisson(lam, rng):
    if lam < 30:
        limit, k, p = math.exp(-lam), 0, 1.0
        while True:
            p *= rng.random()
            if p <= limit:
                return k
            k += 1
    return max(0, round(rng.gauss(lam, math.sqrt(lam))))


def meanstd_flags(counts, threshold=3.0, min_count=10):
    m = statistics.mean(counts)
    sd = statistics.pstdev(counts) or 1.0
    return [c >= min_count and (c - m) / sd >= threshold for c in counts]


def run(n_series=500, n_windows=30, seed=42):
    rng = random.Random(seed)
    conf = {"robust": [0, 0, 0], "meanstd": [0, 0, 0]}          # tp, fp, fn
    by_mag = {}                                                  # mag -> [robust hits, meanstd hits, total]
    normal_windows = 0
    for _ in range(n_series):
        lam = rng.uniform(10, 60)
        counts = [poisson(lam, rng) for _ in range(n_windows)]
        labels, mags = [False] * n_windows, {}
        for i in rng.sample(range(n_windows), rng.choice([0, 1, 2, 3])):
            mag = rng.choice([2, 3, 4, 6])
            counts[i] = poisson(lam * mag, rng)
            labels[i], mags[i] = True, mag
        normal_windows += labels.count(False)
        preds = {"robust": flag_counts(counts)[0], "meanstd": meanstd_flags(counts)}
        for name, fl in preds.items():
            for p, l in zip(fl, labels):
                conf[name][0] += p and l
                conf[name][1] += p and not l
                conf[name][2] += l and not p
        for i, mag in mags.items():
            b = by_mag.setdefault(mag, [0, 0, 0])
            b[0] += preds["robust"][i]
            b[1] += preds["meanstd"][i]
            b[2] += 1
    return conf, by_mag, normal_windows, n_series, n_windows


def report(conf, by_mag, normal_windows, n_series, n_windows):
    out = [f"Synthetic validation: {n_series} series x {n_windows} windows, seed 42",
           f"{'method':<9}{'TP':>6}{'FP':>6}{'FN':>6}{'precision':>11}{'recall':>8}{'F1':>7}{'FP/1k normal':>14}"]
    for name, (tp, fp, fn) in conf.items():
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        out.append(f"{name:<9}{tp:>6}{fp:>6}{fn:>6}{p:>11.3f}{r:>8.3f}{f1:>7.3f}{1000 * fp / normal_windows:>14.2f}")
    out += ["", "Recall by injected spike size (x normal rate):",
            f"{'size':<6}{'n':>5}{'robust':>9}{'meanstd':>9}"]
    for mag in sorted(by_mag):
        rh, mh, n = by_mag[mag]
        out.append(f"{str(mag) + 'x':<6}{n:>5}{rh / n:>9.2f}{mh / n:>9.2f}")
    return "\n".join(out)


if __name__ == "__main__":
    print(report(*run()))
    sys.exit(0)
