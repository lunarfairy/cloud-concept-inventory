
"""Property checks for cci.net.resolve variants (negative/positive controls)."""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cci.net import Zone, resolve
NETS = ['A', 'B', 'C', None]
def run(n=20000, seed=9):
    rng = random.Random(seed); res = {m: [0, 0, 0] for m in ('NET-7p', 'NET-7g', 'NET-7x')}
    for _ in range(n):
        linked = rng.sample(['A', 'B', 'C'], rng.randint(0, 2))
        zones = [Zone('.corp.internal', {'db.corp.internal': '10.1.0.20'}, linked)]
        public = {'db.corp.internal': '54.1.1.1'} if rng.random() < 0.3 else {}
        peers = {'A': ['B'], 'B': ['A']} if rng.random() < 0.6 else {}
        cn = rng.choice(NETS); ref = resolve('db.corp.internal', cn, zones, public, peers)
        trig = {'NET-7p': cn is not None and cn not in linked and any(cn in peers.get(l, []) for l in linked),
                'NET-7g': cn not in linked,
                'NET-7x': cn is not None and cn in linked}
        for m, t in trig.items():
            out = resolve('db.corp.internal', cn, zones, public, peers, m)
            if t: res[m][2] += out != ref
            else: res[m][0] += 1; res[m][1] += out != ref
    return res
def test_dns_variants_are_controlled():
    for m, (neg, bad, pos) in run().items():
        assert bad == 0, m; assert pos > 0, m
if __name__ == '__main__':
    r = run(); [print(m, v) for m, v in r.items()]; sys.exit(1 if any(v[1] or not v[2] for v in r.values()) else 0)
