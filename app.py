# app.py
# ---------------------------------------------------------
# Amazon Market Analyzer – Upgrade Opportunity Score 2.0
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
    compute_profits, compute_opportunity_score
)

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
.grid-ess { display:grid; grid-template-columns: 1.8fr 1.2fr 1.6fr 1.6fr 1.2fr; gap: 14px; }
.card { background: var(--card); padding: 14px 16px; border-radius: 16px; border:1px solid #1f1f22; }
h1,h2,h3,h4 { color: var(--text); }
hr { border-color:#222227; }
label, p, span, div { color: var(--text); }
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
site_price_override = st.sidebar.text_input("Prezzo HDGaming (vuoto = usa BB IT Current)", value="")
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
    st.markdown("**Vista Essenziale** — identità + prezzi chiave + profitti Amazon/HDG. \
Pannelli avanzati disponibili a richiesta.")
with colB:
    st.metric("Sconto default", f"{int(disc_default*100)}%")
with colC:
    st.toggle("Dark Mode", value=True, key="__dark_fake__", disabled=True)

if not (orig_file and tgt_file):
    st.info("⬆️ Carica **Lista di Origine** e **Lista di Confronto** per iniziare.")
    st.stop()

# Carica
df_orig = load_data(orig_file)
df_tgt  = load_data(tgt_file)

# Merge by ASIN (safe)
if "ASIN" not in df_orig.columns or "ASIN" not in df_tgt.columns:
    st.error("Assicurati che entrambi i file contengano la colonna **ASIN**.")
    st.stop()

# Preferisci colonne della lista target per prezzi BB target,
# mantieni identità da origine, poi fai left join sulla target.
id_cols = [c for c in ["ASIN","Title","Brand","Locale","Package: Weight (g)","Item: Weight (g)"] if c in df_orig.columns]
df = pd.merge(df_orig, df_tgt, on="ASIN", how="left", suffixes=("", " (tgt)"))

# Imposta locale target (default IT, modificabile con selectbox se vuoi estendere)
locale_target = "IT"

# Calcola profitti
dfp = compute_profits(
    df,
    price_col_origin=origin_price_col,
    price_col_target_bb=target_price_col + "",
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
df_view["BB_AmzShare90d"] = df_view.get("Buy Box: % Amazon 90 days", pd.Series([np.nan]*len(df_view))).astype(float)

mask = (
    (df_view["ProfitAmazonEUR"] >= min_profit_eur) &
    (df_view["ProfitAmazonPctView"] >= min_profit_pct) &
    ((df_view["BB_AmzShare90d"].fillna(0.0)) <= max_amz_share) &
    (df_view.get("Total Offer Count", pd.Series([0]*len(df_view))).fillna(0) <= max_offer_cnt) &
    (df_view.get("Sales Rank: Current", pd.Series([0]*len(df_view))).fillna(0) <= max_rank)
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

df_ess = df_view[cols_ess].rename(columns={
    origin_price_col: "Orig Price",
    target_price_col: "BB Target",
    "ProfitAmazonPctView": "Profit Amazon %",
    "ProfitSitePctView": "Profit HDG %",
    "SitePriceGross": "Prezzo HDG",
})

# Ordinamento per score
df_ess = df_ess.sort_values(by="OpportunityScore", ascending=False)

# Render con badge per profitti
def _badge(v, suffix="€"):
    if pd.isna(v):
        cls = "badge-profit-neu"; txt = "—"
    else:
        try:
            val = float(v)
            if suffix == "%": val = round(val, 1)
            else: val = round(val, 2)
            if float(v) > 0.01:
                cls = "badge-profit-pos"
            elif float(v) < -0.01:
                cls = "badge-profit-neg"
            else:
                cls = "badge-profit-neu"
            txt = f"{val}{suffix}"
        except Exception:
            cls = "badge-profit-neu"; txt = "—"
    return f'<span class="badge badge-xl {cls}">{txt}</span>'

st.markdown("### 📋 Elenco prodotti (Essenziale)")
# Costruiamo una tabella HTML elegante per i badge
table_rows = []
header = [
    "ASIN","Title","Brand","Locale",
    "Orig Price","Costo ex-IVA","Peso (g)",
    "BB Target","Profit Amazon €","Profit Amazon %",
    "Prezzo HDG","Profit HDG €","Profit HDG %",
    "Rank","%Amazon 90d","Return","Score"
]
table_rows.append("<tr>" + "".join([f"<th style='text-align:left;padding:8px 10px'>{h}</th>" for h in header]) + "</tr>")

for _, r in df_ess.iterrows():
    peso = r.get("Package: Weight (g)", np.nan)
    if pd.isna(peso): peso = r.get("Item: Weight (g)", np.nan)
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
        f"{round(float(r.get('OpportunityScore',0)),1)}"
    ]
    table_rows.append("<tr>" + "".join([f"<td style='padding:8px 10px'>{cell}</td>" for cell in row]) + "</tr>")

html_table = f"""
<div class="card">
  <div style="overflow:auto;">
    <table style="width:100%;border-collapse:collapse">
      {''.join(table_rows)}
    </table>
  </div>
</div>
"""

def _safe(x):
    try:
        if x is None or (isinstance(x,float) and np.isnan(x)): return "—"
        if isinstance(x,(int,float)): 
            return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")
        return str(x)
    except Exception:
        return "—"

st.markdown(html_table, unsafe_allow_html=True)

# Pannello avanzato opzionale
with st.expander("Dettagli avanzati / diagnostica"):
    st.write("Prime righe dataset unito (post-calcoli):")
    st.dataframe(dfp.head(50))
    st.caption("Suggerimento: usa i preset in sidebar per Flip / Margine / Volume.")

st.success("Aggiornamento completato: Opportunity Score 2.0, profitti Amazon/HDG, sconto default 21%, UI Essenziale.")
