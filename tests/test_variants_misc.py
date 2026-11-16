
"""Property-based checks for cci.misc variants (caching, replication, health checks, scaling, sessions, cost,
shared responsibility): negative and positive controls as in test_variants_iam.py. Run: python -m pytest tests"""
import random, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cci import misc as M
def run(n=4000, seed=5):
    rng = random.Random(seed); res = {}; viol = {}
    def chk(m, trig, a, b):
        r = res.setdefault(m, [0, 0, 0])
        if trig: r[2] += a != b
        else:
            r[0] += 1
            if a != b: r[1] += 1; viol.setdefault(m, (a, b))
    for _ in range(n):
        # CDN
        ma = rng.choice([0, 60, 300, 3600]); sm = rng.choice([None, 30, 600]); kq = rng.random() < 0.5
        ev = [dict(t=0, type='origin_update', path='/p', version='v1'), dict(t=0, type='origin_headers', path='/p', max_age=ma, **({} if sm is None else {'s_maxage': sm}))]
        t = 0; qs = ['', 'a=1', 'a=2']
        for k in range(rng.randint(2, 5)):
            t += rng.choice([1, 20, 100, 700])
            if rng.random() < 0.3: ev.append(dict(t=t, type='origin_update', path='/p', version='v%d' % (k + 2)))
            elif rng.random() < 0.1: ev.append(dict(t=t, type='invalidate', path='/p'))
            else: ev.append(dict(t=t, type='request', path='/p', query=rng.choice(qs)))
        ref = M.cdn_serve(ev, key_includes_query=kq)
        cur = []; o = None
        for e in ev:
            if e['type'] == 'origin_update': o = e['version']
            if e['type'] == 'request': cur.append(o)
        chk('CAC-1', any(r[0] != c for r, c in zip(ref, cur)), M.cdn_serve(ev, 'CAC-1', kq), ref)
        exp = False; seen = {}
        for e in ev:
            if e['type'] == 'invalidate': seen = {}
            if e['type'] == 'request':
                k = (e['path'], e.get('query', '') if kq else ''); ttl = sm if sm is not None else ma
                if k in seen and e['t'] >= seen[k] + ttl: exp = True
                if k not in seen or e['t'] >= seen[k] + ttl: seen[k] = e['t']
        chk('CAC-1n', exp, M.cdn_serve(ev, 'CAC-1n', kq), ref)
        chk('CAC-2', (not kq) and len({e.get('query', '') for e in ev if e['type'] == 'request'}) > 1, M.cdn_serve(ev, 'CAC-2', kq), ref)
        chk('CAC-4', sm is not None and sm != ma, M.cdn_serve(ev, 'CAC-4', kq), ref)
        # replication
        lag = rng.choice([0, 0.2, 2]); tr = rng.choice([0, 0.5, 1.5, 3]); src = rng.choice(['replica', 'primary'])
        r0 = M.replica_read(0, lag, tr, src)
        chk('CAC-3', src == 'replica' and 0 <= tr < lag, M.replica_read(0, lag, tr, src, 'CAC-3'), r0)
        # health checks
        resl = [rng.random() < 0.5 for _ in range(rng.randint(3, 10))]; ut = rng.randint(1, 4); ht = rng.randint(1, 4)
        r0 = M.health_timeline(resl, 10, ut, ht)
        chk('LB-1t', ut > 1 or ht > 1, M.health_timeline(resl, 10, ut, ht, model='LB-1t'), r0)
        code = rng.choice([200, 204, 301, 302, 404, 500, 503]); mt = rng.choice([(200, 200), (200, 399)]); ca = rng.random() < 0.8; li = rng.random() < 0.8
        r0 = M.health_check_passes(code, mt, ca, li)
        chk('LB-1b', li and ((code < 500 and not (mt[0] <= code <= mt[1])) or (code in (301, 302) and not ca)), M.health_check_passes(code, mt, ca, li, model='LB-1b'), r0)
        # scaling
        cu = rng.randint(1, 8); me = rng.choice([20, 40, 60, 80, 95]); tg = rng.choice([40, 50, 60]); mn = rng.randint(1, 3); mx = rng.randint(4, 10)
        r0 = M.target_tracking(cu, me, tg, mn, mx); raw = math.ceil(cu * me / tg)
        chk('ELA-2m', raw > mx, M.target_tracking(cu, me, tg, mn, mx, 'ELA-2m'), r0)
        chk('ELA-2a', r0 != (min(mx, cu + 1) if me > tg else cu), M.target_tracking(cu, me, tg, mn, mx, 'ELA-2a'), r0)
        chk('ELA-2v', r0 != cu, M.target_tracking(cu, me, tg, mn, mx, 'ELA-2v'), r0)
        # sessions
        st = rng.random() < 0.5; store = rng.choice(['local', 'external']); ni = rng.randint(2, 6); nr = rng.randint(1, ni - 1)
        r0 = M.sessions_lost_on_scale_in(ni, nr, 2000, st, store, 1)
        chk('LB-4', st and store == 'local', M.sessions_lost_on_scale_in(ni, nr, 2000, st, store, 1, 'LB-4'), r0)
        # cost
        its = [dict(kind='instance', rate_h=0.1, hours_running=rng.choice([0, 100, 730])),
               dict(kind='volume', gb=50, rate_gb_month=0.1, attached_to_stopped=rng.random() < 0.5),
               dict(kind='public_ip', rate_h=0.005, idle=rng.random() < 0.5),
               dict(kind='nat', rate_h=0.045, gb=rng.choice([0, 100]), rate_gb=0.045, idle=rng.random() < 0.3),
               dict(kind='egress', gb=rng.choice([0, 100]), rate_gb=0.09)]
        r0 = M.monthly_cost(its)
        chk('CST-1', its[1]['attached_to_stopped'] or its[2]['idle'] or its[3]['idle'], M.monthly_cost(its, model='CST-1'), r0)
        chk('CST-2', its[3]['gb'] > 0 or its[4]['gb'] > 0, M.monthly_cost(its, model='CST-2'), r0)
        # shared responsibility
        sv = rng.choice(M.SERVICE_MODELS); ly = rng.choice(M.LAYERS); v = M.SHR[sv][M.LAYERS.index(ly)]
        chk('SHR-1', v == 'C', M.who(sv, ly, 'SHR-1'), v)
        chk('SHR-2', v == 'P' and M.LAYERS.index(ly) >= 2, M.who(sv, ly, 'SHR-2'), v)
    return res, viol
def test_misc_variants_are_controlled():
    res, viol = run()
    for m, (neg, bad, pos) in res.items():
        assert bad == 0, (m, viol.get(m)); assert pos > 0, ('variant never changes an outcome', m)
if __name__ == '__main__':
    res, viol = run()
    for m, r in res.items(): print(m, 'neg_checked=%d violations=%d trigger_changes=%d' % tuple(r), viol.get(m, ''))
    sys.exit(1 if any(r[1] or not r[2] for r in res.values()) else 0)
