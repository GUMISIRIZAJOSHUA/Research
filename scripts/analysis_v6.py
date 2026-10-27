from pathlib import Path
import json
import csv
import numpy as np
from scipy.stats import wilcoxon
from collections import defaultdict

RECORDS = Path("evaluation_records_v6.jsonl")
PLAN = Path("ANALYSIS_PLAN_v6.md")
METHODS = ["distance", "energy", "soil", "distance_clearance"]
REF = "full"
OUTCOMES = [
    ("scalarized_cost", "Scalarized cost"),
    ("distance_m", "Distance (m)"),
    ("energy_Wh", "Energy (Wh)"),
    ("mission_time_s", "Mission time (s)"),
    ("mean_row_error_m", "Mean row error (m)"),
    ("minimum_swept_body_clearance_m", "Minimum swept-body clearance (m)"),
]
CLEARANCE = "minimum_swept_body_clearance_m"
B = 10000
SEED = 20261026


def holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adjusted = [0.0] * m
    running = 0.0

    for rank, i in enumerate(order):
        running = max(running, (m - rank) * pvals[i])
        adjusted[i] = min(1.0, running)

    return adjusted


def bootstrap_median_ci(diffs, rng, n=B):
    if len(diffs) == 0:
        return None, None, None
    d = np.asarray(diffs, dtype=float)
    stats = np.empty(n)
    for i in range(n):
        sample = d[rng.integers(0, len(d), size=len(d))]
        stats[i] = np.median(sample)
    return float(np.median(d)), float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))


def paired_test(diffs):
    if len(diffs) == 0:
        return None, None, None, 0
    d = np.asarray(diffs, dtype=float)
    if np.all(d == 0):
        p = 1.0
    else:
        p = float(wilcoxon(d, alternative="two-sided", zero_method="wilcox").pvalue)
    mean = float(np.mean(d))
    sd = float(np.std(d, ddof=1)) if len(d) > 1 else 0.0
    return mean, sd, p, len(d)


def value(record, key):
    v = record.get(key)
    return float(v) if v is not None else np.nan


def paired_records(records, method):
    by_case = defaultdict(dict)
    for r in records:
        if r.get("method") in (method, REF) and r.get("success") and r.get("verification_error") is None:
            by_case[(r["family"], r["case"])][r["method"]] = r
    pairs = []
    for pair in by_case.values():
        if method in pair and REF in pair:
            pairs.append((pair[method], pair[REF]))
    return pairs


def analyze(records, method, split_label, rng):
    pairs = paired_records(records, method)
    rows = []
    for key, label in OUTCOMES:
        diffs = []
        favorable = 0
        for a, b in pairs:
            d = value(a, key) - value(b, key)
            if not np.isnan(d):
                diffs.append(d)
                if (key == CLEARANCE and d > 0) or (key != CLEARANCE and d < 0):
                    favorable += 1
        med, lo, hi = bootstrap_median_ci(diffs, rng)
        mean, sd, p, n = paired_test(diffs)
        rows.append({
            "split": split_label,
            "method": method,
            "outcome": key,
            "outcome_label": label,
            "paired_n": n,
            "median_difference": med,
            "bootstrap_low": lo,
            "bootstrap_high": hi,
            "mean_difference": mean,
            "sd_difference": sd,
            "wilcoxon_p": p,
            "favorable_n": favorable,
            "favorable_percent": (100.0 * favorable / n) if n else None,
        })
    return rows, pairs


record_files = [Path("evaluation_records_v6.jsonl"), Path("pilot_records_v6.jsonl")]
records = []
for record_file in record_files:
    records.extend(
        json.loads(line)
        for line in record_file.open(encoding="utf-8")
        if line.strip()
    )
by_split = defaultdict(list)
for r in records:
    by_split[r["split"]].append(r)

primary = []
robustness = []
pair_counts = []
primary_rng = np.random.default_rng(SEED)
robustness_rng = np.random.default_rng(SEED + 1)

for method in METHODS:
    rows, pairs = analyze(by_split["evaluation"], method, "evaluation", primary_rng)
    primary.extend(rows)
    pair_counts.append({"method": method, "paired_n": len(pairs)})
    for split in ("pilot", "evaluation"):
        rows, _ = analyze(by_split[split], method, split, robustness_rng)
        robustness.extend(rows)

pvals = [r["wilcoxon_p"] for r in primary]
adjusted = holm(pvals)
for r, p_adj in zip(primary, adjusted):
    r["holm_adjusted_p"] = p_adj
    r["significant_holm_0.05"] = p_adj < 0.05

status_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
for r in records:
    status_counts[r["split"]][r["method"]][r["status"]] += 1

no_path_counts = {
    split: {method: counts.get("no_path", 0) for method, counts in methods.items()}
    for split, methods in status_counts.items()
}

result = {
    "revision": "analysis-v6",
    "prespecified_plan": PLAN.name,
    "records_files": ["evaluation_records_v6.jsonl", "pilot_records_v6.jsonl"],
    "record_count": len(records),
    "bootstrap_resamples": B,
    "bootstrap_seed": SEED,
    "confirmatory_tests": 24,
    "primary_analysis_split": "evaluation",
    "primary_comparisons": primary,
    "robustness_analyses": robustness,
    "paired_case_counts_evaluation": pair_counts,
    "no_path_counts_by_split_method": no_path_counts,
    "completion_status_counts_by_split_method": {
        split: {method: dict(counts) for method, counts in methods.items()}
        for split, methods in status_counts.items()
    },
}

out_json = Path("analysis_v6_results.json")
out_json.write_text(json.dumps(result, indent=2), encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        return
    fields = [
        "split", "method", "outcome", "outcome_label", "paired_n",
        "median_difference", "bootstrap_low", "bootstrap_high",
        "mean_difference", "sd_difference", "wilcoxon_p",
        "holm_adjusted_p", "significant_holm_0.05",
        "favorable_n", "favorable_percent",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


write_csv(Path("analysis_v6_primary.csv"), primary)
write_csv(Path("analysis_v6_robustness.csv"), robustness)

print(json.dumps({"primary_summary": [
    {
        "method": r["method"],
        "outcome": r["outcome"],
        "paired_n": r["paired_n"],
        "median_difference": r["median_difference"],
        "ci": [r["bootstrap_low"], r["bootstrap_high"]],
        "wilcoxon_p": r["wilcoxon_p"],
        "holm_p": r["holm_adjusted_p"],
        "significant": r["significant_holm_0.05"],
    }
    for r in primary
]}, indent=2))

print("WROTE:", out_json)
print("WROTE: analysis_v6_primary.csv")
print("WROTE: analysis_v6_robustness.csv")