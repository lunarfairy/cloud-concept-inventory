# Psychometric design simulation, version 2: multi-site calibration and DIF screening

All numbers are read from `sim_v2_summary.csv` (condition level) and `sim_v2_reps.csv` (replication level), produced by `python sim_driver.py`. Monte Carlo standard errors (MC SE) are in parentheses. No human-participant data are involved: everything below is simulated.

## Methods (matches `sim_v2.py`)

**Software.** Simulation and analysis were run in Python 3.11.16 with numpy 2.4.6, scipy 1.17.1, statsmodels 0.15.0 and girth 0.8.0. The round-1 text said R mirt; that was wrong, because no R code was used. Two-parameter logistic (2PL) calibration used `girth.twopl_mml`, which is marginal maximum likelihood with a N(0,1) latent density, 41 quadrature nodes on [−4.5, 4.5], and girth's lookup-table integration. The iteration cap was raised from girth's default of 25 to 100 EM cycles, with convergence declared at max|Δa| < 10⁻³. Logistic regressions used `statsmodels` `Logit` (Newton–Raphson, at most 100 iterations). BH and Holm adjustments used `statsmodels.stats.multitest.multipletests`.

**Data generation.** Each replication draws new item parameters. Discriminations are a_j ~ LogNormal(μ = 0.15, σ = 0.3), as in round 1 (median 1.16). Difficulties are b_j ~ N(0, 1) truncated to [−2.5, 2.5] via `scipy.stats.truncnorm`; round 1 used `np.clip` of a normal draw, which piles mass at the bounds. Responses follow P(X_ij = 1) = logistic(a_j(θ_i − b_j)). There are three sites with ability θ ~ N(μ_s, 1), where μ = (0, −0.2, +0.2), and n examinees per site. DIF items sit at fixed positions round(linspace(2, J−3, K)), i.e. items 2, 12, 22 and 32 (0-based) for J = 35 and K = 4. Item parameters are random, so the positions are arbitrary.

In the main condition (M), the DIF items are 0.5 units harder on the θ scale (b_j + 0.5) at site 2 only (μ = −0.2). Given θ, this lowers the conditional log-odds at site 2 by a_j × 0.5. It is therefore not a constant 0.5 logit: over replications the mean generating shift was 0.605 logit, and 89.6% of DIF items had a_j × 0.5 ≥ 0.4.

Each replication has its own seed, `SeedSequence([20261111, condition code, n, replication])`.

**Screening procedure.** For each item j, a matching score S is formed as the sum of the anchor items plus item j itself (the studied item is always included). S is standardised in the pooled sample to z. Two logistic regressions are fitted:
- Model 0: logit P(X_j = 1) = β₀ + β₁z.
- Model 1: adds dummies for sites 2 and 3 (δ₂, δ₃) and the z × site interactions (γ₂, γ₃).

The omnibus likelihood-ratio statistic for Model 1 against Model 0 is referred to χ² with 4 df. BH is applied at q = 0.05 across the items whose fits succeeded.

A fit counts as failed if statsmodels reports non-convergence, a convergence or Hessian-inversion warning, or perfect separation, or if it raises an error. Warnings are captured per fit, not suppressed. A failed test gets p = NaN, is excluded from the BH family, cannot be flagged, and is counted.

The **one-stage** analysis uses all J items as anchor. The **two-stage purified** analysis then removes every BH-flagged item from the anchor and retests all J items with the purified matching score (each studied item still included in its own score), followed by a second BH step. A safeguard keeps the ⌈J/2⌉ items with the largest stage-1 p-values if stage 1 flags more than half the items; it never triggered (0 of 10,000 replications).

An **oracle** analysis uses the true non-DIF items as anchor. It is a diagnostic only, and is not available in practice.

**Effect-size (combined) rule.** Because z = 0 is the pooled mean score, δ₂, δ₃ and δ₃ − δ₂ are the pairwise site differences in the item's conditional log-odds at the mean matching score. An item is retained as DIF only if it is BH-significant **and** max(|δ₂|, |δ₃|, |δ₃ − δ₂|) ≥ 0.4 logit; 0.3 logit is also reported.

The 0.4 threshold follows the ETS Mantel–Haenszel categories. An |MH D-DIF| of 1.0 delta unit, the boundary between category A (negligible) and category B, corresponds to |ln α_MH| = 1/2.35 = 0.426 logit, because MH D-DIF = −2.35 ln α_MH. We round this down to 0.4 so the rule stays on the logit scale of the logistic model.

This rule replaces the round-1 Nagelkerke ΔR² ≥ 0.035 rule. Under that rule, a 0.5 b-shift almost never counts as DIF (power ≤ 0.011 in every cell below).

**Pairwise follow-up.** For each item flagged in the purified analysis, three 2-df Wald tests compare sites pairwise, each jointly testing the intercept and slope difference within Model 1. Holm adjustment at α = 0.05 is applied across the three pairs within the item.

**Conditions.** The main condition M uses J = 35, K = 4 DIF items, n ∈ {300, 500, 750, 1000} per site and 500 replications per cell. Every sensitivity condition uses n ∈ {500, 750, 1000} and 200 replications, unless stated otherwise.
- **S0** (added diagnostic): no DIF items. FDR then equals the family-wise error rate.
- **S1**: round-1 configuration, with the 0.5 shift at both sites 2 and 3. Analysed with both the new 3-site procedure and the round-1 analysis (`orig`): rest score (item excluded) matching, a binary reference-vs-other-sites contrast with a 2-df LR test, BH, and Nagelkerke ΔR² ≥ 0.035, one stage. `orig` was also applied to M.
- **S2**: opposing DIF, +0.5 at site 2 and −0.5 at site 3.
- **S3**: DIF magnitude 0.3 (S3a) or 0.7 (S3b).
- **S4**: K = 2 (S4a; items 2 and 32) or K = 8 (S4b; items 2, 6, 11, 15, 19, 23, 28, 32).
- **S5a**: unequal sites, n = 500/750/1000 for sites 1/2/3 (DIF at site 2, n = 750). One cell, 200 replications.
- **S5b**: site means 0, −0.5, +0.5.
- **S6**: non-uniform DIF, with a_j multiplied by 0.7 at site 2 and no b shift.
- **S7**: local dependence. Items 0–17 form 9 two-item testlets, with logit a_j(θ_i + γ_i,t(j) − b_j) and γ ~ N(0, 0.5) (Bradlow–Wainer form). DIF items 2 and 12 lie in testlets. Fitted with the unidimensional model.
- **S8**: multidimensionality. Seven domain abilities with correlation 0.7, each with site mean μ_s and variance 1; items 5k…5k+4 load on domain k. Fitted unidimensionally.
- **S9**: final form, J = 28 (DIF items 2, 10, 17, 25).
- **S10**: subgroup-DIF feasibility. A binary subgroup (focal with probability 0.3, independent of site and ability) within the pooled 3 × n sample, with the 0.5 b shift on 4 items for the focal group and no site DIF. Same screen with a binary group (2-df LR test, |δ| ≥ 0.4 rule, purification).

**Calibration.** Calibration precision was computed in M (and also in S7–S9) by fitting girth 2PL MML to the pooled sample. Reported quantities are:
- RMSE and mean bias of b and a over non-DIF items;
- EAP marginal reliability, var(EAP) / (var(EAP) + mean posterior variance) under a N(0,1) prior with 41 Gauss–Hermite nodes, computed with both the estimated and the generating parameters.

**Outcomes.** Per-item power is the mean over replications of S/K. The per-null-item false-positive rate (FPR) is the mean of V/(J − K). Empirical FDR is the mean of V/max(R, 1). Also reported: P(V ≥ 1), failed fits and runtime. MC SE = SD over replications / √R.

**Compute.** The grid had 10,000 replications. It ran on 16 independent worker processes (one BLAS thread each) on a 20-logical-CPU Windows host, taking 169.7 min wall time and 43.7 worker-hours. The host's CPU allocation to the workers was throttled during the run: per-process utilisation was about 10–20% of a core. Per-replication runtimes therefore overstate the cost on an unloaded machine; for scale, one M replication at n = 750 took 3.3 s when run alone.

## Results

### Main condition (M): power, FDR, and recommended sample size
Results are for 500 replications per cell; values are estimate (MC SE).

| n per site | One-stage, BH: power | One-stage, BH: FDR | Purified, BH: power | Purified, BH: FDR | Purified, BH + \|Δ\| ≥ 0.4: power | Purified, BH + \|Δ\| ≥ 0.4: FDR | Oracle anchor, BH: FDR |
|---|---|---|---|---|---|---|---|
| 300 | 0.311 (0.011) | 0.069 (0.008) | 0.348 (0.013) | 0.054 (0.008) | 0.348 (0.013) | 0.049 (0.008) | 0.049 (0.007) |
| 500 | 0.615 (0.011) | 0.080 (0.007) | 0.674 (0.012) | 0.056 (0.006) | 0.667 (0.012) | 0.039 (0.005) | 0.055 (0.005) |
| 750 | 0.777 (0.010) | 0.081 (0.006) | 0.836 (0.009) | 0.057 (0.005) | 0.815 (0.009) | 0.031 (0.004) | 0.055 (0.005) |
| 1000 | 0.884 (0.007) | 0.085 (0.006) | 0.918 (0.007) | 0.050 (0.004) | 0.870 (0.008) | 0.018 (0.003) | 0.054 (0.005) |

**The FDR excess has two parts: matching-score contamination and residual observed-score bias.**
- The one-stage screen reproduces the round-1 problem. Its FDR is 0.081 (0.006) at 750/site and 0.085 (0.006) at 1000/site, against BH's nominal 0.05.
- Without DIF (S0), BH alone held FDR at 0.050–0.055. The excess therefore needs DIF items in the matching score.
- With the true anchor (oracle), FDR dropped to 0.055 (0.005) at 750/site.
- Two-stage purification came close to the oracle: 0.057 (0.005) at 750/site and 0.050 (0.004) at 1000/site. On average 0.89 of the 4 DIF items remained in the purified anchor at 750/site, and 0.46 at 1000/site.

So the round-1 inflation came mainly from same-direction DIF items contaminating the matching score. Rest-score versus total-score matching is not the main factor. In S1, the new one-stage total-score screen is also inflated, with FDR 0.062–0.088 against 0.083–0.098 for the round-1 rest-score binary analysis. Purification, not the choice of matching score, removes most of the excess.

The oracle and purified BH-only FDRs stay slightly above the BH bound q·m₀/m = 0.044. That residual comes from matching on an observed score when sites differ in ability, and it grows with larger ability gaps (S5b below). The combined rule removes it. The purified combined rule had FDR 0.049 (0.008), 0.039 (0.005), 0.031 (0.004) and 0.018 (0.003) at 300, 500, 750 and 1000 per site.

**Recommended n.** Under the purified combined rule (BH q = 0.05 and |Δ| ≥ 0.4 logit), per-item power was:

| n per site | Power (MC SE) |
|---|---|
| 300 | 0.348 (0.013) |
| 500 | 0.667 (0.012) |
| 750 | 0.815 (0.009) |
| 1000 | 0.870 (0.008) |

The smallest grid value with power ≥ 0.80 is **750 per site** (2,250 in total). Its 95% MC interval is 0.796–0.833, so 750 sits at the threshold. Linear interpolation between 500 and 750 gives about 725 per site; this is indicative only. At **1000 per site** the rule has a margin: power 0.870 (0.008), FDR 0.018 (0.003).

The 0.4 rule costs little power at 750/site: BH-only power was 0.836 against 0.815 with the rule. The cost is larger at 1000/site, with power 0.918 against 0.870. Under the 0.4 rule power is capped below 1: about 10% of DIF items have a generating conditional log-odds shift a_j × 0.5 below 0.4, and estimation in the observed-score metric adds further attenuation. With the 0.3 threshold, power was 0.833 (0.009) and FDR 0.044 (0.005) at 750/site; at 1000/site they were 0.914 (0.007) and 0.027 (0.003).

**Per-null-item FPR and failures (M).**

| N/site | Procedure | Per-null-item FPR | P(≥1 false flag) | Failed fits (non-converged) / tests | Mean runtime per replication (s) |
|---|---|---|---|---|---|
| 300 | One-stage | 0.0057 (BH) / 0.0053 (BH+0.4) | 0.154 / 0.144 | 0 (0) / 17500 | 23.9 |
| 300 | Purified | 0.0042 (BH) / 0.0037 (BH+0.4) | 0.118 / 0.102 | 1 (1) / 17500 | 23.9 |
| 300 | Oracle anchor | 0.0045 (BH) / 0.0039 (BH+0.4) | 0.124 / 0.106 | 1 (1) / 17500 | 23.9 |
| 500 | One-stage | 0.0098 (BH) / 0.0071 (BH+0.4) | 0.252 / 0.192 | 0 (0) / 17500 | 27.4 |
| 500 | Purified | 0.0068 (BH) / 0.0045 (BH+0.4) | 0.196 / 0.132 | 0 (0) / 17500 | 27.4 |
| 500 | Oracle anchor | 0.0070 (BH) / 0.0049 (BH+0.4) | 0.198 / 0.138 | 0 (0) / 17500 | 27.4 |
| 750 | One-stage | 0.0117 (BH) / 0.0074 (BH+0.4) | 0.298 / 0.202 | 0 (0) / 17500 | 32.4 |
| 750 | Purified | 0.0083 (BH) / 0.0043 (BH+0.4) | 0.224 / 0.120 | 0 (0) / 17500 | 32.4 |
| 750 | Oracle anchor | 0.0082 (BH) / 0.0042 (BH+0.4) | 0.222 / 0.120 | 0 (0) / 17500 | 32.4 |
| 1000 | One-stage | 0.0138 (BH) / 0.0052 (BH+0.4) | 0.324 / 0.146 | 0 (0) / 17500 | 37.0 |
| 1000 | Purified | 0.0079 (BH) / 0.0026 (BH+0.4) | 0.214 / 0.078 | 0 (0) / 17500 | 37.0 |
| 1000 | Oracle anchor | 0.0086 (BH) / 0.0027 (BH+0.4) | 0.224 / 0.080 | 0 (0) / 17500 | 37.0 |

Over the whole grid, 3 of 1,107,400 item-level logistic tests failed, all through Newton non-convergence: one in the purified screen (M, 300/site) and two in the oracle screen (M, 300/site and S5b, 500/site). No separation or errors occurred. Every girth calibration converged (at most 11 EM cycles), and no discrimination estimate reached the [0.2, 5.0] bounds.

**Pairwise localisation (purified, BH-flagged DIF items, Holm across the 3 pairs).**

| Condition | N/site | Flagged DIF items | All truly differing pairs Holm-significant | Spurious pair significant | Exact pattern |
|---|---|---|---|---|---|
| M | 300 | 697 | 0.859 | 0.063 | 0.822 |
| M | 500 | 1348 | 0.927 | 0.062 | 0.881 |
| M | 750 | 1672 | 0.958 | 0.046 | 0.916 |
| M | 1000 | 1836 | 0.980 | 0.047 | 0.936 |
| S1 | 500 | 550 | 0.936 | 0.062 | 0.882 |
| S1 | 750 | 726 | 0.946 | 0.061 | 0.891 |
| S1 | 1000 | 760 | 0.975 | 0.062 | 0.916 |
| S2 | 500 | 776 | 0.713 | n/a (all pairs differ) | 0.713 |
| S2 | 750 | 799 | 0.886 | n/a (all pairs differ) | 0.886 |
| S2 | 1000 | 800 | 0.946 | n/a (all pairs differ) | 0.946 |
| S5a | 500/750/1000 | 654 | 0.939 | 0.043 | 0.907 |
| S5b | 500 | 475 | 0.912 | 0.067 | 0.853 |
| S5b | 750 | 647 | 0.937 | 0.046 | 0.898 |
| S5b | 1000 | 711 | 0.961 | 0.060 | 0.906 |

### Round-1 configuration (S1) and the round-1 analysis

The round-1 CSV gives an empirical FDR of the round-1 one-stage analysis of 0.087 (MC SE 0.013) at 750/site, 0.081 at 1000/site and 0.045 at 500/site (100 replications per cell; FDR computed as V/max(R,1) with V = FPR × 31 and S = power × 4). Rerunning the same analysis on the corrected generator (truncated-normal b) with 200 replications gives:

| Condition | N/site | Power, BH | FDR, BH | Power, BH+Nagelkerke ΔR²≥0.035 | FDR, BH+Nagelkerke | Power, BH+\|Δ\|≥0.4 | FDR, BH+\|Δ\|≥0.4 |
|---|---|---|---|---|---|---|---|
| S1 | 500 | 0.736 (0.017) | 0.083 (0.009) | 0.011 (0.004) | 0.000 (0.000) | 0.693 (0.016) | 0.036 (0.007) |
| S1 | 750 | 0.914 (0.010) | 0.093 (0.009) | 0.009 (0.003) | 0.000 (0.000) | 0.784 (0.013) | 0.026 (0.006) |
| S1 | 1000 | 0.960 (0.007) | 0.098 (0.009) | 0.004 (0.002) | 0.000 (0.000) | 0.769 (0.014) | 0.011 (0.004) |
| M | 300 | 0.046 (0.005) | 0.064 (0.010) | 0.002 (0.001) | 0.004 (0.003) | 0.043 (0.005) | 0.048 (0.009) |
| M | 500 | 0.108 (0.008) | 0.064 (0.010) | 0.000 (0.000) | 0.000 (0.000) | 0.094 (0.007) | 0.033 (0.007) |
| M | 750 | 0.229 (0.011) | 0.058 (0.008) | 0.000 (0.000) | 0.000 (0.000) | 0.137 (0.007) | 0.020 (0.005) |
| M | 1000 | 0.348 (0.011) | 0.066 (0.008) | 0.000 (0.000) | 0.000 (0.000) | 0.141 (0.008) | 0.006 (0.003) |

The new 3-site procedure applied to the S1 data had the following purified combined-rule results:

| n per site | Power | FDR |
|---|---|---|
| 500 | 0.685 (0.019) | 0.032 (0.007) |
| 750 | 0.885 (0.011) | 0.029 (0.006) |
| 1000 | 0.896 (0.010) | 0.016 (0.004) |

When DIF is located at only one site (M), the binary contrast pools a shifted site with an unshifted one and loses most of its power. Its BH-only power was 0.229 (0.011) at 750/site, against 0.836 (0.009) for the purified 3-site test.

### Sensitivity conditions (power is per DIF item)

| Condition | N/site | One-stage BH: power | One-stage BH: FDR | Purified BH: power | Purified BH: FDR | Purified BH+\|Δ\|≥0.4: power | Purified BH+\|Δ\|≥0.4: FDR | Purified BH+\|Δ\|≥0.3: power | Purified BH+\|Δ\|≥0.3: FDR |
|---|---|---|---|---|---|---|---|---|---|
| M main | 300 | 0.311 (0.011) | 0.069 (0.008) | 0.348 (0.013) | 0.054 (0.008) | 0.348 (0.013) | 0.049 (0.008) | 0.348 (0.013) | 0.053 (0.008) |
| M main | 500 | 0.615 (0.011) | 0.080 (0.007) | 0.674 (0.012) | 0.056 (0.006) | 0.667 (0.012) | 0.039 (0.005) | 0.672 (0.012) | 0.045 (0.005) |
| M main | 750 | 0.777 (0.010) | 0.081 (0.006) | 0.836 (0.009) | 0.057 (0.005) | 0.815 (0.009) | 0.031 (0.004) | 0.833 (0.009) | 0.044 (0.005) |
| M main | 1000 | 0.884 (0.007) | 0.085 (0.006) | 0.918 (0.007) | 0.050 (0.004) | 0.870 (0.008) | 0.018 (0.003) | 0.914 (0.007) | 0.027 (0.003) |
| S0 no DIF (diagnostic, added) | 500 | — | 0.050 (0.015) | — | 0.050 (0.015) | — | 0.040 (0.014) | — | 0.050 (0.015) |
| S0 no DIF (diagnostic, added) | 750 | — | 0.055 (0.016) | — | 0.055 (0.016) | — | 0.040 (0.014) | — | 0.045 (0.015) |
| S0 no DIF (diagnostic, added) | 1000 | — | 0.050 (0.015) | — | 0.050 (0.015) | — | 0.015 (0.009) | — | 0.035 (0.013) |
| S1 pooled shift at sites 2+3 | 500 | 0.614 (0.017) | 0.062 (0.010) | 0.688 (0.019) | 0.046 (0.008) | 0.685 (0.019) | 0.032 (0.007) | 0.685 (0.019) | 0.042 (0.008) |
| S1 pooled shift at sites 2+3 | 750 | 0.863 (0.012) | 0.074 (0.009) | 0.907 (0.011) | 0.047 (0.007) | 0.885 (0.011) | 0.029 (0.006) | 0.907 (0.011) | 0.036 (0.006) |
| S1 pooled shift at sites 2+3 | 1000 | 0.912 (0.010) | 0.088 (0.009) | 0.950 (0.008) | 0.047 (0.007) | 0.896 (0.010) | 0.016 (0.004) | 0.950 (0.008) | 0.028 (0.005) |
| S2 opposing DIF (+0.5 / −0.5) | 500 | 0.960 (0.007) | 0.117 (0.010) | 0.970 (0.006) | 0.040 (0.007) | 0.970 (0.006) | 0.030 (0.005) | 0.970 (0.006) | 0.033 (0.006) |
| S2 opposing DIF (+0.5 / −0.5) | 750 | 0.995 (0.002) | 0.168 (0.012) | 0.999 (0.001) | 0.041 (0.006) | 0.998 (0.002) | 0.020 (0.005) | 0.999 (0.001) | 0.033 (0.006) |
| S2 opposing DIF (+0.5 / −0.5) | 1000 | 1.000 (0.000) | 0.206 (0.013) | 1.000 (0.000) | 0.040 (0.007) | 1.000 (0.000) | 0.014 (0.004) | 1.000 (0.000) | 0.028 (0.005) |
| S3a magnitude 0.3 | 500 | 0.147 (0.014) | 0.040 (0.010) | 0.169 (0.016) | 0.032 (0.009) | 0.169 (0.016) | 0.024 (0.007) | 0.169 (0.016) | 0.025 (0.007) |
| S3a magnitude 0.3 | 750 | 0.275 (0.018) | 0.037 (0.009) | 0.294 (0.019) | 0.030 (0.008) | 0.278 (0.018) | 0.021 (0.007) | 0.289 (0.019) | 0.023 (0.008) |
| S3a magnitude 0.3 | 1000 | 0.424 (0.019) | 0.077 (0.013) | 0.464 (0.021) | 0.067 (0.012) | 0.383 (0.020) | 0.050 (0.013) | 0.460 (0.021) | 0.054 (0.011) |
| S3b magnitude 0.7 | 500 | 0.906 (0.010) | 0.086 (0.009) | 0.939 (0.009) | 0.044 (0.007) | 0.936 (0.009) | 0.033 (0.006) | 0.939 (0.009) | 0.037 (0.006) |
| S3b magnitude 0.7 | 750 | 0.963 (0.007) | 0.102 (0.010) | 0.980 (0.005) | 0.055 (0.007) | 0.973 (0.006) | 0.025 (0.005) | 0.979 (0.005) | 0.043 (0.007) |
| S3b magnitude 0.7 | 1000 | 0.984 (0.004) | 0.149 (0.011) | 0.995 (0.002) | 0.059 (0.007) | 0.983 (0.005) | 0.024 (0.005) | 0.995 (0.002) | 0.044 (0.006) |
| S4a 2 DIF items | 500 | 0.600 (0.025) | 0.048 (0.010) | 0.625 (0.025) | 0.040 (0.009) | 0.623 (0.025) | 0.033 (0.008) | 0.625 (0.025) | 0.037 (0.009) |
| S4a 2 DIF items | 750 | 0.748 (0.022) | 0.059 (0.010) | 0.775 (0.022) | 0.049 (0.010) | 0.752 (0.023) | 0.029 (0.007) | 0.772 (0.022) | 0.038 (0.009) |
| S4a 2 DIF items | 1000 | 0.892 (0.016) | 0.062 (0.010) | 0.905 (0.015) | 0.047 (0.009) | 0.860 (0.018) | 0.019 (0.006) | 0.902 (0.015) | 0.033 (0.007) |
| S4b 8 DIF items | 500 | 0.512 (0.013) | 0.126 (0.010) | 0.637 (0.016) | 0.061 (0.008) | 0.630 (0.016) | 0.049 (0.007) | 0.636 (0.016) | 0.057 (0.008) |
| S4b 8 DIF items | 750 | 0.719 (0.010) | 0.140 (0.009) | 0.854 (0.010) | 0.044 (0.005) | 0.814 (0.010) | 0.026 (0.004) | 0.849 (0.010) | 0.033 (0.005) |
| S4b 8 DIF items | 1000 | 0.850 (0.009) | 0.215 (0.009) | 0.934 (0.007) | 0.042 (0.005) | 0.861 (0.008) | 0.017 (0.003) | 0.928 (0.007) | 0.027 (0.004) |
| S5a unequal n 500/750/1000 | 500/750/1000 | 0.766 (0.016) | 0.079 (0.009) | 0.818 (0.016) | 0.053 (0.008) | 0.799 (0.016) | 0.028 (0.006) | 0.816 (0.016) | 0.042 (0.007) |
| S5b site means 0, −0.5, +0.5 | 500 | 0.535 (0.018) | 0.070 (0.010) | 0.594 (0.020) | 0.051 (0.008) | 0.589 (0.019) | 0.038 (0.007) | 0.591 (0.020) | 0.048 (0.008) |
| S5b site means 0, −0.5, +0.5 | 750 | 0.745 (0.016) | 0.110 (0.011) | 0.809 (0.016) | 0.092 (0.010) | 0.786 (0.016) | 0.049 (0.008) | 0.800 (0.016) | 0.061 (0.009) |
| S5b site means 0, −0.5, +0.5 | 1000 | 0.851 (0.012) | 0.122 (0.010) | 0.889 (0.011) | 0.082 (0.009) | 0.840 (0.012) | 0.037 (0.007) | 0.889 (0.011) | 0.056 (0.007) |
| S6 non-uniform (a × 0.7) | 500 | 0.177 (0.016) | 0.052 (0.013) | 0.188 (0.017) | 0.050 (0.013) | 0.159 (0.016) | 0.041 (0.012) | 0.174 (0.016) | 0.043 (0.012) |
| S6 non-uniform (a × 0.7) | 750 | 0.301 (0.018) | 0.048 (0.011) | 0.296 (0.017) | 0.045 (0.011) | 0.233 (0.015) | 0.031 (0.010) | 0.256 (0.016) | 0.034 (0.010) |
| S6 non-uniform (a × 0.7) | 1000 | 0.525 (0.019) | 0.041 (0.008) | 0.519 (0.019) | 0.041 (0.008) | 0.290 (0.016) | 0.017 (0.007) | 0.380 (0.016) | 0.036 (0.008) |
| S7 testlets (9 × 2, var 0.5) | 500 | 0.550 (0.020) | 0.066 (0.010) | 0.593 (0.021) | 0.037 (0.008) | 0.586 (0.021) | 0.027 (0.007) | 0.593 (0.021) | 0.031 (0.008) |
| S7 testlets (9 × 2, var 0.5) | 750 | 0.764 (0.016) | 0.073 (0.010) | 0.820 (0.015) | 0.040 (0.007) | 0.804 (0.015) | 0.026 (0.006) | 0.818 (0.015) | 0.032 (0.006) |
| S7 testlets (9 × 2, var 0.5) | 1000 | 0.881 (0.012) | 0.062 (0.008) | 0.920 (0.010) | 0.035 (0.006) | 0.841 (0.013) | 0.013 (0.004) | 0.915 (0.010) | 0.022 (0.004) |
| S8 7 correlated domains (r = 0.7) | 500 | 0.569 (0.019) | 0.061 (0.009) | 0.630 (0.020) | 0.046 (0.008) | 0.627 (0.020) | 0.030 (0.006) | 0.629 (0.020) | 0.036 (0.007) |
| S8 7 correlated domains (r = 0.7) | 750 | 0.745 (0.018) | 0.076 (0.010) | 0.799 (0.017) | 0.042 (0.007) | 0.775 (0.017) | 0.015 (0.004) | 0.797 (0.017) | 0.029 (0.006) |
| S8 7 correlated domains (r = 0.7) | 1000 | 0.868 (0.012) | 0.080 (0.009) | 0.916 (0.010) | 0.044 (0.007) | 0.856 (0.013) | 0.011 (0.003) | 0.912 (0.010) | 0.024 (0.005) |
| S9 J = 28 | 500 | 0.581 (0.018) | 0.072 (0.010) | 0.649 (0.019) | 0.043 (0.007) | 0.639 (0.019) | 0.032 (0.007) | 0.645 (0.019) | 0.039 (0.007) |
| S9 J = 28 | 750 | 0.792 (0.014) | 0.092 (0.010) | 0.861 (0.013) | 0.041 (0.007) | 0.834 (0.014) | 0.025 (0.005) | 0.861 (0.013) | 0.031 (0.006) |
| S9 J = 28 | 1000 | 0.890 (0.012) | 0.111 (0.010) | 0.941 (0.008) | 0.048 (0.007) | 0.890 (0.012) | 0.025 (0.005) | 0.939 (0.009) | 0.035 (0.006) |
| S10 binary subgroup (30% focal) | 500 | 0.672 (0.019) | 0.072 (0.009) | 0.729 (0.019) | 0.050 (0.008) | 0.710 (0.019) | 0.025 (0.005) | 0.724 (0.019) | 0.037 (0.007) |
| S10 binary subgroup (30% focal) | 750 | 0.851 (0.014) | 0.093 (0.010) | 0.886 (0.013) | 0.044 (0.007) | 0.795 (0.016) | 0.018 (0.005) | 0.877 (0.014) | 0.025 (0.005) |
| S10 binary subgroup (30% focal) | 1000 | 0.924 (0.010) | 0.106 (0.010) | 0.960 (0.008) | 0.031 (0.006) | 0.831 (0.014) | 0.002 (0.002) | 0.935 (0.010) | 0.016 (0.004) |

**Conditions that break the 750/site recommendation.** The purified combined rule falls below 0.80 power at 750/site in the following conditions:
- S3a magnitude 0.3: 0.278 (0.018)
- S6 non-uniform (a × 0.7): 0.233 (0.015)
- S4a 2 DIF items: 0.752 (0.023)
- S8 7 correlated domains (r = 0.7): 0.775 (0.017)
- S5b site means 0, −0.5, +0.5: 0.786 (0.016)
- S10 binary subgroup (30% focal): 0.795 (0.016)
- S5a unequal n 500/750/1000: 0.799 (0.016)

The last three are within about 1 MC SE of 0.80. The combined-rule FDR stayed ≤ 0.05 in every cell; the maximum was 0.050.

At **1000/site**, only two conditions stay below 0.80:
- S3a (magnitude 0.3): 0.383 (0.020). A 0.3 b-shift implies a mean generating log-odds shift of 0.36, below the 0.4 threshold for most items, so this is by design.
- S6 (non-uniform DIF): 0.290 (0.016). The intercept-at-mean rule does not register discrimination-only DIF; the omnibus BH test alone reached 0.519 (0.019).

All other conditions reached ≥ 0.831 at 1000/site.

**BH without the effect-size rule is not safe under larger ability gaps or more DIF items.** BH-only FDR exceeded 0.05 in these cells:
- S5b (means 0, ±0.5), purified: 0.092 (0.010) at 750/site and 0.082 (0.009) at 1000/site. With the oracle anchor it was still 0.086 (0.010) at 750/site, which isolates observed-score matching under impact as the cause.
- S4b (8 DIF items), one-stage: 0.215 (0.009) at 1000/site.
- S2 (opposing DIF), one-stage: 0.206 (0.013) at 1000/site.

Purification brought S4b and S2 down to 0.042 (0.005) and 0.040 (0.007).

### Calibration precision (girth 2PL MML, pooled sample, non-DIF items)

| Condition | N/site | RMSE b (SE) | RMSE a (SE) | Mean bias b | Mean bias a | Marginal reliability, estimated params | Marginal reliability, generating params | Non-converged calibrations |
|---|---|---|---|---|---|---|---|---|
| M | 300 | 0.1086 (0.0010) | 0.1251 (0.0011) | -0.0002 | +0.0241 | 0.894 | 0.892 | 0 |
| M | 500 | 0.0833 (0.0008) | 0.0988 (0.0009) | +0.0000 | +0.0217 | 0.893 | 0.893 | 0 |
| M | 750 | 0.0698 (0.0006) | 0.0799 (0.0006) | -0.0016 | +0.0176 | 0.893 | 0.892 | 0 |
| M | 1000 | 0.0595 (0.0005) | 0.0698 (0.0006) | +0.0010 | +0.0186 | 0.893 | 0.892 | 0 |
| S7 | 500 | 0.0875 (0.0014) | 0.1520 (0.0022) | +0.0015 | -0.0637 | 0.885 | 0.888 | 0 |
| S7 | 750 | 0.0750 (0.0009) | 0.1432 (0.0024) | -0.0037 | -0.0602 | 0.884 | 0.888 | 0 |
| S7 | 1000 | 0.0621 (0.0008) | 0.1415 (0.0023) | +0.0033 | -0.0659 | 0.885 | 0.888 | 0 |
| S8 | 500 | 0.1703 (0.0027) | 0.2725 (0.0027) | +0.0007 | -0.2337 | 0.856 | 0.866 | 0 |
| S8 | 750 | 0.1637 (0.0021) | 0.2686 (0.0024) | -0.0047 | -0.2333 | 0.855 | 0.865 | 0 |
| S8 | 1000 | 0.1511 (0.0021) | 0.2671 (0.0025) | +0.0018 | -0.2355 | 0.856 | 0.866 | 0 |
| S9 | 500 | 0.0864 (0.0016) | 0.0993 (0.0014) | +0.0005 | +0.0200 | 0.871 | 0.870 | 0 |
| S9 | 750 | 0.0693 (0.0012) | 0.0808 (0.0011) | +0.0006 | +0.0155 | 0.870 | 0.869 | 0 |
| S9 | 1000 | 0.0605 (0.0010) | 0.0709 (0.0009) | -0.0026 | +0.0185 | 0.871 | 0.870 | 0 |

Marginal reliability barely changes with n. It is a property of the generating item parameters (here a ~ LogNormal(0.15, 0.3), b ~ truncated N(0, 1), J = 35), not an empirical prediction for the inventory. Under misspecification (S7 testlets, S8 seven domains), the unidimensional fit underestimates discrimination (mean bias in a: -0.060 in S7 and -0.233 in S8 at 750/site). In S8, RMSE of a rises to 0.269.

### Runtime and failures by condition

| Condition | N/site | Replications | Failed logistic tests: one-stage / purified / oracle (all non-convergence) | Tests per procedure | Mean runtime per replication (s) | Total worker time (min) |
|---|---|---|---|---|---|---|
| M | 300 | 500 | 0 / 1 / 1 | 17500 | 23.9 | 199 |
| M | 500 | 500 | 0 / 0 / 0 | 17500 | 27.4 | 228 |
| M | 750 | 500 | 0 / 0 / 0 | 17500 | 32.4 | 270 |
| M | 1000 | 500 | 0 / 0 / 0 | 17500 | 37.0 | 308 |
| S0 | 500 | 200 | 0 / 0 / — | 7000 | 4.5 | 15 |
| S0 | 750 | 200 | 0 / 0 / — | 7000 | 4.8 | 16 |
| S0 | 1000 | 200 | 0 / 0 / — | 7000 | 5.7 | 19 |
| S1 | 500 | 200 | 0 / 0 / 0 | 7000 | 11.4 | 38 |
| S1 | 750 | 200 | 0 / 0 / 0 | 7000 | 13.7 | 46 |
| S1 | 1000 | 200 | 0 / 0 / 0 | 7000 | 15.6 | 52 |
| S2 | 500 | 200 | 0 / 0 / 0 | 7000 | 7.4 | 25 |
| S2 | 750 | 200 | 0 / 0 / 0 | 7000 | 8.2 | 27 |
| S2 | 1000 | 200 | 0 / 0 / 0 | 7000 | 9.4 | 31 |
| S3a | 500 | 200 | 0 / 0 / 0 | 7000 | 6.6 | 22 |
| S3a | 750 | 200 | 0 / 0 / 0 | 7000 | 7.7 | 26 |
| S3a | 1000 | 200 | 0 / 0 / 0 | 7000 | 9.1 | 30 |
| S3b | 500 | 200 | 0 / 0 / 0 | 7000 | 7.5 | 25 |
| S3b | 750 | 200 | 0 / 0 / 0 | 7000 | 9.0 | 30 |
| S3b | 1000 | 200 | 0 / 0 / 0 | 7000 | 9.9 | 33 |
| S4a | 500 | 200 | 0 / 0 / 0 | 7000 | 6.8 | 23 |
| S4a | 750 | 200 | 0 / 0 / 0 | 7000 | 7.9 | 26 |
| S4a | 1000 | 200 | 0 / 0 / 0 | 7000 | 9.2 | 31 |
| S4b | 500 | 200 | 0 / 0 / 0 | 7000 | 7.8 | 26 |
| S4b | 750 | 200 | 0 / 0 / 0 | 7000 | 9.2 | 31 |
| S4b | 1000 | 200 | 0 / 0 / 0 | 7000 | 11.0 | 37 |
| S5a | 500/750/1000 | 200 | 0 / 0 / 0 | 7000 | 8.6 | 29 |
| S5b | 500 | 200 | 0 / 0 / 1 | 7000 | 6.8 | 23 |
| S5b | 750 | 200 | 0 / 0 / 0 | 7000 | 8.6 | 29 |
| S5b | 1000 | 200 | 0 / 0 / 0 | 7000 | 10.0 | 33 |
| S6 | 500 | 200 | 0 / 0 / 0 | 7000 | 6.7 | 22 |
| S6 | 750 | 200 | 0 / 0 / 0 | 7000 | 7.8 | 26 |
| S6 | 1000 | 200 | 0 / 0 / 0 | 7000 | 8.7 | 29 |
| S7 | 500 | 200 | 0 / 0 / 0 | 7000 | 22.7 | 76 |
| S7 | 750 | 200 | 0 / 0 / 0 | 7000 | 27.3 | 91 |
| S7 | 1000 | 200 | 0 / 0 / 0 | 7000 | 32.3 | 108 |
| S8 | 500 | 200 | 0 / 0 / 0 | 7000 | 21.4 | 71 |
| S8 | 750 | 200 | 0 / 0 / 0 | 7000 | 26.6 | 89 |
| S8 | 1000 | 200 | 0 / 0 / 0 | 7000 | 31.5 | 105 |
| S9 | 500 | 200 | 0 / 0 / 0 | 5600 | 17.2 | 57 |
| S9 | 750 | 200 | 0 / 0 / 0 | 5600 | 20.8 | 69 |
| S9 | 1000 | 200 | 0 / 0 / 0 | 5600 | 25.4 | 85 |
| S10 | 500 | 200 | 0 / 0 / 0 | 7000 | 5.9 | 20 |
| S10 | 750 | 200 | 0 / 0 / 0 | 7000 | 6.7 | 22 |
| S10 | 1000 | 200 | 0 / 0 / 0 | 7000 | 7.7 | 26 |

Per-replication times were measured under the host-side CPU throttling described in Methods. They are given for transparency and are not benchmarks.

## Reference notes (match to manuscript bibliography)
Swaminathan & Rogers (1990), logistic-regression DIF; Jodoin & Gierl (2001), Nagelkerke ΔR² categories; Holland & Thayer (1988) and Zwick (2012, ETS RR-12-08), MH D-DIF categories; Benjamini & Hochberg (1995); Holm (1979); Bradlow, Wainer & Wang (1999), testlet model; French & Maller (2007), purification in LR DIF; Morris, White & Crowther (2019), ADEMP simulation reporting.
