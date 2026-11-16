"""Round-4 machine cue audit: scoring and pre-specified analysis (audit_r4_prespec.md, written 2026-11-11).

Run from the package root:  python scripts/audit_r4_code.py
Inputs : data/banks.json, data/machine_respondents/raw_respondents_r4.jsonl (panel outputs), data/machine_respondents/local_scores_r4.jsonl
Outputs: data/machine_respondents/responses_r4_audit.csv, audit_r4_results.json, audit_r4_tables.md
Scoring uses cci.administer.render/score unchanged (qmaps re-rendered from each record's seed).
"""
import json, os, sys, math
import numpy as np, pandas as pd
from scipy.stats import binomtest, beta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
import cci.administer as A

B = json.load(open('data/banks.json', encoding='utf-8'))
PRE = {'R1': B['PREAMBLE'], 'R3': B['PREAMBLE'], 'R4': B['PREAMBLE_R4']}
PANEL = ['claude-haiku-4-5-20251001', 'claude-haiku-5-5', 'claude-sonnet-4-5-20250929', 'claude-sonnet-5-5',
         'claude-opus-4-5-20251101', 'claude-opus-5-5']
NBOOT, NSIM, MARGIN = 2000, 10000, 0.35
# administration whose two parsed 'answers' are the instruction's format example echoed inside a refusal
SPURIOUS = [('claude-sonnet-4-5-20250929', 'R4', 'optonly', 7004)]

# ---------------------------------------------------------------- 1. scoring
recs = [json.loads(l) for l in open('data/machine_respondents/raw_respondents_r4.jsonl', encoding='utf-8')]
rows = []
for k, r in enumerate(recs):
    items = B[r['bank']]
    qmap = A.render(int(r['seed']), r['cond'] == 'full', items, PRE[r['bank']])[1]
    for row in A.score([r], [qmap], items):
        row['adm'] = k; row['bank'] = r['bank']; rows.append(row)
D = pd.DataFrame(rows)[['adm', 'model', 'bank', 'cond', 'seed', 'thinking', 'item', 'shown', 'choice', 'correct', 'code']]
D.to_csv('data/machine_respondents/responses_r4_audit.csv', index=False)
D['answered'] = D['choice'].notna()
D['corr'] = D['correct'].map(lambda x: x is True or x == True)

# token usage
tok = {k: int(sum((r['usage'] or {}).get(k) or 0 for r in recs)) for k in
       ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')}
tok['total'] = sum(tok.values())

# ---------------------------------------------------------------- helpers
def cp(k, n, level=0.95):
    if n == 0: return [None, None]
    a = 1 - level
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return [float(lo), float(hi)]

def adm_table(d):
    g = d.groupby('adm').agg(model=('model', 'first'), bank=('bank', 'first'), cond=('cond', 'first'), seed=('seed', 'first'),
                             sched=('item', 'size'), ans=('answered', 'sum'), cor=('corr', 'sum')).reset_index()
    return g

def estimands(g):
    S, N, C = g['sched'].sum(), g['ans'].sum(), g['cor'].sum()
    return dict(cond_acc=(C / N) if N else np.nan, unans_incorrect=C / S, unans_chance=(C + 0.25 * (S - N)) / S)

def cluster_boot(g, seed=0, nboot=NBOOT):
    """administration-cluster bootstrap; one rng(seed) per call; resamples all administrations in g."""
    rng = np.random.default_rng(seed); n = len(g)
    S, N, C = g['sched'].to_numpy(float), g['ans'].to_numpy(float), g['cor'].to_numpy(float)
    idx = rng.integers(0, n, size=(nboot, n))
    s, a, c = S[idx].sum(1), N[idx].sum(1), C[idx].sum(1)
    out = {}
    with np.errstate(invalid='ignore', divide='ignore'):
        bs = dict(cond_acc=np.where(a > 0, c / a, np.nan), unans_incorrect=c / s, unans_chance=(c + 0.25 * (s - a)) / s)
    for k, v in bs.items():
        v = v[~np.isnan(v)]
        out[k] = dict(ci95=[float(np.quantile(v, .025)), float(np.quantile(v, .975))] if len(v) else [None, None],
                      ci90=[float(np.quantile(v, .05)), float(np.quantile(v, .95))] if len(v) else [None, None],
                      n_valid_resamples=int(len(v)))
    return out

def pooled(g):
    e = estimands(g); bt = cluster_boot(g)
    res = dict(n_adm=int(len(g)), n_answering_adm=int((g['ans'] > 0).sum()), n_declines=int((g['ans'] == 0).sum()),
               scheduled=int(g['sched'].sum()), answered=int(g['ans'].sum()), correct=int(g['cor'].sum()),
               answer_rate=float(g['ans'].sum() / g['sched'].sum()))
    for k in e:
        res[k] = None if (isinstance(e[k], float) and np.isnan(e[k])) else float(e[k])
        res[k + '_boot'] = bt[k]
    return res

def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)
    q = np.empty(m); prev = 1.0
    for rank, i in reversed(list(enumerate(o, 1))):
        prev = min(prev, p[i] * m / rank); q[i] = prev
    return q

def item_flags(d, bank):
    out = []
    for it in B[bank]:
        x = d[(d['item'] == it['id']) & d['answered']]
        n, k = int(len(x)), int(x['corr'].sum())
        p = float(binomtest(k, n, 0.25, alternative='greater').pvalue) if n else 1.0
        out.append(dict(item=it['id'], domain=it['domain'], n=n, correct=k, acc=(k / n if n else None), ci95=cp(k, n), p_one_sided=p))
    q = bh([o['p_one_sided'] for o in out])
    for o, qq in zip(out, q):
        o['q_bh'] = float(qq); o['testable'] = o['n'] >= 10; o['flag'] = bool(o['testable'] and qq < 0.05)
    return out

def distractor_test(d, bank, seed=0, nsim=NSIM):
    """Among wrong answers: observed share on modelled distractors vs uniform choice among the item's 3 non-key options.
    Null simulation keeps each wrong answer's item (and model) fixed and redraws its distractor uniformly; nsim draws."""
    ib = {it['id']: it for it in B[bank]}
    w = d[d['answered'] & ~d['corr']].copy()
    if len(w) == 0: return dict(n_wrong=0)
    w['modelled'] = ~w['code'].isin(['UNMODELLED', 'KEY'])
    pm = w['item'].map(lambda i: sum(o['code'] not in ('KEY', 'UNMODELLED') for o in ib[i]['options']) / 3.0).to_numpy()
    rng = np.random.default_rng(seed)
    obs = float(w['modelled'].mean()); exp = float(pm.mean())
    sims = (rng.random((nsim, len(pm))) < pm).mean(1)
    res = dict(n_wrong=int(len(w)), obs_share_modelled=obs, expected_share=exp, excess=obs - exp,
               null_q025=float(np.quantile(sims, .025)), null_q975=float(np.quantile(sims, .975)),
               p_greater=float((np.sum(sims >= obs - 1e-12) + 1) / (nsim + 1)),
               p_two_sided=float(min(1.0, 2 * min((np.sum(sims >= obs - 1e-12) + 1) / (nsim + 1), (np.sum(sims <= obs + 1e-12) + 1) / (nsim + 1)))),
               degenerate=bool(np.all(pm == 1.0) or np.all(pm == 0.0)))
    per_model = {}
    for m, wm in w.groupby('model'):
        pmm = pm[(w['model'] == m).to_numpy()]
        sm = (np.random.default_rng(seed).random((nsim, len(pmm))) < pmm).mean(1); o = float(wm['modelled'].mean())
        per_model[m] = dict(n_wrong=int(len(wm)), obs=o, expected=float(pmm.mean()),
                            p_greater=float((np.sum(sm >= o - 1e-12) + 1) / (nsim + 1)))
    res['per_model'] = per_model
    return res

# ---------------------------------------------------------------- 2. analysis
R = dict(prespec='audit_r4_prespec.md (2026-11-11)', panel=PANEL, tokens=tok,
         n_requests=len(recs), n_errors=sum(r['error'] is not None for r in recs),
         resolved=sorted(set(str(r['resolved']) for r in recs)), stop_reasons=pd.Series([r['stop'] for r in recs]).value_counts().to_dict())
G = adm_table(D)

def answer_rates(G):
    out = []
    for (m, b, c), g in G.groupby(['model', 'bank', 'cond']):
        out.append(dict(model=m, bank=b, cond=c, n_adm=int(len(g)), declines=int((g['ans'] == 0).sum()),
                        answering_adm=int((g['ans'] > 0).sum()), scheduled=int(g['sched'].sum()), answered=int(g['ans'].sum()),
                        answer_rate=float(g['ans'].sum() / g['sched'].sum()), answered_per_adm=g['ans'].astype(int).tolist()))
    return out
R['answer_rates'] = answer_rates(G)

def run_main(G, D, tag):
    out = {}
    out['pooled'] = {f'{b}_{c}': pooled(G[(G.bank == b) & (G.cond == c)]) for b, c in [('R1', 'optonly'), ('R3', 'optonly'), ('R4', 'optonly'), ('R4', 'full')]}
    pr = out['pooled']['R4_optonly']
    ub = pr['cond_acc_boot']['ci90'][1]
    out['criterion1'] = dict(estimate=pr['cond_acc'], ci90_upper=ub, margin=MARGIN,
                             verdict=('acceptable' if (ub is not None and ub <= MARGIN) else 'not met'))
    # per-model SW (all banks) + criterion 2 on R4
    pm = []
    for b in ['R1', 'R3', 'R4']:
        for m in PANEL:
            g = G[(G.bank == b) & (G.cond == 'optonly') & (G.model == m)]
            k, n = int(g['cor'].sum()), int(g['ans'].sum()); na = int((g['ans'] > 0).sum())
            row = dict(model=m, bank=b, answering_adm=na, answered=n, correct=k, acc=(k / n if n else None),
                       cp95=cp(k, n, .95), cp90=cp(k, n, .90), answer_rate=float(n / g['sched'].sum()))
            if b == 'R4':
                if na >= 3:
                    bt = cluster_boot(g)['cond_acc']
                    row['boot90'] = bt['ci90']; row['boot95'] = bt['ci95']
                    row['criterion2'] = 'acceptable' if bt['ci90'][1] <= MARGIN else 'not met'
                    row['criterion2_cp90_check'] = 'acceptable' if row['cp90'][1] <= MARGIN else 'not met'
                else:
                    row['criterion2'] = 'not assessable'
            pm.append(row)
    out['per_model_sw'] = pm
    out['items_R4_sw'] = item_flags(D[(D.bank == 'R4') & (D.cond == 'optonly')], 'R4')
    out['flagged_R4'] = [o['item'] for o in out['items_R4_sw'] if o['flag']]
    out['n_testable_R4'] = int(sum(o['testable'] for o in out['items_R4_sw']))
    # matched stage comparison (models answering in all three SW banks), model-cluster bootstrap
    acc = {(r['model'], r['bank']): r['acc'] for r in pm}
    ms = [m for m in PANEL if all(acc[(m, b)] is not None for b in ['R1', 'R3', 'R4'])]
    mc = dict(models=ms)
    for a in ['R1', 'R3']:
        dif = np.array([acc[(m, a)] - acc[(m, 'R4')] for m in ms])
        if len(ms):
            rng = np.random.default_rng(0); bsm = dif[rng.integers(0, len(ms), size=(NBOOT, len(ms)))].mean(1)
            mc[f'{a}_minus_R4'] = dict(per_model=dict(zip(ms, dif.tolist())), mean=float(dif.mean()),
                                       ci95=[float(np.quantile(bsm, .025)), float(np.quantile(bsm, .975))],
                                       ci90=[float(np.quantile(bsm, .05)), float(np.quantile(bsm, .95))])
    out['matched'] = mc
    return out

R['primary'] = run_main(G, D, 'primary')
# full form per model (R4)
ff = []
for m in PANEL:
    g = G[(G.bank == 'R4') & (G.cond == 'full') & (G.model == m)]
    k, n = int(g['cor'].sum()), int(g['ans'].sum())
    ff.append(dict(model=m, answered=n, scheduled=int(g['sched'].sum()), correct=k, acc=(k / n if n else None), cp95=cp(k, n),
                   per_adm_correct=g['cor'].astype(int).tolist()))
R['full_form_per_model'] = ff
R['items_R4_full'] = [dict(item=o['item'], n=o['n'], correct=o['correct'], acc=o['acc'])
                      for o in item_flags(D[(D.bank == 'R4') & (D.cond == 'full')], 'R4')]
# secondary descriptive item flags on R1/R3 SW (same rule; BH within each bank)
R['items_secondary'] = {b: [o for o in item_flags(D[(D.bank == b) & (D.cond == 'optonly')], b) if o['flag']] for b in ['R1', 'R3']}
# distractor choice among errors
R['distractors'] = {'R4_full': distractor_test(D[(D.bank == 'R4') & (D.cond == 'full')], 'R4'),
                    'R4_optonly': distractor_test(D[(D.bank == 'R4') & (D.cond == 'optonly')], 'R4'),
                    'R3_optonly': distractor_test(D[(D.bank == 'R3') & (D.cond == 'optonly')], 'R3'),
                    'R1_optonly': distractor_test(D[(D.bank == 'R1') & (D.cond == 'optonly')], 'R1')}
# sensitivity: treat the spurious-parse administration as a decline (not pre-specified; disclosed)
D2 = D.copy()
for (m, b, c, s) in SPURIOUS:
    msk = (D2.model == m) & (D2.bank == b) & (D2.cond == c) & (D2.seed == s)
    D2.loc[msk, ['answered', 'corr']] = False
R['sensitivity_spurious_parse_as_decline'] = dict(admins=[list(x) for x in SPURIOUS], **{k: v for k, v in run_main(adm_table(D2), D2, 'sens').items()
                                                  if k in ('pooled', 'criterion1', 'flagged_R4', 'matched')})
R['sensitivity_spurious_parse_as_decline']['per_model_R4'] = [r for r in run_main(adm_table(D2), D2, 's')['per_model_sw'] if r['bank'] == 'R4']

# ---------------------------------------------------------------- 3. local open-weight models
LP = 'data/machine_respondents/local_scores_r4.jsonl'
if os.path.exists(LP):
    L = pd.DataFrame([json.loads(l) for l in open(LP)])
    L['pkey'] = [p[k] for p, k in zip(L['probs'], L['key'])]
    L['argmax_correct'] = [max(p, key=p.get) == k for p, k in zip(L['probs'], L['key'])]
    loc = []
    for (m, c), g in L.groupby(['model', 'cond']):
        rng = np.random.default_rng(0); v = g['pkey'].to_numpy(); bs = v[rng.integers(0, len(v), size=(NBOOT, len(v)))].mean(1)
        loc.append(dict(model=m, cond=c, n_items=int(len(g)), mean_pkey=float(v.mean()),
                        item_boot95=[float(np.quantile(bs, .025)), float(np.quantile(bs, .975))],
                        argmax_acc=float(g['argmax_correct'].mean()), n_items_pkey_gt_0_5=int((v > 0.5).sum())))
    R['local'] = loc
else:
    R['local'] = None

json.dump(R, open('data/machine_respondents/audit_r4_results.json', 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))

# ---------------------------------------------------------------- 4. tables
f = lambda x, d=3: '' if x is None else f'{x:.{d}f}'
ci = lambda c: '' if c is None or c[0] is None else f'[{c[0]:.3f}, {c[1]:.3f}]'
T = ['# Round-4 machine cue audit: tables', '', f"Requests: {R['n_requests']} (errors {R['n_errors']}); host.llm tokens: {tok}", '']
P = R['primary']
T += ['## 1. Pooled estimates (administration-cluster bootstrap, 2,000 resamples, seed 0)', '',
      '| Bank/cond | adm | declines | answer rate | answered | cond. acc | 95% CI | 90% CI | unanswered=incorrect [95% CI] | unanswered=0.25 [95% CI] |',
      '|---|---|---|---|---|---|---|---|---|---|']
for k, p in P['pooled'].items():
    T.append(f"| {k} | {p['n_adm']} | {p['n_declines']} | {f(p['answer_rate'])} | {p['answered']}/{p['scheduled']} | {f(p['cond_acc'])} | "
             f"{ci(p['cond_acc_boot']['ci95'])} | {ci(p['cond_acc_boot']['ci90'])} | {f(p['unans_incorrect'])} {ci(p['unans_incorrect_boot']['ci95'])} | "
             f"{f(p['unans_chance'])} {ci(p['unans_chance_boot']['ci95'])} |")
c1 = P['criterion1']
T += ['', f"**Criterion 1 (R4 SW):** conditional accuracy {f(c1['estimate'])}, 90% upper bound {f(c1['ci90_upper'])} vs margin 0.35 -> **{c1['verdict']}**.", '']
T += ['## 2. Answer rates by model x bank x condition', '', '| Model | Bank | Cond | declines/adm | answer rate | answered per adm |', '|---|---|---|---|---|---|']
for r in R['answer_rates']:
    T.append(f"| {r['model']} | {r['bank']} | {r['cond']} | {r['declines']}/{r['n_adm']} | {f(r['answer_rate'])} | {r['answered_per_adm']} |")
T += ['', '## 3. Per-model stem-withheld accuracy (exact Clopper-Pearson intervals; criterion 2 on R4 uses the per-model cluster bootstrap 90% upper bound)', '',
      '| Model | Bank | answering adm | correct/answered | acc | CP 95% | CP 90% | boot 90% | criterion 2 |', '|---|---|---|---|---|---|---|---|---|']
for r in P['per_model_sw']:
    T.append(f"| {r['model']} | {r['bank']} | {r['answering_adm']} | {r['correct']}/{r['answered']} | {f(r['acc'])} | {ci(r['cp95'])} | {ci(r['cp90'])} | "
             f"{ci(r.get('boot90'))} | {r.get('criterion2', '')} |")
T += ['', '## 4. R4 item-level residual-cue screen (SW; one-sided exact binomial vs 0.25; BH over 36 items; flag needs q<0.05 and n>=10)', '',
      f"Testable items (n>=10): {P['n_testable_R4']}/36. Flagged: {P['flagged_R4'] or 'none'}.", '',
      '| Item | n | correct | acc | CP 95% | p | q (BH) | flag |', '|---|---|---|---|---|---|---|---|']
for o in sorted(P['items_R4_sw'], key=lambda o: o['p_one_sided']):
    T.append(f"| {o['item']} | {o['n']} | {o['correct']} | {f(o['acc'])} | {ci(o['ci95'])} | {f(o['p_one_sided'], 4)} | {f(o['q_bh'], 4)} | {'FLAG' if o['flag'] else ('' if o['testable'] else 'n<10')} |")
M = P['matched']
T += ['', '## 5. Matched stage comparison (SW; models answering all three banks; model-cluster bootstrap)', '', f"Models: {M['models']}", '']
for a in ['R1', 'R3']:
    if f'{a}_minus_R4' in M:
        x = M[f'{a}_minus_R4']
        T.append(f"- {a} - R4: mean {f(x['mean'])}, 95% {ci(x['ci95'])}, 90% {ci(x['ci90'])}; per model " + ', '.join(f'{k}: {v:+.3f}' for k, v in x['per_model'].items()))
T += ['', '## 6. R4 full form per model (descriptive; tool-free exposure, not difficulty evidence)', '', '| Model | correct/answered | acc | CP 95% | per-adm correct |', '|---|---|---|---|---|']
for r in R['full_form_per_model']:
    T.append(f"| {r['model']} | {r['correct']}/{r['answered']} (of {r['scheduled']}) | {f(r['acc'])} | {ci(r['cp95'])} | {r['per_adm_correct']} |")
T += ['', '## 7. Distractor choice among errors (uniform-choice null preserving item and model counts; 10,000 draws, seed 0)', '',
      '| Form | wrong answers | observed share modelled | expected | null 95% range | p (greater) | p (two-sided) |', '|---|---|---|---|---|---|---|']
for k, x in R['distractors'].items():
    if x.get('n_wrong'):
        T.append(f"| {k}{' (degenerate: all distractors modelled)' if x['degenerate'] else ''} | {x['n_wrong']} | {f(x['obs_share_modelled'])} | {f(x['expected_share'])} | "
                 f"[{f(x['null_q025'])}, {f(x['null_q975'])}] | {f(x['p_greater'], 4)} | {f(x['p_two_sided'], 4)} |")
    else:
        T.append(f"| {k} | 0 | | | | | |")
T += ['', 'Per model (full form R4): ' + '; '.join(f"{m}: {v['obs']:.2f} vs {v['expected']:.2f} (n={v['n_wrong']}, p={v['p_greater']:.3f})"
                                              for m, v in R['distractors']['R4_full'].get('per_model', {}).items())]
S = R['sensitivity_spurious_parse_as_decline']
T += ['', '## 8. Sensitivity (not pre-specified): spurious parse treated as a decline', '',
      f"claude-sonnet-4-5 R4 SW seed 7004 refused but echoed the instruction's format example ('Q1: B, Q2: C'), which the unchanged parser scores as 2 answers.",
      f"R4 SW conditional accuracy {f(S['pooled']['R4_optonly']['cond_acc'])}, 90% CI {ci(S['pooled']['R4_optonly']['cond_acc_boot']['ci90'])}; criterion 1: {S['criterion1']['verdict']}; flagged: {S['flagged_R4'] or 'none'}."]
if R['local']:
    T += ['', '## 9. Local open-weight models, R4 (key probability averaged over four cyclic rotations)', '',
          '| Model | Cond | items | mean P(key) | item-bootstrap 95% | argmax acc | items P(key)>0.5 |', '|---|---|---|---|---|---|---|']
    for r in R['local']:
        T.append(f"| {r['model']} | {r['cond']} | {r['n_items']} | {f(r['mean_pkey'])} | {ci(r['item_boot95'])} | {f(r['argmax_acc'])} | {r['n_items_pkey_gt_0_5']} |")
open('data/machine_respondents/audit_r4_tables.md', 'w', encoding='utf-8').write('\n'.join(T) + '\n')
print(json.dumps(dict(criterion1=c1, flagged=P['flagged_R4'], tokens=tok['total']), default=str))
