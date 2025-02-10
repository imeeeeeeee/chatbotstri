import pandas as pd
import os

def load_parts(path, frac, chunksize=100000):
    sampled_data = pd.DataFrame()

    for chunk in pd.read_stata(path, chunksize=chunksize):
        # Append a fraction of each chunk to the sample
        sampled_data = pd.concat([sampled_data, chunk.sample(frac=frac, random_state=42)], ignore_index=True)
    return sampled_data


def load_data(path, sample_frac=0.15):
    """Load dataset with smart format detection and optimized loading"""
    try:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found at {path}")
            
        ext = os.path.splitext(path)[1].lower()
        
        if ext == '.dta':
            df = load_parts(path, sample_frac)
        elif ext == '.parquet':
            df = pd.read_parquet(path)
        elif ext == '.csv':
            df = pd.read_csv(path, low_memory=False)
        elif ext in ('.xls', '.xlsx'):
            df = pd.read_excel(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        
        cols_to_drop = ["orderid", "MeasureID", "Country_code", "Sector_id", "Sector_code", "Subsector_code", "Policy_area_code", "STRIcode"] 
        df = df.drop(cols_to_drop, axis=1)
        return _clean_dataframe(df)
        
    except Exception as e:
        raise RuntimeError(f"Data loading error: {str(e)}")

import pandas as pd
import numpy as np

def _clean_dataframe(df):
    """Fix data type issues to ensure Arrow compatibility"""

    for col in df.columns:
        # Handle string columns properly
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip().replace({'nan': None, 'None': None, '': None})

            # Convert numeric-like strings to proper numbers
            if df[col].str.match(r"^\d+(\.\d+)?$", na=True).all():
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Ensure integer columns are stored as Int64 for Arrow compatibility
        elif pd.api.types.is_integer_dtype(df[col]):
            df[col] = df[col].astype("Int64")  # Nullable integer type

        # Ensure float columns remain float64
        elif pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].astype("float64")

        # Convert categorical columns (avoid Arrow issues with mixed types)
        elif df[col].nunique() < 50 and df[col].dtype == 'object':
            df[col] = df[col].astype('category')

        # Convert datetime columns properly
        elif "date" in col.lower() or pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Ensure the "Type" column exists before setting its type
    if "Type" in df.columns:
        df["Type"] = df["Type"].astype("string")

    # Convert dtypes to Arrow-compatible types
    return df.convert_dtypes()



def _fix_string_column(series):
    """Ensure consistent string formatting to avoid Arrow errors"""
    return (
        series.astype(str)
        .str.strip()
        .replace({'nan': None, 'None': None, '': None})  # Handle missing values
    )
