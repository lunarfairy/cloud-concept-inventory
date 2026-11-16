"""audit_code.py - LLM-based sensitivity audit of the CCI misconception corpus.

Stages (run in order; each writes to OUT):
  1. agreement()      -> agreement_tables.csv (A vs B, final vs A/B; no new coding)
  2. draw_sample()    -> sample_frame.csv (stratified sample, seed, inclusion probabilities)
  3. fetch_full()     -> se_full.jsonl (WORKSPACE ONLY, never published: full bodies)
  4. recode()         -> audit_raw.jsonl (claude-opus-5, thinking disabled; T and F conditions)
  5. analyse()        -> audit_sample.csv, audit_results.json
No human coders exist for this audit; the reference is a stronger LLM configuration, not a gold standard.
"""
import os, re, json, html, hashlib, time, urllib.request, urllib.parse, gzip
import numpy as np, pandas as pd

DATA = os.environ.get('CCI_DATA', 'data/')
OUT = os.environ.get('CCI_OUT', 'data/corpus_audit/')
CODING_INPUT = os.environ.get('CCI_CODING_INPUT', 'coding_input.jsonl')
os.makedirs(OUT, exist_ok=True)
SEED = 20261111
DOMAINS = ['SHR', 'IAM', 'NET', 'LB', 'ELA', 'CAC', 'CST', 'NONE']


# ---------------------------------------------------------------- labels
def load_labels():
    fc = pd.read_csv(DATA + 'final_codes.csv', keep_default_na=False)
    A = pd.read_csv(DATA + 'coding_coderA.csv', keep_default_na=False)
    B = pd.read_csv(DATA + 'coding_coderB.csv', keep_default_na=False)
    m = fc[['cid', 'pid', 'site', 'qid', 'conceptual', 'domain', 'code', 'newlabel', 'source']].rename(
        columns={'conceptual': 'F_c', 'domain': 'F_d', 'code': 'F_code', 'newlabel': 'F_new'})
    for X, p in ((A, 'A'), (B, 'B')):
        m = m.merge(X[['cid', 'conceptual', 'domain', 'code', 'status']].rename(columns={
            'conceptual': p + '_c', 'domain': p + '_d', 'code': p + '_code', 'status': p + '_status'}), on='cid')
    for p in 'ABF':  # anything that is not a valid Y/N is treated as missing
        m.loc[~m[p + '_c'].isin(['Y', 'N']), p + '_c'] = ''

    def stratum(r):
        if r.A_c == '' or r.B_c == '':
            return 'out-of-frame'
        return {('Y', 'Y'): 'both-Y', ('N', 'N'): 'both-N', ('Y', 'N'): 'A-only-Y', ('N', 'Y'): 'B-only-Y'}[(r.A_c, r.B_c)]
    m['stratum'] = m.apply(stratum, axis=1)
    return m


# ---------------------------------------------------------------- agreement statistics
def binary_stats(x, y, pos='Y'):
    """x, y: arrays of 'Y'/'N'. Returns confusion counts, observed agreement, Cohen kappa, PABAK, Gwet AC1."""
    x = np.asarray(x) == pos; y = np.asarray(y) == pos; n = len(x)
    a = int((x & y).sum()); b = int((x & ~y).sum()); c = int((~x & y).sum()); d = int((~x & ~y).sum())
    po = (a + d) / n
    p1, p2 = (a + b) / n, (a + c) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    pi = (p1 + p2) / 2
    pe_g = 2 * pi * (1 - pi)
    ac1 = (po - pe_g) / (1 - pe_g)
    return dict(n=n, YY=a, YN=b, NY=c, NN=d, po=po, kappa=kappa, pabak=2 * po - 1, ac1=ac1,
                pos_agree=2 * a / (2 * a + b + c) if (2 * a + b + c) else float('nan'),
                neg_agree=2 * d / (2 * d + b + c) if (2 * d + b + c) else float('nan'),
                mcnemar_b=b, mcnemar_c=c, mcnemar_p=mcnemar_exact(b, c))


def nominal_stats(x, y):
    """Multi-category agreement: po, Cohen kappa, Gwet AC1 (Gwet 2008 multi-category form)."""
    x = np.asarray(x, dtype=object); y = np.asarray(y, dtype=object); n = len(x)
    cats = sorted(set(x) | set(y)); q = len(cats)
    po = float((x == y).mean())
    px = np.array([(x == k).mean() for k in cats]); py = np.array([(y == k).mean() for k in cats])
    pe = float((px * py).sum())
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    pik = (px + py) / 2
    pe_g = float((pik * (1 - pik)).sum() / (q - 1)) if q > 1 else 0.0
    ac1 = (po - pe_g) / (1 - pe_g) if pe_g < 1 else float('nan')
    return dict(n=n, n_categories=q, po=po, kappa=kappa, ac1=ac1)


def mcnemar_exact(b, c):
    from scipy.stats import binomtest
    return float(binomtest(b, b + c, 0.5).pvalue) if b + c > 0 else 1.0


def agreement(m=None):
    m = load_labels() if m is None else m
    rows = []

    def add(section, comparison, stat, value, n=None, note=''):
        rows.append(dict(section=section, comparison=comparison, statistic=stat, value=value, n=n, note=note))
    # (1) conceptual Y/N A vs B
    v = m[(m.A_c != '') & (m.B_c != '')]
    s = binary_stats(v.A_c, v.B_c)
    for k in ['YY', 'YN', 'NY', 'NN']:
        add('conceptual_confusion', 'A(rows) vs B(cols)', 'A=%s,B=%s' % (k[0], k[1]), s[k], s['n'],
            'coder A = claude-sonnet-5, coder B = claude-haiku-5-5')
    for k in ['po', 'kappa', 'pabak', 'ac1', 'pos_agree', 'neg_agree', 'mcnemar_p']:
        add('conceptual_agreement', 'A vs B', k, s[k], s['n'])
    add('conceptual_prevalence', 'A', 'share_Y', (v.A_c == 'Y').mean(), len(v))
    add('conceptual_prevalence', 'B', 'share_Y', (v.B_c == 'Y').mean(), len(v))
    # (2) final vs each coder
    for p, nm in (('A', 'coder A'), ('B', 'coder B')):
        w = m[(m.F_c != '') & (m[p + '_c'] != '')]
        s = binary_stats(w.F_c, w[p + '_c'])
        for k in ['YY', 'YN', 'NY', 'NN']:
            add('final_vs_coder_confusion', 'final(rows) vs %s(cols)' % nm, 'F=%s,%s=%s' % (k[0], p, k[1]), s[k], s['n'])
        for k in ['po', 'kappa', 'pabak', 'ac1', 'pos_agree', 'neg_agree', 'mcnemar_p']:
            add('final_vs_coder_agreement', 'final vs %s' % nm, k, s[k], s['n'],
                'all threads with a valid final label and a valid %s label' % nm)
        # full-label (conceptual|domain|code) exact agreement
        lab = lambda d, q: d[q + '_c'] + '|' + d[q + '_d'] + '|' + d[q + '_code']
        add('final_vs_coder_agreement', 'final vs %s' % nm, 'exact_label_agreement', float((lab(w, 'F') == lab(w, p)).mean()), len(w))
    add('final_prevalence', 'final', 'n_Y', int((m.F_c == 'Y').sum()), int((m.F_c != '').sum()))
    # (3) domain and code confusion among both-Y
    by = m[m.stratum == 'both-Y']
    s = nominal_stats(by.A_d, by.B_d)
    for k in ['po', 'kappa', 'ac1']:
        add('bothY_domain_agreement', 'A vs B', k, s[k], s['n'])
    ct = pd.crosstab(by.A_d, by.B_d)
    for a_ in ct.index:
        for b_ in ct.columns:
            if ct.loc[a_, b_]:
                add('bothY_domain_confusion', 'A(rows) vs B(cols)', 'A=%s,B=%s' % (a_, b_), int(ct.loc[a_, b_]), s['n'])
    s = nominal_stats(by.A_code, by.B_code)
    for k in ['po', 'kappa', 'ac1']:
        add('bothY_code_agreement', 'A vs B', k, s[k], s['n'])
    sd = by[by.A_d == by.B_d]
    add('bothY_code_agreement', 'A vs B, same domain only', 'po', float((sd.A_code == sd.B_code).mean()), len(sd))
    cc = by[by.A_code != by.B_code].groupby(['A_code', 'B_code']).size().sort_values(ascending=False)
    for (a_, b_), k in cc.head(25).items():
        add('bothY_code_confusion_top25', 'A vs B (disagreements)', 'A=%s,B=%s' % (a_, b_), int(k), len(by))
    # (4) per-domain agreement (A vs B, domain indicator over all valid threads; Y with domain d vs not)
    for d in DOMAINS[:-1]:
        xa = np.where((v.A_c == 'Y') & (v.A_d == d), 'Y', 'N'); xb = np.where((v.B_c == 'Y') & (v.B_d == d), 'Y', 'N')
        s = binary_stats(xa, xb)
        for k in ['YY', 'YN', 'NY', 'pos_agree', 'kappa', 'ac1']:
            add('per_domain_agreement', 'A vs B, indicator conceptual & domain=%s' % d, k, s[k], s['n'])
        xf = np.where((m.F_c == 'Y') & (m.F_d == d), 'Y', 'N')
        add('per_domain_agreement', 'final count domain=%s' % d, 'n_final', int((xf == 'Y').sum()), int((m.F_c != '').sum()))
    df = pd.DataFrame(rows)
    df.to_csv(OUT + 'agreement_tables.csv', index=False)
    return df


# ---------------------------------------------------------------- stratified sample
STRATUM_N = {'both-Y': 100, 'both-N': 100, 'A-only-Y': 40, 'B-only-Y': 80}
BOTHY_MIN = 8


def draw_sample(m=None, seed=SEED):
    """Stratified simple random sampling without replacement.
    Strata: both-Y (sub-stratified by final domain; final N/INVALID = sub-stratum 'NONE'), both-N, A-only-Y, B-only-Y.
    Within both-Y, every sub-stratum with >=10 threads gets >=8; sub-strata with <10 threads are taken with certainty;
    the remainder is allocated proportionally to (N_h - 8) by largest remainder. The two out-of-frame threads
    (coder A output invalid) are included with certainty so the weighted estimate covers the whole corpus."""
    m = load_labels() if m is None else m
    rng = np.random.default_rng(seed)
    m = m.copy()
    m['substratum'] = m['stratum']
    by = m.stratum == 'both-Y'
    m.loc[by, 'substratum'] = 'both-Y:' + np.where(m.loc[by, 'F_c'] == 'Y', m.loc[by, 'F_d'], 'NONE')
    sizes = m.substratum.value_counts().to_dict()
    alloc = {}
    sub = {k: v for k, v in sizes.items() if k.startswith('both-Y:')}
    certain = {k: v for k, v in sub.items() if v < 10}
    alloc.update(certain)
    rest = {k: v for k, v in sub.items() if v >= 10}
    budget = STRATUM_N['both-Y'] - sum(certain.values()) - BOTHY_MIN * len(rest)
    w = {k: v - BOTHY_MIN for k, v in rest.items()}
    raw = {k: budget * w[k] / sum(w.values()) for k in rest}
    fl = {k: int(np.floor(raw[k])) for k in rest}
    left = budget - sum(fl.values())
    for k in sorted(rest, key=lambda k: -(raw[k] - fl[k]))[:left]:
        fl[k] += 1
    for k in rest:
        alloc[k] = BOTHY_MIN + fl[k]
    for k in ['both-N', 'A-only-Y', 'B-only-Y']:
        alloc[k] = min(STRATUM_N[k], sizes[k])
    alloc['out-of-frame'] = sizes.get('out-of-frame', 0)
    picks = []
    for k in sorted(alloc):
        ids = m.loc[m.substratum == k, 'cid'].sort_values().to_numpy()
        sel = rng.choice(ids, size=alloc[k], replace=False) if alloc[k] < len(ids) else ids
        picks.append(pd.DataFrame({'cid': sel, 'substratum': k, 'N_h': len(ids), 'n_h': alloc[k],
                                   'incl_prob': alloc[k] / len(ids)}))
    s = pd.concat(picks).merge(m, on=['cid', 'substratum'], how='left')
    s['weight'] = 1 / s['incl_prob']
    s = s.sort_values('cid').reset_index(drop=True)
    s.to_csv(OUT + 'sample_frame.csv', index=False)
    meta = dict(seed=seed, allocation=alloc, population=sizes, n=len(s))
    json.dump(meta, open(OUT + 'sample_meta.json', 'w'), indent=1)
    return s, meta


# ---------------------------------------------------------------- full-text fetch (Stack Exchange API 2.3)
def clean(h):
    """Identical to the round-1 harvest cleaner (code blocks kept as [code] ... [/code], first 400 chars each)."""
    h = re.sub(r"<pre[^>]*>(.*?)</pre>", lambda m: " [code] " + m.group(1)[:400] + " [/code] ", h, flags=re.S)
    h = re.sub(r"<[^>]+>", " ", h); h = html.unescape(h); return re.sub(r"\s+", " ", h).strip()


FULL_CAP = 6000
SE_SITE = {'stackoverflow': 'stackoverflow', 'serverfault': 'serverfault', 'security': 'security'}


def se_get(path, ids, site, filt='withbody'):
    out, page = [], 1
    while True:
        u = 'https://api.stackexchange.com/2.3/%s/%s?%s' % (path, ';'.join(map(str, ids)), urllib.parse.urlencode(
            dict(site=SE_SITE[site], filter=filt, pagesize=100, page=page)))
        for attempt in range(4):
            try:
                b = urllib.request.urlopen(u, timeout=60).read()
                try: b = gzip.decompress(b)
                except OSError: pass
                j = json.loads(b); break
            except Exception as e:
                time.sleep(5 * (attempt + 1)); j = None
        if j is None:
            raise RuntimeError('SE API failed: %s' % path)
        out += j['items']
        if j.get('backoff'): time.sleep(j['backoff'] + 1)
        if not j.get('has_more'): return out, j.get('quota_remaining')
        page += 1


def fetch_full(cids=None, path_out=None):
    """Fetches current question and accepted-answer bodies for the given cids (default: whole corpus).
    Full bodies are written to a WORKSPACE-ONLY file (licence/privacy): never publish se_full.jsonl."""
    m = load_labels()
    ci = {json.loads(l)['cid']: json.loads(l) for l in open(CODING_INPUT, encoding='utf-8')}
    m = m if cids is None else m[m.cid.isin(cids)]
    recs = {}
    quota = None
    for site, g in m.groupby('site'):
        qids = g.qid.astype(int).tolist()
        qitems = []
        for i in range(0, len(qids), 100):
            it, quota = se_get('questions', qids[i:i + 100], site); qitems += it; time.sleep(0.5)
        qmap = {q['question_id']: q for q in qitems}
        aids = [q['accepted_answer_id'] for q in qitems if q.get('accepted_answer_id')]
        aitems = []
        for i in range(0, len(aids), 100):
            it, quota = se_get('answers', aids[i:i + 100], site); aitems += it; time.sleep(0.5)
        amap = {a['answer_id']: a for a in aitems}
        for r in g.itertuples():
            q = qmap.get(int(r.qid)); c = ci[r.cid]
            rec = dict(cid=r.cid, site=site, question_id=int(r.qid), q_found=q is not None)
            if q:
                aid = q.get('accepted_answer_id'); a = amap.get(aid) if aid else None
                qt = clean(q.get('body', '')); at = clean(a['body']) if a else ''
                rec.update(answer_id=aid, q_last_edit=q.get('last_edit_date'), a_last_edit=(a or {}).get('last_edit_date'),
                           q_len_full=len(qt), a_len_full=len(at),
                           q_prefix_match=qt[:700] == c['question'], a_prefix_match=at[:500] == c['accepted_answer'],
                           question_full=qt[:FULL_CAP], answer_full=at[:FULL_CAP])
            recs[r.cid] = rec
    out = path_out or (OUT + 'se_full.jsonl')
    with open(out, 'w', encoding='utf-8') as f:
        for k in sorted(recs):
            f.write(json.dumps(recs[k], ensure_ascii=False) + '\n')
    return recs, quota


# ---------------------------------------------------------------- re-coding (claude-opus-5, thinking disabled)
AUDIT_MODEL = 'claude-opus-5'
BATCH = 12


def codebook_codes(cb):
    return sorted(set(re.findall(r'^([A-Z]{2,3}-\d+)\s', cb, flags=re.M)))


def render(cid, title, tags, q, a):
    return '[CID] %s\nTITLE: %s\nTAGS: %s\nQUESTION: %s\nACCEPTED ANSWER: %s' % (cid, title, tags, q, a)


def build_prompt(template, codebook, blocks):
    return template.replace('<<CODEBOOK>>', codebook).replace('<<THREADS>>', '\n\n'.join(blocks))


def parse(text, cids, codes):
    """Same validation rules as round 1 (run_coderA.json)."""
    out = {}
    for line in text.strip().splitlines():
        p = [x.strip() for x in line.strip().split('|')]
        if len(p) != 6 or p[0] not in cids:
            continue
        cid, c, d, code, new, conf = p
        ok = (c in ('Y', 'N') and d in DOMAINS and (code in codes or code in ('NEW', 'NONE')) and conf in ('1', '2', '3')
              and ((c == 'N') == (code == 'NONE'))
              and (code in ('NEW', 'NONE') or code.split('-')[0] == d)
              and (code != 'NEW' or (new not in ('', '-') and len(new.split()) <= 8)))
        out[cid] = dict(conceptual=c, domain=d, code=code, newlabel=new, conf=int(conf) if conf in ('1', '2', '3') else None,
                        status='ok' if ok else 'invalid', line=line.strip())
    return out


def recode(host, sample, full, coding_input, template, codebook, raw_path, seed=SEED, conds=('T', 'F')):
    """Batches are identical in both conditions (same seeded shuffle, so strata are mixed and blinded);
    only the QUESTION/ACCEPTED ANSWER text differs: T = exact coded snippets, F = full cleaned bodies (<=6,000 chars)."""
    codes = codebook_codes(codebook)
    order = list(np.random.default_rng(seed + 1).permutation(sorted(sample)))
    batches = [order[i:i + BATCH] for i in range(0, len(order), BATCH)]
    results, raw = {c: {} for c in conds}, []

    def text_for(cond, cid):
        r = coding_input[cid]
        if cond == 'T':
            return render(cid, r['title'], r['tags'], r['question'], r['accepted_answer'])
        f = full[cid]
        return render(cid, r['title'], r['tags'], f['question_full'], f['answer_full'])

    def run(jobs, phase):
        reqs = [dict(prompt=build_prompt(template, codebook, [text_for(cond, c) for c in b]), model=AUDIT_MODEL,
                     max_tokens=3000, thinking={'type': 'disabled'}) for cond, b in jobs]
        res = host.llm(reqs, max_concurrency=12)
        for (cond, b), rq, rs in zip(jobs, reqs, res):
            parsed = parse(rs.get('text', ''), set(b), codes) if 'error' not in rs else {}
            raw.append(dict(phase=phase, condition=cond, cids=b, prompt_sha256=hashlib.sha256(rq['prompt'].encode('utf-8')).hexdigest(),
                            model_returned=rs.get('model'), usage=rs.get('usage'), stop_reason=rs.get('stop_reason'),
                            error=rs.get('error'), text=rs.get('text')))
            for cid in b:
                if cid in parsed and (parsed[cid]['status'] == 'ok' or cid not in results[cond]
                                      or results[cond][cid]['status'] != 'ok'):
                    results[cond][cid] = dict(parsed[cid], phase=phase)
    run([(c, b) for c in conds for b in batches], 'pass1')
    for attempt in (1, 2):
        retry = [(c, [cid for cid in sample if results[c].get(cid, {}).get('status') != 'ok']) for c in conds]
        retry = [(c, b[i:i + BATCH]) for c, b in retry for i in range(0, len(b), BATCH) if b]
        if not retry:
            break
        run(retry, 'retry%d' % attempt)
    with open(raw_path, 'w', encoding='utf-8') as f:
        for r in raw:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return results, raw


# ---------------------------------------------------------------- analyses
def _final_code_counts():
    fc = pd.read_csv(DATA + 'final_codes.csv', keep_default_na=False)
    return fc[fc.conceptual == 'Y'].code.value_counts().to_dict()


FINAL_CODE_COUNTS = _final_code_counts()
REPORTED_NEW = FINAL_CODE_COUNTS.get('NEW', 0)
REPORTED = dict(conceptual=624, n_valid=1903, NET=203, IAM=112, LB=109, CST=68, ELA=67, CAC=63, SHR=2)
NBOOT = 4000


def build_sample_table(sample, results, full):
    s = sample.rename(columns={'F_c': 'F_c_final', 'F_d': 'F_d_final', 'F_code': 'F_code_final', 'F_new': 'F_new_final'}).copy()
    for cond in ('T', 'F'):
        r = results[cond]
        s[cond + '_c'] = [r[c]['conceptual'] if c in r else '' for c in s.cid]
        s[cond + '_d'] = [(r[c]['domain'] if r[c]['status'] == 'ok' else 'INVALID') if c in r else '' for c in s.cid]
        s[cond + '_code'] = [(r[c]['code'] if r[c]['status'] == 'ok' else 'INVALID') if c in r else '' for c in s.cid]
        s[cond + '_new'] = [r[c]['newlabel'] if c in r else '' for c in s.cid]
        s[cond + '_conf'] = [r[c]['conf'] if c in r else None for c in s.cid]
        s[cond + '_status'] = [r[c]['status'] if c in r else 'missing' for c in s.cid]
    s['answer_id'] = [full[c].get('answer_id') for c in s.cid]
    s['q_len_full'] = [full[c]['q_len_full'] for c in s.cid]
    s['a_len_full'] = [full[c]['a_len_full'] for c in s.cid]
    s['truncated_in_round1'] = (s.q_len_full > 700) | (s.a_len_full > 500)
    s['capped_6000'] = (s.q_len_full > FULL_CAP) | (s.a_len_full > FULL_CAP)
    s['accepted_answer_unchanged'] = [bool(full[c]['a_prefix_match'] and full[c]['q_prefix_match']) for c in s.cid]
    s['edited_after_coding'] = [bool((full[c].get('q_last_edit') or 0) > CODING_DATE_TS or (full[c].get('a_last_edit') or 0) > CODING_DATE_TS)
                                for c in s.cid]
    return s


CODING_DATE_TS = pd.Timestamp('2026-11-04').timestamp()


def raowu_weights(s, B=NBOOT, seed=SEED + 2):
    """Rao-Wu (1988) rescaling bootstrap for stratified SRSWOR (m_h = n_h - 1, lambda_h = sqrt(1 - f_h));
    certainty strata (f_h = 1) get fixed weights. Returns a B x n matrix of replicate weights."""
    rng = np.random.default_rng(seed)
    W = np.tile(s.weight.to_numpy(float), (B, 1))
    for h, g in s.groupby('substratum'):
        idx = g.index.to_numpy(); n = len(idx); f = n / g.N_h.iloc[0]
        if n < 2 or f >= 1:
            continue
        mh = n - 1; lam = np.sqrt(mh * (1 - f) / (n - 1))
        draws = rng.integers(0, n, size=(B, mh))
        r = np.zeros((B, n))
        for j in range(n):
            r[:, j] = (draws == j).sum(1)
        W[:, idx] = g.weight.to_numpy() * (1 - lam + lam * (n / mh) * r)
    return W


def ci(x):
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def analyse(s):
    s = s.reset_index(drop=True)
    res = {}
    # (a) truncation effect T vs F
    tf = s[(s.T_c != '') & (s.F_c != '')]
    a = {}
    for nm, g in (('all', tf), ('truncated_in_round1', tf[tf.truncated_in_round1]), ('not_truncated_identical_input', tf[~tf.truncated_in_round1])):
        st = binary_stats(g.T_c, g.F_c)
        yy = g[(g.T_c == 'Y') & (g.F_c == 'Y')]
        okd = yy[(yy.T_d != 'INVALID') & (yy.F_d != 'INVALID')]
        dom = nominal_stats(okd.T_d, okd.F_d) if len(okd) else {}
        cod = nominal_stats(okd.T_code, okd.F_code) if len(okd) else {}
        full_lab = float(((g.T_c + '|' + g.T_d.where(g.T_c == 'Y', 'NONE') + '|' + g.T_code) ==
                          (g.F_c + '|' + g.F_d.where(g.F_c == 'Y', 'NONE') + '|' + g.F_code)).mean())
        a[nm] = dict(conceptual=st, domain_among_bothY=dom, code_among_bothY=cod, exact_label_agreement=full_lab,
                     n_T_Y=int((g.T_c == 'Y').sum()), n_F_Y=int((g.F_c == 'Y').sum()))
    W = raowu_weights(s)
    w = s.weight.to_numpy(float)
    agreeTF = (s.T_c == s.F_c).to_numpy(float)
    a['weighted_conceptual_agreement'] = dict(est=float((w * agreeTF).sum() / w.sum()), ci95=ci((W * agreeTF).sum(1) / W.sum(1)))
    res['a_truncation_T_vs_F'] = a
    # (b) final labels vs F audit, per stratum and per final domain/code
    b = {'per_stratum': {}, 'per_final_domain': {}, 'per_final_code': {}}
    for nm, g in s.groupby('stratum'):
        b['per_stratum'][nm] = dict(n=len(g), N=int(g.groupby('substratum').N_h.first().sum()),
                                    final_Y=int((g.F_c_final == 'Y').sum()), audit_F_Y=int((g.F_c == 'Y').sum()),
                                    conceptual_agreement=float((g.F_c_final == g.F_c).mean()),
                                    audit_T_Y=int((g.T_c == 'Y').sum()))
    fy = s[s.F_c_final == 'Y']
    for nm, g in fy.groupby('F_d_final'):
        b['per_final_domain'][nm] = dict(n=len(g), audit_Y=int((g.F_c == 'Y').sum()),
                                         audit_same_domain=int(((g.F_c == 'Y') & (g.F_d == nm)).sum()),
                                         audit_same_code=int(((g.F_c == 'Y') & (g.F_code == g.F_code_final)).sum()),
                                         weighted_share_audit_Y=float((g.weight * (g.F_c == 'Y')).sum() / g.weight.sum()))
    for nm, g in fy.groupby('F_code_final'):
        b['per_final_code'][nm] = dict(n=len(g), audit_Y=int((g.F_c == 'Y').sum()),
                                       audit_same_code=int(((g.F_c == 'Y') & (g.F_code == nm)).sum()))
    both = s[(s.F_c_final == 'Y') & (s.F_c == 'Y')]
    b['domain_agreement_final_vs_F_among_bothY'] = dict(nominal_stats(both.F_d_final, both.F_d),
        weighted_po=float((both.weight * (both.F_d_final == both.F_d)).sum() / both.weight.sum()))
    b['code_agreement_final_vs_F_among_bothY'] = dict(nominal_stats(both.F_code_final, both.F_code),
        weighted_po=float((both.weight * (both.F_code_final == both.F_code)).sum() / both.weight.sum()))
    b['conceptual_final_vs_F_unweighted'] = binary_stats(s.F_c_final.where(s.F_c_final == 'Y', 'N'), s.F_c)
    res['b_final_vs_F'] = b
    # (c) Horvitz-Thompson estimates under F (and T for comparison)
    c = {}
    for cond in ('F', 'T'):
        y = (s[cond + '_c'] == 'Y').to_numpy(float)
        est = {'conceptual': dict(est=float((w * y).sum()), ci95=ci((W * y).sum(1)), reported=REPORTED['conceptual'])}
        for d in ['NET', 'IAM', 'LB', 'CST', 'ELA', 'CAC', 'SHR']:
            yd = ((s[cond + '_c'] == 'Y') & (s[cond + '_d'] == d)).to_numpy(float)
            est[d] = dict(est=float((w * yd).sum()), ci95=ci((W * yd).sum(1)), reported=REPORTED[d],
                          share_est=float((w * yd).sum() / (w * y).sum()), share_ci95=ci((W * yd).sum(1) / (W * y).sum(1)),
                          share_reported=REPORTED[d] / REPORTED['conceptual'])
        yn = ((s[cond + '_c'] == 'Y') & (s[cond + '_code'] == 'NEW')).to_numpy(float)
        est['NEW_code'] = dict(est=float((w * yn).sum()), ci95=ci((W * yn).sum(1)), reported=int(REPORTED_NEW))
        est['prevalence'] = dict(est=float((w * y).sum() / w.sum()), ci95=ci((W * y).sum(1) / W.sum(1)),
                                 reported=REPORTED['conceptual'] / REPORTED['n_valid'])
        c[cond] = est
    res['c_HT_estimates'] = c
    res['c_HT_estimates']['note'] = ('Totals over the 1,904-thread corpus (sum of weights = %.1f); the reported 624 is over 1,903 '
                                     'valid final labels (T1575 final INVALID, counted as not conceptual here). CIs: Rao-Wu rescaling '
                                     'bootstrap, %d replicates; they cover sampling variance only, not run-to-run LLM variance.' % (w.sum(), NBOOT))
    # (d) precision / recall of the final 'conceptual' label (and of each coder) against the F audit
    d = {}
    yF = (s.F_c == 'Y').to_numpy(float)
    for nm, col in (('final', 'F_c_final'), ('coderA', 'A_c'), ('coderB', 'B_c')):
        yx = (s[col] == 'Y').to_numpy(float); valid = (s[col].isin(['Y', 'N']) | (nm == 'final')).to_numpy(float)
        tp, tpb = (w * yx * yF * valid).sum(), (W * yx * yF * valid).sum(1)
        d[nm] = dict(precision=float(tp / (w * yx * valid).sum()), precision_ci95=ci(tpb / (W * yx * valid).sum(1)),
                     recall=float(tp / (w * yF * valid).sum()), recall_ci95=ci(tpb / (W * yF * valid).sum(1)),
                     est_TP=float(tp), est_FP=float((w * yx * (1 - yF) * valid).sum()), est_FN=float((w * (1 - yx) * yF * valid).sum()))
        f1 = 2 * tpb / ((W * yx * valid).sum(1) + (W * yF * valid).sum(1))
        d[nm]['F1'] = float(2 * tp / ((w * yx * valid).sum() + (w * yF * valid).sum())); d[nm]['F1_ci95'] = ci(f1)
        agr = (yx == yF).astype(float)
        d[nm]['weighted_agreement'] = float((w * agr * valid).sum() / (w * valid).sum())
    res['d_precision_recall_vs_F'] = d
    # (e) per-code audited frequency vs final
    e = []
    codes = sorted(set(s.F_code[s.F_c == 'Y']) | set(FINAL_CODE_COUNTS))
    for k in codes:
        yk = ((s.F_c == 'Y') & (s.F_code == k)).to_numpy(float)
        e.append(dict(code=k, final_count=int(FINAL_CODE_COUNTS.get(k, 0)), audit_est=float((w * yk).sum()),
                      audit_ci95=ci((W * yk).sum(1)), n_sample_F=int(yk.sum())))
    for r in e:
        r['diff'] = r['audit_est'] - r['final_count']
        r['final_outside_ci'] = not (r['audit_ci95'][0] <= r['final_count'] <= r['audit_ci95'][1])
    e.sort(key=lambda r: -abs(r['diff']))
    res['e_code_frequencies'] = e
    return res



def extra(s, res):
    """Per-stratum HT contributions (F audit vs final labels) and the paired F - T contrast."""
    s = s.reset_index(drop=True)
    W = raowu_weights(s); w = s.weight.to_numpy(float)
    yF = (s.F_c == 'Y').to_numpy(float); yT = (s.T_c == 'Y').to_numpy(float); yfin = (s.F_c_final == 'Y').to_numpy(float)
    contrib = {}
    for h, g in s.groupby('stratum'):
        i = g.index.to_numpy()
        popY = load_labels(); popY = int(((popY.stratum == h) & (popY.F_c == 'Y')).sum())
        contrib[h] = dict(N=int(g.groupby('substratum').N_h.first().sum()), final_Y_in_population=popY,
                          HT_audit_F_Y=float((w[i] * yF[i]).sum()), HT_audit_F_Y_ci95=ci((W[:, i] * yF[i]).sum(1)),
                          HT_final_Y_from_sample=float((w[i] * yfin[i]).sum()))
    d = (W * (yF - yT)).sum(1)
    res['c_stratum_contributions'] = contrib
    res['c_F_minus_T_conceptual_total'] = dict(est=float((w * (yF - yT)).sum()), ci95=ci(d))
    res['c_HT_final_from_sample_check'] = dict(est=float((w * yfin).sum()), ci95=ci((W * yfin).sum(1)), true=624)
    return res



def usage_total(raw):
    keys = ['input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens']
    return {k: int(sum((r.get('usage') or {}).get(k, 0) for r in raw)) for k in keys}


def main(host=None, fetch=False, recode_now=False, prompt_path=DATA + 'prompt_coder.txt', codebook_path=DATA + 'codebook_v1.md',
         full_path='audit/private/se_full.jsonl'):
    """Full pipeline. With fetch=False / recode_now=False it re-uses se_full.jsonl and audit_raw.jsonl
    (re-parsing the raw outputs), so all published numbers can be recomputed without new API calls."""
    m = load_labels()
    agreement(m)
    s, meta = draw_sample(m)
    if fetch:
        fetch_full(None, full_path)
    full = {json.loads(l)['cid']: json.loads(l) for l in open(full_path, encoding='utf-8')}
    ci_ = {json.loads(l)['cid']: json.loads(l) for l in open(CODING_INPUT, encoding='utf-8')}
    template = open(prompt_path, encoding='utf-8').read(); codebook = open(codebook_path, encoding='utf-8').read()
    if recode_now:
        results, raw = recode(host, list(s.cid), full, ci_, template, codebook, OUT + 'audit_raw.jsonl')
    raw = [json.loads(l) for l in open(OUT + 'audit_raw.jsonl', encoding='utf-8')]
    # re-parse raw outputs in the original order (pass1, retry1, retry2); the pilot record is excluded
    codes = codebook_codes(codebook); results = {'T': {}, 'F': {}}
    for r in raw:
        if r['phase'] == 'pilot_excluded':
            continue
        parsed = parse(r.get('text') or '', set(r['cids']), codes)
        for cid, v in parsed.items():
            cur = results[r['condition']].get(cid)
            if cur is None or v['status'] == 'ok' or cur['status'] != 'ok':
                if cur is not None and cur['status'] == 'ok':
                    continue
                results[r['condition']][cid] = dict(v, phase=r['phase'])
    st = build_sample_table(s, results, full)
    res = extra(st, analyse(st))
    return m, s, meta, st, res, raw
