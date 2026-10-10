# capstone_kevina

# Does spending more on education put more children in school?

PyData Data Science Foundations, Week 5 capstone, organised by the six CRISP-DM phases.

## The question

**Do countries that spend more on education, relative to their income, have higher school enrolment (primary, secondary, tertiary) and lower dropout?**

## Links

| Deliverable | Link |
| --- | --- |
| Live app (Streamlit Community Cloud) | [ADD APP LINK] |
| Slides (one per CRISP-DM phase) | [ADD SLIDES LINK] |
| Article | [ADD SUBSTACK OR MEDIUM LINK] |

## Short answer

Mostly yes, but modestly. Countries that spend more tend to have more children enrolled, most clearly in secondary school and in low-income countries.

- After accounting for a country's income, the link between spending and primary enrolment is 0.18 (likely range 0.08 to 0.27). For secondary enrolment it is 0.34.
- For university enrolment and dropout, about half of the link is explained by a country's wealth.
- Four hypothesis tests (t-test, two-proportion Z-test, ANOVA, chi-square) give p-values between 0.029 and 0.067, all pointing the same way.
- This is an association, not proof that spending causes enrolment. Countries were not randomly assigned to spend more or less.

## Data

Six tables from two publishers, joined by country code and year into one table of **10,562 rows and 20 columns** (225 countries and territories, 1970 to 2025).

| Source | What it provides |
| --- | --- |
| Our World in Data | Education spending (% of GDP), primary and tertiary gross enrolment, children out of school |
| World Bank (WDI) | GDP per capita (PPP), secondary enrolment, persistence to the last primary grade |
| World Bank income groups | Low, lower-middle, upper-middle and high income classification |

Our World in Data republishes some World Bank and UNESCO figures, so the two publishers are not fully independent evidence.

## Method in brief

1. **Business understanding:** question, decision and hypothesis written before looking at the data.
2. **Data understanding:** shape, data types, missing values, central tendency, spread and one distribution per table.
3. **Data preparation:** outer joins on country code and year, a left join for income group, suspect spending values (Micronesia 1972, Somalia 2018 to 2023) set to missing rather than filled, and engineered columns (dropout, higher or lower spender within income group, 90% primary enrolment flag, one-year lagged spending).
4. **Modeling (no machine learning):** Pearson and Spearman correlations, partial correlation controlling for log GDP per capita, a country-level bootstrap for the likely range, and conditional probabilities.
5. **Evaluation:** four hypothesis tests on one row per country (203 countries). Each states H0 and H1, a real statistic and p-value, and what a p-value is not.
6. **Deployment:** the Streamlit app in this repository.

The tests use one row per country because the same country appears in many years, and those rows are not independent.

## Repository layout

```
.
├── app.py                  Streamlit app
├── analysis.py             data loading and statistics (used by the app and notebooks)
├── charts.py               labelled charts (used by the app and notebooks)
├── .streamlit/config.toml  app theme
├── data/
│   ├── raw/                original downloads
│   └── cleaned/            cleaned tables and joined.csv
├── notebooks/              one notebook per phase, including:
│   ├── 09_phase4_modeling.ipynb
│   ├── 10_phase5_hypothesis_tests.ipynb
│   └── 11_phase6_charts.ipynb
├── pyproject.toml
├── uv.lock
└── README.md
```

Adjust the notebook list to match the files in your `notebooks/` folder.

## Run it locally

This project uses [uv](https://docs.astral.sh/uv/).

```bash
git clone capstone_kevina
cd capstone_kevina
uv sync
uv run streamlit run webapp.py
```

To rerun the analysis, open the notebooks in order and use Restart and Run All. The join notebook rebuilds `data/cleaned/joined.csv`.

## Limits

- Not an experiment: stability, aid, geography and governance may explain some differences.
- Spending is missing in more than half of the country-years, and each result uses only rows where both measures exist.
- Countries are averaged over the years they have data, and those years differ between countries.
- Gross enrolment can exceed 100% because it counts over-age and under-age pupils.

## Data sources

- Our World in Data: <https://ourworldindata.org>
- World Bank World Development Indicators and income classification: <https://data.worldbank.org>
