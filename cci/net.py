
"""Vendor-neutral reference model of virtual-network reachability with buggy mental models.
Functions return (ok, reason) where reason is the first failing check (or 'ok')."""
import ipaddress as ip
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
EPH = (1024, 65535); ANY = '0.0.0.0/0'
def inet(c): return ip.ip_network(c, strict=False)
def inaddr(a, c): return ip.ip_address(a) in inet(c)

@dataclass
class FwRule:
    proto: str; ports: Tuple[int, int] = (0, 65535); peer: str = ANY
@dataclass
class AclRule:
    num: int; action: str; proto: str; ports: Tuple[int, int] = (0, 65535); peer: str = ANY
@dataclass
class Host:
    name: str; subnet: str; private_ip: str; public_ip: Optional[str] = None
    fw_in: List[FwRule] = field(default_factory=list)
    fw_out: List[FwRule] = field(default_factory=lambda: [FwRule('all')])
    listening: List[int] = field(default_factory=list); icmp_reply: bool = True
@dataclass
class Net:
    subnets: Dict[str, dict]; route_tables: Dict[str, list]; hosts: Dict[str, Host]
    nat: Dict[str, str] = field(default_factory=dict)       # nat id -> subnet where it is placed
    peers: Dict[str, 'Net'] = field(default_factory=dict); name: str = 'netA'; cidr: str = '10.0.0.0/16'

def _pm(r, proto, port, peer):
    return r.proto in ('all', proto) and (proto == 'icmp' or r.ports[0] <= port <= r.ports[1]) and inaddr(peer, r.peer)
def fw_ok(rules, proto, port, peer): return any(_pm(r, proto, port, peer) for r in rules)
def acl_ok(rules, proto, port, peer, model='reference'):
    if rules is None: return True
    rs = sorted(rules, key=lambda r: r.num)
    m = [r for r in rs if _pm(r, proto, port, peer)]
    if not m: return False
    if model == 'NET-5d': return not any(r.action == 'deny' for r in m)          # deny always wins
    if model == 'NET-5s':                                                        # most specific prefix wins
        return max(m, key=lambda r: (inet(r.peer).prefixlen, -r.num)).action == 'allow'
    if model == 'NET-5r': return m[-1].action == 'allow'                          # highest number first
    return m[0].action == 'allow'
def acl_range_ok(rules, proto, rng, peer, model='reference'):
    if rules is None: return True
    return all(acl_ok(rules, proto, p, peer, model) for p in (rng[0], 32768, 49152, rng[1]))
def route(net, subnet, dst):
    best = None
    for c, t in net.route_tables[net.subnets[subnet]['rt']]:
        if inaddr(dst, c) and (best is None or inet(c).prefixlen > inet(best[0]).prefixlen): best = (c, t)
    return None if best is None else best[1]

def tcp_in(net, h, port, client='203.0.113.10', model='reference'):
    """Internet client -> host public address, TCP port (connection must complete)."""
    H = net.hosts[h]; S = net.subnets[H.subnet]
    if model == 'NET-4':      # buggy: a successful ping is taken to show TCP reachability
        return icmp_in(net, h, client)
    via_nat = (model == 'NET-2' and H.public_ip is None and (route(net, H.subnet, client) or '').startswith('nat:'))
    # NET-2 (buggy): the NAT gateway is believed to forward unsolicited inbound connections to the private host;
    # only the public-address and gateway-route checks are replaced, every other check still applies.
    if not via_nat:
        if H.public_ip is None: return (False, 'no_public_ip')
        if model not in ('NET-1',) and route(net, H.subnet, client) != 'igw': return (False, 'no_igw_route')
    if not acl_ok(S.get('acl_in'), 'tcp', port, client, model): return (False, 'acl_in')
    if not fw_ok(H.fw_in, 'tcp', port, client): return (False, 'fw_in')
    if model == 'NET-3s' and not fw_ok(H.fw_out, 'tcp', EPH[0], client): return (False, 'fw_out_reply')
    if port not in H.listening: return (False, 'not_listening')
    if model not in ('NET-3a',) and not acl_range_ok(S.get('acl_out'), 'tcp', EPH, client, model): return (False, 'acl_out_return')
    return (True, 'ok')

def icmp_in(net, h, client='203.0.113.10', model='reference'):
    H = net.hosts[h]; S = net.subnets[H.subnet]
    if H.public_ip is None: return (False, 'no_public_ip')
    if model != 'NET-1' and route(net, H.subnet, client) != 'igw': return (False, 'no_igw_route')
    if not acl_ok(S.get('acl_in'), 'icmp', 0, client, model): return (False, 'acl_in')
    if not fw_ok(H.fw_in, 'icmp', 0, client): return (False, 'fw_in')
    if not H.icmp_reply: return (False, 'no_reply')
    if model != 'NET-3a' and not acl_ok(S.get('acl_out'), 'icmp', 0, client, model): return (False, 'acl_out_return')
    return (True, 'ok')

def tcp_out(net, h, port=443, dst='198.51.100.20', model='reference'):
    """Host -> internet address (outbound connection must complete)."""
    H = net.hosts[h]; S = net.subnets[H.subnet]
    if not fw_ok(H.fw_out, 'tcp', port, dst): return (False, 'fw_out')
    if model == 'NET-3s' and not fw_ok(H.fw_in, 'tcp', EPH[0], dst): return (False, 'fw_in_reply')
    if not acl_ok(S.get('acl_out'), 'tcp', port, dst, model): return (False, 'acl_out')
    if model == 'NET-1p' and H.public_ip is None: return (False, 'needs_public_ip')
    t = route(net, H.subnet, dst)
    if t == 'igw':
        if H.public_ip is None and model != 'NET-1x': return (False, 'no_public_ip')
    elif t and t.startswith('nat:'):
        ns = net.nat.get(t.split(':')[1])
        if ns is None: return (False, 'no_nat')
        if model != 'NET-2p' and route(net, ns, dst) != 'igw': return (False, 'nat_subnet_no_igw_route')
    else:
        if model == 'NET-1n' and H.public_ip: return (True, 'public_ip_suffices')
        return (False, 'no_route')
    if model != 'NET-3a' and not acl_range_ok(S.get('acl_in'), 'tcp', EPH, dst, model): return (False, 'acl_in_return')
    return (True, 'ok')

def tcp_private(net, src, dst_net, dst, port, model='reference'):
    """Host -> host by private address, possibly across peering links."""
    A = net.hosts[src]; SA = net.subnets[A.subnet]; B = dst_net.hosts[dst]; SB = dst_net.subnets[B.subnet]
    if not fw_ok(A.fw_out, 'tcp', port, B.private_ip): return (False, 'fw_out')
    t = route(net, A.subnet, B.private_ip)
    if dst_net is net:
        if t != 'local': return (False, 'no_route')
    else:
        direct = t == 'peer:' + dst_net.name
        if (not direct) and model != 'NET-6' and t and t.startswith('peer:') and t.split(':')[1] in net.peers:
            return (False, 'not_transitive')
        if model == 'NET-6':
            via = t and t.startswith('peer:') and t.split(':')[1] in net.peers and dst_net.name in net.peers[t.split(':')[1]].peers
            direct = direct or bool(via)
        if not direct: return (False, 'no_peering_route')
        if dst_net.name not in net.peers and model != 'NET-6': return (False, 'not_peered')
    if not acl_ok(SB.get('acl_in'), 'tcp', port, A.private_ip, model): return (False, 'acl_in')
    if not fw_ok(B.fw_in, 'tcp', port, A.private_ip): return (False, 'fw_in')
    if port not in B.listening: return (False, 'not_listening')
    return (True, 'ok')


# ---------------- name resolution (private DNS zones) ----------------
@dataclass
class Zone:
    suffix: str; records: Dict[str, str]; linked: List[str] = field(default_factory=list); private: bool = True

def resolve(name, client_net, zones, public, peers=None, model='reference'):
    """Return the address that `name` resolves to for a client in virtual network `client_net`
    (None = a client on the internet), or None if it does not resolve.
    Reference: a private zone answers only clients in virtual networks linked to it; otherwise public DNS answers.
    Buggy variants (each changes one rule):
      NET-7p  peering is believed to share private zones (a network peered with a linked network can resolve them);
      NET-7g  private zones are believed to answer every client, including internet clients;
      NET-7x  only public DNS records are believed to resolve (private zones are ignored)."""
    peers = peers or {}
    if model != 'NET-7x':
        for z in zones:
            if not z.private or not name.endswith(z.suffix) or name not in z.records: continue
            nets = set(z.linked)
            if model == 'NET-7p':
                nets |= {p for n in z.linked for p in peers.get(n, [])}
            if model == 'NET-7g' or (client_net is not None and client_net in nets):
                return z.records[name]
    return public.get(name)
