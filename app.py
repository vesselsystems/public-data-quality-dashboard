"""Streamlit entry point for the data-quality dashboard."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from data_quality_dashboard.data import load_with_sql, yearly_summary
from data_quality_dashboard.provenance import ProvenanceMetadataError, validate_provenance
from data_quality_dashboard.quality import (
    quality_score,
    run_quality_checks,
    temperature_order_anomalies,
)

PROJECT_ROOT = Path(__file__).parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "seattle_weather.csv"
PROVENANCE_PATH = PROJECT_ROOT / "data" / "raw" / "provenance.json"

st.set_page_config(page_title="Public Data Quality Dashboard", page_icon="📊", layout="wide")

st.title("Public Data Quality & EDA Dashboard")
st.caption("A SQL-to-Python workflow: validate first, interpret second.")

with st.sidebar:
    st.subheader("Snapshot provenance")
    if PROVENANCE_PATH.exists():
        try:
            provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
            source = provenance["source"]
            snapshot = provenance["local_snapshot"]
            if not isinstance(source, dict) or not isinstance(snapshot, dict):
                raise ValueError("source and local_snapshot must be objects")
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
            st.warning(f"Provenance metadata cannot be displayed: {error}")
        else:
            st.markdown(f"[{source['publisher']}]({source['url']})")
            st.caption(f"Upstream revision: `{source['upstream_ref']}`")
            st.caption(f"SHA-256: `{snapshot['sha256']}`")
            st.caption(f"Retrieved: {snapshot['retrieved_at_utc'] or 'not recorded'}")
            st.caption(source["license_or_terms"])
    else:
        st.warning("Provenance metadata is not available.")

if not DATA_PATH.exists():
    st.error("The dataset has not been downloaded yet.")
    st.code("python scripts/download_data.py")
    st.stop()

try:
    provenance_result = validate_provenance(
        PROVENANCE_PATH,
        raw_path=DATA_PATH,
        project_root=PROJECT_ROOT,
    )
except ProvenanceMetadataError as error:
    st.error(f"The tracked provenance metadata is invalid: {error}")
    st.stop()
if not provenance_result.passed:
    detail = "; ".join(provenance_result.errors) or "snapshot measurements do not match"
    st.error(f"The local snapshot failed provenance validation: {detail}")
    st.caption("No dashboard analysis is shown until the reviewed snapshot is restored.")
    st.stop()

source_frame = load_with_sql(DATA_PATH)
checks = run_quality_checks(source_frame)
anomalies = temperature_order_anomalies(source_frame)
score = quality_score(checks)
core_checks = [check for check in checks if check.name != "calendar_coverage"]
coverage_check = next(check for check in checks if check.name == "calendar_coverage")
# Keep validation tied to source order, then sort only the display data.
frame = source_frame.sort_values("date", kind="stable").reset_index(drop=True)

left, middle, right, far_right = st.columns(4)
left.metric(
    "Core quality score",
    f"{score}% ({sum(check.passed for check in core_checks)}/{len(core_checks)})",
)
middle.metric("Observations", f"{len(frame):,}")
right.metric("Start date", str(frame["date"].min()) if not frame.empty else "—")
far_right.metric("End date", str(frame["date"].max()) if not frame.empty else "—")

st.write(
    "The dashboard makes source completeness and analytical assumptions visible before showing "
    "temperature trends."
)
st.caption(
    "The score is the historical seven-check summary; calendar coverage is a separate "
    "supplemental check so the score's meaning remains comparable across runs."
)
coverage_message = (
    f"Calendar coverage: {'PASS' if coverage_check.passed else 'FAIL'} — "
    f"{coverage_check.detail}"
)
if coverage_check.passed:
    st.success(coverage_message)
else:
    st.warning(coverage_message)

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

    st.subheader("Temperature-order anomaly review")
    st.caption(
        "These rows violate min ≤ mean ≤ max. They remain in the descriptive output; no values "
        "are swapped, imputed, or excluded automatically."
    )
    if anomalies.empty:
        st.success("No temperature-order anomalies found.")
    else:
        st.warning(f"{len(anomalies):,} rows require review.")
        st.dataframe(anomalies, use_container_width=True, hide_index=True)
        st.download_button(
            "Download anomaly review CSV",
            anomalies.to_csv(index=False),
            file_name="temperature_order_anomalies.csv",
            mime="text/csv",
        )

with tab_trends:
    st.subheader("Mean temperature over time")
    if frame.empty:
        st.warning("No rows are available for a trend or annual summary.")
    else:
        # Reindex the display copy to the daily calendar so missing periods are
        # rendered as gaps rather than an apparently continuous line.
        chart_source = frame[["date", "mean_temperature_c"]].drop_duplicates(
            subset=["date"], keep="first"
        )
        chart_frame = (
            chart_source.set_index("date")
            .reindex(pd.date_range(frame["date"].min(), frame["date"].max(), freq="D"))
            .rename_axis("date")
            .reset_index()
        )
        chart = px.line(
            chart_frame,
            x="date",
            y="mean_temperature_c",
            labels={"date": "Date", "mean_temperature_c": "Mean temperature (°C)"},
            title="Seattle daily mean temperature (observed dates only)",
        )
        chart.update_layout(hovermode="x unified")
        st.plotly_chart(chart, use_container_width=True)
        st.caption(
            "Blank intervals represent missing calendar days; the chart does not impute or "
            "connect those periods. Quality checks and anomaly tables retain source rows."
        )

        yearly = yearly_summary(frame)
        st.subheader("Annual summary")
        st.dataframe(yearly, use_container_width=True, hide_index=True)

with tab_sql:
    st.subheader("What the SQL layer does")
    st.code(
        """
SELECT
    rowid + 1 AS source_row_number,
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
        "The full auditable quality query is in `sql/quality_checks.sql`; it includes the "
        "calendar-coverage and temperature-order review queries. DuckDB keeps the SQL step "
        "reproducible without requiring a separate database server."
    )
