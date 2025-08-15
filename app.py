# app.py
# ---------------------------------------------------------
# Amazon Market Analyzer — Opportunity 2.0
# UI dark, vista Essenziale, profitti Amazon & HDG, sconto default 21%.
# ---------------------------------------------------------

import streamlit as st

st.set_page_config(
    page_title="Amazon Market Analyzer — Opportunity 2.0",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import numpy as np
import json
from loaders import load_data, default_discount_map
from score import (
    SHIPPING_COSTS,
    VAT_RATES,
    normalize_locale,
    calculate_shipping_cost,
    calc_final_purchase_price,
    compute_profits,
    compute_opportunity_score,
    compute_price_regime,
    recompute_row_profit,
    compute_amazon_risk,
    compute_quality_metrics,
    compute_window_signal,
    parse_float,
    parse_int,
    DEFAULT_PENALTY_MAP,
    DEFAULT_PENALTY_THRESHOLD,
    DEFAULT_PENALTY_SUGGESTED,
)
from utils import load_preset, save_preset

# Presets for quick score configurations
PRESETS = {
    "Flip veloce": {
        "weights_pillars": {
            "wP": 30,
            "wK": 20,
            "wN": 20,
            "wX": 10,
            "wM": 8,
            "wL": 7,
            "wR": 5,
        },
        "weights_core": {
            "Epsilon": 2.0,
            "Theta": 1.0,
            "Alpha": 1.5,
            "Beta": 1.5,
            "Delta": 1.0,
            "Zeta": 1.0,
            "Gamma": 3.0,
        },
        "filters": {
            "min_profit_eur": 3.0,
            "min_profit_pct": 10.0,
            "max_amz_share": 50.0,
            "max_offer_cnt": 40,
            "max_rank": 350000,
        },
    },
    "Margine alto": {
        "weights_pillars": {
            "wP": 60,
            "wK": 10,
            "wN": 10,
            "wX": 5,
            "wM": 5,
            "wL": 5,
            "wR": 5,
        },
        "weights_core": {
            "Epsilon": 4.0,
            "Theta": 3.0,
            "Alpha": 1.0,
            "Beta": 1.0,
            "Delta": 1.0,
            "Zeta": 1.0,
            "Gamma": 1.0,
        },
        "filters": {
            "min_profit_eur": 10.0,
            "min_profit_pct": 30.0,
            "max_amz_share": 40.0,
            "max_offer_cnt": 30,
            "max_rank": 200000,
        },
    },
    "Volume/Rotazione": {
        "weights_pillars": {
            "wP": 35,
            "wK": 15,
            "wN": 20,
            "wX": 10,
            "wM": 8,
            "wL": 7,
            "wR": 5,
        },
        "weights_core": {
            "Epsilon": 1.0,
            "Theta": 0.5,
            "Alpha": 1.5,
            "Beta": 2.0,
            "Delta": 1.0,
            "Zeta": 1.0,
            "Gamma": 4.0,
        },
        "filters": {
            "min_profit_eur": 2.0,
            "min_profit_pct": 8.0,
            "max_amz_share": 60.0,
            "max_offer_cnt": 50,
            "max_rank": 400000,
        },
    },
}

# Default values used for widgets and preset handling
DEFAULT_WEIGHTS_PILLARS = {
    "wP": 40,
    "wK": 15,
    "wN": 15,
    "wX": 10,
    "wM": 8,
    "wL": 7,
    "wR": 5,
}

DEFAULT_WEIGHTS_CORE = {
    "Epsilon": 3.0,
    "Theta": 1.5,
    "Alpha": 1.0,
    "Beta": 1.0,
    "Delta": 1.0,
    "Zeta": 1.0,
    "Gamma": 2.0,
}

DEFAULT_FILTERS = {
    "min_profit_eur": 5.0,
    "min_profit_pct": 15.0,
    "max_amz_share": 50.0,
    "max_offer_cnt": 40,
    "max_rank": 350000,
}

# -----------------------
# Helpers di formattazione/HTML
# -----------------------


def _safe(x):
    """Ritorna stringa formattata o '—' se NaN/None. Numeri con 2 decimali e virgola italiana."""
    try:
        if x is None:
            return "—"
        if isinstance(x, (int, np.integer)):
            return f"{int(x)}"
        if isinstance(x, (float, np.floating)):
            if np.isnan(x):
                return "—"
            return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        # tenta conversione numerica soft
        xv = parse_float(x, default=np.nan)
        if pd.notna(xv):
            return _safe(float(xv))
        return str(x)
    except Exception:
        return "—"


def _badge(value, suffix="€", cls_prefix="badge-profit", display_value=None):
    """Badge XL colorato con colori customizzabili.

    Parameters
    ----------
    value : float | int
        Valore usato per determinare il colore (positivo=verde, negativo=rosso).
    suffix : str, default "€"
        Suffisso mostrato accanto al valore.
    cls_prefix : str, default "badge-profit"
        Prefisso delle classi CSS da utilizzare ("-pos", "-neg", "-neu").
    display_value : float | int | None
        Valore da visualizzare; se ``None`` viene usato ``value``.
    """

    if display_value is None:
        display_value = value

    if value is None or (isinstance(value, float) and np.isnan(value)):
        cls = f"{cls_prefix}-neu"
        txt = "—"
    else:
        try:
            v = float(value)
            disp_val = float(display_value) if display_value is not None else v
            if suffix == "%":
                disp = f"{round(disp_val, 1)}{suffix}"
            else:
                disp = f"{round(disp_val, 2)}{suffix}"
            if v > 0.01:
                cls = f"{cls_prefix}-pos"
            elif v < -0.01:
                cls = f"{cls_prefix}-neg"
            else:
                cls = f"{cls_prefix}-neu"
            txt = disp
        except Exception:
            cls = f"{cls_prefix}-neu"
            txt = "—"
    return f'<span class="badge badge-xl {cls}">{txt}</span>'


def _z_badge(z):
    """Badge colorato per z-score: verde ≤ -1, rosso ≥ 1, grigio altrimenti."""
    try:
        v = float(z)
    except Exception:
        return f'<span class="badge badge-xl badge-profit-neu">—</span>'
    if np.isnan(v):
        return f'<span class="badge badge-xl badge-profit-neu">—</span>'
    cls = "badge-profit-neu"
    if v <= -1:
        cls = "badge-profit-pos"
    elif v >= 1:
        cls = "badge-profit-neg"
    txt = f"{v:.2f}"
    return f'<span class="badge badge-xl {cls}">{txt}</span>'


def _flag_badge(val, txt_ok="No MAP", txt_bad="MAP"):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        cls = "badge-flag-neu"
        txt = "N/A"
    else:
        try:
            flag = bool(val)
        except Exception:
            flag = False
        if flag:
            cls = "badge-flag-neg"
            txt = txt_bad
        else:
            cls = "badge-flag-pos"
            txt = txt_ok
    return f'<span class="badge badge-xl {cls}">{txt}</span>'


def _risk_badge(value, threshold, suffix="%"):
    """Badge per rischi: verde se valore < soglia, rosso se >= soglia."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        cls = "badge-profit-neu"
        txt = "—"
    else:
        try:
            v = float(value)
            disp = f"{round(v, 1)}{suffix}" if suffix else f"{round(v, 1)}"
            cls = "badge-profit-pos" if v < threshold else "badge-profit-neg"
            txt = disp
        except Exception:
            cls = "badge-profit-neu"
            txt = "—"
    return f'<span class="badge badge-xl {cls}">{txt}</span>'


def _window_badge(signal: str | None) -> str:
    """Badge per il segnale di finestra favorevole."""

    mapping = {
        "LIGHTNING": ("⚡", "badge-green"),
        "DELAY": ("⏳", "badge-red"),
        "SELL": ("OOS", "badge-green"),
    }
    if signal is None:
        txt, cls = "—", "badge-gray"
    else:
        txt, cls = mapping.get(str(signal).upper(), ("—", "badge-gray"))
    return f'<span class="badge badge-xl {cls}">{txt}</span>'


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """Return a list of required columns that are absent from *df*."""
    return [c for c in required if c not in df.columns]


def _validate_required_columns(
    df_orig: pd.DataFrame, df_tgt: pd.DataFrame, required: list[str]
) -> None:
    """Check both datasets for missing columns and report them together.

    Parameters
    ----------
    df_orig, df_tgt : pd.DataFrame
        DataFrames representing the origin and target datasets.
    required : list[str]
        Columns that must be present in both datasets.
    """
    errors: list[str] = []
    miss_orig = _missing_columns(df_orig, required)
    if miss_orig:
        errors.append(f"Origin dataset: Missing columns: {', '.join(miss_orig)}")
    miss_tgt = _missing_columns(df_tgt, required)
    if miss_tgt:
        errors.append(f"Target dataset: Missing columns: {', '.join(miss_tgt)}")
    if errors:
        for err in errors:
            st.error(err)
        st.stop()


# -----------------------
# THEME (dark minimal)
# -----------------------
CUSTOM_CSS = """
<style>
:root {
  --bg: #0B0B0C;
  --card: #141416;
  --text: #FFFFFF;
  --muted: #A0A0A0;
  --accent: #E50914;
  --good: #00c46a;
  --warn: #ffcc00;
  --bad: #ff4d4d;
}
.stApp { background: var(--bg) !important; }
[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 1.2rem; }
div[data-baseweb="select"] * { background: var(--card) !important; color: var(--text) !important; }
.stDataFrame { border: 1px solid #1f1f22; border-radius: 14px; }
.badge {
  display:inline-block; padding:.25rem .6rem; border-radius:10px; font-weight:600;
}
.badge-profit-pos { background: rgba(0,196,106,.12); color: var(--good); }
.badge-profit-neg { background: rgba(229,9,20,.12); color: var(--bad); }
.badge-profit-neu { background: rgba(255,255,255,.1); color: var(--text); }
.badge-quality-pos { background: rgba(0,196,106,.12); color: var(--good); }
.badge-quality-neg { background: rgba(229,9,20,.12); color: var(--bad); }
.badge-quality-neu { background: rgba(255,255,255,.1); color: var(--text); }
.badge-flag-pos { background: rgba(0,196,106,.12); color: var(--good); }
.badge-flag-neg { background: rgba(229,9,20,.12); color: var(--bad); }
.badge-flag-neu { background: rgba(255,255,255,.1); color: var(--text); }
.badge-green { background: rgba(0,196,106,.12); color: var(--good); }
.badge-gray { background: rgba(255,255,255,.1); color: var(--muted); }
.badge-red { background: rgba(229,9,20,.12); color: var(--bad); }
.badge-xl { font-size: 0.95rem; }
.streamlit-expanderHeader, .streamlit-expanderContent { background: var(--card); color: var(--text); }
.card { background: var(--card); padding: 14px 16px; border-radius: 16px; border:1px solid #1f1f22; }
h1,h2,h3,h4 { color: var(--text); }
hr { border-color:#222227; }
label, p, span, div { color: var(--text); }
th { position: sticky; top: 0; background: var(--card); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# -----------------------
# SIDEBAR - Upload & Settings
# -----------------------
st.sidebar.title("⚙️ Impostazioni")

st.sidebar.subheader("Carica file")
orig_file = st.sidebar.file_uploader("Lista di Origine", type=["xlsx", "xls", "csv"])
tgt_file = st.sidebar.file_uploader("Lista di Confronto", type=["xlsx", "xls", "csv"])

st.sidebar.subheader("Prezzi da usare")
price_cols_hint = [
    "Buy Box 🚚: Current",
    "Amazon: Current",
    "New: Current",
    "New, 3rd Party FBM 🚚: Current",
    "New, 3rd Party FBA: Current",
]

origin_price_col = st.sidebar.selectbox(
    "Prezzo Origine", options=price_cols_hint, index=0
)
target_price_col = st.sidebar.selectbox(
    "Prezzo Target (Amazon)", options=price_cols_hint, index=0
)

st.sidebar.subheader("Parametri vendita")
use_fba = st.sidebar.toggle("Usa FBA (considera Pick&Pack)", value=False)
site_price_override = st.sidebar.text_input(
    "Prezzo HDGaming (vuoto = usa BB IT Current)", value=""
)
site_price_override_val = parse_float(site_price_override, default=None)

st.sidebar.subheader("Sconto acquisto (default 21%)")
disc_default = (
    st.sidebar.slider(
        "Sconto default per tutti i paesi", min_value=0, max_value=60, value=21, step=1
    )
    / 100.0
)
discount_map = {"discount_default_all": disc_default}

st.sidebar.subheader("Preset")
for name, preset in PRESETS.items():
    if st.sidebar.button(name):
        st.session_state.update(preset["weights_pillars"])
        st.session_state.update(preset["weights_core"])
        st.session_state.update(preset["filters"])

# current state for saving/loading/downloading
current_weights_pillars = {
    k: st.session_state.get(k, v) for k, v in DEFAULT_WEIGHTS_PILLARS.items()
}
current_weights_core = {
    k: st.session_state.get(k, v) for k, v in DEFAULT_WEIGHTS_CORE.items()
}
current_filters = {k: st.session_state.get(k, v) for k, v in DEFAULT_FILTERS.items()}

preset_name = st.sidebar.text_input("Preset name", key="preset_name")
col_save, col_load = st.sidebar.columns(2)
if col_save.button("Save", use_container_width=True):
    save_preset(
        preset_name, current_weights_pillars, current_weights_core, current_filters
    )
if col_load.button("Load", use_container_width=True):
    data = load_preset(preset_name)
    if data:
        st.session_state.update(data.get("weights_pillars", {}))
        st.session_state.update(data.get("weights_core", {}))
        st.session_state.update(data.get("filters", {}))
        st.experimental_rerun()

preset_json = json.dumps(
    {
        "weights_pillars": current_weights_pillars,
        "weights_core": current_weights_core,
        "filters": current_filters,
    },
    indent=2,
)
st.sidebar.download_button(
    "Download current preset",
    preset_json,
    file_name=f"{preset_name or 'preset'}.json",
    mime="application/json",
)

uploaded_preset = st.sidebar.file_uploader("Upload preset", type="json")
if uploaded_preset is not None:
    try:
        data = json.load(uploaded_preset)
        st.session_state.update(data.get("weights_pillars", {}))
        st.session_state.update(data.get("weights_core", {}))
        st.session_state.update(data.get("filters", {}))
        st.experimental_rerun()
    except Exception:
        st.sidebar.error("Invalid preset file")

st.sidebar.subheader("Pesi pilastri (Opportunity 2.0)")
wP = st.sidebar.slider(
    "Profit",
    0,
    60,
    value=st.session_state.get("wP", DEFAULT_WEIGHTS_PILLARS["wP"]),
    key="wP",
)
wK = st.sidebar.slider(
    "Edge",
    0,
    40,
    value=st.session_state.get("wK", DEFAULT_WEIGHTS_PILLARS["wK"]),
    key="wK",
)
wN = st.sidebar.slider(
    "Demand",
    0,
    40,
    value=st.session_state.get("wN", DEFAULT_WEIGHTS_PILLARS["wN"]),
    key="wN",
)
wX = st.sidebar.slider(
    "Competition",
    0,
    30,
    value=st.session_state.get("wX", DEFAULT_WEIGHTS_PILLARS["wX"]),
    key="wX",
)
wM = st.sidebar.slider(
    "AmazonRisk",
    0,
    30,
    value=st.session_state.get("wM", DEFAULT_WEIGHTS_PILLARS["wM"]),
    key="wM",
)
wL = st.sidebar.slider(
    "Stability",
    0,
    30,
    value=st.session_state.get("wL", DEFAULT_WEIGHTS_PILLARS["wL"]),
    key="wL",
)
wR = st.sidebar.slider(
    "Quality",
    0,
    30,
    value=st.session_state.get("wR", DEFAULT_WEIGHTS_PILLARS["wR"]),
    key="wR",
)
weights_pillars = dict(wP=wP, wK=wK, wN=wN, wX=wX, wM=wM, wL=wL, wR=wR)

st.sidebar.subheader("Pesi storici (Core)")
Epsilon = st.sidebar.slider(
    "Margine % (ε)",
    0.0,
    5.0,
    value=st.session_state.get("Epsilon", DEFAULT_WEIGHTS_CORE["Epsilon"]),
    step=0.1,
    key="Epsilon",
)
Theta = st.sidebar.slider(
    "Margine € (θ)",
    0.0,
    5.0,
    value=st.session_state.get("Theta", DEFAULT_WEIGHTS_CORE["Theta"]),
    step=0.1,
    key="Theta",
)
Alpha = st.sidebar.slider(
    "Vendibilità Rank (α)",
    0.0,
    3.0,
    value=st.session_state.get("Alpha", DEFAULT_WEIGHTS_CORE["Alpha"]),
    step=0.1,
    key="Alpha",
)
Beta = st.sidebar.slider(
    "Domanda recente (β)",
    0.0,
    3.0,
    value=st.session_state.get("Beta", DEFAULT_WEIGHTS_CORE["Beta"]),
    step=0.1,
    key="Beta",
)
Delta = st.sidebar.slider(
    "Concorrenza (δ)",
    0.0,
    3.0,
    value=st.session_state.get("Delta", DEFAULT_WEIGHTS_CORE["Delta"]),
    step=0.1,
    key="Delta",
)
Zeta = st.sidebar.slider(
    "Trend Rank (ζ)",
    0.0,
    3.0,
    value=st.session_state.get("Zeta", DEFAULT_WEIGHTS_CORE["Zeta"]),
    step=0.1,
    key="Zeta",
)
Gamma = st.sidebar.slider(
    "Volume stimato (γ)",
    0.0,
    4.0,
    value=st.session_state.get("Gamma", DEFAULT_WEIGHTS_CORE["Gamma"]),
    step=0.1,
    key="Gamma",
)
weights_core = dict(
    Epsilon=Epsilon,
    Theta=Theta,
    Alpha=Alpha,
    Beta=Beta,
    Delta=Delta,
    Zeta=Zeta,
    Gamma=Gamma,
)

st.sidebar.subheader("Penalties")
penalty_map = st.sidebar.slider(
    "Penalty MAP",
    0.0,
    0.3,
    value=st.session_state.get("penalty_map", DEFAULT_PENALTY_MAP),
    step=0.01,
    key="penalty_map",
    help="Penalty applied when MAP restriction exists.",
)
penalty_threshold = st.sidebar.slider(
    "Penalty Threshold",
    0.0,
    0.3,
    value=st.session_state.get("penalty_threshold", DEFAULT_PENALTY_THRESHOLD),
    step=0.01,
    key="penalty_threshold",
    help="Penalty if price exceeds competitive threshold.",
)
penalty_suggested = st.sidebar.slider(
    "Penalty Suggested",
    0.0,
    0.3,
    value=st.session_state.get("penalty_suggested", DEFAULT_PENALTY_SUGGESTED),
    step=0.01,
    key="penalty_suggested",
    help="Penalty if price exceeds suggested price.",
)

st.sidebar.subheader("Filtri rapidi")
min_profit_eur = st.sidebar.number_input(
    "Min Profit Amazon €",
    value=st.session_state.get("min_profit_eur", DEFAULT_FILTERS["min_profit_eur"]),
    step=0.5,
    key="min_profit_eur",
)
min_profit_pct = st.sidebar.number_input(
    "Min Profit Amazon %",
    value=st.session_state.get("min_profit_pct", DEFAULT_FILTERS["min_profit_pct"]),
    step=1.0,
    key="min_profit_pct",
)
max_amz_share = st.sidebar.number_input(
    "Max %Amazon BuyBox (90d)",
    value=st.session_state.get("max_amz_share", DEFAULT_FILTERS["max_amz_share"]),
    step=1.0,
    key="max_amz_share",
)
exclude_amz_bb = st.sidebar.checkbox(
    "Escludi %Amazon BB sopra soglia", value=True, key="exclude_amz_bb"
)
max_offer_cnt = st.sidebar.number_input(
    "Max Offer Count",
    value=int(st.session_state.get("max_offer_cnt", DEFAULT_FILTERS["max_offer_cnt"])),
    step=1,
    key="max_offer_cnt",
)
max_rank = st.sidebar.number_input(
    "Max Sales Rank (curr)",
    value=int(st.session_state.get("max_rank", DEFAULT_FILTERS["max_rank"])),
    step=5000,
    key="max_rank",
)

# -----------------------
# MAIN
# -----------------------
st.title("🔎 Amazon Market Analyzer — Opportunity 2.0")

colA, colB, colC = st.columns([1.2, 1, 1])
with colA:
    st.markdown(
        "**Vista Essenziale** — identità + prezzi chiave + profitti Amazon/HDG. "
        "Pannelli avanzati disponibili a richiesta."
    )
with colB:
    st.metric("Sconto default", f"{int(disc_default*100)}%")
with colC:
    st.toggle("Dark Mode", value=True, key="__dark_fake__", disabled=True)

if not (orig_file and tgt_file):
    st.info("⬆️ Carica **Lista di Origine** e **Lista di Confronto** per iniziare.")
    st.stop()

# Colonne richieste
required_columns = ["ASIN", "Locale", origin_price_col, target_price_col]

# Carica e verifica colonne
df_orig = load_data(orig_file)
df_tgt = load_data(tgt_file)
_validate_required_columns(df_orig, df_tgt, required_columns)

# Left join: partiamo dall'origine (identità/Locale/peso), poi aggiungiamo target
df = pd.merge(df_orig, df_tgt, on="ASIN", how="left", suffixes=("", " (tgt)"))

# Imposta locale target (default IT)
locale_target = "IT"

# Calcola profitti (logica IVA/sconto invariata; default sconto = sidebar)
dfp = compute_profits(
    df,
    price_col_origin=origin_price_col,
    price_col_target_bb=target_price_col,
    locale_target=locale_target,
    locale_origin_col="Locale",
    use_fba=use_fba,
    site_price=site_price_override_val,
    payment_fee_site=0.05,
    default_discount_all=disc_default,
)

# Colonna modificabile manualmente con fallback al Buy Box corrente
dfp["Prezzo Sito"] = dfp["SitePriceGross"].fillna(dfp.get("Buy Box 🚚: Current"))

# Opportunity Score
dfp["OpportunityScore"] = compute_opportunity_score(
    dfp,
    weights_pillars,
    weights_core,
    penalty_map=penalty_map,
    penalty_threshold=penalty_threshold,
    penalty_suggested=penalty_suggested,
)
dfp["WindowSignal"] = compute_window_signal(dfp)

# Apply manual site price edits from previous interactions
if "dfp_editor" in st.session_state:
    edited_df = st.session_state["dfp_editor"]
    base_df = dfp.head(len(edited_df))
    base_prices = base_df["Prezzo Sito"].astype(float).fillna(-9e9)
    edited_prices = edited_df["Prezzo Sito"].astype(float).fillna(-9e9)
    changed = edited_prices != base_prices
    if changed.any():
        for idx in edited_df.index[changed]:
            new_price = edited_df.at[idx, "Prezzo Sito"]
            dfp.at[idx, "Prezzo Sito"] = new_price
            dfp.at[idx, "SitePriceGross"] = new_price
            row = dfp.loc[idx].rename(
                {origin_price_col: "Price_Base", target_price_col: "BuyBoxPrice"}
            )
            row["SitePriceGross"] = new_price
            updated = recompute_row_profit(
                row,
                use_fba=use_fba,
                site_price_col="SitePriceGross",
                payment_fee_site=0.05,
            )
            for col in [
                "ProfitAmazonEUR",
                "ProfitAmazonPct",
                "ProfitSiteEUR",
                "ProfitSitePct",
                "OpportunityScore",
                "SitePriceGross",
            ]:
                dfp.at[idx, col] = updated[col]
            dfp.at[idx, "Prezzo Sito"] = updated["SitePriceGross"]


# Filtri rapidi
def _to_pct(x):
    try:
        return float(x) * 100.0
    except Exception:
        return np.nan


df_view = dfp.copy()
df_view["ProfitAmazonPctView"] = df_view["ProfitAmazonPct"].map(_to_pct)
df_view["ProfitSitePctView"] = df_view["ProfitSitePct"].map(_to_pct)
df_view["BB_AmzShare90d"] = (
    dfp.get("Buy Box: % Amazon 90 days", pd.Series([np.nan] * len(dfp)))
    .map(lambda x: parse_float(x, default=np.nan))
    .astype(float)
)

profit_amz_eur_ok = df_view["ProfitAmazonEUR"].map(
    lambda x: parse_float(x, default=np.nan)
).fillna(-9e9) >= float(min_profit_eur)
profit_amz_pct_ok = df_view["ProfitAmazonPctView"].map(
    lambda x: parse_float(x, default=np.nan)
).fillna(-9e9) >= float(min_profit_pct)
if exclude_amz_bb:
    amz_share_ok = df_view["BB_AmzShare90d"].fillna(0.0) <= float(max_amz_share)
else:
    amz_share_ok = pd.Series(True, index=df_view.index)
offer_cnt_ok = df_view.get("Total Offer Count", pd.Series([0] * len(df_view))).map(
    lambda x: parse_int(x, default=np.nan)
).fillna(0) <= int(max_offer_cnt)
rank_ok = df_view.get("Sales Rank: Current", pd.Series([0] * len(df_view))).map(
    lambda x: parse_int(x, default=np.nan)
).fillna(0) <= int(max_rank)

mask = profit_amz_eur_ok & profit_amz_pct_ok & amz_share_ok & offer_cnt_ok & rank_ok

filter_counts = {
    f"Profit ≥ €{min_profit_eur}": int(profit_amz_eur_ok.sum()),
    f"Profit ≥ {min_profit_pct}%": int(profit_amz_pct_ok.sum()),
}
if exclude_amz_bb:
    filter_counts[f"Amz Share ≤ {max_amz_share}%"] = int(amz_share_ok.sum())
filter_counts.update(
    {
        f"Offer count ≤ {max_offer_cnt}": int(offer_cnt_ok.sum()),
        f"Rank ≤ {max_rank}": int(rank_ok.sum()),
    }
)

badges_html = " ".join(
    [
        f"<span class='badge badge-gray badge-xl'>{name} ({count})</span>"
        for name, count in filter_counts.items()
    ]
)

st.markdown(badges_html, unsafe_allow_html=True)

df_view = df_view[mask]

if st.toggle("Solo con finestra favorevole"):
    df_view = df_view[df_view["WindowSignal"].notna() & (df_view["WindowSignal"] != "")]

csv_view = df_view.to_csv(decimal=",", sep=";", index=False).encode("utf-8")
st.download_button(
    "📥 Scarica CSV filtrato",
    data=csv_view,
    file_name="dati_filtrati.csv",
    mime="text/csv",
    help="Il CSV usa la virgola come separatore decimale e il punto e virgola come delimitatore.",
)

# Vista ESSENZIALE
cols_ess = []
for c in [
    "ASIN",
    "Title",
    "Brand",
    "Locale",
    origin_price_col,
    "PurchaseNetExVAT",
    "Package: Weight (g)",
    "Item: Weight (g)",
    target_price_col,
    "ProfitAmazonEUR",
    "ProfitAmazonPctView",
    "SitePriceGross",
    "ProfitSiteEUR",
    "ProfitSitePctView",
    "Sales Rank: Current",
    "Buy Box: % Amazon 90 days",
    "Return Rate",
    "OpportunityScore",
    "WindowSignal",
]:
    if c in df_view.columns:
        cols_ess.append(c)

if len(cols_ess) == 0:
    st.error("Non sono presenti le colonne attese per la Vista Essenziale.")
    st.stop()

df_ess = df_view[cols_ess].rename(
    columns={
        origin_price_col: "Orig Price",
        target_price_col: "BB Target",
        "ProfitAmazonPctView": "Profit Amazon %",
        "ProfitSitePctView": "Profit HDG %",
        "SitePriceGross": "Prezzo HDG",
    }
)

# Ordinamento per score
if "OpportunityScore" in df_ess.columns:
    df_ess = df_ess.sort_values(by="OpportunityScore", ascending=False)

# Render tabella HTML con badge
st.markdown("### 📋 Elenco prodotti (Essenziale)")

header = [
    "ASIN",
    "Title",
    "Brand",
    "Locale",
    "Orig Price",
    "Costo ex-IVA",
    "Peso (g)",
    "BB Target",
    "Profit Amazon €",
    "Profit Amazon %",
    "Prezzo HDG",
    "Profit HDG €",
    "Profit HDG %",
    "Rank",
    "%Amazon 90d",
    "Return",
    "Score",
    "Window",
]

rows_html = []
rows_html.append(
    "<tr>"
    + "".join(
        [f"<th style='text-align:left;padding:8px 10px'>{h}</th>" for h in header]
    )
    + "</tr>"
)

for _, r in df_ess.iterrows():
    peso = r.get("Package: Weight (g)", np.nan)
    if pd.isna(peso):
        peso = r.get("Item: Weight (g)", np.nan)

    row = [
        r.get("ASIN", ""),
        r.get("Title", ""),
        r.get("Brand", ""),
        r.get("Locale", ""),
        f"{_safe(r.get('Orig Price'))}",
        f"{_safe(r.get('PurchaseNetExVAT'))}",
        f"{_safe(peso)}",
        f"{_safe(r.get('BB Target'))}",
        _badge(r.get("ProfitAmazonEUR"), "€"),
        _badge(r.get("Profit Amazon %"), "%"),
        f"{_safe(r.get('Prezzo HDG'))}",
        _badge(r.get("ProfitSiteEUR"), "€"),
        _badge(r.get("Profit HDG %"), "%"),
        f"{_safe(r.get('Sales Rank: Current'))}",
        f"{_safe(r.get('Buy Box: % Amazon 90 days'))}",
        f"{_safe(r.get('Return Rate'))}",
        f"{_safe(r.get('OpportunityScore'))}",
        _window_badge(r.get("WindowSignal")),
    ]
    rows_html.append(
        "<tr>"
        + "".join([f"<td style='padding:8px 10px'>{cell}</td>" for cell in row])
        + "</tr>"
    )

html_table = f"""
<div class="card">
  <div style="overflow:auto; max-height: 70vh;">
    <table style="width:100%;border-collapse:collapse">
      {''.join(rows_html)}
    </table>
  </div>
</div>
"""
st.markdown(html_table, unsafe_allow_html=True)

# Dettaglio per ASIN selezionato
asin_sel = st.selectbox("Dettaglio ASIN", options=df_ess["ASIN"].unique())
df_sel = dfp[dfp["ASIN"] == asin_sel]
reg = compute_price_regime(df_sel, target_price_col)
risk = compute_amazon_risk(df_sel)
quality = compute_quality_metrics(df_sel)
st.markdown("#### Price Regime")
st.write("Media 30g:", _safe(reg.get("BB_MA_30")))
st.write("Media 90g:", _safe(reg.get("BB_MA_90")))
st.write("Media 180g:", _safe(reg.get("BB_MA_180")))
st.write("Media 365g:", _safe(reg.get("BB_MA_365")))
st.write("Deviazione std:", _safe(reg.get("BB_STD")))
st.write("Banda -1σ:", _safe(reg.get("BB_LOWER_1SD")))
st.write("Banda +1σ:", _safe(reg.get("BB_UPPER_1SD")))
st.markdown(
    "Z-score attuale: " + _z_badge(reg.get("BB_ZSCORE")), unsafe_allow_html=True
)

st.markdown("#### Competition Map")
row = df_sel.iloc[0] if not df_sel.empty else {}
st.write("Total Offer Count:", _safe(row.get("Total Offer Count")))
st.write(
    "Buy Box: Winner Count 90 days:",
    _safe(row.get("Buy Box: Winner Count 90 days")),
)
st.write("Buy Box: Unqualified:", _safe(row.get("Buy Box: Unqualified")))
st.markdown(
    "MAP restriction: " + _flag_badge(row.get("MAP restriction")),
    unsafe_allow_html=True,
)

st.markdown("#### Amazon Risk & Events")
st.markdown(
    "%Amazon Buy Box 30g: " + _risk_badge(risk.get("BB_AMZ_30"), 50, "%"),
    unsafe_allow_html=True,
)
st.markdown(
    "%Amazon Buy Box 90g: " + _risk_badge(risk.get("BB_AMZ_90"), 50, "%"),
    unsafe_allow_html=True,
)
st.markdown(
    "%Amazon Buy Box 180g: " + _risk_badge(risk.get("BB_AMZ_180"), 50, "%"),
    unsafe_allow_html=True,
)
st.markdown(
    "%Amazon Buy Box 365g: " + _risk_badge(risk.get("BB_AMZ_365"), 50, "%"),
    unsafe_allow_html=True,
)
st.markdown(
    "Amazon: OOS Count 90 days: " + _risk_badge(risk.get("AMZ_OOS_90"), 5, ""),
    unsafe_allow_html=True,
)
st.markdown(
    "Amazon: Amazon offer shipping delay: "
    + _flag_badge(risk.get("AMZ_SHIP_DELAY"), txt_ok="No delay", txt_bad="Delay"),
    unsafe_allow_html=True,
)
st.markdown(
    "Lightning Deals: Is Lowest: "
    + _flag_badge(risk.get("LD_IS_LOWEST"), txt_ok="No", txt_bad="Yes"),
    unsafe_allow_html=True,
)

st.markdown("#### Quality & Returns")
ret = quality.get("Return Rate")
st.markdown(
    "Return Rate: " + _badge(-ret, "%", cls_prefix="badge-quality", display_value=ret),
    unsafe_allow_html=True,
)
rating = quality.get("Reviews: Rating")
st.markdown(
    "Reviews Rating: "
    + _badge(
        rating - 4.0,
        "★",
        cls_prefix="badge-quality",
        display_value=rating,
    ),
    unsafe_allow_html=True,
)
st.markdown(
    "Review Momentum: "
    + _badge(
        quality.get("ReviewsMomentum"),
        "",
        cls_prefix="badge-quality",
    ),
    unsafe_allow_html=True,
)

# Pannello avanzato opzionale
with st.expander("Dettagli avanzati / diagnostica"):
    st.write("Prime righe dataset unito (post-calcoli):")
    cols_disable = [c for c in dfp.columns if c != "Prezzo Sito"]
    if st.checkbox("Abilita editor prezzi", key="show_editor"):
        st.data_editor(dfp.head(50).copy(), disabled=cols_disable, key="dfp_editor")
    st.caption("Suggerimento: usa i preset in sidebar per Flip / Margine / Volume.")

st.success(
    "Opportunity Score 2.0, profitti Amazon/HDG, sconto default 21% e Vista Essenziale attivi."
)
