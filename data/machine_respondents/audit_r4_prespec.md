# Round-4 machine cue audit: pre-specified design and decision criteria
Written 2026-11-11, before any Round-4 administration was run.

## Panel and forms
- Commercial panel (fixed): claude-haiku-4-5-20251001, claude-haiku-5-5, claude-sonnet-4-5-20250929, claude-sonnet-5-5,
  claude-opus-4-5-20251101, claude-opus-5-5. Thinking disabled where the platform permits; Sonnet 5.5 and Opus 5.5 run with the
  server-default adaptive reasoning (the platform rejects 'disabled' for them). Same instruction, preamble rules and parser as Rounds 1-3
  (cci/administer.py).
- Stem-withheld (SW) condition: banks R1 (35 items, Round-1 preamble), R3 (35 items, Round-3 preamble) and R4 (36 items, Round-4
  preamble), each administered to every panel model with the SAME five seeds (7000-7004) -> 90 administrations; this gives a
  constant-panel, matched comparison across development stages that the original Rounds 1-3 did not.
- Full-form condition: R4 to every panel model with seeds 8000-8004 -> 30 administrations.
- Local open-weight models (SmolLM2-360M-Instruct, Qwen2.5-0.5B-Instruct, Qwen2.5-1.5B-Instruct): R4 full and SW forms, key
  probability averaged over four cyclic option rotations (as in Round 3), if the weights are available locally.

## Outcomes
- Answer rate: answered items / scheduled items, per model x bank x condition. An administration answering no item is a 'decline'.
- Conditional accuracy: correct / answered (as in Rounds 1-3).
- Sensitivity estimands: (i) unanswered = incorrect; (ii) unanswered = chance (0.25 credit).
- Uncertainty: administration-cluster bootstrap (2,000 resamples, seed 0) for pooled estimates; exact binomial intervals for
  per-item and per-model cells. Intervals describe this bank and this model panel; they do not generalise to other model families.

## Pre-specified decision criteria (R4, stem-withheld)
1. Bank-level cue margin: pooled conditional SW accuracy is acceptable if the upper bound of its 90% cluster-bootstrap interval is
   <= 0.35 (an excess over chance of at most 0.10). This is a one-sided equivalence-style criterion, not a test of 'no cue'.
2. Model-level: the same criterion per model with >= 3 answering administrations; models below that are reported as 'not assessable'.
3. Item-level residual-cue flag: an item is flagged when its pooled SW accuracy over all answered administrations has an exact one-sided
   binomial p < 0.05 against 0.25 after Benjamini-Hochberg adjustment across the 36 items, with at least 10 answers. Flagged items are
   reported and queued for revision before human piloting; unflagged items are 'not flagged at this depth', not 'cue-free'.
4. Matched stage comparison: for models that answered in all three banks, the paired difference R1-R4 and R3-R4 in SW accuracy, with a
   model-cluster bootstrap.
5. Full form: per-model accuracy on R4 reported descriptively (exposure to tool-assisted answering), not as difficulty evidence.
