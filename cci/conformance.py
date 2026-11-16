
"""Conformance tests: each reference model reproduces behaviour stated in provider documentation or RFC 9111."""
from cci.iam import Stmt, Request, PolicySet, evaluate
from cci import net as N, misc as M
from cci.net import FwRule, AclRule, Host
from cci.fixtures import base_net, _peer_nets
R = lambda act, res, racct='111': Request('role/R','111',act,res,racct)
T = []
def t(name, source, cond): T.append((name, source, bool(cond)))
# --- authorisation (provider policy-evaluation logic)
t('explicit deny overrides allow', 'policy evaluation logic', evaluate(PolicySet(identity=[Stmt('Allow',['s:*']),Stmt('Deny',['s:Del'])]), R('s:Del','b/x'))[0]=='DENY')
t('implicit deny without grant', 'policy evaluation logic', evaluate(PolicySet(), R('s:Get','b/x'))[0]=='DENY')
t('same-account resource grant suffices', 'policy evaluation logic', evaluate(PolicySet(resource=[Stmt('Allow',['s:Get'],['b/*'],principals=['role/R'])]), R('s:Get','b/x'))[0]=='ALLOW')
t('cross-account needs identity AND resource grant (identity only)', 'policy evaluation logic', evaluate(PolicySet(identity=[Stmt('Allow',['s:Get'],['b/*'])]), R('s:Get','b/x','222'))[0]=='DENY')
t('cross-account needs identity AND resource grant (resource only)', 'policy evaluation logic', evaluate(PolicySet(resource=[Stmt('Allow',['s:Get'],['b/*'],principals=['acct:111'])]), R('s:Get','b/x','222'))[0]=='DENY')
t('cross-account both sides -> allow', 'policy evaluation logic', evaluate(PolicySet(identity=[Stmt('Allow',['s:Get'],['b/*'])],resource=[Stmt('Allow',['s:Get'],['b/*'],principals=['acct:111'])]), R('s:Get','b/x','222'))[0]=='ALLOW')
t('organisation guardrail allow does not grant', 'policy evaluation logic', evaluate(PolicySet(guardrail=[Stmt('Allow',['*'])]), R('s:Get','b/x'))[0]=='DENY')
t('guardrail without matching allow caps identity grant', 'policy evaluation logic', evaluate(PolicySet(identity=[Stmt('Allow',['db:Q'])],guardrail=[Stmt('Allow',['s:*'])]), R('db:Q','d'))[0]=='DENY')
t('boundary = intersection with identity policy', 'permissions boundaries', evaluate(PolicySet(identity=[Stmt('Allow',['s:*'])],boundary=[Stmt('Allow',['s:Get'])]), R('s:Put','b/x'))[0]=='DENY' and evaluate(PolicySet(identity=[Stmt('Allow',['s:*'])],boundary=[Stmt('Allow',['s:Get'])]), R('s:Get','b/x'))[0]=='ALLOW')
t('boundary alone does not grant', 'permissions boundaries', evaluate(PolicySet(identity=[],boundary=[Stmt('Allow',['*'])]), R('s:Get','b/x'))[0]=='DENY')
# --- networking (security groups vs network ACLs; VPC routing)
n = base_net(fw_out=[FwRule('tcp',(443,443))], fw_in=[FwRule('tcp',(80,80))])
t('stateful host firewall: replies allowed without outbound rule', 'compare security groups and network ACLs', N.tcp_in(n,'web',80)[0])
n = base_net(acl_in=[AclRule(100,'allow','tcp',(80,80))], acl_out=[AclRule(100,'allow','tcp',(80,80))])
t('stateless ACL: return traffic needs ephemeral-port rule', 'compare security groups and network ACLs', N.tcp_in(n,'web',80) == (False,'acl_out_return'))
n = base_net(acl_in=[AclRule(100,'allow','tcp',(80,80))], acl_out=[AclRule(100,'allow','tcp',(1024,65535))])
t('stateless ACL with ephemeral outbound rule works', 'compare security groups and network ACLs', N.tcp_in(n,'web',80)[0])
t('ACL rules: lowest number first, first match wins', 'network ACL rules', N.acl_ok([AclRule(100,'allow','tcp'),AclRule(90,'deny','tcp',(22,22))],'tcp',22,'1.2.3.4') is False)
t('ACL implicit deny when no rule matches', 'network ACL rules', N.acl_ok([AclRule(100,'allow','tcp',(443,443))],'tcp',22,'1.2.3.4') is False)
t('internet reachability needs public IP and IGW route', 'VPC internet gateways', (not N.tcp_in(base_net(pub_route=False),'web',80)[0]) and N.tcp_in(base_net(),'web',80)[0] and (not N.tcp_in(base_net(public_ip=None),'web',80)[0]))
t('NAT gateway: outbound yes, unsolicited inbound no', 'NAT gateways', N.tcp_out(base_net(),'app',443)[0] and not N.tcp_in(base_net(),'app',22)[0])
A,B,C = _peer_nets(); B.hosts['hb'].fw_in=[FwRule('tcp',(5432,5432))]; B.hosts['hb'].listening=[5432]
t('peering is not transitive', 'VPC peering', N.tcp_private(A,'ha',B,'hb',5432)[0] and not N.tcp_private(A,'ha',C,'hc',5432)[0])
# --- caching (RFC 9111)
ev=[dict(t=0,type='origin_update',path='/a',version='v1'),dict(t=0,type='origin_headers',path='/a',max_age=60,s_maxage=600),dict(t=0,type='request',path='/a'),
    dict(t=1,type='origin_update',path='/a',version='v2'),dict(t=100,type='request',path='/a'),dict(t=700,type='request',path='/a')]
s=M.cdn_serve(ev)
t('shared cache uses s-maxage over max-age', 'RFC 9111 s.5.2.2.10', s[1][0]=='v1' and s[2][0]=='v2')
ev2=[dict(t=0,type='origin_update',path='/a',version='v1'),dict(t=0,type='origin_headers',path='/a',max_age=60),dict(t=0,type='request',path='/a'),
     dict(t=1,type='origin_update',path='/a',version='v2'),dict(t=30,type='request',path='/a'),dict(t=61,type='request',path='/a')]
s=M.cdn_serve(ev2)
t('fresh response served until freshness lifetime', 'RFC 9111 s.4.2', s[1][0]=='v1' and s[2][0]=='v2')
ev3=ev2[:4]+[dict(t=10,type='invalidate',path='/a'),dict(t=20,type='request',path='/a')]
t('invalidation evicts cached object', 'CDN invalidation', M.cdn_serve(ev3)[-1][0]=='v2')
# --- health checks, scaling, replication
t('unhealthy after threshold consecutive failures', 'target health checks', M.health_timeline([False]*5,10,3,3)[0]==30)
t('a success resets the failure count', 'target health checks', M.health_timeline([False,False,True,False,False,False],10,3,3)[0]==60)
t('target tracking clamps to max size', 'target tracking scaling', M.target_tracking(4,80,40,2,7)==7 and M.target_tracking(4,80,40,2,10)==8)
t('async replica stale before lag elapses', 'read replicas', M.replica_read(0,2,0.5)=='old' and M.replica_read(0,2,2.5)=='new')
# --- shared responsibility
t('customer patches IaaS guest OS; provider patches managed-DB OS', 'shared responsibility models', M.who('virtual machine (IaaS)','guest operating system patching')=='C' and M.who('managed relational database (PaaS)','guest operating system patching')=='P')
t('customer owns access configuration under every service model', 'shared responsibility models', all(M.who(s,'identity and access configuration')=='C' for s in M.SERVICE_MODELS))

# --- added in Round 4 (name resolution, egress paths, cache keys, cost, health recovery, ICMP over stateless ACLs)
from cci.net import Zone, resolve
Z = [Zone('.corp.internal', {'db.corp.internal': '10.1.0.20'}, ['A'])]
t('private zone answers a linked network', 'private DNS zones (association/link)', resolve('db.corp.internal', 'A', Z, {}) == '10.1.0.20')
t('private zone does not answer a peered but unlinked network', 'private DNS zones (association/link)', resolve('db.corp.internal', 'B', Z, {}, {'A': ['B'], 'B': ['A']}) is None)
t('private zone does not answer internet clients', 'private DNS zones', resolve('db.corp.internal', None, Z, {}) is None)
n = base_net(); n.nat = {'nat1': 'private'}
t('NAT gateway placed in a subnet without an internet route gives no egress', 'NAT gateways', N.tcp_out(n, 'app', 443) == (False, 'nat_subnet_no_igw_route'))
n = base_net(acl_in=[AclRule(100, 'allow', 'icmp')], acl_out=[AclRule(100, 'allow', 'tcp', (1024, 65535))], fw_in=[FwRule('icmp')])
t('stateless ACL also needs an outbound rule for ICMP replies', 'compare security groups and network ACLs', N.icmp_in(n, 'web') == (False, 'acl_out_return'))
evq = [dict(t=0, type='origin_update', path='/p', version='v'), dict(t=0, type='origin_headers', path='/p', max_age=300),
       dict(t=0, type='request', path='/p', query='a=1'), dict(t=60, type='request', path='/p', query='a=2')]
t('cache key without query string serves the first rendering to a different query', 'CDN cache keys', M.cdn_serve(evq)[-1] == ('v', 'a=1') and M.cdn_serve(evq, key_includes_query=True)[-1] == ('v', 'a=2'))
t('allocated idle public IPv4 address is billed hourly', 'public IPv4 pricing', M.monthly_cost([dict(kind='public_ip', rate_h=0.005, idle=True)]) == 3.65)
t('healthy again after healthy-threshold consecutive successes', 'target health checks', M.health_timeline([False, False, False, True, True, True], 10, 3, 3, ) == (30, 60))


def results():
    """List of (name, source, passed) for every conformance case."""
    return list(T)

if __name__ == '__main__':
    import csv, sys
    with open('data/conformance_tests.csv', 'w', newline='') as fh:
        w = csv.writer(fh); w.writerow(['test', 'source', 'passed']); w.writerows(T)
    bad = [x for x in T if not x[2]]
    print(len(T), 'conformance cases;', len(bad), 'failed'); sys.exit(1 if bad else 0)
