# Code

Implementation for the hierarchical forecasting evaluation described in the
thesis. See `../report/` for the write-up.

## Structure

```
Code/
├── config.py                      Single source of truth: column names,
│                                   hierarchy structure, reconciler mapping,
│                                   paths. Imported by the pipeline notebook
│                                   AND the Streamlit app - keeps the two
│                                   from silently drifting apart.
├── requirements-pipeline.txt       Full stack needed to run the notebooks.
│
├── notebooks/
│   ├── 01_eda.ipynb                EDA on the RAW data. Every cleanup
│   │                                decision in the pipeline notebook is
│   │                                justified here with real numbers/charts.
│   └── 02_pipeline.ipynb           Builds the hierarchy, fits base models,
│                                   reconciles, evaluates, and exports the
│                                   parquet files the app reads.
│
├── artifacts/
│   ├── raw_cache/                  Gitignored. Parsed-CSV parquet cache -
│   │                                fully regenerable from data/m5/.
│   └── dashboard_data/             Committed. The 4 small parquet files
│                                   the Streamlit app depends on.
│
├── app/
│   ├── streamlit_app.py            Reads only from artifacts/dashboard_data/
│   │                                - never re-runs the pipeline itself.
│   └── requirements.txt            Minimal deps - what Streamlit Community
│                                   Cloud actually installs.
│
└── data/
    ├── README.md                   Kaggle download instructions.
    └── m5/                         Gitignored. Raw CSVs live here locally.
```

## Data flow

```
Kaggle CSVs (data/m5/)
       │
       ▼
01_eda.ipynb  ───────────────►  justifies every decision below
       │
       ▼
02_pipeline.ipynb   (imports config.py)
   • aggregate daily → monthly
   • drop partial first month
   • fix item universe (training data only)
   • build hierarchy (Total → State → Store → Category → Department → Item)
   • fit HistoricAverage / ETS / Theta
   • reconcile with Bottom-Up / MinTrace / Top-Down
   • evaluate sMAPE by level and by volume segment
       │
       ▼
artifacts/dashboard_data/*.parquet  ──►  app/streamlit_app.py (imports config.py)
                                              │
                                              ▼
                                        live dashboard
```

## Running locally

**Dashboard only** (uses the parquet files already in `artifacts/dashboard_data/`):

```bash
cd Code
pip install -r app/requirements.txt
streamlit run app/streamlit_app.py
```

**Full pipeline** (re-generates `artifacts/dashboard_data/`, requires the raw M5 CSVs):

```bash
cd Code
pip install -r requirements-pipeline.txt
# download data - see data/README.md
jupyter lab notebooks/01_eda.ipynb
jupyter lab notebooks/02_pipeline.ipynb
```

## Deploying to Streamlit Community Cloud

1. Push the whole thesis repo to GitHub.
2. On share.streamlit.io, set the main file path to `Code/app/streamlit_app.py`.
3. Cloud finds `Code/app/requirements.txt` automatically (it searches from
   the entrypoint's folder up to the repo root) and `.streamlit/config.toml`
   at the repo root.
4. Only `Code/artifacts/dashboard_data/*.parquet` needs to be present in the
   repo for the app to work - raw data and the pipeline stack are not needed
   at deploy time.
