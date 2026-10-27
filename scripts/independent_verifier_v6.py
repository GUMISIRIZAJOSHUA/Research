"""Independent verification of frozen v6 successful routes.
Regenerates routes with the frozen planner, then recomputes metrics using
separately written geometry and cost code. Does not modify v6 records.
"""
import json
import math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from agri_generator_v3 import make_world
from agri_planner_v4 import METHODS, PARAM, run_mission

REVISION = 'independent-verifier-v6'
FILES = ['pilot_records_v6.jsonl', 'evaluation_records_v6.jsonl']
METHODS_ORDER = ['distance', 'energy', 'soil', 'distance_clearance', 'full']
SCALES = np.array([1.0, 60.0, 1.0, 1.0, 1.0])
SAMPLE_STEP_M = 0.02
TOL = {'distance_m': 1e-8, 'energy_Wh': 1e-8, 'mission_time_s': 1e-8,
       'row_integral_m2': 1e-8, 'mean_row_error_m': 1e-8,
       'minimum_swept_body_clearance_m': 2e-4, 'scalarized_cost': 1e-8}

def load_jsonl(name):
    with open(name, encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]

def xy(world, state):
    return (np.array([state[1], state[0]], dtype=float) + 0.5) * world['res']

def rectangle_distance(point, world):
    """Independent point-to-occupied-cell-rectangle distance."""
    px, py = point
    half = world['res'] / 2.0
    occupied = np.argwhere(world['raw'])
    if not len(occupied):
        return math.inf
    dx = np.maximum(np.abs(occupied[:, 1] * world['res'] + half - px) - half, 0.0)
    dy = np.maximum(np.abs(occupied[:, 0] * world['res'] + half - py) - half, 0.0)
    return float(np.min(np.hypot(dx, dy)))

def segment_segment_distance(p1, p2, q1, q2):
    d1 = p2 - p1
    d2 = q2 - q1
    r = p1 - q1
    a = float(d1 @ d1)
    e = float(d2 @ d2)
    f = float(d2 @ r)
    if a <= 1e-15 and e <= 1e-15:
        return float(np.linalg.norm(r))
    if a <= 1e-15:
        s = 0.0
        t = np.clip(f / e, 0.0, 1.0)
    else:
        c = float(d1 @ r)
        if e <= 1e-15:
            t = 0.0
            s = np.clip(-c / a, 0.0, 1.0)
        else:
            b = float(d1 @ d2)
            denom = a * e - b * b
            s = np.clip((b * f - c * e) / denom, 0.0, 1.0) if denom > 1e-15 else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t = 0.0
                s = np.clip(-c / a, 0.0, 1.0)
            elif t > 1.0:
                t = 1.0
                s = np.clip((b - c) / a, 0.0, 1.0)
    closest1 = p1 + s * d1
    closest2 = q1 + t * d2
    return float(np.linalg.norm(closest1 - closest2))

def segment_rectangle_distance_independent(a, b, world):
    if '_verifier_tree' not in world:
        occupied = np.argwhere(world['raw'])
        centers = np.column_stack((occupied[:, 1] * world['res'] + world['res'] / 2.0,
                                   occupied[:, 0] * world['res'] + world['res'] / 2.0))
        world['_verifier_tree'] = cKDTree(centers)
        world['_verifier_centers'] = centers
    tree = world['_verifier_tree']
    centers = world['_verifier_centers']
    half = world['res'] / 2.0
    midpoint = (a + b) / 2.0
    nearest_distance = float(tree.query(midpoint)[0])
    radius = nearest_distance + float(np.linalg.norm(b - a)) / 2.0 + world['res'] * math.sqrt(2.0) + 1e-9
    candidates = tree.query_ball_point(midpoint, radius)
    if not candidates:
        return math.inf
    best = math.inf
    for i in candidates:
        lo = centers[i] - half
        hi = centers[i] + half
        d = b - a
        tmin, tmax = 0.0, 1.0
        parallel_overlap = True
        for dim in range(2):
            if abs(d[dim]) < 1e-15:
                parallel_overlap &= (a[dim] >= lo[dim]) and (a[dim] <= hi[dim])
            else:
                t1 = (lo[dim] - a[dim]) / d[dim]
                t2 = (hi[dim] - a[dim]) / d[dim]
                tmin = max(tmin, min(t1, t2))
                tmax = min(tmax, max(t1, t2))
        if parallel_overlap and tmin <= tmax:
            return 0.0
        for endpoint in (a, b):
            dx = max(max(lo[0] - endpoint[0], endpoint[0] - hi[0]), 0.0)
            dy = max(max(lo[1] - endpoint[1], endpoint[1] - hi[1]), 0.0)
            best = min(best, math.hypot(dx, dy))
        corners = (lo, np.array([lo[0], hi[1]]), hi, np.array([hi[0], lo[1]]))
        edges = ((corners[0], corners[1]), (corners[1], corners[2]),
                 (corners[2], corners[3]), (corners[3], corners[0]))
        for corner in corners:
            best = min(best, segment_segment_distance(a, b, corner, corner))
        for start, end in edges:
            best = min(best, segment_segment_distance(a, b, start, end))
    return best

def independent_route_metrics(world, path, weights):
    values = np.zeros(5)
    duration = 0.0
    clearance_total = 0.0
    row_distance = 0.0
    turn_total = 0.0
    minimum_clearance = math.inf
    previous = xy(world, path[0])
    for a, b in zip(path[:-1], path[1:]):
        pa, pb = xy(world, a), xy(world, b)
        horizontal = float(np.linalg.norm(pb - pa))
        rise = float(world['z'][b[0], b[1]] - world['z'][a[0], a[1]])
        distance = math.hypot(horizontal, rise)
        slope = math.atan2(rise, horizontal)
        heading_change = min((int(b[2]) - int(a[2])) % 8,
                             (int(a[2]) - int(b[2])) % 8) * math.pi / 4.0
        duration += distance / PARAM['speed_m_s']
        traction = max(0.0, PARAM['mass_kg'] * PARAM['g_m_s2'] *
                       (PARAM['rolling_coefficient'] * math.cos(slope) * distance + rise))
        energy = (PARAM['auxiliary_power_W'] * distance / PARAM['speed_m_s'] +
                  traction / PARAM['drive_efficiency'] +
                  PARAM['turn_loss_J_rad'] * heading_change)
        soil = 0.5 * (world['soil'][a[0], a[1]] + world['soil'][b[0], b[1]]) * horizontal
        inrow = bool(world['inrow'][a[0], a[1]] and world['inrow'][b[0], b[1]])
        row = 0.5 * (world['row'][a[0], a[1]] + world['row'][b[0], b[1]]) * horizontal * inrow
        values += np.array([distance, energy, 0.0, soil, row])
        row_distance += horizontal * inrow
        turn_total += heading_change
        # Independent conservative swept-clearance estimate by dense sampling.
        segment_length = float(np.linalg.norm(pb - pa))
        samples = max(2, int(math.ceil(segment_length / SAMPLE_STEP_M)) + 1)
        margin = segment_rectangle_distance_independent(pa, pb, world) - PARAM['footprint_radius_m']
        minimum_clearance = min(minimum_clearance, margin)
        clearance_total += math.exp(-max(0.0, margin) / PARAM['clearance_decay_m']) * segment_length
        previous = pb
    values[2] = clearance_total
    scalar = float(weights @ (values / SCALES))
    return {'distance_m': float(values[0]),
            'energy_Wh': float(values[1] / 3600.0),
            'mission_time_s': float(duration),
            'row_integral_m2': float(values[4]),
            'mean_row_error_m': float(values[4] / row_distance) if row_distance else None,
            'minimum_swept_body_clearance_m': (float(minimum_clearance)
                                                if math.isfinite(minimum_clearance) else None),
            'scalarized_cost': scalar}

def main():
    records = []
    for name in FILES:
        records.extend(load_jsonl(name))
    successful = [r for r in records if r['success'] == 1]
    print(f'Regenerating and independently verifying {len(successful)} successful routes...')
    passed = 0
    failures = []
    max_cost_difference = 0.0
    for number, record in enumerate(successful, 1):
        family = int(record['family'][1:])
        world = make_world(family, record['case'], record['split'])
        regenerated, path = run_mission(world, METHODS[record['method']])
        if regenerated['status'] != 'success' or len(path) != record['route_state_count']:
            failures.append({'key': record['key'], 'reason': 'route_regeneration_mismatch',
                             'stored_states': record['route_state_count'],
                             'regenerated_states': len(path)})
            continue
        independent = independent_route_metrics(world, path, np.array(METHODS[record['method']]))
        stored = {'distance_m': record['distance_m'],
                  'energy_Wh': record['energy_Wh'],
                  'mission_time_s': record['mission_time_s'],
                  'row_integral_m2': record['row_integral_m2'],
                  'mean_row_error_m': record['mean_row_error_m'],
                  'minimum_swept_body_clearance_m': record['minimum_swept_body_clearance_m'],
                  'scalarized_cost': record['scalarized_cost']}
        mismatches = {}
        for key, stored_value in stored.items():
            independent_value = independent[key]
            if stored_value is None or independent_value is None:
                if stored_value != independent_value:
                    mismatches[key] = {'stored': stored_value, 'independent': independent_value}
                continue
            difference = abs(float(stored_value) - float(independent_value))
            if key == 'scalarized_cost':
                max_cost_difference = max(max_cost_difference, difference)
            if difference > TOL[key]:
                mismatches[key] = {'stored': stored_value, 'independent': independent_value,
                                   'absolute_difference': difference}
        if mismatches:
            failures.append({'key': record['key'], 'reason': 'metric_mismatch',
                             'mismatches': mismatches})
        else:
            passed += 1
        if number % 100 == 0:
            print(f'Verified {number}/{len(successful)}')
    report = {'revision': REVISION, 'analysis_plan_sha256':
              json.loads(Path('analysis_plan_checksum_v6.json').read_text(encoding='utf-8'))['sha256'],
              'successful_routes_checked': len(successful), 'routes_passed': passed,
              'routes_failed': len(failures), 'max_absolute_scalarized_cost_difference':
              max_cost_difference, 'sampling_step_m': SAMPLE_STEP_M, 'tolerances': TOL,
              'failures': failures,
              'limitations': ['Routes were regenerated with the frozen planner because route states were not stored in v6 records.',
                             'Clearance uses independent dense sampling and is approximate; its tolerance is therefore larger.',
                             'This verifies the declared simulation model, not physical-field behavior.']}
    Path('independent_verification_v6.json').write_text(
        json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'failures'}, indent=2))
    if failures:
        print('INDEPENDENT VERIFICATION FAILED')
        raise SystemExit(1)
    print('INDEPENDENT VERIFICATION PASSED')

if __name__ == '__main__':
    main()