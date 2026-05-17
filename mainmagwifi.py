import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

OLD_CSV = Path("VecaisCels.csv")
NEW_CSV = Path("JaunaisCels.csv")

OLD_PLOT = Path("difference_ms_vecaiscels.png")
NEW_PLOT = Path("difference_ms_jaunaiscels.png")

MIN_MS = 0.0
STATS_MAX_MS = 5000.0
PLOT_MAX_MS = 500.0
BIN_WIDTH = 5.0


def load_difference_ms(path: Path) -> pd.Series:
    df = pd.read_csv(path)

    if "DifferenceMs" in df.columns:
        s = df["DifferenceMs"]
    else:
        if df.shape[1] != 1:
            raise ValueError(f"{path}: expected one column or column named 'DifferenceMs'")
        s = df.iloc[:, 0]

    s = pd.to_numeric(s, errors="coerce").dropna()
    s = s[(s >= MIN_MS) & (s <= STATS_MAX_MS)]
    if s.empty:
        raise ValueError(f"{path}: no DifferenceMs values in range {MIN_MS}..{STATS_MAX_MS}")
    return s


def summarize(s: pd.Series) -> dict:
    x = s.to_numpy()

    mode_result = stats.mode(x, keepdims=True)
    mode_ms = float(mode_result.mode[0]) if mode_result.count[0] > 0 else float("nan")

    p95_low, p95_high = np.percentile(x, [2.5, 97.5])
    p99_low, p99_high = np.percentile(x, [0.5, 99.5])

    return {
        "count": int(s.count()),
        "min_ms": float(s.min()),
        "max_ms": float(s.max()),
        "mean_ms": float(s.mean()),
        "median_ms": float(s.median()),
        "mode_ms": mode_ms,
        "std_ms": float(s.std(ddof=1)),
        "interval_95_ms": (float(p95_low), float(p95_high)),
        "interval_99_ms": (float(p99_low), float(p99_high)),
    }


def print_summary(name: str, summary: dict) -> None:
    print(f"\n{name} statistics ({MIN_MS:g} <= DifferenceMs <= {STATS_MAX_MS:g}):")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def make_shared_bin_edges() -> np.ndarray:
    plot_max = np.ceil(PLOT_MAX_MS / BIN_WIDTH) * BIN_WIDTH

    # Last bin is overflow bin:
    # normal bins: 0 .. plot_max
    # overflow bin: >= plot_max, drawn from plot_max .. plot_max + BIN_WIDTH
    return np.arange(MIN_MS, plot_max + BIN_WIDTH + 1e-9, BIN_WIDTH)


def plot_histogram(
    s: pd.Series,
    stats_dict: dict,
    title: str,
    out_path: Path,
    bin_edges: np.ndarray,
) -> None:
    x = s.to_numpy()

    overflow_start = bin_edges[-2]
    overflow_center = overflow_start + BIN_WIDTH * 0.5

    # Values in final bin are overflow: >= overflow_start
    x_binned = np.where(x >= overflow_start, overflow_center, x)
    overflow_count = int(np.sum(x >= overflow_start))

    p99_low, p99_high = stats_dict["interval_99_ms"]
    p95_low, p95_high = stats_dict["interval_95_ms"]

    fig, ax = plt.subplots(figsize=(11, 6))

    # Only draw intervals if visible in plot range
    if p99_low < overflow_start:
        ax.axvspan(
            max(p99_low, MIN_MS),
            min(p99_high, overflow_start),
            color="#dddddd",
            alpha=1,
            label=f"99% HDI: [{p99_low:.3f}, {p99_high:.3f}]",
        )

    if p95_low < overflow_start:
        ax.axvspan(
            max(p95_low, MIN_MS),
            min(p95_high, overflow_start),
            color="#f7c388",
            alpha=1,
            label=f"95% HDI: [{p95_low:.3f}, {p95_high:.3f}]",
        )

    ax.hist(
        x_binned,
        bins=bin_edges,
        color="steelblue",
        edgecolor="black",
        alpha=0.85,
    )

    if MIN_MS <= stats_dict["mean_ms"] < overflow_start:
        ax.axvline(
            stats_dict["mean_ms"],
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean: {stats_dict['mean_ms']:.3f}",
        )

    if MIN_MS <= stats_dict["median_ms"] < overflow_start:
        ax.axvline(
            stats_dict["median_ms"],
            color="green",
            linestyle="--",
            linewidth=1.5,
            label=f"Median: {stats_dict['median_ms']:.3f}",
        )

    tick_step = max(1, int(25 / BIN_WIDTH))
    ticks = list(bin_edges[::tick_step])
    if overflow_start not in ticks:
        ticks.append(overflow_start)
    ticks = sorted(set(ticks))

    labels = [f"{t:.0f}" for t in ticks]
    for i, tick in enumerate(ticks):
        if np.isclose(tick, overflow_start):
            labels[i] = f">={overflow_start:.0f}"

    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)

    # Force x-axis and y-axis to meet at visible (0, 0)
    ax.set_xlim(0, bin_edges[-1])
    ax.set_ylim(bottom=0)
    ax.margins(x=0, y=0)

    ax.spines["left"].set_position(("data", 0))
    ax.spines["bottom"].set_position(("data", 0))
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)

    ax.set_title(title)
    ax.set_xlabel("Laiks, ms")
    ax.set_ylabel("Skaits")

    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.show()


def main() -> None:
    old_s = load_difference_ms(OLD_CSV)
    new_s = load_difference_ms(NEW_CSV)

    old_stats = summarize(old_s)
    new_stats = summarize(new_s)

    print_summary("VecaisCels.csv", old_stats)
    print_summary("JaunaisCels.csv", new_stats)

    bin_edges = make_shared_bin_edges()

    print(f"\nbin_width_ms: {BIN_WIDTH}")
    print(f"stats_max_ms: {STATS_MAX_MS}")
    print(f"plot_max_ms: {PLOT_MAX_MS}")
    print(f"overflow_bin_starts_at_ms: {bin_edges[-2]}")
    print(f"num_bins_including_overflow: {len(bin_edges) - 1}")
    print(f"bin_start_ms: {bin_edges[0]}")
    print(f"bin_end_ms: {bin_edges[-1]}")

    plot_histogram(
        s=old_s,
        stats_dict=old_stats,
        title="Ceļa laiks - Asus RT-AC55U maršrutētājs",
        out_path=OLD_PLOT,
        bin_edges=bin_edges,
    )

    plot_histogram(
        s=new_s,
        stats_dict=new_stats,
        title="Ceļa laiks - Xiaomi AX3000T maršrutētājs",
        out_path=NEW_PLOT,
        bin_edges=bin_edges,
    )


if __name__ == "__main__":
    main()