"""Frozen retrospective evaluation; protected labels are used only after prediction.

Scientific outputs, not backend review artifacts. See EXPERIMENT_PROTOCOL_V2.md.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, HuberRegressor
from .dataset import (FILES, LABEL_DESCRIPTIONS, UNITS, download_file, verify_file,
    audit_csv, load_electrical, load_weather_bins, merge_electrical,
    exact_alignment_report, as_json_file)
from .model import (_score, _parameters, _predict, _day_block_bootstrap,
    find_fault_episodes, make_bins)

VERSION='0.2.0-research'
SEED=20261010
FEATURES=['reference_power_w','GTI','DTI','TA']
ELECTRICAL=['Va','Ia','Vg','Ig','Fg']


def support_seconds(times, max_gap=18.):
    dt=np.diff(pd.Series(times).astype('int64').to_numpy()/1e9)
    return float(dt[(dt>0)&(dt<=max_gap)].sum())


def aggregate(paired, minutes=5):
    """Fixed, nonoverlapping windows; elapsed support is conservative at edges."""
    f=paired.copy()
    f['bin_start']=f.timestamp.dt.floor(f'{minutes}min')
    f['known']=f.fault_label.isin(LABEL_DESCRIPTIONS)
    f['healthy_row']=f.fault_label.eq(0)&f.known
    agg={c:(c,'mean') for c in ['target_power_w','reference_power_w',*FEATURES[1:],
        'TPV',*[f'{s}_{suffix}' for s in ELECTRICAL for suffix in ['x','y']]] if c in f}
    agg.update(row_count=('timestamp','size'),support_s=('timestamp',support_seconds),
        healthy=('healthy_row','all'),known=('known','all'),fault_fraction=('fault_label',lambda x: float(x.gt(0).mean())))
    if 'residual_w' in f:
        agg.update(residual_w=('residual_w','mean'),expected_power_w=('expected_power_w','mean'),
            eligible=('eligible','all'))
    for c in ['weather_coverage','GTI_coverage','DTI_coverage','TA_coverage']:
        if c in f: agg[c]=(c,'min')
    b=f.groupby('bin_start',sort=True).agg(**agg).reset_index()
    b['local_day']=b.bin_start.dt.tz_convert('Indian/Reunion').dt.date.astype(str)
    b['quality']=b.support_s.ge(minutes*60*.8)&b.reference_power_w.ge(100)&b.target_power_w.ge(0)&b[['target_power_w','reference_power_w']].apply(np.isfinite).all(axis=1)
    return b


def weather_valid(b):
    if not set(FEATURES).issubset(b): return pd.Series(False,index=b.index)
    ok=b[FEATURES].apply(np.isfinite).all(axis=1)
    for c in ['weather_coverage','GTI_coverage','DTI_coverage','TA_coverage']:
        ok &= b[c].ge(.8)
    return ok


def fit_models(train, selection):
    models={n:{'name':n,'features':['reference_power_w'],'fixed_capacity_ratio':ratio} for n,ratio in
        [('capacity_table_arithmetic',2.10/2.04),('capacity_paper_prose',2.04/2.09)]}
    for n,est in [('calibrated_linear',LinearRegression()),('huber_reference',HuberRegressor(epsilon=1.35,alpha=.0001,max_iter=500))]:
        if n=='huber_reference' and len(train)<500: continue
        est.fit(train[['reference_power_w']].to_numpy(float),train.target_power_w.to_numpy(float))
        models[n]={'name':n,'features':['reference_power_w'],'estimator':est,'training_rows':len(train),'preprocessing':'Frozen pre-event five-minute means; no imputation/scaling.'}
    wt=train.loc[weather_valid(train)]
    if len(wt)>=500 and weather_valid(selection).mean()>=.90:
        est=LinearRegression().fit(wt[FEATURES].to_numpy(float),wt.target_power_w.to_numpy(float))
        models['weather_assisted_linear']={'name':'weather_assisted_linear','features':FEATURES,'estimator':est,'training_rows':len(wt),'preprocessing':'Field-specific weather coverage >=80%; no imputation; pre-event only.'}
    chosen='capacity_table_arithmetic'; comparisons={}; scores={}
    for n,m in models.items():
        v=selection.loc[weather_valid(selection)] if len(m['features'])>1 else selection
        scores[n]=_score(v.target_power_w,_predict(m,v))
    for n in ['calibrated_linear','huber_reference','weather_assisted_linear']:
        if n not in models: continue
        v=selection.loc[weather_valid(selection)] if len(models[n]['features'])>1 else selection
        base=_score(v.target_power_w,_predict(models[chosen],v))['mae_w']
        candidate=_score(v.target_power_w,_predict(models[n],v))['mae_w']
        improvement=1-candidate/base if base else 0
        comparisons[n]={'against':chosen,'common_bins':len(v),'improvement':improvement,'passed':improvement>=.05}
        if improvement>=.05: chosen=n
    return models,chosen,{'selection_scores':scores,'comparisons':comparisons,'parameters':{n:_parameters(m) for n,m in models.items()},'selected_model':chosen}


def predict_stream(paired, model, domain):
    """Label-free detector inputs. Never read fault_label in this function."""
    f=paired.copy()
    ok=f[model['features']].apply(np.isfinite).all(axis=1)&f.target_power_w.ge(0)&f.reference_power_w.ge(100)
    ok &= f.reference_power_w.between(*domain)
    if len(model['features'])>1: ok &= weather_valid(f)
    f['expected_power_w']=np.nan
    if ok.any(): f.loc[ok,'expected_power_w']=_predict(model,f.loc[ok])
    f['eligible']=ok&f.expected_power_w.ge(0)&np.isfinite(f.expected_power_w)
    f['residual_w']=f.expected_power_w-f.target_power_w
    return f


def alarms(windows, threshold, minutes=5):
    """Two consecutive eligible windows. Missing windows reset persistence."""
    w=windows.copy()
    w['usable']=w.quality&w.eligible&w.residual_w.notna()
    above=w.usable&w.residual_w.gt(threshold)
    contiguous=w.bin_start.diff().dt.total_seconds().eq(minutes*60)
    w['alert']=above&above.shift(1,fill_value=False)&contiguous
    w['confirmation']=w.bin_start+pd.Timedelta(minutes=minutes)
    w['alarm_start']=w.alert&~(w.alert.shift(1,fill_value=False)&contiguous)
    # All supporting windows must be known healthy to count a healthy alarm.
    w['support_healthy']=w.healthy&w.healthy.shift(1,fill_value=False)&contiguous
    return w


def integrate(rows, require_fault=False):
    """Do not filter rows before integration: adjacency and gaps remain explicit."""
    if len(rows)<2: return {'available':False,'valid_seconds':0.,'signed_energy_kwh':None,'positive_only_kwh':None,'actual_energy_kwh':None,'expected_energy_kwh':None,'interval_count':0}
    t=rows.timestamp.astype('int64').to_numpy()/1e9; dt=np.diff(t)
    ok=rows.eligible.to_numpy(bool)
    mask=ok[:-1]&ok[1:]&(dt>0)&(dt<=18)
    if 'source_row' in rows: mask &= np.diff(rows.source_row.to_numpy())==1
    if require_fault:
        labels=rows.fault_label.to_numpy(); mask &= (labels[:-1]>0)&(labels[1:]>0)
    seconds=float(dt[mask].sum())
    out={'available':seconds>0,'valid_seconds':seconds,'interval_count':int(mask.sum())}
    for key,col,pos in [('signed_energy_kwh','residual_w',False),('positive_only_kwh','residual_w',True),('actual_energy_kwh','target_power_w',False),('expected_energy_kwh','expected_power_w',False)]:
        values=rows[col].to_numpy(float)
        if pos: values=np.maximum(values,0)
        out[key]=float((.5*(values[:-1]+values[1:])*dt)[mask].sum()/3.6e6) if seconds else None
    return out


def healthy_metrics(w, start_day, end_day=None):
    s=w.loc[w.local_day.ge(start_day)&(w.local_day.le(end_day) if end_day else True)]
    h=s.loc[s.usable&s.healthy]
    hours=float(h.support_s.sum()/3600)
    fp=int((h.alert&h.support_healthy).sum()); tn=int((~h.alert).sum())
    runs=int((s.alarm_start&s.support_healthy&s.healthy).sum())
    daily=h.assign(fp=(h.alert&h.support_healthy).astype(int),runs=(h.alarm_start&h.support_healthy).astype(int)).groupby('local_day').agg(seconds=('support_s','sum'),runs=('runs','sum'),fp=('fp','sum'),n=('usable','size'))
    ci=None
    if len(daily)>=2:
        v=daily[['seconds','runs']].to_numpy(float); rng=np.random.default_rng(SEED)
        sums=v[rng.integers(len(v),size=(2000,len(v)))].sum(axis=1)
        ci=np.quantile(sums[:,1]/(sums[:,0]/3600),[.025,.975]).tolist()
    return {'evaluated_healthy_windows':len(h),'evaluated_healthy_hours':hours,'healthy_alert_runs':runs,
        'false_alarm_runs_per_healthy_hour':runs/hours if hours else None,'false_alarm_rate_day_bootstrap_95pct':ci,
        'healthy_FP_windows':fp,'healthy_TN_windows':tn,'ambiguous_boundary_alert_windows':int((h.alert&~h.support_healthy).sum()),
        'alert_window_fraction':fp/len(h) if len(h) else None,'healthy_days':len(daily)}


def event_detection(episode,w):
    overlap=w.bin_start.lt(episode['end'])&w.confirmation.gt(episode['start'])
    # Confirmation must occur during labelled event span; no backdating or grace period.
    hit=w.alert&overlap&w.confirmation.between(episode['start'],episode['end'])
    selected=w.loc[overlap]
    evaluated=int(selected.usable.sum())
    first=w.loc[hit,'confirmation'].min() if hit.any() else None
    return {'detected':bool(hit.any()),'confirmation_utc':first,
        'latency_seconds':float((first-episode['start']).total_seconds()) if first is not None else None,
        'eligible_overlapping_windows':evaluated,'overlapping_windows':len(selected)}


def placebos(episode, stream, calibration, event_energy):
    """Match predictors only, then assess signed residual distributions by day."""
    n=max(1,int(np.ceil(event_energy['valid_seconds']/300)))
    ev=stream.loc[stream.timestamp.between(episode['start'],episode['end'])&stream.eligible]
    if ev.empty: return {'status':'unavailable','reason':'No eligible event samples.'}
    blocks=[]
    for day,g in calibration.groupby('local_day'):
        g=g.sort_values('bin_start')
        # Greedy nonoverlap among accepted candidates; alignment is predeclared UTC 5min.
        next_i=0
        for i in range(len(g)-n+1):
            if i<next_i: continue
            sub=g.iloc[i:i+n]
            if not (sub.usable&sub.healthy).all() or (len(sub)>1 and not sub.bin_start.diff().dropna().eq(pd.Timedelta(minutes=5)).all()): continue
            ref=float(sub.reference_power_w.mean()); evref=float(ev.reference_power_w.mean())
            if abs(ref-evref)>.2*evref: continue
            if 'GTI' in sub and ev.GTI.notna().all():
                evgti=float(ev.GTI.mean())
                if abs(float(sub.GTI.mean())-evgti)>.2*max(evgti,1): continue
            blocks.append({'day':day,'mean_signed_w':float(sub.residual_w.mean()),'windows':n})
            next_i=i+n
    p=pd.DataFrame(blocks)
    if len(p)<5 or (len(p) and p.day.nunique()<3):
        return {'status':'unavailable','reason':'Need >=5 predictor-matched nonoverlapping blocks on >=3 calibration days.','blocks':len(p),'days':int(p.day.nunique()) if len(p) else 0}
    day_values=p.groupby('day').mean_signed_w.mean().to_numpy()
    rng=np.random.default_rng(SEED); draws=day_values[rng.integers(len(day_values),size=(2000,len(day_values)))].mean(axis=1)
    duration=event_energy['valid_seconds']/3.6e6
    noise=np.quantile(p.mean_signed_w,[.025,.5,.975])*duration
    signed=event_energy['signed_energy_kwh']
    return {'status':'available','blocks':len(p),'days':int(p.day.nunique()),'window_count_per_block':n,
        'placebo_signed_energy_percentiles_kwh':noise.tolist(),
        'placebo_mean_signed_w_day_bootstrap_95pct':np.quantile(draws,[.025,.975]).tolist(),
        'event_minus_placebo_median_kwh':signed-noise[1],
        'empirical_model_error_band_kwh':[signed-noise[2],signed-noise[0]],
        'exceeds_placebo_97_5pct':bool(signed>noise[2]),
        'interpretation':'Non-simultaneous empirical model-error band, NOT true-counterfactual confidence interval; matching tolerance 20% Pg2 and GTI; adjacent days may depend.'}


def electrical_envelopes(train):
    edges=np.unique(np.quantile(train.reference_power_w,np.linspace(0,1,11)))
    g=train.copy(); g['stratum']=pd.cut(g.reference_power_w,edges,include_lowest=True,labels=False)
    env={}
    for signal in ELECTRICAL:
        g['delta']=g[f'{signal}_x']-g[f'{signal}_y']
        env[signal]={str(int(k)):{'low':float(v.delta.quantile(.025)),'median':float(v.delta.median()),'high':float(v.delta.quantile(.975)),'n':len(v)} for k,v in g.groupby('stratum') if pd.notna(k)}
    return edges,env


def electrical_event(ev,train,edges,env):
    b=ev.loc[ev.quality&ev.eligible].copy()
    b['stratum']=pd.cut(b.reference_power_w,edges,include_lowest=True,labels=False)
    # Joint numpy matching avoids five repeated dataframe searches per observation.
    train_ref=train.reference_power_w.to_numpy(float)
    train_delta=np.column_stack([(train[f'{s}_x']-train[f'{s}_y']).to_numpy(float) for s in ELECTRICAL])
    train_gti=train.GTI.to_numpy(float) if 'GTI' in train else None
    train_ta=train.TA.to_numpy(float) if 'TA' in train else None
    matched={s:[] for s in ELECTRICAL}
    for row in b.itertuples(index=False):
        mask=(train_ref>=.8*row.reference_power_w)&(train_ref<=1.2*row.reference_power_w)
        if train_gti is not None and np.isfinite(getattr(row,'GTI',np.nan)):
            mask &= (train_gti>=.8*row.GTI)&(train_gti<=1.2*row.GTI)&(train_ta>=row.TA-5)&(train_ta<=row.TA+5)
        if mask.sum()>=10:
            med=np.nanmedian(train_delta[mask],axis=0)
            for i,s in enumerate(ELECTRICAL):
                matched[s].append(float(getattr(row,f'{s}_x')-getattr(row,f'{s}_y')-med[i]))
    out={}
    for signal in ELECTRICAL:
        delta=b[f'{signal}_x']-b[f'{signal}_y']; valid=b.stratum.notna()&delta.notna()
        ranges=b.loc[valid,'stratum'].map(lambda k: env[signal].get(str(int(k))))
        low=ranges.map(lambda x:x['low']); high=ranges.map(lambda x:x['high'])
        outside=(delta.loc[valid]<low)|(delta.loc[valid]>high)
        matches=matched[signal]
        out[signal]={'unit':UNITS[signal],'valid_five_minute_bins':int(valid.sum()),'median_target':float(b[f'{signal}_x'].median()),'median_reference':float(b[f'{signal}_y'].median()),
            'median_target_minus_reference':float(delta.median()),'outside_healthy_envelope_fraction':float(outside.mean()) if len(outside) else None,
            'matched_bins':len(matches),'matched_median_delta_from_healthy':float(np.median(matches)) if matches else None}
    return out


def run(data_dir, output_dir, protocol_path, include_weather=True):
    root=Path(data_dir); out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    protocol=Path(protocol_path).read_bytes(); protocol_hash=hashlib.sha256(protocol).hexdigest()
    checks=[]; audits={}
    for name in FILES:
        if not include_weather and FILES[name]['role']=='weather': continue
        path=download_file(name,root)
        check=verify_file(path,name); check['sha256']=hashlib.sha256(path.read_bytes()).hexdigest() if FILES[name]['role']=='metadata' else None
        # Stream SHA256 instead of reading large CSVs into memory.
        if check['sha256'] is None:
            h=hashlib.sha256()
            with path.open('rb') as f:
                for block in iter(lambda:f.read(4*1024*1024),b''): h.update(block)
            check['sha256']=h.hexdigest()
        checks.append(check)
        if name.endswith('.csv'):
            print('Audit',name,flush=True); audits[name]=audit_csv(path,chunksize=500000,expected_frequency_seconds=1 if FILES[name]['role']=='weather' else 5)
    t=load_electrical(root/'dt2_electrical_production_inverter_1_with_faults.csv',target=True)
    t['source_row']=np.arange(len(t))
    r=load_electrical(root/'dt3_electrical_production_inverter_2.csv',target=False)
    alignment=exact_alignment_report(t,r); paired=merge_electrical(t,r)
    first=t.loc[t.fault_label.gt(0),'timestamp'].min(); first_day=str(first.tz_convert('Indian/Reunion').date())
    preliminary=make_bins(paired)
    days=sorted(preliminary.loc[preliminary.healthy&preliminary.daylight&preliminary.paired_valid&preliminary.local_day.astype(str).lt(first_day),'local_day'].astype(str).unique())
    i=int(.6*len(days)); j=int(.8*len(days)); boundaries={'train':[days[0],days[i-1]],'selection':[days[i],days[j-1]],'calibration':[days[j],days[-1]],'protected_start':first_day}
    if include_weather:
        print('Streaming weather means',flush=True)
        weather=load_weather_bins(root/'dt1_solar_and_meteorological_measurement.csv')
        paired['bin_start']=paired.timestamp.dt.floor('5min')
        paired=paired.merge(weather,on='bin_start',how='left',validate='many_to_one').drop(columns='bin_start')
    b=aggregate(paired)
    splits={n:b.loc[b.local_day.between(*limits)&b.quality&b.healthy].copy() for n,limits in boundaries.items() if isinstance(limits,list)}
    if len(splits['train'])<500 or any(len(splits[n])<100 or splits[n].local_day.nunique()<10 for n in ['selection','calibration']):
        raise ValueError('Frozen feasibility minimum failed; do not manufacture protected conclusions.')
    models,chosen,comparison=fit_models(splits['train'],splits['selection'])
    q=np.quantile(splits['train'].reference_power_w,[.005,.995]); margin=.1*(q[1]-q[0]); domain=[float(q[0]-margin),float(q[1]+margin)]
    stream=predict_stream(paired,models[chosen],domain)
    all_windows={m:aggregate(stream,m) for m in [1,5,15]}
    thresholds={m:float(max(0, w.loc[w.local_day.between(*boundaries['calibration'])&w.quality&w.eligible&w.healthy,'residual_w'].quantile(.99))) for m,w in all_windows.items()}
    baseline_windows={}
    baseline_thresholds={}
    for name,model in models.items():
        bw=all_windows[5] if name==chosen else aggregate(predict_stream(paired,model,domain),5)
        bc=bw.loc[bw.local_day.between(*boundaries['calibration'])&bw.quality&bw.eligible&bw.healthy]
        baseline_thresholds[name]=float(max(0,bc.residual_w.quantile(.99)))
        baseline_windows[name]=bw
    edges,env=electrical_envelopes(splits['train'])
    code_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    frozen={'version':VERSION,'protocol_sha256':protocol_hash,'code_sha256':code_hash,'freeze_utc':datetime.now(timezone.utc).isoformat(),
        'boundaries':boundaries,'populations':{n:{'bins':len(v),'days':int(v.local_day.nunique()),'weather_bins':int(weather_valid(v).sum())} for n,v in splits.items()},
        'model_comparison_pre_protected':comparison,'reference_domain_w':domain,'thresholds_w':thresholds,'baseline_thresholds_w':baseline_thresholds,'primary_minutes':5,'persistence_windows':2,'electrical_edges':edges,'electrical_envelopes':env}
    as_json_file(frozen,out/'frozen_parameters_v2.json')
    print('FROZEN',chosen,thresholds,flush=True)
    # PROTECTED scoring begins here; no fitting or tuning below this line.
    windows={m:alarms(w,thresholds[m],m) for m,w in all_windows.items()}
    w=windows[5]; later=b.loc[b.local_day.ge(first_day)&b.quality&b.healthy]
    comparison.update({'protocol_sha256':protocol_hash,'boundaries':boundaries,'populations':frozen['populations'],'later_healthy_scores':{},'common_weather_later_scores':{},'later_healthy_day_uncertainty':{}})
    for n,model in models.items():
        s=later.loc[weather_valid(later)] if len(model['features'])>1 else later
        pred=_predict(model,s); comparison['later_healthy_scores'][n]=_score(s.target_power_w,pred)
        comparison['later_healthy_day_uncertainty'][n]=_day_block_bootstrap(s.target_power_w,pred,s.local_day,seed=SEED)
        common=later.loc[weather_valid(later)]
        if len(common): comparison['common_weather_later_scores'][n]=_score(common.target_power_w,_predict(model,common))
    episodes=find_fault_episodes(t); records=[]
    cal=w.loc[w.local_day.between(*boundaries['calibration'])]
    for e in episodes:
        rows=stream.loc[stream.timestamp.between(e['start'],e['end'])]
        energy=integrate(rows,require_fault=True)
        raw=t.loc[t.timestamp.between(e['start'],e['end'])]
        denom_rows=raw.copy(); denom_rows['eligible']=True; denom_rows['residual_w']=0.; denom_rows['expected_power_w']=0.
        labelled_support=integrate(denom_rows,require_fault=True)['valid_seconds']
        energy['observed_labelled_support_seconds']=labelled_support
        energy['coverage']=energy['valid_seconds']/labelled_support if labelled_support else 0.
        energy['wall_span_coverage']=energy['valid_seconds']/e['duration_seconds'] if e['duration_seconds'] else 0.
        evw=w.loc[w.bin_start.lt(e['end'])&w.confirmation.gt(e['start'])]
        records.append({**e,'event_id':f'shading_{e["group_id"]+1:02d}','intervention_day':str(e['start'].tz_convert('Indian/Reunion').date()),
            'detection':{str(m):event_detection(e,windows[m]) for m in windows},'energy':energy,
            'placebo':placebos(e,stream,cal,energy) if energy['available'] else {'status':'unavailable'},
            'electrical':electrical_event(evw,splits['train'],edges,env)})
    detected=sum(e['detection']['5']['detected'] for e in records)
    baseline_detection={}
    for name,bw in baseline_windows.items():
        ba=alarms(bw,baseline_thresholds[name],5)
        baseline_detection[name]={'detected_episodes':sum(event_detection(e,ba)['detected'] for e in episodes),'episode_count':len(episodes),'threshold_w':baseline_thresholds[name],'healthy_stability':healthy_metrics(ba,first_day)}
    eligible=[e for e in records if e['energy']['coverage']>=.8]
    healthy={str(m):healthy_metrics(x,first_day) for m,x in windows.items()}
    calibration={str(m):healthy_metrics(x,*boundaries['calibration']) for m,x in windows.items()}
    day=pd.DataFrame([{'day':e['intervention_day'],'detected':int(e['detection']['5']['detected']),'energy':e['energy']['signed_energy_kwh'],'n':1} for e in records]).groupby('day').agg(detected=('detected','sum'),energy=('energy','sum'),n=('n','sum'))
    rng=np.random.default_rng(SEED); a=day.to_numpy(float); draws=a[rng.integers(len(a),size=(2000,len(a)))].sum(axis=1)
    recall_ci=np.quantile(draws[:,0]/draws[:,2],[.025,.975]).tolist()
    mean_energy_ci=np.quantile(draws[:,1]/draws[:,2],[.025,.975]).tolist()
    monthly=later.assign(month=later.bin_start.dt.strftime('%Y-%m'),ratio=later.target_power_w/later.reference_power_w).groupby('month').ratio.median()
    stability={'monthly_healthy_target_reference_median':monthly.to_dict(),'relative_median_range':float((monthly.max()-monthly.min())/monthly.median()),'interpretation':'Target/reference co-stability diagnostic only; inverter2 has no per-row fault ground truth.'}
    alarm_population=w.loc[w.local_day.ge(first_day)&w.usable&w.known]
    tp=int((alarm_population.alert&alarm_population.fault_fraction.gt(0)).sum()); fp=int((alarm_population.alert&alarm_population.healthy&alarm_population.support_healthy).sum())
    fn=int((~alarm_population.alert&alarm_population.fault_fraction.gt(0)).sum()); tn=int((~alarm_population.alert&alarm_population.healthy).sum())
    nmae=comparison['later_healthy_scores'][chosen]['nmae']; rate=healthy['5']['false_alarm_runs_per_healthy_hour']
    verdict='GO' if detected/len(records)>=.8 and rate<=.05 and nmae<=.1 else 'LIMIT'
    grouping={str(g):len(find_fault_episodes(t,gap_seconds=g)) for g in [60,300,900]}
    best=next((e for e in records if e['detection']['5']['detected'] and e['energy']['coverage']>=.8),None)
    electrical_healthy=electrical_event(w.loc[w.local_day.ge(first_day)&w.healthy],splits['train'],edges,env)
    result={'analysis_version':VERSION,'protocol_sha256':protocol_hash,'code_sha256':code_hash,'produced_at':datetime.now(timezone.utc).isoformat(),
        'verdicts':{'E1':'GO','E2':verdict,'E3':'LIMIT','E4':'LIMIT','universal_diagnosis':'REJECT'},'boundaries':boundaries,
        'selected_model':chosen,'thresholds_w':thresholds,'episode_count':len(records),'detected_episodes':detected,'episode_recall':detected/len(records),
        'adequately_covered_episode_count':len(eligible),'covered_episode_recall':sum(e['detection']['5']['detected'] for e in eligible)/len(eligible) if eligible else None,
        'intervention_days':len(day),'recall_intervention_day_bootstrap_95pct':recall_ci,'mean_event_signed_energy_day_bootstrap_95pct_kwh':mean_energy_ci,
        'grouping_sensitivity_counts':grouping,'healthy_stability':healthy,'healthy_calibration':calibration,'reference_stability':stability,
        'window_confusion':{'unit':'eligible labelled 5min windows; any label makes a positive window','TP':tp,'FN':fn,'FP':fp,'TN':tn,'precision_on_labelled_windows':tp/(tp+fp) if tp+fp else None,'ambiguous_boundary_alerts_excluded':int((alarm_population.alert&alarm_population.healthy&~alarm_population.support_healthy).sum())},
        'electrical_later_healthy_comparison':electrical_healthy,
        'baseline_detection':baseline_detection,'window_sensitivity':{str(m):{'detected':sum(e['detection'][str(m)]['detected'] for e in records),'episodes':len(records)} for m in windows},
        'missed_event_ids':[e['event_id'] for e in records if not e['detection']['5']['detected']],
        'demo_event_id':best['event_id'] if best else None,'episodes':records,
        'limitations':['Retrospective dataset-aware redesign; no prospective test.','Single installation; day blocks may remain dependent.','No inverter2 per-row ground truth or actual unshaded inverter1 counterfactual.','Placebo intervals quantify empirical healthy-model error, not causal magnitude accuracy.','Raw weather-assisted predictions use 5min environmental means.','No maintenance interventions, recovered electricity, diagnosis validation or finance.']}
    as_json_file(result,out/'shading_evaluation_v2.json'); as_json_file(comparison,out/'model_comparison_v2.json')
    as_json_file({'checks':checks,'audits':audits,'alignment':alignment,'label_values_after_canonicalization':sorted(t.fault_label.dropna().unique()),'protocol_sha256':protocol_hash},out/'data_quality_report_v2.json')
    versions={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','matplotlib','jsonschema','nbformat','pytest','nbclient']}
    as_json_file({'python':__import__('sys').version,'versions':versions},out/'runtime_versions_v2.json')
    w.to_csv(out/'five_minute_evaluation_v2.csv',index=False)
    pd.DataFrame([{'event_id':e['event_id'],'start':e['start'],'end':e['end'],'labels':','.join(e['labels']),**e['detection']['5'],**e['energy']} for e in records]).to_csv(out/'episode_metrics_v2.csv',index=False)
    selected=stream.loc[stream.timestamp.between(best['start']-pd.Timedelta(minutes=20),best['end']+pd.Timedelta(minutes=20))] if best else stream.iloc[:0]
    selected.to_csv(out/'demo_measured_series_v2.csv',index=False)
    healthy_example=cal.loc[cal.usable&cal.healthy].iloc[:12]
    hstream=stream.loc[stream.timestamp.between(healthy_example.bin_start.min(),healthy_example.bin_start.max()+pd.Timedelta(minutes=5))]
    examples={'healthy_interval':{'start':hstream.timestamp.min(),'end':hstream.timestamp.max(),'energy':integrate(hstream)},'shading_event':best,
        'insufficient_data':{'start':t.timestamp.iloc[np.diff(t.timestamp.astype('int64')).argmax()],'reason':'Measured source outage: no interpolation and no deviation estimate.'}}
    gap=np.diff(t.timestamp.astype('int64').to_numpy())/1e9; gi=int(gap.argmax())
    examples['insufficient_data'].update({'start':t.timestamp.iloc[gi],'end':t.timestamp.iloc[gi+1],'gap_seconds':float(gap[gi]),'energy_kwh':None})
    as_json_file(examples,out/'example_cases_v2.json')
    charts(out,w,records,comparison,boundaries,best)
    return result


def charts(out,w,records,comparison,boundaries,best):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    charts_dir=out/'charts'; charts_dir.mkdir(exist_ok=True)
    fig,ax=plt.subplots(figsize=(11,3.5))
    for k,color in [('train','royalblue'),('selection','darkorange'),('calibration','seagreen')]:
        v=boundaries[k]
        ax.axvspan(pd.Timestamp(v[0]),pd.Timestamp(v[1])+pd.Timedelta(days=1),color=color,alpha=.2,label=k)
    ax.axvspan(pd.Timestamp(boundaries['protected_start']),w.bin_start.max().tz_localize(None),color='gray',alpha=.1,label='protected / later healthy')
    for e in records: ax.plot(pd.Timestamp(e['start']).tz_localize(None),1,'|',color='crimson')
    ax.set(title='Frozen pre-event populations and 23 protected shading episodes',yticks=[],xlabel='Date (UTC markers; split dates RET)'); ax.legend(); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(charts_dir/'timeline.png',dpi=160); plt.close(fig)
    if best:
        s=w.loc[w.bin_start.between(best['start']-pd.Timedelta(minutes=30),best['end']+pd.Timedelta(minutes=30))].set_index('bin_start')
        s=s.reindex(pd.date_range(s.index.min(),s.index.max(),freq='5min'))
        fig,ax=plt.subplots(figsize=(11,4)); ax.plot(s.index,s.target_power_w,label='Measured inverter1 AC W'); ax.plot(s.index,s.expected_power_w,label='Healthy expected AC W')
        ax.axvspan(best['start'],best['end'],color='crimson',alpha=.1,label='Physical shading label')
        hits=s.loc[s.alert.fillna(False)]; ax.scatter(hits.confirmation,hits.target_power_w,marker='x',label='Alarm at window end (y=window mean)')
        ax.set(title=f'{best["event_id"]}: earliest eligible detected case',ylabel='W',xlabel='UTC'); ax.legend(); fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(charts_dir/'demo_episode.png',dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,4)); ids=[e['event_id'] for e in records]; vals=[e['energy']['signed_energy_kwh'] for e in records]
    ax.bar(ids,vals,color=['teal' if e['detection']['5']['detected'] else 'orange' for e in records]); ax.tick_params(axis='x',rotation=90); ax.set(ylabel='Signed expected-minus-measured kWh',title='Known-event deviations; teal detected, orange missed; no repair recovery'); fig.tight_layout(); fig.savefig(charts_dir/'event_energy.png',dpi=160); plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,4)); names=list(comparison['later_healthy_scores']); ax.bar(names,[comparison['later_healthy_scores'][n]['mae_w'] for n in names]); ax.tick_params(axis='x',rotation=25); ax.set(ylabel='Later healthy MAE (W)',title='Stability scores after all parameters frozen'); fig.tight_layout(); fig.savefig(charts_dir/'model_comparison.png',dpi=160); plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,signal in zip(axs,['Va','Ia']):
        ax.bar(ids,[e['electrical'][signal]['matched_median_delta_from_healthy'] if e['electrical'][signal]['matched_median_delta_from_healthy'] is not None else np.nan for e in records]); ax.tick_params(axis='x',rotation=90); ax.set(title=f'{signal}: matched target-reference shift',ylabel=UNITS[signal])
    fig.tight_layout(); fig.savefig(charts_dir/'electrical_observations.png',dpi=160); plt.close(fig)


def main():
    p=argparse.ArgumentParser(); p.add_argument('--data-dir',required=True); p.add_argument('--output-dir',required=True); p.add_argument('--protocol',required=True); p.add_argument('--no-weather',action='store_true'); a=p.parse_args()
    result=run(a.data_dir,a.output_dir,a.protocol,not a.no_weather)
    print(json.dumps({k:result[k] for k in ['selected_model','episode_count','detected_episodes','episode_recall','verdicts']},indent=2))

if __name__=='__main__': main()
