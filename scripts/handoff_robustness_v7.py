import csv
import json
import time
from pathlib import Path
import heapq
import numpy as np

from agri_generator_v3 import make_world
from agri_planner_v4 import (
    METHODS, SCALES, PARAM, prepare, valid_position, xy, transition,
    search, run_mission, verify_route
)

FAMILIES = range(1, 7)
SEEDS = [0, 1, 2]          # 18 evaluation cases: 3 per family
SPLIT = "evaluation"
OUT_CSV = Path("handoff_robustness_v7_records.csv")
OUT_JSON = Path("handoff_robustness_v7_summary.json")


def search_to_heading(w, start, goal, goal_heading, weights, multiplier=1.0, limit=None):
    """
    Same search rules as agri_planner_v4.search, but requires a specified
    arrival heading at the goal position.
    """
    weights = np.asarray(weights, dtype=float)
    start = tuple(map(int, start))
    goal = tuple(map(int, goal))
    prepare(w)

    stats = dict(
        expanded_states=0,
        queue_pops=0,
        stale_entries=0,
        generated_transitions=0,
        accepted_transitions=0,
    )
    begin = time.perf_counter()

    def finish(status, path=None, cost=None):
        return dict(
            status=status,
            path=path,
            cost=cost,
            search_ms=(time.perf_counter() - begin) * 1000,
            **stats,
        )

    if not valid_position(w, start) or not valid_position(w, goal):
        return finish("invalid_endpoint")
    if not (0 <= start[2] < 8) or not (0 <= goal_heading < 8):
        return finish("invalid_endpoint")

    allowance = PARAM["expansion_limit_per_segment"] if limit is None else limit

    def heuristic(a):
        return weights[0] * np.linalg.norm(xy(w, a) - xy(w, goal)) / SCALES[0]

    queue = [(heuristic(start), 0.0, 0, start)]
    counter = 0
    best = {start: 0.0}
    parent = {}

    while queue:
        _, g, _, a = heapq.heappop(queue)
        stats["queue_pops"] += 1

        if g > best[a] + PARAM["cost_update_tolerance"]:
            stats["stale_entries"] += 1
            continue

        if a[:2] == goal and a[2] == goal_heading:
            path = [a]
            while path[-1] != start:
                path.append(parent[path[-1]])
            return finish("success", path[::-1], g)

        if stats["expanded_states"] >= allowance:
            return finish("expansion_limit")

        stats["expanded_states"] += 1

        for heading in ((a[2] - 1) % 8, a[2], (a[2] + 1) % 8):
            stats["generated_transitions"] += 1
            tr = transition(w, a, heading, multiplier)
            if tr is None:
                continue

            stats["accepted_transitions"] += 1
            b, values, *_ = tr
            candidate = g + float(weights @ (values / SCALES))

            if candidate < best.get(b, np.inf) - PARAM["cost_update_tolerance"]:
                best[b] = candidate
                parent[b] = a
                counter += 1
                heapq.heappush(
                    queue,
                    (candidate + heuristic(b), candidate, counter, b),
                )

    return finish("no_path")


def lookahead_mission(w, weights, multiplier=1.0):
    """
    One-step lookahead over arrival headings at each intermediate waypoint.

    At waypoint i, the planner selects the arrival heading that minimizes:
        cost to waypoint i under heading h
      + best cost from waypoint i under heading h to waypoint i + 1

    The final waypoint uses the original position-only search.
    """
    weights = np.asarray(weights, dtype=float)
    goals = [tuple(map(int, g)) for g in w["goals"]]
    path = [tuple(map(int, w["start"]))]
    completed = 0
    total_cost = 0.0
    status = "success"
    selected_headings = []

    for i, goal in enumerate(goals):
        start_state = path[-1]
        is_last = i == len(goals) - 1

        if is_last:
            result = search(w, start_state, goal, weights, multiplier)
            if result["status"] != "success":
                return dict(
                    status=result["status"],
                    path=path,
                    completed=completed,
                    cost=total_cost,
                    selected_headings=selected_headings,
                )

            path.extend(result["path"][1:])
            total_cost += float(result["cost"])
            completed += 1
            continue

        best_choice = None

        for arrival_heading in range(8):
            to_waypoint = search_to_heading(
                w,
                start_state,
                goal,
                arrival_heading,
                weights,
                multiplier,
            )

            if to_waypoint["status"] != "success":
                continue

            next_start = (goal[0], goal[1], arrival_heading)
            next_result = search(
                w,
                next_start,
                goals[i + 1],
                weights,
                multiplier,
            )

            if next_result["status"] != "success":
                continue

            pair_cost = float(to_waypoint["cost"]) + float(next_result["cost"])

            if best_choice is None or pair_cost < best_choice["cost"]:
                best_choice = dict(
                    heading=arrival_heading,
                    cost=pair_cost,
                    to_waypoint=to_waypoint,
                    next_result=next_result,
                )

        if best_choice is None:
            return dict(
                status="lookahead_no_path",
                path=path,
                completed=completed,
                cost=total_cost,
                selected_headings=selected_headings,
            )

        path.extend(best_choice["to_waypoint"]["path"][1:])
        total_cost += float(best_choice["to_waypoint"]["cost"])
        completed += 1
        selected_headings.append(best_choice["heading"])

    return dict(
        status=status,
        path=path,
        completed=completed,
        cost=total_cost,
        selected_headings=selected_headings,
    )


def metrics_for(w, path, weights, multiplier=1.0):
    return verify_route(
        w,
        path,
        w["goals"][: len(w["goals"])],
        weights,
        multiplier,
    )


def main():
    rows = []
    summaries = []

    metric_keys = [
        "distance_m",
        "energy_Wh",
        "mission_time_s",
        "minimum_swept_body_clearance_m",
        "clearance_exposure_m",
        "soil_exposure_m",
        "mean_row_error_m",
        "scalarized_cost",
    ]

    for family in FAMILIES:
        for seed in SEEDS:
            w = make_world(family, seed, SPLIT)

            for method, weights in METHODS.items():
                weights = np.asarray(weights, dtype=float)

                baseline_record, baseline_path = run_mission(w, weights)
                baseline_metrics = None
                if baseline_record["status"] == "success":
                    baseline_metrics = metrics_for(w, baseline_path, weights)

                lookahead = lookahead_mission(w, weights)
                lookahead_metrics = None
                if lookahead["status"] == "success":
                    lookahead_metrics = metrics_for(
                        w,
                        np.asarray(lookahead["path"], dtype=int),
                        weights,
                    )

                row = dict(
                    family=family,
                    seed=seed,
                    method=method,
                    baseline_status=baseline_record["status"],
                    lookahead_status=lookahead["status"],
                )

                for key in metric_keys:
                    baseline_value = (
                        None
                        if baseline_metrics is None
                        else baseline_metrics.get(key)
                    )
                    lookahead_value = (
                        None
                        if lookahead_metrics is None
                        else lookahead_metrics.get(key)
                    )

                    difference = None
                    if baseline_value is not None and lookahead_value is not None:
                        difference = lookahead_value - baseline_value

                    row[f"baseline_{key}"] = baseline_value
                    row[f"lookahead_{key}"] = lookahead_value
                    row[f"difference_{key}"] = difference

                rows.append(row)
                summaries.append(row)

                print(
                    f"F{family} seed={seed} {method}: "
                    f"baseline={baseline_record['status']}, "
                    f"lookahead={lookahead['status']}"
                )

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            dict(
                analysis="one_step_arrival_heading_lookahead_robustness",
                families=list(FAMILIES),
                seeds=SEEDS,
                split=SPLIT,
                methods=list(METHODS.keys()),
                records=summaries,
            ),
            f,
            indent=2,
        )

    print(f"Wrote {OUT_CSV} and {OUT_JSON}")


if __name__ == "__main__":
    main()