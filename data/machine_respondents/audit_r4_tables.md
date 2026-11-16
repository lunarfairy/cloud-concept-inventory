# Round-4 machine cue audit: tables

Requests: 120 (errors 0); host.llm tokens: {'input_tokens': 613565, 'cache_creation_input_tokens': 82367, 'cache_read_input_tokens': 280593, 'output_tokens': 50079, 'total': 1026604}

## 1. Pooled estimates (administration-cluster bootstrap, 2,000 resamples, seed 0)

| Bank/cond | adm | declines | answer rate | answered | cond. acc | 95% CI | 90% CI | unanswered=incorrect [95% CI] | unanswered=0.25 [95% CI] |
|---|---|---|---|---|---|---|---|---|---|
| R1_optonly | 30 | 0 | 1.000 | 1050/1050 | 0.854 | [0.810, 0.892] | [0.817, 0.888] | 0.854 [0.810, 0.892] | 0.854 [0.810, 0.892] |
| R3_optonly | 30 | 15 | 0.500 | 525/1050 | 0.293 | [0.257, 0.330] | [0.262, 0.324] | 0.147 [0.092, 0.201] | 0.272 [0.253, 0.291] |
| R4_optonly | 30 | 16 | 0.435 | 470/1080 | 0.336 | [0.297, 0.377] | [0.304, 0.369] | 0.146 [0.088, 0.207] | 0.287 [0.267, 0.310] |
| R4_full | 30 | 0 | 1.000 | 1080/1080 | 0.835 | [0.760, 0.898] | [0.773, 0.890] | 0.835 [0.760, 0.898] | 0.835 [0.760, 0.898] |

**Criterion 1 (R4 SW):** conditional accuracy 0.336, 90% upper bound 0.369 vs margin 0.35 -> **not met**.

## 2. Answer rates by model x bank x condition

| Model | Bank | Cond | declines/adm | answer rate | answered per adm |
|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-haiku-4-5-20251001 | R3 | optonly | 5/5 | 0.000 | [0, 0, 0, 0, 0] |
| claude-haiku-4-5-20251001 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-haiku-4-5-20251001 | R4 | optonly | 5/5 | 0.000 | [0, 0, 0, 0, 0] |
| claude-haiku-5-5 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-haiku-5-5 | R3 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-haiku-5-5 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-haiku-5-5 | R4 | optonly | 2/5 | 0.600 | [0, 0, 36, 36, 36] |
| claude-opus-4-5-20251101 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-opus-4-5-20251101 | R3 | optonly | 5/5 | 0.000 | [0, 0, 0, 0, 0] |
| claude-opus-4-5-20251101 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-opus-4-5-20251101 | R4 | optonly | 5/5 | 0.000 | [0, 0, 0, 0, 0] |
| claude-opus-5-5 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-opus-5-5 | R3 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-opus-5-5 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-opus-5-5 | R4 | optonly | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-sonnet-4-5-20250929 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-sonnet-4-5-20250929 | R3 | optonly | 5/5 | 0.000 | [0, 0, 0, 0, 0] |
| claude-sonnet-4-5-20250929 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-sonnet-4-5-20250929 | R4 | optonly | 4/5 | 0.011 | [0, 0, 0, 0, 2] |
| claude-sonnet-5-5 | R1 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-sonnet-5-5 | R3 | optonly | 0/5 | 1.000 | [35, 35, 35, 35, 35] |
| claude-sonnet-5-5 | R4 | full | 0/5 | 1.000 | [36, 36, 36, 36, 36] |
| claude-sonnet-5-5 | R4 | optonly | 0/5 | 1.000 | [36, 36, 36, 36, 36] |

## 3. Per-model stem-withheld accuracy (exact Clopper-Pearson intervals; criterion 2 on R4 uses the per-model cluster bootstrap 90% upper bound)

| Model | Bank | answering adm | correct/answered | acc | CP 95% | CP 90% | boot 90% | criterion 2 |
|---|---|---|---|---|---|---|---|---|
| claude-haiku-4-5-20251001 | R1 | 5 | 143/175 | 0.817 | [0.752, 0.871] | [0.762, 0.864] |  |  |
| claude-haiku-5-5 | R1 | 5 | 113/175 | 0.646 | [0.570, 0.716] | [0.582, 0.706] |  |  |
| claude-sonnet-4-5-20250929 | R1 | 5 | 147/175 | 0.840 | [0.777, 0.891] | [0.787, 0.884] |  |  |
| claude-sonnet-5-5 | R1 | 5 | 163/175 | 0.931 | [0.883, 0.964] | [0.891, 0.960] |  |  |
| claude-opus-4-5-20251101 | R1 | 5 | 163/175 | 0.931 | [0.883, 0.964] | [0.891, 0.960] |  |  |
| claude-opus-5-5 | R1 | 5 | 168/175 | 0.960 | [0.919, 0.984] | [0.926, 0.981] |  |  |
| claude-haiku-4-5-20251001 | R3 | 0 | 0/0 |  |  |  |  |  |
| claude-haiku-5-5 | R3 | 5 | 41/175 | 0.234 | [0.174, 0.304] | [0.182, 0.293] |  |  |
| claude-sonnet-4-5-20250929 | R3 | 0 | 0/0 |  |  |  |  |  |
| claude-sonnet-5-5 | R3 | 5 | 57/175 | 0.326 | [0.257, 0.401] | [0.267, 0.389] |  |  |
| claude-opus-4-5-20251101 | R3 | 0 | 0/0 |  |  |  |  |  |
| claude-opus-5-5 | R3 | 5 | 56/175 | 0.320 | [0.252, 0.395] | [0.262, 0.383] |  |  |
| claude-haiku-4-5-20251001 | R4 | 0 | 0/0 |  |  |  |  | not assessable |
| claude-haiku-5-5 | R4 | 3 | 26/108 | 0.241 | [0.164, 0.333] | [0.174, 0.318] | [0.222, 0.250] | acceptable |
| claude-sonnet-4-5-20250929 | R4 | 1 | 1/2 | 0.500 | [0.013, 0.987] | [0.025, 0.975] |  | not assessable |
| claude-sonnet-5-5 | R4 | 5 | 64/180 | 0.356 | [0.286, 0.430] | [0.296, 0.419] | [0.311, 0.400] | not met |
| claude-opus-4-5-20251101 | R4 | 0 | 0/0 |  |  |  |  | not assessable |
| claude-opus-5-5 | R4 | 5 | 67/180 | 0.372 | [0.301, 0.447] | [0.312, 0.436] | [0.339, 0.406] | not met |

## 4. R4 item-level residual-cue screen (SW; one-sided exact binomial vs 0.25; BH over 36 items; flag needs q<0.05 and n>=10)

Testable items (n>=10): 36/36. Flagged: ['IAM06', 'IAM07', 'NET06', 'NET08', 'LB02', 'LB03', 'ELA01', 'CAC02', 'CST01', 'SHR01'].

| Item | n | correct | acc | CP 95% | p | q (BH) | flag |
|---|---|---|---|---|---|---|---|
| IAM06 | 13 | 10 | 0.769 | [0.462, 0.950] | 0.0001 | 0.0011 | FLAG |
| LB02 | 13 | 10 | 0.769 | [0.462, 0.950] | 0.0001 | 0.0011 | FLAG |
| ELA01 | 13 | 10 | 0.769 | [0.462, 0.950] | 0.0001 | 0.0011 | FLAG |
| CST01 | 13 | 10 | 0.769 | [0.462, 0.950] | 0.0001 | 0.0011 | FLAG |
| IAM07 | 13 | 9 | 0.692 | [0.386, 0.909] | 0.0010 | 0.0059 | FLAG |
| CAC02 | 13 | 9 | 0.692 | [0.386, 0.909] | 0.0010 | 0.0059 | FLAG |
| NET06 | 13 | 8 | 0.615 | [0.316, 0.861] | 0.0056 | 0.0203 | FLAG |
| NET08 | 13 | 8 | 0.615 | [0.316, 0.861] | 0.0056 | 0.0203 | FLAG |
| LB03 | 13 | 8 | 0.615 | [0.316, 0.861] | 0.0056 | 0.0203 | FLAG |
| SHR01 | 13 | 8 | 0.615 | [0.316, 0.861] | 0.0056 | 0.0203 | FLAG |
| ELA02 | 13 | 7 | 0.538 | [0.251, 0.808] | 0.0243 | 0.0795 |  |
| NET02 | 13 | 6 | 0.462 | [0.192, 0.749] | 0.0802 | 0.2063 |  |
| ELA05 | 13 | 6 | 0.462 | [0.192, 0.749] | 0.0802 | 0.2063 |  |
| CST04 | 13 | 6 | 0.462 | [0.192, 0.749] | 0.0802 | 0.2063 |  |
| LB04 | 13 | 5 | 0.385 | [0.139, 0.684] | 0.2060 | 0.4636 |  |
| CST03 | 13 | 5 | 0.385 | [0.139, 0.684] | 0.2060 | 0.4636 |  |
| IAM03 | 13 | 4 | 0.308 | [0.091, 0.614] | 0.4157 | 0.8315 |  |
| SHR02 | 13 | 4 | 0.308 | [0.091, 0.614] | 0.4157 | 0.8315 |  |
| ELA03 | 13 | 3 | 0.231 | [0.050, 0.538] | 0.6674 | 1.0000 |  |
| ELA04 | 13 | 3 | 0.231 | [0.050, 0.538] | 0.6674 | 1.0000 |  |
| IAM01 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| NET03 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| NET07 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| LB01 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| CAC04 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| CST02 | 13 | 2 | 0.154 | [0.019, 0.454] | 0.8733 | 1.0000 |  |
| NET04 | 14 | 2 | 0.143 | [0.018, 0.428] | 0.8990 | 1.0000 |  |
| IAM02 | 13 | 1 | 0.077 | [0.002, 0.360] | 0.9762 | 1.0000 |  |
| IAM04 | 13 | 1 | 0.077 | [0.002, 0.360] | 0.9762 | 1.0000 |  |
| NET05 | 13 | 1 | 0.077 | [0.002, 0.360] | 0.9762 | 1.0000 |  |
| CAC01 | 13 | 1 | 0.077 | [0.002, 0.360] | 0.9762 | 1.0000 |  |
| CAC03 | 14 | 1 | 0.071 | [0.002, 0.339] | 0.9822 | 1.0000 |  |
| IAM05 | 13 | 0 | 0.000 | [0.000, 0.247] | 1.0000 | 1.0000 |  |
| NET01 | 13 | 0 | 0.000 | [0.000, 0.247] | 1.0000 | 1.0000 |  |
| SHR03 | 13 | 0 | 0.000 | [0.000, 0.247] | 1.0000 | 1.0000 |  |
| SHR04 | 13 | 0 | 0.000 | [0.000, 0.247] | 1.0000 | 1.0000 |  |

## 5. Matched stage comparison (SW; models answering all three banks; model-cluster bootstrap)

Models: ['claude-haiku-5-5', 'claude-sonnet-5-5', 'claude-opus-5-5']

- R1 - R4: mean 0.523, 95% [0.405, 0.588], 90% [0.462, 0.584]; per model claude-haiku-5-5: +0.405, claude-sonnet-5-5: +0.576, claude-opus-5-5: +0.588
- R3 - R4: mean -0.030, 95% [-0.052, -0.006], 90% [-0.045, -0.014]; per model claude-haiku-5-5: -0.006, claude-sonnet-5-5: -0.030, claude-opus-5-5: -0.052

## 6. R4 full form per model (descriptive; tool-free exposure, not difficulty evidence)

| Model | correct/answered | acc | CP 95% | per-adm correct |
|---|---|---|---|---|
| claude-haiku-4-5-20251001 | 126/180 (of 180) | 0.700 | [0.627, 0.766] | [24, 27, 25, 25, 25] |
| claude-haiku-5-5 | 87/180 (of 180) | 0.483 | [0.408, 0.559] | [17, 16, 19, 19, 16] |
| claude-sonnet-4-5-20250929 | 158/180 (of 180) | 0.878 | [0.821, 0.922] | [31, 31, 32, 32, 32] |
| claude-sonnet-5-5 | 177/180 (of 180) | 0.983 | [0.952, 0.997] | [35, 36, 35, 36, 35] |
| claude-opus-4-5-20251101 | 174/180 (of 180) | 0.967 | [0.929, 0.988] | [36, 35, 34, 34, 35] |
| claude-opus-5-5 | 180/180 (of 180) | 1.000 | [0.980, 1.000] | [36, 36, 36, 36, 36] |

## 7. Distractor choice among errors (uniform-choice null preserving item and model counts; 10,000 draws, seed 0)

| Form | wrong answers | observed share modelled | expected | null 95% range | p (greater) | p (two-sided) |
|---|---|---|---|---|---|---|
| R4_full | 178 | 0.646 | 0.699 | [0.646, 0.753] | 0.9781 | 0.0736 |
| R4_optonly | 312 | 0.417 | 0.599 | [0.551, 0.647] | 1.0000 | 0.0002 |
| R3_optonly | 371 | 0.426 | 0.571 | [0.526, 0.617] | 1.0000 | 0.0002 |
| R1_optonly (degenerate: all distractors modelled) | 153 | 1.000 | 1.000 | [1.000, 1.000] | 1.0000 | 1.0000 |

Per model (full form R4): claude-haiku-4-5-20251001: 0.78 vs 0.73 (n=54, p=0.227); claude-haiku-5-5: 0.57 vs 0.66 (n=93, p=0.989); claude-opus-4-5-20251101: 0.67 vs 0.78 (n=6, p=1.000); claude-sonnet-4-5-20250929: 0.73 vs 0.80 (n=22, p=0.967); claude-sonnet-5-5: 0.00 vs 0.33 (n=3, p=1.000)

## 8. Sensitivity (not pre-specified): spurious parse treated as a decline

claude-sonnet-4-5 R4 SW seed 7004 refused but echoed the instruction's format example ('Q1: B, Q2: C'), which the unchanged parser scores as 2 answers.
R4 SW conditional accuracy 0.335, 90% CI [0.303, 0.369]; criterion 1: not met; flagged: ['IAM06', 'IAM07', 'NET06', 'NET08', 'LB02', 'LB03', 'ELA01', 'CAC02', 'CST01', 'SHR01'].

## 9. Local open-weight models, R4 (key probability averaged over four cyclic rotations)

| Model | Cond | items | mean P(key) | item-bootstrap 95% | argmax acc | items P(key)>0.5 |
|---|---|---|---|---|---|---|
| HuggingFaceTB__SmolLM2-360M-Instruct | full | 36 | 0.250 | [0.245, 0.255] | 0.222 | 0 |
| HuggingFaceTB__SmolLM2-360M-Instruct | optonly | 36 | 0.253 | [0.249, 0.257] | 0.278 | 0 |
| Qwen__Qwen2.5-0.5B-Instruct | full | 36 | 0.258 | [0.232, 0.286] | 0.194 | 1 |
| Qwen__Qwen2.5-0.5B-Instruct | optonly | 36 | 0.230 | [0.208, 0.255] | 0.194 | 0 |
