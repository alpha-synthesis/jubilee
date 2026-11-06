"""Render manuscript tables and Figure 2 from the reruns.

Inputs: the aggregates written by collections-ope-testbed/scripts/tmlr_aggregate.py
for the three rerun protocols (paired, grid20, grid5), one directory per reward.
Every number printed by the manuscript's grid and cash tables comes from these
files; nothing is typed by hand.

Usage:
  python scripts/render_rerun_tables.py --rerun ../collections-ope-testbed/outputs/rerun_20261106 \
      [--source .] [--figures figures]
"""
from pathlib import Path
import argparse, csv, json, math, statistics
from collections import defaultdict

ap = argparse.ArgumentParser(description='Render tables from the reruns')
ap.add_argument('--rerun', type=Path, required=True)
ap.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
ap.add_argument('--figures', type=Path, default=None)
ap.add_argument('--skip-figure', action='store_true')
args = ap.parse_args()
S = args.source; R = args.rerun
T = S / 'tables'; T.mkdir(exist_ok=True)
FIG = args.figures or (S / 'figures')

def rows(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f))

def fnum(x):
    return float(x) if x not in ('', None, 'nan', 'None') else float('nan')

def pm(m, s, d=1):
    return f"${m:+.{d}f} \\pm {s:.{d}f}$"

def table(name, caption, label, cols, heads, data, scale=False, size=r'\footnotesize', prehead=None):
    lines = [r'\begin{table}[!htbp]', r'\centering', r'\caption{' + caption + '}', r'\label{' + label + '}', size]
    if scale:
        lines += [r'\begin{adjustbox}{max width=\linewidth}']
    lines += [r'\begin{tabular}{' + cols + '}', r'\toprule'] + (prehead or []) + [' & '.join(heads) + r' \\', r'\midrule']
    lines += [' & '.join(row) + r' \\' for row in data]
    lines += [r'\bottomrule', r'\end{tabular}']
    if scale:
        lines += [r'\end{adjustbox}']
    lines += [r'\end{table}', '']
    (T / (name + '.tex')).write_text('\n'.join(lines))

POL = {'pi_b': r'$\pi_b$', 'pi_far': r'$\pi_{\mathrm{visit}}$', 'pi_near': r'$\pi_{\mathrm{sms}}$',
       'pi_stage': r'$\pi_{\mathrm{stage}}$'}
EST = [('dm', 'DM'), ('dm_blind', 'DM (context-blind)'), ('is', 'IS'), ('snips', 'SNIPS'),
       ('dr', 'DR (cross-fitted)'), ('dm_plus_is', r'DM\textsuperscript{+}-IS'),
       ('pilot_is', 'pilot-IS'), ('pilot_dr', 'pilot-DR')]
LOGFAM = ['dm', 'is', 'snips', 'dr', 'dm_plus_is']

# ---------------------------------------------------------------- grid (score and cash)
# cell -> (alpha, coupling, sigma, eps, tau); hazards from configs/grid via the protocol copies
GRID = {
    'cell_01_control_eps0': ('01', 0.6, 'off', 0.25, 0.00, '0.001882'),
    'cell_02_control_eps08': ('02', 0.6, 'off', 0.25, 0.08, '0.001885'),
    'cell_03_a06_eps0': ('03', 0.6, 'on', 0.25, 0.00, '0.001700'),
    'cell_04_a06_eps08': ('04', 0.6, 'on', 0.25, 0.08, '0.001700'),
    'cell_05_a10_eps0': ('05', 1.0, 'on', 0.25, 0.00, '0.001461'),
    'cell_06_a10_eps08': ('06', 1.0, 'on', 0.25, 0.08, '0.001421'),
    'cell_07_a14_eps0': ('07', 1.4, 'on', 0.25, 0.00, '0.001015'),
    'cell_08_a14_eps08': ('08', 1.4, 'on', 0.25, 0.08, '0.000992'),
    'cell_09_a18_eps0': ('09', 1.8, 'on', 0.25, 0.00, '0.000752'),
    'cell_10_a18_eps08': ('10', 1.8, 'on', 0.25, 0.08, '0.000756'),
    'cell_11_b_noise015': ('11', 0.6, 'on', 0.15, 0.08, '0.001700'),
    'cell_12_b_noise040': ('12', 0.6, 'on', 0.40, 0.08, '0.001558'),
    'cell_13_b_noise060': ('13', 0.6, 'on', 0.60, 0.08, '0.001443'),
    'cell_14_corner_14_040': ('14', 1.4, 'on', 0.40, 0.08, '0.000950'),
    'cell_15_corner_18_060': ('15', 1.8, 'on', 0.60, 0.08, '0.000648'),
    'cell_16_a02_eps08': ('16', 0.2, 'on', 0.25, 0.08, '0.001700'),
    'cell_17_a04_eps08': ('17', 0.4, 'on', 0.25, 0.08, '0.001700'),
}
LADDER = [('control', 'cell_02_control_eps08'), ('0.2', 'cell_16_a02_eps08'), ('0.4', 'cell_17_a04_eps08'),
          ('0.6', 'cell_04_a06_eps08'), ('1.0', 'cell_06_a10_eps08'), ('1.4', 'cell_08_a14_eps08'),
          ('1.8', 'cell_10_a18_eps08')]

def load_grid(reward):
    """Concatenate the grid20 and grid5 aggregates of one reward."""
    out = defaultdict(list)
    for proto in ('grid20', 'grid5'):
        d = R / proto / f'aggregate_{reward}'
        if not d.exists():
            continue
        for name in ('error_summary', 'estimates_by_run', 'selection_by_run', 'reference_values_by_run',
                     'rarity_and_cohort_by_run', 'reference_gaps_by_run'):
            p = d / f'{name}.csv'
            if p.exists():
                out[name] += rows(p)
    return out

summary = {}
for reward in ('score', 'cash'):
    g = load_grid(reward)
    if not g:
        continue
    suf = '' if reward == 'score' else '_cash'
    err = {(r['cond'], r['estimator'], r['target']): r for r in g['error_summary'] if r['regime'] == 'tabular'}
    # Table 17: configurations, hazards, runs, realized recovery, reference scores and their SE
    ref = defaultdict(list)
    for r in g['reference_values_by_run']:
        ref[(r['cond'], r['candidate'])].append((fnum(r['mean']), fnum(r['se_within'])))
    rar = defaultdict(list)
    for r in g['rarity_and_cohort_by_run']:
        rar[r['cond']].append(fnum(r['recovery_12m']))
    data = []
    for cond, (cid, a, coup, sig, eps, tau) in GRID.items():
        if (cond, 'pi_b') not in ref:
            continue
        n = len(ref[(cond, 'pi_b')])
        rec = 100 * statistics.mean(rar[cond]) if rar[cond] else float('nan')
        vals = [statistics.mean(m for m, _ in ref[(cond, c)]) for c in ('pi_b', 'pi_far', 'pi_near')]
        semax = max(s for c in ('pi_b', 'pi_far', 'pi_near') for _, s in ref[(cond, c)])
        data.append([cid, f'{a:.1f}', coup, f'{sig:.2f}', f'{eps:.2f}', tau, str(n), f'{rec:.2f}',
                     f'{vals[0]:.1f}', f'{vals[1]:.1f}', f'{vals[2]:.1f}', f'{semax:.2f}'])
    table('grid_values' + suf, 'Parameter configurations, realized recovery and policy reference ' +
          ('scores.' if reward == 'score' else 'cash values.'), 'tab:gridvalues' + suf, 'crcrrrrrrrrr',
          ['cell', r'$\alpha$', 'coupling', r'$\sigma$', r'$\varepsilon$', r'$\tau$', 'runs',
           'recovery (\\%)', 'behavior', POL['pi_far'], POL['pi_near'], 'max ref. SE'], data, True)
    # Table 6: confounding ladder
    def e(cond, est, tgt):
        r = err.get((cond, est, tgt))
        if r is None or r['n_defined'] in ('0', '', None):
            return '--'
        return pm(fnum(r['mean_error']), fnum(r['se_mean_error']))
    data = [[lab] + [e(c, m, 'pi_far') for m in ('dr', 'pilot_is', 'pilot_dr')]
            + [e(c, m, 'pi_near') for m in ('dr', 'pilot_is', 'pilot_dr')] for lab, c in LADDER]
    table('grid_frontier' + suf, 'Mean errors across confounding strengths' + ('.' if reward == 'score' else ' under cash.'),
          'tab:frontier' + suf, 'lrrrrrr',
          [r'$\alpha$', 'DR', 'pilot-IS', 'pilot-DR', 'DR', 'pilot-IS', 'pilot-DR'], data, True, prehead=[r'& \multicolumn{3}{c}{$\pi_{\mathrm{visit}}$} & \multicolumn{3}{c}{$\pi_{\mathrm{sms}}$} \\', r'\cmidrule(lr){2-4}\cmidrule(lr){5-7}'])
    # Table 5: negative control (cell 02)
    c = 'cell_02_control_eps08'
    def fam_range(tgt):
        ms = [fnum(err[(c, m, tgt)]['mean_error']) for m in LOGFAM]
        ses = [fnum(err[(c, m, tgt)]['se_mean_error']) for m in LOGFAM]
        return f"${min(ms):+.1f}$ to ${max(ms):+.1f}$ ($\\pm {max(ses):.1f}$)"
    data = [['log-based five (range of means)', fam_range('pi_far'), fam_range('pi_near')]]
    for m, n in (('dm_blind', 'DM (context-blind)'), ('pilot_is', 'pilot-IS'), ('pilot_dr', 'pilot-DR')):
        data.append([n, e(c, m, 'pi_far'), e(c, m, 'pi_near')])
    table('grid_control' + suf, 'Mean estimator errors in the negative control' + ('.' if reward == 'score' else ' under cash.'),
          'tab:control' + suf, 'lrr', ['estimator', POL['pi_far'], POL['pi_near']], data)
    # Tables 9 and 10: containment pooled over the eps = 0.08 cells, and in the control
    eps08 = [c for c, v in GRID.items() if v[4] > 0]
    byrun = [r for r in g['estimates_by_run'] if r['regime'] == 'tabular' and r['cond'] in eps08]
    def cont(conds, est, tgt):
        sel = [r for r in byrun if r['cond'] in conds and r['estimator'] == est and r['target'] == tgt
               and r['contains_reference'] not in ('', 'None')]
        if not sel:
            return '--', '--', 0
        frac = sum(r['contains_reference'] == 'True' for r in sel) / len(sel)
        w = statistics.mean(fnum(r['ci_width']) for r in sel)
        return f'{frac:.3f}', f'{w:.1f}', len(sel)
    data = []
    for m, n in EST:
        fv, wv, nv = cont(eps08, m, 'pi_far'); fs, ws, ns = cont(eps08, m, 'pi_near')
        data.append([n if m != 'dm' else 'DM (fixed model)', fv, wv, fs, ws])
    n165 = cont(eps08, 'dr', 'pi_far')[2]
    table('grid_coverage' + suf, 'Reference containment and interval width' + ('.' if reward == 'score' else ' under cash.'),
          'tab:coverage' + suf, 'lrrrr', ['estimator', 'fraction', 'mean width', 'fraction', 'mean width'], data, prehead=[r'& \multicolumn{2}{c}{$\pi_{\mathrm{visit}}$} & \multicolumn{2}{c}{$\pi_{\mathrm{sms}}$} \\', r'\cmidrule(lr){2-3}\cmidrule(lr){4-5}'])
    data = []
    for tgt in ('pi_far', 'pi_near'):
        for m, n in (('dm', 'DM (fixed model)'), ('dm_refit', 'DM refit'), ('dr', 'DR'), ('pilot_is', 'pilot-IS')):
            f, w, k = cont([c], m, tgt)
            data.append([POL[tgt], n, f, w])
    table('grid_control_intervals' + suf, 'Intervals in the negative control' + ('.' if reward == 'score' else ' under cash.'),
          'tab:controlintervals' + suf, 'llrr', ['target', 'estimator', 'fraction', 'mean width'], data)
    # Table 12 and 18: selection over the eps = 0.08 runs and per cell
    sel = [r for r in g['selection_by_run'] if r['regime'] == 'tabular']
    ref_best = {r['ref_best'] for r in sel}
    data = []
    for m, n in EST:
        s = [r for r in sel if r['estimator'] == m and r['cond'] in eps08 and r['defined'] == 'True']
        if not s:
            continue
        correct = sum(r['correct'] == 'True' for r in s)
        data.append([n, f'{correct} / {len(s)}', f'{100 * correct / len(s):.1f}',
                     f'{statistics.mean(fnum(r["regret"]) for r in s):.2f}'])
    table('grid_selection' + suf, 'Policy selection in the parameter grid' + ('.' if reward == 'score' else ' under cash.'),
          'tab:selection' + suf, 'lrrr', ['estimator', 'correct / runs', 'percent', 'mean regret'], data)
    data = []
    for cond, (cid, *_) in GRID.items():
        line = [cid]
        for m, _ in EST:
            s = [r for r in sel if r['estimator'] == m and r['cond'] == cond]
            if not s or all(r['defined'] != 'True' for r in s):
                line.append('--'); continue
            s = [r for r in s if r['defined'] == 'True']
            line.append(f"{sum(r['correct'] == 'True' for r in s)} ({statistics.mean(fnum(r['regret']) for r in s):.2f})")
        if len(line) > 1 and any(x != '--' for x in line[1:]):
            data.append(line)
    table('grid_cell_selection' + suf, 'Policy selection by parameter configuration' + ('.' if reward == 'score' else ' under cash.'),
          'tab:cellselection' + suf, 'crrrrrrrr', ['cell'] + [n.replace('DM (context-blind)', 'DM-blind').replace('DR (cross-fitted)', 'DR') for _, n in EST], data, True)
    summary[f'grid_{reward}'] = {'runs_eps08': n165, 'ref_best': sorted(ref_best),
                                 'cells': len(data)}
    # Figure 2 data (score only)
    if reward == 'score' and not args.skip_figure:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            plt.rcParams.update({'pdf.fonttype': 42, 'ps.fonttype': 42, 'font.size': 9})
            style = {'dr': dict(color='#0072B2', marker='s', ls='-', label='log-based family (DM·IS·SNIPS·DR·DM⁺-IS)'),
                     'dm_blind': dict(color='#999999', marker='x', ls=':', label='DM (context-blind)'),
                     'pilot_is': dict(color='#D55E00', marker='D', ls='-', label='pilot-IS'),
                     'pilot_dr': dict(color='#CC79A7', marker='v', ls='--', label='pilot-DR')}
            fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
            x = list(range(len(LADDER)))
            for ax, tgt, title in zip(axes, ('pi_far', 'pi_near'), (r'target $\pi_{\mathrm{visit}}$', r'target $\pi_{\mathrm{sms}}$')):
                for m, st in style.items():
                    ys = [fnum(err[(c, m, tgt)]['mean_error']) for _, c in LADDER]
                    es = [fnum(err[(c, m, tgt)]['se_mean_error']) for _, c in LADDER]
                    ax.errorbar(x, ys, yerr=es, capsize=2, ms=4, lw=1.2, **st)
                ax.axhline(0, color='k', lw=0.6)
                ax.set_xticks(x); ax.set_xticklabels([lab for lab, _ in LADDER])
                ax.set_title(title); ax.set_xlabel('hidden confounding strength')
                ax.grid(alpha=0.3)
            axes[0].set_ylabel('mean error (US$, ± one SE)')
            h, l = axes[0].get_legend_handles_labels()
            fig.legend(h, l, loc='lower center', ncol=4, frameon=False, bbox_to_anchor=(0.5, -0.08), fontsize=7.5)
            fig.tight_layout()
            FIG.mkdir(exist_ok=True)
            fig.savefig(FIG / 'fig_confounding_frontier.pdf', bbox_inches='tight')
            fig.savefig(FIG / 'fig_confounding_frontier.png', dpi=200, bbox_inches='tight')
            plt.close(fig)
            summary['figure2'] = 'rendered'
        except Exception as ex:  # matplotlib missing or data incomplete
            summary['figure2'] = f'not rendered: {ex}'

# ---------------------------------------------------------------- paired study under cash
conds = ['A_off', 'A_on', 'B_off', 'B_on']
def cl(c):
    world, state = c.split('_')
    return '$' + world + r'_{\mathrm{' + state + '}}$'
P = R / 'paired'
for reward in ('score', 'cash'):
    d = P / f'aggregate_{reward}'
    if not d.exists():
        continue
    suf = '_rerun' if reward == 'score' else '_cash'
    err = {(r['cond'], r['regime'], r['estimator'], r['target']): r for r in rows(d / 'error_summary.csv')}
    ref = rows(d / 'reference_values_by_run.csv'); gaps = rows(d / 'reference_gaps_by_run.csv')
    sel = rows(d / 'selection_summary.csv'); si = {(r['cond'], r['regime'], r['estimator']): r for r in sel}
    ir = rows(d / 'interval_diagnostic.csv'); ii = {(r['cond'], r['target'], r['interval']): r for r in ir}
    def er(c, reg, m, p):
        r = err[(c, reg, m, p)]
        return pm(fnum(r['mean_error']), fnum(r['se_mean_error']))
    data = [[cl(c)] + [f"{statistics.mean(fnum(r['mean']) for r in ref if r['cond'] == c and r['candidate'] == p):.1f}" for p in POL] for c in conds]
    table('campaign_values' + suf, 'Policy reference ' + ('scores' if reward == 'score' else 'cash values') + ' by condition.',
          'tab:campaignvalues' + suf, 'lrrrr', ['condition'] + list(POL.values()), data)
    models = [('tabular', 'dr', 'tabular DR'), ('nontabular', 'dm', 'boosted DM'), ('nontabular', 'is', 'boosted IS'),
              ('nontabular', 'snips', 'boosted SNIPS'), ('nontabular', 'dr', 'boosted DR'),
              ('tabular', 'pilot_is', 'pilot-IS'), ('tabular', 'pilot_dr', 'tabular pilot-DR')]
    for tgt, tname in (('pi_far', 'visit'), ('pi_near', 'sms'), ('pi_stage', 'stage')):
        table(f'campaign_{tname}' + suf, f'{POL[tgt]} errors by condition' + ('.' if reward == 'score' else ' under cash.'),
              f'tab:campaign{tname}' + suf, 'lrrrr', ['estimator'] + [cl(c) for c in conds],
              [[name] + [er(c, reg, m, tgt) for c in conds] for reg, m, name in models], True)
    smodels = [('tabular', 'dr'), ('nontabular', 'dr'), ('tabular', 'pilot_is'), ('tabular', 'pilot_dr')]
    def best_label(raw):
        """selection_summary.ref_best is a JSON count of reference-best candidates per run."""
        try:
            counts = json.loads(raw)
        except Exception:
            return POL.get(raw, raw)
        total = sum(counts.values())
        win, n = max(counts.items(), key=lambda kv: kv[1])
        return POL.get(win, win) + ('' if n == total else f' ({n}/{total})')
    sdata = []
    for c in conds:
        line = [cl(c), best_label(si[(c, 'tabular', 'dr')]['ref_best'])]
        for reg, m in smodels:
            r = si[(c, reg, m)]
            line.append(f"{r['correct_all']}/{r['n_runs']} (${fnum(r['mean_regret']):.1f} \\pm {fnum(r['se_mean_regret']):.1f}$)")
        sdata.append(line)
    table('campaign_selection' + suf, 'Policy selection in the paired study' + ('.' if reward == 'score' else ' under cash.'),
          'tab:campaignselection' + suf, 'llrrrr', ['condition', 'reference best', 'tabular DR', 'boosted DR', 'pilot-IS', 'pilot-DR'], sdata, True)
    idata = []
    for c, p in [(c, p) for c in conds for p in ['pi_far', 'pi_near', 'pi_stage']]:
        line = [cl(c), POL[p]]
        for m in ['dm', 'dm_refit', 'dr', 'pilot_is']:
            r = ii.get((c, p, m))
            line.append('--' if r is None else f"{r['contains']}/{r['n_seeds']} ({fnum(r['mean_width']):.1f})")
        idata.append(line)
    table('campaign_intervals' + suf, 'Interval containment and width in the paired study' + ('.' if reward == 'score' else ' under cash.'),
          'tab:campaignintervals' + suf, 'llrrrr', ['condition', 'target', 'DM (fixed model)', 'DM refit', 'DR', 'pilot-IS'], idata, True)
    for c in conds:
        allm = [('tabular', m, n) for m, n in [('dm', 'DM'), ('dm_blind', 'DM, context-blind'), ('is', 'IS'), ('snips', 'SNIPS'), ('dr', 'DR'), ('dm_plus_is', r'DM\textsuperscript{+}-IS'), ('pilot_is', 'pilot-IS'), ('pilot_dr', 'pilot-DR')]] + \
               [('nontabular', m, n) for m, n in [('dm', 'DM'), ('is', 'IS'), ('snips', 'SNIPS'), ('dr', 'DR'), ('pilot_dr', 'pilot-DR')]]
        body = [[('tabular' if reg == 'tabular' else 'boosted'), n] + [er(c, reg, m, p) for p in ['pi_far', 'pi_near', 'pi_stage']] for reg, m, n in allm]
        table('full_errors_' + c + suf, 'Estimator errors in condition ' + cl(c) + ('.' if reward == 'score' else ' under cash.'),
              'tab:campaignfullerrors' + c + suf, 'llrrr', ['regime', 'estimator', POL['pi_far'], POL['pi_near'], POL['pi_stage']], body, True)
    summary[f'paired_{reward}'] = {
        'reference_value_se_max': max(fnum(r['se_within']) for r in ref),
        'reference_gap_se_max': max(fnum(r['se_within']) for r in gaps),
        'ref_best': sorted({r['ref_best'] for r in sel}),
        'runs': len({(r['cond'], r['seed']) for r in ref})}

# ---------------------------------------------------------------- annotated direct method (paired study)
dmp = P / 'dm_plus' / 'dm_plus_summary.csv'
if dmp.exists():
    dd = {(r['cond'], r['target'], r['reward'], r['annotator'], r['estimator']): r for r in rows(dmp)}
    cols = [('none', 'dm', 'DM, logs only'), ('exact', 'dm_plus_xfit', r'DM\textsuperscript{+}, exact'),
            ('protocol', 'dm_plus_xfit', r'DM\textsuperscript{+}, corrupted'),
            ('protocol', 'dm_plus_is_xfit', r'DM\textsuperscript{+}-IS, corrupted')]
    data = [[cl(c)] + [pm(fnum(dd[(c, 'pi_far', 'score', a, e)]['mean_error']),
                         fnum(dd[(c, 'pi_far', 'score', a, e)]['se_mean_error'])) for a, e, _ in cols] for c in conds]
    table('dm_plus', 'Annotated estimators for the field-visit policy.', 'tab:dmplus', 'lrrrr',
          ['condition'] + [n for _, _, n in cols], data, True)
    ex = [r for k, r in dd.items() if k[3] == 'exact' and k[4] == 'dm_plus_xfit']
    pr = [r for k, r in dd.items() if k[3] == 'protocol' and k[4] == 'dm_plus_xfit']
    summary['dm_plus'] = {'exact_error_range': [min(fnum(r['mean_error']) for r in ex), max(fnum(r['mean_error']) for r in ex)],
                          'protocol_error_range': [min(fnum(r['mean_error']) for r in pr), max(fnum(r['mean_error']) for r in pr)]}

(S / 'rerun_render_summary.json').write_text(json.dumps(summary, indent=1) + '\n')
print(json.dumps(summary, indent=1))
