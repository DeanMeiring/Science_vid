"""Birthday cows, for Experiment 12 (the birthday paradox).

Model: each cow's birthday is independent and equally likely to be any of 365 days (no leap day).
Real cow births cluster in calving season, so this is the ideal model, not real herds.

- exact(n): chance that ANY two of n cows share a birthday, 1 - prod(1 - k/365), k = 0..n-1.
- exact_particular(m): chance that at least one of m OTHER cows shares ONE particular cow's birthday,
  1 - (364/365)^m. A different question.
- simulate(n, trials): seeded herds; the herds the video shows are the first herds of this same run,
  in order, never picked.

SEED is fixed here before any result was looked at (Experiment 12 -> 12). Don't change it to get a
nicer-looking run.
"""
import numpy as np

DAYS = 365
SEED = 12
TRIALS = 100_000
SIZES = (10, 20, 22, 23)        # herd sizes the video shows

def exact(n):
    k = np.arange(n)
    return 1.0 - float(np.prod(1.0 - k / DAYS))

def exact_particular(m):
    return 1.0 - (1.0 - 1.0 / DAYS) ** m

def smallest(p, target=0.5):
    n = 1
    while p(n) <= target: n += 1
    return n

def herds(n, trials=TRIALS, seed=SEED):
    """(trials, n) birthdays, 0 = 1 Jan. Each herd size gets its own stream from the one seed."""
    rng = np.random.default_rng([seed, n])
    return rng.integers(0, DAYS, (trials, n), dtype=np.int16)

def has_match(b):
    s = np.sort(b, axis=1)
    return (np.diff(s, axis=1) == 0).any(axis=1)

def matches(row):
    """Pairs (i, j) of cows in one herd with the same birthday."""
    return [(i, j) for i in range(len(row)) for j in range(i + 1, len(row)) if row[i] == row[j]]

def date(d):
    return (np.datetime64("2025-01-01") + np.timedelta64(int(d), "D")).astype(object).strftime("%d %b")   # 2025: no leap day

def simulate(n, trials=TRIALS, seed=SEED):
    """Observed rate, its standard error, the 95% interval (normal approx.), and the running tally."""
    m = has_match(herds(n, trials, seed))
    p = m.mean(); se = np.sqrt(p * (1 - p) / trials)
    return dict(n=n, trials=trials, hits=int(m.sum()), rate=float(p), se=float(se),
                ci95=(float(p - 1.96 * se), float(p + 1.96 * se)), running=np.cumsum(m))

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from common import gentle
    gentle()
    print(f"seed {SEED}, {TRIALS:,} herds per size, {DAYS} equally likely days, no leap day\n")
    print("exact, any two match:")
    for n in (10, 20, 22, 23, 30, 50):
        print(f"  {n:2d} cows: {exact(n):.4%}")
    print(f"  smallest herd above 50%: {smallest(exact)} cows; pairs among 23: {23 * 22 // 2}\n")
    print(f"simulated (95% interval = rate +/- 1.96 x standard error):")
    for n in SIZES:
        r = simulate(n)
        print(f"  {n:2d} cows: {r['hits']:,} of {r['trials']:,} = {r['rate']:.2%}  (SE {r['se']:.2%}, "
              f"95% {r['ci95'][0]:.2%} to {r['ci95'][1]:.2%}; exact {exact(n):.2%})")
        run = r["running"]
        print(f"           tally after 10, 100, 1,000, 10,000 herds: "
              + ", ".join(f"{run[k - 1]:,}/{k:,}" for k in (10, 100, 1000, 10_000)))
    print("\nfirst herds of 23 (as the video shows them, in order):")
    b = herds(23)
    for h in range(5):
        pr = matches(b[h])
        print(f"  herd {h + 1}: " + ("no match" if not pr else
              "; ".join(f"cows {i + 1} & {j + 1} on {date(b[h][i])}" for i, j in pr)))
    print(f"\none particular cow (a different question): another cow shares ITS birthday")
    for m in (22, 252, 253):
        print(f"  with {m} other cows: {exact_particular(m):.2%}")
    print(f"  first above 50%: {smallest(exact_particular)} other cows ({smallest(exact_particular) + 1} in all)")
