
"""Vendor-neutral reference model of cloud authorisation, with buggy mental models.

evaluate(ps, req, model) returns (decision, reason).

The reference decision is computed by an explicit pipeline of named rules:
  R1 grants       collect applicable Allow / Deny statements (identity, resource, boundary, guardrail)
  R2 deny         an applicable explicit Deny in any policy wins
  R3 guardrail    an organisation guardrail never grants; if present it must also allow the action (cap)
  R4 boundary     a permission boundary never grants; an identity grant counts only if the boundary allows it
  R5 combine      same account: identity grant OR resource grant suffices;
                  different accounts: identity grant AND resource grant are both required
  R6 default      anything not granted is denied

Each buggy model perturbs exactly ONE rule (documented in VARIANTS); every other rule is evaluated
exactly as in the reference. tests/test_variants.py checks this property on randomly generated scenarios:
whenever a variant's trigger condition is absent its decision equals the reference decision.
"""
from fnmatch import fnmatchcase
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class Stmt:
    effect: str
    actions: List[str]
    resources: List[str] = field(default_factory=lambda: ['*'])
    principals: Optional[List[str]] = None
    conditions: Dict[str, object] = field(default_factory=dict)

@dataclass
class Request:
    principal: str
    principal_account: str
    action: str
    resource: str
    resource_account: str
    context: Dict[str, object] = field(default_factory=dict)
    same_org: bool = False          # caller and resource accounts belong to one organisation

@dataclass
class PolicySet:
    identity: List[Stmt] = field(default_factory=list)   # in attachment order
    resource: List[Stmt] = field(default_factory=list)
    boundary: Optional[List[Stmt]] = None
    guardrail: Optional[List[Stmt]] = None
    creator: Optional[List[Stmt]] = None   # identity policies of the principal that created the role (scenario fact)

VARIANTS = {
 'IAM-1':   ('R2', 'Allow beats deny: an explicit Deny is ignored when some Allow also applies.'),
 'IAM-2':   ('R6', 'Default allow: whatever is not explicitly denied is allowed (every implicit deny becomes allow).'),
 'IAM-2org':('R5', 'Same organisation counts as same account: the one-side rule is applied to cross-account requests inside one organisation.'),
 'IAM-3':   ('R5', 'One side suffices everywhere: the same-account rule is applied to every cross-account request.'),
 'IAM-3i':  ('R5', 'Identity side always required: a resource-policy grant alone never suffices, even within one account.'),
 'IAM-3r':  ('R5', 'Resource side always required: an identity grant alone never suffices, even within one account.'),
 'IAM-4c':  ('R1', 'Role inherits its creator: the creator\'s identity policies are counted as the role\'s identity grants.'),
 'IAM-5':   ('R1', 'Container and object identifiers are interchangeable when matching resources.'),
 'IAM-5w':  ('R1', 'A wildcard * is believed not to cross "/" separators.'),
 'IAM-5x':  ('R1', 'Identity policies cannot name resources owned by another account (such statements are ignored).'),
 'IAM-6a':  ('R3,R4', 'Guardrails grant: an Allow in a guardrail or boundary is counted as an identity grant (caps still apply).'),
 'IAM-6b':  ('R3,R4', 'Guardrails do not cap: guardrails and boundaries are ignored as limits.'),
 'IAM-6c':  ('R4', 'Boundary defines permissions: when a boundary exists, the identity grant is whatever the boundary allows.'),
 'IAM-7o':  ('R2', 'First match decides: among identity statements, the first applicable one in attachment order decides; later identity Denies are ignored.'),
}

def _m(pats, v): return any(fnmatchcase(v, p) for p in pats)

def _applies(s, req, rp=False, model='reference'):
    if not _m(s.actions, req.action): return False
    res = req.resource
    if model == 'IAM-5':   # container and object identifiers treated as interchangeable
        pats = s.resources + [p[:-2] for p in s.resources if p.endswith('/*')]
        if not (_m(pats, res) or _m(s.resources, res + '/x')): return False
    elif model == 'IAM-5w':  # wildcard * believed not to cross '/' separators
        if not any(fnmatchcase(res, p) and (p.count('/') == res.count('/')) for p in s.resources): return False
    elif not _m(s.resources, res): return False
    if rp:
        pr = s.principals or []
        if not ('*' in pr or req.principal in pr or ('acct:' + req.principal_account) in pr): return False
    for k, v in s.conditions.items():
        if req.context.get(k) != v: return False
    return True

def _first_match(stmts, req, model):
    for s in stmts:
        if _applies(s, req, False, model):
            return s.effect
    return None

def evaluate(ps, req, model='reference'):
    mdl = model
    A = lambda L, rp=False: [s for s in (L or []) if s.effect == 'Allow' and _applies(s, req, rp, mdl)]
    D = lambda L, rp=False: [s for s in (L or []) if s.effect == 'Deny' and _applies(s, req, rp, mdl)]
    same = req.principal_account == req.resource_account
    # ---- R1 grants
    ident = list(ps.identity)
    if model == 'IAM-4c' and ps.creator: ident = ident + list(ps.creator)
    if model == 'IAM-5x' and not same: ident = []
    idA, idD = A(ident), D(ident)
    rsA, rsD = A(ps.resource, True), D(ps.resource, True)
    bA, bD, gA, gD = A(ps.boundary), D(ps.boundary), A(ps.guardrail), D(ps.guardrail)
    if model == 'IAM-7o':
        fm = _first_match(ident, req, model)
        idA, idD = ([1] if fm == 'Allow' else []), ([1] if fm == 'Deny' else [])
    if model == 'IAM-6a':
        idA = idA or bA or gA
    # ---- R2 deny
    deny = bool(idD or rsD or bD or gD)
    if deny and not (model == 'IAM-1' and (idA or rsA)):
        return ('DENY', 'explicit_deny')
    # ---- R3 guardrail cap
    guard_cap = ps.guardrail is not None and not gA and model != 'IAM-6b'
    # ---- R4 boundary cap / definition
    if model == 'IAM-6c' and ps.boundary is not None:
        id_ok = bool(bA)
    else:
        id_ok = bool(idA) and (ps.boundary is None or bool(bA) or model == 'IAM-6b')
    bcap = bool(idA) and not id_ok
    if guard_cap:
        id_ok = False
        rs_ok = False       # a guardrail caps every principal in the account, whichever side grants
    else:
        rs_ok = bool(rsA)
    # ---- R5 combine
    one_side = same or model == 'IAM-3' or (model == 'IAM-2org' and req.same_org)
    if model == 'IAM-3i':
        ok = id_ok and (rs_ok or same)
    elif model == 'IAM-3r':
        ok = rs_ok and (id_ok or same)
    elif one_side:
        ok = id_ok or rs_ok
    else:
        ok = id_ok and rs_ok
    if ok:
        return ('ALLOW', 'both_sides' if (id_ok and rs_ok and not same) else ('identity_grant' if id_ok else 'resource_grant'))
    # ---- R6 default deny
    if model == 'IAM-2':
        return ('ALLOW', 'not_denied')
    if guard_cap and (idA or rsA): return ('DENY', 'guardrail_cap')
    if bcap: return ('DENY', 'boundary_cap')
    if not same and not one_side and (id_ok or rs_ok):
        return ('DENY', 'cross_account_missing_resource_grant' if id_ok else 'cross_account_missing_identity_grant')
    return ('DENY', 'no_grant')

MODELS = ['reference'] + list(VARIANTS)
