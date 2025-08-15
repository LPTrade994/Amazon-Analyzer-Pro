# score.py
# -------------------------------------------------------------------
# Costanti, utility e calcoli centralizzati per margini, fees e score.
# Logica IVA/sconto invariata – default sconto=21%.
# -------------------------------------------------------------------

from __future__ import annotations
import math
import pandas as pd
import numpy as np


def parse_float(x, default=None):
    try:
        if pd.isna(x):
            return default
        s = str(x).strip().replace("%", "").replace(",", ".")
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
        if pd.isna(x):
            return 0
        s = str(x).lower().strip().replace(",", ".")
        if s.endswith("kg"):
            return float(s.replace("kg", "")) * 1000
        if s.endswith("g"):
            return float(s.replace("g", ""))
        return float(s)
    except Exception:
        return 0

# ---------------------------
# Config base & costanti
# ---------------------------

VAT_RATES = {
    "IT": 0.22, "DE": 0.19, "FR": 0.20, "ES": 0.21, "UK": 0.20,
    "NL": 0.21, "BE": 0.21, "PL": 0.23, "SE": 0.25, "AT": 0.20,
}

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
    return SHIPPING_COSTS[-1][2]

def _col(df: pd.DataFrame, name: str, default=0.0) -> pd.Series:
    if name in df.columns:
        s = df[name]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        return s
    return pd.Series([default]*len(df), index=df.index)

def _norm_percentile(series: pd.Series, low=0.05, high=0.95):
    if series is None or len(series) == 0:
        return pd.Series([], dtype=float)
    s = series.map(lambda x: parse_float(x, default=np.nan)).replace([np.inf, -np.inf], np.nan)
    fill = np.nanmedian(s) if np.isfinite(np.nanmedian(s)) else 0.0
    s = s.fillna(fill)
    a, b = np.nanquantile(s, low), np.nanquantile(s, high)
    if not np.isfinite(a) or not np.isfinite(b) or a == b:
        return pd.Series([0.5]*len(s), index=s.index)
    out = (s - a) / (b - a)
    return out.clip(0.0, 1.0)

def _zscore(x: pd.Series, mean: pd.Series, std: pd.Series) -> pd.Series:
    """Z = (x - mean) / std, con gestione std=0 e non finiti."""
    x = x.map(lambda v: parse_float(v, default=np.nan))
    mean = mean.map(lambda v: parse_float(v, default=np.nan))
    std = std.map(lambda v: parse_float(v, default=np.nan))
    std_safe = std.where(std.abs() > 1e-12, np.nan)
    z = (x - mean) / std_safe
    z = z.where(np.isfinite(z), 0.0)
    return z

def _to_bool_series(s: pd.Series) -> pd.Series:
    """
    Converte una Series (stringhe/numeri/NaN) in booleano robusto:
    true: yes,y,true,1,si,sì,on
    false: no,n,false,0,off,'' e NaN
    Numerici: >0 -> True, 0 -> False
    """
    if s is None or len(s) == 0:
        return pd.Series([], dtype=bool)
    # prova numerico
    s_num = s.map(lambda v: parse_float(v, default=np.nan))
    mask_num = s_num.notna()
    out = pd.Series(False, index=s.index)
    out.loc[mask_num] = s_num.loc[mask_num] > 0

    # gestisci stringhe
    s_str = s.astype(str).str.strip().str.lower()
    true_vals = {"yes","y","true","1","si","sì","on"}
    false_vals = {"no","n","false","0","off","", "nan", "none"}
    out.loc[~mask_num & s_str.isin(true_vals)] = True
    out.loc[~mask_num & s_str.isin(false_vals)] = False
    # il resto rimane False per default
    return out

# ---------------------------
# Price regime helpers
# ---------------------------

def compute_price_regime(df: pd.DataFrame, price_col: str) -> pd.Series:
    """Calcola medie mobili e regime di prezzo per una serie Buy Box.

    Restituisce una ``Series`` con:
      - medie 30/90/180/365 giorni
      - deviazione standard (ultimi 365 giorni)
      - bande ``±1σ`` attorno alla media 365
      - z-score dell'ultimo prezzo rispetto alla media 365
    """

    prices = _col(df, price_col).map(lambda x: parse_float(x, default=np.nan))
    prices = prices.dropna()
    if prices.empty:
        return pd.Series(
            {
                "BB_MA_30": np.nan,
                "BB_MA_90": np.nan,
                "BB_MA_180": np.nan,
                "BB_MA_365": np.nan,
                "BB_STD": np.nan,
                "BB_LOWER_1SD": np.nan,
                "BB_UPPER_1SD": np.nan,
                "BB_ZSCORE": np.nan,
            }
        )

    def _mean(window: int) -> float:
        if len(prices) < window:
            return prices.mean()
        return prices.tail(window).mean()

    ma30 = _mean(30)
    ma90 = _mean(90)
    ma180 = _mean(180)
    ma365 = _mean(365)

    segment = prices.tail(min(365, len(prices)))
    std = segment.std()
    lower = ma365 - std if pd.notna(std) else np.nan
    upper = ma365 + std if pd.notna(std) else np.nan
    current = prices.iloc[-1]
    z = (current - ma365) / std if pd.notna(std) and std > 1e-12 else 0.0

    return pd.Series(
        {
            "BB_MA_30": ma30,
            "BB_MA_90": ma90,
            "BB_MA_180": ma180,
            "BB_MA_365": ma365,
            "BB_STD": std,
            "BB_LOWER_1SD": lower,
            "BB_UPPER_1SD": upper,
            "BB_ZSCORE": z,
        }
    )

# ---------------------------
# Logica costo d’acquisto (invariata, default sconto 21%)
# ---------------------------

def calc_final_purchase_price(
    data,
    price_or_discount,
    origin_locale_col: str = "Locale",
    discount_map: dict[str, float] | None = None,
) -> pd.Series | float:
    """
    Calcola il prezzo finale di acquisto al netto dell'IVA e dello sconto.

    Può operare sia su un singolo ``dict``/``Series`` (ritornando un float) sia su un
    ``DataFrame`` (ritornando una Series).  Per il caso ``DataFrame`` il secondo
    argomento è il nome della colonna del prezzo, mentre per il caso singolo è il
    valore dello sconto (0–1).
    """

    if isinstance(data, pd.DataFrame):
        df = data
        price_col_origin = price_or_discount
        if discount_map is None:
            discount_map = {}
        default_disc = float(discount_map.get("discount_default_all", 0.21))

        prices = _col(df, price_col_origin).map(lambda x: parse_float(x, default=np.nan))
        locales = _col(df, origin_locale_col).astype(str).map(normalize_locale)

        out = []
        for i in df.index:
            loc = locales.loc[i]
            vat = VAT_RATES.get(loc, 0.22)
            base = prices.loc[i]
            exvat = base / (1.0 + vat) if pd.notna(base) else np.nan
            disc = float(discount_map.get(loc, default_disc))
            exvat_disc = exvat * (1.0 - disc) if pd.notna(exvat) else np.nan
            out.append(exvat_disc)

        return pd.Series(out, index=df.index, name="PurchaseNetExVAT")

    # gestione singolo record (dict o Series)
    row = data
    discount = float(price_or_discount)
    base = parse_float(row.get("Price_Base"), default=np.nan)
    locale = row.get("Locale (base)") or row.get("Locale")
    loc_norm = normalize_locale(str(locale))
    vat = VAT_RATES.get(loc_norm, 0.22)
    exvat = base / (1.0 + vat) if pd.notna(base) else np.nan
    if not pd.notna(exvat):
        return np.nan
    if loc_norm == "IT":
        return exvat - base * discount
    return exvat * (1.0 - discount)

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
    Colonne restituite:
      - PurchaseNetExVAT
      - ProfitAmazonEUR, ProfitAmazonPct
      - ProfitSiteEUR,   ProfitSitePct
      - ShipOut_FBMCost, SaleGrossAmazon, SitePriceGross
    """
    df = df.copy()

    discount_map = {"discount_default_all": default_discount_all}
    df["PurchaseNetExVAT"] = calc_final_purchase_price(
        df, price_col_origin, origin_locale_col=locale_origin_col, discount_map=discount_map
    )

    vat_target = VAT_RATES.get(normalize_locale(locale_target), 0.22)
    vat_it = VAT_RATES.get("IT", 0.22)

    sale_gross_amz = _col(df, price_col_target_bb).map(lambda x: parse_float(x, default=np.nan))

    fee_ref_amt = _col(df, "Referral Fee based on current Buy Box price", np.nan).map(lambda x: parse_float(x, default=np.nan))
    fee_ref_pct = _col(df, "Referral Fee %", 0.0).map(lambda x: parse_float(x, default=np.nan)) / 100.0
    fee_ref_amt = fee_ref_amt.fillna(fee_ref_pct * sale_gross_amz)

    pkg_w = _col(df, "Package: Weight (g)", np.nan).map(lambda x: parse_weight(x) if pd.notna(x) else np.nan)
    item_w = _col(df, "Item: Weight (g)", np.nan).map(lambda x: parse_weight(x) if pd.notna(x) else np.nan)
    weights = pkg_w.fillna(item_w).fillna(0.0)
    ship_fbm = weights.map(calculate_shipping_cost)

    pick_pack = (
        _col(df, "FBA Pick&Pack Fee", 0.0).map(lambda x: parse_float(x, default=np.nan))
        if use_fba
        else pd.Series([0.0] * len(df), index=df.index)
    )
    ship_out_eff = pd.Series([0.0]*len(df), index=df.index) if use_fba else ship_fbm

    proceeds_gross_amz = sale_gross_amz - fee_ref_amt - pick_pack - ship_out_eff
    proceeds_exvat_amz = proceeds_gross_amz / (1.0 + vat_target)

    purchase_net = df["PurchaseNetExVAT"].map(lambda x: parse_float(x, default=np.nan))
    profit_amz_eur = proceeds_exvat_amz - purchase_net
    profit_amz_pct = profit_amz_eur / purchase_net.replace(0, np.nan)

    default_site_price = _col(df, "Buy Box 🚚: Current", np.nan).map(lambda x: parse_float(x, default=np.nan))
    site_price_series = pd.Series([site_price]*len(df), index=df.index) if site_price is not None else default_site_price

    pay_fee = site_price_series * float(payment_fee_site)
    proceeds_gross_site = site_price_series - pay_fee - ship_fbm
    proceeds_exvat_site = proceeds_gross_site / (1.0 + vat_it)

    profit_site_eur = proceeds_exvat_site - purchase_net
    profit_site_pct = profit_site_eur / purchase_net.replace(0, np.nan)

    df["ProfitAmazonEUR"] = profit_amz_eur
    df["ProfitAmazonPct"] = profit_amz_pct
    df["ProfitSiteEUR"]   = profit_site_eur
    df["ProfitSitePct"]   = profit_site_pct
    df["ShipOut_FBMCost"] = ship_fbm
    df["SaleGrossAmazon"] = sale_gross_amz
    df["SitePriceGross"]  = site_price_series

    return df

# ---------------------------
# Simple scoring helpers
# ---------------------------

def margin_score(df: pd.DataFrame) -> pd.Series:
    """Basic margin-based score normalised to 0–1."""
    margin = _col(df, "Margine_Netto_%", 0.0).map(lambda x: parse_float(x, default=np.nan))
    bonus = _col(df, "Trend_Bonus", 0.0).map(lambda x: parse_float(x, default=np.nan))
    roi = _col(df, "ROI_Factor", 0.0).map(lambda x: parse_float(x, default=np.nan))
    combined = margin.fillna(0) + bonus.fillna(0) + roi.fillna(0)
    return _norm_percentile(combined)


def demand_score(df: pd.DataFrame) -> pd.Series:
    """Higher score for lower sales rank."""
    rank = _col(df, "SalesRank_Comp", np.nan).map(lambda x: parse_int(x, default=np.nan))
    return (1.0 - _norm_percentile(rank.fillna(rank.median()))).clip(0, 1)


def competition_score(df: pd.DataFrame) -> pd.Series:
    """Higher score when there are fewer competing offers."""
    offers = _col(df, "NewOffer_Comp", np.nan).map(lambda x: parse_int(x, default=np.nan))
    return (1.0 - _norm_percentile(offers.fillna(offers.median()))).clip(0, 1)


def volatility_score(df: pd.DataFrame) -> pd.Series:
    """Score inversely related to price volatility."""
    vol = _col(df, "PriceVolatility", 0.0).map(lambda x: parse_float(x, default=np.nan))
    return (1.0 - _norm_percentile(vol)).clip(0, 1)


def risk_score(df: pd.DataFrame) -> pd.Series:
    """Average of the basic subscores as a placeholder risk metric."""
    m = margin_score(df)
    d = demand_score(df)
    c = competition_score(df)
    v = volatility_score(df)
    return ((m + d + c + v) / 4.0).clip(0, 1)


def aggregate_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate opportunities by ASIN keeping highest score per ASIN."""
    if df.empty:
        return df
    sorted_df = df.sort_values("Opportunity_Score", ascending=False)
    agg = sorted_df.groupby("ASIN").first().reset_index()
    if "Locale (comp)" in agg.columns:
        agg = agg.rename(columns={"Locale (comp)": "Best_Market"})
    return agg

# ---------------------------
# Opportunity Score 2.0
# ---------------------------

def compute_opportunity_score(
    df: pd.DataFrame,
    weights_pillars: dict[str, float],
    weights_core: dict[str, float],
) -> pd.Series:
    """
    Calcola OpportunityScore (0-100) usando 7 pilastri (+ integrazione pesi storici su Profit).
    weights_pillars keys: wP,wK,wN,wX,wM,wL,wR
    weights_core keys: Epsilon,Theta,Alpha,Beta,Delta,Zeta,Gamma
    """
    # ------ Profit component (Epsilon/Theta) ------
    nz_profit_pct = _norm_percentile(
        _col(df, "ProfitAmazonPct", 0.0).map(lambda x: parse_float(x, default=np.nan)).fillna(0.0)
    )
    nz_profit_eur = _norm_percentile(
        _col(df, "ProfitAmazonEUR", 0.0).map(lambda x: parse_float(x, default=np.nan)).fillna(0.0)
    )
    eps = float(weights_core.get("Epsilon", 3.0))
    the = float(weights_core.get("Theta", 1.5))
    denom = max(1e-6, eps + the)
    profit_component = (eps * nz_profit_pct + the * nz_profit_eur) / denom
    profit_component = profit_component.clip(0, 1)

    # ------ Kappa (MarketEdge) ------
    bb_cur   = _col(df, "SaleGrossAmazon", 0.0).map(lambda x: parse_float(x, default=np.nan))
    bb90_tgt = _col(df, "Buy Box 🚚: 90 days avg.", bb_cur).map(lambda x: parse_float(x, default=np.nan))
    sd90_tgt = _col(df, "Buy Box: Standard Deviation 90 days", 0.0).map(lambda x: parse_float(x, default=np.nan))
    sd90_tgt = sd90_tgt.where(sd90_tgt.abs() > 1e-9, np.nan)

    z_sell_raw = _zscore(bb_cur, bb90_tgt, sd90_tgt)
    z_sell = _norm_percentile(z_sell_raw)

    origin_locale = _col(df, "Locale", "IT").astype(str).map(normalize_locale)
    vat_origin_series = origin_locale.map(lambda c: VAT_RATES.get(c, 0.22))
    buy_gross_proxy = _col(df, "PurchaseNetExVAT", 0.0).map(lambda x: parse_float(x, default=np.nan)) * (1.0 + vat_origin_series)

    bb90_orig = _col(df, "Buy Box 🚚: 90 days avg. (origine)", bb90_tgt).map(lambda x: parse_float(x, default=np.nan))
    sd90_orig = _col(df, "Buy Box: Standard Deviation 90 days (origine)", sd90_tgt).map(lambda x: parse_float(x, default=np.nan))
    sd90_orig = sd90_orig.where(sd90_orig.abs() > 1e-9, np.nan)

    z_buy_raw = _zscore(buy_gross_proxy, bb90_orig, sd90_orig)
    z_buy = _norm_percentile(z_buy_raw)

    edge_base = (z_sell + (1.0 - z_buy)) / 2.0  # 0–1

    thr = _col(df, "Competitive Price Threshold", np.nan).map(lambda x: parse_float(x, default=np.nan))
    sug = _col(df, "Suggested Lower Price", np.nan).map(lambda x: parse_float(x, default=np.nan))
    pen_thr = _to_bool_series(bb_cur > thr).astype(float) * 0.15
    pen_sug = _to_bool_series(bb_cur > sug).astype(float) * 0.10

    kappa = (edge_base - pen_thr - pen_sug).clip(0, 1)

    # ------ Nu (DemandMomentum) ------
    rank_curr = _col(df, "Sales Rank: Current", np.nan).map(lambda x: parse_int(x, default=np.nan))
    rank_score = 1.0 - _norm_percentile(rank_curr.fillna(np.nanmedian(rank_curr)))
    drops90 = _norm_percentile(_col(df, "Sales Rank: Drops last 90 days", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    bpm     = _norm_percentile(_col(df, "Bought in past month", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    chg90   = _norm_percentile(_col(df, "90 days change % monthly sold", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    zeta    = float(weights_core.get("Zeta", 1.0))
    nu = (0.40*rank_score + 0.25*drops90 + 0.20*bpm + 0.15*chg90 + 0.05*(zeta/3.0)).clip(0,1)

    # ------ Xi (CompetitionPressure) ------
    offer   = _norm_percentile(_col(df, "Total Offer Count", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    winner  = 1.0 - _norm_percentile(_col(df, "Buy Box: Winner Count 90 days", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    unqual  = _norm_percentile(_col(df, "Buy Box: Unqualified", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    map_pen = _to_bool_series(_col(df, "MAP restriction", False)).astype(float) * 0.2
    xi = (1.0 - (0.5*offer + 0.3*winner) + 0.2*unqual - map_pen).clip(0,1)

    # ------ Mu (AmazonRisk) ------
    p_amz = _norm_percentile(_col(df, "Buy Box: % Amazon 90 days", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    oos   = _norm_percentile(_col(df, "Amazon: OOS Count 90 days", 0.0).map(lambda x: parse_int(x, default=np.nan)))
    delay_presence = _to_bool_series(_col(df, "Amazon: Amazon offer shipping delay", np.nan)).astype(float) * 0.1
    mu = (1.0 - 0.8*p_amz + 0.3*oos + delay_presence).clip(0,1)

    # ------ Lambda (PriceStability) ------
    sd90_for_stab = _norm_percentile(_col(df, "Buy Box: Standard Deviation 90 days", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    flp           = _norm_percentile(_col(df, "Buy Box: Flipability 90 days", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    lamb = (1.0 - 0.7*sd90_for_stab + 0.5*flp).clip(0,1)

    # ------ Rho (QualityRisk) ------
    ret   = 1.0 - _norm_percentile(_col(df, "Return Rate", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    rate  = _norm_percentile(_col(df, "Reviews: Rating", 0.0).map(lambda x: parse_float(x, default=np.nan)))
    rc_g  = _norm_percentile(
        _col(df, "Reviews: Rating Count", 0.0).map(lambda x: parse_int(x, default=np.nan)) -
        _col(df, "Reviews: Rating Count - 90 days avg.", 0.0).map(lambda x: parse_int(x, default=np.nan))
    )
    deal_pen = _to_bool_series(_col(df, "Lightning Deals: Is Lowest", False)).astype(float) * 0.1
    rho = (0.5*ret + 0.3*rate + 0.2*rc_g - deal_pen).clip(0,1)

    # ------ Pesatura pilastri ------
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
