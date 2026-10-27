from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import platform
import sys

required = [
    "ANALYSIS_PLAN_v6.md",
    "analysis_plan_checksum_v6.json",
    "development_manifest_v6.json",
    "evaluation_records_v6.jsonl",
    "pilot_records_v6.jsonl",
    "evaluation_summary_v6.json",
    "pilot_summary_v6.json",
    "independent_verifier_v6.py",
    "independent_verification_v6.json",
    "analysis_v6.py",
    "analysis_v6_results.json",
    "analysis_v6_primary.csv",
    "analysis_v6_robustness.csv",
    "make_results_report_v6.py",
    "RESULTS_v6.md",
    "make_figures_v6.py",
    "make_manifest_v6.py",
    "requirements_v6.txt",
    "agri_evaluation_v6.py",
    "agri_pilot_v6.py",
    "agri_planner_v4.py",
    "agri_generator_v2.py",
    "agri_generator_v3.py",
    "figures/figure_primary_forest_v6.png",
    "figures/figure_robustness_medians_v6.png",
    "figures/figure_computational_cost_v6.png",
]

paths = [Path(name) for name in required]
missing = [p.as_posix() for p in paths if not p.is_file()]
if missing:
    raise SystemExit("Missing required files:\n" + "\n".join(missing))

entries = []
for path in paths:
    data = path.read_bytes()
    if not data:
        raise SystemExit(f"Empty required file: {path}")
    entries.append({
        "path": path.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })

manifest = {
    "revision": "release-inventory-v6",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "python": sys.version,
    "platform": platform.platform(),
    "scope": (
        "Inventory of current analysis, verification, source, and figure files. "
        "Hashes record current contents; they do not independently certify "
        "scientific validity, dependency completeness, or agreement with "
        "the earlier frozen development manifest."
    ),
    "files": entries,
}

output = Path("release_manifest_v6.json")
with output.open("x", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("WROTE:", output)
print("FILES_HASHED:", len(entries))
print("TOTAL_BYTES:", sum(x["bytes"] for x in entries))