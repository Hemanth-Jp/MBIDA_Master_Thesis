"""
M5 Hierarchical Forecast Explorer (Streamlit)
===============================================

    Total -> State -> Store -> Category -> Department -> Item

Cascading dropdowns (st.selectbox is searchable out of the box - just
click and start typing). Leave any level on "(All)" and the app
resolves that to the correct hierarchy node's `unique_id`
(e.g. "Total", "Total/CA", "Total/CA/CA_1", ...) and plots whatever
aggregate (or bottom-level) series that represents.

The chart shows:
  - actuals (train + test, shaded backgrounds; "live" is a forecast-only
    window with no real ground truth, so it's excluded from the actual line)
  - the base forecast (histavg / ets / theta) you pick
  - the reconciled forecast(s) you pick (BottomUp / MinTrace / TopDown)

--------------------------------------------------------------------
DATA

This app reads from Code/artifacts/dashboard_data/ - four parquet files
produced by notebooks/02_pipeline.ipynb. It never re-runs the pipeline
itself (Streamlit Community Cloud only ever executes this file).

Run locally:
    pip install -r requirements.txt
    streamlit run app/streamlit_app.py
--------------------------------------------------------------------
"""

import sys
from pathlib import Path

# Make Code/config.py importable regardless of the working directory this
# app is launched from (matters especially on Streamlit Community Cloud,
# which always sets the cwd to the repo root, not to app/).
sys.path.append(str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_theme import st_theme

ALL_LABEL = "(All)"

st.set_page_config(page_title="M5 Hierarchy Explorer", layout="wide")

# Reads Streamlit's actual active theme (light/dark, including "Use system
# setting") straight from the browser - no manual toggle needed.
_theme = st_theme()
if _theme is not None:
    st.session_state["_chart_base_theme"] = _theme.get("base", "light")
dark = st.session_state.get("_chart_base_theme", "light") == "dark"


# ==============================================================================
# LOAD DATA (cached so switching dropdowns doesn't re-read parquet each time)
# ==============================================================================
@st.cache_data
def load_data():
    hierarchy_df = pd.read_parquet(config.DASHBOARD_DATA_DIR / "hierarchy.parquet")
    actuals_df = pd.read_parquet(config.DASHBOARD_DATA_DIR / "actuals.parquet")
    pred_df = pd.read_parquet(config.DASHBOARD_DATA_DIR / "pred_with_gt.parquet")
    rec_df = pd.read_parquet(config.DASHBOARD_DATA_DIR / "rec_with_gt.parquet")

    for df_ in (actuals_df, pred_df, rec_df):
        df_[config.DATE_COL] = pd.to_datetime(df_[config.DATE_COL])

    return hierarchy_df, actuals_df, pred_df, rec_df


try:
    hierarchy_df, actuals_df, pred_df, rec_df = load_data()
except FileNotFoundError as e:
    st.error(
        f"Couldn't find one of the required parquet files in "
        f"`{config.DASHBOARD_DATA_DIR}`.\n\n{e}\n\n"
        "Run notebooks/02_pipeline.ipynb first - its final section writes "
        "hierarchy.parquet, actuals.parquet, pred_with_gt.parquet, and "
        "rec_with_gt.parquet into that folder."
    )
    st.stop()

rec_cols_available = set(rec_df.columns)


def reconciled_col(base_model: str, reconciler_suffix: str) -> str | None:
    candidate = f"{base_model}/{reconciler_suffix}"
    return candidate if candidate in rec_cols_available else None


# ==============================================================================
# HELPERS: cascading dropdown option builders + unique_id resolution
# ==============================================================================
def options_with_all(values):
    values = sorted(v for v in values if pd.notna(v))
    return [ALL_LABEL] + list(values)


def unique_id_for_selection(state, store, cat, dept, item) -> str:
    """
    Build the hierarchy node's unique_id from the (possibly partial)
    selection. Every id starts with the "Total" root. Stops at the
    first level left on "(All)" - deeper dropdowns are ignored,
    matching how the pipeline's `SPEC` (config.py) builds aggregate nodes:
        [Total]
        [Total, state]
        [Total, state, store]
        [Total, state, store, cat]
        [Total, state, store, cat, dept]
        [Total, state, store, cat, dept, item]

    Leaving every dropdown on "(All)" resolves to "Total" itself
    (the grand total).
    """
    parts = [config.ROOT_LABEL]
    for val in (state, store, cat, dept, item):
        if val in (None, ALL_LABEL):
            break
        parts.append(val)
    return config.LEVEL_SEP.join(parts)


# ==============================================================================
# SIDEBAR - cascading dropdowns + model / reconciler controls
# ==============================================================================
st.title("M5 Hierarchical Forecast Explorer")
st.caption(
    "Drill down Total \u2192 State \u2192 Store \u2192 Category \u2192 Department \u2192 Item. "
    "Leave a level on \u201c(All)\u201d to view that aggregate node instead of a "
    "single item. Click a dropdown and type to search."
)

with st.sidebar:
    st.header("Hierarchy")

    state = st.selectbox("State", options_with_all(hierarchy_df[config.COL_STATE].unique()))

    if state == ALL_LABEL:
        store_opts = [ALL_LABEL]
    else:
        subset = hierarchy_df[hierarchy_df[config.COL_STATE] == state]
        store_opts = options_with_all(subset[config.COL_STORE].unique())
    store = st.selectbox("Store", store_opts)

    if ALL_LABEL in (state, store):
        cat_opts = [ALL_LABEL]
    else:
        subset = hierarchy_df[
            (hierarchy_df[config.COL_STATE] == state) & (hierarchy_df[config.COL_STORE] == store)
        ]
        cat_opts = options_with_all(subset[config.COL_CAT].unique())
    cat = st.selectbox("Category", cat_opts)

    if ALL_LABEL in (state, store, cat):
        dept_opts = [ALL_LABEL]
    else:
        subset = hierarchy_df[
            (hierarchy_df[config.COL_STATE] == state)
            & (hierarchy_df[config.COL_STORE] == store)
            & (hierarchy_df[config.COL_CAT] == cat)
        ]
        dept_opts = options_with_all(subset[config.COL_DEPT].unique())
    dept = st.selectbox("Department", dept_opts)

    if ALL_LABEL in (state, store, cat, dept):
        item_opts = [ALL_LABEL]
    else:
        subset = hierarchy_df[
            (hierarchy_df[config.COL_STATE] == state)
            & (hierarchy_df[config.COL_STORE] == store)
            & (hierarchy_df[config.COL_CAT] == cat)
            & (hierarchy_df[config.COL_DEPT] == dept)
        ]
        item_opts = options_with_all(subset[config.COL_ITEM].unique())
    item = st.selectbox("Item", item_opts)

    st.header("Forecast")
    base_model = st.radio("Base model", config.BASE_MODELS, horizontal=True)
    chosen_reconcilers = st.multiselect(
        "Reconciliation method(s)", list(config.RECONCILERS.keys()), default=["MinTrace (wls_struct)"]
    )


# ==============================================================================
# BUILD THE CHART
# ==============================================================================
uid = unique_id_for_selection(state, store, cat, dept, item)
level_label = f"Selected node: **{uid}**  (level = {uid.count(config.LEVEL_SEP) + 1})"

# --- full actual history, but only through "test" -- the "live" window has
# no real ground truth, so plotting it as if it were observed sales is
# misleading. Cut the line there. ---
actual_full = actuals_df[actuals_df[config.ID_COL] == uid].sort_values(config.DATE_COL)
if actual_full.empty:
    st.warning(f"No data found for '{uid}'.")
    st.stop()

actual = actual_full[actual_full[config.CAT_LABEL_COL] != "live"]

# --- colors that stay readable in both chart themes ---
if dark:
    actual_color = "#F2F2F2"
    grid_color = "rgba(255,255,255,0.15)"
    font_color = "#E6E6E6"
    annotation_color = "#CFCFCF"
    train_fill = "rgba(255,255,255,0.06)"
else:
    actual_color = "black"
    grid_color = "rgba(0,0,0,0.12)"
    font_color = "#262730"
    annotation_color = "#666666"
    train_fill = "rgba(0,0,0,0.04)"

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=actual[config.DATE_COL], y=actual[config.TARGET_COL], mode="lines+markers",
        name="Actual", line=dict(color=actual_color, width=2), marker=dict(size=6),
    )
)

# --- base forecast (pred_df already only contains the horizon) ---
fc = pred_df[pred_df[config.ID_COL] == uid].sort_values(config.DATE_COL)
fig.add_trace(
    go.Scatter(
        x=fc[config.DATE_COL], y=fc[base_model], mode="lines+markers",
        name=f"Base: {base_model}", line=dict(dash="dot", width=2), marker=dict(size=6),
    )
)

# --- reconciled forecast(s) (rec_df already only contains the horizon) ---
rec_sub = rec_df[rec_df[config.ID_COL] == uid].sort_values(config.DATE_COL)
missing = []
for label_name in chosen_reconcilers:
    col = reconciled_col(base_model, config.RECONCILERS[label_name])
    if col is None:
        missing.append(label_name)
        continue
    fig.add_trace(
        go.Scatter(
            x=rec_sub[config.DATE_COL], y=rec_sub[col], mode="lines+markers",
            name=f"Reconciled: {label_name}", line=dict(width=2), marker=dict(size=6),
        )
    )

# --- shade + label train / test / live regions ---
phase_style = {
    "train": dict(fill=train_fill, text="Train"),
    "test": dict(fill="rgba(255,165,0,0.12)", text="Test"),
    "live": dict(fill="rgba(0,178,89,0.12)", text="Live"),
}
for phase, style in phase_style.items():
    phase_dates = actual_full.loc[actual_full[config.CAT_LABEL_COL] == phase, config.DATE_COL]
    if phase_dates.empty:
        continue
    fig.add_vrect(
        x0=phase_dates.min(), x1=phase_dates.max(),
        fillcolor=style["fill"], line_width=0,
        annotation_text=style["text"], annotation_position="top left",
        annotation_font_size=10, annotation_font_color=annotation_color,
    )

fig.update_layout(
    xaxis_title="Date",
    yaxis_title="Sales",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=60, l=40, r=20, b=40),
    height=560,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=font_color),
    xaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color),
    yaxis=dict(gridcolor=grid_color, zerolinecolor=grid_color),
)

if missing:
    level_label += (
        f"   |   No column found for: {', '.join(missing)} "
        "(check config.RECONCILERS suffixes vs. rec_with_gt.columns)"
    )

st.markdown(level_label)
st.plotly_chart(fig, width="stretch")
