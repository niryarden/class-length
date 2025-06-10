import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
import ast
from scipy.stats import pearsonr, spearmanr, ttest_ind

df = pd.read_parquet("outputs/output.parquet")

def parse_list_column(series):
    def parse(x):
        if isinstance(x, str):
            return ast.literal_eval(x)
        elif isinstance(x, list):
            return x
        elif hasattr(x, "tolist"):
            return x.tolist()
        else:
            return []
    return series.apply(parse)

def analyze_contributions(column_data):
    metrics = []
    for row in column_data:
        counts = sorted(row, reverse=True)
        total = sum(counts)
        result = {}
        for i in range(1, 6):
            top_total = sum(counts[:i])
            result[f"top_{i}_contributors_percent"] = round((top_total / total) * 100, 2) if total else 0.0
        for i in range(1, 6):
            result[f"{i}_time_contributors"] = counts.count(i)
        metrics.append(result)
    return pd.DataFrame(metrics)

def extract_lengths(col):
    parsed = parse_list_column(col)
    stats = pd.DataFrame()
    stats["mean_effective_length"] = parsed.apply(lambda x: sum(x) / len(x) if x else 0)
    stats["median_effective_length"] = parsed.apply(lambda x: sorted(x)[len(x)//2] if x else 0)
    stats["max_effective_length"] = parsed.apply(lambda x: max(x) if x else 0)
    return stats

contrib_lists = parse_list_column(df["contributors_distribution"])
contrib_metrics = analyze_contributions(contrib_lists)
length_stats = extract_lengths(df["class_effective_lengths"])

df = pd.concat([df.reset_index(drop=True), contrib_metrics, length_stats], axis=1)

# Define column groups
length_cols = ["mean_effective_length", "median_effective_length", "max_effective_length"]
top_contrib_cols = [f"top_{i}_contributors_percent" for i in range(1, 6)]
low_contrib_cols = [f"{i}_time_contributors" for i in range(1, 6)]
all_metrics = length_cols + top_contrib_cols + low_contrib_cols

# Create output directory
os.makedirs("analysis_outputs/plots", exist_ok=True)

# Descriptive statistics
desc_stats = df[all_metrics].describe(percentiles=[.05, .25, .5, .75, .95]).T
desc_stats.to_excel("analysis_outputs/descriptive_statistics.xlsx")

# Histograms and CDFs with mean and median lines
for col in all_metrics:
    mean_val = df[col].mean()
    median_val = df[col].median()

    plt.figure(figsize=(6, 4))
    sns.histplot(df[col], bins=30, kde=False)
    plt.axvline(mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.2f}")
    plt.axvline(median_val, color="blue", linestyle=":", label=f"Median: {median_val:.2f}")
    plt.title(f"Histogram of {col}")
    plt.xlabel(col)
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"analysis_outputs/plots/histogram_{col}.png")
    plt.close()

    plt.figure(figsize=(6, 4))
    sorted_vals = np.sort(df[col])
    cdf = np.arange(1, len(sorted_vals)+1) / len(sorted_vals)
    plt.plot(sorted_vals, cdf, label="CDF")
    plt.axvline(mean_val, color="red", linestyle="--", label=f"Mean: {mean_val:.2f}")
    plt.axvline(median_val, color="blue", linestyle=":", label=f"Median: {median_val:.2f}")
    plt.title(f"CDF of {col}")
    plt.xlabel(col)
    plt.ylabel("Cumulative Probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"analysis_outputs/plots/cdf_{col}.png")
    plt.close()

# LLCD plots
for col in length_cols + [f"{i}_time_contributors" for i in range(1, 6)]:
    plt.figure(figsize=(6, 4))
    vals = df[col].replace(0, np.nan).dropna()
    vals_sorted = np.sort(vals)
    ccdf = 1.0 - np.arange(1, len(vals_sorted) + 1) / len(vals_sorted)
    plt.loglog(vals_sorted, ccdf)
    plt.title(f"Log-Log Complementary CDF of {col}")
    plt.xlabel(col)
    plt.ylabel("1 - CDF")
    plt.tight_layout()
    plt.savefig(f"analysis_outputs/plots/llcd_{col}.png")
    plt.close()

# Correlation analysis and scatter plots with Pearson annotation
pearson_rows = []

for l_col in length_cols:
    for c_col in top_contrib_cols + low_contrib_cols:
        pearson_corr, p_p = pearsonr(df[l_col], df[c_col])
        pearson_rows.append({"Length Metric": l_col, "Contribution Metric": c_col, "Correlation": pearson_corr, "p-value": p_p})

        plt.figure(figsize=(6, 4))
        sns.regplot(x=df[l_col], y=df[c_col], scatter_kws={"s": 10}, line_kws={"color": "red"})
        plt.title(f"{l_col} vs {c_col}")
        plt.xlabel(l_col)
        plt.ylabel(c_col)
        plt.text(0.05, 0.95, f"r={pearson_corr:.4f}, p={p_p}",
                 transform=plt.gca().transAxes, fontsize=9, verticalalignment='top',
                 bbox=dict(facecolor='white', alpha=0.5))
        plt.tight_layout()
        plt.savefig(f"analysis_outputs/plots/scatter_{l_col}_vs_{c_col}.png")
        plt.close()

pd.DataFrame(pearson_rows).to_excel("analysis_outputs/pearson_correlations_annotated.xlsx", index=False)

# T-test and boxplots with annotation
df["centralized"] = df["top_1_contributors_percent"] > 80
ttest_rows = []

for l_col in length_cols:
    centralized_vals = df[df["centralized"]][l_col]
    non_centralized_vals = df[~df["centralized"]][l_col]
    t_stat, p_val = ttest_ind(centralized_vals, non_centralized_vals, equal_var=False)
    ttest_rows.append({"Length Metric": l_col, "t-stat": t_stat, "p-value": p_val})

    plt.figure(figsize=(6, 4))
    sns.boxplot(x="centralized", y=l_col, data=df)
    plt.title(f"{l_col} by Centralization (Top1 > 80%)")
    plt.xlabel("Centralized (>80%)")
    plt.ylabel(l_col)
    plt.text(0.05, 0.95, f"t={t_stat:.4f}, p={p_val}",
             transform=plt.gca().transAxes, fontsize=9, verticalalignment='top',
             bbox=dict(facecolor='white', alpha=0.5))
    plt.tight_layout()
    plt.savefig(f"analysis_outputs/plots/boxplot_{l_col}_centralized_annotated.png")
    plt.close()

pd.DataFrame(ttest_rows).to_excel("analysis_outputs/ttest_results_updated.xlsx", index=False)
