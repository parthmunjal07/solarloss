"""Mechanics and leakage tests; synthetic fixtures are not scientific results."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import pandas as pd
import pytest
from solarloss_research.dataset import canonical_fault_label, LABEL_DESCRIPTIONS
from solarloss_research.model import find_fault_episodes
from solarloss_research.evaluation_v2 import integrate, alarms, predict_stream, support_seconds
from solarloss_research.review import review_identity, build_review_artifact


@pytest.mark.parametrize('label',[0,1,2.1,2.2,2.3,3.1,3.2,4])
def test_all_documented_float32_labels_map(label):
    canonical=canonical_fault_label(np.float32(label))
    assert canonical==label
    assert canonical in LABEL_DESCRIPTIONS


def test_unknown_label_not_rounded_into_known_label():
    assert canonical_fault_label(2.1001)==2.1001
    assert np.isnan(canonical_fault_label(np.nan))


def test_episode_fractional_description_regression():
    t=pd.DataFrame({'timestamp':pd.date_range('2022-02-08',periods=3,freq='6s',tz='UTC'),'fault_label':np.array([2.1,2.1,2.1],dtype='float32')})
    assert find_fault_episodes(t)[0]['label_descriptions']==[LABEL_DESCRIPTIONS[2.1]]


def rows(times,residuals,labels):
    return pd.DataFrame({'timestamp':pd.to_datetime(times,unit='s',utc=True),'source_row':np.arange(len(times)),
        'residual_w':residuals,'expected_power_w':np.full(len(times),100.),'target_power_w':100.-np.array(residuals),
        'fault_label':labels,'eligible':True})


def test_actual_elapsed_integration_excludes_gap_and_healthy_pause():
    f=rows([0,6,12,60,66],[20]*5,[1,1,0,1,1])
    r=integrate(f,require_fault=True)
    assert r['valid_seconds']==12
    assert r['signed_energy_kwh']==pytest.approx(240/3.6e6)
    assert support_seconds(f.timestamp)==18


def test_integration_does_not_bridge_deleted_original_rows():
    f=rows([0,6,12],[10]*3,[1]*3)
    assert integrate(f.iloc[[0,2]],require_fault=True)['available'] is False


def test_signed_zero_positive_energy_is_not_evidence():
    f=rows([0,6,12],[-10,0,10],[0]*3)
    r=integrate(f)
    assert r['signed_energy_kwh']==0
    assert r['positive_only_kwh']>0


def test_missing_predictions_do_not_become_zero_energy():
    f=rows([0,6],[20,20],[1,1]); f['eligible']=False
    r=integrate(f,True)
    assert r['signed_energy_kwh'] is None


def windows(minutes=5):
    return pd.DataFrame({'bin_start':pd.to_datetime(['2022-01-01T00:00Z','2022-01-01T00:05Z','2022-01-01T00:15Z']),
        'residual_w':[30.,30.,30.],'quality':True,'eligible':True,'healthy':True})


def test_persistence_uses_confirmation_end_and_resets_on_missing_window():
    w=alarms(windows(),20,5)
    assert w.alert.tolist()==[False,True,False]
    assert w.confirmation.iloc[1]==pd.Timestamp('2022-01-01T00:10Z')


def test_calibrated_window_threshold_not_reused_implicitly():
    w=alarms(windows(),35,5)
    assert not w.alert.any()


def test_predictions_and_eligibility_do_not_depend_on_fault_labels():
    f=pd.DataFrame({'reference_power_w':[200.,300.],'target_power_w':[150.,150.],'fault_label':[0.,0.]})
    m={'features':['reference_power_w'],'fixed_capacity_ratio':.9}
    a=predict_stream(f,m,[100,1000]); f['fault_label']=[4.,2.1]; b=predict_stream(f,m,[100,1000])
    np.testing.assert_array_equal(a.expected_power_w,b.expected_power_w)
    np.testing.assert_array_equal(a.eligible,b.eligible)


def test_reference_outside_frozen_predictor_domain_unavailable():
    f=pd.DataFrame({'reference_power_w':[5000.],'target_power_w':[150.]})
    m={'features':['reference_power_w'],'fixed_capacity_ratio':.9}
    assert not predict_stream(f,m,[100,2000]).eligible.any()


def test_export_identity_and_unapproved_semantics_are_blocked():
    assert review_identity('shading_01')==('review_shading_01','review_shading_01.json')
    with pytest.raises(ValueError,match='approval'):
        build_review_artifact(audits={},file_checks=[],alignment={},bins=pd.DataFrame(),model_info={},summary={},produced_at='2026-10-10T00:00Z')
    with pytest.raises(ValueError,match='unavailable shading'):
        build_review_artifact(audits={},file_checks=[],alignment={},bins=pd.DataFrame(),model_info={},summary={'episodes':[]},produced_at='2026-10-10T00:00Z',semantics_approved=True)


def test_proposed_metric_availability_and_signed_semantics():
    import json
    from jsonschema import Draft202012Validator
    schema=json.loads((Path(__file__).resolve().parents[1]/'contracts/review.schema.v0.2.0.proposed.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema['properties']['metrics']['items'])
    m={'id':'signed_generation_deviation','availability':'estimated','value':-.1,'unit':'kWh','population':'synthetic test event','definition':'expected-observed','calculation':'trapezoid UTC seconds','reason':None,'coverage':{'valid_seconds':12,'observed_labelled_seconds':12,'wall_span_seconds':12}}
    assert not list(validator.iter_errors(m))
    m['id']='positive_only_generation_deviation'
    assert list(validator.iter_errors(m))
    m.update(availability='unavailable',value=None,reason='No eligible measurements')
    assert not list(validator.iter_errors(m))
    m['value']=0
    assert list(validator.iter_errors(m))
