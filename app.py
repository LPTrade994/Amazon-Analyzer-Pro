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
from loaders import load_data, parse_float, parse_int, parse_weight, default_discount_map
from score import (
    SHIPPING_COSTS, VAT_RATES, normalize_locale,
    calculate_shipping_cost, calc_final_purchase_price,
    compute_profits, compute_opportunity_score, compute_price_regime
)

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

def _badge(value, suffix="€"):
    """Badge XL colorato per profitti."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        cls = "badge-profit-neu"; txt = "—"
    else:
        try:
            v = float(value)
            if suffix == "%":
                disp = f"{round(v, 1)}{suffix}"
            else:
                disp = f"{round(v, 2)}{suffix}"
            if v > 0.01:
                cls = "badge-profit-pos"
            elif v < -0.01:
                cls = "badge-profit-neg"
            else:
                cls = "badge-profit-neu"
            txt = disp
        except Exception:
            cls = "badge-profit-neu"; txt = "—"
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


def _missing_columns(df: pd.DataFrame, required: list[str]) -> list[str]:
    """Return a list of required columns that are absent from *df*."""
    return [c for c in required if c not in df.columns]


def _validate_required_columns(df_orig: pd.DataFrame, df_tgt: pd.DataFrame, required: list[str]) -> None:
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
.badge-xl { font-size: 0.95rem; }
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
orig_file = st.sidebar.file_uploader("Lista di Origine", type=["xlsx","xls","csv"])
tgt_file  = st.sidebar.file_uploader("Lista di Confronto", type=["xlsx","xls","csv"])

st.sidebar.subheader("Prezzi da usare")
price_cols_hint = [
    "Buy Box 🚚: Current", "Amazon: Current", "New: Current",
    "New, 3rd Party FBM 🚚: Current", "New, 3rd Party FBA: Current"
]

origin_price_col = st.sidebar.selectbox("Prezzo Origine", options=price_cols_hint, index=0)
target_price_col = st.sidebar.selectbox("Prezzo Target (Amazon)", options=price_cols_hint, index=0)

st.sidebar.subheader("Parametri vendita")
use_fba = st.sidebar.toggle("Usa FBA (considera Pick&Pack)", value=False)
site_price_override = st.sidebar.text_input(
    "Prezzo HDGaming (vuoto = usa BB IT Current)", value=""
)
site_price_override_val = parse_float(site_price_override, default=None)

st.sidebar.subheader("Sconto acquisto (default 21%)")
disc_default = st.sidebar.slider("Sconto default per tutti i paesi", min_value=0, max_value=60, value=21, step=1) / 100.0
discount_map = {"discount_default_all": disc_default}

st.sidebar.subheader("Pesi pilastri (Opportunity 2.0)")
wP = st.sidebar.slider("Profit", 0, 60, 40)
wK = st.sidebar.slider("Edge", 0, 40, 15)
wN = st.sidebar.slider("Demand", 0, 40, 15)
wX = st.sidebar.slider("Competition", 0, 30, 10)
wM = st.sidebar.slider("AmazonRisk", 0, 30, 8)
wL = st.sidebar.slider("Stability", 0, 30, 7)
wR = st.sidebar.slider("Quality", 0, 30, 5)
weights_pillars = dict(wP=wP,wK=wK,wN=wN,wX=wX,wM=wM,wL=wL,wR=wR)

st.sidebar.subheader("Pesi storici (Core)")
Epsilon = st.sidebar.slider("Margine % (ε)", 0.0, 5.0, 3.0, 0.1)
Theta   = st.sidebar.slider("Margine € (θ)", 0.0, 5.0, 1.5, 0.1)
Alpha   = st.sidebar.slider("Vendibilità Rank (α)", 0.0, 3.0, 1.0, 0.1)
Beta    = st.sidebar.slider("Domanda recente (β)", 0.0, 3.0, 1.0, 0.1)
Delta   = st.sidebar.slider("Concorrenza (δ)", 0.0, 3.0, 1.0, 0.1)
Zeta    = st.sidebar.slider("Trend Rank (ζ)", 0.0, 3.0, 1.0, 0.1)
Gamma   = st.sidebar.slider("Volume stimato (γ)", 0.0, 4.0, 2.0, 0.1)
weights_core = dict(Epsilon=Epsilon,Theta=Theta,Alpha=Alpha,Beta=Beta,Delta=Delta,Zeta=Zeta,Gamma=Gamma)

st.sidebar.subheader("Filtri rapidi")
min_profit_eur = st.sidebar.number_input("Min Profit Amazon €", value=5.0, step=0.5)
min_profit_pct = st.sidebar.number_input("Min Profit Amazon %", value=15.0, step=1.0)
max_amz_share  = st.sidebar.number_input("Max %Amazon BuyBox (90d)", value=50.0, step=1.0)
max_offer_cnt  = st.sidebar.number_input("Max Offer Count", value=40, step=1)
max_rank       = st.sidebar.number_input("Max Sales Rank (curr)", value=350000, step=5000)

# -----------------------
# MAIN
# -----------------------
st.title("🔎 Amazon Market Analyzer — Opportunity 2.0")

colA, colB, colC = st.columns([1.2,1,1])
with colA:
    st.markdown("**Vista Essenziale** — identità + prezzi chiave + profitti Amazon/HDG. "
                "Pannelli avanzati disponibili a richiesta.")
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
    default_discount_all=disc_default
)

# Opportunity Score
dfp["OpportunityScore"] = compute_opportunity_score(dfp, weights_pillars, weights_core)

# Filtri rapidi
def _to_pct(x):
    try:
        return float(x)*100.0
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

mask = (
    (
        df_view["ProfitAmazonEUR"].map(lambda x: parse_float(x, default=np.nan)).fillna(-9e9)
        >= float(min_profit_eur)
    )
    & (
        df_view["ProfitAmazonPctView"].map(lambda x: parse_float(x, default=np.nan)).fillna(-9e9)
        >= float(min_profit_pct)
    )
    & (df_view["BB_AmzShare90d"].fillna(0.0) <= float(max_amz_share))
    & (
        df_view.get("Total Offer Count", pd.Series([0] * len(df_view)))
        .map(lambda x: parse_int(x, default=np.nan))
        .fillna(0)
        <= int(max_offer_cnt)
    )
    & (
        df_view.get("Sales Rank: Current", pd.Series([0] * len(df_view)))
        .map(lambda x: parse_int(x, default=np.nan))
        .fillna(0)
        <= int(max_rank)
    )
)
df_view = df_view[mask]

# Vista ESSENZIALE
cols_ess = []
for c in ["ASIN","Title","Brand","Locale",
          origin_price_col, "PurchaseNetExVAT", "Package: Weight (g)", "Item: Weight (g)",
          target_price_col, "ProfitAmazonEUR","ProfitAmazonPctView",
          "SitePriceGross","ProfitSiteEUR","ProfitSitePctView",
          "Sales Rank: Current", "Buy Box: % Amazon 90 days", "Return Rate",
          "OpportunityScore"]:
    if c in df_view.columns:
        cols_ess.append(c)

if len(cols_ess) == 0:
    st.error("Non sono presenti le colonne attese per la Vista Essenziale.")
    st.stop()

df_ess = df_view[cols_ess].rename(columns={
    origin_price_col: "Orig Price",
    target_price_col: "BB Target",
    "ProfitAmazonPctView": "Profit Amazon %",
    "ProfitSitePctView": "Profit HDG %",
    "SitePriceGross": "Prezzo HDG",
})

# Ordinamento per score
if "OpportunityScore" in df_ess.columns:
    df_ess = df_ess.sort_values(by="OpportunityScore", ascending=False)

# Render tabella HTML con badge
st.markdown("### 📋 Elenco prodotti (Essenziale)")

header = [
    "ASIN","Title","Brand","Locale",
    "Orig Price","Costo ex-IVA","Peso (g)",
    "BB Target","Profit Amazon €","Profit Amazon %",
    "Prezzo HDG","Profit HDG €","Profit HDG %",
    "Rank","%Amazon 90d","Return","Score"
]

rows_html = []
rows_html.append("<tr>" + "".join([f"<th style='text-align:left;padding:8px 10px'>{h}</th>" for h in header]) + "</tr>")

for _, r in df_ess.iterrows():
    peso = r.get("Package: Weight (g)", np.nan)
    if pd.isna(peso):
        peso = r.get("Item: Weight (g)", np.nan)

    row = [
        r.get("ASIN",""),
        r.get("Title",""),
        r.get("Brand",""),
        r.get("Locale",""),
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
    ]
    rows_html.append("<tr>" + "".join([f"<td style='padding:8px 10px'>{cell}</td>" for cell in row]) + "</tr>")

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
with st.expander("Price Regime"):
    st.write("Media 30g:", _safe(reg.get("BB_MA_30")))
    st.write("Media 90g:", _safe(reg.get("BB_MA_90")))
    st.write("Media 180g:", _safe(reg.get("BB_MA_180")))
    st.write("Media 365g:", _safe(reg.get("BB_MA_365")))
    st.write("Deviazione std:", _safe(reg.get("BB_STD")))
    st.write("Banda -1σ:", _safe(reg.get("BB_LOWER_1SD")))
    st.write("Banda +1σ:", _safe(reg.get("BB_UPPER_1SD")))
    st.markdown("Z-score attuale: " + _z_badge(reg.get("BB_ZSCORE")), unsafe_allow_html=True)

# Pannello avanzato opzionale
with st.expander("Dettagli avanzati / diagnostica"):
    st.write("Prime righe dataset unito (post-calcoli):")
    st.dataframe(dfp.head(50))
    st.caption("Suggerimento: usa i preset in sidebar per Flip / Margine / Volume.")

st.success("Opportunity Score 2.0, profitti Amazon/HDG, sconto default 21% e Vista Essenziale attivi.")
