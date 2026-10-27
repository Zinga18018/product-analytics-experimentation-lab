# README plot evidence

## Source and meaning

The figure reads only `outputs/experiment_readout.json` from base commit
`a202a003ee935645f9179d95ea94fe501dc3ea84`.

- Git blob: `7ae7109b1f0502de3fe6f599eab2519d88d2bb75`.
- SHA-256 of actual committed LF bytes:
  `78a6d58ba828d77caafd1b713b1abb424b7f87787032ddd40fb26c2bd7e033dd`.
- Exclusive cutoff: `2026-03-02`; common complete-follow-up horizon: eight days.
- Eligible users: 4,413 (2,179 control; 2,234 treatment); immature exclusions: 587.
- Conversion difference: +3.594784 percentage points, two-sided 95% interval
  [1.260181, 5.923038].
- Retention difference: -0.613100 percentage points, two-sided 95% interval
  [-3.488393, 2.264631].

The code multiplies full-precision proportion differences and bounds by 100;
only displayed labels are rounded. Dots are treatment-minus-control estimates,
horizontal lines are Newcombe/Wilson difference intervals, and dashed vertical
lines mark the declared lower-bound thresholds (0 and -2 percentage points).
Conversion also passes the source's significance gate. Retention fails its
noninferiority threshold: **hold**, not proof of harm. The saved revenue,
minimum-sample and assignment-balance gates pass but are not plotted.

This is synthetic data, not business impact. Policy values are illustrative and
were not prospectively preregistered before the historical synthetic data were
generated. These are marginal, fixed-horizon intervals, not sequential-test
results or a simultaneous joint confidence region.

## Reproduce without rebuilding data

The data check and six plot unit tests use only the Python standard library:

```sh
python -S scripts/plot_experiment_intervals.py --data-only
python -S -m unittest discover -s tests -p test_readme_plot.py -v
```

Optional rendering uses a separate dependency; it is not required by the app or
ordinary test discovery:

```sh
python -m pip install -r requirements-visuals.txt
python scripts/plot_experiment_intervals.py
python scripts/plot_experiment_intervals.py --check
```

The first command writes `docs/images/experiment-intervals.svg`; `--check`
rerenders in memory and compares exact bytes. Matplotlib 3.10.8, DejaVu Sans, a
fixed SVG hash salt and omitted date metadata make this deterministic in the
checked environment. `--png path.png --png-width 390` produces an optional local
QA render of the same figure. PNG previews are not required repository assets.

The script rejects a changed source hash, including changed line endings. Use
the source's committed LF bytes for this frozen illustration; review any source
update before deliberately changing the pinned hash and regenerating the plot.
It does not import the analytics pipeline, rebuild the database, train a model
or contact external services.

## Checks performed for the README change

- Source hash, denominators, reconstructed rates, interval bounds, decision and
  accessible SVG checked by six standard-library tests.
- Exact rerender repeated successfully; changed source and changed SVG rejected.
- Native-width and 390-pixel PNGs inspected for labels, spacing and clipping.
- Existing 24 tests passed; 30 including the six plot tests.
- The inspected deterministic generator reproduced dataset counts; the readout
  and four stress scenarios match the saved aggregates within 1e-12 numerical
  tolerance. The generated Markdown report matches exactly.
- No local Streamlit/browser QA: Streamlit was absent. Unit tests and aggregate
  reproduction are not deployment evidence or validation of real-world causal
  assumptions. No source or historical numerical output was changed.

