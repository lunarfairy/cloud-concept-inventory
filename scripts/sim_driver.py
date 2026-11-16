"""
sim_driver.py -- runs the full sim_v2 grid and produces all outputs with one command:

    python sim_driver.py                 # run (resumes if parts exist), merge, summarise, figure, env
    python sim_driver.py --workers 16    # number of independent worker processes (default 16)
    python sim_driver.py --summary-only  # skip simulation; rebuild CSVs/figure from parts/

Workers are independent subprocess.Popen processes (multiprocessing.Pool is not usable on the
host used here); each runs `python sim_driver.py --worker k K` and appends one JSON line per
replication to parts/part_k.jsonl. BLAS threads are pinned to 1 per worker.

Outputs: sim_v2_reps.csv, sim_v2_summary.csv, sim_v2_env.txt, fig_sim_v2.png, fig_sim_v2.pdf.
"""
import argparse
import glob
import json
import os
import platform
import subprocess
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "parts")
sys.path.insert(0, HERE)
import sim_v2 as S  # noqa: E402

PROCS = ("one", "pur", "orc", "orig")
RULES = ("sig", "es3", "es4", "nag")


def task_list():
    tasks = [(c, N, r) for c, (_, _, grid, reps) in S.CONDITIONS.items() for N in grid
             for r in range(1, reps + 1)]
    order = np.random.default_rng(S.BASE_SEED).permutation(len(tasks))   # balance heavy cells
    return [tasks[i] for i in order]


def done_tasks():
    done = set()
    for f in glob.glob(os.path.join(PARTS, "part_*.jsonl")):
        with open(f) as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                    done.add((d["cond"], d["N"], d["rep"]))
                except Exception:
                    pass
    return done


def worker(k, K):
    tasks = task_list()[k::K]
    done = done_tasks()
    path = os.path.join(PARTS, f"part_{k}.jsonl")
    with open(path, "a") as fh:
        for (c, N, r) in tasks:
            if (c, N, r) in done:
                continue
            rec = S.run_rep(c, N, r)
            fh.write(json.dumps(rec, default=float) + "\n"); fh.flush()


def run_grid(K):
    os.makedirs(PARTS, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
               PYTHONHASHSEED="0")
    pre = os.path.dirname(sys.executable)
    env["PATH"] = os.pathsep.join([pre, os.path.join(pre, "Library", "bin"), env.get("PATH", "")])
    t0 = time.time()
    procs = [subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker", str(k), str(K)],
                              env=env, cwd=HERE,
                              stdout=open(os.path.join(PARTS, f"w{k}.out"), "w"),
                              stderr=open(os.path.join(PARTS, f"w{k}.err"), "w"))
             for k in range(K)]
    rc = [p.wait() for p in procs]
    wall = time.time() - t0
    with open(os.path.join(PARTS, "grid_wall_seconds.txt"), "a") as fh:
        fh.write(f"{wall:.1f} workers={K} rc={rc}\n")
    print(f"grid wall time {wall/60:.1f} min, return codes {set(rc)}")


def merge():
    rows = []
    for f in sorted(glob.glob(os.path.join(PARTS, "part_*.jsonl"))):
        with open(f) as fh:
            rows += [json.loads(x) for x in fh if x.strip()]
    df = pd.DataFrame(rows).drop_duplicates(["cond", "N", "rep"]).sort_values(["cond", "N", "rep"])
    df.to_csv(os.path.join(HERE, "sim_v2_reps.csv"), index=False)
    return df


def _mse(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return (x.mean(), x.std(ddof=1) / np.sqrt(x.size)) if x.size > 1 else (np.nan, np.nan)


def summarise(df):
    out = []
    for (c, N), g in df.groupby(["cond", "N"], sort=False):
        base = dict(cond=c, N=N, n_sites=f"{g.n1.iloc[0]}/{g.n2.iloc[0]}/{g.n3.iloc[0]}",
                    reps=len(g), J=int(g.J.iloc[0]), m1=int(g.m1.iloc[0]), m0=int(g.m0.iloc[0]),
                    runtime_mean_s=g.runtime_s.mean(), runtime_total_s=g.runtime_s.sum())
        if "true_logit_dif_mean" in g and g.true_logit_dif_mean.notna().any():
            base["true_logit_dif_mean"] = g.true_logit_dif_mean.mean()
            base["true_logit_dif_share_ge04"] = g.true_logit_dif_ge04.mean()
        if "rmse_b" in g and g.rmse_b.notna().any():
            for v in ("rmse_b", "rmse_a", "bias_b", "bias_a", "rel_est", "rel_gen"):
                base[v], base[v + "_se"] = _mse(g[v])
            base["cal_nonconverged"] = int((g.cal_converged == 0).sum())
            base["cal_a_at_bound_total"] = int(g.cal_a_at_bound.sum())
            base["cal_iters_max"] = int(g.cal_iters.max())
        if "pair_n_flagged_dif" in g and g.pair_n_flagged_dif.notna().any():
            nf = g.pair_n_flagged_dif.sum()
            base["pair_flagged_dif_total"] = int(nf)
            for v in ("pair_all_true", "pair_any_true", "pair_false", "pair_exact"):
                base[v + "_rate"] = g[v].sum() / nf if nf else np.nan
        if "pur_anchor_size" in g:
            base["pur_anchor_size_mean"] = g.pur_anchor_size.mean()
            base["pur_anchor_capped_reps"] = int(g.pur_anchor_capped.sum())
            base["pur_anchor_ndif_mean"] = g.pur_anchor_ndif.mean()
        for p in PROCS:
            if f"{p}_sig_R" not in g or g[f"{p}_sig_R"].isna().all():
                continue
            gp = g[g[f"{p}_sig_R"].notna()]
            fails = dict(failed_tests=int(gp[f"{p}_n_fail"].sum()),
                         nonconv_tests=int(gp[f"{p}_n_nonconv"].sum()),
                         separation_tests=int(gp[f"{p}_n_sep"].sum()),
                         error_tests=int(gp[f"{p}_n_err"].sum()),
                         reps_with_failure=int((gp[f"{p}_n_fail"] > 0).sum()),
                         tests_total=int(len(gp) * gp.J.iloc[0]))
            for r in RULES:
                if f"{p}_{r}_R" not in gp or gp[f"{p}_{r}_R"].isna().all():
                    continue
                R, V, Sx = gp[f"{p}_{r}_R"], gp[f"{p}_{r}_V"], gp[f"{p}_{r}_S"]
                row = dict(base, procedure=p, rule=r, **fails)
                if row["m1"] > 0:
                    row["power"], row["power_se"] = _mse(Sx / gp.m1)
                    row["power_all_dif"] = (Sx == gp.m1).mean()
                row["fpr"], row["fpr_se"] = _mse(V / gp.m0)
                row["fdr"], row["fdr_se"] = _mse(V / np.maximum(R, 1))
                row["p_any_false"] = (V > 0).mean()
                row["mean_R"] = R.mean()
                out.append(row)
    sm = pd.DataFrame(out)
    first = ["cond", "N", "n_sites", "reps", "procedure", "rule", "power", "power_se", "fpr",
             "fpr_se", "fdr", "fdr_se", "p_any_false", "power_all_dif", "mean_R", "failed_tests",
             "nonconv_tests", "separation_tests", "error_tests", "reps_with_failure", "tests_total"]
    sm = sm[[c for c in first if c in sm] + [c for c in sm if c not in first]]
    sm.to_csv(os.path.join(HERE, "sim_v2_summary.csv"), index=False)
    return sm


def write_env():
    from importlib.metadata import version
    lines = [f"python {platform.python_version()} ({sys.version.split()[0]}, {platform.platform()})"]
    for pkg in ("numpy", "scipy", "statsmodels", "girth", "pandas", "matplotlib"):
        try:
            lines.append(f"{pkg} {version(pkg)}")
        except Exception as e:  # pragma: no cover
            lines.append(f"{pkg} unavailable ({e})")
    lines += ["",
              "2PL calibration: girth.twopl_mml (marginal maximum likelihood, N(0,1) latent density,",
              "  41 quadrature nodes on [-4.5, 4.5], lookup-table integration (girth defaults),",
              f"  max_iteration={S.GIRTH_MAXITER} (girth default 25), stop when max|delta a| < 1e-3,",
              "  discrimination bounded to [0.2, 5.0] by girth's fminbound).",
              f"DIF logistic regressions: statsmodels.discrete.discrete_model.Logit, method='newton', "
              f"maxiter={S.LOGIT_MAXITER}.",
              "Multiplicity: statsmodels.stats.multitest.multipletests ('fdr_bh' across items, 'holm' across pairs).",
              "R / mirt were NOT used.",
              f"Base seed {S.BASE_SEED}; replication seed = SeedSequence([base, condition code, N, rep]).",
              f"Host: {os.cpu_count()} logical CPUs; workers pinned to 1 BLAS thread."]
    with open(os.path.join(HERE, "sim_v2_env.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")


def figure(sm):
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.transforms import blended_transform_factory as btf
    mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8,
                         "axes.labelsize": 8, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
                         "legend.fontsize": 7, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    m = sm[(sm.cond == "M")]
    Ns = sorted(m.N.unique())
    # (procedure, rule, label, colour, marker, linestyle, x-dodge)
    series = [("one", "sig", "One-stage, BH only", "#9db4c8", "o", "--", -18),
              ("one", "es4", "One-stage, BH + |Δ| ≥ 0.4", "#4a6b8a", "o", "-", -6),
              ("pur", "sig", "Purified, BH only", "#f2b48a", "s", "--", 6),
              ("pur", "es4", "Purified, BH + |Δ| ≥ 0.4", "#c4501b", "s", "-", 18)]
    fig, axs = plt.subplots(1, 3, figsize=(7.1, 2.85), constrained_layout=True,
                            gridspec_kw=dict(width_ratios=[1.05, 1.05, 0.9]))
    for p, r, lab, col, mk, ls, dx in series:
        d = m[(m.procedure == p) & (m.rule == r)].sort_values("N")
        for ax, v in ((axs[0], "power"), (axs[1], "fdr")):
            ax.errorbar(d.N + dx, d[v], yerr=1.96 * d[v + "_se"], color=col, marker=mk, ms=3.5,
                        lw=1.6 if r == "es4" else 1.1, ls=ls, capsize=2, label=lab,
                        zorder=3 if p == "pur" and r == "es4" else 2)
    for ax, yv, txt in ((axs[0], 0.8, "0.80"), (axs[1], 0.05, "q = 0.05")):
        ax.axhline(yv, color="0.55", lw=0.8, ls=":", zorder=1)
        ax.text(1.01, yv, txt, color="0.4", fontsize=6.5, va="center", ha="left",
                transform=btf(ax.transAxes, ax.transData), clip_on=False)
    axs[0].set(xlabel="Examinees per site", ylabel="Power per DIF item", ylim=(0, 1.02))
    axs[0].set_title("Power, one-site DIF (b shift 0.5)", loc="left")
    axs[1].set(xlabel="Examinees per site", ylabel="Empirical FDR, mean of V / max(R, 1)")
    axs[1].set_title("False discovery rate", loc="left")
    top = max(0.1, float(m[m.procedure.isin(["one", "pur"])].eval("fdr + 1.96*fdr_se").max()) * 1.08)
    axs[1].set_ylim(0, top)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="outside lower center", ncol=4, handlelength=2.4,
               columnspacing=1.2)
    c = m[(m.procedure == "pur") & (m.rule == "sig")].sort_values("N")
    for v, lab, col, mk in (("rmse_a", "Discrimination (a)", "#7b5ea7", "^"),
                            ("rmse_b", "Difficulty (b)", "#3b7a57", "D")):
        axs[2].errorbar(c.N, c[v], yerr=1.96 * c[v + "_se"], color=col, marker=mk, ms=3.5, lw=1.3,
                        capsize=2, label=lab)
    axs[2].set(xlabel="Examinees per site", ylabel="RMSE, non-DIF items", ylim=(0, None))
    axs[2].legend(frameon=False, loc="lower left", handlelength=2.0)
    axs[2].set_title("2PL calibration RMSE", loc="left")
    for ax, L in zip(axs, "abc"):
        ax.set_xticks(Ns)
        ax.set_xlim(Ns[0] - 80, Ns[-1] + 80)
        ax.text(-0.02, 1.07, L, transform=ax.transAxes, fontweight="bold", fontsize=10,
                ha="right", va="bottom")
    fig.savefig(os.path.join(HERE, "fig_sim_v2.png"), dpi=300)
    fig.savefig(os.path.join(HERE, "fig_sim_v2.pdf"))
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", nargs=2, type=int)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--summary-only", action="store_true")
    a = ap.parse_args()
    if a.worker:
        worker(*a.worker)
        sys.exit(0)
    if not a.summary_only:
        run_grid(a.workers)
    df = merge()
    sm = summarise(df)
    write_env()
    figure(sm)
    print(f"{len(df)} replications, {len(sm)} summary rows")
