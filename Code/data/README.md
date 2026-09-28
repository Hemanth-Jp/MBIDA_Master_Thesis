# Data

Raw M5 files are **not** committed - they're ~450MB combined and redistribution
isn't covered by the Kaggle competition rules.

## Setup

1. Download from Kaggle: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
2. Place these two files here, in `data/m5/`:
   ```
   data/m5/sales_train_validation.csv
   data/m5/calendar.csv
   ```
3. Run `notebooks/01_eda.ipynb` and `notebooks/02_pipeline.ipynb`. Both cache
   parsed data to `artifacts/raw_cache/` (also gitignored) as Parquet, so the
   CSVs are only read once.

`notebooks/02_pipeline.ipynb` exports the small, aggregated files the
Streamlit app depends on into `artifacts/dashboard_data/` - those **are**
committed, since the deployed app has no way to regenerate them itself.
