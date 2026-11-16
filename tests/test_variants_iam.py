
"""Property-based checks for the authorisation model (cci.iam).

(1) Each buggy variant is a controlled perturbation: on randomly generated scenarios in which the
    variant's trigger condition is absent, its decision equals the reference decision (negative control).
(2) Each variant is reachable: some generated scenario with the trigger present changes the decision
    (positive control).
Run: python -m pytest tests  (or python tests/test_variants_iam.py)
"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cci.iam import Stmt, Request, PolicySet, evaluate, VARIANTS, _applies

ACTS = ['s:Get', 's:Put', 's:Del', 'c:Start']
APAT = ['s:*', 's:Get', 's:Del', 'c:*', '*', 's:Put']
RES = ['b/x', 'b/k/y', 'b', 'c/z']
RPAT = ['b/*', 'b', '*', 'b/k/*', 'c/*', 'c/z']

def rstmt(rng, rp=False, eff=None):
    return Stmt(eff or rng.choice(['Allow', 'Allow', 'Deny']), rng.sample(APAT, rng.randint(1, 2)),
                rng.sample(RPAT, rng.randint(1, 2)), principals=(rng.choice([['role/R'], ['acct:111'], ['*'], ['acct:999']]) if rp else None))

def scenario(rng):
    ps = PolicySet(identity=[rstmt(rng) for _ in range(rng.randint(0, 3))],
                   resource=[rstmt(rng, rp=True) for _ in range(rng.randint(0, 2))],
                   boundary=([rstmt(rng, eff='Allow') for _ in range(rng.randint(1, 2))] if rng.random() < 0.35 else None),
                   guardrail=([rstmt(rng, eff='Allow') for _ in range(rng.randint(1, 2))] + ([rstmt(rng, eff='Deny')] if rng.random() < 0.2 else []) if rng.random() < 0.35 else None),
                   creator=([rstmt(rng, eff='Allow')] if rng.random() < 0.3 else None))
    req = Request('role/R', '111', rng.choice(ACTS), rng.choice(RES), rng.choice(['111', '111', '222']), same_org=rng.random() < 0.5)
    return ps, req

def facts(ps, req):
    A = lambda L, rp=False: [s for s in (L or []) if s.effect == 'Allow' and _applies(s, req, rp)]
    D = lambda L, rp=False: [s for s in (L or []) if s.effect == 'Deny' and _applies(s, req, rp)]
    f = dict(idA=A(ps.identity), idD=D(ps.identity), rsA=A(ps.resource, True), rsD=D(ps.resource, True),
             bA=A(ps.boundary), bD=D(ps.boundary), gA=A(ps.guardrail), gD=D(ps.guardrail),
             same=req.principal_account == req.resource_account)
    f['deny'] = bool(f['idD'] or f['rsD'] or f['bD'] or f['gD'])
    f['gcap'] = ps.guardrail is not None and not f['gA']
    f['id_ok'] = bool(f['idA']) and (ps.boundary is None or bool(f['bA'])) and not f['gcap']
    return f

def appl_differs(ps, req, model):
    for L, rp in ((ps.identity, False), (ps.resource, True), (ps.boundary or [], False), (ps.guardrail or [], False)):
        for s in L:
            if _applies(s, req, rp) != _applies(s, req, rp, model): return True
    return False

def trigger(model, ps, req):
    f = facts(ps, req); ref = evaluate(ps, req)
    if model == 'IAM-1':   return f['deny'] and bool(f['idA'] or f['rsA'])
    if model == 'IAM-2':   return ref[0] == 'DENY' and ref[1] != 'explicit_deny'
    if model == 'IAM-2org':return (not f['same']) and req.same_org
    if model == 'IAM-3':   return not f['same']
    if model == 'IAM-3i':  return f['same'] and bool(f['rsA'])
    if model == 'IAM-3r':  return f['same'] and f['id_ok']
    if model == 'IAM-4c':  return bool(ps.creator) and any(_applies(s, req) for s in ps.creator)
    if model in ('IAM-5', 'IAM-5w'): return appl_differs(ps, req, model)
    if model == 'IAM-5x':  return (not f['same']) and bool(f['idA'] or f['idD'])
    if model == 'IAM-6a':  return bool(f['bA'] or f['gA']) and not f['idA']
    if model == 'IAM-6b':  return f['gcap'] or (ps.boundary is not None and bool(f['idA']) and not f['bA'])
    if model == 'IAM-6c':  return ps.boundary is not None and bool(f['bA']) != bool(f['idA'] and f['bA'])
    if model == 'IAM-7o':
        seen_allow = False
        for s in ps.identity:
            if _applies(s, req):
                if s.effect == 'Allow': seen_allow = True
                elif seen_allow: return True
        return False
    raise KeyError(model)

def run(n=40000, seed=7):
    rng = random.Random(seed); res = {m: [0, 0, 0] for m in VARIANTS}   # [neg checked, neg violations, pos changes]
    viol = {}
    for _ in range(n):
        ps, req = scenario(rng); ref = evaluate(ps, req)[0]
        for m in VARIANTS:
            out = evaluate(ps, req, m)[0]
            if trigger(m, ps, req):
                res[m][2] += out != ref
            else:
                res[m][0] += 1
                if out != ref:
                    res[m][1] += 1; viol.setdefault(m, (ps, req, ref, out))
    return res, viol

def test_iam_variants_are_controlled():
    res, viol = run()
    for m, (neg, bad, pos) in res.items():
        assert bad == 0, (m, viol.get(m))
        assert pos > 0, ('variant never changes a decision', m)

if __name__ == '__main__':
    res, viol = run()
    for m, r in res.items(): print(m, 'neg_checked=%d violations=%d trigger_changes=%d' % tuple(r))
    sys.exit(1 if any(r[1] or not r[2] for r in res.values()) else 0)
