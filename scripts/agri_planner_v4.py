"""Development planner verification; no full benchmark or publication claims.
Requires agri_generator_v3.py beside this file for --smoke.
"""
import argparse
import hashlib
import heapq
import json
import platform
import time
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

REVISION='planner-v4-development'
DIRS=np.array([(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),(-1,1)],dtype=int)
NAMES=['distance','energy','clearance','soil','row']
METHODS={'distance':[1,0,0,0,0],'energy':[0,1,0,0,0],'soil':[0,0,0,1,0],
         'distance_clearance':[.5,0,.5,0,0],'full':[.2]*5}
SCALES=np.array([1.,60.,1.,1.,1.])
PARAM=dict(resolution_m=.5,footprint_radius_m=.35,speed_m_s=.5,mass_kg=35.,g_m_s2=9.81,
    rolling_coefficient=.04,drive_efficiency=.65,auxiliary_power_W=12.,turn_loss_J_rad=3.,
    max_heading_change_rad=np.pi/4,max_slope_rad=np.deg2rad(15),clearance_decay_m=.5,
    budget_Wh=20.,time_limit_s=1200.,expansion_limit_per_segment=20000,
    cost_update_tolerance=1e-12,verification_atol=1e-8)


def weights_checked(weights):
    w=np.asarray(weights,dtype=float)
    if w.shape!=(5,) or not np.isfinite(w).all() or (w<0).any() or w.sum()<=0:
        raise ValueError('Weights must be five finite nonnegative numbers with positive sum')
    return w/w.sum()


def xy(w,p):
    return (np.array([p[1],p[0]],dtype=float)+.5)*w['res']


def wrapped_change(a,b):
    return min((int(b)-int(a))%8,(int(a)-int(b))%8)*np.pi/4


def prepare(w):
    if '_prepared' in w:return
    iy,ix=np.nonzero(w['raw'])
    centers=np.column_stack(((ix+.5)*w['res'],(iy+.5)*w['res']))
    w['_obstacle_tree']=cKDTree(centers) if len(centers) else None
    w['_obstacle_centers']=centers
    w['_edge_clearances']={}
    w['_prepared']=True


def segment_rectangle_distance(a,b,centers,half):
    # Exact Euclidean distance to the union of closed axis-aligned cell rectangles.
    if not len(centers):return np.inf
    lo=centers-half;hi=centers+half;v=b-a
    near=np.zeros(len(centers));far=np.ones(len(centers));possible=np.ones(len(centers),bool)
    for dim in range(2):
        if abs(v[dim])<1e-15:
            possible&=(a[dim]>=lo[:,dim])&(a[dim]<=hi[:,dim])
        else:
            t1=(lo[:,dim]-a[dim])/v[dim];t2=(hi[:,dim]-a[dim])/v[dim]
            near=np.maximum(near,np.minimum(t1,t2));far=np.minimum(far,np.maximum(t1,t2))
    if np.any(possible&(near<=far)):return 0.
    da=np.maximum(np.maximum(lo-a,a-hi),0.)
    db=np.maximum(np.maximum(lo-b,b-hi),0.)
    best=min(float(np.linalg.norm(da,axis=1).min()),float(np.linalg.norm(db,axis=1).min()))
    corners=np.stack((lo,np.column_stack((lo[:,0],hi[:,1])),hi,np.column_stack((hi[:,0],lo[:,1]))),axis=1)
    vv=float(v@v)
    if vv>0:
        t=np.clip(np.sum((corners-a)*v,axis=2)/vv,0.,1.)
        dc=np.linalg.norm(corners-a-t[...,None]*v,axis=2).min()
        best=min(best,float(dc))
    return best


def edge_margin(w,p,q):
    prepare(w)
    key=tuple(sorted((tuple(p[:2]),tuple(q[:2]))))
    if key not in w['_edge_clearances']:
        a=xy(w,p);b=xy(w,q);tree=w['_obstacle_tree']
        if tree is None:distance=np.inf
        else:
            mid=(a+b)/2
            d0=float(tree.query(mid)[0])
            radius=d0+np.linalg.norm(b-a)/2+w['res']/np.sqrt(2)+1e-10
            ids=tree.query_ball_point(mid,radius)
            distance=segment_rectangle_distance(a,b,w['_obstacle_centers'][ids],w['res']/2)
        w['_edge_clearances'][key]=distance
    return w['_edge_clearances'][key]-PARAM['footprint_radius_m']


def contained(w,p):
    a=xy(w,p);ny,nx=w['raw'].shape;r=PARAM['footprint_radius_m']
    return bool(r<=a[0]<=nx*w['res']-r and r<=a[1]<=ny*w['res']-r)


def valid_position(w,p):
    y,x=map(int,p[:2]);ny,nx=w['raw'].shape
    return bool(0<=y<ny and 0<=x<nx and w['free'][y,x] and contained(w,p))


def costs_for_geometry(w,a,b,multiplier):
    dsxy=float(np.linalg.norm(xy(w,b)-xy(w,a)))
    dz=float(w['z'][b[0],b[1]]-w['z'][a[0],a[1]])
    ds=float(np.hypot(dsxy,dz));slope=float(np.arctan2(dz,dsxy))
    angle=wrapped_change(a[2],b[2]);dt=ds/PARAM['speed_m_s']
    traction=max(0.,PARAM['mass_kg']*PARAM['g_m_s2']*(PARAM['rolling_coefficient']*multiplier*np.cos(slope)*ds+dz))
    energy=PARAM['auxiliary_power_W']*dt+traction/PARAM['drive_efficiency']+PARAM['turn_loss_J_rad']*angle
    margin=edge_margin(w,a,b)
    exposure=0. if np.isinf(margin) else np.exp(-max(0.,margin)/PARAM['clearance_decay_m'])*dsxy
    soil=.5*(w['soil'][a[0],a[1]]+w['soil'][b[0],b[1]])*dsxy
    # Declared endpoint mask approximation for boundary-crossing transitions.
    inrow=bool(w['inrow'][a[0],a[1]] and w['inrow'][b[0],b[1]])
    row=.5*(w['row'][a[0],a[1]]+w['row'][b[0],b[1]])*dsxy*inrow
    return np.array([ds,energy,exposure,soil,row]),dt,dsxy*inrow,angle,margin,slope


def transition(w,a,hnew,multiplier=1.):
    if not 0<=int(hnew)<8 or wrapped_change(a[2],hnew)>PARAM['max_heading_change_rad']+1e-12:
        return None
    dy,dx=DIRS[int(hnew)];b=(int(a[0]+dy),int(a[1]+dx),int(hnew))
    if not valid_position(w,a) or not valid_position(w,b):return None
    if dx and dy and (not w['free'][a[0],b[1]] or not w['free'][b[0],a[1]]):return None
    values,dt,rd,angle,margin,slope=costs_for_geometry(w,a,b,multiplier)
    if margin < -1e-10 or abs(slope)>PARAM['max_slope_rad']+1e-12:return None
    return b,values,dt,rd,angle,margin


def search(w,start,goal,weights,multiplier=1.,limit=None):
    weights=weights_checked(weights);start=tuple(map(int,start));goal=tuple(map(int,goal))
    prepare(w)
    stats=dict(expanded_states=0,queue_pops=0,stale_entries=0,generated_transitions=0,accepted_transitions=0)
    begin=time.perf_counter()
    def finish(status,path=None,cost=None):
        return dict(status=status,path=path,cost=cost,search_ms=(time.perf_counter()-begin)*1000,**stats)
    if not valid_position(w,start) or not valid_position(w,goal):return finish('invalid_endpoint')
    if not 0<=start[2]<8:return finish('invalid_endpoint')
    allowance=PARAM['expansion_limit_per_segment'] if limit is None else limit
    def heuristic(a):return weights[0]*np.linalg.norm(xy(w,a)-xy(w,goal))/SCALES[0]
    queue=[(heuristic(start),0.,0,start)];counter=0;best={start:0.};parent={}
    while queue:
        _,g,_,a=heapq.heappop(queue);stats['queue_pops']+=1
        if g>best[a]+PARAM['cost_update_tolerance']:
            stats['stale_entries']+=1;continue
        if a[:2]==goal:
            path=[a]
            while path[-1]!=start:path.append(parent[path[-1]])
            return finish('success',path[::-1],g)
        if stats['expanded_states']>=allowance:return finish('expansion_limit')
        stats['expanded_states']+=1
        for heading in ((a[2]-1)%8,a[2],(a[2]+1)%8):
            stats['generated_transitions']+=1
            tr=transition(w,a,heading,multiplier)
            if tr is None:continue
            stats['accepted_transitions']+=1
            b,values,*_=tr;candidate=g+float(weights@(values/SCALES))
            if candidate<best.get(b,np.inf)-PARAM['cost_update_tolerance']:
                best[b]=candidate;parent[b]=a;counter+=1
                heapq.heappush(queue,(candidate+heuristic(b),candidate,counter,b))
    return finish('no_path')


def verify_route(w,path,goals,weights,multiplier=1.,expected_cost=None):
    # Recompute from the state sequence, without calling transition or search.
    weights=weights_checked(weights)
    p=np.asarray(path,dtype=int)
    if p.ndim!=2 or p.shape[1]!=3 or len(p)==0:raise ValueError('Invalid route array')
    if tuple(p[0])!=tuple(w['start']):raise ValueError('Initial state mismatch')
    values=np.zeros(5);duration=0.;rd=0.;angle_sum=0.;margin_min=np.inf
    for state in p:
        if not valid_position(w,state) or not 0<=state[2]<8:raise ValueError('Invalid route state')
    for a,b in zip(p[:-1],p[1:]):
        dy,dx=b[:2]-a[:2]
        if not np.array_equal([dy,dx],DIRS[int(b[2])]):raise ValueError('Displacement/heading mismatch')
        angle=wrapped_change(a[2],b[2])
        if angle>PARAM['max_heading_change_rad']+1e-12:raise ValueError('Heading bound violated')
        if dx and dy and (not w['free'][a[0],b[1]] or not w['free'][b[0],a[1]]):raise ValueError('Corner violation')
        v,dt,inrow,ang,margin,slope=costs_for_geometry(w,a,b,multiplier)
        if margin < -1e-10:raise ValueError('Swept footprint intersects an exclusion')
        if abs(slope)>PARAM['max_slope_rad']+1e-12:raise ValueError('Slope violation')
        values+=v;duration+=dt;rd+=inrow;angle_sum+=ang;margin_min=min(margin_min,margin)
    next_goal=0
    for state in p:
        if next_goal<len(goals) and tuple(state[:2])==tuple(goals[next_goal]):next_goal+=1
    if next_goal!=len(goals):raise ValueError('Reached segment targets not present in prescribed order')
    scalar=float(weights@(values/SCALES))
    if expected_cost is not None and not np.isclose(scalar,expected_cost,rtol=1e-9,atol=PARAM['verification_atol']):
        raise ValueError('Search cost and route recomputation disagree')
    return dict(distance_m=float(values[0]),energy_Wh=float(values[1]/3600),
        clearance_exposure_m=float(values[2]),soil_exposure_m=float(values[3]),row_integral_m2=float(values[4]),
        mean_row_error_m=float(values[4]/rd) if rd else None,inrow_distance_m=float(rd),
        minimum_swept_body_clearance_m=float(margin_min) if np.isfinite(margin_min) else None,
        turn_angle_rad=float(angle_sum),mission_time_s=float(duration),scalarized_cost=scalar)


def run_mission(w,weights,multiplier=1.):
    if not np.isfinite(multiplier) or multiplier<=0:raise ValueError('Invalid resistance multiplier')
    weights=weights_checked(weights)
    prep=time.perf_counter();prepare(w);preprocessing_ms=(time.perf_counter()-prep)*1000
    begin=time.perf_counter();path=[tuple(w['start'])];completed=0;cost=0.;status='success'
    counters=dict(expanded_states=0,queue_pops=0,stale_entries=0,generated_transitions=0,accepted_transitions=0)
    search_ms=0.;segments=[]
    for goal in w['goals']:
        result=search(w,path[-1],goal,weights,multiplier)
        search_ms+=result['search_ms']
        for key in counters:counters[key]+=result[key]
        segments.append(dict(target=list(goal),status=result['status'],search_ms=result['search_ms'],
            terminal_state=result['path'][-1] if result['path'] else None))
        if result['status']!='success':status=result['status'];break
        path.extend(result['path'][1:]);cost+=result['cost'];completed+=1
    planning_ms=(time.perf_counter()-begin)*1000
    verification_begin=time.perf_counter();error=None
    try:
        metrics=verify_route(w,path,w['goals'][:completed],weights,multiplier,expected_cost=cost)
    except ValueError as exc:
        status='verification_failure';error=str(exc);metrics={}
    verification_ms=(time.perf_counter()-verification_begin)*1000
    energy_fail=bool(metrics and metrics['energy_Wh']>PARAM['budget_Wh'])
    time_fail=bool(metrics and metrics['mission_time_s']>PARAM['time_limit_s'])
    # Resource screening is after full selected-route assembly and verification.
    if status=='success':
        if energy_fail:status='energy_budget'
        elif time_fail:status='nominal_time_budget'
    record=dict(success=int(status=='success'),status=status,completed_waypoints=completed,
        geometric_completion=bool(completed==len(w['goals']) and error is None),
        resource_energy_exceeded=energy_fail,resource_time_exceeded=time_fail,
        preprocessing_ms=preprocessing_ms,search_ms=search_ms,planning_ms=planning_ms,
        verification_ms=verification_ms,heuristic_regime='A_star' if weights[0]>0 else 'uniform_cost',
        weights=weights.tolist(),segments=segments,verification_error=error,**metrics,**counters)
    return record,np.asarray(path,dtype=int)


def _test_world(n=12):
    zeros=np.zeros((n,n));free=np.ones((n,n),bool)
    return dict(raw=np.zeros((n,n),bool),free=free,z=zeros.copy(),soil=zeros.copy(),
        row=zeros.copy(),inrow=free.copy(),res=.5,start=(5,3,0),goals=[(5,7)])


def verify():
    checks=[];w=_test_world();a=w['start']
    tr=transition(w,a,0)
    expected=.5*(PARAM['auxiliary_power_W']/PARAM['speed_m_s']+PARAM['mass_kg']*PARAM['g_m_s2']*PARAM['rolling_coefficient']/PARAM['drive_efficiency'])
    assert np.isclose(tr[1][0],.5) and np.isclose(tr[1][1],expected)
    checks+=['known axial length and flat-ground energy','joule/Wh conversion']
    diagonal=transition(w,a,1)
    assert np.isclose(diagonal[1][0],np.sqrt(.5))
    checks.append('known diagonal length')
    assert transition(w,a,2) is None
    checks.append('heading-bound rejection')
    w2=_test_world();w2['z'][5,4]=-.1
    downhill=transition(w2,a,0)
    assert downhill is not None and downhill[1][1]>=PARAM['auxiliary_power_W']*downhill[2]>0
    checks.append('positive downhill expenditure without regeneration')
    for inrow in (False,True):
        w3=_test_world();w3['row'][:]=.4;w3['inrow'][:]=inrow
        edge=transition(w3,a,0)
        assert np.isclose(edge[1][4],.2 if inrow else 0.)
        assert np.isclose(edge[3],.5 if inrow else 0.)
    checks.append('headland masking of integral and denominator')
    wc=_test_world();wc['raw'][5,4]=True;wc['free'][5,4]=False
    assert transition(wc,a,0) is None
    assert transition(wc,a,1) is None
    checks.append('obstacle and diagonal-corner rejection')
    assert np.isclose(segment_rectangle_distance(np.array([0.,0.]),np.array([1.,0.]),np.array([[.5,1.]]),.25),.75)
    assert segment_rectangle_distance(np.array([0.,0.]),np.array([1.,0.]),np.array([[.5,0.]]),.25)==0.
    checks.append('analytical swept-segment to occupied-rectangle distance')
    r,p=run_mission(_test_world(),[.2]*5)
    r2,p2=run_mission(_test_world(),[1.]*5)
    assert r['success']==1 and np.isclose(r['distance_m'],2.) and np.array_equal(p,p2)
    assert np.isclose(r['energy_Wh']*3600,expected*4)
    assert r['queue_pops']==r['stale_entries']+r['expanded_states']+1
    checks+=['known complete route','equivalent-weight and route reproducibility','queue accounting']
    rejected=p.copy();rejected[1,2]=4
    try:verify_route(_test_world(),rejected,[(5,7)],[.2]*5)
    except ValueError:pass
    else:raise AssertionError('Invalid route accepted')
    checks.append('verification rejects corrupted displacement/heading')
    limited=search(_test_world(),a,(5,7),[.2]*5,limit=0)
    assert limited['status']=='expansion_limit'
    checks.append('explicit expansion-limit outcome')
    old=PARAM['budget_Wh']
    try:
        PARAM['budget_Wh']=1e-12
        screened,screen_path=run_mission(_test_world(),[.2]*5)
        assert screened['status']=='energy_budget' and screened['geometric_completion']
        assert len(screen_path)==len(p) and tuple(screen_path[-1][:2])==(5,7)
    finally:PARAM['budget_Wh']=old
    checks.append('resource screening retains complete selected route')
    return dict(status='passed',revision=REVISION,checks=checks,
        limitations=['Verification shares the documented geometry and cost primitives; it is not a fully independent implementation.',
            'No physical calibration, continuous-motion validation, or statistical validation.',
            'Swept clearance concerns polygonal raster cells, not measured farmland.',
            'Grid admissibility also retains conservative generator node masking.',
            'Row/headland boundary transitions use a declared endpoint-mask approximation.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--verify-only',action='store_true')
    p.add_argument('--smoke',action='store_true',help='One pilot F1 mission using the v3 generator')
    args=p.parse_args()
    if not args.verify_only and not args.smoke:p.error('Use --verify-only or --smoke; full benchmark is not implemented in this module')
    result=verify();print(json.dumps(result,indent=2))
    if args.smoke:
        from agri_generator_v3 import make_world
        w=make_world(1,0,'pilot')
        record,path=run_mission(w,METHODS['full'])
        print('GENERATOR INTEGRATION SMOKE CHECK:')
        print(json.dumps(record,indent=2))
        print('Route states:',len(path))
        if not record['success']:raise RuntimeError('Pilot smoke mission did not complete; inspect outcome before proceeding')

if __name__=='__main__':main()
