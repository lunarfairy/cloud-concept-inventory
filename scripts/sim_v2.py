"""
sim_v2.py -- Psychometric design simulation (version 2) for a multi-site
Cloud Concept Inventory calibration.

Replaces phase2_sim_mod.py (round 1). Changes, each answering a verified review point:
  (1) Software is reported as it is: 2PL calibration uses the Python package
      girth (twopl_mml, marginal maximum likelihood), NOT R mirt; logistic
      regressions use statsmodels Logit (Newton-Raphson). Versions -> sim_v2_env.txt.
  (2) Difficulties are drawn from a truncated normal, scipy.stats.truncnorm on
      [-2.5, 2.5] (mean 0, SD 1 before truncation), not np.clip(normal).
  (3) DIF is screened across the THREE sites (two site dummies + two
      score x site interactions, 4-df omnibus LR test), not a pooled binary
      "reference vs both other sites" contrast. The pooled binary analysis of
      round 1 is kept only as `orig` for condition S1 (and as a comparison in M).
  (4) Empirical FDR (V / max(R, 1), averaged over replications) is recorded
      alongside per-null-item FPR. A two-stage purification of the matching
      score and an oracle (true-anchor) analysis are included as diagnostics.
  (5) Every logistic fit's convergence status is recorded (no silent p = 1,
      no global warning suppression). Failed tests get p = NaN, are excluded
      from the BH family and cannot be flagged; their count is reported.
  (6) A shift of +d in b_j at a site is a shift of -a_j * d in that site's
      conditional log-odds given theta (2PL logit = a_j (theta - b_j)).
  (7) Effect-size rule on the logit scale: an item is retained as DIF only if
      it is BH-significant AND the largest pairwise site difference in its
      estimated conditional log-odds intercept at the pooled mean matching score
      is >= 0.4 logit (0.3 also reported). 0.426 logit = 1.0 ETS delta unit,
      the boundary between ETS category A (negligible) and B (MH D-DIF =
      -2.35 ln alpha_MH); 0.4 is that boundary rounded down.

Everything a replication needs is in `run_rep(cond, N, rep)`; seeds are derived
deterministically from (BASE_SEED, condition code, N, rep) via numpy SeedSequence.
"""
import time
import warnings
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
from statsmodels.tools.sm_exceptions import (ConvergenceWarning,
                                             PerfectSeparationWarning,
                                             HessianInversionWarning)
try:
    from statsmodels.tools.sm_exceptions import PerfectSeparationError
except ImportError:  # pragma: no cover
    class PerfectSeparationError(Exception):
        pass

BASE_SEED = 20261111
ALPHA_Q = 0.05          # BH false discovery level across items
ALPHA_PAIR = 0.05       # Holm family-wise level across the 3 pairwise contrasts of a flagged item
ES_THRESHOLDS = (0.3, 0.4)  # logit; 0.4 is the main rule
NAGEL_THR = 0.035       # round-1 Nagelkerke rule (Jodoin & Gierl), used only by `orig`
LOGIT_MAXITER = 100
GIRTH_MAXITER = 100     # girth default is 25; raised so non-convergence is rare and countable

# ----------------------------------------------------------------------------
# Conditions
# ----------------------------------------------------------------------------
BASE = dict(J=35, K=4, dif_mag=0.5, dif_mode="one_site", a_ratio=0.7,
            mu=(0.0, -0.2, 0.2), unequal=None, testlet_items=0, testlet_var=0.5,
            n_domains=1, domain_r=0.7, subgroup=False, subgroup_prop=0.3,
            calib=False, orig=False)

CONDITIONS = {
    # name: (code, overrides, N grid, reps)
    "M":   (1,  dict(calib=True, orig=True), (300, 500, 750, 1000), 500),
    "S0":  (2,  dict(K=0), (500, 750, 1000), 200),                 # added diagnostic: no DIF
    "S1":  (3,  dict(dif_mode="pooled", orig=True), (500, 750, 1000), 200),
    "S2":  (4,  dict(dif_mode="opposing"), (500, 750, 1000), 200),
    "S3a": (5,  dict(dif_mag=0.3), (500, 750, 1000), 200),
    "S3b": (6,  dict(dif_mag=0.7), (500, 750, 1000), 200),
    "S4a": (7,  dict(K=2), (500, 750, 1000), 200),
    "S4b": (8,  dict(K=8), (500, 750, 1000), 200),
    "S5a": (9,  dict(unequal=(500, 750, 1000)), (0,), 200),        # N label 0 = unequal 500/750/1000
    "S5b": (10, dict(mu=(0.0, -0.5, 0.5)), (500, 750, 1000), 200),
    "S6":  (11, dict(dif_mode="nonuniform"), (500, 750, 1000), 200),
    "S7":  (12, dict(testlet_items=18, calib=True), (500, 750, 1000), 200),
    "S8":  (13, dict(n_domains=7, calib=True), (500, 750, 1000), 200),
    "S9":  (14, dict(J=28, calib=True), (500, 750, 1000), 200),
    "S10": (15, dict(subgroup=True, K=4), (500, 750, 1000), 200),
}


def cond_params(cond):
    p = dict(BASE)
    p.update(CONDITIONS[cond][1])
    return p


def dif_positions(J, K):
    """Fixed, evenly spread DIF item positions (parameters are random, so positions are arbitrary)."""
    if K == 0:
        return np.array([], dtype=int)
    return np.unique(np.round(np.linspace(2, J - 3, K)).astype(int))


# ----------------------------------------------------------------------------
# Generator
# ----------------------------------------------------------------------------
def generate(p, N, rng):
    """Return dict with X (n x J 0/1), grp (site 0..2), sub (focal subgroup 0/1 or None),
    generating a, b, DIF item indices and the per-person shifted parameters."""
    J, K = p["J"], p["K"]
    a = rng.lognormal(0.15, 0.3, J)                                    # a ~ LogNormal(mu=0.15, sigma=0.3)
    b = stats.truncnorm.rvs(-2.5, 2.5, loc=0.0, scale=1.0, size=J, random_state=rng)
    ns = p["unequal"] if p["unequal"] is not None else (N, N, N)
    grp = np.repeat(np.arange(3), ns)
    n = grp.size
    mu = np.asarray(p["mu"])
    # abilities
    if p["n_domains"] > 1:
        D = p["n_domains"]
        S = np.full((D, D), p["domain_r"]); np.fill_diagonal(S, 1.0)
        th_d = mu[grp][:, None] + rng.multivariate_normal(np.zeros(D), S, size=n)  # n x D
        dom = np.arange(J) // (J // D)                                  # 5 consecutive items per domain
        TH = th_d[:, dom]                                               # n x J
    else:
        TH = np.repeat(rng.normal(mu[grp], 1.0)[:, None], J, axis=1)
    if p["testlet_items"] > 0:                                          # Bradlow-Wainer testlet effects
        T = p["testlet_items"] // 2
        gam = rng.normal(0.0, np.sqrt(p["testlet_var"]), size=(n, T))
        tl = np.arange(p["testlet_items"]) // 2
        TH[:, :p["testlet_items"]] = TH[:, :p["testlet_items"]] + gam[:, tl]
    dif = dif_positions(J, K)
    B = np.tile(b, (n, 1)); A = np.tile(a, (n, 1))
    sub = None
    d = p["dif_mag"]
    if p["subgroup"]:
        sub = (rng.random(n) < p["subgroup_prop"]).astype(int)          # independent of site and ability
        B[np.ix_(sub == 1, dif)] += d
    elif K > 0:
        mode = p["dif_mode"]
        if mode == "one_site":
            B[np.ix_(grp == 1, dif)] += d
        elif mode == "pooled":
            B[np.ix_(grp != 0, dif)] += d
        elif mode == "opposing":
            B[np.ix_(grp == 1, dif)] += d
            B[np.ix_(grp == 2, dif)] -= d
        elif mode == "nonuniform":
            A[np.ix_(grp == 1, dif)] *= p["a_ratio"]
        else:
            raise ValueError(mode)
    P = 1.0 / (1.0 + np.exp(-A * (TH - B)))
    X = (rng.random(P.shape) < P).astype(np.int8)
    return dict(X=X, grp=grp, sub=sub, a=a, b=b, dif=dif, ns=ns)


# ----------------------------------------------------------------------------
# Logistic-regression DIF screen
# ----------------------------------------------------------------------------
def fit_logit(y, Xd):
    """Fit Logit by Newton; return (result or None, status) with status in
    {'ok','nonconv','separation','error'}. Warnings are captured, not suppressed."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            res = sm.Logit(y, Xd).fit(disp=0, method="newton", maxiter=LOGIT_MAXITER)
        except PerfectSeparationError:
            return None, "separation"
        except Exception:
            return None, "error"
    cats = {type(x.message) if isinstance(x.message, Warning) else None for x in w}
    if any(issubclass(c, PerfectSeparationWarning) for c in cats if c):
        return res, "separation"
    if (not res.mle_retvals.get("converged", False)) or not np.isfinite(res.llf) \
            or any(issubclass(c, (ConvergenceWarning, HessianInversionWarning)) for c in cats if c):
        return res, "nonconv"
    return res, "ok"


def _pairs(G):
    return [(r, s) for r in range(G) for s in range(r + 1, G)]


def screen(X, g, anchor, match="total", nagel=False):
    """Per-item LR DIF screen.

    X: n x J responses; g: group codes 0..G-1 (0 = reference);
    anchor: boolean J-vector of items forming the matching score.
    match='total': matching score = sum of anchor items plus the studied item
                   (studied item always included, Holland-Thayer convention);
    match='rest' : sum of anchor items excluding the studied item (round-1 `orig`).
    Model 0: logit P(y=1) = b0 + b1 z;   Model 1 adds G-1 group dummies and G-1 z x group terms.
    z = matching score standardised in the pooled sample, so dummy coefficients are
    group differences in the conditional log-odds at the pooled mean score.
    Returns dict of per-item arrays.
    """
    n, J = X.shape
    G = int(g.max()) + 1
    Dm = np.column_stack([(g == k).astype(float) for k in range(1, G)])
    pairs = _pairs(G)
    out = dict(p=np.full(J, np.nan), eff=np.full(J, np.nan), nag=np.full(J, np.nan),
               pw=np.full((J, len(pairs)), np.nan), delta=np.full((J, G - 1), np.nan),
               status=np.empty(J, dtype=object))
    Xa = X[:, anchor].sum(1).astype(float)
    for j in range(J):
        if match == "total":
            s = Xa + (0.0 if anchor[j] else X[:, j])
        else:
            s = Xa - (X[:, j] if anchor[j] else 0.0)
        sd = s.std()
        y = X[:, j].astype(float)
        if sd == 0 or y.min() == y.max():
            out["status"][j] = "error"; continue
        z = (s - s.mean()) / sd
        X0 = np.column_stack([np.ones(n), z])
        X1 = np.column_stack([X0, Dm, z[:, None] * Dm])
        r0, s0 = fit_logit(y, X0)
        r1, s1 = fit_logit(y, X1)
        st = s1 if s0 == "ok" else s0
        out["status"][j] = st
        if st != "ok":
            continue
        lr = max(2.0 * (r1.llf - r0.llf), 0.0)
        out["p"][j] = stats.chi2.sf(lr, 2 * (G - 1))
        dl = r1.params[2:2 + G - 1]
        out["delta"][j] = dl
        full = np.concatenate([[0.0], dl])
        out["eff"][j] = max(abs(full[r] - full[s_]) for r, s_ in pairs)
        if nagel:
            ll0n = r0.llnull
            rr = lambda l: (1 - np.exp(2 * (ll0n - l) / n)) / (1 - np.exp(2 * ll0n / n))
            out["nag"][j] = rr(r1.llf) - rr(r0.llf)
        # pairwise 2-df Wald tests (intercept and slope difference) between groups r and s
        V = r1.cov_params(); beta = r1.params
        for k, (r, s_) in enumerate(pairs):
            L = np.zeros((2, beta.size))
            for row, off in enumerate((2, 2 + G - 1)):
                if s_ > 0: L[row, off + s_ - 1] += 1.0
                if r > 0:  L[row, off + r - 1] -= 1.0
            c = L @ beta
            try:
                W = float(c @ np.linalg.solve(L @ V @ L.T, c))
                out["pw"][j, k] = stats.chi2.sf(W, 2)
            except np.linalg.LinAlgError:
                pass
    return out


def bh_flags(p, q=ALPHA_Q):
    """BH over the items with a valid p-value; failed tests are not flagged."""
    flag = np.zeros(p.size, bool)
    ok = np.isfinite(p)
    if ok.sum() > 0:
        flag[ok] = multipletests(p[ok], alpha=q, method="fdr_bh")[0]
    return flag


def holm_pairs(pw_row, alpha=ALPHA_PAIR):
    ok = np.isfinite(pw_row)
    rej = np.zeros(pw_row.size, bool)
    if ok.sum():
        rej[ok] = multipletests(pw_row[ok], alpha=alpha, method="holm")[0]
    return rej


def purified_screen(X, g, nagel=False):
    """Two-stage procedure. Stage 1: all items in the matching score, BH-flag.
    Stage 2: BH-flagged items removed from the matching score (each studied item
    still included in its own score), all items retested, BH again.
    If stage 1 flags more than half the items, the anchor is the ceil(J/2) items with
    the largest stage-1 p-values (recorded as anchor_capped)."""
    J = X.shape[1]
    s1 = screen(X, g, np.ones(J, bool), nagel=nagel)
    f1 = bh_flags(s1["p"])
    anchor = ~f1
    capped = False
    kmin = int(np.ceil(J / 2))
    if anchor.sum() < kmin:
        capped = True
        pp = np.where(np.isfinite(s1["p"]), s1["p"], 1.0)
        anchor = np.zeros(J, bool); anchor[np.argsort(-pp)[:kmin]] = True
    s2 = screen(X, g, anchor, nagel=nagel)
    return s1, s2, anchor, capped


# ----------------------------------------------------------------------------
# Calibration (girth 2PL MML) and marginal reliability
# ----------------------------------------------------------------------------
NODES, WTS = np.polynomial.hermite_e.hermegauss(41); WTS = WTS / WTS.sum()


def marginal_rel(X, a, b):
    """EAP marginal reliability var(EAP) / (var(EAP) + mean posterior variance), N(0,1) prior,
    41-node Gauss-Hermite quadrature. X: n x J."""
    P = np.clip(1 / (1 + np.exp(-a[:, None] * (NODES[None, :] - b[:, None]))), 1e-9, 1 - 1e-9)
    LL = X @ np.log(P) + (1 - X) @ np.log(1 - P)
    LL -= LL.max(1, keepdims=True)
    L = np.exp(LL) * WTS[None, :]
    post = L / L.sum(1, keepdims=True)
    eap = post @ NODES
    psd2 = post @ NODES ** 2 - eap ** 2
    return eap.var() / (eap.var() + psd2.mean())


_GIRTH_ITERS = [0]


def _install_girth_counter():
    """girth.twopl_mml returns no convergence flag; count EM cycles by wrapping LatentPDF.__call__
    (called exactly once per cycle with the cycle index)."""
    import sys
    import girth  # noqa: F401
    mod = sys.modules["girth.unidimensional.polytomous.grm_mml"]
    LP = mod.LatentPDF
    if getattr(LP, "_wrapped_counter", False):
        return
    orig = LP.__call__

    def wrapped(self, partial_int, iteration):
        _GIRTH_ITERS[0] = iteration + 1
        return orig(self, partial_int, iteration)
    LP.__call__ = wrapped
    LP._wrapped_counter = True


def calibrate(X, a, b, dif):
    import girth
    _install_girth_counter()
    _GIRTH_ITERS[0] = 0
    J = X.shape[1]
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        est = girth.twopl_mml(X.T.astype(int), {"max_iteration": GIRTH_MAXITER})
    ah, bh = np.asarray(est["Discrimination"], float), np.asarray(est["Difficulty"], float).ravel()
    nd = np.setdiff1d(np.arange(J), dif)
    ok = np.isfinite(ah).all() and np.isfinite(bh).all()
    r = dict(cal_iters=_GIRTH_ITERS[0], cal_converged=int(_GIRTH_ITERS[0] < GIRTH_MAXITER and ok),
             cal_warnings=len(w), cal_a_at_bound=int(((ah <= 0.2001) | (ah >= 4.999)).sum()))
    if ok:
        r.update(rmse_b=np.sqrt(np.mean((bh[nd] - b[nd]) ** 2)),
                 rmse_a=np.sqrt(np.mean((ah[nd] - a[nd]) ** 2)),
                 bias_b=np.mean(bh[nd] - b[nd]), bias_a=np.mean(ah[nd] - a[nd]),
                 rel_est=marginal_rel(X.astype(float), ah, bh))
    r["rel_gen"] = marginal_rel(X.astype(float), a, b)   # reliability from generating parameters
    return r


# ----------------------------------------------------------------------------
# One replication
# ----------------------------------------------------------------------------
def _counts(flag, isdif):
    R = int(flag.sum()); V = int((flag & ~isdif).sum()); S = int((flag & isdif).sum())
    return R, V, S


def _record(rec, tag, out, flag_sig, isdif, nagel=False):
    """Add R/V/S for significance-only and combined rules, plus failure counts."""
    rules = {"sig": flag_sig}
    for t in ES_THRESHOLDS:
        eff = np.where(np.isfinite(out["eff"]), out["eff"], 0.0)
        rules[f"es{int(round(t * 10))}"] = flag_sig & (eff >= t)
    if nagel:
        nag = np.where(np.isfinite(out["nag"]), out["nag"], 0.0)
        rules["nag"] = flag_sig & (nag >= NAGEL_THR)
    for rn, f in rules.items():
        R, V, S = _counts(f, isdif)
        rec[f"{tag}_{rn}_R"], rec[f"{tag}_{rn}_V"], rec[f"{tag}_{rn}_S"] = R, V, S
    st = out["status"]
    rec[f"{tag}_n_fail"] = int(sum(x != "ok" for x in st))
    rec[f"{tag}_n_nonconv"] = int(sum(x == "nonconv" for x in st))
    rec[f"{tag}_n_sep"] = int(sum(x == "separation" for x in st))
    rec[f"{tag}_n_err"] = int(sum(x == "error" for x in st))
    if isdif.any():
        e = out["eff"][isdif]
        rec[f"{tag}_eff_dif_mean"] = float(np.nanmean(e)) if np.isfinite(e).any() else np.nan
    e0 = out["eff"][~isdif]
    rec[f"{tag}_eff_null_mean"] = float(np.nanmean(e0)) if np.isfinite(e0).any() else np.nan


def true_pairs(p):
    """Which of the pairs (0,1),(0,2),(1,2) truly differ for DIF items."""
    m = p["dif_mode"]
    return {"one_site": (True, False, True), "nonuniform": (True, False, True),
            "pooled": (True, True, False), "opposing": (True, True, True)}[m]


def run_rep(cond, N, rep):
    p = cond_params(cond)
    code = CONDITIONS[cond][0]
    t0 = time.perf_counter()
    rng = np.random.default_rng(np.random.SeedSequence([BASE_SEED, code, int(N), int(rep)]))
    gd = generate(p, N, rng)
    X, grp, dif, a = gd["X"], gd["grp"], gd["dif"], gd["a"]
    J = X.shape[1]
    isdif = np.zeros(J, bool); isdif[dif] = True
    rec = dict(cond=cond, N=int(N), n1=int(gd["ns"][0]), n2=int(gd["ns"][1]), n3=int(gd["ns"][2]),
               rep=int(rep), J=J, m1=int(isdif.sum()), m0=int((~isdif).sum()))
    # generating effect in theta-metric conditional log-odds: |a_j * d| for uniform DIF
    if isdif.any():
        ta = a[dif] * p["dif_mag"]
        rec["true_logit_dif_mean"] = float(ta.mean()) if p["dif_mode"] != "nonuniform" else np.nan
        rec["true_logit_dif_ge04"] = float((ta >= 0.4).mean()) if p["dif_mode"] != "nonuniform" else np.nan
    g = gd["sub"] if p["subgroup"] else grp
    # one-stage and two-stage purified screens
    s1, s2, anchor, capped = purified_screen(X, g)
    f1, f2 = bh_flags(s1["p"]), bh_flags(s2["p"])
    _record(rec, "one", s1, f1, isdif)
    _record(rec, "pur", s2, f2, isdif)
    rec["pur_anchor_size"] = int(anchor.sum()); rec["pur_anchor_capped"] = int(capped)
    rec["pur_anchor_ndif"] = int((anchor & isdif).sum())
    # oracle diagnostic: matching score from the true non-DIF items only
    if isdif.any():
        so = screen(X, g, ~isdif)
        _record(rec, "orc", so, bh_flags(so["p"]), isdif)
    # pairwise follow-up (Holm over the 3 site pairs) for purified BH-flagged DIF items
    if not p["subgroup"] and isdif.any():
        tp = np.array(true_pairs(p))
        n_fl = n_all_true = n_any_true = n_false = n_exact = 0
        for j in np.where(f2 & isdif)[0]:
            rej = holm_pairs(s2["pw"][j])
            n_fl += 1
            n_all_true += int(rej[tp].all()); n_any_true += int(rej[tp].any())
            n_false += int(rej[~tp].any()) if (~tp).any() else 0
            n_exact += int((rej == tp).all())
        rec.update(pair_n_flagged_dif=n_fl, pair_all_true=n_all_true, pair_any_true=n_any_true,
                   pair_false=n_false, pair_exact=n_exact)
        # null items flagged: how many have >= 1 Holm-significant pair
        rec["pair_null_flagged_anysig"] = int(sum(holm_pairs(s2["pw"][j]).any()
                                                  for j in np.where(f2 & ~isdif)[0]))
    # round-1 analysis: rest score, binary reference-vs-others contrast, Nagelkerke rule, one stage
    if p["orig"]:
        so = screen(X, (grp != 0).astype(int), np.ones(J, bool), match="rest", nagel=True)
        _record(rec, "orig", so, bh_flags(so["p"]), isdif, nagel=True)
    if p["calib"]:
        rec.update(calibrate(X, gd["a"], gd["b"], dif))
    rec["runtime_s"] = time.perf_counter() - t0
    return rec


if __name__ == "__main__":
    import sys
    import json
    c, N, r = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    print(json.dumps(run_rep(c, N, r), default=float, indent=1))
