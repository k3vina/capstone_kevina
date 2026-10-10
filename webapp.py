"""Streamlit app: do countries that spend more on education have more children in school?

Run locally:  uv run streamlit run app.py
"""
import matplotlib.pyplot as plt
import streamlit as st

import analysis as A
import charts as C


REPO_URL = ""
SLIDES_URL = ""
ARTICLE_URL = ""

st.set_page_config(page_title="Education spending and school enrolment", page_icon="📚", layout="centered")


@st.cache_data
def load_everything():
    joined = A.load_joined()
    ctry = A.country_table(joined)
    return {
        "joined": joined,
        "ctry": ctry,
        "by_spending": A.enrolment_by_spending(joined),
        "by_income": A.high_enrolment_by_income(ctry),
        "wealth": A.wealth_check(joined),
        "headline": A.headline_partial(joined),
        "welch": A.welch(ctry, "dropout"),
        "tests": A.run_tests(ctry),
    }


def show(fig):
    st.pyplot(fig)
    plt.close(fig)


try:
    D = load_everything()
except FileNotFoundError:
    st.error(f"Data file not found: {A.DATA_PATH}. Commit data/cleaned/joined.csv to the repository.")
    st.stop()

joined, ctry, headline, tests = D["joined"], D["ctry"], D["headline"], D["tests"]
by_income = D["by_income"]

# numbers used in the text, computed from the data so text and charts always agree
d2 = ctry.dropna(subset=["high_primary"])
share_high = d2.loc[d2["spend_group"] == "high", "high_primary"].astype(int).mean() * 100
share_low = d2.loc[d2["spend_group"] == "low", "high_primary"].astype(int).mean() * 100
low_inc = by_income[by_income["income"] == "Low"].set_index("spend_group")["share"] * 100

# ------------------------------------------------------------------ header
st.title("Does spending more on education put more children in school?")
st.caption("Capstone project, PyData Data Science Foundations. Data: Our World in Data and the World Bank.")

st.markdown(
    "**The question.** Do countries that spend a larger share of their income on education have higher school "
    "enrolment and lower dropout?"
)

st.subheader("The short answer")
st.markdown(
    f"Mostly yes, but the link is modest. Countries that spend more tend to have more children enrolled, "
    f"especially in secondary school, and somewhat less dropout. Part of that link is simply that richer countries "
    f"spend more and enrol more, but some of it remains after accounting for income. The link is clearest in "
    f"low-income countries, where only about {low_inc.get('low', float('nan')):.0f}% of the lower-spending half reach "
    f"90% primary enrolment, against about {low_inc.get('high', float('nan')):.0f}% of the higher-spending half. "
    f"This shows an association, not proof that spending causes enrolment."
)

c1, c2, c3 = st.columns(3)
c1.metric("Countries analysed", f"{len(ctry)}")
c2.metric("Reach 90% primary enrolment, higher spenders", f"{share_high:.0f}%",
          f"{share_high - share_low:+.0f} points vs lower spenders")
c3.metric("Link with spending, income accounted for", f"{headline['r']:.2f}",
          f"likely range {headline['lo']:.2f} to {headline['hi']:.2f}", delta_color="off")

# ------------------------------------------------------------------ chart 1
st.header("1. More spending goes with more students enrolled")
show(C.fig_enrolment_by_spending(D["by_spending"]))
st.markdown(
    "What this shows: grouping all country-years by how much they spend, average enrolment rises at every level of "
    "schooling. Primary enrolment is already high almost everywhere, so there is little room left for spending to "
    "raise it. Secondary and tertiary enrolment rise much more."
)
with st.expander("Show the numbers"):
    t = D["by_spending"].rename(columns={"spend": "average spending (% of GDP)", "value": "average enrolment (%)",
                                         "n": "country-years", "level": "school level"})
    st.dataframe(t.round(1))

# ------------------------------------------------------------------ chart 2
st.header("2. The link is clearest where enrolment is still low")
show(C.fig_high_enrolment_by_income(by_income))
st.markdown(
    "What this shows: within each income group, we split countries into a higher-spending and a lower-spending half "
    "and count how many reach 90% primary enrolment. The gap is largest among low-income countries. In high-income "
    "countries nearly everyone is already at the top, so spending cannot make a visible difference there."
)
with st.expander("Show the numbers"):
    st.dataframe(by_income.assign(share=(by_income["share"] * 100).round(0)).rename(
        columns={"share": "% reaching 90%", "countries": "number of countries"}))

# ------------------------------------------------------------------ chart 3
st.header("3. Is it just that rich countries spend more?")
show(C.fig_wealth_check(D["wealth"]))
st.markdown(
    "What this shows: part of the link is wealth, but not all of it. For primary and secondary enrolment, accounting "
    "for a country's income changes little. For tertiary enrolment and for dropout, about half of the link disappears."
)
with st.expander("Show the numbers"):
    st.dataframe(D["wealth"].drop(columns="key").round(3))

# ------------------------------------------------------------------ explorer
st.header("4. Explore the countries")
left, right = st.columns(2)
outcome = left.selectbox("Outcome", list(A.OUTCOMES.keys()), index=1,
                         format_func=lambda k: A.OUTCOMES[k][1])
groups = right.multiselect("Income groups to show", A.INCOME_ORDER, default=A.INCOME_ORDER)
if groups:
    show(C.fig_country_scatter(ctry, outcome, groups))
else:
    st.info("Pick at least one income group.")

# ------------------------------------------------------------------ chart 5
st.header("5. Dropout")
show(C.fig_dropout_groups(D["welch"]))
st.markdown(
    "What this shows: pupils who start primary school but do not reach the last grade. The higher-spending half of "
    "countries has about 5 points less dropout on average, but the evidence is not conclusive: the gap could be "
    "chance."
)

# ------------------------------------------------------------------ tests
st.header("How sure are we?")
st.markdown(
    "We ran four standard statistical tests comparing higher- and lower-spending countries. Each test gives a "
    "*p-value*: the chance of seeing a gap this large if spending and the outcome were really unrelated. A small "
    "p-value (below 0.05) means the gap would be unusual by chance. It does **not** tell us how big or important "
    "the gap is, and it does not prove that spending causes the difference."
)
show_t = tests[["Question", "Test", "Statistic", "What we saw", "Reading"]].copy()
show_t["p-value"] = tests["p-value"].round(3)
st.dataframe(show_t, hide_index=True)
st.markdown(
    "Two tests are below 0.05 and two are just above it. All four point the same way. Because we ran four tests, "
    "one result below 0.05 could appear by chance; none passes the stricter cut-off of 0.0125 that corrects for "
    "that. So the evidence is consistent but modest."
)

# ------------------------------------------------------------------ meaning and limits
st.header("What this suggests")
st.markdown(
    "- Education budgets are associated with better access to school, most clearly for secondary schooling and "
    "in lower-income countries.\n"
    "- Raising spending alone is unlikely to be enough. Dropout depends on things a budget share does not capture, "
    "such as household poverty and distance to school.\n"
    "- Where primary enrolment is already near full, other measures such as keeping pupils to the last grade and "
    "quality of teaching matter more than the size of the budget."
)

st.header("Limits to keep in mind")
st.markdown(
    "- **Not an experiment.** Countries were not assigned to spend more or less. Stability, aid, geography and "
    "governance may explain some of the differences.\n"
    "- **One row per country for the tests.** The same country appears in many years, so each country is "
    "averaged over the years it has data. Countries are compared on different periods.\n"
    "- **Missing data.** Each result uses only the countries and years where both measures exist; many small "
    "territories are missing.\n"
    "- **Enrolment above 100%.** Gross enrolment counts over-age and under-age pupils, so it can pass 100%."
)

with st.expander("About the data and method"):
    st.markdown(
        f"Six sources, joined on country code and year into one table of **{len(joined):,} country-year rows** "
        f"for {joined['code'].nunique()} countries (1970 to 2025):\n"
        "- Our World in Data: education spending (% of GDP), gross primary and tertiary enrolment, share of "
        "primary-age children out of school.\n"
        "- World Bank WDI: GDP per capita, gross secondary enrolment, persistence to the last primary grade.\n"
        "- World Bank income classification: low, lower-middle, upper-middle and high income.\n\n"
        "Suspect spending values (Micronesia 1972, Somalia 2018 to 2023) were set to missing. "
        "Dropout is 100 minus the share of pupils who reach the last primary grade."
    )

links = [(n, u) for n, u in [("GitHub repository", REPO_URL), ("Slides", SLIDES_URL), ("Article", ARTICLE_URL)] if u]
if links:
    st.divider()
    st.markdown(" | ".join(f"[{n}]({u})" for n, u in links))
