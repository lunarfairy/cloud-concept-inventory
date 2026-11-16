
"""Three NON-OPERATIONAL sample items for publication (Appendix C). They are built with the same reference
models, buggy variants and twin checks as the bank, but use new scenarios, so releasing them does not expose
operational items."""
import cci.bank as _B                      # build the operational bank first (shared ITEMS list)
import cci.bank_a as BA
from cci.bank_a import combo_item, value_item, _std, NET_MODELS
from cci.iam import Stmt, Request, PolicySet, evaluate, MODELS as IAM_MODELS
from cci import net as N, misc as M
from cci.net import FwRule, AclRule
from cci.items1 import base_net
_n0 = len(BA.ITEMS)
def f_s1(m, v):
    rq = lambda res, acct: Request('fn/F', '333', 'queue:SendMessage', res, acct, same_org=True)
    rp = [Stmt('Allow', ['queue:SendMessage'], ['queue/q2'], principals=['acct:333'])] if v == 'rp' else []
    idp = [Stmt('Allow', ['queue:SendMessage'], ['queue/q1', 'queue/q2'])]
    a = evaluate(PolicySet(identity=idp, resource=rp), rq('queue/q2', '444'), m)[0] == 'ALLOW'
    b = evaluate(PolicySet(identity=idp), rq('queue/q1', '333'), m)[0] == 'ALLOW'
    return (a, b)
_std(combo_item('S1', 'IAM', 'Cross-account access requires both sides (sample)',
 "Function F runs with a role in account 333 whose identity policy allows queue:SendMessage on queue/q1 and on queue/q2. Queue q1 belongs to account 333; queue q2 belongs to account 444, "
 "and neither queue has a resource policy. Both accounts are in the same organisation; no guardrails or denies apply. F sends (1) a message to q2 and (2) a message to q1. Which sends succeed?",
 f_s1, '', '', IAM_MODELS, ['none', 'rp'], vendor='high'), a='send (1)', b='send (2)', plural='sends succeed', neg='Neither send succeeds.')
def f_s2(m, v):
    out = [AclRule(100, 'allow', 'tcp', (22, 22))] + ([AclRule(110, 'allow', 'tcp', (1024, 65535))] if v == 'eph' else [])
    inn = [AclRule(100, 'allow', 'tcp', (22, 22))]
    n = base_net(acl_in=inn, acl_out=out, fw_in=[FwRule('tcp', (22, 22))], listening=(22,))
    return (N.tcp_in(n, 'web', 22, model=m)[0], N.icmp_in(n, 'web', model=m)[0])
_std(combo_item('S2', 'NET', 'Stateless filters need return-path rules (sample)',
 "VM web has a public IP in subnet S, which routes 0.0.0.0/0 to the internet gateway; an SSH server listens on TCP 22. S's subnet ACL has exactly: inbound #100 allow TCP 22 from 0.0.0.0/0; "
 "outbound #100 allow TCP 22 to 0.0.0.0/0; anything else is denied. web's host firewall allows inbound TCP 22 and all outbound traffic. Client source ports are 1024-65535. "
 "From the internet: (1) open SSH to web; (2) ping web. Which succeed?",
 f_s2, '', '', NET_MODELS, ['base', 'eph'], vendor='high'), a='(1) succeeds', b='(2) succeeds', verb='', plural='succeed', neg='Neither succeeds.')
def f_s3(m, v):
    ttl = 600 if v == 'base' else 120
    ev = [dict(t=0, type='origin_update', path='/app.js', version='old'), dict(t=0, type='origin_headers', path='/app.js', max_age=ttl),
          dict(t=0, type='request', path='/app.js'), dict(t=60, type='origin_update', path='/app.js', version='new'),
          dict(t=300, type='request', path='/app.js'), dict(t=900, type='request', path='/app.js')]
    s = M.cdn_serve(ev, model=m); return (s[1][0], s[2][0])
value_item('S3', 'CAC', 'TTL: origin changes are not instantly visible (sample)',
 "/app.js is served through a CDN; the origin sends Cache-Control: max-age=600 and nothing else. At 12:00:00 a request through edge E caches the file; at 12:01:00 the file changes at the origin. "
 "No invalidation is issued, and E keeps its copy until it expires without revalidating it. Which versions do requests through E receive (1) at 12:05:00 and (2) at 12:15:00?",
 f_s3, [(('old', 'new'), '(1) old version; (2) new version'), (('new', 'new'), '(1) new version; (2) new version'),
        (('old', 'old'), '(1) old version; (2) old version'), (('new', 'old'), '(1) new version; (2) old version')], ['reference', 'CAC-1', 'CAC-1n', 'CAC-2', 'CAC-4'], ['base', 'ttl120'])
SAMPLES = BA.ITEMS[_n0:]
del BA.ITEMS[_n0:]
