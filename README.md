# Cloud Concept Inventory

Reference models, buggy variants, verification tests, and DIF design simulations.
The current version contains code only; the operational item bank is not included.
Earlier analysis code and data remain in the [research snapshot](https://github.com/lunarfairy/cloud-concept-inventory/tree/02923ef0c13b036a29bc5a75cca3f939d5bf6b31).

## Run

Python 3.11. From the repository root:

```sh
python -m pip install -r requirements.txt
python -m pytest -q tests
python -m cci.conformance
python scripts/run_property_tests.py
```

Tests write CSV reports to `data/`.

```sh
python scripts/sim_driver.py --workers 16
```

The full simulation takes about 44 single-core hours and resumes existing runs.
Outputs are written to `scripts/`; use `--summary-only` to rebuild summaries from an existing run.

## Files

- `cci/`: models and test fixtures.
- `tests/`: conformance and variant-isolation tests.
- `scripts/`: test reporting and simulation.

[MIT License](LICENSE).
