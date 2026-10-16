"""Streamlit dashboard: do countries that spend more on education have more children in school?

Run locally:  uv run streamlit run app.py
"""
import matplotlib.pyplot as plt
import streamlit as st

import analysis as A
import charts as C

# Fill these in once the article, slides and repo exist. Empty strings are not shown.
REPO_URL = "https://github.com/k3vina/capstone_kevina/tree/main"
SLIDES_URL = "https://1drv.ms/p/c/0c4589f2251de4da/IQAm5bbFdFX1SI8Qsle-Us2cAahCJXLVEThddCQkLw19sl8?e=x6BTF9"
ARTICLE_URL = "https://medium.com/@kevinajepkonga/does-spending-more-on-education-put-more-children-in-school-3a1056176edb?postPublishedType=repub"

st.set_page_config(page_title="Education spending and school enrolment", page_icon="📚",
                   layout="wide", initial_sidebar_state="expanded")


@st.cache_data
def load_all():
    return A.load_joined()


def safe(fn, *args, **kwargs):
    """Run a calculation; return None if the current filters leave too little data."""
    try:
        return fn(*args, **kwargs)
    except (ValueError, KeyError, IndexError, ZeroDivisionError):
        return None


@st.cache_data
def compute(groups: tuple, years: tuple):
    """Everything the dashboard shows, for the chosen income groups and years."""
    j = load_all()
    if set(groups) != set(A.INCOME_ORDER):
        j = j[j["income_group"].isin(groups)]
    if years != (int(load_all()["year"].min()), int(load_all()["year"].max())):
        j = j[(j["year"] >= years[0]) & (j["year"] <= years[1])]
    ctry = A.country_table(j)
    out = {"joined": j, "ctry": ctry, "enough": len(ctry) >= 10}
    if not out["enough"]:
        return out
    out["by_spending"] = safe(A.enrolment_by_spending, j) if len(j) > 200 else None
    out["by_income"] = safe(A.high_enrolment_by_income, ctry)
    out["wealth"] = safe(A.wealth_check, j)
    out["headline"] = safe(A.headline_partial, j, 500)
    out["welch"] = safe(A.welch, ctry, "dropout")
    out["tests"] = safe(A.run_tests, ctry)
    return out


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


def not_enough(what="this chart"):
    st.info(f"Not enough countries with data for {what}. Widen the filters in the sidebar.")


DATA_DIR = A.DATA_PATH.parent
DATASETS = {
    "joined.csv": "The main table: all six sources joined on country code and year, with the new columns. "
                  "This is what every chart is built from.",
    "owid_spend_pct_gdp.csv": "Education spending as a share of GDP (Our World in Data), with a flag for suspect values.",
    "owid_enr_primary_gross.csv": "Gross primary school enrolment (Our World in Data).",
    "owid_enr_tertiary_gross.csv": "Gross tertiary (university) enrolment (Our World in Data).",
    "owid_enr_upper_secondary.csv": "Upper secondary enrolment (Our World in Data).",
    "owid_out_of_school_share.csv": "Share of primary-age children out of school (Our World in Data).",
    "wdi_clean.csv": "Cleaned World Bank indicators: GDP per capita, enrolment at each level, persistence to the last primary grade.",
    "income_groups.csv": "World Bank income classification of each economy by year.",
}
COLUMN_NOTES = [
    ("code", "Three-letter country code used to join the tables"),
    ("year", "Calendar year"),
    ("country", "Country or territory name"),
    ("spend_pct_gdp", "Education spending, % of GDP"),
    ("enr_primary_gross / enr_secondary_gross / enr_tertiary_gross", "Gross enrolment, % of the age group (can pass 100%)"),
    ("enr_primary_net / enr_secondary_net / enr_preprimary", "Net primary, net secondary and pre-primary enrolment, %"),
    ("out_of_school_share", "Share of primary-age children out of school, %"),
    ("gdp_pc_ppp", "GDP per capita, adjusted for purchasing power (World Bank)"),
    ("persistence_last_grade", "% of pupils who start primary school and reach the last grade"),
    ("spend_per_primary_student", "Spending per primary student, as published by the World Bank"),
    ("income_group", "World Bank income group: Low, Lower middle, Upper middle, High"),
    ("spend_suspect", "True where the spending value looked wrong and was set to missing"),
    ("dropout_proxy", "New column: 100 minus persistence_last_grade"),
    ("spend_lag1", "New column: spending one year earlier"),
    ("high_spend", "New column: 1 if spending is above the median of its income group"),
    ("high_enrol_primary", "New column: 1 if gross primary enrolment is 90% or more"),
]


@st.cache_data
def read_bytes(name: str) -> bytes:
    return (DATA_DIR / name).read_bytes()


@st.cache_data
def csv_shape(name: str):
    import pandas as pd
    df = pd.read_csv(DATA_DIR / name)
    return df.shape


def to_csv_bytes(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


joined_all = load_all()
Y0, Y1 = int(joined_all["year"].min()), int(joined_all["year"].max())

# ------------------------------------------------------------------ sidebar filters
st.sidebar.header("Filters")
groups = st.sidebar.multiselect("Income groups", A.INCOME_ORDER, default=A.INCOME_ORDER,
                                help="Countries are grouped by the World Bank by their income level.")
years = st.sidebar.slider("Years", Y0, Y1, (Y0, Y1))
st.sidebar.caption("Every chart and number on the dashboard updates with these filters. "
                   "Each country is averaged over the years it has data inside the range.")
st.sidebar.divider()
st.sidebar.caption("Data: Our World in Data and the World Bank.")

if not groups:
    st.warning("Pick at least one income group in the sidebar.")
    st.stop()

D = compute(tuple(groups), tuple(years))
FULL = compute(tuple(A.INCOME_ORDER), (Y0, Y1))
ctry, joined = D["ctry"], D["joined"]

# ------------------------------------------------------------------ header
st.title("Does spending more on education put more children in school?")
st.caption("Capstone project, PyData Data Science Foundations")

low_inc = {}
if FULL.get("by_income") is not None:
    low_inc = (FULL["by_income"][FULL["by_income"]["income"] == "Low"]
               .set_index("spend_group")["share"] * 100).to_dict()
st.info(
    "**The short answer:** mostly yes, but the link is modest. Countries that spend more tend to have more children "
    "enrolled, especially in secondary school, and somewhat less dropout. Part of that is simply that richer countries "
    "spend more and enrol more, but some of it remains after accounting for income. The link is clearest in "
    "low-income countries"
    + (f", where about {low_inc.get('low', float('nan')):.0f}% of the lower-spending half reach 90% primary enrolment, "
       f"against about {low_inc.get('high', float('nan')):.0f}% of the higher-spending half" if low_inc else "")
    + ". This shows an association, not proof that spending causes enrolment."
)

if not D["enough"]:
    st.warning("Fewer than 10 countries match these filters. Widen the income groups or the year range.")
    st.stop()

# ------------------------------------------------------------------ headline numbers
d2 = ctry.dropna(subset=["high_primary"])
sg = d2.assign(hp=d2["high_primary"].astype(int)).groupby("spend_group")["hp"].mean() * 100
hl, w = D["headline"], D["welch"]

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("Countries in view", f"{len(ctry)}")
    st.caption(f"{len(joined):,} country-years of data")
with k2:
    if {"high", "low"} <= set(sg.index):
        st.metric("Higher spenders reaching 90%", f"{sg['high']:.0f}%")
        st.caption(f"Primary enrolment. {sg['low']:.0f}% of lower spenders ({sg['high'] - sg['low']:+.0f} points)")
    else:
        st.metric("Higher spenders reaching 90%", "n/a")
with k3:
    if hl:
        st.metric("Link with spending, income removed", f"{hl['r']:.2f}")
        st.caption(f"Primary enrolment. Likely range {hl['lo']:.2f} to {hl['hi']:.2f}")
    else:
        st.metric("Link with spending, income removed", "n/a")
with k4:
    if w:
        st.metric("Dropout gap, higher vs lower spenders", f"{w['diff']:+.1f} points")
        st.caption(f"Test p-value {w['p']:.2f}")
    else:
        st.metric("Dropout gap, higher vs lower spenders", "n/a")

st.caption("The notes beside each chart describe all countries and years. The charts and numbers follow your filters.")

# ------------------------------------------------------------------ tabs
t1, t2, t3, t4, t5, t7 = st.tabs([
    "Spending and enrolment", "By income group", "Is it just wealth?",
    "Explore countries", "Hypothesis tests", "Download data",
])

with t1:
    left, right = st.columns([2, 1])
    with left:
        if D["by_spending"] is not None:
            show(C.fig_enrolment_by_spending(D["by_spending"]))
        else:
            not_enough()
    with right:
        st.subheader("What this shows")
        st.markdown(
            "Country-years are sorted into eight groups by how much they spend, and the average enrolment of each "
            "group is plotted.\n\n"
            "Enrolment rises with spending at every level of schooling. Primary enrolment is already high almost "
            "everywhere, so there is little room left to rise. Secondary and tertiary enrolment rise much more."
        )
        if D["by_spending"] is not None:
            with st.expander("Show the numbers"):
                tb = D["by_spending"].rename(columns={"spend": "average spending (% of GDP)",
                                                      "value": "average enrolment (%)",
                                                      "n": "country-years", "level": "school level"})
                st.dataframe(tb.round(1), hide_index=True)

with t2:
    left, right = st.columns([2, 1])
    with left:
        if D["by_income"] is not None and len(D["by_income"]):
            show(C.fig_high_enrolment_by_income(D["by_income"]))
        else:
            not_enough()
    with right:
        st.subheader("What this shows")
        st.markdown(
            "Within each income group, countries are split into a higher-spending and a lower-spending half, and we "
            "count how many reach 90% primary enrolment.\n\n"
            "The gap is largest among low-income countries. In high-income countries nearly everyone is already at "
            "the top, so spending cannot make a visible difference there."
        )
        if D["by_income"] is not None and len(D["by_income"]):
            with st.expander("Show the numbers"):
                st.dataframe(D["by_income"].assign(share=(D["by_income"]["share"] * 100).round(0)).rename(
                    columns={"share": "% reaching 90%", "countries": "number of countries"}), hide_index=True)

with t3:
    left, right = st.columns([2, 1])
    with left:
        if D["wealth"] is not None and D["wealth"]["rows"].min() >= 30:
            show(C.fig_wealth_check(D["wealth"]))
        else:
            not_enough()
    with right:
        st.subheader("What this shows")
        st.markdown(
            "Richer countries both spend more and enrol more. The blue bars show the link with spending alone. "
            "The orange bars remove the effect of a country's income.\n\n"
            "For primary and secondary enrolment, accounting for income changes little. For tertiary enrolment and "
            "for dropout, about half of the link disappears."
        )
        if D["wealth"] is not None:
            with st.expander("Show the numbers"):
                st.dataframe(D["wealth"].drop(columns="key").round(3), hide_index=True)

with t4:
    c_out, c_note = st.columns([1, 2])
    outcome = c_out.selectbox("Outcome", list(A.OUTCOMES.keys()), index=1, format_func=lambda k: A.OUTCOMES[k][1])
    c_note.markdown("Each dot is one country, averaged over the years it has data. "
                    "The dashed line is the overall trend. Use the sidebar to change which countries are shown.")
    left, right = st.columns([2, 1])
    with left:
        show(C.fig_country_scatter(ctry, outcome, groups))
    with right:
        st.markdown("**Countries in this view**")
        col = outcome
        tb = ctry[["country", "income", "spend", col]].dropna().sort_values(col, ascending=False)
        tb = tb.rename(columns={"country": "Country", "income": "Income group",
                                "spend": "Spending (% GDP)", col: "Outcome (%)"})
        st.dataframe(tb.round(1), hide_index=True, height=420)

with t5:
    st.subheader("Hypothesis tests")
    tests = D["tests"]
    if tests is not None and len(tests):
        sh = tests[["Question", "Test", "Statistic", "p-value", "What we saw", "Reading"]].copy()
        sh["p-value"] = sh["p-value"].map(lambda p: f"{p:.3f}")
        st.table(sh.style.hide(axis="index"))
        st.caption("Higher- and lower-spending countries were not randomized, so these are comparisons, not an experiment. "
                   "A p-value is not the chance that spending causes the difference.")
    else:
        not_enough("the tests")

with t7:
    st.subheader("Download the data")
    st.markdown("Every table behind the dashboard is available as a CSV file. "
                "Please credit Our World in Data and the World Bank if you reuse them.")

    st.markdown("**1. What you are looking at now** (follows the sidebar filters)")
    d1, d2c = st.columns(2)
    with d1:
        view = joined.drop(columns=["log_gdp"], errors="ignore")
        st.download_button("Country-year table, filtered", to_csv_bytes(view), "country_year_filtered.csv",
                           "text/csv", help=f"{len(view):,} rows")
        st.caption(f"{len(view):,} rows, one per country and year.")
    with d2c:
        st.download_button("Country table, filtered", to_csv_bytes(ctry), "country_table_filtered.csv",
                           "text/csv", help=f"{len(ctry):,} rows")
        st.caption(f"{len(ctry):,} rows, one per country, averaged over the years in view. "
                   "The tests and the country charts use this table.")

    st.markdown("**2. The cleaned tables**")
    for name, desc in DATASETS.items():
        path = DATA_DIR / name
        if not path.exists():
            continue
        shape = csv_shape(name)
        c_a, c_b = st.columns([4, 1])
        c_a.markdown(f"**{name}**  \n{desc}  \n*{shape[0]:,} rows, {shape[1]} columns*")
        c_b.download_button("Download", read_bytes(name), name, "text/csv", key=f"dl_{name}")

    with st.expander("Preview the joined table"):
        st.dataframe(joined_all.drop(columns=["log_gdp"], errors="ignore").head(200), hide_index=True)

    with st.expander("What each column means"):
        import pandas as pd
        st.dataframe(pd.DataFrame(COLUMN_NOTES, columns=["Column", "Meaning"]), hide_index=True)

# ------------------------------------------------------------------ footer: project links, shown under every tab
links = [(n, u) for n, u in [("GitHub repository", REPO_URL), ("Slides", SLIDES_URL), ("Article", ARTICLE_URL)] if u]
if links:
    st.divider()
    st.markdown("**Project links:** " + " | ".join(f"[{n}]({u})" for n, u in links))