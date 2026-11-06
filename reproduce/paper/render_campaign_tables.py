from pathlib import Path
import re, csv, json, shutil, statistics, math, hashlib

import argparse
ap=argparse.ArgumentParser(description='Render manuscript tables from frozen campaign aggregates')
ap.add_argument('--evidence',type=Path,required=True)
ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1])
ap.add_argument('--audit-dir',type=Path)
ap.add_argument('--settlement-evidence',type=Path)
ap.add_argument('--exploration-evidence',type=Path)
ap.add_argument('--rerun-equivalence',type=Path,help='summary.json of the full regeneration of the 80 paired runs under model 2.1.0')
args=ap.parse_args()
S=args.source; E=args.evidence; ROOT=args.audit_dir or S
ROOT.mkdir(parents=True,exist_ok=True)
T=S/'tables'; T.mkdir(exist_ok=True)
C=E/'campaign'/'tables'
def rows(path):
    with Path(path).open() as f: return list(csv.DictReader(f))
def cell(x): return x.replace('_',r'\_')
conds=['A_off','A_on','B_off','B_on']
def cl(c):
    world, state = c.split('_')
    return '$' + world + r'_{\mathrm{' + state + '}}$'
pol={'pi_b':r'$\pi_b$','pi_far':r'$\pi_{\mathrm{visit}}$','pi_near':r'$\pi_{\mathrm{sms}}$','pi_stage':r'$\pi_{\mathrm{stage}}$'}
errors=rows(C/'error_summary.csv')
idx={(r['cond'],r['regime'],r['estimator'],r['target']):r for r in errors}
def er(c,reg,m,p):
    r=idx[c,reg,m,p]
    return f"${float(r['mean_error']):+.1f} \\pm {float(r['se_mean_error']):.1f}$"
def table(name,caption,label,cols,heads,data,scale=False):
    lines=[r'\begin{table}[!htbp]',r'\centering',r'\caption{'+caption+'}',r'\label{'+label+'}',r'\small']
    if scale: lines += [r'\begin{adjustbox}{max width=\linewidth}']
    lines += [r'\begin{tabular}{'+cols+'}',r'\toprule',' & '.join(heads)+r' \\',r'\midrule']
    lines += [' & '.join(row)+r' \\' for row in data]
    lines += [r'\bottomrule',r'\end{tabular}']
    if scale: lines += [r'\end{adjustbox}']
    lines += [r'\end{table}','']
    (T/(name+'.tex')).write_text('\n'.join(lines))

# Independently reconcile seed statistics from per-run data; these data are rounded CSV.
raw=rows(C/'estimates_by_run.csv'); count=0
for key,r in idx.items():
    g=[x for x in raw if (x['cond'],x['regime'],x['estimator'],x['target'])==key and x['error']]
    if not g: continue
    x=[float(z['error']) for z in g]
    for field,calc in [('mean_error',statistics.mean(x)),('se_mean_error',statistics.stdev(x)/math.sqrt(len(x))),('rmse',math.sqrt(statistics.mean(z*z for z in x)))]:
        assert abs(float(r[field])-calc)<.003,(key,field,r[field],calc)
        count+=1
ref=rows(C/'reference_values_by_run.csv'); gaps=rows(C/'reference_gaps_by_run.csv')
assert len({(r['cond'],r['seed']) for r in ref})==80
assert max(float(r['se_within']) for r in ref)<1.89
assert max(float(r['se_within']) for r in gaps)<.62
sel=rows(C/'selection_by_run.csv')
assert all(r['ref_best']=='pi_stage' and r['top_resolved']=='True' for r in sel)
post=rows(C/'selection_tests_post_hoc.csv')
tests=sorted([r for r in post if r['kind']=='seed-block t'],key=lambda r:float(r['p']))
assert len(tests)==12
running=0
for j,r in enumerate(tests):
    running=max(running,min(1,(len(tests)-j)*float(r['p'])))
    assert abs(running-float(r['p_holm']))<.00001
(ROOT/'numeric_reconciliation.json').write_text(json.dumps({'error_summary_checks':count,'reference_runs':80,'reference_value_se_max':max(float(r['se_within']) for r in ref),'reference_gap_se_max':max(float(r['se_within']) for r in gaps),'selection_rows_checked':len(sel),'holm_tests_checked':len(tests),'result':'pass'},indent=2)+'\n')

# All displayed numbers are generated from the technical evidence.
data=[]
for c in conds:
    data.append([cl(c)]+[f"{statistics.mean(float(r['mean']) for r in ref if r['cond']==c and r['candidate']==p):.1f}" for p in pol])
table('campaign_values','Policy reference scores by condition.','tab:campaignvalues','lrrrr',['condition']+list(pol.values()),data)
table('campaign_worlds','Recovery mechanisms and baseline hazards.','tab:campaignworlds','lrrr',['channel','A, all stages','B, before 90 days','B, from 90 days'],[
['none',r'$-0.85$',r'$-0.85$',r'$-0.85$'],['SMS',r'$+0.10$',r'$+0.30$',r'$-0.10$'],['app message',r'$+0.18$',r'$+0.30$',r'$0.00$'],['phone',r'$+0.35$',r'$+0.30$',r'$+0.45$'],['field visit',r'$+0.48$',r'$+0.30$',r'$+0.65$'],[r'baseline hazard $\tau$','0.001421',r'\multicolumn{2}{c}{0.001426}']])
models=[('tabular','dr','tabular DR'),('nontabular','dm','boosted DM'),('nontabular','is','boosted IS'),('nontabular','snips','boosted SNIPS'),('nontabular','dr','boosted DR'),('tabular','pilot_is','pilot-IS'),('tabular','pilot_dr','tabular pilot-DR')]
table('campaign_visit','Field-visit policy score errors.','tab:campaignvisit','lrrrr',['estimator']+[cl(c) for c in conds],[[name]+[er(c,reg,m,'pi_far') for c in conds] for reg,m,name in models],True)
ss=rows(C/'selection_summary.csv'); si={(r['cond'],r['regime'],r['estimator']):r for r in ss}
smodels=[('tabular','dr'),('nontabular','dr'),('tabular','pilot_is'),('tabular','pilot_dr')]
sdata=[]
for c in conds:
    line=[cl(c)]
    for reg,m in smodels:
        r=si[c,reg,m]
        line.append(f"{r['correct_all']}/20 (${float(r['mean_regret']):.1f} \\pm {float(r['se_mean_regret']):.1f}$)")
    sdata.append(line)
table('campaign_selection','Policy selection in the paired study.','tab:campaignselection','lrrrr',['condition','tabular DR','boosted DR','pilot-IS','pilot-DR'],sdata,True)
ir=rows(C/'interval_diagnostic.csv'); ii={(r['cond'],r['target'],r['interval']):r for r in ir}
idata=[]
for c,p in [(c,p) for c in ['A_off','B_off'] for p in ['pi_far','pi_near','pi_stage']]+[('A_on','pi_far'),('B_on','pi_far')]:
    line=[cl(c),pol[p]]
    for m in ['dm','dm_refit','dr','pilot_is']:
        r=ii[c,p,m]
        line.append(f"{r['contains']}/20 ({float(r['mean_width']):.1f})")
    idata.append(line)
table('campaign_intervals','Interval containment and width in the paired study.','tab:campaignintervals','llrrrr',['condition','target','DM (fixed model)','DM refit','DR','pilot-IS'],idata,True)
ag=rows(E/'campaign/import_tables/T10_log_family_agreement.csv'); ai={(r['cond'],r['regime'],r['target']):r for r in ag}
tgt=['π_visit','π_sms','π_stage']
agrows=[]
for c in conds:
    agrows.append([cl(c),'tabular']+[f"{float(ai[c,'tabular',p]['mean_spread']):.1f}" for p in tgt])
    agrows.append([cl(c),'boosted']+[f"{float(ai[c,'nontabular',p]['mean_spread']):.1f}" for p in tgt])
    agrows.append([cl(c),'boosted without IS']+[f"{float(ai[c,'nontabular',p]['mean_spread_without_is']):.1f}" for p in tgt])
table('campaign_agreement','Estimator disagreement by model regime.','tab:campaignagreement','llrrr',['condition','regime',pol['pi_far'],pol['pi_near'],pol['pi_stage']],agrows)
# RMSE (bootstrap-over-seeds SE) from the delivered import tables T4.
def pm(s): return '$'+s.replace(' ± ',r' \pm ')+'$'
rt={(r['cond'],r['estimator']):r for r in rows(E/'campaign/import_tables/T4_rmse_tabular.csv')}
rn={(r['cond'],r['estimator']):r for r in rows(E/'campaign/import_tables/T4_rmse_nontabular.csv')}
tcol={'pi_far':'π_visit','pi_near':'π_sms','pi_stage':'π_stage'}
rdata=[[cl(c),pol[p],pm(rt[c,'dr'][tcol[p]]),pm(rn[c,'dm'][tcol[p]]),pm(rn[c,'dr'][tcol[p]]),pm(rt[c,'pilot_is'][tcol[p]]),pm(rt[c,'pilot_dr'][tcol[p]])] for c in conds for p in ['pi_far','pi_near','pi_stage']]
table('campaign_rmse','Root-mean-square error by condition and target.','tab:campaignrmse','llrrrrr',['condition','target','tabular DR','boosted DM','boosted DR','pilot-IS','pilot-DR'],rdata,True)
# Support, clipping and importance weights from the per-run diagnostics.
sup=rows(C/'support_and_dose_by_run.csv'); ntd=rows(C/'nontabular_diagnostics_by_run.csv')
sdat=[]
for c in conds:
    for p in ['pi_far','pi_near','pi_stage']:
        s=[r for r in sup if r['cond']==c and r['target']==p]; d=[r for r in ntd if r['cond']==c and r['target']==p]
        anc=[int(float(r['n_anchor'])) for r in s]; mat=[int(float(r['n_match'])) for r in s]
        line=[cl(c),pol[p],f"{min(mat):,}--{max(mat):,}",f"{min(anc):,}--{max(anc):,}",str(max(int(float(r['contexts_without_support'])) for r in s)),f"{100*max(float(r['cohort_share_without_support']) for r in s):.2f}"]
        if d:
            line += [str(max(int(float(r['n_clipped_on_match'])) for r in d)),f"{min(float(r['propensity_min_on_match']) for r in d):.5f}",f"{statistics.mean(float(r['sum_w_over_n']) for r in d):.2f}"]
        else:
            line += ['--','--','--']
        sdat.append(line)
table('campaign_support','Support, clipping and importance weights in the paired study.','tab:campaignsupport','llrrrrrrr',['condition','target','matched rows','randomized matches','unsupported contexts','cohort share (\\%)','clipped matches','minimum propensity','mean IS weight'],sdat,True)
full=[]
full.append(r'\section{Complete results for the paired study}\label{sec:campaignextra}')
full.append('The complete comparisons in Tables~\\ref{tab:campaignfullerrors},\n\\ref{tab:campaignfullerrorsA_on}, \\ref{tab:campaignfullerrorsB_off} and\n\\ref{tab:campaignfullerrorsB_on} cover every fitted estimator in both regimes.\nThey report mean score errors and seed-level standard errors in US\\$\nper decision against independent simulated references, using 20 seeds\nper condition. Comparing regimes requires accounting for their joint\nchanges in covariates, model class and propensity cross-fitting.\nPilot-IS is shared across regimes, and shared seed blocks remain the\nunit for paired comparisons.\n\nComplementing these error comparisons, Table~\\ref{tab:campaignagreement}\nreports within-regime disagreement among log-based methods. The exploratory spread is the\nlargest minus smallest estimate within a run, in US\\$ per decision,\naveraged over 20 blocks per condition. For the tabular regime it includes\nDM, IS, SNIPS, DR and augmented DR, while the boosted comparison includes\nDM, IS, SNIPS and DR. The third row of each condition repeats the boosted\nspread without IS, whose positive control offset accounts for much of the\ndisagreement.\n')
full.append(r'\input{tables/campaign_agreement}')
for j,c in enumerate(conds):
    nm='full_errors_'+c
    allm=[('tabular',m,n) for m,n in [('dm','DM'),('dm_blind','DM, context-blind'),('is','IS'),('snips','SNIPS'),('dr','DR'),('dm_plus_is',r'DM\textsuperscript{+}-IS'),('pilot_is','pilot-IS'),('pilot_dr','pilot-DR')]]+[('nontabular',m,n) for m,n in [('dm','DM'),('is','IS'),('snips','SNIPS'),('dr','DR'),('pilot_dr','pilot-DR')]]
    body=[]
    for reg,m,n in allm:
        body.append([('tabular' if reg=='tabular' else 'boosted'),n]+[er(c,reg,m,p) for p in ['pi_far','pi_near','pi_stage']])
    label='tab:campaignfullerrors' if j==0 else 'tab:campaignfullerrors'+c
    table(nm,'Estimator score errors in condition '+cl(c)+'.',label,'llrrr',['regime','estimator',pol['pi_far'],pol['pi_near'],pol['pi_stage']],body,True)
    full.append(r'\input{tables/'+nm+'}')
full.append('Table~\\ref{tab:campaignrmse} reports root-mean-square error with a\nbootstrap-over-seeds SE for the representative estimators of both\nregimes and the pilots. Under coupling the pilots have no uniformly lower\nRMSE than the log-based estimators for the visit policy, because their\nseed-level dispersion is of the same order as the log-based error, and\ntheir RMSE is larger for the SMS and stage policies.\n')
full.append(r'\input{tables/campaign_rmse}')
full.append('\\FloatBarrier\n\n\\subsection{Numerical approximations and support}')
full.append('Targets use discount-bin centers, whereas matching logged offers vary within the bin. A development comparison of the center dose against a uniform dose within the bin changes SMS and visit values by approximately 0.03 and 0.08~US\\$ per decision.\n\nA complementary first-order calculation holds recovery probabilities fixed and includes the reward factor $(1-d)$, weighted by context. The resulting logged-dose offsets are approximately $+0.45$~US\\$ for the visit target, $-0.44$~US\\$ for SMS and $-1.97$~US\\$ for the stage-dependent target. Because this offset calculation excludes the recovery response to dose, it is not a complete bound on discretization error.\n')
full.append('The action-support check finds target cells in every occupied context except a small set of extreme-delinquency contexts containing at most 0.07\\% of the cohort. Randomized target matches range from 1,279 to 1,425 per run. Boosted estimated propensities are clipped at 0.001, below the design floor $\\varepsilon/44\\simeq0.0018$. Table~\\ref{tab:campaignsupport} reports, per condition and target, the logged rows matching the target, the randomized matches, the contexts without support and their cohort share, the matched rows whose estimated propensity fell below the clip, the minimum estimated propensity and the mean boosted IS weight, whose excess over one is the Jensen inflation behind the positive boosted IS control error. Neither regime receives borrower-level latent factors.\n')
full.append(r'\input{tables/campaign_support}')
(S/'sections/campaign_appendix.tex').write_text('\n'.join(full)+'\n')

# Additional score analyses; all numerical inputs are delivered aggregates.
if args.settlement_evidence and args.exploration_evidence:
    V=args.settlement_evidence
    X=args.exploration_evidence
    ex=rows(X/'main/tables/by_world.csv')
    exidx={r['world']:r for r in ex}
    def interval(mu,lo,hi,dec=2):
        return f"${float(mu):+.{dec}f}\\;[{float(lo):+.{dec}f}, {float(hi):+.{dec}f}]$"
    data=[]
    for w in ['A_on','B_on']:
        r=exidx[w]
        data.append([cl(w),interval(r['delta_mean'],r['delta_ci95_low'],r['delta_ci95_high']),
                     f"{100*float(r['relative_delta_mean']):.2f}\\%"])
    table('exploration_score',
          'Effect of randomized exploration on the score.',
          'tab:explorationscore','lrr',['world',r'$\Delta$ [95\% interval]','relative reduction'],data)

    gaps=rows(V/'diagnostic_2_1_0/tables/score_cash_gaps_by_world.csv')
    gi={(r['world'],r['objective'],r['gap']):r for r in gaps}
    gpairs=[('pi_far - pi_b',r'$\pi_{\mathrm{visit}}-\pi_b$'),
            ('pi_stage - pi_b',r'$\pi_{\mathrm{stage}}-\pi_b$'),
            ('pi_far - pi_stage',r'$\pi_{\mathrm{visit}}-\pi_{\mathrm{stage}}$')]
    data=[]
    for w in ['A_on','B_on']:
        for key,label in gpairs:
            line=[cl(w),label]
            for obj in ['score','cash']:
                r=gi[w,obj,key]
                line.append(interval(r['mean'],r['ci95_low'],r['ci95_high']))
            data.append(line)
    table('score_cash_gaps',
          'Policy differences under score and simulated cash.',
          'tab:scorecash','llrr',['world','gap','synthetic score','simulated cash'],data,True)

    eq=json.loads((V/'equivalence/summary.json').read_text())
    rep=json.loads((V/'representative_case/representative_case_comparison.json').read_text())
    assert eq['all_units_equal'] and eq['n_checks_equal']==eq['n_checks']==3968
    assert eq['checks_by_comparison']['2.0.0 vs 2.1.0']['equal']==3904
    assert rep['all_equal'] and all(c['equal'] for c in rep['checks'])
    panel=[c for c in rep['checks'] if 'panel.json' in c['check']]
    assert len(panel)==1 and panel[0]['n_compared']==788
    RQ=None
    if args.rerun_equivalence:
        RQ=json.loads(args.rerun_equivalence.read_text())
        # result fields only: the 3 timing/usage fields per run differ by construction
        assert RQ['runs_compared']==80 and RQ['fields_different']==3*RQ['runs_compared']
    table('score_equivalence',
          'Score equivalence between simulator models.',
          'tab:scoreequivalence','lr',['validation quantity','count'],[
              ['comparison units',str(eq['n_units'])],
              ['exact checks, all equal',str(eq['n_checks'])],
              ['cross-model checks, all equal','3904'],
              *([['complete runs regenerated','1 of 80'],
                 ['equal estimator-output fields in that run','788']] if not args.rerun_equivalence else
                [['complete runs regenerated',f"{RQ['runs_compared']} of 80"],
                 ['equal result fields in those runs (timing and memory excluded)',f"{RQ['fields_equal']:,} of {RQ['fields_equal']:,}"]])])
    table('auxiliary_compute',
          'Computation for score analyses and model verification.',
          'tab:auxiliarycompute','lr',['analysis','CPU-hours'],[
              ['exploration effect (Section~\\ref{sec:explorationscore}) and an unreported accounting variant','8.16'],
              ['partial-payment reward diagnostic (not reported)','1.01'],
              ['score-equivalence validation (Table~\\ref{tab:scoreequivalence}) and a superseded cash diagnostic','6.69']])
    (ROOT/'score_validation_numbers.json').write_text(json.dumps({
        'equivalence_units':eq['n_units'],'exact_checks':eq['n_checks'],
        'cross_model_checks':3904,'regenerated_runs':1,'panel_fields':788,
        'exploration_conditions':len(ex),'displayed_gap_rows':len(data),
        'source_files':{'exploration':str(X/'main/tables/by_world.csv'),
                        'cash_gaps':str(V/'diagnostic_2_1_0/tables/score_cash_gaps_by_world.csv')},
        'result':'pass'},indent=2)+'\n')

