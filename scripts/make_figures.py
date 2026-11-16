
"""Draw Figures 1-4 from released data and build/numbers.json. Run from the package root after make_numbers.py:
python scripts/make_figures.py"""
import os, sys, json, numpy as np, pandas as pd, matplotlib as mpl
mpl.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Patch, FancyBboxPatch, FancyArrowPatch
from scipy.stats import beta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); os.chdir(ROOT)
exec(open('scripts/figstyle_helpers.py').read())
apply_figure_style(sizes=(8, 7, 6))
os.makedirs('build/figs', exist_ok=True)
NUM = json.load(open('build/numbers.json' if os.path.exists('build/numbers.json') else 'data/numbers.json', encoding='utf-8'))
def bbox_check(fig):
    fig.canvas.draw(); r = fig.canvas.get_renderer()
    T = [(t, t.get_window_extent(r)) for t in fig.findobj(mpl.text.Text) if t.get_text().strip() and t.get_visible()]
    ov = [(a.get_text()[:25], b.get_text()[:25]) for i, (a, ba) in enumerate(T) for b, bb in T[i + 1:] if ba.overlaps(bb)]
    fb = fig.bbox; outb = [t.get_text()[:25] for t, bt in T if bt.x0 < fb.x0 - 1 or bt.x1 > fb.x1 + 1 or bt.y0 < fb.y0 - 1 or bt.y1 > fb.y1 + 1]
    return ov, outb
def save(fig, name):
    print(name, bbox_check(fig)); fig.savefig(f'build/figs/{name}.pdf', bbox_inches='tight'); fig.savefig(f'build/figs/{name}.png', dpi=300, bbox_inches='tight'); plt.close(fig)
cp = lambda k, n, a=0.05: (beta.ppf(a / 2, k, n - k + 1) if k > 0 else 0.0, beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0)
# ------------------------------------------------------------------ Figure 1
fig, ax = plt.subplots(figsize=(7.0, 3.4)); ax.set_xlim(0, 100); ax.set_ylim(0, 48); ax.axis('off')
def box(x, y, w, h, title, body, fc):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=fc, ec='0.3', lw=0.7))
    ax.text(x + 1, y + h - 1.6, title, fontsize=7, weight='bold', va='top'); ax.text(x + 1, y + h - 5.6, body, fontsize=6, va='top', linespacing=1.25)
box(1, 27, 30, 19, "1  Machine-coded corpus", f"{NUM['NQall']} Q&A questions from three\nStack Exchange sites; {NUM['NQacc']}\naccepted-answer threads coded by\ntwo LLMs and a blinded adjudicator;\nfull-text audit of {NUM['AuditN']} threads", '#deebf7')
box(35, 27, 30, 19, "2  Reference & buggy models", f"Authorisation, reachability, DNS,\nhealth checks, scaling, caching,\nreplication, cost, responsibility;\n{NUM['NBugsFour']} single-rule buggy variants\n({NUM['NVarUsedTested']} isolation-tested); {NUM['NConformance']} conformance\ncases", '#e5f5e0')
box(69, 27, 30, 19, "3  Oracle-backed items", f"Key = reference-model output;\ndistractors = buggy-model outputs;\nassumption contract per item;\neach item has a twin that keys\nanother option ({NUM['NItemsFour']} items)", '#fee6ce')
box(1, 2, 46, 19, "4  Machine cue audit (Rounds 1-4)", f"Six commercial models, full and stem-withheld\nforms; Rounds 1-3 guided revision; Round 4\npre-specified, constant panel, three banks\n({NUM['NAdmAll']} + {NUM['NAdmFour']} administrations); small open-weight\nmodels as a floor reference", '#efedf5')
box(53, 2, 46, 19, "5  Human validation: Stages A-C (proposed)", "Blind expert key review (Delphi);\niterative cognitive interviews;\nmulti-institution 2PL calibration with purified\nDIF screening, sized by simulation", '#f0f0f0')
for (x1, y1, x2, y2) in [(31.5, 36.5, 34.5, 36.5), (65.5, 36.5, 68.5, 36.5), (47.5, 11.5, 52.5, 11.5)]:
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=8, lw=0.8, color='0.25'))
ax.add_patch(FancyArrowPatch((78, 26.6), (38, 21.6), arrowstyle='<|-|>', mutation_scale=8, lw=0.8, color='0.25'))
ax.text(36, 24.6, 'draft, audit, revise (4 rounds)', fontsize=6, color='0.25', ha='right')
save(fig, 'fig1_pipeline')
# ------------------------------------------------------------------ Figure 2
F = pd.read_csv('data/final_codes.csv'); C = F[F.conceptual == 'Y']
DOMC = {'NET': '#1f77b4', 'IAM': '#d62728', 'LB': '#9467bd', 'ELA': '#2ca02c', 'CAC': '#ff7f0e', 'CST': '#8c564b', 'SHR': '#7f7f7f'}
DOMN = {'NET': 'Network reachability', 'IAM': 'Identity & access', 'LB': 'Load balancing', 'ELA': 'Elasticity & state', 'CAC': 'Caching & consistency', 'CST': 'Cost', 'SHR': 'Shared responsibility'}
order = ['NET', 'IAM', 'LB', 'ELA', 'CAC', 'CST', 'SHR']
untargeted = set(x.strip() for x in NUM['Untargeted'].split(','))
cc = C[C.code != 'NEW'].code.value_counts()
codes = sorted(cc.index, key=lambda c: (order.index(c.split('-')[0]), -cc[c])); y = np.arange(len(codes))[::-1]
fig = plt.figure(figsize=(7.0, 4.8)); gs = fig.add_gridspec(1, 2, width_ratios=[1.45, 1], wspace=0.38)
ax = fig.add_subplot(gs[0])
for yi, c in zip(y, codes):
    d = c.split('-')[0]; t = c not in untargeted
    ax.barh(yi, cc[c], color=DOMC[d] if t else 'white', edgecolor=DOMC[d], lw=1.0, height=0.72)
    ax.text(cc[c] + 0.8, yi, str(cc[c]), va='center', fontsize=6)
ax.set_yticks(y); ax.set_yticklabels(codes, fontsize=6); ax.set_xlim(0, cc.max() * 1.15); ax.set_ylim(-0.8, len(codes) - 0.2)
ax.set_xlabel('Conceptual threads assigned the code'); ax.set_title('Networking codes are the most frequent', loc='left')
ax.legend(handles=[Patch(facecolor='white', edgecolor='k', label='Code not targeted by any item')], frameon=False, loc='lower right', fontsize=6)
panel_letter(ax, 'a')
ax2 = fig.add_subplot(gs[1]); AU = json.load(open('data/corpus_audit/audit_results.json'))['c_HT_estimates']['F']
yy = np.arange(len(order))[::-1]
for yi, d in zip(yy, order):
    fin = int((C.domain == d).sum()); est = AU[d]['est']; lo, hi = AU[d]['ci95']
    ax2.barh(yi + 0.18, fin, height=0.34, color=DOMC[d], edgecolor=DOMC[d])
    ax2.barh(yi - 0.18, est, height=0.34, color='white', edgecolor=DOMC[d], hatch='////', lw=0.8)
    ax2.errorbar(est, yi - 0.18, xerr=[[est - lo], [hi - est]], fmt='none', ecolor='0.2', lw=0.7, capsize=1.5)
ax2.set_yticks(yy); ax2.set_yticklabels([DOMN[d] for d in order], fontsize=6); ax2.set_xlabel('Conceptual threads'); ax2.set_xlim(0, 340)
ax2.set_title('Audit total exceeds final coding', loc='left')
ax2.legend(handles=[Patch(facecolor='0.45', label='Final machine coding'), Patch(facecolor='white', edgecolor='0.3', hatch='////', label='Full-text audit estimate (95% CI)')], frameon=False, loc='lower right', fontsize=6)
panel_letter(ax2, 'b')
save(fig, 'fig2_taxonomy')
# ------------------------------------------------------------------ Figure 3
R4 = pd.read_csv('data/machine_respondents/responses_r4_audit.csv')
MLAB = {'claude-haiku-4-5-20251001': 'Haiku 4.5', 'claude-haiku-5-5': 'Haiku 5.5', 'claude-sonnet-4-5-20250929': 'Sonnet 4.5', 'claude-sonnet-5-5': 'Sonnet 5.5', 'claude-opus-4-5-20251101': 'Opus 4.5', 'claude-opus-5-5': 'Opus 5.5'}
MCOL = {'Haiku 4.5': '#9ecae1', 'Haiku 5.5': '#3182bd', 'Sonnet 4.5': '#a1d99b', 'Sonnet 5.5': '#31a354', 'Opus 4.5': '#fdae6b', 'Opus 5.5': '#e6550d'}
fig = plt.figure(figsize=(7.0, 5.4)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1.25, 1], hspace=0.62, wspace=0.28)
ax = fig.add_subplot(gs[0, 0])
for j, (bank, tag) in enumerate([('R1', 'SWone'), ('R3', 'SWthree'), ('R4', 'SWfour')]):
    d = R4[(R4.bank == bank) & (R4.cond == 'optonly') & R4.choice.notna()]
    g = d.groupby('model').correct.agg(['mean', 'size'])
    for i, m in enumerate(MLAB):
        if m in g.index and g.loc[m, 'size'] >= 30:
            ax.scatter(j + (i - 2.5) * 0.06, g.loc[m, 'mean'], s=6 + g.loc[m, 'size'] / 8, color=MCOL[MLAB[m]], edgecolor='k', lw=0.3, zorder=3)
    est, lo, hi = float(NUM[tag]), float(NUM[tag + 'Lo']), float(NUM[tag + 'Hi'])
    ax.errorbar(j + 0.3, est, yerr=[[est - lo], [hi - est]], fmt='D', color='k', ms=4, capsize=2, zorder=4)
ax.axhline(0.25, color='0.5', ls='--', lw=0.8); ax.axhline(0.35, color='0.5', ls=':', lw=0.8)
ax.text(-0.42, 0.205, 'chance', fontsize=6, color='0.4', ha='left'); ax.text(-0.42, 0.37, 'pre-specified margin', fontsize=6, color='0.4', ha='left')
ax.set_xticks([0, 1, 2]); ax.set_xticklabels(['Round-1 bank\n(reasoned options)', 'Round-3 bank', 'Draft form\n(Round 4)'])
ax.set_xlim(-0.45, 2.6); ax.set_ylim(0, 1.02); ax.set_ylabel('Stem-withheld accuracy')
ax.set_title('Options alone still beat chance on the draft form', loc='left')
ax.legend(handles=[plt.Line2D([], [], marker='o', ls='', color=MCOL[MLAB[m]], markeredgecolor='k', mew=0.3, label=MLAB[m]) for m in MLAB] +
          [plt.Line2D([], [], marker='D', ls='', color='k', label='Pooled, 95% CI')], frameon=False, fontsize=6, loc='upper right', ncol=2, columnspacing=0.8, handletextpad=0.3)
panel_letter(ax, 'a')
axc = fig.add_subplot(gs[0, 1])
f4 = R4[(R4.bank == 'R4') & (R4.cond == 'full') & R4.choice.notna()]
ms = list(MLAB)
for i, m in enumerate(ms):
    g = f4[f4.model == m]; k = int(g.correct.astype(bool).sum()); n = len(g); lo, hi = cp(k, n)
    axc.errorbar(i, k / n, yerr=[[k / n - lo], [hi - k / n]], fmt='o', color=MCOL[MLAB[m]], mec='k', mew=0.3, ms=5, capsize=2, ecolor='0.3', lw=0.7)
axc.axhline(0.25, color='0.5', ls='--', lw=0.8)
axc.set_xticks(range(len(ms))); axc.set_xticklabels([MLAB[m].replace(' ', '\n') for m in ms], fontsize=6); axc.set_ylim(0, 1.06); axc.set_xlim(-0.5, 5.5)
axc.set_ylabel('Full-form accuracy'); axc.set_title('Capable models answer nearly all items', loc='left')
panel_letter(axc, 'b')
axb = fig.add_subplot(gs[1, :])
A4 = json.load(open('data/machine_respondents/audit_r4_results.json'))
IT = pd.DataFrame(A4['primary']['items_R4_sw'])
if os.path.exists('data/banks.json'):
    BK = json.load(open('data/banks.json', encoding='utf-8')); two = {it['id'] for it in BK['R4'] if it['options'][0]['text'].startswith('Both')}
else:
    two = set(json.load(open('data/two_case_ids_r4.json', encoding='utf-8')))
IT = IT.sort_values(['acc', 'item'], ascending=[False, True]).reset_index(drop=True)
for x, r in IT.iterrows():
    lo, hi = cp(int(r['correct']), int(r['n'])); c = DOMC[r['domain']]; mk = 'o' if r['item'] in two else 's'
    axb.plot([x, x], [lo, hi], color='0.7', lw=0.7, zorder=1)
    axb.scatter(x, r['acc'], marker=mk, s=18, color=c if r['flag'] else 'white', edgecolor=c, lw=0.9, zorder=3)
axb.axhline(0.25, color='0.5', ls='--', lw=0.8)
axb.set_xticks(range(len(IT))); axb.set_xticklabels(IT['item'], rotation=90, fontsize=5.5); axb.set_xlim(-0.8, len(IT) - 0.2); axb.set_ylim(-0.04, 1.04)
axb.set_ylabel('Stem-withheld accuracy'); axb.set_title(f"{NUM['NFlagFour']} of {len(IT)} draft items are flagged as answerable from their options", loc='left')
axb.legend(handles=[plt.Line2D([], [], marker='o', ls='', mfc='0.4', mec='0.4', label='Two-case item, flagged'), plt.Line2D([], [], marker='s', ls='', mfc='0.4', mec='0.4', label='Single-outcome item, flagged'),
                    plt.Line2D([], [], marker='o', ls='', mfc='white', mec='0.4', label='Not flagged')], frameon=False, fontsize=6, loc='upper right', ncol=3)
panel_letter(axb, 'c')
save(fig, 'fig3_audit')

# ------------------------------------------------------------------ Figure 4
S = pd.read_csv('data/sim/sim_v2_summary.csv')
sel = lambda c, p, r: S[(S.cond == c) & (S.procedure == p) & (S.rule == r) & (S.N > 0)].sort_values('N')
PROC = [('one', 'sig', 'One-stage, BH only', '#9e9ac8', 'o', '--'), ('pur', 'sig', 'Purified, BH only', '#6a51a3', 's', '-.'), ('pur', 'es4', 'Purified, BH + effect size >= 0.4 logit', '#e6550d', 'D', '-')]
fig = plt.figure(figsize=(7.0, 4.9)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=0.62, wspace=0.42)
axp, axf = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])
for p, r, lab, col, mk, ls in PROC:
    d = sel('M', p, r)
    axp.errorbar(d.N, d.power, yerr=2 * d.power_se, color=col, marker=mk, ms=3.5, ls=ls, lw=1, capsize=1.5, label=lab)
    axf.errorbar(d.N, d.fdr, yerr=2 * d.fdr_se, color=col, marker=mk, ms=3.5, ls=ls, lw=1, capsize=1.5)
axp.axhline(0.8, color='0.5', ls=':', lw=0.8); axp.text(310, 0.82, 'power 0.80', fontsize=6, color='0.4')
axf.axhline(0.05, color='0.5', ls=':', lw=0.8); axf.text(625, 0.0445, 'FDR 0.05', fontsize=6, color='0.4', ha='center')
for a in (axp, axf): a.set_xticks([300, 500, 750, 1000]); a.set_xlabel('Students per site (three sites)'); a.set_xlim(250, 1050)
axp.set_ylim(0, 1.0); axp.set_ylabel('Per-item power'); axp.set_title('Purified screens gain power', loc='left')
axf.set_ylim(0, 0.1); axf.set_ylabel('False-discovery rate'); axf.set_title('One-stage screens exceed the nominal FDR', loc='left')
axp.legend(frameon=False, fontsize=6, loc='lower right')
panel_letter(axp, 'a'); panel_letter(axf, 'b')
axs = fig.add_subplot(gs[1, :])
lab = {'M': 'Main design', 'S3a': 'DIF 0.3', 'S3b': 'DIF 0.7', 'S4a': '2 DIF items', 'S4b': '8 DIF items', 'S2': 'Opposing DIF', 'S1': 'Shift at 2 sites', 'S5a': 'Unequal n',
       'S5b': 'Ability gap 0.5', 'S6': 'Non-uniform DIF', 'S7': 'Testlets', 'S8': '7 domains', 'S9': '28 items', 'S10': 'Subgroup 30%'}
rows = []
for c in lab:
    n = 0 if c == 'S5a' else 750
    d = S[(S.cond == c) & (S.N == n) & (S.procedure == 'pur') & (S.rule == 'es4')].iloc[0]
    rows.append((c, d.power, d.power_se))
rows.sort(key=lambda t: -t[1])
for x, (c, pw, se) in enumerate(rows):
    col = '#e6550d' if c == 'M' else ('#3182bd' if pw >= 0.8 else '0.55')
    axs.errorbar(x, pw, yerr=2 * se, fmt='D' if c == 'M' else 'o', color=col, ms=4, capsize=1.5, lw=0.8)
axs.axhline(0.8, color='0.5', ls=':', lw=0.8)
axs.set_xticks(range(len(rows))); axs.set_xticklabels([lab[c] for c, _, _ in rows], rotation=35, ha='right', fontsize=6)
axs.set_ylim(0, 1.05); axs.set_xlim(-0.6, len(rows) - 0.4); axs.set_ylabel('Per-item power at 750 per site')
axs.set_title('The 750-per-site target is borderline and fails for small or non-uniform DIF', loc='left')
axs.legend(handles=[plt.Line2D([], [], marker='D', ls='', color='#e6550d', label='Main design'), plt.Line2D([], [], marker='o', ls='', color='#3182bd', label='Power at least 0.80'), plt.Line2D([], [], marker='o', ls='', color='0.55', label='Power below 0.80')], frameon=False, fontsize=6, loc='lower left')
panel_letter(axs, 'c')
save(fig, 'fig4_sim')
