"""Data loading and statistics for the capstone: education spending and school outcomes.

Everything here works on joined.csv, the table built in the join notebook.
The notebooks and the Streamlit app both import this file, so the numbers always agree.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DATA_PATH = Path(__file__).parent / "data" / "cleaned" / "joined.csv"
INCOME_ORDER = ["Low", "Lower middle", "Upper middle", "High"]

# plain-language names for the outcomes
OUTCOMES = {
    "primary": ("enr_primary_gross", "Primary school enrolment"),
    "secondary": ("enr_secondary_gross", "Secondary school enrolment"),
    "tertiary": ("enr_tertiary_gross", "Tertiary (university) enrolment"),
    "dropout": ("dropout_proxy", "Pupils who do not reach the last primary grade"),
}


def load_joined(path=DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["log_gdp"] = np.log(df["gdp_pc_ppp"].where(df["gdp_pc_ppp"] > 0))
    return df


def _mode(s):
    return s.mode().iloc[0] if s.notna().any() else np.nan


def country_table(joined: pd.DataFrame) -> pd.DataFrame:
    """One row per country: its average over the years it has data.

    The same country appears in many years with similar values, so country-year rows are
    not independent. Tests are run on this table instead.
    """
    ctry = (joined.groupby("code")
            .agg(country=("country", "first"),
                 spend=("spend_pct_gdp", "mean"),
                 primary=("enr_primary_gross", "mean"),
                 secondary=("enr_secondary_gross", "mean"),
                 tertiary=("enr_tertiary_gross", "mean"),
                 dropout=("dropout_proxy", "mean"),
                 income=("income_group", _mode))
            .dropna(subset=["spend", "income"])
            .reset_index())
    median_in_group = ctry.groupby("income")["spend"].transform("median")
    ctry["spend_group"] = np.where(ctry["spend"] > median_in_group, "high", "low")
    bands = ctry.groupby("income")["spend"].transform(
        lambda s: pd.qcut(s, 3, labels=["low", "middle", "high"]).astype(str))
    ctry["spend_band"] = pd.Categorical(bands, categories=["low", "middle", "high"], ordered=True)
    ctry["high_primary"] = (ctry["primary"] >= 90).astype("Int8").where(ctry["primary"].notna())
    ctry["income"] = pd.Categorical(ctry["income"], categories=INCOME_ORDER, ordered=True)
    return ctry


# ---------------------------------------------------------------- chart data
def enrolment_by_spending(joined: pd.DataFrame, n_bands: int = 8) -> pd.DataFrame:
    """Average enrolment at each spending level (country-years, pooled)."""
    rows = []
    for key in ["primary", "secondary", "tertiary"]:
        col, label = OUTCOMES[key]
        d = joined[["spend_pct_gdp", col]].dropna().copy()
        d["band"] = pd.qcut(d["spend_pct_gdp"], n_bands, duplicates="drop")
        g = d.groupby("band", observed=True).agg(spend=("spend_pct_gdp", "mean"),
                                                 value=(col, "mean"), n=(col, "size")).reset_index(drop=True)
        g["level"] = key
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def high_enrolment_by_income(ctry: pd.DataFrame) -> pd.DataFrame:
    """Share of countries with primary enrolment >= 90%, high vs low spenders, by income group."""
    d = ctry.dropna(subset=["high_primary"]).copy()
    d["high_primary"] = d["high_primary"].astype(int)
    out = (d.groupby(["income", "spend_group"], observed=True)["high_primary"]
             .agg(share="mean", countries="size").reset_index())
    return out


def _residuals(y, z):
    slope, intercept = np.polyfit(z, y, 1)
    return y - (slope * z + intercept)


def partial_corr(df, x, y, z):
    d = df[[x, y, z]].dropna()
    a, b, c = d[x].to_numpy(), d[y].to_numpy(), d[z].to_numpy()
    raw = np.corrcoef(a, b)[0, 1]
    part = np.corrcoef(_residuals(a, c), _residuals(b, c))[0, 1]
    return len(d), raw, part


def wealth_check(joined: pd.DataFrame) -> pd.DataFrame:
    """Correlation of spending with each outcome, before and after accounting for income."""
    rows = []
    for key, (col, label) in OUTCOMES.items():
        n, raw, part = partial_corr(joined, "spend_pct_gdp", col, "log_gdp")
        rows.append({"outcome": label, "key": key, "rows": n, "spending alone": raw,
                     "after accounting for income": part})
    return pd.DataFrame(rows)


def headline_partial(joined: pd.DataFrame, reps: int = 1000, seed: int = 42):
    """Spending vs primary enrolment, accounting for GDP per capita, with a 95% interval
    from resampling whole countries."""
    dd = joined[["code", "spend_pct_gdp", "enr_primary_gross", "log_gdp"]].dropna().reset_index(drop=True)
    idx = [g.index.to_numpy() for _, g in dd.groupby("code")]
    X, Y, Z = (dd[c].to_numpy() for c in ["spend_pct_gdp", "enr_primary_gross", "log_gdp"])

    def pr(ix):
        return np.corrcoef(_residuals(X[ix], Z[ix]), _residuals(Y[ix], Z[ix]))[0, 1]

    rng = np.random.default_rng(seed)
    point = pr(np.arange(len(dd)))
    boot = [pr(np.concatenate([idx[i] for i in rng.integers(0, len(idx), len(idx))])) for _ in range(reps)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"r": point, "lo": lo, "hi": hi, "rows": len(dd), "countries": len(idx)}


# ---------------------------------------------------------------- hypothesis tests
def welch(df, outcome, group="spend_group", hi="high", lo="low"):
    a = df.loc[df[group] == hi, outcome].dropna()
    b = df.loc[df[group] == lo, outcome].dropna()
    t, p = stats.ttest_ind(a, b, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    diff = a.mean() - b.mean()
    ci = diff + np.array([-1, 1]) * stats.t.ppf(0.975, dof) * np.sqrt(va + vb)
    return {"a": a, "b": b, "diff": diff, "ci": ci, "t": t, "p": p}


def two_prop(x1, n1, x0, n0):
    p1, p0 = x1 / n1, x0 / n0
    pooled = (x1 + x0) / (n1 + n0)
    z = (p1 - p0) / np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n0))
    return p1, p0, z, 2 * stats.norm.sf(abs(z))


def run_tests(ctry: pd.DataFrame) -> pd.DataFrame:
    """The four hypothesis tests of Phase 5, in plain language."""
    rows = []
    w = welch(ctry, "dropout")
    rows.append(("Do high-spending countries lose fewer pupils before the last primary grade?",
                 "Welch t-test", f"t = {w['t']:.2f}", w["p"],
                 f"About {abs(w['diff']):.0f} points less dropout in high-spending countries"))

    d2 = ctry.dropna(subset=["high_primary"])
    g = d2.groupby("spend_group")["high_primary"].agg(["sum", "count"]).astype(int)
    p1, p0, z, p = two_prop(g.loc["high", "sum"], g.loc["high", "count"], g.loc["low", "sum"], g.loc["low", "count"])
    rows.append(("Are high-spending countries more likely to reach 90% primary enrolment?",
                 "Two-proportion Z-test", f"z = {z:.2f}", p,
                 f"{p1 * 100:.0f}% of high spenders against {p0 * 100:.0f}% of low spenders"))

    d3 = ctry.dropna(subset=["secondary"])
    groups = [d3.loc[d3["spend_band"] == b, "secondary"] for b in ["low", "middle", "high"]]
    F, p = stats.f_oneway(*groups)
    rows.append(("Does secondary enrolment differ between low, middle and high spenders?",
                 "ANOVA (F-test)", f"F = {F:.2f}", p,
                 f"Averages of {groups[0].mean():.0f}%, {groups[1].mean():.0f}% and {groups[2].mean():.0f}%"))

    d4 = ctry.dropna(subset=["high_primary"])
    ct = pd.crosstab(d4["spend_band"], d4["high_primary"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    rows.append(("Is reaching 90% primary enrolment independent of spending level?",
                 "Chi-square test", f"chi-square = {chi2:.2f}", p,
                 "Share reaching 90%: " + ", ".join(
                     f"{b} {ct.loc[b, 1] / ct.loc[b].sum() * 100:.0f}%" for b in ["low", "middle", "high"])))

    out = pd.DataFrame(rows, columns=["Question", "Test", "Statistic", "p-value", "What we saw"])

    def verdict(p):
        if p < 0.05:
            return "Unlikely to be chance (p below 0.05)"
        if p < 0.10:
            return "Suggestive, not conclusive"
        return "No clear evidence"

    out["Reading"] = out["p-value"].map(verdict)
    return out
