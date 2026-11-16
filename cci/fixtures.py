"""Scenario fixtures shared by items, conformance cases and property tests (no item text)."""
from cci.net import FwRule, AclRule, Host, Net

def base_net(pub_route=True, acl_in=None, acl_out=None, fw_in=None, fw_out=None, public_ip='54.0.0.10', listening=(80,)):
    rt = {'rt-pub': [('10.0.0.0/16','local')] + ([('0.0.0.0/0','igw')] if pub_route else []),
          'rt-priv': [('10.0.0.0/16','local'), ('0.0.0.0/0','nat:nat1')]}
    subnets = {'public': dict(cidr='10.0.1.0/24', rt='rt-pub', acl_in=acl_in, acl_out=acl_out),
               'private': dict(cidr='10.0.2.0/24', rt='rt-priv', acl_in=None, acl_out=None)}
    web = Host('web','public','10.0.1.10',public_ip, fw_in=fw_in if fw_in is not None else [FwRule('tcp',(80,80))],
               fw_out=fw_out if fw_out is not None else [FwRule('all')], listening=list(listening))
    app = Host('app','private','10.0.2.20',None, fw_in=[FwRule('tcp',(22,22)),FwRule('tcp',(8080,8080))], listening=[22,8080])
    return Net(subnets=subnets, route_tables=rt, hosts={'web':web,'app':app}, nat={'nat1':'public'})


def _peer_nets():
    A = Net(subnets={'a': dict(cidr='10.1.0.0/24', rt='rtA')}, route_tables={'rtA':[('10.1.0.0/16','local'),('10.2.0.0/16','peer:netB'),('10.3.0.0/16','peer:netB')]},
            hosts={'ha':Host('ha','a','10.1.0.5',fw_out=[FwRule('all')])}, name='netA', cidr='10.1.0.0/16')
    B = Net(subnets={'b': dict(cidr='10.2.0.0/24', rt='rtB')}, route_tables={'rtB':[('10.2.0.0/16','local'),('10.1.0.0/16','peer:netA'),('10.3.0.0/16','peer:netC')]},
            hosts={'hb':Host('hb','b','10.2.0.5')}, name='netB', cidr='10.2.0.0/16')
    C = Net(subnets={'c': dict(cidr='10.3.0.0/24', rt='rtC')}, route_tables={'rtC':[('10.3.0.0/16','local'),('10.2.0.0/16','peer:netB'),('10.1.0.0/16','peer:netB')]},
            hosts={'hc':Host('hc','c','10.3.0.5',fw_in=[FwRule('tcp',(5432,5432),'10.0.0.0/8')],listening=[5432])}, name='netC', cidr='10.3.0.0/16')
    A.peers={'netB':B}; B.peers={'netA':A,'netC':C}; C.peers={'netB':B}
    return A,B,C
