"""Weight-sensitivity evaluation v7; 96 evaluation cases x 4 profiles = 384 missions.

Uses the frozen v6 generator and planner. Does not modify original v6 records.
"""
import argparse
import json
import platform
import time
from pathlib import Path

from agri_generator_v3 import make_world
from agri_planner_v4 import REVISION, run_mission

FAMILIES = 6
CASES = 16

SENSITIVITY_METHODS = {
    "distance_dominant": [0.40, 0.15, 0.15, 0.15, 0.15],
    "energy_dominant": [0.15, 0.40, 0.15, 0.15, 0.15],
    "clearance_dominant": [0.15, 0.15, 0.40, 0.15, 0.15],
    "soil_dominant": [0.15, 0.15, 0.15, 0.40, 0.15],
}

METHOD_ORDER = list(SENSITIVITY_METHODS)


def mission_key(family, case, method):
    return f"evaluation|F{family}|{case:02d}|{method}"


def load_done(path):
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("record_status") == "complete" and r.get("key"):
                done.add(r["key"])
    return done


def summarize(records):
    by_method = {}
    by_family = {}
    by_mission = {}

    for r in records:
        for scope, key in (
            (by_mission, r["key"]),
            (by_family, r["family"]),
            (by_method, r["method"]),
        ):
            s = scope.setdefault(key, {
                "n": 0,
                "success": 0,
                "geometric_completion": 0,
                "resource_energy_exceeded": 0,
                "resource_time_exceeded": 0,
                "verification_failure": 0,
                "search_ms": 0.0,
                "planning_ms": 0.0,
                "verification_ms": 0.0,
                "expanded_states": 0,
                "accepted_transitions": 0,
            })
            s["n"] += 1
            s["success"] += r["success"]
            s["geometric_completion"] += r["geometric_completion"]
            s["resource_energy_exceeded"] += r["resource_energy_exceeded"]
            s["resource_time_exceeded"] += r["resource_time_exceeded"]
            s["verification_failure"] += int(r["status"] == "verification_failure")
            for k in (
                "search_ms",
                "planning_ms",
                "verification_ms",
                "expanded_states",
                "accepted_transitions",
            ):
                s[k] += r[k]

    for scope in (by_mission, by_family, by_method):
        for s in scope.values():
            n = s["n"]
            s["success_rate"] = s["success"] / n
            s["geometric_completion_rate"] = s["geometric_completion"] / n
            for k in ("search_ms", "planning_ms", "verification_ms"):
                s[k + "_mean"] = s[k] / n

    return {
        "by_mission": by_mission,
        "by_family": by_family,
        "by_method": by_method,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--records", default="sensitivity_records_v7.jsonl")
    p.add_argument("--summary", default="sensitivity_summary_v7.json")
    p.add_argument("--limit-missions", type=int, default=0)
    args = p.parse_args()

    records_path = Path(args.records)
    summary_path = Path(args.summary)

    if records_path.exists() and summary_path.exists() and records_path.stat().st_mtime > summary_path.stat().st_mtime:
        raise RuntimeError("Records are newer than summary; rerun without deleting records.")

    done = load_done(records_path)
    total = FAMILIES * CASES * len(METHOD_ORDER)
    expected = min(total, args.limit_missions) if args.limit_missions else total

    print(f"Sensitivity revision: {REVISION}; expected missions: {expected}; already complete: {len(done)}")

    started = time.perf_counter()
    completed_now = 0
    mode = "a" if records_path.exists() else "x"

    with records_path.open(mode, encoding="utf-8") as out:
        for family in range(1, FAMILIES + 1):
            for case in range(1, CASES + 1):
                world = make_world(family, case, "evaluation")

                for method in METHOD_ORDER:
                    key = mission_key(family, case, method)

                    if key in done:
                        continue

                    if args.limit_missions and completed_now >= args.limit_missions:
                        break

                    weights = SENSITIVITY_METHODS[method]
                    record, path = run_mission(world, weights)

                    row = {
                        "key": key,
                        "record_status": "complete",
                        "revision": REVISION,
                        "analysis": "operational_weight_sensitivity_v7",
                        "split": "evaluation",
                        "family": f"F{family}",
                        "case": case,
                        "method": method,
                        "weights": weights,
                        "python": platform.python_version(),
                        "platform": platform.platform(),
                        "route_state_count": int(len(path)),
                        "recorded_at": time.time(),
                        **record,
                    }

                    out.write(json.dumps(row, separators=(",", ":")) + "\n")
                    out.flush()
                    completed_now += 1

                    print(
                        f"{key}: {record['status']} "
                        f"search={record['search_ms']:.1f} ms "
                        f"states={len(path)} "
                        f"energy={record.get('energy_Wh')} Wh"
                    )

                if args.limit_missions and completed_now >= args.limit_missions:
                    break

            if args.limit_missions and completed_now >= args.limit_missions:
                break

    all_rows = []
    if records_path.exists():
        for line in records_path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("record_status") == "complete":
                all_rows.append(r)

    summary = summarize(all_rows)
    summary.update({
        "revision": REVISION,
        "analysis": "operational_weight_sensitivity_v7",
        "expected_total_missions": total,
        "completed_missions": len(all_rows),
        "missing_missions": total - len(all_rows),
        "elapsed_seconds_this_invocation": time.perf_counter() - started,
        "reference_profile": [0.20, 0.20, 0.20, 0.20, 0.20],
        "limitations": [
            "Descriptive sensitivity analysis only; no confirmatory inference or publication claims.",
            "Uses the frozen v6 generator, planner, hard constraints, and evaluation cases.",
            "Does not modify or replace the locked v6 primary evaluation records.",
            "No physical calibration, continuous-motion validation, or external-baseline comparison.",
        ],
    })

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Completed this invocation: {completed_now}; total complete: {len(all_rows)}/{total}")
    print(f"Records: {records_path}")
    print(f"Summary: {summary_path}")

    if len(all_rows) == total:
        print("SENSITIVITY EVALUATION COMPLETE.")


if __name__ == "__main__":
    main()