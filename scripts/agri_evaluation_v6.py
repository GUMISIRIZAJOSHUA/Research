"""Development evaluation runner v6; 96 evaluation cases x 5 methods = 480 missions.
Requires agri_generator_v3.py and agri_planner_v4.py beside this file.
Generator signature: make_world(family, case, split).
Resume-safe: completed mission records are skipped.
"""
import argparse
import json
import platform
import time
from pathlib import Path
from agri_planner_v4 import METHODS,REVISION,run_mission
from agri_generator_v3 import make_world

FAMILIES=6;CASES=16;METHOD_ORDER=['distance','energy','soil','distance_clearance','full']
def mission_key(family,case,method):return f'evaluation|F{family}|{case:02d}|{method}'
def load_done(path):
    done=set()
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line)
            except ValueError:continue
            if r.get('record_status')=='complete' and r.get('key'):done.add(r['key'])
    return done
def summarize(records):
    by={};family={};method={}
    for r in records:
        for scope,key in ((by,r['key']),(family,r['family']),(method,r['method'])):
            s=scope.setdefault(key,dict(n=0,success=0,geometric_completion=0,resource_energy_exceeded=0,
                resource_time_exceeded=0,verification_failure=0,search_ms=0.,planning_ms=0.,
                verification_ms=0.,expanded_states=0,accepted_transitions=0))
            s['n']+=1;s['success']+=r['success'];s['geometric_completion']+=r['geometric_completion']
            s['resource_energy_exceeded']+=r['resource_energy_exceeded'];s['resource_time_exceeded']+=r['resource_time_exceeded']
            s['verification_failure']+=int(r['status']=='verification_failure')
            for k in ('search_ms','planning_ms','verification_ms','expanded_states','accepted_transitions'):s[k]+=r[k]
    for scope in (by,family,method):
        for s in scope.values():
            n=s['n'];s['success_rate']=s['success']/n;s['geometric_completion_rate']=s['geometric_completion']/n
            for k in ('search_ms','planning_ms','verification_ms'):s[k+'_mean']=s[k]/n
    return dict(by_mission=by,by_family=family,by_method=method)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',default='evaluation_records_v6.jsonl')
    p.add_argument('--summary',default='evaluation_summary_v6.json')
    p.add_argument('--limit-missions',type=int,default=0,help='Optional smoke limit; 0 means all 480')
    args=p.parse_args()
    records_path=Path(args.records);summary_path=Path(args.summary)
    if records_path.exists() and summary_path.exists() and records_path.stat().st_mtime>summary_path.stat().st_mtime:
        raise RuntimeError('Records are newer than summary; rerun without deleting records')
    done=load_done(records_path);total=FAMILIES*CASES*len(METHOD_ORDER)
    expected=min(total,args.limit_missions) if args.limit_missions else total
    print(f'Evaluation revision: {REVISION}; expected missions this invocation: {expected}; already complete: {len(done)}')
    if len(done)>=total and not args.limit_missions:
        print('All evaluation missions already complete; no searches will be rerun.')
    started=time.perf_counter();completed_now=0
    mode='a' if records_path.exists() else 'x'
    with records_path.open(mode,encoding='utf-8') as out:
        for family in range(1,FAMILIES+1):
            for case in range(1,CASES+1):
                w=make_world(family,case,'evaluation')
                for name in METHOD_ORDER:
                    key=mission_key(family,case,name)
                    if key in done:continue
                    if args.limit_missions and completed_now>=args.limit_missions:break
                    record,path=run_mission(w,METHODS[name])
                    row=dict(key=key,record_status='complete',revision=REVISION,split='evaluation',
                        family=f'F{family}',case=case,method=name,python=platform.python_version(),
                        platform=platform.platform(),route_state_count=int(len(path)),
                        recorded_at=time.time(),**record)
                    out.write(json.dumps(row,separators=(',',':'))+'\n');out.flush()
                    completed_now+=1
                    print(f"{key}: {record['status']} search={record['search_ms']:.1f} ms "
                          f"states={len(path)} energy={record.get('energy_Wh')} Wh")
                if args.limit_missions and completed_now>=args.limit_missions:break
            if args.limit_missions and completed_now>=args.limit_missions:break
    all_rows=[]
    if records_path.exists():
        for line in records_path.read_text(encoding='utf-8').splitlines():
            try:r=json.loads(line)
            except ValueError:continue
            if r.get('record_status')=='complete':all_rows.append(r)
    summary=summarize(all_rows);summary.update(revision=REVISION,expected_total_missions=total,
        completed_missions=len(all_rows),missing_missions=total-len(all_rows),
        elapsed_seconds_this_invocation=time.perf_counter()-started,
        limitations=['Development evaluation only; no statistical inference or publication claims.',
            'Verification shares documented primitives with the planner.',
            'No physical calibration or continuous-motion validation.',
            'Resource screening occurs after full selected-route assembly and verification.',
            'Pilot F6 case 11 was a documented no_path case; evaluation outcomes are recorded independently.'])
    summary_path.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(f"Completed this invocation: {completed_now}; total complete: {len(all_rows)}/{total}")
    print(f"Records: {records_path}\nSummary: {summary_path}")
    if len(all_rows)==total:
        print('EVALUATION COMPLETE. Development slot total: 960/960 including the completed pilot.')
if __name__=='__main__':main()
