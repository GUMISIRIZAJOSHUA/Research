"""Development-stage generator and diversity audit; does not run route searches."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt

GENERATOR_REVISION = 'diversity-v3-development'
SETTINGS = {
    'grid_cells': 40, 'resolution_m': 0.5, 'footprint_radius_m': 0.35,
    'headland_depth_choices_m': [3.0, 3.25, 3.5, 3.75, 4.0, 4.25, 4.5],
    'nominal_centerlines_m': [4.0, 9.0, 14.0],
    'centerline_offset_uniform_range_m': [-0.75, 0.75],
    'corridor_half_width_choices_m': [1.25, 1.375, 1.5, 1.625, 1.75],
    'bend_amplitude_range_m': [0.35, 0.85],
    'bend_wavelength_range_m': [12.0, 20.0],
    'terrain_amplitude_range_m': [0.25, 0.65],
    'soil_peak_amplitude': 0.8,
    'clearance_convention': 'conservative occupied-cell circumdisk lower bound at cell centers',
    'row_distance_convention': 'Euclidean distance to sampled centerline polylines',
    'provenance': 'synthetic design settings; not physically calibrated',
}

def _polyline_distance(X, Y, xs, ys):
    points=np.column_stack((X.ravel(),Y.ravel()))
    best=np.full(len(points),np.inf)
    for i in range(len(xs)-1):
        a=np.array([xs[i],ys[i]])
        v=np.array([xs[i+1]-xs[i],ys[i+1]-ys[i]])
        t=np.clip(((points-a)@v)/np.dot(v,v),0.0,1.0)
        best=np.minimum(best,np.linalg.norm(points-a-t[:,None]*v,axis=1))
    return best.reshape(X.shape)

def make_world(family, seed, split='evaluation'):
    if family not in range(1,7) or split not in ('pilot','evaluation') or seed<0:
        raise ValueError('Invalid family, seed, or split')
    split_key={'pilot':173,'evaluation':947}[split]
    rng=np.random.default_rng(np.random.SeedSequence([2026,int(family),int(seed),split_key]))
    n=SETTINGS['grid_cells']; r=SETTINGS['resolution_m']
    y,x=np.mgrid[:n,:n]; X=(x+0.5)*r; Y=(y+0.5)*r
    xs=(np.arange(n)+0.5)*r; length=n*r
    head_depth=float(rng.choice(SETTINGS['headland_depth_choices_m']))
    centers=np.asarray(SETTINGS['nominal_centerlines_m'])+rng.uniform(*SETTINGS['centerline_offset_uniform_range_m'],size=3)
    width=float(rng.choice(SETTINGS['corridor_half_width_choices_m']))
    amplitude=float(rng.uniform(*SETTINGS['bend_amplitude_range_m'])) if family in (3,6) else 0.0
    wavelength=float(rng.uniform(*SETTINGS['bend_wavelength_range_m']))
    phase=float(rng.uniform(0,2*np.pi))
    bend=amplitude*np.sin(2*np.pi*xs/wavelength+phase)
    row=np.min(np.stack([_polyline_distance(X,Y,xs,c+bend) for c in centers]),axis=0)
    head=(X<head_depth)|(X>length-head_depth)
    crop=(row>width)&(~head)
    boundary=np.zeros((n,n),dtype=bool)
    boundary[[0,-1],:]=True;boundary[:,[0,-1]]=True
    start_col=3
    left_col=int(head_depth/r)+2
    right_col=n-int(head_depth/r)-3
    target_cols=[right_col,left_col,right_col]
    targets=[]
    for lane,col in enumerate(target_cols):
        rr=int(np.argmin(np.abs((np.arange(n)+0.5)*r-(centers[lane]+bend[col]))))
        targets.append((rr,col))
    start_row=int(np.argmin(np.abs((np.arange(n)+0.5)*r-(centers[0]+bend[start_col]))))
    start=(start_row,start_col,0)
    endpoint_xy=np.array([(X[a,b],Y[a,b]) for a,b in [start[:2]]+targets])
    obstacles=np.zeros((n,n),dtype=bool);obstacle_records=[]
    if family in (2,6):
        for _ in range(3):
            cx=float(rng.uniform(5.5,14.0));lane=int(rng.integers(0,3))
            cb=amplitude*np.sin(2*np.pi*cx/wavelength+phase)
            cy=float(centers[lane]+cb+rng.choice([-1.0,1.0])*rng.uniform(0.65,1.0))
            radius=float(rng.uniform(0.3,0.55))
            candidate=(X-cx)**2+(Y-cy)**2<radius**2
            # Preserve endpoint neighborhoods, without testing planner success.
            near=np.min((X[...,None]-endpoint_xy[:,0])**2+(Y[...,None]-endpoint_xy[:,1])**2,axis=2)<1.0**2
            candidate &= ~near
            obstacles |= candidate
            obstacle_records.append({'center_m':[cx,cy],'radius_m':radius,'endpoint_mask_m':1.0})
    raw=crop|obstacles|boundary
    center_clearance=distance_transform_edt(~raw)*r
    lower=np.maximum(0.0,center_clearance-r/np.sqrt(2))
    free=(~raw)&(lower>=SETTINGS['footprint_radius_m'])
    z=np.zeros((n,n));soil=np.zeros_like(z);terrain_records=[];soil_records=[]
    if family in (4,6):
        for _ in range(2):
            cx,cy=rng.uniform(5,14,2);amp=float(rng.uniform(*SETTINGS['terrain_amplitude_range_m']))
            z+=amp*np.exp(-((X-cx)**2+(Y-cy)**2)/12.0)
            terrain_records.append({'center_m':[float(cx),float(cy)],'amplitude_m':amp,'denominator_m2':12.0})
    if family in (5,6):
        for _ in range(4):
            cx,cy=rng.uniform(4,15,2)
            soil+=0.8*np.exp(-((X-cx)**2+(Y-cy)**2)/7.0)
            soil_records.append({'center_m':[float(cx),float(cy)],'amplitude':0.8,'denominator_m2':7.0})
        soil=np.clip(soil,0,1)
    if not free[start[:2]] or any(not free[g] for g in targets):
        raise RuntimeError(f'Endpoint validation failed: family={family}, seed={seed}, split={split}')
    return dict(family=int(family),seed=int(seed),split=split,raw=raw,free=free,
        clearance=center_clearance,boundary_clearance_lower_bound=lower,
        crop=crop,obstacles=obstacles,boundary=boundary,z=z,soil=soil,
        row=row,inrow=~head,headland=head,start=start,goals=targets,res=r,
        centerlines=np.stack([np.column_stack((xs,c+bend)) for c in centers]),
        generator_parameters=dict(headland_depth_m=head_depth,centerlines_m=centers.tolist(),
            corridor_half_width_m=width,bend_amplitude_m=amplitude,
            bend_wavelength_m=wavelength,bend_phase_rad=phase,
            obstacles=obstacle_records,terrain=terrain_records,soil=soil_records))

def signatures(w):
    def hashed(keys):
        h=hashlib.sha256()
        for key in keys:
            arr=np.ascontiguousarray(w[key]);h.update(key.encode());h.update(str(arr.shape).encode());h.update(arr.dtype.str.encode());h.update(arr.tobytes())
        return h.hexdigest()
    geometry=hashed(('raw','free'))
    layers=hashed(('raw','free','z','soil','row','inrow'))
    mission=json.dumps({'start':w['start'],'goals':w['goals']},sort_keys=True)
    case=hashlib.sha256((layers+mission).encode()).hexdigest()
    return geometry,layers,case

def audit(cases=16):
    records=[]
    print('Split       Family  Cases  Occupancy_geometry  Map_layers  Map_missions')
    all_sets={}
    for split in ('pilot','evaluation'):
        all_sets[split]=set()
        for family in range(1,7):
            sig=[signatures(make_world(family,seed,split)) for seed in range(cases)]
            counts=[len({s[i] for s in sig}) for i in range(3)]
            record=dict(split=split,family=family,cases=cases,unique_occupancy_geometry=counts[0],unique_map_layers=counts[1],unique_map_missions=counts[2])
            records.append(record);all_sets[split].update(s[2] for s in sig)
            print(f'{split:11s} F{family}      {cases:3d}       {counts[0]:3d}               {counts[1]:3d}         {counts[2]:3d}')
            if counts[2]!=cases:
                raise RuntimeError('Duplicate map-mission cases detected; do not proceed to final evaluation')
    overlap=len(all_sets['pilot']&all_sets['evaluation'])
    if overlap:
        raise RuntimeError('Pilot/evaluation case overlap detected')
    print('Exact pilot/evaluation map-mission overlap:',overlap)
    print('GENERATOR AUDIT PASSED. No route searches or experiment results were produced.')
    return dict(generator_revision=GENERATOR_REVISION,settings=SETTINGS,case_counts=records,exact_split_overlap=overlap,
        limitations=['Exact uniqueness is not proof of broad geometric diversity or statistical precision.',
                    'This audits generation and endpoint admissibility only.',
                    'The original planner, verifier, analysis, and plotting still require revision.',
                    'Do not substitute center-clearance for exact swept-body clearance.'])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=int,default=16)
    parser.add_argument('--report',default='generator_diversity_audit.json')
    args=parser.parse_args()
    if args.cases<2:parser.error('--cases must be at least 2')
    report=audit(args.cases)
    path=Path(args.report)
    if path.exists():raise FileExistsError('Report already exists; use a new --report filename')
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Audit report saved:',path)
