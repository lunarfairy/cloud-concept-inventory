
"""Property-based checks for the reachability model (cci.net): every buggy variant equals the reference
whenever the rule it perturbs is not exercised (negative control) and changes some outcome when it is
(positive control). Run: python -m pytest tests"""
import random, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cci import net as N
from cci.net import FwRule, AclRule, Host
from cci.fixtures import base_net, _peer_nets

VARS = ['NET-1','NET-1n','NET-1x','NET-1p','NET-2','NET-2p','NET-3a','NET-3s','NET-4','NET-5d','NET-5s','NET-5r','NET-6']
PEERS = ['0.0.0.0/0', '203.0.113.0/24', '198.51.100.0/24', '10.0.0.0/8']
def racl(rng):
    if rng.random() < 0.4: return None
    rules = []
    for k in range(rng.randint(1, 4)):
        lo = rng.choice([0, 22, 80, 443, 1024]); hi = rng.choice([lo, 65535, lo + 1000])
        rules.append(AclRule(100 * (k + 1) + rng.randint(0, 50), rng.choice(['allow', 'allow', 'deny']), rng.choice(['tcp', 'all', 'icmp']), (lo, min(hi, 65535)), rng.choice(PEERS)))
    return rules
def rfw(rng, out=False):
    if out and rng.random() < 0.6: return [FwRule('all')]
    return [FwRule(rng.choice(['tcp', 'icmp', 'all']), rng.choice([(22, 22), (80, 80), (443, 443), (0, 65535), (1024, 65535)]), rng.choice(PEERS)) for _ in range(rng.randint(0, 3))]
def rnet(rng):
    n = base_net(pub_route=rng.random() < 0.7, acl_in=racl(rng), acl_out=racl(rng), fw_in=rfw(rng), fw_out=rfw(rng, True),
                 public_ip=('54.0.0.10' if rng.random() < 0.7 else None), listening=tuple(rng.sample([22, 80, 443], rng.randint(0, 3))))
    app = n.hosts['app']; app.fw_in = rfw(rng); app.fw_out = rfw(rng, True); app.listening = rng.sample([22, 80, 443, 8080], rng.randint(0, 3))
    if rng.random() < 0.3: app.public_ip = '54.0.0.20'
    n.route_tables['rt-priv'] = [('10.0.0.0/16', 'local')] + ([( '0.0.0.0/0', rng.choice(['nat:nat1', 'nat:nat1', 'igw', 'nat:nat9']))] if rng.random() < 0.85 else [])
    n.nat = {'nat1': rng.choice(['public', 'public', 'private'])}
    n.subnets['private']['acl_in'] = racl(rng); n.subnets['private']['acl_out'] = racl(rng)
    return n
def acl_diff(rules, proto, ports, peer, m):
    return rules is not None and any(N.acl_ok(rules, proto, p, peer) != N.acl_ok(rules, proto, p, peer, m) for p in ports)
EPHP = (1024, 32768, 49152, 65535)
def trig_in(m, n, h, port, cl):
    H = n.hosts[h]; S = n.subnets[H.subnet]; rt = N.route(n, H.subnet, cl) or ''
    if m == 'NET-1': return bool(H.public_ip) and rt != 'igw'
    if m == 'NET-2': return H.public_ip is None and rt.startswith('nat:')
    if m == 'NET-3a': return S.get('acl_out') is not None and not N.acl_range_ok(S.get('acl_out'), 'tcp', N.EPH, cl)
    if m == 'NET-3s': return not N.fw_ok(H.fw_out, 'tcp', N.EPH[0], cl)
    if m == 'NET-4': return N.icmp_in(n, h, cl)[0] != N.tcp_in(n, h, port, cl)[0]
    if m.startswith('NET-5'): return acl_diff(S.get('acl_in'), 'tcp', (port,), cl, m) or acl_diff(S.get('acl_out'), 'tcp', EPHP, cl, m)
    return False
def trig_out(m, n, h, port, dst):
    H = n.hosts[h]; S = n.subnets[H.subnet]; rt = N.route(n, H.subnet, dst) or ''
    if m == 'NET-1n': return rt == '' and bool(H.public_ip)
    if m == 'NET-1x': return rt == 'igw' and H.public_ip is None
    if m == 'NET-1p': return H.public_ip is None
    if m == 'NET-2p': return rt.startswith('nat:') and n.nat.get(rt.split(':')[1]) is not None and N.route(n, n.nat[rt.split(':')[1]], dst) != 'igw'
    if m == 'NET-3a': return S.get('acl_in') is not None and not N.acl_range_ok(S.get('acl_in'), 'tcp', N.EPH, dst)
    if m == 'NET-3s': return not N.fw_ok(H.fw_in, 'tcp', N.EPH[0], dst)
    if m.startswith('NET-5'): return acl_diff(S.get('acl_out'), 'tcp', (port,), dst, m) or acl_diff(S.get('acl_in'), 'tcp', EPHP, dst, m)
    return False
def trig_icmp(m, n, h, cl):
    H = n.hosts[h]; S = n.subnets[H.subnet]; rt = N.route(n, H.subnet, cl) or ''
    if m == 'NET-1': return bool(H.public_ip) and rt != 'igw'
    if m == 'NET-3a': return S.get('acl_out') is not None and not N.acl_ok(S.get('acl_out'), 'icmp', 0, cl)
    if m.startswith('NET-5'): return acl_diff(S.get('acl_in'), 'icmp', (0,), cl, m) or acl_diff(S.get('acl_out'), 'icmp', (0,), cl, m)
    return False
def run(n_iter=6000, seed=3):
    rng = random.Random(seed); res = {m: [0, 0, 0] for m in VARS}; viol = {}
    def chk(m, trig, a, b, tag):
        if trig: res[m][2] += a != b
        else:
            res[m][0] += 1
            if a != b: res[m][1] += 1; viol.setdefault(m, tag)
    for it in range(n_iter):
        n = rnet(rng); cl = rng.choice(['203.0.113.10', '198.51.100.7']); port = rng.choice([22, 80, 443])
        for h in ('web', 'app'):
            ref_in = N.tcp_in(n, h, port, cl)[0]; ref_out = N.tcp_out(n, h, port, cl)[0]; ref_ic = N.icmp_in(n, h, cl)[0]
            for m in VARS:
                chk(m, trig_in(m, n, h, port, cl), N.tcp_in(n, h, port, cl, model=m)[0], ref_in, ('in', it, h))
                chk(m, trig_out(m, n, h, port, cl), N.tcp_out(n, h, port, cl, model=m)[0], ref_out, ('out', it, h))
                chk(m, trig_icmp(m, n, h, cl), N.icmp_in(n, h, cl, model=m)[0], ref_ic, ('icmp', it, h))
        A, B, C = _peer_nets()
        if rng.random() < 0.5: A.peers['netC'] = C; C.peers['netA'] = A; A.route_tables['rtA'][2] = ('10.3.0.0/16', 'peer:netC')
        B.hosts['hb'].fw_in = [FwRule('tcp', (5432, 5432), '10.0.0.0/8')]; B.hosts['hb'].listening = [5432]
        for dn, dh in ((B, 'hb'), (C, 'hc')):
            ref = N.tcp_private(A, 'ha', dn, dh, 5432)[0]
            for m in VARS:
                tr = (m == 'NET-6' and dn.name not in A.peers)
                chk(m, tr, N.tcp_private(A, 'ha', dn, dh, 5432, model=m)[0], ref, ('priv', it, dh))
    return res, viol
def test_net_variants_are_controlled():
    res, viol = run()
    for m, (neg, bad, pos) in res.items():
        assert bad == 0, (m, viol.get(m)); assert pos > 0, ('variant never changes an outcome', m)
if __name__ == '__main__':
    res, viol = run()
    for m, r in res.items(): print(m, 'neg_checked=%d violations=%d trigger_changes=%d' % tuple(r), viol.get(m, ''))
    sys.exit(1 if any(r[1] or not r[2] for r in res.values()) else 0)
