# Cloud Concept Inventory: Reference Models, Cue-Audit Analysis, and DIF Simulations

Public code and released non-item data for the development stage of a draft Cloud Concept Inventory (CCI).

## Test security and controlled-access files

Operational item-bank modules, full item stems, and operational answer keys are withheld from this public repository to preserve test security. They are provided confidentially to peer reviewers and, under an instructor use agreement, to educators. Scripts that score or re-render operational forms (`scripts/audit_r4_code.py`, `scripts/local_score_r4.py`) are included for methodological inspection and require the controlled-access archive unpacked over this directory to execute.

## Installation

Tested with Python 3.11:

```sh
python -m pip install -r requirements.txt
```

## Public verification and figures

Run from the repository root:

```sh
python -m pytest -q tests                # 39 conformance and property-based isolation tests
python -m cci.conformance                 # regenerate data/conformance_tests.csv (35 cases)
python scripts/run_property_tests.py      # regenerate data/property_tests.csv (45 variants)
python scripts/make_figures.py            # regenerate Figures 1-4 in build/figs/
```

Optional simulation summary rebuild (from `data/sim/sim_v2_parts.tar.gz`) or full simulation grid (20261111 base seed; ~44 single-core hours):

```sh
tar -xzf data/sim/sim_v2_parts.tar.gz -C scripts/
python scripts/sim_driver.py --summary-only
python scripts/sim_driver.py --workers 16
```

## Layout

- `cci/`: executable reference and single-rule buggy models (`iam.py`, `net.py`, `misc.py`, `fixtures.py`, `preamble.py`, `samples.py`, `administer.py`, `conformance.py`).
- `tests/`: public conformance and property-based isolation test suites (`test_conformance.py`, `test_variants_*.py`).
- `data/`: misconception codebook, Stack Exchange post identifiers, coding outputs and snippet hashes, corpus sensitivity-audit records (`corpus_audit/`), machine-respondent raw outputs and summary tables (`machine_respondents/`), DIF simulation outputs (`sim/`), aggregate manuscript scalars (`numbers.json`), and non-secret two-case item IDs (`two_case_ids_r4.json`).
- `scripts/`: figure generation, property-test runner, DIF simulation (`sim_v2.py`, `sim_driver.py`), and cue-audit scoring scripts.

## Data sources and license

Stack Exchange post metadata and snippet hashes derive from public Q&A posts retrieved via the Stack Exchange API v2.3 (CC BY-SA); no post text or user identifiers are redistributed. Machine-respondent outputs and DIF simulation datasets are model-generated or synthetic. Code is released under the [MIT License](LICENSE).
