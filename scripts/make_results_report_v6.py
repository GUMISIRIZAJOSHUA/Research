from pathlib import Path
import json
import csv

RESULTS = Path("analysis_v6_results.json")
PRIMARY = Path("analysis_v6_primary.csv")
ROBUST = Path("analysis_v6_robustness.csv")
OUT = Path("RESULTS_v6.md")

r = json.loads(RESULTS.read_text(encoding="utf-8"))

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fmt(x, digits=4):
    x = num(x)
    if x is None:
        return "—"
    return f"{x:.{digits}g}"
def load_csv(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

primary = load_csv(PRIMARY)
robust = load_csv(ROBUST)

method_names = {
    "distance": "Distance-focused",
    "energy": "Energy-focused",
    "soil": "Soil-focused",
    "distance_clearance": "Distance-clearance",
}

outcome_names = {
    "scalarized_cost": "Scalarized cost",
    "distance_m": "Distance (m)",
    "energy_Wh": "Energy (Wh)",
    "mission_time_s": "Mission time (s)",
    "mean_row_error_m": "Mean row error (m)",
    "minimum_swept_body_clearance_m": "Minimum clearance (m)",
}

lines = []
lines.append("# Results")
lines.append("")
lines.append("## Verification and analysis set")
lines.append("")
verification = json.loads(Path("independent_verification_v6.json").read_text(encoding="utf-8"))
lines.append(
    f"The independent verifier checked {verification['successful_routes_checked']} successful routes; "
    f"{verification['routes_passed']} passed and {verification['routes_failed']} failed. "
    f"The maximum absolute scalarized-cost discrepancy was "
    f"{verification['max_absolute_scalarized_cost_difference']:.3g}."
)
lines.append("")
lines.append(
    "The primary analysis used the evaluation split. Each of the four reference configurations "
    "was compared with the full five-objective formulation on the same 94 jointly successful cases."
)
lines.append("")
lines.append("## Primary comparisons")
lines.append("")
lines.append(
    "Differences are method minus full composite. For minimum clearance, positive differences "
    "indicate greater clearance; for all other outcomes, negative differences indicate lower values. "
    "Bootstrap intervals are 95% percentile intervals from 10,000 paired case resamples. "
    "Wilcoxon p-values were Holm-adjusted across all 24 prespecified tests."
)
lines.append("")
lines.append("| Comparison | Outcome | Paired n | Median difference | 95% bootstrap CI | Wilcoxon p | Holm-adjusted p |")
lines.append("|---|---|---:|---:|---:|---:|---:|")
for x in primary:
    lines.append(
        f"| {method_names[x['method']]} vs. full | {outcome_names[x['outcome']]} | "
        f"{x['paired_n']} | {fmt(num(x['median_difference']))} | "
        f"[{fmt(num(x['bootstrap_low']))}, {fmt(num(x['bootstrap_high']))}] | "
        f"{fmt(num(x['wilcoxon_p']))} | {fmt(num(x['holm_adjusted_p']))} |"
    )
lines.append("")
lines.append("## Robustness across splits")
lines.append("")
lines.append("The following descriptive checks repeat the paired median estimates separately for the pilot and evaluation splits.")
lines.append("")
lines.append("| Split | Comparison | Outcome | Paired n | Median difference | 95% bootstrap CI |")
lines.append("|---|---|---|---:|---:|---:|")
for x in robust:
    lines.append(
        f"| {x['split']} | {method_names[x['method']]} vs. full | {outcome_names[x['outcome']]} | "
        f"{x['paired_n']} | {fmt(num(x['median_difference']))} | "
        f"[{fmt(num(x['bootstrap_low']))}, {fmt(num(x['bootstrap_high']))}] |"
    )
lines.append("")
lines.append("## Completion outcomes")
lines.append("")
lines.append("| Split | Method | Status counts |")
lines.append("|---|---|---|")
for split, methods in r["completion_status_counts_by_split_method"].items():
    for method, counts in methods.items():
        rendered = ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))
        lines.append(f"| {split} | {method_names.get(method, method)} | {rendered} |")
lines.append("")
lines.append("## Interpretation boundary")
lines.append("")
lines.append(
    "Scalarized-cost comparisons reflect each configuration’s declared objective and do not establish "
    "cross-method superiority. Results apply only to the implemented synthetic grid-world model, its "
    "declared parameters, and its generated cases; they do not establish field performance, physical-robot "
    "validity, calibrated energy consumption, agronomic benefit, or real-world routing superiority."
)
lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"WROTE: {OUT}")
print(f"Primary rows: {len(primary)}")
print(f"Robustness rows: {len(robust)}")