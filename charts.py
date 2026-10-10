"""Labelled charts for the capstone. Each function returns a matplotlib Figure.

The notebook and the Streamlit app both call these functions, so they show the same charts.
Colours follow a validated categorical palette (blue, orange, aqua) and a one-hue blue ramp
for the ordered income groups.
"""
import textwrap

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from analysis import INCOME_ORDER, OUTCOMES

matplotlib.rcParams.update({"font.family": "DejaVu Sans", "axes.unicode_minus": False})

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#6b6a66", "#e6e5e1"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INCOME_COLORS = {"Low": "#86b6ef", "Lower middle": "#3987e5", "Upper middle": "#1c5cab", "High": "#0d366b"}


def _base(figsize=(8.2, 4.6)):
    fig, ax = plt.subplots(figsize=figsize, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=10, length=0)
    ax.yaxis.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(INK2)
    ax.yaxis.label.set_color(INK2)
    return fig, ax


def _titles(fig, title, subtitle=None, left=0.09, right=0.97):
    w_in = fig.get_figwidth()
    tw, sw = int(w_in * 8.0), int(w_in * 11.8)
    t_lines = textwrap.wrap(title, tw)
    s_lines = textwrap.wrap(subtitle, sw) if subtitle else []
    fig.text(0.012, 0.975, "\n".join(t_lines), fontsize=13.5, fontweight="bold",
             color=INK, va="top", ha="left", linespacing=1.25)
    y_sub = 0.975 - 0.068 * len(t_lines) - 0.012
    if s_lines:
        fig.text(0.012, y_sub, "\n".join(s_lines), fontsize=9.5, color=MUTED, va="top", ha="left", linespacing=1.3)
    top = y_sub - 0.046 * len(s_lines) - 0.06
    fig.subplots_adjust(top=top, left=left, right=right, bottom=0.19)


def _source(fig, text):
    lines = textwrap.wrap(text, int(fig.get_figwidth() * 13))
    fig.text(0.012, 0.012, "\n".join(lines), fontsize=8, color=MUTED, va="bottom", ha="left")


def _legend(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=9.5, labelcolor=INK2, **kw)
    return leg


# --------------------------------------------------------------- 1. enrolment by spending level
def fig_enrolment_by_spending(df):
    """df from analysis.enrolment_by_spending."""
    fig, ax = _base()
    spec = [("primary", "Primary", BLUE), ("secondary", "Secondary", ORANGE), ("tertiary", "Tertiary", AQUA)]
    for key, label, color in spec:
        g = df[df["level"] == key]
        ax.plot(g["spend"], g["value"], color=color, lw=2, marker="o", ms=6, mec=SURFACE, mew=1.5,
                label=f"{label} school" if key != "tertiary" else "Tertiary (university)")
        ax.annotate(label, (g["spend"].iloc[-1], g["value"].iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=10, color=INK)
    ax.set_xlabel("Education spending (% of a country's GDP): average in each of 8 spending levels")
    ax.set_ylabel("Average enrolment (% of age group)")
    ax.set_ylim(0, 115)
    ax.set_xlim(None, df["spend"].max() + 1.3)
    _legend(ax, loc="lower right")
    _titles(fig, "Countries that spend more tend to have more students enrolled",
            "Enrolment rises with spending at every level of schooling, most clearly for secondary and tertiary. "
            "Enrolment can pass 100% because it counts over-age and under-age pupils.")
    _source(fig, "Sources: Our World in Data, World Bank. Country-years 1970 to 2025 grouped into 8 spending levels.")
    return fig


# --------------------------------------------------------------- 2. who gains: income groups
def fig_high_enrolment_by_income(df):
    """df from analysis.high_enrolment_by_income."""
    fig, ax = _base()
    x = np.arange(len(INCOME_ORDER))
    w = 0.34
    series = [("high", "Higher-spending half", BLUE, +w / 2), ("low", "Lower-spending half", ORANGE, -w / 2)]
    for grp, label, color, off in series:
        vals, ns = [], []
        for inc in INCOME_ORDER:
            r = df[(df["income"] == inc) & (df["spend_group"] == grp)]
            vals.append(float(r["share"].iloc[0]) * 100 if len(r) else np.nan)
            ns.append(int(r["countries"].iloc[0]) if len(r) else 0)
        bars = ax.bar(x + off, vals, width=w - 0.04, color=color, label=label)
        for xi, v in zip(x + off, vals):
            ax.annotate(f"{v:.0f}%", (xi, v), xytext=(0, 4), textcoords="offset points", ha="center",
                        fontsize=10, color=INK)
    totals = [int(df[df["income"] == inc]["countries"].sum()) for inc in INCOME_ORDER]
    ax.set_xticks(x)
    ax.set_xticklabels([f"{inc} income\n({n} countries)" for inc, n in zip(INCOME_ORDER, totals)])
    ax.set_ylim(0, 118)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Share of countries")
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    _legend(ax, loc="upper left", ncol=2)
    _titles(fig, "In low-income countries, higher spenders far more often reach high primary enrolment",
            "Share of countries with primary enrolment of at least 90%. Each country is compared with others in "
            "its own income group; in high-income countries nearly all are already at the top.")
    _source(fig, "Sources: Our World in Data, World Bank. One value per country (average over its years). "
                 "Differences are not proof that spending causes enrolment.")
    return fig


# --------------------------------------------------------------- 3. is it just wealth?
def fig_wealth_check(df):
    """df from analysis.wealth_check."""
    fig, ax = _base(figsize=(8.2, 4.4))
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, lw=0.8)
    y = np.arange(len(df))
    h = 0.34
    for col, label, color, off in [("spending alone", "Spending alone", BLUE, -h / 2),
                                   ("after accounting for income", "After accounting for a country's income", ORANGE, +h / 2)]:
        vals = df[col].to_numpy()
        ax.barh(y + off, vals, height=h - 0.04, color=color, label=label)
        for yi, v in zip(y + off, vals):
            ax.annotate(f"{v:+.2f}", (v, yi), xytext=(5 if v >= 0 else -5, 0), textcoords="offset points",
                        ha="left" if v >= 0 else "right", va="center", fontsize=9.5, color=INK)
    ax.axvline(0, color=INK2, lw=1)
    short = {"primary": "Primary enrolment", "secondary": "Secondary enrolment", "tertiary": "Tertiary enrolment",
             "dropout": "Dropout\n(negative = less dropout)"}
    ax.set_yticks(y)
    ax.set_yticklabels([short[k] for k in df["key"]])
    ax.invert_yaxis()
    ax.set_xlim(-0.5, 0.55)
    ax.set_xlabel("Strength of the link with spending (0 = no link, 1 = perfect link)")
    _legend(ax, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    _titles(fig, "Part of the link is just wealth, but some remains", left=0.27, subtitle=
            "Richer countries both spend and enrol more. The orange bars remove that effect; "
            "secondary enrolment keeps its link, tertiary and dropout lose about half.")
    _source(fig, "Sources: Our World in Data, World Bank. Correlations on country-years with data for all three measures.")
    return fig


# --------------------------------------------------------------- 4. scatter by country
def fig_country_scatter(ctry, outcome="secondary", income_groups=None):
    income_groups = list(income_groups) if income_groups else list(INCOME_ORDER)
    col = {"primary": "primary", "secondary": "secondary", "tertiary": "tertiary", "dropout": "dropout"}[outcome]
    label = OUTCOMES[outcome][1]
    d = ctry[ctry["income"].isin(income_groups)].dropna(subset=["spend", col])
    fig, ax = _base()
    for inc in INCOME_ORDER:
        s = d[d["income"] == inc]
        if len(s):
            ax.scatter(s["spend"], s[col], s=42, color=INCOME_COLORS[inc], edgecolor=SURFACE, linewidth=0.8,
                       label=inc, zorder=3)
    r = np.nan
    if len(d) > 5:
        slope, intercept = np.polyfit(d["spend"], d[col], 1)
        xs = np.linspace(d["spend"].min(), d["spend"].max(), 50)
        ax.plot(xs, slope * xs + intercept, color=INK2, lw=1.8, ls="--", zorder=2)
        r = np.corrcoef(d["spend"], d[col])[0, 1]
    ax.set_xlabel("Education spending (% of GDP), average for the country")
    ax.set_ylabel(f"{label} (%)" if outcome != "dropout" else "Pupils not reaching last grade (%)")
    _legend(ax, loc="upper left", bbox_to_anchor=(1.01, 1.0), title="Income group", title_fontsize=9.5)
    link = "no clear link" if abs(r) < 0.1 else ("a weak link" if abs(r) < 0.3 else "a moderate link")
    titles = {"primary": "Spending and primary enrolment, country by country",
              "secondary": "Spending and secondary enrolment, country by country",
              "tertiary": "Spending and tertiary enrolment, country by country",
              "dropout": "Spending and dropout, country by country"}
    _titles(fig, titles[outcome],
            f"Each dot is one country. The dashed line is the overall trend. Link with spending: {r:.2f} ({link}); "
            f"0 means no link. {len(d)} countries shown.", right=0.80)
    _source(fig, "Sources: Our World in Data, World Bank. Averages over the years each country has data.")
    return fig


# --------------------------------------------------------------- 5. dropout
def fig_dropout_groups(w):
    """w is the dict returned by analysis.welch(ctry, 'dropout')."""
    fig, ax = _base(figsize=(7.4, 4.6))
    data = [("Lower-spending\ncountries", w["b"], ORANGE), ("Higher-spending\ncountries", w["a"], BLUE)]
    rng = np.random.default_rng(1)
    for i, (name, s, color) in enumerate(data):
        ax.scatter(i + rng.uniform(-0.18, 0.18, len(s)), s, s=30, color=color, alpha=0.55,
                   edgecolor=SURFACE, linewidth=0.6, zorder=3)
        ax.hlines(s.mean(), i - 0.3, i + 0.3, color=INK, lw=2.5, zorder=4)
        ax.annotate(f"average {s.mean():.0f}%", (i + 0.33, s.mean()), va="center", fontsize=10, color=INK)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([d[0] for d in data])
    ax.set_xlim(-0.6, 1.9)
    ax.set_ylabel("Pupils not reaching last grade (%)")
    lo, hi = w["ci"]
    _titles(fig, "Dropout is somewhat lower in higher-spending countries, but the evidence is not conclusive",
            f"Each dot is one country. The gap is about {abs(w['diff']):.0f} points. Allowing for chance, the true gap could be "
            f"anywhere between {abs(lo):.0f} points lower and {max(hi, 0):.1f} points higher (test result p = {w['p']:.2f}).")
    _source(fig, "Sources: Our World in Data, World Bank. Dropout is 100 minus the share of pupils who reach the last primary grade.")
    return fig
