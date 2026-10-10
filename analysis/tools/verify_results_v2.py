"""Independent real-result arithmetic checks; run after the full notebook/CLI."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

def verify(analysis_dir):
    root=Path(analysis_dir); p=root/'results'
    s=json.loads((p/'shading_evaluation_v2.json').read_text())
    f=json.loads((p/'frozen_parameters_v2.json').read_text())
    cases=json.loads((p/'example_cases_v2.json').read_text())
    w=pd.read_csv(p/'five_minute_evaluation_v2.csv',parse_dates=['bin_start'])
    cal=w.loc[w.local_day.between(*s['boundaries']['calibration'])&w.quality&w.eligible&w.healthy]
    assert abs(float(cal.residual_w.quantile(.99))-s['thresholds_w']['5'])<1e-9
    assert hashlib.sha256((root/'EXPERIMENT_PROTOCOL_V2.md').read_bytes()).hexdigest()==s['protocol_sha256']
    assert hashlib.sha256((root/'src/solarloss_research/evaluation_v2.py').read_bytes()).hexdigest()==s['code_sha256']
    h=s['healthy_stability']['5']
    assert abs(h['healthy_alert_runs']/h['evaluated_healthy_hours']-h['false_alarm_runs_per_healthy_hour'])<1e-12
    assert sum(e['detection']['5']['detected'] for e in s['episodes'])==s['detected_episodes']
    c=cases['shading_event']; d=pd.read_csv(p/'demo_measured_series_v2.csv',parse_dates=['timestamp'])
    d=d.loc[d.timestamp.between(c['start'],c['end'])]
    par=f['model_comparison_pre_protected']['parameters'][s['selected_model']]
    expected=np.full(len(d),par['intercept_w'])
    for name,coefficient in par['coefficients'].items(): expected+=d[name].to_numpy()*coefficient
    ok=d.eligible.to_numpy(bool); labels=d.fault_label.to_numpy(); dt=np.diff(d.timestamp.astype('int64'))/1e9
    assert np.allclose(expected[ok],d.expected_power_w.to_numpy()[ok],rtol=0,atol=1e-8)
    valid=ok[:-1]&ok[1:]&(labels[:-1]>0)&(labels[1:]>0)&(dt>0)&(dt<=18)&(np.diff(d.source_row)==1)
    residual=expected-d.target_power_w.to_numpy()
    energy=float(np.sum(.5*(residual[:-1]+residual[1:])[valid]*dt[valid])/3.6e6)
    assert abs(energy-c['energy']['signed_energy_kwh'])<1e-10
    print('Protocol/code identity, calibration threshold, healthy alarm arithmetic, event counts, raw demo predictions and energy: PASS')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--analysis-dir',default=str(Path(__file__).resolve().parents[1])); verify(parser.parse_args().analysis_dir)
