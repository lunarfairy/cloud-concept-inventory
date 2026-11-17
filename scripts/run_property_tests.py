
"""Run the property-based isolation tests and write data/property_tests.csv (one row per buggy variant)."""
import os, sys, csv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'tests')); os.chdir(ROOT)
import test_variants_iam as TI, test_variants_net as TN, test_variants_misc as TM, test_variants_dns as TD
from cci.iam import VARIANTS
DESC = {'NET-1': 'Internet reachability without a gateway route (route check skipped)', 'NET-1n': 'A public address suffices for egress without any route',
 'NET-1x': 'Egress through the internet gateway without a public address', 'NET-1p': 'Egress through NAT believed to need a public address',
 'NET-2': 'NAT believed to forward unsolicited inbound connections (only address/route checks replaced)', 'NET-2p': 'NAT subnet believed not to need an internet route',
 'NET-3a': 'Stateless ACL treated as stateful (return-path checks skipped)', 'NET-3s': 'Stateful host firewall treated as stateless (reply rule required)',
 'NET-4': 'TCP reachability judged by a ping', 'NET-5d': 'Any matching deny wins in an ordered ACL', 'NET-5s': 'Most specific prefix wins in an ordered ACL',
 'NET-5r': 'Highest-numbered rule evaluated first', 'NET-6': 'Peering believed transitive', 'NET-7p': 'Peering believed to share private DNS zones',
 'NET-7g': 'Private DNS zones believed to answer every client', 'NET-7x': 'Only public DNS records believed to resolve',
 'CAC-1': 'Cached copies believed to track origin changes at once', 'CAC-1n': 'Cached copies believed never to expire (only invalidation refreshes)',
 'CAC-2': 'Query string always part of the cache key', 'CAC-4': 'Shared caches believed to use max-age, ignoring s-maxage', 'CAC-3': 'Replica reads believed synchronous',
 'LB-1t': 'A single failed check flips health state', 'LB-1b': '"Loads in a browser" believed to mean healthy', 'ELA-2m': 'Scaling believed to ignore the maximum size',
 'ELA-2a': 'Scaling believed to add one instance per breach', 'ELA-2v': 'Scaling believed to resize instances, not add them', 'LB-4': 'Stickiness believed to preserve sessions on scale-in',
 'CST-1': 'Stopped or idle resources believed free', 'CST-2': 'Gateway processing and egress believed free', 'SHR-1': 'Provider believed to secure customer layers',
 'SHR-2': 'Customer believed to manage every software layer'}
rows = []
r, _ = TI.run()
for m, (neg, bad, pos) in r.items(): rows.append(dict(model='authorisation', variant=m, rule=VARIANTS[m][0], description=VARIANTS[m][1], negative_cases=neg, violations=bad, positive_changes=pos))
for mod, name in [(TN, 'reachability'), (TD, 'name resolution'), (TM, 'misc')]:
    r = mod.run(); r = r[0] if isinstance(r, tuple) else r
    for m, (neg, bad, pos) in r.items(): rows.append(dict(model=name, variant=m, rule='', description=DESC.get(m, ''), negative_cases=neg, violations=bad, positive_changes=pos))
os.makedirs('data', exist_ok=True)
with open('data/property_tests.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(len(rows), 'variants;', sum(r['violations'] for r in rows), 'violations')
