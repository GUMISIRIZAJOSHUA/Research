"""Create Figure 8: operational-weight sensitivity median paired differences."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CSV_PATH = Path("table10_weight_sensitivity_v7.csv")
OUTPUT_PATH = Path("figure_weight_sensitivity_v7.png")

METHOD_LABELS = {
    "distance_dominant": "Distance-dominant",
    "energy_dominant": "Energy-dominant",
    "clearance_dominant": "Clearance-dominant",
    "soil_dominant": "Soil-dominant",
}

PANELS = [
    ("distance_m", "Distance difference (m)"),
    ("energy_Wh", "Modeled energy difference (Wh)"),
    ("minimum_swept_body_clearance_m", "Minimum clearance difference (m)"),
    ("clearance_exposure_m", "Clearance-exposure difference (m)"),
    ("mean_row_error_m", "Mean row-error difference (m)"),
]

METHOD_ORDER = [
    "distance_dominant",
    "energy_dominant",
    "clearance_dominant",
    "soil_dominant",
]

COLORS = {
    "distance_dominant": "#4C72B0",
    "energy_dominant": "#DD8452",
    "clearance_dominant": "#55A868",
    "soil_dominant": "#C44E52",
}


def main():
    df = pd.read_csv(CSV_PATH)

    fig, axes = plt.subplots(
        nrows=1,
        ncols=len(PANELS),
        figsize=(16, 4.8),
        sharey=True,
        constrained_layout=True,
    )

    y_positions = range(len(METHOD_ORDER))

    for ax, (outcome, label) in zip(axes, PANELS):
        subset = df[df["outcome"] == outcome].set_index("method")

        medians = []
        lower_errors = []
        upper_errors = []

        for method in METHOD_ORDER:
            row = subset.loc[method]
            median = float(row["median_difference"])
            lo = float(row["bootstrap_2.5pct"])
            hi = float(row["bootstrap_97.5pct"])

            medians.append(median)
            lower_errors.append(max(0.0, median - lo))
            upper_errors.append(max(0.0, hi - median))

        ax.barh(
            y_positions,
            medians,
            xerr=[lower_errors, upper_errors],
            color=[COLORS[m] for m in METHOD_ORDER],
            height=0.62,
            edgecolor="black",
            linewidth=0.5,
            capsize=3,
        )

        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Median paired difference", fontsize=9)
        ax.grid(axis="x", linestyle=":", alpha=0.45)
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=9)

        # Use separate x-limits when all values are zero.
        if all(abs(v) < 1e-12 for v in medians):
            ax.set_xlim(-0.05, 0.05)

    axes[0].set_yticks(list(y_positions))
    axes[0].set_yticklabels([METHOD_LABELS[m] for m in METHOD_ORDER])
    axes[0].invert_yaxis()

    fig.suptitle(
        "Operational-weight sensitivity relative to the equal-weight full formulation",
        fontsize=12,
        fontweight="bold",
    )

    fig.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Figure created: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()