from __future__ import annotations
import argparse, csv, json, math, statistics, hashlib
from pathlib import Path
from typing import Any

_ap = argparse.ArgumentParser(description="Rebuild the evidence ledger from the extracted source package.")
_ap.add_argument("--source-root", type=Path, required=True)
_ap.add_argument("--output-root", type=Path, required=True)
_args = _ap.parse_args()
ROOT = _args.source_root.resolve()
OUT = _args.output_root.resolve()
EVD = OUT / 'evidence'
FIG = OUT / 'figures'
EVD.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)

_cache: dict[str, Any] = {}

def load(rel: str) -> Any:
    if rel not in _cache:
        with open(ROOT / rel, 'r', encoding='utf-8') as f:
            _cache[rel] = json.load(f)
    return _cache[rel]

def ptr_get(obj: Any, pointer: str) -> Any:
    if pointer in ('', '/'):
        return obj
    cur = obj
    for token in pointer.lstrip('/').split('/'):
        token = token.replace('~1','/').replace('~0','~')
        cur = cur[int(token)] if isinstance(cur, list) else cur[token]
    return cur

def jval(rel: str, pointer: str) -> Any:
    return ptr_get(load(rel), pointer)

def encode(v: Any) -> str:
    if isinstance(v, (dict, list, bool)) or v is None:
        return json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    return repr(v) if isinstance(v, float) else str(v)

rows: list[dict[str, str]] = []

def add_json(eid: str, problem: str, description: str, rel: str, pointer: str, unit: str = '', note: str = '') -> Any:
    value = jval(rel, pointer)
    rows.append({
        'evidence_id': eid, 'problem_id': problem, 'status': 'SEALED_JSON',
        'description': description, 'source_path': rel, 'json_pointer_or_range': pointer,
        'value': encode(value), 'unit': unit, 'derivation': '', 'source_evidence_ids': '', 'notes': note,
    })
    return value

def add_derived(eid: str, problem: str, description: str, value: Any, unit: str, formula: str, sources: list[str], note: str = '') -> Any:
    rows.append({
        'evidence_id': eid, 'problem_id': problem, 'status': 'DERIVED_FROM_SEALED_JSON',
        'description': description, 'source_path': '', 'json_pointer_or_range': '',
        'value': encode(value), 'unit': unit, 'derivation': formula,
        'source_evidence_ids': ';'.join(sources), 'notes': note,
    })
    return value

def add_code(eid: str, problem: str, description: str, rel: str, line_range: str, excerpt: str, note: str = '') -> None:
    rows.append({
        'evidence_id': eid, 'problem_id': problem, 'status': 'PACKAGE_SOURCE_CODE',
        'description': description, 'source_path': rel, 'json_pointer_or_range': line_range,
        'value': excerpt, 'unit': '', 'derivation': '', 'source_evidence_ids': '', 'notes': note,
    })

def add_hyp(eid: str, problem: str, description: str, value: str, note: str = '') -> None:
    rows.append({
        'evidence_id': eid, 'problem_id': problem, 'status': 'HYPOTHETICAL',
        'description': description, 'source_path': '', 'json_pointer_or_range': '',
        'value': value, 'unit': '', 'derivation': '', 'source_evidence_ids': '', 'notes': note,
    })

# ---------- P1 ----------
r408='results/research_loop/r408_v2_solving_gate/formal_analysis.json'
r409='results/research_loop/r409_heldout_gate/formal_analysis.json'
r415='results/research_loop/r415_energy_port_extra_banks/formal_analysis.json'
r437='results/research_loop/r437_relaxed_spectral/formal_analysis.json'
add_json('P1-E01','P1','Selected constructive arm',r408,'/found_candidate/arm_id')
add_json('P1-E02','P1','R408 differential ratio',r408,'/found_candidate/differential_ratio','ratio')
add_json('P1-E03','P1','R408 probe cross ratio',r408,'/found_candidate/probe_cross_ratio','ratio')
add_json('P1-E04','P1','R409 held-out differential ratio',r409,'/differential_ratio','ratio')
add_json('P1-E05','P1','R409 held-out probe cross ratio',r409,'/probe_cross_ratio','ratio')
add_json('P1-E06','P1','Differential-ratio ceiling',r415,'/thresholds/differential_ratio_max','ratio')
add_json('P1-E07','P1','Probe-cross ceiling',r415,'/thresholds/probe_cross_ratio_max','ratio')
add_json('P1-E08','P1','Strict probe-cross ceiling',r415,'/thresholds/strict_cross_ratio_max','ratio')
blocks=[('conditions','a4_conditions_b'),('relaxed','a4_md_relaxed'),('stiff','a4_md_stiff')]
p1tab=[]
base_num=9
for idx,(short,b) in enumerate(blocks):
    n=base_num+idx*8
    M=add_json(f'P1-E{n:02d}','P1',f'{short} block baseline M',r415,f'/blocks/{b}/block/vsg_m0','package model unit')
    D=add_json(f'P1-E{n+1:02d}','P1',f'{short} block D vector',r415,f'/blocks/{b}/block/d0_per_agent','package model unit')
    rd=add_json(f'P1-E{n+2:02d}','P1',f'{short} block differential ratio',r415,f'/blocks/{b}/summary/differential_ratio','ratio')
    rx=add_json(f'P1-E{n+3:02d}','P1',f'{short} block probe cross ratio',r415,f'/blocks/{b}/summary/probe_cross_ratio','ratio')
    ld=add_json(f'P1-E{n+4:02d}','P1',f'{short} local differential energy',r415,f'/blocks/{b}/summary/local_differential_energy','Hz^2 s')
    lx=add_json(f'P1-E{n+5:02d}','P1',f'{short} local off-diagonal energy',r415,f'/blocks/{b}/summary/local_probe_off_diagonal_energy','Hz^2 s')
    gp=add_json(f'P1-E{n+6:02d}','P1',f'{short} candidate guards pass',r415,f'/blocks/{b}/summary/candidate_guards_pass')
    passed=add_json(f'P1-E{n+7:02d}','P1',f'{short} block pass',r415,f'/blocks/{b}/summary/passed')
    cand_d=add_derived(f'P1-D{idx*3+1:02d}','P1',f'{short} candidate differential energy',rd*ld,'Hz^2 s','differential_ratio × local_differential_energy',[f'P1-E{n+2:02d}',f'P1-E{n+4:02d}'])
    cand_x=add_derived(f'P1-D{idx*3+2:02d}','P1',f'{short} candidate off-diagonal energy',rx*lx,'Hz^2 s','probe_cross_ratio × local_probe_off_diagonal_energy',[f'P1-E{n+3:02d}',f'P1-E{n+5:02d}'])
    red=add_derived(f'P1-D{idx*3+3:02d}','P1',f'{short} relative differential-energy reduction',1-rd,'fraction','1 − differential_ratio',[f'P1-E{n+2:02d}'])
    p1tab.append({'block':short,'M':M,'D_each':D[0] if isinstance(D,list) and len(set(D))==1 else encode(D),'r_d':rd,'r_cross':rx,'local_Ed':ld,'candidate_Ed':cand_d,'local_Ex':lx,'candidate_Ex':cand_x,'relative_Ed_reduction':red,'guards_pass':gp,'block_pass':passed})
add_json('P1-E33','P1','R437 sampling frequency',r437,'/fs_hz','Hz')
add_json('P1-E34','P1','Relaxed-block median peak frequency',r437,'/classification/relaxed_peak_freq_hz','Hz')
add_json('P1-E35','P1','Relaxed-block spectral-window fraction',r437,'/classification/relaxed_window_fraction','fraction')
add_json('P1-E36','P1','Passing-block peak frequencies',r437,'/classification/passing_peaks_hz','Hz')
add_json('P1-E37','P1','Passing-block window fractions',r437,'/classification/passing_window_fractions','fraction')
add_json('P1-E38','P1','R437 mechanism verdict',r437,'/classification/verdict')
add_json('P1-E39','P1','R437 mechanism reason',r437,'/classification/reason')
add_json('P1-E40','P1','Relaxed candidate median peak PSD',r437,'/per_block/a4_md_relaxed/bandpass_k3p5/median_peak_psd','PSD unit')
add_json('P1-E41','P1','Relaxed local median peak PSD',r437,'/per_block/a4_md_relaxed/local_feasibility_native/median_peak_psd','PSD unit')

# ---------- P2 ----------
r440='results/research_loop/r440_robustness_expansion/formal_analysis.json'
p2tab=[]
for n in (1,2):
    rel=f'results/research_loop/r440_robustness_expansion/delay/delay_{n}.json'
    b=(n-1)*9+1
    steps=add_json(f'P2-E{b:02d}','P2',f'Delay case {n}: delay steps',rel,'/delay_steps','steps')
    rd=add_json(f'P2-E{b+1:02d}','P2',f'Delay case {n}: differential ratio',r440,f'/classification/per_delay/{n}/ratios/r_d','ratio')
    rx=add_json(f'P2-E{b+2:02d}','P2',f'Delay case {n}: cross ratio',r440,f'/classification/per_delay/{n}/ratios/r_cross','ratio')
    gp=add_json(f'P2-E{b+3:02d}','P2',f'Delay case {n}: guards pass',r440,f'/classification/per_delay/{n}/ratios/guards_pass')
    passed=add_json(f'P2-E{b+4:02d}','P2',f'Delay case {n}: unit pass',r440,f'/classification/per_delay/{n}/passed')
    cd=add_json(f'P2-E{b+5:02d}','P2',f'Delay case {n}: candidate mean differential energy',rel,'/bandpass_k3p5/disturbance/mean_differential_frequency_energy_hz2_s','Hz^2 s')
    ld=add_json(f'P2-E{b+6:02d}','P2',f'Delay case {n}: local mean differential energy',rel,'/local_feasibility_native/disturbance/mean_differential_frequency_energy_hz2_s','Hz^2 s')
    cx=add_json(f'P2-E{b+7:02d}','P2',f'Delay case {n}: candidate off-diagonal energy',rel,'/bandpass_k3p5/probe/off_diagonal_response_energy_hz2_s','Hz^2 s')
    lx=add_json(f'P2-E{b+8:02d}','P2',f'Delay case {n}: local off-diagonal energy',rel,'/local_feasibility_native/probe/off_diagonal_response_energy_hz2_s','Hz^2 s')
    exceed=add_derived(f'P2-D{n:02d}','P2',f'Delay case {n}: amount above differential ceiling',rd-jval(r415,'/thresholds/differential_ratio_max'),'ratio','r_d − differential_ratio_max',[f'P2-E{b+1:02d}','P1-E06'])
    p2tab.append({'delay_steps':steps,'r_d':rd,'r_cross':rx,'candidate_Ed':cd,'local_Ed':ld,'candidate_Ex':cx,'local_Ex':lx,'r_d_excess_over_0p95':exceed,'guards_pass':gp,'passed':passed})
add_json('P2-E19','P2','R440 overall verdict',r440,'/classification/verdict')

# ---------- P3 source-code facts ----------
add_code('P3-S01','P3','Environment writes interpolated live M and D into ANDES GENCLS before each TDS substep','src/andes_rl_kundur/env/andes/base_env.py','L382-L408','GENCLS.set("M", ...); GENCLS.set("D", ...); TDS.run(); then states are read.')
add_code('P3-S02','P3','Environment diagnostic uses the swing-equation form','src/andes_rl_kundur/env/andes/base_env.py','L523-L541','omega_dot = (Pm - Pe - D*(omega-1.0))/max(M,0.1).')
add_code('P3-S03','P3','Imported audit states the index-1 DAE reduced input Jacobian and warns actual Jacobians are absent','paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md','DAE paragraph + Remaining project-specific inputs','B_ur = f_u - f_y g_y^{-1} g_u; actual reduced/DAE Jacobians are not supplied.')

# ---------- M3 ----------
r410='results/research_loop/r410_message_repair/endpoint_table.json'
r431='results/research_loop/r431_sac_slew/formal_analysis.json'
r438='results/research_loop/r438_sac_message_channels/formal_analysis.json'
add_json('M3-E01','M3','R410 message differential ratio vs deterministic',r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_message/disturbance_differential_energy','ratio')
add_json('M3-E02','M3','R410 message off-diagonal ratio vs deterministic',r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_message/off_diagonal_response_energy','ratio')
add_json('M3-E03','M3','R410 no-message differential ratio vs deterministic',r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/disturbance_differential_energy','ratio')
add_json('M3-E04','M3','R410 no-message off-diagonal ratio vs deterministic',r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/off_diagonal_response_energy','ratio')
add_json('M3-E05','M3','R410 message improvement over no-message: differential',r410,'/full_method_improvement_vs_comparators/cd_matd3_no_message/disturbance_differential_energy','fraction')
add_json('M3-E06','M3','R410 message improvement over no-message: off-diagonal',r410,'/full_method_improvement_vs_comparators/cd_matd3_no_message/off_diagonal_response_energy','fraction')
add_json('M3-E07','M3','R431 message differential ratio vs deterministic',r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_message/disturbance_differential_energy','ratio')
add_json('M3-E08','M3','R431 message off-diagonal ratio vs deterministic',r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_message/off_diagonal_response_energy','ratio')
add_json('M3-E09','M3','R431 no-message differential ratio vs deterministic',r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/disturbance_differential_energy','ratio')
add_json('M3-E10','M3','R431 no-message off-diagonal ratio vs deterministic',r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/off_diagonal_response_energy','ratio')
add_json('M3-E11','M3','R431 message improvement over no-message: differential',r431,'/b1_table/message_improvement_vs_comparators/cd_matd3_no_message/disturbance_differential_energy','fraction')
add_json('M3-E12','M3','R431 message improvement over no-message: off-diagonal',r431,'/b1_table/message_improvement_vs_comparators/cd_matd3_no_message/off_diagonal_response_energy','fraction')
add_json('M3-E13','M3','R438 observation-only differential median',r438,'/classification/per_arm_medians/sac_obs_only/disturbance_differential_energy','energy')
add_json('M3-E14','M3','R438 observation-only off-diagonal median',r438,'/classification/per_arm_medians/sac_obs_only/off_diagonal_response_energy','energy')
add_json('M3-E15','M3','R438 reward-only differential median',r438,'/classification/per_arm_medians/sac_rew_only/disturbance_differential_energy','energy')
add_json('M3-E16','M3','R438 reward-only off-diagonal median',r438,'/classification/per_arm_medians/sac_rew_only/off_diagonal_response_energy','energy')
add_json('M3-E17','M3','R438 sealed message differential median',r438,'/classification/r431_sealed_medians/message/disturbance_differential_energy','energy')
add_json('M3-E18','M3','R438 sealed message off-diagonal median',r438,'/classification/r431_sealed_medians/message/off_diagonal_response_energy','energy')
add_json('M3-E19','M3','R438 sealed no-message differential median',r438,'/classification/r431_sealed_medians/no_message/disturbance_differential_energy','energy')
add_json('M3-E20','M3','R438 sealed no-message off-diagonal median',r438,'/classification/r431_sealed_medians/no_message/off_diagonal_response_energy','energy')
add_json('M3-E21','M3','R438 observation-only disturbance-side classification',r438,'/classification/channel_sides/sac_obs_only/disturbance')
add_json('M3-E22','M3','R438 observation-only off-diagonal-side classification',r438,'/classification/channel_sides/sac_obs_only/off_diagonal')
add_json('M3-E23','M3','R438 reward-only disturbance-side classification',r438,'/classification/channel_sides/sac_rew_only/disturbance')
add_json('M3-E24','M3','R438 reward-only off-diagonal-side classification',r438,'/classification/channel_sides/sac_rew_only/off_diagonal')
add_json('M3-E25','M3','R438 verdict',r438,'/classification/verdict')

# ---------- M5 ----------
r416='results/research_loop/r416_headroom_expansion/formal_analysis.json'
r439='results/research_loop/r439_timevarying_oracle/formal_analysis.json'
r441='results/research_loop/r441_timevarying_guard/formal_analysis.json'
add_json('M5-E01','M5','R416 classification',r416,'/classification/classification')
add_json('M5-E02','M5','R416 selected deterministic arm',r416,'/classification/selected_deterministic_arm')
add_json('M5-E03','M5','R439 original verdict',r439,'/classification/verdict')
add_json('M5-E04','M5','R441 guard-completion verdict',r441,'/classification/verdict')
m5tab=[]
for i,pid in enumerate(['eval_a','eval_b','eval_c','eval_d']):
    rel=f'results/research_loop/r441_timevarying_guard/profiles/{pid}.json'
    base=5+i*15
    k=add_json(f'M5-E{base:02d}','M5',f'{pid}: winner segment count',rel,'/winner_k','segments')
    cand=add_json(f'M5-E{base+1:02d}','M5',f'{pid}: winner schedule',rel,'/winner_candidate')
    sd=add_json(f'M5-E{base+2:02d}','M5',f'{pid}: static differential energy',rel,'/static/disturbance_differential_energy','energy')
    wd=add_json(f'M5-E{base+3:02d}','M5',f'{pid}: winner differential energy',rel,'/winner/disturbance_differential_energy','energy')
    sx=add_json(f'M5-E{base+4:02d}','M5',f'{pid}: static off-diagonal energy',rel,'/static/off_diagonal_response_energy','energy')
    wx=add_json(f'M5-E{base+5:02d}','M5',f'{pid}: winner off-diagonal energy',rel,'/winner/off_diagonal_response_energy','energy')
    idd=add_json(f'M5-E{base+6:02d}','M5',f'{pid}: differential improvement',rel,'/guards/r_d_improvement','fraction')
    idx=add_json(f'M5-E{base+7:02d}','M5',f'{pid}: off-diagonal improvement',rel,'/guards/r_cross_improvement','fraction')
    sr=add_json(f'M5-E{base+8:02d}','M5',f'{pid}: static action RMS',rel,'/static/action_rms','action RMS')
    wr=add_json(f'M5-E{base+9:02d}','M5',f'{pid}: winner action RMS',rel,'/winner/action_rms','action RMS')
    st=add_json(f'M5-E{base+10:02d}','M5',f'{pid}: static action total variation',rel,'/static/action_total_variation','action TV')
    wt=add_json(f'M5-E{base+11:02d}','M5',f'{pid}: winner action total variation',rel,'/winner/action_total_variation','action TV')
    rg=add_json(f'M5-E{base+12:02d}','M5',f'{pid}: action RMS no-harm',rel,'/guards/action_stress_no_harm/action_rms_no_harm')
    tg=add_json(f'M5-E{base+13:02d}','M5',f'{pid}: action variation no-harm',rel,'/guards/action_stress_no_harm/action_variation_no_harm')
    cg=add_json(f'M5-E{base+14:02d}','M5',f'{pid}: common-mode no-harm bundle',rel,'/guards/common_no_harm')
    ri=add_derived(f'M5-D{i*2+1:02d}','M5',f'{pid}: fractional action-RMS increase',wr/sr-1,'fraction','winner.action_rms / static.action_rms − 1',[f'M5-E{base+9:02d}',f'M5-E{base+8:02d}'])
    ti=add_derived(f'M5-D{i*2+2:02d}','M5',f'{pid}: fractional action-TV increase',wt/st-1,'fraction','winner.action_total_variation / static.action_total_variation − 1',[f'M5-E{base+11:02d}',f'M5-E{base+10:02d}'])
    m5tab.append({'profile':pid,'winner_k':k,'winner_schedule':encode(cand),'static_Ed':sd,'winner_Ed':wd,'Ed_improvement':idd,'static_Ex':sx,'winner_Ex':wx,'Ex_improvement':idx,'static_action_rms':sr,'winner_action_rms':wr,'action_rms_increase':ri,'static_action_tv':st,'winner_action_tv':wt,'action_tv_increase':ti,'action_rms_guard':rg,'action_tv_guard':tg,'common_guards':encode(cg)})
# candidates tested values from R439
for i in range(4):
    add_json(f'M5-E{65+i:02d}','M5',f'R439 profile {i}: candidates tested',r439,f'/classification/per_profile/{i}/candidates_tested','candidates')
add_hyp('M5-H01','M5','Proposed exhaustive diagonal-grid schedule cardinality','|G|^K (brief describes a five-point grid; treat the numerical cardinality as HYPOTHETICAL until the candidate generator is sealed as JSON).')

# ---------- M4 ----------
r436='results/research_loop/r436_energy_residual_sac/formal_analysis.json'
add_json('M4-E01','M4','R436 classification',r436,'/classification/classification')
add_json('M4-E02','M4','Variants passed by deterministic bandpass',r436,'/classification/bandpass_pass_variants')
add_json('M4-E03','M4','Variants beyond deterministic: message residual',r436,'/classification/beyond_deterministic_variants/residual_sac_message')
add_json('M4-E04','M4','Variants beyond deterministic: no-message residual',r436,'/classification/beyond_deterministic_variants/residual_sac_no_message')
add_json('M4-E05','M4','Nominal bandpass differential ratio',r436,'/classification/nominal_bandpass/r_d','ratio')
add_json('M4-E06','M4','Nominal bandpass cross ratio',r436,'/classification/nominal_bandpass/r_cross','ratio')
add_json('M4-E07','M4','Nominal residual-message median differential ratio',r436,'/variants/nominal/residual_sac_message/median_r_d','ratio')
add_json('M4-E08','M4','Nominal residual-message median cross ratio',r436,'/variants/nominal/residual_sac_message/median_r_cross','ratio')
add_json('M4-E09','M4','Nominal residual-no-message median differential ratio',r436,'/variants/nominal/residual_sac_no_message/median_r_d','ratio')
add_json('M4-E10','M4','Nominal residual-no-message median cross ratio',r436,'/variants/nominal/residual_sac_no_message/median_r_cross','ratio')
# Compute max absolute median deviation from bandpass over variants
for arm, label, did in [('residual_sac_message','message','M4-D01'),('residual_sac_no_message','no-message','M4-D03')]:
    diffs_d=[]; diffs_x=[]; src_d=[]; src_x=[]
    for v,rec in load(r436)['variants'].items():
        bd=rec['bandpass']['r_d']; bx=rec['bandpass']['r_cross']
        ad=rec[arm]['median_r_d']; ax=rec[arm]['median_r_cross']
        diffs_d.append(abs(ad-bd)); diffs_x.append(abs(ax-bx))
        src_d.extend([f'{r436}#/variants/{v}/bandpass/r_d',f'{r436}#/variants/{v}/{arm}/median_r_d'])
        src_x.extend([f'{r436}#/variants/{v}/bandpass/r_cross',f'{r436}#/variants/{v}/{arm}/median_r_cross'])
    add_derived(did,'M4',f'Max absolute r_d deviation from bandpass across variants: {label}',max(diffs_d),'ratio','max_v |median_r_d(arm,v) − r_d(bandpass,v)|',[],note='Source pointer pairs listed in evidence/m4_deviation_sources.json.')
    add_derived('M4-D02' if did=='M4-D01' else 'M4-D04','M4',f'Max absolute r_cross deviation from bandpass across variants: {label}',max(diffs_x),'ratio','max_v |median_r_cross(arm,v) − r_cross(bandpass,v)|',[],note='Source pointer pairs listed in evidence/m4_deviation_sources.json.')
# save source pointer pairs separately
m4src={}
for arm in ['residual_sac_message','residual_sac_no_message']:
    m4src[arm]=[]
    for v in load(r436)['variants']:
        m4src[arm].append({'variant':v,'bandpass_r_d':f'/variants/{v}/bandpass/r_d','arm_r_d':f'/variants/{v}/{arm}/median_r_d','bandpass_r_cross':f'/variants/{v}/bandpass/r_cross','arm_r_cross':f'/variants/{v}/{arm}/median_r_cross'})
(EVD/'m4_deviation_sources.json').write_text(json.dumps({'source_path':r436,'pointer_pairs':m4src},indent=2),encoding='utf-8')

# ---------- M1 ----------
r425='results/research_loop/r425_guard_constraints_signfix/formal_analysis.json'
r427='results/research_loop/r427_critic_target_normalization/formal_analysis.json'
add_json('M1-E01','M1','Projected-dual step',r425,'/repair/multiplier_step','dual units/update')
add_json('M1-E02','M1','Projected-dual ceiling',r425,'/repair/multiplier_max','dual units')
add_json('M1-E03','M1','RMS harm factor',r425,'/repair/rms_harm_factor','ratio')
add_json('M1-E04','M1','TV harm factor',r425,'/repair/tv_harm_factor','ratio')

def multiplier_aggregates(rel: str, prefix: str, start: int):
    d=load(rel)['guard_multiplier_readout']
    rms=[x for rec in d.values() for x in rec['rms_residual_trace']]
    tv=[x for rec in d.values() for x in rec['tv_residual_trace']]
    mu=[x for rec in d.values() for key in ('mu_rms_trace','mu_tv_trace') for x in rec[key]]
    root_ptrs=[f'/guard_multiplier_readout/{k}' for k in d]
    vals={
      'rms_min':min(rms),'rms_median':statistics.median(rms),'rms_max':max(rms),
      'tv_min':min(tv),'tv_median':statistics.median(tv),'tv_max':max(tv),
      'all_mu_at_cap':all(abs(x-jval(r425,'/repair/multiplier_max'))<1e-12 for x in mu),
      'n_runs':len(d), 'n_residuals_each':len(rms),
    }
    for j,(key,desc,unit) in enumerate([
      ('rms_min','RMS residual minimum','normalized residual'),('rms_median','RMS residual median','normalized residual'),('rms_max','RMS residual maximum','normalized residual'),
      ('tv_min','TV residual minimum','normalized residual'),('tv_median','TV residual median','normalized residual'),('tv_max','TV residual maximum','normalized residual'),('all_mu_at_cap','All stored RMS/TV multipliers equal the sealed ceiling','boolean')]):
      add_derived(f'M1-D{start+j:02d}','M1',f'{prefix}: {desc}',vals[key],unit,f'aggregate over {";".join(root_ptrs)}',[],note='All source arrays are in the named JSON under the six run keys.')
    return vals
m1_r425=multiplier_aggregates(r425,'R425',1)
m1_r427=multiplier_aggregates(r427,'R427',8)
(EVD/'m1_aggregate_source_roots.json').write_text(json.dumps({'R425':{'source_path':r425,'roots':[f'/guard_multiplier_readout/{k}' for k in load(r425)['guard_multiplier_readout']]},'R427':{'source_path':r427,'roots':[f'/guard_multiplier_readout/{k}' for k in load(r427)['guard_multiplier_readout']]}},indent=2),encoding='utf-8')

# ---------- M2 ----------
r421r='results/research_loop/r421_diagnostics/diagnostic_readout.json'
r435='results/research_loop/r435_multiplier_floor/formal_analysis.json'
rat421=[rec['failure_flags']['ratios']['critic_loss_q4_over_q1'] for rec in load(r421r)['runs'].values()]
add_derived('M2-D01','M2','R421 critic-loss Q4/Q1 minimum',min(rat421),'ratio','min across /runs/*/failure_flags/ratios/critic_loss_q4_over_q1',[],note=f'Source: {r421r}.')
add_derived('M2-D02','M2','R421 critic-loss Q4/Q1 maximum',max(rat421),'ratio','max across /runs/*/failure_flags/ratios/critic_loss_q4_over_q1',[],note=f'Source: {r421r}.')
# R432
r432_files=sorted(ROOT.glob('results/research_loop/r432_b3_diagnostics/train/*/seed*/diagnostics_summary.json'))
rat432=[]; r432_roots=[]
for p in r432_files:
    rel=str(p.relative_to(ROOT)); d=load(rel); rat432.append(d['critic_loss_q4']/d['critic_loss_q1']); r432_roots.append(rel+'#/critic_loss_q1;#/critic_loss_q4')
add_derived('M2-D03','M2','R432 critic-loss Q4/Q1 minimum',min(rat432),'ratio','min(critic_loss_q4 / critic_loss_q1) over six diagnostics summaries',[],note='Source pairs listed in evidence/m2_ratio_sources.json.')
add_derived('M2-D04','M2','R432 critic-loss Q4/Q1 maximum',max(rat432),'ratio','max(critic_loss_q4 / critic_loss_q1) over six diagnostics summaries',[],note='Source pairs listed in evidence/m2_ratio_sources.json.')
rat427=[rec['ratio'] for rec in load(r427)['critic_loss_original_readout'].values()]
add_derived('M2-D05','M2','R427 original-scale critic-loss Q4/Q1 minimum',min(rat427),'ratio','min across /critic_loss_original_readout/*/ratio',[],note=f'Source: {r427}.')
add_derived('M2-D06','M2','R427 original-scale critic-loss Q4/Q1 maximum',max(rat427),'ratio','max across /critic_loss_original_readout/*/ratio',[],note=f'Source: {r427}.')
add_json('M2-E01','M2','R435 mechanical integrity',r435,'/mechanical_ok')
add_json('M2-E02','M2','R435 primary pairs hit',r435,'/primary_pairs_hit','pairs')
add_json('M2-E03','M2','R435 primary threshold',r435,'/primary_threshold','pairs')
add_json('M2-E04','M2','R435 verdict',r435,'/verdict')
# guard failure counts in R427
gf=load(r427)['classification']['guard_failures']
metrics=['action_rms_no_harm','action_variation_no_harm','common_frequency_no_harm','worst_peak_no_harm','rocof_no_harm']
counts={m:sum(m in rec['failed'] for rec in gf if rec['arm_id'].startswith('cd_matd3')) for m in metrics}
for i,m in enumerate(metrics,7):
    add_derived(f'M2-D{i:02d}','M2',f'R427 CD-arm guard-failure count: {m}',counts[m],'run-profile failures','count records in /classification/guard_failures for CD arms containing metric',[],note=f'Source: {r427}.')
(EVD/'m2_ratio_sources.json').write_text(json.dumps({'R421':{'source_path':r421r,'pointers':[f'/runs/{k}/failure_flags/ratios/critic_loss_q4_over_q1' for k in load(r421r)['runs']]},'R432':r432_roots,'R427':{'source_path':r427,'pointers':[f'/critic_loss_original_readout/{k}/ratio' for k in load(r427)['critic_loss_original_readout']]},'R427_guard_failures':{'source_path':r427,'pointer':'/classification/guard_failures'}},indent=2),encoding='utf-8')

# ---------- C1 ----------
add_code('C1-S01','C1','Blueprint explicitly does not provide a formal dual certificate','tmp/yang_md_decoupling_marl/vsg_v2_fir_response_solver.py','L269','"formal_dual_certificate": False')
add_code('C1-S02','C1','Audit permits class-limited Youla/SLS infeasibility only with bounded stable convex class and verified dual/Farkas certificate','paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md','Safe-to-use bullet','A precisely bounded stable convex class with an independently verified dual lower bound or Farkas certificate is required.')

# ---------- write evidence register ----------
fieldnames=['evidence_id','problem_id','status','description','source_path','json_pointer_or_range','value','unit','derivation','source_evidence_ids','notes']
with open(EVD/'evidence_register.csv','w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(rows)
(EVD/'evidence_register.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')

# Data tables
for name,data in [('p1_block_decomposition.csv',p1tab),('p2_delay_table.csv',p2tab),('m5_endpoint_action_table.csv',m5tab)]:
    with open(EVD/name,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0].keys())); w.writeheader(); w.writerows(data)

# M3 table
m3tab=[
 {'family':'R410 CD-MATD3','arm':'message','differential_ratio':jval(r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_message/disturbance_differential_energy'),'offdiag_ratio':jval(r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_message/off_diagonal_response_energy')},
 {'family':'R410 CD-MATD3','arm':'no_message','differential_ratio':jval(r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/disturbance_differential_energy'),'offdiag_ratio':jval(r410,'/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/off_diagonal_response_energy')},
 {'family':'R431 adapted SAC','arm':'message','differential_ratio':jval(r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_message/disturbance_differential_energy'),'offdiag_ratio':jval(r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_message/off_diagonal_response_energy')},
 {'family':'R431 adapted SAC','arm':'no_message','differential_ratio':jval(r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/disturbance_differential_energy'),'offdiag_ratio':jval(r431,'/b1_table/median_endpoint_ratio_vs_deterministic/cd_matd3_no_message/off_diagonal_response_energy')},
]
with open(EVD/'m3_contrast_table.csv','w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(m3tab[0].keys()));w.writeheader();w.writerows(m3tab)

# Summary of aggregate values for report templating
aggregates={
 'p1':p1tab,'p2':p2tab,'m5':m5tab,'m1':{'R425':m1_r425,'R427':m1_r427},
 'm2':{'R421_min':min(rat421),'R421_max':max(rat421),'R432_min':min(rat432),'R432_max':max(rat432),'R427_min':min(rat427),'R427_max':max(rat427),'R427_guard_counts':counts},
 'm4':{r['evidence_id']:r['value'] for r in rows if r['evidence_id'].startswith('M4-D')},
}
(EVD/'computed_aggregates.json').write_text(json.dumps(aggregates,ensure_ascii=False,indent=2),encoding='utf-8')

# Figures (default matplotlib colors only)
import matplotlib.pyplot as plt
# P1 ratio decomposition
fig,ax=plt.subplots(figsize=(7.4,4.2))
labels=[x['block'] for x in p1tab]; xs=range(len(labels))
ax.plot(xs,[x['r_d'] for x in p1tab],marker='o',label='r_d')
ax.plot(xs,[x['r_cross'] for x in p1tab],marker='s',label='r_cross')
ax.axhline(jval(r415,'/thresholds/differential_ratio_max'),linestyle='--',label='r_d ceiling')
ax.axhline(jval(r415,'/thresholds/strict_cross_ratio_max'),linestyle=':',label='strict r_cross ceiling')
ax.set_xticks(list(xs),labels); ax.set_ylabel('ratio'); ax.set_title('P1: sealed block ratios'); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(FIG/'p1_block_ratios.png',dpi=180); plt.close(fig)
# P1 absolute energies
fig,ax=plt.subplots(figsize=(7.4,4.2))
ax.plot(xs,[x['local_Ed'] for x in p1tab],marker='o',label='local differential energy')
ax.plot(xs,[x['candidate_Ed'] for x in p1tab],marker='s',label='candidate differential energy')
ax.set_xticks(list(xs),labels); ax.set_ylabel('Hz²·s'); ax.set_title('P1: ratio numerator and denominator by block'); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(FIG/'p1_absolute_differential_energy.png',dpi=180); plt.close(fig)
# P2 delay
fig,ax=plt.subplots(figsize=(7.0,4.0))
ax.plot([x['delay_steps'] for x in p2tab],[x['r_d'] for x in p2tab],marker='o',label='r_d')
ax.plot([x['delay_steps'] for x in p2tab],[x['r_cross'] for x in p2tab],marker='s',label='r_cross')
ax.axhline(jval(r415,'/thresholds/differential_ratio_max'),linestyle='--',label='r_d ceiling')
ax.set_xlabel('integer delay steps'); ax.set_ylabel('ratio'); ax.set_title('P2: sealed delay cases'); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(FIG/'p2_delay_ratios.png',dpi=180); plt.close(fig)
# M3 message contrast
fig,ax=plt.subplots(figsize=(7.4,4.2))
for family in ['R410 CD-MATD3','R431 adapted SAC']:
    sub=[x for x in m3tab if x['family']==family]
    ax.plot([x['arm'] for x in sub],[x['differential_ratio'] for x in sub],marker='o',label=family+' differential')
ax.axhline(1.0,linestyle='--',label='deterministic reference')
ax.set_ylabel('differential ratio'); ax.set_title('M3: sign reversal of message contrast'); ax.grid(True,alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(FIG/'m3_message_contrast.png',dpi=180); plt.close(fig)
# M5 endpoint vs action stress
fig,ax=plt.subplots(figsize=(7.4,4.5))
for row in m5tab:
    ax.scatter(row['action_rms_increase'],row['Ed_improvement'])
    ax.annotate(row['profile'],(row['action_rms_increase'],row['Ed_improvement']),xytext=(4,4),textcoords='offset points')
ax.set_xlabel('fractional action-RMS increase'); ax.set_ylabel('differential-energy improvement'); ax.set_title('M5: measured endpoint/action-stress anchors'); ax.grid(True,alpha=.25); fig.tight_layout(); fig.savefig(FIG/'m5_endpoint_action_tradeoff.png',dpi=180); plt.close(fig)

print(f'wrote {len(rows)} evidence rows')
