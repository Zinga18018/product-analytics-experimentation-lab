"""Plot the saved synthetic conversion/retention readout; no database rebuild."""
from pathlib import Path
import argparse
import hashlib
import io
import json
import math
import os
import re
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/experiment_readout.json"
OUTPUT = ROOT / "docs/images/experiment-intervals.svg"
SOURCE_SHA256 = "78a6d58ba828d77caafd1b713b1abb424b7f87787032ddd40fb26c2bd7e033dd"


def checked_data(source=SOURCE):
    raw = Path(source).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("Recorded source bytes changed (including line endings); review before updating the plot.")
    record = json.loads(raw)
    if record["eligible_users"] != 4413 or record["excluded_immature_users"] != 587:
        raise ValueError("Unexpected follow-up denominators.")
    if record["policy"]["as_of"] != "2026-03-02" or record["confidence_level"] != .95:
        raise ValueError("Unexpected cutoff or confidence level.")
    for name in ("conversion", "retention"):
        result = record[name]
        if result["control_users"] != 2179 or result["treatment_users"] != 2234:
            raise ValueError("Unexpected arm sizes.")
        for arm in ("control", "treatment"):
            if not math.isclose(result[arm + "_rate"],
                                result[arm + "_successes"] / result[arm + "_users"], abs_tol=1e-14):
                raise ValueError("Rate disagrees with numerator and denominator.")
        values = [result[key] for key in ("ci_low", "absolute_lift", "ci_high")]
        if not all(math.isfinite(value) for value in values) or values != sorted(values):
            raise ValueError("Invalid difference interval.")
        if not math.isclose(result["absolute_lift"], result["treatment_rate"] - result["control_rate"], abs_tol=1e-14):
            raise ValueError("Difference must be treatment minus control.")
    checks = record["checks"]
    if record["decision"] != "hold" or [key for key, value in checks.items() if not value] != ["retention"]:
        raise ValueError("Expected a retention-blocked hold.")
    if record["conversion"]["ci_low"] <= record["policy"]["min_conversion_lift"]:
        raise ValueError("Conversion lower bound must clear its declared threshold.")
    if record["retention"]["ci_low"] >= -record["policy"]["retention_loss_tolerance"]:
        raise ValueError("Retention lower bound must fail its declared threshold.")
    return record


def render(png=None, png_width=1024):
    record = checked_data()
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "product-intervals-mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    if matplotlib.__version__ != "3.10.8":
        raise RuntimeError("Install requirements-visuals.txt for exact plot reproduction.")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11,
                         "svg.fonttype": "none", "svg.hashsalt": "product-synthetic-intervals-v1",
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False}):
        fig, axes = plt.subplots(2, 1, figsize=(6.6, 4.5), sharex=True)
        fig.subplots_adjust(left=.10, right=.96, top=.80, bottom=.17, hspace=.90)
        fig.suptitle("Synthetic experiment: hold", fontsize=13, y=.97)
        for ax, key, label, color, threshold in [
            (axes[0], "conversion", "Conversion", "#32648e", record["policy"]["min_conversion_lift"]),
            (axes[1], "retention", "Retention", "#ae612d", -record["policy"]["retention_loss_tolerance"]),
        ]:
            result = record[key]
            low, delta, high = [100 * result[k] for k in ("ci_low", "absolute_lift", "ci_high")]
            ax.set_title(f"{label}: {delta:+.2f} pp", loc="left", fontsize=11.5, pad=10)
            ax.axvline(100 * threshold, color="#666666", linestyle="--", linewidth=1.2)
            ax.errorbar(delta, .5, xerr=[[delta - low], [high - delta]], fmt="o",
                        color=color, markersize=7, linewidth=2.2, capsize=5, zorder=3)
            ax.text(.99, .94, f"95% CI [{low:.2f}, {high:.2f}]", ha="right", va="top",
                    transform=ax.transAxes, fontsize=10)
            ax.text(100 * threshold + .13, .06, f"{100 * threshold:g} pp boundary",
                    fontsize=10, color="#555555")
            ax.set(ylim=(0, 1), yticks=[], xlim=(-4.5, 6.5), xticks=[-4, -2, 0, 2, 4, 6])
            ax.grid(axis="x", color="#eeeeee", linewidth=.7)
            ax.set_axisbelow(True)
        axes[1].set_xlabel("Treatment minus control (percentage points)", fontsize=11, labelpad=8)
        buf = io.StringIO()
        fig.savefig(buf, format="svg", metadata={"Date": None}, facecolor="white")
        if png:
            Path(png).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(png, dpi=png_width / 6.6, facecolor="white")
        plt.close(fig)
    svg = buf.getvalue().replace('<svg ', '<svg role="img" aria-labelledby="title desc" ', 1)
    match = re.search(r"<svg\b[^>]*>", svg)
    description = ('<title id="title">Synthetic conversion and retention difference intervals</title>'
                   '<desc id="desc">Treatment minus control: conversion +3.59 percentage points '
                   'with two-sided 95% interval [1.26, 5.92]; retention -0.61 with interval [-3.49, 2.26]. '
                   'Conversion clears its zero boundary. Retention lower bound fails the -2 point '
                   'loss tolerance, so the overall decision is hold. This is unestablished '
                   'noninferiority, not proof of harm. Synthetic data; 4413 eligible users; '
                   'exclusive cutoff 2026-03-02; illustrative policy not prospectively preregistered. '
                   'Source SHA-256: ' + SOURCE_SHA256 + '.</desc>')
    svg = svg[:match.end()] + description + svg[match.end():]
    ET.fromstring(svg)
    return svg.encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare an exact rerender to the checked-in SVG")
    parser.add_argument("--data-only", action="store_true", help="Check source, rates, intervals and decision with only the standard library")
    parser.add_argument("--png", type=Path, help="Optional local QA render; not needed by the README")
    parser.add_argument("--png-width", type=int, default=1024)
    args = parser.parse_args()
    if args.png_width < 1:
        parser.error("--png-width must be positive")
    if args.data_only:
        checked_data()
        print("PASS: exact source hash, mature cohort, rates, intervals and retention-blocked hold")
        return
    svg = render(args.png, args.png_width)
    if args.check:
        if OUTPUT.read_bytes() != svg:
            raise ValueError("Checked-in SVG differs from an exact rerender.")
        print("PASS: pinned readout and byte-identical Matplotlib SVG")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(svg)
        print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
