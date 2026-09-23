"""
Brisbane River Water Quality Analysis -- Live Dashboard

Run locally with:
    streamlit run app.py

Reuses the same cleaning logic as the notebooks (src/cleaning.py) and follows
the same reproducibility pattern: if the cleaned dataset isn't present, it
auto-downloads the raw CSV from this repo's GitHub Release and regenerates it.
"""
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import cleaning  # noqa: E402

st.set_page_config(
    page_title="Brisbane River Water Quality",
    page_icon="\U0001F30A",
    layout="wide",
)

RAW_PATH = Path("data/raw/brisbane_water_quality.csv")
PROCESSED_PATH = Path("data/processed/water_quality_cleaned.csv")
DATA_URL = (
    "https://github.com/davis-mironga/brisbane-river-water-quality-analysis/"
    "releases/download/v1.0-data/brisbane_water_quality.csv"
)

SEASON_ORDER = ["Summer", "Autumn", "Winter", "Spring"]

PARAM_LABELS = {
    "temperature": "Temperature (\u00b0C)",
    "dissolved_oxygen": "Dissolved Oxygen (mg/L)",
    "dissolved_oxygen_pct_sat": "Dissolved Oxygen (% Saturation)",
    "ph": "pH",
    "salinity": "Salinity (PSU)",
    "specific_conductance": "Specific Conductance",
    "turbidity": "Turbidity (NTU)",
    "chlorophyll": "Chlorophyll",
    "water_speed": "Water Speed (cm/s)",
    "water_direction": "Water Direction (degrees)",
}

# Cross-validated anomaly windows (confirmed 4 independent ways -- see README)
EVENT_1 = (pd.Timestamp("2024-05-17"), pd.Timestamp("2024-05-23"))
EVENT_2 = (pd.Timestamp("2024-04-08"), pd.Timestamp("2024-04-11"))


@st.cache_data(show_spinner="Loading dataset...")
def load_data() -> pd.DataFrame:
    """Load the cleaned dataset, regenerating it from raw data if missing."""
    if not PROCESSED_PATH.exists():
        df_raw = cleaning.load_raw_data(RAW_PATH, download_url=DATA_URL)
        df = cleaning.rename_columns(df_raw) if hasattr(cleaning, "rename_columns") else df_raw
        df = cleaning.convert_timestamp(df)
        if hasattr(cleaning, "add_time_features"):
            df = cleaning.add_time_features(df)
        PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(PROCESSED_PATH, index=False)

    df = pd.read_csv(PROCESSED_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["season"] = pd.Categorical(df["season"], categories=SEASON_ORDER, ordered=True)
    return df


df = load_data()
available_params = [p for p in PARAM_LABELS if p in df.columns]

# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------
st.sidebar.title("\U0001F30A Filters")

selected_seasons = st.sidebar.multiselect(
    "Season", options=SEASON_ORDER, default=SEASON_ORDER
)

selected_param = st.sidebar.selectbox(
    "Parameter to explore",
    options=available_params,
    format_func=lambda p: PARAM_LABELS.get(p, p),
    index=available_params.index("turbidity") if "turbidity" in available_params else 0,
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Source:** [GitHub repo](https://github.com/davis-mironga/"
    "brisbane-river-water-quality-analysis)"
)

filtered = df[df["season"].isin(selected_seasons)] if selected_seasons else df.iloc[0:0]

# ---------------------------------------------------------------------------
# Header + key metrics
# ---------------------------------------------------------------------------
st.title("Brisbane River Water Quality Analysis")
st.caption(
    "~11 months of water-quality sensor readings from a monitoring buoy on the "
    "Brisbane River, Australia. Explore the data below, or read the full "
    "writeup on [GitHub](https://github.com/davis-mironga/"
    "brisbane-river-water-quality-analysis)."
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Readings (filtered)", f"{len(filtered):,}")
col2.metric("Total dataset", f"{len(df):,}")
if len(filtered) and selected_param in filtered.columns:
    missing_pct = filtered[selected_param].isna().mean() * 100
    col3.metric(f"Missing ({PARAM_LABELS.get(selected_param, selected_param)})", f"{missing_pct:.1f}%")
else:
    col3.metric("Missing", "n/a")
col4.metric("Monitoring period", "Aug 2023 - Jun 2024")

st.markdown("---")

# ---------------------------------------------------------------------------
# Daily trend
# ---------------------------------------------------------------------------
st.subheader(f"Daily Trend -- {PARAM_LABELS.get(selected_param, selected_param)}")

if len(filtered) and selected_param in filtered.columns:
    daily = (
        filtered.set_index("timestamp")[selected_param]
        .resample("D")
        .mean()
        .reset_index()
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["timestamp"], y=daily[selected_param],
            mode="lines", name=PARAM_LABELS.get(selected_param, selected_param),
            line=dict(color="#2E86AB", width=1.3),
        )
    )
    for start, end, label in [(*EVENT_1, "Cross-validated anomaly"), (*EVENT_2, "Smaller anomaly")]:
        fig.add_vrect(
            x0=start, x1=end, fillcolor="#D62839", opacity=0.15,
            line_width=0, annotation_text=label if selected_param == "turbidity" else None,
            annotation_position="top left",
        )
    fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Date", yaxis_title=PARAM_LABELS.get(selected_param, selected_param),
    )
    st.plotly_chart(fig, width='stretch')
    if selected_param == "turbidity":
        st.caption(
            "Shaded windows mark a turbidity event confirmed four independent ways. "
            "Both windows border real equipment outages in the sensor's own logs, so "
            "sensor biofouling/maintenance disturbance is at least as plausible a cause "
            "as a rainfall event -- see Key Findings below."
        )
else:
    st.info("No data for the current filter selection.")

# ---------------------------------------------------------------------------
# Seasonal distribution
# ---------------------------------------------------------------------------
st.subheader(f"Seasonal Distribution -- {PARAM_LABELS.get(selected_param, selected_param)}")

if len(filtered) and selected_param in filtered.columns:
    fig2 = px.box(
        filtered, x="season", y=selected_param, color="season",
        category_orders={"season": SEASON_ORDER},
        labels={selected_param: PARAM_LABELS.get(selected_param, selected_param), "season": ""},
    )
    fig2.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig2, width='stretch')
else:
    st.info("No data for the current filter selection.")

# ---------------------------------------------------------------------------
# Daily (diel) cycle
# ---------------------------------------------------------------------------
st.subheader(f"Hour-of-Day Pattern -- {PARAM_LABELS.get(selected_param, selected_param)}")

if len(filtered) and selected_param in filtered.columns:
    hourly = filtered.groupby("hour", observed=True)[selected_param].mean().reset_index()
    fig3 = px.line(
        hourly, x="hour", y=selected_param, markers=True,
        labels={selected_param: PARAM_LABELS.get(selected_param, selected_param), "hour": "Hour of day"},
    )
    fig3.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, width='stretch')
    if selected_param == "dissolved_oxygen_pct_sat":
        st.caption(
            "Lowest around dawn, peaking mid-afternoon -- consistent with a daily "
            "(diel) oxygen cycle driven by photosynthesis during daylight hours."
        )
else:
    st.info("No data for the current filter selection.")

# ---------------------------------------------------------------------------
# Correlation heatmap
# ---------------------------------------------------------------------------
st.subheader("Relationships Between Parameters")

corr_cols = [c for c in available_params if c in filtered.columns]
if len(filtered) and len(corr_cols) > 1:
    corr = filtered[corr_cols].corr()
    fig4 = px.imshow(
        corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
        labels=dict(color="Pearson r"),
        x=[PARAM_LABELS.get(c, c) for c in corr_cols],
        y=[PARAM_LABELS.get(c, c) for c in corr_cols],
    )
    fig4.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig4, width='stretch')
    st.caption(
        "Salinity and specific conductance are near-perfectly correlated because "
        "salinity is commonly derived from conductivity by the sensor itself -- "
        "an expected relationship, not an independent finding."
    )
else:
    st.info("No data for the current filter selection.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Key findings (static summary, matches the corrected project writeup)
# ---------------------------------------------------------------------------
st.subheader("Key Findings")
st.markdown(
    """
1. **Two turbidity events (8-11 April and 17-23 May 2024)**, confirmed independently four
   separate ways. Both events border equipment-outage periods in the sensor's own logs,
   which is at least as consistent with sensor biofouling or post-outage disturbance as
   with a rainfall event.
2. **Temperature and dissolved oxygen move in opposite seasonal directions**, consistent
   with the physical relationship between water temperature and gas solubility.
3. **A clear daily (diel) oxygen cycle** driven by daylight/photosynthesis, lowest at dawn,
   highest in the afternoon.
4. **Turbidity is right-skewed**, with the confirmed events standing well outside the
   typical range of readings.
5. **Salinity varies by season**, plausibly reflecting freshwater river-flow dilution
   versus tidal/saline influence.
6. **Missing data is not random** -- it clusters into periods consistent with real
   equipment outages, which is why it was investigated rather than blindly removed.

*All findings use careful, non-causal language throughout. Full methodology, SQL analysis,
and a 23-test verification suite are documented in the
[GitHub repository](https://github.com/davis-mironga/brisbane-river-water-quality-analysis).*
"""
)
