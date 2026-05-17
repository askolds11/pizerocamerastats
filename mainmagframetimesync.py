import pandas as pd
import numpy as np
import arviz as az
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

CSV_PATH = Path("AllFrameTimeSync.csv")  # change path if needed
HISTOGRAM_PATH = Path("frametime_sync_histogram.png")

# CSV columns:
# "PictureTaken", "DifferenceMs", "NtpErrorMillis", "BaseNtpErrorMillis"
df = pd.read_csv(
    CSV_PATH,
    names=["PictureTaken", "DifferenceMs", "NtpErrorMillis", "BaseNtpErrorMillis"],
    parse_dates=["PictureTaken"],
)

diff = df["DifferenceMs"].dropna()
if diff.empty:
    raise ValueError("No DifferenceMs values found.")

x = diff.to_numpy()

# Basic stats
count = int(diff.count())
min_ms = float(diff.min())
max_ms = float(diff.max())
mean_ms = float(diff.mean())
median_ms = float(diff.median())
std_ms = float(diff.std(ddof=1))

# Exact sample mode (can be less useful for near-continuous data)
mode_result = stats.mode(x, keepdims=True)
mode_ms = float(mode_result.mode[0]) if mode_result.count[0] > 0 else float("nan")

# 95% HDI (highest density interval)
hdi_95_low_ms, hdi_95_high_ms = az.hdi(x, prob=0.95)
hdi_95_low_ms = float(hdi_95_low_ms)
hdi_95_high_ms = float(hdi_95_high_ms)

# 99% HDI (highest density interval)
hdi_99_low_ms, hdi_99_high_ms = az.hdi(x, prob=0.99)
hdi_99_low_ms = float(hdi_99_low_ms)
hdi_99_high_ms = float(hdi_99_high_ms)

summary = {
    "count": count,
    "min_ms": min_ms,
    "max_ms": max_ms,
    "mean_ms": mean_ms,
    "median_ms": median_ms,
    "mode_ms": mode_ms,
    "std_ms": std_ms,
    "interval_95_hdi_ms": (hdi_95_low_ms, hdi_95_high_ms),
    "interval_99_hdi_ms": (hdi_99_low_ms, hdi_99_high_ms),
}

print("DifferenceMs statistics:")
for k, v in summary.items():
    print(f"  {k}: {v}")

# Histogram bins: width=5, enough bins for range, 0 aligned to bin edge
bin_width = 5.0
start = np.floor(min_ms / bin_width) * bin_width
end = np.ceil(max_ms / bin_width) * bin_width
start = min(start, 0.0)
end = max(end, 0.0)
bin_edges = np.arange(start, end + bin_width, bin_width)

print(f"bin_width_ms: {bin_width}")
print(f"num_bins: {len(bin_edges) - 1}")
print(f"bin_start_ms: {bin_edges[0]}")
print(f"bin_end_ms: {bin_edges[-1]}")

# Plot
plt.figure(figsize=(11, 6))
plt.axvspan(hdi_99_low_ms, hdi_99_high_ms, color="#dddddd", alpha=1, label=f"99% HDI: [{hdi_99_low_ms:.3f}, {hdi_99_high_ms:.3f}]")
plt.axvspan(hdi_95_low_ms, hdi_95_high_ms, color="#f7c388", alpha=1, label=f"95% HDI: [{hdi_95_low_ms:.3f}, {hdi_95_high_ms:.3f}]")
plt.hist(x, bins=bin_edges, color="steelblue", edgecolor="black", alpha=0.85)
plt.title("Kadru laiku histogramma (sinhronizēts)")
plt.xlabel("Atšķirība no galvenās ierīces (ms)")
plt.ylabel("Skaits")

# plt.axvline(mean_ms, color="red", linestyle="--", linewidth=1.5, label=f"Mean: {mean_ms:.3f}")
# plt.axvline(median_ms, color="green", linestyle="--", linewidth=1.5, label=f"Median: {median_ms:.3f}")


plt.legend()
plt.tight_layout()
plt.savefig(HISTOGRAM_PATH, dpi=200)
plt.show()