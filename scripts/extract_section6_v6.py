from pathlib import Path
import json
from collections import defaultdict
from statistics import median

analysis = json.loads(
    Path("analysis_v6_results.json").read_text(encoding="utf-8")
)
records = [
    json.loads(line)
    for line in Path("evaluation_records_v6.jsonl")
    .read_text(encoding="utf-8").splitlines()
    if line.strip()
]

def fmt(value):
    return "NA" if value is None else f"{value:.8g}"

lines = [
    "SECTION 6 DATA SUMMARY",
    "",
    "PRIMARY COMPARISONS",
    "method | outcome | n | median difference | CI low | CI high | Holm p",
]

for row in analysis["primary_comparisons"]:
    lines.append(
        f"{row['method']} | {row['outcome']} | {row['paired_n']} | "
        f"{fmt(row['median_difference'])} | "
        f"{fmt(row['bootstrap_low'])} | "
        f"{fmt(row['bootstrap_high'])} | "
        f"{fmt(row['holm_adjusted_p'])}"
    )

lines += [
    "",
    "DESCRIPTIVE ROBUSTNESS",
    "split | method | outcome | n | median difference | CI low | CI high | favorable %",
]

for row in analysis["robustness_analyses"]:
    lines.append(
        f"{row['split']} | {row['method']} | {row['outcome']} | "
        f"{row['paired_n']} | {fmt(row['median_difference'])} | "
        f"{fmt(row['bootstrap_low'])} | "
        f"{fmt(row['bootstrap_high'])} | "
        f"{fmt(row['favorable_percent'])}"
    )

lines += [
    "",
    "COMPLETION STATUS COUNTS",
    json.dumps(
        analysis["completion_status_counts_by_split_method"],
        indent=2,
    ),
]

by_method = defaultdict(list)
for record in records:
    if record.get("split") == "evaluation":
        by_method[record["method"]].append(record)

lines += [
    "",
    "COMPUTATIONAL SUMMARY",
    "Timing and search-effort summaries are conditional on success.",
    "Quartiles use numpy's linear percentile method.",
]

import numpy as np

for method in sorted(by_method):
    attempts = by_method[method]
    successful = [r for r in attempts if r.get("success")]
    lines.append(
        f"{method}: attempts={len(attempts)}, "
        f"successful={len(successful)}"
    )

    for metric in (
        "search_ms",
        "planning_ms",
        "preprocessing_ms",
        "verification_ms",
        "expanded_states",
        "queue_pops",
        "stale_entries",
    ):
        values = [
            float(r[metric])
            for r in successful
            if r.get(metric) is not None
        ]
        if values:
            q1, q3 = np.percentile(values, [25, 75])
            lines.append(
                f"  {metric}: n={len(values)}, "
                f"median={fmt(median(values))}, "
                f"Q1={fmt(q1)}, Q3={fmt(q3)}"
            )

lines += ["", "EVALUATION CLEARANCE SIGN COUNTS"]
by_case = defaultdict(dict)
for record in records:
    if record.get("split") == "evaluation":
        by_case[(record["family"], record["case"])][
            record["method"]
        ] = record

for method in ("distance", "energy", "soil", "distance_clearance"):
    differences = []
    for case in by_case.values():
        a, b = case.get(method), case.get("full")
        if a and b and a.get("success") and b.get("success"):
            x = a.get("minimum_swept_body_clearance_m")
            y = b.get("minimum_swept_body_clearance_m")
            if x is not None and y is not None:
                differences.append(float(x) - float(y))

    lines.append(
        f"{method}: n={len(differences)}, "
        f"greater={sum(d > 0 for d in differences)}, "
        f"equal={sum(d == 0 for d in differences)}, "
        f"lower={sum(d < 0 for d in differences)}"
    )

output = Path("section6_summary_v6.txt")
output.write_text("\n".join(lines), encoding="utf-8")

print("WROTE:", output)
print("BYTES:", output.stat().st_size)