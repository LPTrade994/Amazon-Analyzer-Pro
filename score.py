# score.py
# -------------------------------------------------------------------
# Costanti, utility e calcoli centralizzati per margini, fees e score.
# Logica IVA/sconto invariata – solo default sconto=21%.
# -------------------------------------------------------------------

from __future__ import annotations
import math
import pandas as pd
import numpy as np

# ---------------------------
# Config base & costanti
# ---------------------------

# IVA standard di riferimento per principali mercati EU (override dai file se presenti)
VAT_RATES = {
    "IT": 0.22, "DE": 0.19, "FR": 0.20, "ES": 0.21, "UK": 0.20,
    "NL": 0.21, "BE": 0.21, "PL": 0.23, "SE": 0.25, "AT": 0.20,
}

# Costi di spedizione FBM (esempio semplice per peso lordo in grammi)
SHIPPING_COSTS = [
    (0, 250, 3.50),
    (251, 500, 4.00),
    (501, 1000, 4.80),
    (1001, 2000, 5.90),
    (2001, 5000, 7.90),
    (5001, 10000, 12.50),
]

# ---------------------------
# Utility
# ---------------------------

def normalize_locale(locale: str) -> str:
    if not isinstance(locale, str) or not locale:
        return "IT"
    val = locale.strip().upper()
    # mappature comuni Keepa/Amazon
    if val.startswith("AMAZON."):
        val = val.split(".", 1)[1]
    if len(val) == 5 and "-" in val:
        val = val.split("-", 1)[1]  # es. de-DE -> DE
    if val == "GB":
        return "UK"
    return val[:2]

def calculate_shipping_cost(weight_g: float | int) -> float:
    try:
        w = float(weight_g) if weight_g is not None and not (isinstance(weight_g, float) and math.isnan(weight_g)) else 0.0
    except Exception:
        w = 0.0
    for lo, hi, cost in SHIPPING_COSTS:
        if lo <= w <= hi:
            return cost
    return SHIPPING_COSTS[-1][2]  # massimo

def _safe_num(x, default=None):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def _col(df: pd.DataFrame, name: str, default=0.0) -> pd.Series:
    return df[name] if name in df.columns else pd.Series([default]*len(df), index=df.index)

def _pct(x, y):
    try:
        x = float(x); y = float(y)
        if y == 0:
            return np.nan
        return (x - y) / y
    except Exception:
        return np.nan

def _clamp01(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    if v < 0: return 0.0
    if v > 1: return 1.0
    return v

def _norm_percentile(series: pd.Series, low=0.05, high=0.95):
    if series is None or len(series) == 0:
        return pd.Series([], dtype=float)
    s = series.astype(float).replace([np.inf, -np.inf], np.nan).fillna(series.median())
    a, b = s.quantile(low), s.quantile(high)
    if a == b:
        return pd.Series([0.5]*len(s), index=s.index)
    out = (s - a) / (b - a)
    return out.clip(lower=0.0, upper=1.0)

# ---------------------------
# Logica costo d’acquisto (invariata, default sconto 21%)
# ---------------------------

def calc_final_purchase_price(
    df: pd.DataFrame,
    price_col_origin: str,
    origin_locale_col: str = "Locale",
    discount_map: dict[str, float] | None = None,
) -> pd.Series:
    """
    Calcolo costo d'acquisto netto ex-IVA applicando:
      1) Rimozione IVA del paese di ORIGINE (in base alla colonna 'Locale' o simile)
      2) Applicazione SCONTO (default 21%) – la logica resta invariata, qui forziamo solo il default iniziale

    discount_map: es. {"IT": 0.21, "DE": 0.21, ...}. Se None → default 21% su tutti.
    """
    # Default: 21% su tutti i paesi (l'utente può modificarlo in UI)
    if discount_map is None:
        discount_map = {}

    if "discount_default_all" in discount_map:
        default_disc = float(discount_map["discount_default_all"])
    else:
        default_disc = 0.21

    prices = _col(df, price_col_origin).astype(float)
    locales = _col(df, origin_locale_col).astype(str).map(normalize_locale)

    ex_vat_prices = []
    for i in df.index:
        loc = locales.loc[i]
        vat = VAT_RATES.get(loc, 0.22)
        base = prices.loc[i]
        try:
            exvat = base / (1.0 + vat)
        except Exception:
            exvat = np.nan
        disc = discount_map.get(loc, default_disc)
        try:
            exvat_disc = exvat * (1.0 - float(disc))
        except Exception:
            exvat_disc = exvat
        ex_vat_prices.append(exvat_disc)

    return pd.Series(ex_vat_prices, index=df.index, name="PurchaseNetExVAT")

# ---------------------------
# Profitti Amazon / HDG
# ---------------------------

def compute_profits(
    df: pd.DataFrame,
    price_col_origin: str,
    price_col_target_bb: str,
    locale_target: str = "IT",
    locale_origin_col: str = "Locale",
    use_fba: bool = False,
    site_price: float | None = None,
    payment_fee_site: float = 0.05,
    default_discount_all: float = 0.21,
) -> pd.DataFrame:
    """
    Restituisce colonne:
      - PurchaseNetExVAT
      - ProfitAmazonEUR, ProfitAmazonPct
      - ProfitSiteEUR,   ProfitSitePct
    Usa 'Referral Fee based on current Buy Box price' se presente, altrimenti 'Referral Fee %'.
    Considera pick&pack se use_fba=True, e shipping FBM in caso contrario.
    """
    df = df.copy()

    # Costo d'acquisto netto ex-IVA (logica invariata, solo default sconto=21%)
    discount_map = {"discount_default_all": default_discount_all}
    df["PurchaseNetExVAT"] = calc_final_purchase_price(
        df, price_col_origin, origin_locale_col=locale_origin_col, discount_map=discount_map
    )

    # Target VAT
    vat_target = VAT_RATES.get(normalize_locale(locale_target), 0.22)
    vat_it = VAT_RATES.get("IT", 0.22)

    # Prezzo vendita su Amazon (BB target)
    sale_gross_amz = _col(df, price_col_target_bb)

    # Referral fee amount (priorità alla colonna valore assoluto)
    fee_ref_amt = _col(df, "Referral Fee based on current Buy Box price", np.nan)
    fee_ref_pct = _col(df, "Referral Fee %", 0.0) / 100.0
    fee_ref_amt = fee_ref_amt.fillna(fee_ref_pct * sale_gross_amz)

    # Spedizione in uscita (FBM) o pick&pack FBA
    weights = _col(df, "Package: Weight (g)", 0.0).fillna(_col(df, "Item: Weight (g)", 0.0))
    ship_fbm = weights.map(calculate_shipping_cost)
    pick_pack = _col(df, "FBA Pick&Pack Fee", 0.0) if use_fba else pd.Series([0.0]*len(df), index=df.index)
    ship_out_eff = pd.Series([0.0]*len(df), index=df.index) if use_fba else ship_fbm

    proceeds_gross_amz = sale_gross_amz - fee_ref_amt - pick_pack - ship_out_eff
    proceeds_exvat_amz = proceeds_gross_amz / (1.0 + vat_target)

    profit_amz_eur = proceeds_exvat_amz - df["PurchaseNetExVAT"]
    profit_amz_pct = profit_amz_eur / df["PurchaseNetExVAT"].replace(0, np.nan)

    # Prezzo sito (default: Buy Box IT Current se presente, altrimenti prezzo target scelto)
    default_site_price = _col(df, "Buy Box 🚚: Current", np.nan)
    site_price_series = pd.Series(
        [site_price]*len(df), index=df.index
    ) if site_price is not None else default_site_price

    pay_fee = site_price_series * float(payment_fee_site)
    proceeds_gross_site = site_price_series - pay_fee - ship_fbm
    proceeds_exvat_site = proceeds_gross_site / (1.0 + vat_it)

    profit_site_eur = proceeds_exvat_site - df["PurchaseNetExVAT"]
    profit_site_pct = profit_site_eur / df["PurchaseNetExVAT"].replace(0, np.nan)

    # wrap up
    df["ProfitAmazonEUR"] = profit_amz_eur
    df["ProfitAmazonPct"] = profit_amz_pct
    df["ProfitSiteEUR"] = profit_site_eur
    df["ProfitSitePct"] = profit_site_pct
    df["ShipOut_FBMCost"] = ship_fbm
    df["SaleGrossAmazon"] = sale_gross_amz
    df["SitePriceGross"] = site_price_series

    return df

# ---------------------------
# Opportunity Score 2.0
# ---------------------------

def compute_opportunity_score(
    df: pd.DataFrame,
    weights_pillars: dict[str, float],
    weights_core: dict[str, float],
) -> pd.Series:
    """
    Calcola OpportunityScore (0-100) usando 7 pilastri (+ integrazione pesi storici su Profit/Domanda/Concorrenza).
    weights_pillars keys: wP,wK,wN,wX,wM,wL,wR
    weights_core keys: Epsilon,Theta,Alpha,Beta,Delta,Zeta,Gamma
    """
    # Normalizzazioni robuste
    nz_profit_pct = _norm_percentile(df["ProfitAmazonPct"].replace([np.inf, -np.inf], np.nan).fillna(0))
    nz_profit_eur = _norm_percentile(df["ProfitAmazonEUR"].replace([np.inf, -np.inf], np.nan).fillna(0))

    # Profit component (Epsilon/Theta)
    eps = float(weights_core.get("Epsilon", 3.0))
    the = float(weights_core.get("Theta", 1.5))
    denom = max(1e-6, eps + the)
    profit_component = (eps * nz_profit_pct + the * nz_profit_eur) / denom
    profit_component = profit_component.clip(0, 1)

    # --- Kappa (MarketEdge)
    bb = _col(df, "SaleGrossAmazon")  # same as target BB
    bb90 = _col(df, "Buy Box 🚚: 90 days avg.", bb)  # fallback
    sd90 = _col(df, "Buy Box: Standard Deviation 90 days", 0.0).replace(0, np.nan)
    z_sell = ((bb - bb90) / sd90).replace([np.inf, -np.inf], np.nan).fillna(0)
    z_sell = _norm_percentile(z_sell)

    orig90 = _col(df, "Buy Box 🚚: 90 days avg. (origine)", bb90)  # se non presente fallback
    z_buy = (( _col(df, "PurchaseNetExVAT") * (1.0 + 0.22) ) - orig90) / sd90  # approx per edge buy
    z_buy = z_buy.replace([np.inf, -np.inf], np.nan).fillna(0)
    z_buy = _norm_percentile(z_buy)

    edge = (z_sell + (1.0 - z_buy)) / 2.0  # [0,1]
    pen_thr = (_col(df, "Competitive Price Threshold", 0.0) > 0) & (bb > _col(df, "Competitive Price Threshold", 0.0))
    pen_sug = (_col(df, "Suggested Lower Price", 0.0) > 0) & (bb > _col(df, "Suggested Lower Price", 0.0))
    kappa = (edge - 0.15*pen_thr.astype(float) - 0.10*pen_sug.astype(float)).clip(0, 1)

    # --- Nu (DemandMomentum)
    rank_curr = _col(df, "Sales Rank: Current", np.nan).replace(0, np.nan)
    rank_score = 1.0 - _norm_percentile(rank_curr.fillna(rank_curr.median()))
    drops90 = _norm_percentile(_col(df, "Sales Rank: Drops last 90 days", 0.0))
    bpm     = _norm_percentile(_col(df, "Bought in past month", 0.0))
    chg90   = _norm_percentile(_col(df, "90 days change % monthly sold", 0.0))
    zeta    = float(weights_core.get("Zeta", 1.0))
    nu = (0.40*rank_score + 0.25*drops90 + 0.20*bpm + 0.15*chg90 + 0.05*(zeta/3.0)).clip(0,1)

    # --- Xi (CompetitionPressure)
    offer   = _norm_percentile(_col(df, "Total Offer Count", 0.0))
    winner  = 1.0 - _norm_percentile(_col(df, "Buy Box: Winner Count 90 days", 0.0))
    unqual  = _norm_percentile(_col(df, "Buy Box: Unqualified", 0.0))
    map_pen = _col(df, "MAP restriction", False).fillna(False).astype(float) * 0.2
    xi = (1.0 - (0.5*offer + 0.3*winner) + 0.2*unqual - map_pen).clip(0,1)

    # --- Mu (AmazonRisk)
    p_amz = _norm_percentile(_col(df, "Buy Box: % Amazon 90 days", 0.0))
    oos   = _norm_percentile(_col(df, "Amazon: OOS Count 90 days", 0.0))
    delay = _col(df, "Amazon: Amazon offer shipping delay", np.nan).notna().astype(float) * 0.1
    mu = (1.0 - 0.8*p_amz + 0.3*oos + delay).clip(0,1)

    # --- Lambda (PriceStability)
    sd90 = _norm_percentile(_col(df, "Buy Box: Standard Deviation 90 days", 0.0))
    flp  = _norm_percentile(_col(df, "Buy Box: Flipability 90 days", 0.0))
    lamb = (1.0 - 0.7*sd90 + 0.5*flp).clip(0,1)

    # --- Rho (QualityRisk)
    ret   = 1.0 - _norm_percentile(_col(df, "Return Rate", 0.0))
    rate  = _norm_percentile(_col(df, "Reviews: Rating", 0.0))
    rc_g  = _norm_percentile(_col(df, "Reviews: Rating Count", 0.0) - _col(df, "Reviews: Rating Count - 90 days avg.", 0.0))
    deal_pen = _col(df, "Lightning Deals: Is Lowest", False).fillna(False).astype(float) * 0.1
    rho = (0.5*ret + 0.3*rate + 0.2*rc_g - deal_pen).clip(0,1)

    # Pesi pilastri
    wP = float(weights_pillars.get("wP", 40))
    wK = float(weights_pillars.get("wK", 15))
    wN = float(weights_pillars.get("wN", 15))
    wX = float(weights_pillars.get("wX", 10))
    wM = float(weights_pillars.get("wM", 8))
    wL = float(weights_pillars.get("wL", 7))
    wR = float(weights_pillars.get("wR", 5))
    total_w = max(1.0, wP+wK+wN+wX+wM+wL+wR)

    score = (wP*profit_component + wK*kappa + wN*nu + wX*xi + wM*mu + wL*lamb + wR*rho) * (100.0/total_w)
    return score.clip(0,100)
