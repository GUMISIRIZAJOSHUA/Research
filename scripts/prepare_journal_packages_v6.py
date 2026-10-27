from pathlib import Path
import hashlib
import io
import json
import zipfile

PROJECT = Path("../agri_experiment_work")
RELEASE = PROJECT / "agri_release_v6.zip"
CHECKSUM = PROJECT / "agri_release_v6.zip.sha256"

EXPECTED_SHA256 = (
    "b53033d4ea7a2aa01ddca51821d2049368"
    "beab8ca5724f003ed8df55fe90a430"
)

OUTPUT = Path("journal_submission_candidates_v6")

evidence_paths = [
    Path("clean_test_hash_comparison_v6.txt"),
    Path("clean_test_requirements_v6.txt"),
    Path("clean_test_python_v6.txt"),
    Path("section6_summary_v6.txt"),
]

for path in [RELEASE, CHECKSUM] + evidence_paths:
    if not path.is_file():
        raise SystemExit(f"Missing required file: {path}")

release_bytes = RELEASE.read_bytes()
release_hash = hashlib.sha256(release_bytes).hexdigest()

if release_hash != EXPECTED_SHA256:
    raise SystemExit("Original release ZIP SHA-256 does not match.")

checksum_text = CHECKSUM.read_text(encoding="utf-8")
if checksum_text.split()[0].lower() != release_hash:
    raise SystemExit("Release checksum file does not match the ZIP.")

comparison_lines = [
    line.strip()
    for line in evidence_paths[0].read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]

expected_matches = {
    "MATCH analysis_v6_results.json",
    "MATCH analysis_v6_primary.csv",
    "MATCH analysis_v6_robustness.csv",
    "MATCH RESULTS_v6.md",
}

if set(comparison_lines) != expected_matches or len(comparison_lines) != 4:
    raise SystemExit("Clean-test comparison evidence is not four expected MATCH lines.")

figure_names = [
    "figure_primary_forest_v6.png",
    "figure_robustness_medians_v6.png",
    "figure_computational_cost_v6.png",
]

with zipfile.ZipFile(io.BytesIO(release_bytes), "r") as release:
    if release.testzip() is not None:
        raise SystemExit("Original release archive failed its integrity check.")

    manifest = json.loads(
        release.read("release_manifest_v6.json")
    )

    for entry in manifest["files"]:
        data = release.read(entry["path"])
        if len(data) != entry["bytes"]:
            raise SystemExit(f"Archived size mismatch: {entry['path']}")
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise SystemExit(f"Archived hash mismatch: {entry['path']}")

    figure_data = {
        f"figures/{name}": release.read(f"figures/{name}")
        for name in figure_names
    }

readme = """V6 RESEARCH SUPPLEMENT: SUBMISSION CANDIDATE

Status
This package preserves the verified v6 release and accompanying
same-machine clean-environment evidence. It does not include the
manuscript, which requires final methods/results reconciliation.

Contents
- release/agri_release_v6.zip: original verified research release.
- release/agri_release_v6.zip.sha256: original archive checksum.
- evidence/: clean-test comparison, dependencies, and Python version.
- results/section6_summary_v6.txt: derived descriptive results extract.

To reproduce the analysis
1. Extract release/agri_release_v6.zip into a separate directory.
2. Use a compatible Python environment; the tested version is recorded
   in evidence/clean_test_python_v6.txt.
3. Create a fresh virtual environment.
4. Install requirements_v6.txt from the inner release.
5. Run analysis_v6.py, make_results_report_v6.py, and make_figures_v6.py.

Confirmed checks
- Independent verifier: 945 successful routes checked, 945 passed.
- Primary evaluation: 94 paired cases per comparison.
- Corrected Holm procedure: 21 of 24 tests significant at 0.05.
- Pilot descriptive comparisons: 95 paired cases per comparison.
- Four analysis/report files reproduced byte-for-byte in a fresh
  virtual environment on the same Windows machine.

Interpretation and limitations
- Configurations use different objective weights. Stored scalarized
  costs are not a common performance score.
- Complete route-state sequences were not persisted in v6 records;
  independent verification regenerated routes with the frozen planner.
- The clean test did not establish full benchmark regeneration,
  cross-machine reproducibility, or figure-byte identity.
- No physical field or robot performance is established.
- No claim is made here that all experiments proposed in earlier
  manuscript drafts were executed.

The compact Section 6 summary includes descriptive timing quartiles
and clearance sign counts, not additional confirmatory tests.
"""

figure_index = """FIGURE INDEX: V6 SUBMISSION CANDIDATE

Files are copied unchanged from the verified release archive.

1. figure_primary_forest_v6.png
   Median paired differences and 95% percentile bootstrap intervals
   for the six primary-analysis outcomes; evaluation n=94.
   Proposed manuscript placement: Section 6.2.

2. figure_robustness_medians_v6.png
   Descriptive pilot/evaluation median differences.
   Pilot n=95; evaluation n=94.
   Proposed manuscript placement: Section 6.4.

3. figure_computational_cost_v6.png
   Search-time boxplots for successful evaluation missions.
   Proposed manuscript placement: Section 6.5.

Final manuscript figure numbering and captions must be reconciled
before submission. This index is not a substitute for final captions.
"""

supplement = {
    "README.txt": readme.encode("utf-8"),
    "release/agri_release_v6.zip": release_bytes,
    "release/agri_release_v6.zip.sha256": CHECKSUM.read_bytes(),
}

for path in evidence_paths[:3]:
    supplement[f"evidence/{path.name}"] = path.read_bytes()

supplement["results/section6_summary_v6.txt"] = evidence_paths[3].read_bytes()

figures = dict(figure_data)
figures["FIGURE_INDEX.txt"] = figure_index.encode("utf-8")

OUTPUT.mkdir(exist_ok=False)


def write_and_check(name, members):
    inventory = [
        {
            "path": member,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for member, data in sorted(members.items())
    ]
    members = dict(members)
    members["PACKAGE_CONTENTS.json"] = json.dumps(
        inventory, indent=2
    ).encode("utf-8")

    target = OUTPUT / name
    with zipfile.ZipFile(
        target, "x", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for member, data in members.items():
            archive.writestr(member, data)

    with zipfile.ZipFile(target, "r") as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Integrity failure: {target}")
        if sorted(archive.namelist()) != sorted(members):
            raise SystemExit(f"Member-list mismatch: {target}")
        for member, data in members.items():
            if archive.read(member) != data:
                raise SystemExit(f"Content mismatch: {member}")

    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    checksum = target.with_suffix(target.suffix + ".sha256")
    checksum.write_text(
        f"{digest}  {target.name}\n", encoding="utf-8"
    )

    print("PACKAGE:", target.name)
    print("MEMBERS:", len(members))
    print("BYTES:", target.stat().st_size)
    print("SHA256:", digest)
    print("CONTENT_CHECK: PASS")


write_and_check("journal_supplement_v6.zip", supplement)
write_and_check("journal_figures_v6.zip", figures)