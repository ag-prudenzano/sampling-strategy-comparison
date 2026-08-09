from pathlib import Path
import subprocess

try:
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
except ImportError as exc:
    raise SystemExit(
        "Missing Python packages. Install them with: pip install -r requirements.txt"
    ) from exc

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = ROOT / "figures"
REPORT_FILE = ROOT / "report.md"
POPULATION_FILE = DATA_DIR / "sampling_strategy_population.csv"

POPULATION_SIZE = 50_000
POPULATION_SEED = 20260809
SAMPLE_SIZE = 800
REPEATED_SAMPLES = 400
REPEATED_SAMPLE_SEED = 20260810
REFERENCE_SAMPLE_SEED = 20260811

AGE_BANDS = ["18-24", "25-34", "35-44", "45-54", "55-64", "65-74"]
GENDERS = ["Woman", "Man", "Non-binary / other"]
REGIONS = ["London", "South", "Midlands", "North", "Scotland/Wales"]

FIGURE_BACKGROUND = "#0C0C0D"
FIGURE_TEXT = "#FFFFFF"
FIGURE_MUTED = "#A2A2A9"
FIGURE_LINE = "#313135"
FIGURE_BAR = "#494950"
FIGURE_ACCENT = "#FFFFFF"


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )


def repository_has_origin() -> bool:
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return False
    if inside.returncode != 0 or inside.stdout.strip().lower() != "true":
        return False
    origin = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return origin.returncode == 0


def check_repository_up_to_date() -> bool:
    if not repository_has_origin():
        print("GitHub remote not detected; running analysis without repository sync.")
        return False

    print("Checking repository status against GitHub...")
    run_git("fetch", "origin")
    branch = run_git("branch", "--show-current").stdout.strip()
    remote_ref = f"origin/{branch}" if branch else "origin/main"

    if subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", remote_ref],
        cwd=ROOT,
        capture_output=True,
        text=True,
    ).returncode != 0:
        remote_ref = "origin/main"
        run_git("rev-parse", "--verify", remote_ref)

    comparison = run_git(
        "rev-list", "--left-right", "--count", f"HEAD...{remote_ref}"
    ).stdout.split()
    local_only, remote_only = [int(value) for value in comparison]

    if remote_only > 0:
        message = (
            f"Your Codespace is {remote_only} commit(s) behind {remote_ref}.\n"
            "The analysis stopped before replacing generated files.\n\n"
            "Run:\n\n    git pull --ff-only\n\nThen run:\n\n    python analysis.py"
        )
        if local_only > 0:
            message += (
                "\n\nYour local branch also has commits not on the remote. "
                "Review the Git history if a fast-forward pull cannot complete."
            )
        raise SystemExit(message)

    print(f"Repository is up to date with {remote_ref}.")
    return True


def save_generated_files_to_repository(sync_enabled: bool) -> None:
    if not sync_enabled:
        return

    generated_paths = [
        "report.md",
        "data/sampling_strategy_population.csv",
        "outputs",
        "figures",
    ]
    run_git("add", "--", *generated_paths)
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", *generated_paths], cwd=ROOT
    ).returncode

    if staged == 0:
        print("No generated changes to commit.")
        return
    if staged != 1:
        raise SystemExit("Could not determine whether generated files changed.")

    run_git(
        "commit",
        "-m",
        "Update sampling strategy comparison results",
        "--",
        *generated_paths,
    )
    branch = run_git("branch", "--show-current").stdout.strip()
    if not branch:
        raise SystemExit("Cannot automatically push from a detached Git HEAD.")
    run_git("push", "origin", branch)
    print(f"Generated files committed and pushed to origin/{branch}.")


def ensure_population_file() -> None:
    if POPULATION_FILE.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(POPULATION_SEED)

    age_band = rng.choice(
        AGE_BANDS, POPULATION_SIZE, p=[0.12, 0.20, 0.19, 0.18, 0.17, 0.14]
    )
    gender = rng.choice(GENDERS, POPULATION_SIZE, p=[0.50, 0.48, 0.02])
    region = rng.choice(
        REGIONS, POPULATION_SIZE, p=[0.13, 0.25, 0.21, 0.27, 0.14]
    )

    urban_probability = {
        "London": 0.91,
        "South": 0.68,
        "Midlands": 0.65,
        "North": 0.675,
        "Scotland/Wales": 0.575,
    }
    urbanicity = np.array(
        [
            "Urban" if rng.random() < urban_probability[value] else "Rural / small town"
            for value in region
        ]
    )

    age_digital = {
        "18-24": 74.0,
        "25-34": 70.0,
        "35-44": 62.0,
        "45-54": 53.5,
        "55-64": 43.0,
        "65-74": 34.0,
    }
    digital = (
        np.array([age_digital[value] for value in age_band], dtype=float)
        + np.where(urbanicity == "Urban", 9.7, 0.0)
        + rng.normal(0, 12, POPULATION_SIZE)
    )
    digital = np.clip(np.round(digital, 1), 0, 100)

    age_interest = {
        "18-24": 0.00,
        "25-34": 0.40,
        "35-44": 0.08,
        "45-54": -0.43,
        "55-64": -0.90,
        "65-74": -1.22,
    }
    region_interest = {
        "London": 0.00,
        "South": -0.37,
        "Midlands": -0.44,
        "North": -0.54,
        "Scotland/Wales": -0.56,
    }
    interest = (
        3.55
        + 0.0275 * digital
        + np.array([age_interest[value] for value in age_band])
        + np.array([region_interest[value] for value in region])
        + np.where(urbanicity == "Urban", 0.38, 0.0)
        + rng.normal(0, 1.58, POPULATION_SIZE)
    )
    interest = np.clip(np.round(interest, 1), 0, 10)

    population = pd.DataFrame(
        {
            "person_id": [f"P{number:05d}" for number in range(1, POPULATION_SIZE + 1)],
            "age_band": age_band,
            "gender": gender,
            "region": region,
            "urbanicity": urbanicity,
            "digital_engagement_score": digital,
            "concept_interest_0_10": interest,
            "likely_to_try": (interest >= 7).astype(int),
        }
    )
    population.to_csv(POPULATION_FILE, index=False)
    print(f"Synthetic population generated: {POPULATION_FILE.relative_to(ROOT)}")


def load_population() -> pd.DataFrame:
    population = pd.read_csv(POPULATION_FILE)
    required = {
        "person_id",
        "age_band",
        "gender",
        "region",
        "urbanicity",
        "digital_engagement_score",
        "concept_interest_0_10",
        "likely_to_try",
    }
    missing = sorted(required.difference(population.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if population["person_id"].duplicated().any():
        raise ValueError("Population contains duplicate person_id values.")
    if len(population) < SAMPLE_SIZE:
        raise ValueError("Population is smaller than the requested sample size.")
    if not population["concept_interest_0_10"].between(0, 10).all():
        raise ValueError("concept_interest_0_10 contains values outside 0-10.")
    if not population["likely_to_try"].isin([0, 1]).all():
        raise ValueError("likely_to_try must contain only 0 and 1.")
    return population


def proportional_allocation(keys: pd.Series, n: int) -> pd.Series:
    raw = keys.value_counts(normalize=True).sort_index() * n
    allocation = np.floor(raw).astype(int)
    remainder = n - int(allocation.sum())
    if remainder:
        fractional = (raw - allocation).sort_values(ascending=False)
        allocation.loc[fractional.index[:remainder]] += 1
    return allocation


def prepare_design(population: pd.DataFrame) -> dict[str, object]:
    age_region = population["age_band"].astype(str) + "|" + population["region"].astype(str)
    age_gender = population["age_band"].astype(str) + "|" + population["gender"].astype(str)

    stratified_allocation = proportional_allocation(age_region, SAMPLE_SIZE)
    quota_allocation = proportional_allocation(age_gender, SAMPLE_SIZE)

    stratified_pools = {
        key: np.flatnonzero(age_region.to_numpy() == key)
        for key in stratified_allocation.index
    }
    quota_pools = {}
    for key in quota_allocation.index:
        pool = np.flatnonzero(age_gender.to_numpy() == key)
        frame = population.iloc[pool]
        engagement = frame["digital_engagement_score"].to_numpy()
        urban = frame["urbanicity"].eq("Urban").to_numpy()
        weight = np.exp((engagement - 55) / 35) * np.where(urban, 1.15, 0.85)
        quota_pools[key] = (pool, weight / weight.sum())

    engagement = population["digital_engagement_score"].to_numpy()
    urban = population["urbanicity"].eq("Urban").to_numpy()
    convenience_weight = np.exp((engagement - 55) / 24) * np.where(urban, 1.35, 0.65)

    return {
        "population_size": len(population),
        "stratified_allocation": stratified_allocation,
        "stratified_pools": stratified_pools,
        "quota_allocation": quota_allocation,
        "quota_pools": quota_pools,
        "convenience_weight": convenience_weight / convenience_weight.sum(),
    }


def draw_simple_random(design: dict[str, object], rng: np.random.Generator) -> np.ndarray:
    return rng.choice(int(design["population_size"]), SAMPLE_SIZE, replace=False)


def draw_stratified(design: dict[str, object], rng: np.random.Generator) -> np.ndarray:
    selected = []
    for key, count in design["stratified_allocation"].items():
        selected.append(
            rng.choice(design["stratified_pools"][key], int(count), replace=False)
        )
    return np.concatenate(selected)


def draw_quota(design: dict[str, object], rng: np.random.Generator) -> np.ndarray:
    selected = []
    for key, count in design["quota_allocation"].items():
        pool, weight = design["quota_pools"][key]
        selected.append(rng.choice(pool, int(count), replace=False, p=weight))
    return np.concatenate(selected)


def draw_convenience(design: dict[str, object], rng: np.random.Generator) -> np.ndarray:
    return rng.choice(
        int(design["population_size"]),
        SAMPLE_SIZE,
        replace=False,
        p=design["convenience_weight"],
    )


STRATEGIES = {
    "Simple random": draw_simple_random,
    "Proportional stratified": draw_stratified,
    "Quota": draw_quota,
    "Convenience": draw_convenience,
}


def evaluate_repeated_samples(
    population: pd.DataFrame, design: dict[str, object]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    interest = population["concept_interest_0_10"].to_numpy()
    likely = population["likely_to_try"].to_numpy()
    digital = population["digital_engagement_score"].to_numpy()
    true_mean = float(interest.mean())
    true_likely = float(likely.mean())
    true_digital = float(digital.mean())

    rows = []
    for method_index, (strategy, draw) in enumerate(STRATEGIES.items()):
        rng = np.random.default_rng(REPEATED_SAMPLE_SEED + method_index)
        for replicate in range(1, REPEATED_SAMPLES + 1):
            indices = draw(design, rng)
            mean_interest = float(interest[indices].mean())
            likely_share = float(likely[indices].mean())
            mean_digital = float(digital[indices].mean())
            rows.append(
                {
                    "strategy": strategy,
                    "replicate": replicate,
                    "mean_concept_interest": mean_interest,
                    "mean_error": mean_interest - true_mean,
                    "likely_to_try_share": likely_share,
                    "likely_to_try_error_pp": (likely_share - true_likely) * 100,
                    "mean_digital_engagement": mean_digital,
                    "digital_engagement_error": mean_digital - true_digital,
                }
            )

    estimates = pd.DataFrame(rows)
    summary_rows = []
    for strategy, group in estimates.groupby("strategy", sort=False):
        error = group["mean_error"]
        likely_error = group["likely_to_try_error_pp"]
        summary_rows.append(
            {
                "strategy": strategy,
                "average_mean_estimate": group["mean_concept_interest"].mean(),
                "mean_bias": error.mean(),
                "empirical_sd": group["mean_concept_interest"].std(ddof=1),
                "mean_absolute_error": error.abs().mean(),
                "rmse": float(np.sqrt(np.mean(np.square(error)))),
                "likely_to_try_bias_pp": likely_error.mean(),
                "likely_to_try_rmse_pp": float(np.sqrt(np.mean(np.square(likely_error)))),
                "digital_engagement_bias": group["digital_engagement_error"].mean(),
            }
        )
    return estimates, pd.DataFrame(summary_rows)


def build_reference_samples(
    population: pd.DataFrame, design: dict[str, object]
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = []
    estimate_rows = []
    composition_rows = []
    population_mean = population["concept_interest_0_10"].mean()
    population_likely = population["likely_to_try"].mean()

    variables = ["age_band", "gender", "region"]
    population_shares = {
        variable: population[variable].value_counts(normalize=True)
        for variable in variables
    }

    for method_index, (strategy, draw) in enumerate(STRATEGIES.items()):
        rng = np.random.default_rng(REFERENCE_SAMPLE_SEED + method_index)
        indices = draw(design, rng)
        sample = population.iloc[indices].copy()
        sample.insert(0, "strategy", strategy)
        frames.append(sample)

        mean_interest = sample["concept_interest_0_10"].mean()
        likely_share = sample["likely_to_try"].mean()
        estimate_rows.append(
            {
                "strategy": strategy,
                "mean_concept_interest": mean_interest,
                "mean_error": mean_interest - population_mean,
                "likely_to_try_share": likely_share,
                "likely_to_try_error_pp": (likely_share - population_likely) * 100,
                "mean_digital_engagement": sample["digital_engagement_score"].mean(),
            }
        )

        for variable in variables:
            sample_shares = sample[variable].value_counts(normalize=True)
            categories = population_shares[variable].index
            for category in categories:
                population_share = float(population_shares[variable].get(category, 0))
                sample_share = float(sample_shares.get(category, 0))
                composition_rows.append(
                    {
                        "strategy": strategy,
                        "variable": variable,
                        "category": category,
                        "population_share": population_share,
                        "sample_share": sample_share,
                        "difference_pp": (sample_share - population_share) * 100,
                        "absolute_difference_pp": abs(sample_share - population_share) * 100,
                    }
                )

    return (
        pd.concat(frames, ignore_index=True),
        pd.DataFrame(estimate_rows),
        pd.DataFrame(composition_rows),
    )


def style_axis(ax: plt.Axes, grid_axis: str) -> None:
    ax.figure.patch.set_facecolor(FIGURE_BACKGROUND)
    ax.set_facecolor(FIGURE_BACKGROUND)
    ax.tick_params(colors=FIGURE_MUTED, labelsize=9.5, length=0, pad=7)
    ax.xaxis.label.set_color(FIGURE_MUTED)
    ax.yaxis.label.set_color(FIGURE_MUTED)
    ax.title.set_color(FIGURE_TEXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis=grid_axis, color=FIGURE_LINE, linewidth=0.8, alpha=0.6)
    ax.set_axisbelow(True)


def create_figures(
    population: pd.DataFrame,
    repeated_estimates: pd.DataFrame,
    reference_composition: pd.DataFrame,
) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    population_mean = population["concept_interest_0_10"].mean()

    with plt.rc_context({"font.family": "sans-serif", "font.size": 10}):
        fig, ax = plt.subplots(figsize=(10, 5.8))
        style_axis(ax, "y")
        positions = np.arange(len(STRATEGIES))
        values = [
            repeated_estimates.loc[
                repeated_estimates["strategy"].eq(strategy), "mean_concept_interest"
            ].to_numpy()
            for strategy in STRATEGIES
        ]
        box = ax.boxplot(values, positions=positions, widths=0.55, patch_artist=True)
        for patch in box["boxes"]:
            patch.set_facecolor(FIGURE_BAR)
            patch.set_edgecolor(FIGURE_MUTED)
        for key in ["whiskers", "caps", "medians"]:
            for item in box[key]:
                item.set_color(FIGURE_MUTED if key != "medians" else FIGURE_TEXT)
        for flier in box["fliers"]:
            flier.set_markeredgecolor(FIGURE_MUTED)
        ax.axhline(
            population_mean,
            color=FIGURE_ACCENT,
            linestyle=(0, (4, 4)),
            linewidth=1.6,
            label=f"Population mean  {population_mean:.3f}",
        )
        ax.set_xticks(positions, list(STRATEGIES))
        ax.set_ylabel("Estimated mean concept interest", labelpad=12)
        ax.set_title("Repeated-sample estimates", loc="left", pad=18, fontsize=16, fontweight=400, color=FIGURE_TEXT)
        legend = ax.legend(frameon=False, loc="upper left", fontsize=9.5)
        for text in legend.get_texts():
            text.set_color(FIGURE_MUTED)
        fig.tight_layout(pad=1.6)
        fig.savefig(
            FIGURE_DIR / "estimate_distribution_by_strategy.png",
            dpi=200,
            facecolor=FIGURE_BACKGROUND,
            bbox_inches="tight",
        )
        plt.close(fig)

        deviation = (
            reference_composition.groupby("strategy", sort=False)["absolute_difference_pp"]
            .mean()
            .reindex(list(STRATEGIES))
        )
        fig, ax = plt.subplots(figsize=(9.6, 5.6))
        style_axis(ax, "x")
        bars = ax.barh(list(STRATEGIES), deviation.values, height=0.58, color=FIGURE_BAR)
        maximum = max(float(deviation.max()), 1.0)
        ax.set_xlim(0, maximum * 1.18)
        ax.set_xlabel("Average absolute demographic deviation (percentage points)", labelpad=12)
        ax.set_title("Reference-sample demographic deviation", loc="left", pad=18, fontsize=16, fontweight=400, color=FIGURE_TEXT)
        for bar, value in zip(bars, deviation.values):
            ax.text(
                bar.get_width() + maximum * 0.025,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.2f}",
                va="center",
                color=FIGURE_TEXT,
                fontsize=9.5,
            )
        fig.tight_layout(pad=1.6)
        fig.savefig(
            FIGURE_DIR / "demographic_deviation_by_strategy.png",
            dpi=200,
            facecolor=FIGURE_BACKGROUND,
            bbox_inches="tight",
        )
        plt.close(fig)


def generate_report(
    population: pd.DataFrame,
    performance: pd.DataFrame,
    reference_estimates: pd.DataFrame,
    reference_composition: pd.DataFrame,
) -> None:
    population_mean = float(population["concept_interest_0_10"].mean())
    population_likely = float(population["likely_to_try"].mean())
    lookup = performance.set_index("strategy")
    srs_rmse = float(lookup.loc["Simple random", "rmse"])
    strat_rmse = float(lookup.loc["Proportional stratified", "rmse"])
    strat_improvement = (srs_rmse - strat_rmse) / srs_rmse * 100
    quota_bias = float(lookup.loc["Quota", "mean_bias"])
    convenience_bias = float(lookup.loc["Convenience", "mean_bias"])
    convenience_likely_bias = float(lookup.loc["Convenience", "likely_to_try_bias_pp"])

    composition_average = (
        reference_composition.groupby("strategy", sort=False)["absolute_difference_pp"]
        .mean()
        .reindex(list(STRATEGIES))
    )

    performance_rows = []
    for method in STRATEGIES:
        row = lookup.loc[method]
        performance_rows.append(
            f"| {method} | {row['average_mean_estimate']:.3f} | {row['mean_bias']:+.3f} | "
            f"{row['empirical_sd']:.3f} | {row['rmse']:.3f} | {row['likely_to_try_bias_pp']:+.2f} pp |"
        )

    reference_rows = []
    for _, row in reference_estimates.iterrows():
        method = row["strategy"]
        reference_rows.append(
            f"| {method} | {row['mean_concept_interest']:.3f} | {row['mean_error']:+.3f} | "
            f"{row['likely_to_try_share'] * 100:.1f}% | {composition_average.loc[method]:.2f} pp |"
        )

    report = f"""# Sampling Strategy Comparison

## Study Context

This simulated case study is set within a hypothetical UK online concept survey for a fictional meal-kit subscription. A synthetic population of {len(population):,} adults aged 18–74 provides a known benchmark against which different sampling strategies can be evaluated.

The population proportions and behavioural relationships are entirely simulated and should not be interpreted as estimates of the real UK population. Each sampling strategy draws {SAMPLE_SIZE:,} respondents from the same synthetic population.

## Sampling Objective

The objective is to compare how sampling design affects representativeness, bias and precision when estimating concept interest from a finite population.

The primary estimand is the population mean on a 0–10 concept-interest scale. The secondary estimand is the share of the population scoring 7 or higher, treated as likely to try the concept.

## Sampling Strategies

### Simple random sampling

Every population member has the same selection probability. This provides the probability-sampling benchmark for the comparison.

### Proportional stratified sampling

The population is divided by age band and region. Sample allocation is proportional to each age-by-region stratum, with respondents selected randomly within strata.

### Quota sampling

Age-band and gender quotas reproduce the corresponding population margins, but selection within each quota cell favours more digitally engaged and urban respondents. This models a non-probability online-access mechanism that can remain biased even when visible quotas are matched.

### Convenience sampling

Selection probability increases substantially with digital engagement and urban residence. This represents an easily reached online sample without probability controls or demographic quotas.

## Population Benchmark

The synthetic population mean concept-interest score is {population_mean:.3f}. The population share classified as likely to try is {population_likely * 100:.1f}%.

## Findings

Across {REPEATED_SAMPLES} repeated samples per strategy, simple random and proportional stratified sampling were essentially unbiased. Proportional stratification reduced RMSE for the mean estimate by {strat_improvement:.1f}% relative to simple random sampling.

Quota sampling matched its selected demographic controls closely but still overestimated mean concept interest by {quota_bias:+.3f} points on average. Convenience sampling produced the largest distortion, overestimating mean concept interest by {convenience_bias:+.3f} points and the likely-to-try share by {convenience_likely_bias:+.2f} percentage points on average.

| Strategy | Average mean estimate | Mean bias | Empirical SD | RMSE | Likely-to-try bias |
|---|---:|---:|---:|---:|---:|
{chr(10).join(performance_rows)}

## Reference Sample

A single fixed reference draw is included to make the composition differences tangible. Demographic deviation is the average absolute percentage-point difference across age-band, gender and region categories.

| Strategy | Mean estimate | Mean error | Likely to try | Avg. demographic deviation |
|---|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

## Interpretation

The comparison demonstrates two distinct sampling problems. Probability sampling controls selection directly, while non-probability methods can reproduce selected demographic margins without reproducing the population on variables related to the outcome.

The quota sample is the clearest example: its age and gender composition is deliberately close to the population, yet the within-quota preference for digitally engaged respondents shifts the concept-interest estimate upward. Demographic matching therefore reduces some visible imbalance but does not by itself establish representativeness.

The convenience sample performs worst because the same accessibility mechanism that determines who is easy to reach is also related to concept interest. The proportional stratified design performs best on RMSE because it preserves probability selection while controlling the age-by-region composition of every sample.

## Figures

### Repeated-sample estimates

![Repeated-sample estimates by strategy](figures/estimate_distribution_by_strategy.png)

The dashed line marks the known population mean. Probability samples remain centred close to the benchmark, while quota and convenience samples are shifted upward.

### Demographic deviation

![Reference-sample demographic deviation by strategy](figures/demographic_deviation_by_strategy.png)

The reference sample shows that low demographic deviation does not guarantee an unbiased outcome estimate when selection within demographic groups is non-random.

## Project Files

- [`report.md`](report.md) — this report.
- [`data/sampling_strategy_population.csv`](data/sampling_strategy_population.csv) — synthetic finite population used as the benchmark.
- [`data/sampling_strategy_codebook.csv`](data/sampling_strategy_codebook.csv) — variable definitions.
- [`data/sampling_strategy_scenario.csv`](data/sampling_strategy_scenario.csv) — scenario and simulation parameters.
- [`outputs/repeated_sample_estimates.csv`](outputs/repeated_sample_estimates.csv) — estimate from every repeated sample.
- [`outputs/sampling_performance.csv`](outputs/sampling_performance.csv) — bias, precision and RMSE summary by strategy.
- [`outputs/reference_sample_estimates.csv`](outputs/reference_sample_estimates.csv) — estimates from the fixed reference draw.
- [`outputs/reference_sample_composition.csv`](outputs/reference_sample_composition.csv) — population and reference-sample category shares.
- [`outputs/reference_samples.csv`](outputs/reference_samples.csv) — respondent rows selected in the four fixed reference samples.
- [`figures/estimate_distribution_by_strategy.png`](figures/estimate_distribution_by_strategy.png) — repeated-sample estimate distributions.
- [`figures/demographic_deviation_by_strategy.png`](figures/demographic_deviation_by_strategy.png) — reference-sample demographic deviation.
"""
    REPORT_FILE.write_text(report.strip() + "\n", encoding="utf-8")


def main() -> None:
    sync_enabled = check_repository_up_to_date()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    ensure_population_file()

    population = load_population()
    design = prepare_design(population)
    repeated, performance = evaluate_repeated_samples(population, design)
    reference_samples, reference_estimates, reference_composition = build_reference_samples(
        population, design
    )

    repeated.to_csv(OUTPUT_DIR / "repeated_sample_estimates.csv", index=False)
    performance.to_csv(OUTPUT_DIR / "sampling_performance.csv", index=False)
    reference_estimates.to_csv(OUTPUT_DIR / "reference_sample_estimates.csv", index=False)
    reference_composition.to_csv(OUTPUT_DIR / "reference_sample_composition.csv", index=False)
    reference_samples.to_csv(OUTPUT_DIR / "reference_samples.csv", index=False)

    create_figures(population, repeated, reference_composition)
    generate_report(population, performance, reference_estimates, reference_composition)

    print("Sampling Strategy Comparison")
    print("=" * 28)
    print(f"Population loaded: {len(population):,}")
    print(f"Sample size per strategy: {SAMPLE_SIZE:,}")
    print(f"Repeated samples per strategy: {REPEATED_SAMPLES:,}")
    print(f"Population mean concept interest: {population['concept_interest_0_10'].mean():.3f}")
    print("\nRMSE by strategy:")
    for _, row in performance.iterrows():
        print(f"  {row['strategy']}: {row['rmse']:.3f}")
    print(f"\nReport written to: {REPORT_FILE.relative_to(ROOT)}")
    print(f"Outputs saved to: {OUTPUT_DIR.relative_to(ROOT)}/")
    print(f"Figures saved to: {FIGURE_DIR.relative_to(ROOT)}/")

    save_generated_files_to_repository(sync_enabled)


if __name__ == "__main__":
    main()
