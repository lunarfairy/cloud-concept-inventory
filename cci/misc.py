
"""Reference models (and buggy variants) for caching/consistency, load-balancer health checks,
elastic scaling, cost and the shared-responsibility model."""
import math, random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ---------------- CDN / edge cache ----------------
def cdn_serve(events, model='reference', key_includes_query=False):
    """events: list of dicts in time order:
         {'t':..,'type':'origin_update','path':p,'version':v}
         {'t':..,'type':'invalidate','path':p}
         {'t':..,'type':'request','path':p,'query':q}
       Origin responses carry 'max_age' (browser/any cache) and optional 's_maxage' (shared caches) in seconds,
       supplied in events of type 'origin_headers' {'path':p,'max_age':..,'s_maxage':..}.
       Returns list of versions served for each request, in order."""
    origin, headers, cache, out = {}, {}, {}, []
    for e in events:
        if e['type'] == 'origin_update':
            origin[e['path']] = e['version']
        elif e['type'] == 'origin_headers':
            headers[e['path']] = e
        elif e['type'] == 'invalidate':
            for k in list(cache):
                if k[0] == e['path']:
                    del cache[k]
        elif e['type'] == 'request':
            p = e['path']; q = e.get('query', '')
            kq = (key_includes_query if model != 'CAC-2' else True)
            key = (p, q if kq else '')
            h = headers.get(p, {})
            ttl = h.get('max_age', 0) if model == 'CAC-4' else h.get('s_maxage', h.get('max_age', 0))
            if model == 'CAC-1n': ttl = float('inf')   # buggy: a cached copy never expires; only invalidation refreshes it
            ent = cache.get(key)
            if ent and e['t'] < ent['t'] + ttl:
                if model == 'CAC-1':   # buggy: a cached copy is believed to track origin changes at once
                    out.append((origin[p], ent['v'][1]))   # (cache-key behaviour is unchanged)
                else:
                    out.append(ent['v'])
            else:
                # origin renders the page for this query (version tagged with the query it was rendered for)
                v = (origin[p], q)
                cache[key] = {'t': e['t'], 'v': v}
                out.append(v)
    return out

# ---------------- asynchronous replication ----------------
def replica_read(t_write, lag, t_read, read_from='replica', model='reference'):
    if model == 'CAC-3' or read_from == 'primary':
        return 'new' if t_read >= t_write else 'old'
    return 'new' if t_read >= t_write + lag else 'old'

# ---------------- load-balancer health checks ----------------
def health_timeline(results, interval, unhealthy_threshold, healthy_threshold, start_state='healthy', model='reference'):
    """results: list of booleans, outcome of successive checks at t=interval, 2*interval, ...
       Returns (time first marked unhealthy, time first marked healthy again) or None."""
    state = start_state; fails = succ = 0; t_unh = t_h = None
    for i, ok in enumerate(results, start=1):
        t = i * interval
        if model == 'LB-1t':  # buggy: a single failed check flips state
            if not ok and state == 'healthy': state = 'unhealthy'; t_unh = t_unh or t
            if ok and state == 'unhealthy': state = 'healthy'; t_h = t_h or t
            continue
        if ok:
            succ += 1; fails = 0
            if state == 'unhealthy' and succ >= healthy_threshold:
                state = 'healthy'; t_h = t_h or t
        else:
            fails += 1; succ = 0
            if state == 'healthy' and fails >= unhealthy_threshold:
                state = 'unhealthy'; t_unh = t_unh or t
    return t_unh, t_h

def health_check_passes(status_code, matcher=(200, 200), checker_allowed=True, listening=True, model='reference'):
    if model == 'LB-1b':      # buggy: 'the page loads in a browser' == healthy
        return listening and checker_allowed and status_code < 500 or (status_code in (301, 302) and listening)
    return checker_allowed and listening and matcher[0] <= status_code <= matcher[1]

# ---------------- elastic scaling ----------------
def target_tracking(current, metric, target, mn, mx, model='reference'):
    if model == 'ELA-2v':     # buggy: scaling changes instance size, count unchanged
        return current
    if model == 'ELA-2m':     # buggy: ignores the max bound
        return max(mn, math.ceil(current * metric / target))
    if model == 'ELA-2a':     # buggy: adds one instance per breach
        return min(mx, current + 1) if metric > target else current
    return max(mn, min(mx, math.ceil(current * metric / target)))

def sessions_lost_on_scale_in(n_instances, n_removed, users=100000, sticky=True, store='local', seed=0, model='reference'):
    """Monte-Carlo: fraction of active users whose session state is lost when instances are removed."""
    if model == 'LB-4' and sticky:   # buggy: stickiness is believed to preserve sessions (applies only to sticky routing)
        return 0.0
    if store == 'external':
        return 0.0
    rng = random.Random(seed)
    home = [rng.randrange(n_instances) for _ in range(users)]
    removed = set(range(n_removed))
    if sticky:
        lost = sum(1 for hm in home if hm in removed)
    else:
        # without stickiness the next request lands on a random surviving instance; state lives only on 'home'
        lost = sum(1 for hm in home if rng.randrange(n_instances - n_removed) + n_removed != hm)
    return lost / users

def availability(zones_used, p_zone_fail, p_instance_fail, per_zone=1):
    """P(at least one healthy instance) with independent zone and instance failures."""
    # service up iff some zone up with at least one healthy instance
    p_zone_ok = (1 - p_zone_fail) * (1 - p_instance_fail ** per_zone)
    return 1 - (1 - p_zone_ok) ** zones_used

# ---------------- cost ----------------
def monthly_cost(items, hours=730, model='reference'):
    """items: list of dicts with 'kind' and parameters; returns total USD under the model."""
    tot = 0.0
    for it in items:
        k = it['kind']
        if k == 'instance':
            run = it['hours_running']
            tot += it['rate_h'] * run
        elif k == 'volume':
            if model == 'CST-1' and it.get('attached_to_stopped'): continue
            tot += it['gb'] * it['rate_gb_month']
        elif k == 'public_ip':
            if model == 'CST-1' and it.get('idle'): continue
            tot += it['rate_h'] * hours
        elif k == 'nat':
            if model == 'CST-1' and it.get('idle'): continue
            tot += it['rate_h'] * hours + (0 if model == 'CST-2' else it['gb'] * it['rate_gb'])
        elif k == 'egress':
            if model == 'CST-2': continue
            tot += it['gb'] * it['rate_gb']
        elif k == 'requests':
            tot += it['n'] / 1e6 * it['rate_per_million']
    return round(tot, 2)

# ---------------- shared responsibility ----------------
LAYERS = ['physical facilities', 'host hardware and virtualisation', 'guest operating system patching',
          'language runtime / managed engine patching', 'application code and dependencies',
          'identity and access configuration', 'data classification and protection settings',
          'network access rules for the service']
SERVICE_MODELS = ['virtual machine (IaaS)', 'managed relational database (PaaS)', 'function-as-a-service', 'SaaS application']
# P = provider, C = customer. Consensus of the three major providers' published models (vendor-neutral abstraction).
SHR = {
 'virtual machine (IaaS)':            ['P','P','C','C','C','C','C','C'],
 'managed relational database (PaaS)':['P','P','P','P','C','C','C','C'],
 'function-as-a-service':             ['P','P','P','P','C','C','C','C'],
 'SaaS application':                  ['P','P','P','P','P','C','C','P'],
}
def who(service, layer, model='reference'):
    i = LAYERS.index(layer); v = SHR[service][i]
    if model == 'SHR-1' and v == 'C': return 'P'     # provider secures everything
    if model == 'SHR-2' and v == 'P' and i >= 2: return 'C'   # customer must manage all software layers
    return v
