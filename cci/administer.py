
"""Deterministic machine-administration pipeline (form rendering, request construction, response parsing).

render(seed, stems, items, preamble) shuffles item order and the four options with numpy's default_rng(seed),
exactly as in the archived Rounds 1-3; parse() maps 'Q<n>: <letter>' lines back to canonical option labels.
reproduce_archive() re-renders every archived form from its seed and re-parses the raw outputs; it is used by
tests/test_archive.py to show that data/machine_respondents/responses_api_all_rounds.csv follows from the raw files."""
import re, json
import numpy as np
LET = "ABCD"
WITHHELD = "(question text withheld; choose the option most likely to be correct)"
INSTR = ("You are taking a multiple-choice conceptual test on cloud computing. No tools are available. Answer every question. "
         "Reply with exactly one line per question in the form Q<number>: <letter>, for example Q1: B. Do not add explanations.\n\n")
ADAPTIVE = ('claude-sonnet-5-5', 'claude-opus-5-5')   # the platform rejects thinking='disabled' for these models

def render(seed, stems, items, preamble):
    rng = np.random.default_rng(seed)
    order = list(rng.permutation(len(items)))
    lines = [preamble, ""]; qmap = {}
    for qi, ix in enumerate(order, 1):
        it = items[ix]; perm = list(rng.permutation(4))
        opts = [it['options'][p] for p in perm]
        qmap[f"Q{qi}"] = (it['id'], {LET[j]: opts[j]['label'] for j in range(4)})
        lines.append(f"Q{qi}. " + (it['stem'] if stems else WITHHELD))
        for j, o in enumerate(opts): lines.append(f"  {LET[j]}. {o['text']}")
        lines.append("")
    return "\n".join(lines), qmap

def request(model, seed, stems, items, preamble, max_tokens=800):
    txt, qmap = render(seed, stems, items, preamble)
    if model in ADAPTIVE:
        return {"prompt": INSTR + txt, "model": model, "max_tokens": 16000}, qmap
    return {"prompt": INSTR + txt, "model": model, "max_tokens": max_tokens, "thinking": {"type": "disabled"}}, qmap

def parse(text):
    return dict(re.findall(r"Q(\d+)\s*[:.\-]\s*\(?([ABCD])\b", text or ''))

def score(records, qmaps, items):
    """records: raw dicts (model, cond, seed, thinking, text); qmaps: matching list of qmap."""
    ib = {it['id']: it for it in items}; rows = []
    for k, (mt, qmap) in enumerate(zip(records, qmaps)):
        ans = parse(mt.get('text'))
        for q, (iid, lmap) in qmap.items():
            a = ans.get(q[1:]); canon = lmap.get(a) if a else None
            key = [op['label'] for op in ib[iid]['options'] if op['code'] == 'KEY'][0]
            opt = [op for op in ib[iid]['options'] if op['label'] == canon]
            rows.append(dict(adm=k, model=mt['model'], cond=mt['cond'], seed=mt['seed'], thinking=mt.get('thinking'), item=iid, shown=a,
                             choice=canon, correct=(canon == key) if canon else None, code=opt[0]['code'] if opt else None))
    return rows

def reproduce_archive(banks_path, raw_path, bank_key):
    B = json.load(open(banks_path, encoding='utf-8'))
    items = B[bank_key]; pre = B['PREAMBLE']
    recs = [json.loads(l) for l in open(raw_path, encoding='utf-8')]
    qmaps = [render(int(r['seed']), r['cond'] == 'full', items, pre)[1] for r in recs]
    return score(recs, qmaps, items)
