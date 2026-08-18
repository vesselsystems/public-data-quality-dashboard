"""Streamlit entry point for the data-quality dashboard."""

from pathlib import Path

import plotly.express as px
import streamlit as st

from data_quality_dashboard.data import load_with_sql, yearly_summary
from data_quality_dashboard.quality import quality_score, run_quality_checks

DATA_PATH = Path(__file__).parent / "data" / "raw" / "seattle_weather.csv"

st.set_page_config(page_title="Public Data Quality Dashboard", page_icon="📊", layout="wide")

st.title("Public Data Quality & EDA Dashboard")
st.caption("A SQL-to-Python workflow: validate first, interpret second.")

if not DATA_PATH.exists():
    st.error("The dataset has not been downloaded yet.")
    st.code("python scripts/download_data.py")
    st.stop()

source_frame = load_with_sql(DATA_PATH)
checks = run_quality_checks(source_frame)
score = quality_score(checks)
# Keep validation tied to source order, then sort only the display data.
frame = source_frame.sort_values("date", kind="stable").reset_index(drop=True)

left, middle, right, far_right = st.columns(4)
left.metric("Quality score", f"{score}%")
middle.metric("Observations", f"{len(frame):,}")
right.metric("Start date", str(frame["date"].min()))
far_right.metric("End date", str(frame["date"].max()))

st.write(
    "The dashboard makes source completeness and analytical assumptions visible before showing "
    "temperature trends."
)

tab_quality, tab_trends, tab_sql = st.tabs(["Quality checks", "EDA", "SQL summary"])

with tab_quality:
    st.subheader("Data quality checks")
    st.dataframe(
        {
            "Check": [check.name for check in checks],
            "Status": ["PASS" if check.passed else "FAIL" for check in checks],
            "Evidence": [check.detail for check in checks],
        },
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Checks are implemented in src/data_quality_dashboard/quality.py; chronology is checked "
        "before this display sort."
    )

with tab_trends:
    st.subheader("Mean temperature over time")
    chart = px.line(
        frame,
        x="date",
        y="mean_temperature_c",
        labels={"date": "Date", "mean_temperature_c": "Mean temperature (°C)"},
        title="Seattle daily mean temperature",
    )
    chart.update_layout(hovermode="x unified")
    st.plotly_chart(chart, use_container_width=True)

    yearly = yearly_summary(frame)
    st.subheader("Annual summary")
    st.dataframe(yearly, use_container_width=True, hide_index=True)

with tab_sql:
    st.subheader("What the SQL layer does")
    st.code(
        """
SELECT
    TRY_CAST(Date AS DATE) AS date,
    TRY_CAST(Max_TemperatureC AS DOUBLE) AS max_temperature_c,
    TRY_CAST(Mean_TemperatureC AS DOUBLE) AS mean_temperature_c,
    TRY_CAST(Min_TemperatureC AS DOUBLE) AS min_temperature_c
FROM weather_raw
ORDER BY rowid;
        """,
        language="sql",
    )
    st.markdown(
        "The full auditable quality query is in `sql/quality_checks.sql`. "
        "DuckDB keeps the SQL step reproducible without requiring a separate database server."
    )
