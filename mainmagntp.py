import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

OLD_CSV = Path("VecaisNtp.csv")
NEW_CSV = Path("JaunaisNtp.csv")

OLD_PLOT = Path("ntp_error_vecaisntp.png")
NEW_PLOT = Path("ntp_error_jaunaisntp.png")

STATS_MAX_NTP_ERROR = 50000000.0
PLOT_MAX_NTP_ERROR = 20.0
BIN_WIDTH = 0.5
GRAPH_MIN_NTP_ERROR = 0.0


def load_ntp_error(path: Path) -> pd.Series:
    df = pd.read_csv(path, header=None, names=["CameraId", "NtpError"])

    if df.shape[1] != 2:
        raise ValueError(f"{path}: expected two columns: CameraId, NtpError")

    s = pd.to_numeric(df["NtpError"], errors="coerce").dropna()
    s = s[s <= STATS_MAX_NTP_ERROR]
    if s.empty:
        raise ValueError(f"{path}: no NtpError values <= {STATS_MAX_NTP_ERROR}")
    return s


def summarize(s: pd.Series) -> dict:
    x = s.to_numpy()

    mode_result = stats.mode(x, keepdims=True)
    mode_ntp_error = float(mode_result.mode[0]) if mode_result.count[0] > 0 else float("nan")

    p95_low, p95_high = np.percentile(x, [2.5, 97.5])
    p99_low, p99_high = np.percentile(x, [0.5, 99.5])

    return {
        "count": int(s.count()),
        "min_ntp_error": float(s.min()),
        "max_ntp_error": float(s.max()),
        "mean_ntp_error": float(s.mean()),
        "median_ntp_error": float(s.median()),
        "mode_ntp_error": mode_ntp_error,
        "std_ntp_error": float(s.std(ddof=1)),
        "interval_95_ntp_error": (float(p95_low), float(p95_high)),
        "interval_99_ntp_error": (float(p99_low), float(p99_high)),
    }


def print_summary(name: str, summary: dict) -> None:
    print(f"\n{name} statistics (NtpError <= {STATS_MAX_NTP_ERROR:g}):")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def make_shared_bin_edges() -> np.ndarray:
    plot_max = np.ceil(PLOT_MAX_NTP_ERROR / BIN_WIDTH) * BIN_WIDTH

    # Last bin is overflow bin:
    # normal bins: 0 .. plot_max
    # overflow bin: >= plot_max, drawn from plot_max .. plot_max + BIN_WIDTH
    return np.arange(
        GRAPH_MIN_NTP_ERROR,
        plot_max + BIN_WIDTH + 1e-9,
        BIN_WIDTH,
    )


def plot_histogram(
    s: pd.Series,
    stats_dict: dict,
    title: str,
    out_path: Path,
    bin_edges: np.ndarray,
) -> None:
    x = s.to_numpy()

    # Do not filter negative values out of stats/data, but graph starts at 0.
    x_visible = x[x >= GRAPH_MIN_NTP_ERROR]

    overflow_start = bin_edges[-2]
    overflow_center = overflow_start + BIN_WIDTH * 0.5

    # Values in final bin are overflow: >= overflow_start
    x_binned = np.where(x_visible >= overflow_start, overflow_center, x_visible)
    overflow_count = int(np.sum(x_visible >= overflow_start))
    below_graph_count = int(np.sum(x < GRAPH_MIN_NTP_ERROR))

    p99_low, p99_high = stats_dict["interval_99_ntp_error"]
    p95_low, p95_high = stats_dict["interval_95_ntp_error"]

    fig, ax = plt.subplots(figsize=(11, 6))

    # Only draw intervals if visible in plot range
    if p99_high >= GRAPH_MIN_NTP_ERROR and p99_low < overflow_start:
        ax.axvspan(
            max(p99_low, GRAPH_MIN_NTP_ERROR),
            min(p99_high, overflow_start),
            color="#dddddd",
            alpha=1,
            label=f"99% HDI: [{p99_low:.3f}, {p99_high:.3f}]",
        )

    if p95_high >= GRAPH_MIN_NTP_ERROR and p95_low < overflow_start:
        ax.axvspan(
            max(p95_low, GRAPH_MIN_NTP_ERROR),
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

    if GRAPH_MIN_NTP_ERROR <= stats_dict["mean_ntp_error"] < overflow_start:
        ax.axvline(
            stats_dict["mean_ntp_error"],
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"Mean: {stats_dict['mean_ntp_error']:.3f}",
        )

    if GRAPH_MIN_NTP_ERROR <= stats_dict["median_ntp_error"] < overflow_start:
        ax.axvline(
            stats_dict["median_ntp_error"],
            color="green",
            linestyle="--",
            linewidth=1.5,
            label=f"Median: {stats_dict['median_ntp_error']:.3f}",
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
    ax.set_xlim(GRAPH_MIN_NTP_ERROR, bin_edges[-1])
    ax.set_ylim(bottom=0)
    ax.margins(x=0, y=0)

    ax.spines["left"].set_position(("data", GRAPH_MIN_NTP_ERROR))
    ax.spines["bottom"].set_position(("data", 0))
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)

    ax.set_title(title)
    ax.set_xlabel("Laika sihronizācijas kļūda, ms")
    ax.set_ylabel("Skaits")

    ax.legend()
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.show()


def main() -> None:
    old_s = load_ntp_error(OLD_CSV)
    new_s = load_ntp_error(NEW_CSV)

    old_stats = summarize(old_s)
    new_stats = summarize(new_s)

    print_summary("VecaisNtp.csv", old_stats)
    print_summary("JaunaisNtp.csv", new_stats)

    bin_edges = make_shared_bin_edges()

    print(f"\nbin_width_ntp_error: {BIN_WIDTH}")
    print(f"stats_max_ntp_error: {STATS_MAX_NTP_ERROR}")
    print(f"plot_max_ntp_error: {PLOT_MAX_NTP_ERROR}")
    print(f"graph_min_ntp_error: {GRAPH_MIN_NTP_ERROR}")
    print(f"overflow_bin_starts_at_ntp_error: {bin_edges[-2]}")
    print(f"num_bins_including_overflow: {len(bin_edges) - 1}")
    print(f"bin_start_ntp_error: {bin_edges[0]}")
    print(f"bin_end_ntp_error: {bin_edges[-1]}")

    plot_histogram(
        s=old_s,
        stats_dict=old_stats,
        title="Laika sinhronizācijas kļūda - Asus RT-AC55U maršrutētājs",
        out_path=OLD_PLOT,
        bin_edges=bin_edges,
    )

    plot_histogram(
        s=new_s,
        stats_dict=new_stats,
        title="Laika sinhronizācijas kļūda - Xiaomi AX3000T maršrutētājs",
        out_path=NEW_PLOT,
        bin_edges=bin_edges,
    )


if __name__ == "__main__":
    main()