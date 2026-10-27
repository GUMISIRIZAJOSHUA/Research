"""Compare v7 operational-weight sensitivity profiles with the v6 equal-weight full formulation."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

V6_RECORDS = Path("evaluation_records_v6.jsonl")
V7_RECORDS = Path("sensitivity_records_v7.jsonl")
OUTPUT_CSV = Path("table10_weight_sensitivity_v7.csv")
OUTPUT_JSON = Path("sensitivity_comparison_v7.json")

OUTCOMES = {
    "distance_m": "distance_m",
    "energy_Wh": "energy_Wh",
    "mission_time_s": "mission_time_s",
    "minimum_swept_body_clearance_m": "minimum_swept_body_clearance_m",
    "soil_exposure_m": "soil_exposure_m",
    "clearance_exposure_m": "clearance_exposure_m",
    "mean_row_error_m": "mean_row_error_m",
}
BOOTSTRAP_N = 10000
SEED = 20261028


def load_jsonl(path):
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("record_status") == "complete":
                rows.append(r)
    return rows


def bootstrap_median_ci(values, rng):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return np.nan, np.nan, np.nan
    median = float(np.median(values))
    if len(values) == 1:
        return median, median, median
    samples = np.empty(BOOTSTRAP_N)
    for i in range(BOOTSTRAP_N):
        sample = values[rng.integers(0, len(values), len(values))]
        samples[i] = np.median(sample)
    return median, float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))


def main():
    v6 = load_jsonl(V6_RECORDS)
    v7 = load_jsonl(V7_RECORDS)

    v6_full = {
        (r["family"], int(r["case"])): r
        for r in v6
        if r.get("method") == "full" and r.get("success", 0) == 1
    }

    v7_by_method = {}
    for r in v7:
        if r.get("success", 0) != 1:
            continue
        v7_by_method.setdefault(r["method"], {})[(r["family"], int(r["case"]))] = r

    rng = np.random.default_rng(SEED)
    output_rows = []
    comparison = {}

    for method in sorted(v7_by_method):
        method_rows = v7_by_method[method]
        paired_keys = sorted(set(method_rows) & set(v6_full))
        comparison[method] = {"paired_n": len(paired_keys), "outcomes": {}}

        for outcome, field in OUTCOMES.items():
            if field not in v6_full[paired_keys[0]] or field not in method_rows[paired_keys[0]]:
                continue

            differences = np.array([
                float(method_rows[k][field]) - float(v6_full[k][field])
                for k in paired_keys
            ])

            median, lo, hi = bootstrap_median_ci(differences, rng)
            favorable = int(np.sum(differences > 0))
            ties = int(np.sum(differences == 0))
            unfavorable = int(np.sum(differences < 0))

            comparison[method]["outcomes"][outcome] = {
                "paired_n": len(paired_keys),
                "median_difference": median,
                "bootstrap_95_ci": [lo, hi],
                "greater_than_reference": favorable,
                "equal_to_reference": ties,
                "less_than_reference": unfavorable,
            }

            output_rows.append({
                "method": method,
                "outcome": outcome,
                "paired_n": len(paired_keys),
                "median_difference": median,
                "bootstrap_2.5pct": lo,
                "bootstrap_97.5pct": hi,
                "greater_than_reference": favorable,
                "equal_to_reference": ties,
                "less_than_reference": unfavorable,
            })

    df = pd.DataFrame(output_rows)
    df.to_csv(OUTPUT_CSV, index=False)
    OUTPUT_JSON.write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    print(f"Paired sensitivity comparison complete.")
    print(f"Output table: {OUTPUT_CSV}")
    print(f"Output details: {OUTPUT_JSON}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()