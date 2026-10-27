from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt

RESULTS = Path("analysis_v6_results.json")
RECORDS = Path("evaluation_records_v6.jsonl")
OUTDIR = Path("figures")
OUTDIR.mkdir(exist_ok=True)

r = json.loads(RESULTS.read_text(encoding="utf-8"))
primary = r["primary_comparisons"]
robustness = r["robustness_analyses"]

methods = ["distance", "energy", "soil", "distance_clearance"]
method_labels = {
    "distance": "Distance-focused",
    "energy": "Energy-focused",
    "soil": "Soil-focused",
    "distance_clearance": "Distance-clearance",
}
outcomes = [
    "scalarized_cost",
    "distance_m",
    "energy_Wh",
    "mission_time_s",
    "mean_row_error_m",
    "minimum_swept_body_clearance_m",
]
outcome_labels = {
    "scalarized_cost": "Scalarized cost",
    "distance_m": "Distance (m)",
    "energy_Wh": "Energy (Wh)",
    "mission_time_s": "Mission time (s)",
    "mean_row_error_m": "Mean row error (m)",
    "minimum_swept_body_clearance_m": "Minimum clearance (m)",
}

# Figure 1: primary forest plot, one panel per outcome.
fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey=True)
axes = axes.ravel()

for ax, outcome in zip(axes, outcomes):
    rows = [x for x in primary if x["outcome"] == outcome]
    ys = np.arange(len(methods))
    medians = [x["median_difference"] for x in rows]
    lows = [x["bootstrap_low"] for x in rows]
    highs = [x["bootstrap_high"] for x in rows]
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

    for y, med, lo, hi, color in zip(ys, medians, lows, highs, colors):
        ax.plot([lo, hi], [y, y], color=color, lw=2, alpha=0.8)
        ax.plot(med, y, "o", color=color, ms=6)

    ax.axvline(0, color="black", lw=1, linestyle="--", alpha=0.7)
    ax.set_yticks(ys)
    ax.set_yticklabels([method_labels[m] for m in methods])
    ax.set_title(outcome_labels[outcome], fontsize=11)
    ax.grid(axis="x", alpha=0.25)
    ax.invert_yaxis()

fig.suptitle("Primary paired differences versus full five-objective formulation", fontsize=14)
fig.text(0.5, 0.02, "Median difference; bars show 95% percentile bootstrap confidence intervals", ha="center")
fig.tight_layout(rect=[0, 0.04, 1, 0.95])
fig.savefig(OUTDIR / "figure_primary_forest_v6.png", dpi=300)
plt.close(fig)

# Figure 2: pilot versus evaluation median differences.
fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharey=True)
axes = axes.ravel()

for ax, outcome in zip(axes, outcomes):
    pilot = [x for x in robustness if x["outcome"] == outcome and x["split"] == "pilot"]
    evaluation = [x for x in robustness if x["outcome"] == outcome and x["split"] == "evaluation"]
    ys = np.arange(len(methods))
    width = 0.35

    pilot_medians = [x["median_difference"] for x in pilot]
    evaluation_medians = [x["median_difference"] for x in evaluation]

    ax.barh(ys - width / 2, pilot_medians, height=width, label="Pilot", color="#4c78a8")
    ax.barh(ys + width / 2, evaluation_medians, height=width, label="Evaluation", color="#f58518")
    ax.axvline(0, color="black", lw=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([method_labels[m] for m in methods])
    ax.set_title(outcome_labels[outcome], fontsize=11)
    ax.grid(axis="x", alpha=0.25)
    ax.invert_yaxis()

axes[0].legend(loc="lower right")
fig.suptitle("Robustness of median paired differences across pilot and evaluation splits", fontsize=14)
fig.text(0.5, 0.02, "Method minus full composite", ha="center")
fig.tight_layout(rect=[0, 0.04, 1, 0.95])
fig.savefig(OUTDIR / "figure_robustness_medians_v6.png", dpi=300)
plt.close(fig)

# Figure 3: computational cost by method.
records = [json.loads(line) for line in RECORDS.open(encoding="utf-8") if line.strip()]
search_times = {m: [] for m in methods + ["full"]}
for record in records:
    if record.get("split") == "evaluation" and record.get("success"):
        search_times[record["method"]].append(record["search_ms"])

fig, ax = plt.subplots(figsize=(8, 4.5))
data = [search_times[m] for m in methods + ["full"]]
labels = [method_labels.get(m, "Full five-objective") for m in methods + ["full"]]
ax.boxplot(data, tick_labels=labels, showfliers=False)
ax.set_ylabel("Search time (ms)")
ax.set_title("Computational search cost on successful evaluation routes")
ax.grid(axis="y", alpha=0.25)
plt.xticks(rotation=20, ha="right")
fig.tight_layout()
fig.savefig(OUTDIR / "figure_computational_cost_v6.png", dpi=300)
plt.close(fig)

print("WROTE: figures/figure_primary_forest_v6.png")
print("WROTE: figures/figure_robustness_medians_v6.png")
print("WROTE: figures/figure_computational_cost_v6.png")