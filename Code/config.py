"""
Shared configuration for the M5 hierarchical forecasting project.

Imported by BOTH `notebooks/02_pipeline.ipynb` (which produces the dashboard
parquet files) and `app/streamlit_app.py` (which reads them). Keeping these
constants in one file means the two can never silently drift apart  e.g. the
reconciler column-name suffixes below must match EXACTLY what
`hierarchicalforecast` produces, and previously that string was typed out
separately in the app.

All paths are resolved relative to this file's own location, so both the
notebooks and the app work correctly regardless of the working directory
they're launched from (this matters especially for Streamlit Community
Cloud, which always sets the working directory to the repo root).
"""

from pathlib import Path

# ------------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------------
CODE_DIR = Path(__file__).resolve().parent

DATA_DIR = CODE_DIR / "data" / "m5"                        # raw Kaggle CSVs (gitignored)
RAW_CACHE_DIR = CODE_DIR / "artifacts" / "raw_cache"        # parsed-CSV parquet cache (gitignored)
DASHBOARD_DATA_DIR = CODE_DIR / "artifacts" / "dashboard_data"  # committed - what the app reads

for _d in (RAW_CACHE_DIR, DASHBOARD_DATA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------
# Column names
# ------------------------------------------------------------------------
COL_STATE = "state_id"
COL_STORE = "store_id"
COL_CAT = "cat_id"
COL_DEPT = "dept_id"
COL_ITEM = "item_id"
COL_TOTAL = "total_id"

DATE_COL = "date"
TARGET_COL = "sales"
CAT_LABEL_COL = "_cat"          # holds "train" / "test" / "live"
ID_COL = "unique_id"            # hierarchicalforecast's series identifier

HIERARCHY_COLS = [COL_TOTAL, COL_STATE, COL_STORE, COL_CAT, COL_DEPT, COL_ITEM]
ROOT_LABEL = "Total"            # the constant value written into COL_TOTAL
LEVEL_SEP = "/"                 # hierarchicalforecast's default unique_id separator

# `spec` for hierarchicalforecast's aggregate(): each inner list is one level,
# top-down, always including every column of the levels above it.
SPEC = [HIERARCHY_COLS[: i + 1] for i in range(len(HIERARCHY_COLS))]

# Carries the train/test/live label through aggregation. "min" is a safe
# no-op here since the label only depends on date, not on item/store.
EXOG_VARS = {CAT_LABEL_COL: "min"}

# ------------------------------------------------------------------------
# Time windows
# ------------------------------------------------------------------------
TRAIN_TEST_SPLIT_DATE = "2015-01-01"   # train ends, test begins
FORECAST_START_DATE = "2016-01-01"     # test ends, live begins
FORECAST_END_DATE = "2016-07-01"       # live ends (no real data past Apr 2016)

# ------------------------------------------------------------------------
# Modeling
# ------------------------------------------------------------------------
SEASON_LENGTH = 12                             # monthly data -> yearly seasonality
PERCENTILES = [5, 10, 20, 50, 80, 100]         # cumulative share of TRAINING volume

# ------------------------------------------------------------------------
# Reconciliation methods
#
# Label -> exact column suffix produced by hierarchicalforecast after
# reconcile(). If you change a reconciler's parameters in the pipeline
# notebook, update the matching suffix here too - this is the ONE place
# both sides read from, so there's only one string to keep in sync.
# ------------------------------------------------------------------------
RECONCILERS = {
    "Bottom-Up": "BottomUpSparse",
    "MinTrace (wls_struct)": "MinTraceSparse_method-wls_struct_nonnegative-True",
    "Top-Down": "TopDownSparse_method-proportion_averages",
}

BASE_MODELS = ["histavg", "ets", "theta"]
