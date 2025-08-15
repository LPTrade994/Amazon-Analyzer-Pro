# loaders.py
# --------------------------------------------
# Loader file e parsing basilare con default sconto=21%
# (La logica di calcolo resta invariata; qui solo utilità.)
# --------------------------------------------
from __future__ import annotations
import pandas as pd
import numpy as np
from io import BytesIO

def parse_float(x, default=None):
    try:
        if pd.isna(x): return default
        s = str(x).strip().replace("%","").replace(",","." )
        return float(s)
    except Exception:
        return default

def parse_int(x, default=None):
    try:
        if pd.isna(x): return default
        return int(float(str(x).strip()))
    except Exception:
        return default

def parse_weight(x):
    try:
        if pd.isna(x): return 0
        s = str(x).lower().strip().replace(",", ".")
        if s.endswith("kg"):
            return float(s.replace("kg",""))*1000
        if s.endswith("g"):
            return float(s.replace("g",""))
        return float(s)
    except Exception:
        return 0

def load_data(file) -> pd.DataFrame:
    name = getattr(file, "name", "").lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        df = pd.read_excel(file)
    elif name.endswith(".csv"):
        df = pd.read_csv(file, sep=None, engine="python")
    else:
        # tenta auto
        try:
            df = pd.read_excel(file)
        except Exception:
            file.seek(0)
            df = pd.read_csv(file, sep=None, engine="python")
    return df

def ensure_columns(df: pd.DataFrame, cols: list[str]):
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df

def default_discount_map(countries: list[str] | None = None) -> dict:
    # Default richiesto: 21% su tutti
    dm = {"discount_default_all": 0.21}
    if countries:
        for c in countries:
            dm[c] = 0.21
    return dm
