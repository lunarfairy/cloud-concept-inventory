# Sensitivity audit of the machine-coded misconception corpus

No human coders were available. The audit compares LLM configurations; its reference is a stronger LLM configuration, not a gold standard. Published files contain IDs, labels and hashes only; full post bodies were used in the workspace and not released.

## Methods

**Full-set agreement.** Coder A (claude-sonnet-5) vs coder B (claude-haiku-5-5), and the final label vs each coder; no new coding (agreement_tables.csv).

**Sample.** Stratified SRSWOR, seed 20261111, n = 322: both-Y 100 (sub-stratified by final domain: NET 25, IAM 16, LB 15, ELA 12, CAC 11, CST 11, final-not-conceptual 9, SHR 1 with certainty), both-N 100/812, A-only-Y 40/43, B-only-Y 80/555, plus the 2 threads with invalid coder-A output (certainty). Inverse inclusion probabilities sum to 1,904.

**Full texts.** Stack Exchange API 2.3 (2026-11-11), all 1,904 threads; HTML stripped with the round-1 cleaner (code blocks kept, each capped at 400 chars); bodies capped at 6,000 chars. For all 1,904 threads the current question and accepted answer begin exactly with the coded 700/500-char snippets and none was edited after 2026-11-04; round-1 answer IDs were not archived, so "unchanged" rests on text identity. In the sample, 254/322 threads had been truncated (178 questions, 201 answers); 3 reach the 6,000 cap.

**Re-coding.** claude-opus-5 (thinking disabled, default temperature), round-1 prompt and codebook verbatim, same validation rules, batches of 12 with identical seeded-shuffled composition in both conditions: (T) exact truncated inputs, (F) full texts. 54 pass-1 requests + 3 retries (+1 excluded pilot), 852,764 tokens. F: 322/322 valid; T: 321 valid (T1305 returned domain "NEW" three times; its conceptual label is kept). Corpus estimates are Horvitz–Thompson totals with Rao–Wu rescaling-bootstrap 95% CIs (4,000 replicates); applied to the sample's final labels the estimator returns 622.9 (true 624).

## Results

**Full set.** Conceptual A×B (n = 1,902): YY 492, YN 43, NY 555, NN 812; p_o 0.686, κ 0.398, PABAK 0.371, AC1 0.388 (McNemar p < 1e-100: B far more inclusive). Final vs A: 0.922 (n = 1,901; κ 0.817, AC1 0.865); final vs B: 0.748 (n = 1,903; κ 0.513, AC1 0.504). Among the 492 both-Y threads, domain agreement 0.878 (κ 0.843), code agreement 0.614 (κ 0.595). Per-domain κ ranges 0.469 (ELA) to 0.556 (NET); SHR shows none.

**(a) Truncation.** T vs F conceptual agreement 296/322 (0.919; κ 0.838, PABAK 0.839, AC1 0.840); discordant 8 T-only-Y vs 18 F-only-Y (McNemar exact p = 0.076); weighted agreement 0.935 (0.909–0.959). Among both-Y: domain 0.963 (κ 0.955), code 0.874 (κ 0.867). The 68 never-truncated threads received identical text yet differ on 6 conceptual labels (3 vs 3; 0.912), which is the single-run noise floor. Truncated threads agree at 0.921 but split 5 vs 15 (p = 0.041). Truncation therefore does not reduce agreement beyond noise but shifts labels toward not conceptual (full text yields more conceptual labels): weighted F − T = +53 threads (5–100).

**(b) Final vs F.** Conceptual agreement by stratum: both-Y 0.90 (final Y 91/100, F Y 85), both-N 0.92 (0 vs 8), A-only-Y 0.60 (26 vs 28 of 40), B-only-Y 0.725 (17 vs 31 of 80); unweighted κ 0.643. Among final-Y and F-Y threads (n = 115): domain 0.922 (κ 0.905; weighted 0.930), code 0.757 (κ 0.743). F confirmed conceptual for NET 27/27, LB 19/21, CST 13/15, ELA 15/18, CAC 16/22, IAM 23/29 final-Y threads.

**(c) Weighted estimates (F).** Conceptual threads 754.4 (682.9–827.8) vs reported 624; prevalence 0.396 (0.359–0.435) vs 0.328. Under T: 701.4 (628.6–773.2). The excess comes from B-only-Y (215.1, 159.1–269.6, vs 119 final) and both-N (65.0, 27.2–104.0, vs 0). Domains (reported in brackets): NET 268.2 (222.5–318.6) [203]; IAM 109.7 (79.1–144.4) [112]; LB 107.0 (81.5–137.1) [109]; CST 105.9 (70.4–146.2) [68]; CAC 82.4 (55.3–114.5) [63]; ELA 73.3 (46.8–105.3) [67]; SHR 8.0 (1.3–21.4) [2]. Shares: NET 0.355 vs 0.325, IAM 0.145 vs 0.179, LB 0.142 vs 0.175, CST 0.140 vs 0.109. NET remains the largest domain; NET and CST grow.

**(d) Precision/recall of final "conceptual" vs F (weighted).** Precision 0.884 (0.829–0.932), recall 0.730 (0.665–0.797), F1 0.800 (0.751–0.846); about 72 estimated false positives vs 204 false negatives, so the final label is conservative. Coder A: precision 0.885, recall 0.628; coder B: 0.629, 0.874.

**(e) Codes (largest |audit − final|).** NEW 96.6 (54.9–141.6) vs 44; CST-3 57.5 vs 35; CST-1 40.1 vs 21; NET-7 58.3 vs 40; IAM-2 30.2 vs 13; NET-5 41.7 vs 27; IAM-4 20.9 vs 35; LB-3 62.3 vs 49; ELA-2 3.8 (0.5–11.0) vs 17. Per-code intervals are wide (0–17 sampled threads per code); codes absent from the sample get degenerate [0, 0] intervals.

**Data freeze.** coded_input_hashes.csv holds SHA-256 hashes of every coded snippet pair, record hashes and current answer IDs; snapshot_hash.py re-verifies all 1,904 (0 mismatches). coding_input.jsonl SHA-256: fb7cabbda416179b335fc94ea7d857bc603e1ebb295e4fabee35eef29a12bfd1.

## Limitations

There is no human reference standard; "precision" and "recall" measure agreement with another model, not validity. Coders and auditor share one model family, and claude-opus-5 was also the round-1 adjudicator, so shared biases are undetectable. One run per condition: CIs cover sampling variance only, while identical-input reruns disagree on about 9% of conceptual labels. "Full" text still caps code blocks at 400 chars. Per-code and SHR estimates are imprecise. Answer identity is inferred from text, not archived IDs.
