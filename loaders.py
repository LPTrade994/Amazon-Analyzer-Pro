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
        if pd.isna(x):
            return default
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


def _to_bool_series(s: pd.Series) -> pd.Series:
    """Convert a series to boolean where possible.

    Recognises common true/false strings ("yes", "no", "true", "false", "1", "0")
    and empty strings which become ``NaN``.  Any unrecognised values are
    interpreted using Python's truthiness rules.  ``NaN`` values remain ``NaN``.
    """

    mapping = {
        "yes": True,
        "y": True,
        "true": True,
        "t": True,
        "1": True,
        "no": False,
        "n": False,
        "false": False,
        "f": False,
        "0": False,
    }

    def _convert(x):
        if pd.isna(x):
            return np.nan
        if isinstance(x, str):
            val = x.strip().lower()
            if val == "":
                return np.nan
            if val in mapping:
                return mapping[val]
        try:
            return bool(x)
        except Exception:
            return np.nan

    return s.map(_convert)

def load_data(file, schema: dict[str, str] | None = None) -> pd.DataFrame:
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
            try:
                file.seek(0)
            except Exception:
                pass
            df = pd.read_csv(file, sep=None, engine="python")

    if schema:
        for col, dtype in schema.items():
            if col not in df.columns:
                continue
            dt = dtype.lower()
            if dt in {"float", "float64", "double", "number"}:
                df[col] = df[col].map(lambda x: parse_float(x, default=np.nan)).astype(float)
            elif dt in {"int", "int64", "integer"}:
                df[col] = df[col].map(lambda x: parse_int(x, default=np.nan)).astype("Int64")
            elif dt in {"bool", "boolean"}:
                df[col] = _to_bool_series(df[col])
    return df

def ensure_columns(df: pd.DataFrame, cols: list[str]):
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df


def load_keepa(file) -> pd.DataFrame:
    """Load Keepa exports dropping unnamed columns."""
    df = load_data(file)
    df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
    return df

def default_discount_map(countries: list[str] | None = None) -> dict:
    # Default richiesto: 21% su tutti
    dm = {"discount_default_all": 0.21}
    if countries:
        for c in countries:
            dm[c] = 0.21
    return dm
