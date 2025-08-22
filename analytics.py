"""
Analytics Module - Historic Deals and Advanced Metrics

Modulo "Affari Storici" per identificare opportunità di mean reversion
quando il prezzo corrente è significativamente sotto le medie storiche.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from scoring import velocity_index


def calculate_historic_metrics(row: pd.Series) -> Dict[str, float]:
    """
    Calcola metriche storiche per identificare affari
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        Dict con metriche storiche e deviazioni
    """
    # Prezzi storici
    current_price = row.get('Buy Box 🚚: Current', 0)
    avg_30d = row.get('Buy Box 🚚: 30 days avg.', current_price)
    avg_90d = row.get('Buy Box 🚚: 90 days avg.', current_price)
    avg_180d = row.get('Buy Box 🚚: 180 days avg.', current_price)
    lowest_180d = row.get('Buy Box 🚚: Lowest', current_price)
    highest_180d = row.get('Buy Box 🚚: Highest', current_price)
    
    # Gestione valori NaN o zero
    if pd.isna(current_price) or current_price <= 0:
        current_price = 0
    if pd.isna(avg_30d) or avg_30d <= 0:
        avg_30d = current_price
    if pd.isna(avg_90d) or avg_90d <= 0:
        avg_90d = current_price
    if pd.isna(avg_180d) or avg_180d <= 0:
        avg_180d = current_price
    if pd.isna(lowest_180d) or lowest_180d <= 0:
        lowest_180d = current_price
    if pd.isna(highest_180d) or highest_180d <= 0:
        highest_180d = current_price
    
    # Calcola deviazioni percentuali dalle medie
    dev_30d = (current_price - avg_30d) / avg_30d if avg_30d > 0 else 0.0
    dev_90d = (current_price - avg_90d) / avg_90d if avg_90d > 0 else 0.0
    dev_180d = (current_price - avg_180d) / avg_180d if avg_180d > 0 else 0.0
    
    return {
        'current': float(current_price),
        'avg_30d': float(avg_30d),
        'avg_90d': float(avg_90d),
        'avg_180d': float(avg_180d),
        'dev_30d': float(dev_30d),
        'dev_90d': float(dev_90d),
        'dev_180d': float(dev_180d),
        'lowest': float(lowest_180d),
        'highest': float(highest_180d)
    }


def is_historic_deal(row: pd.Series, thresholds: Dict[str, float] = None) -> bool:
    """
    Determina se è un "Affare Storico"
    
    Args:
        row: Pandas Series con i dati del prodotto
        thresholds: Soglie per i criteri di selezione
        
    Returns:
        bool: True se è un affare storico
    """
    if thresholds is None:
        thresholds = {'dev_90d': -0.10, 'velocity_min': 40}
    
    # Calcola metriche storiche
    metrics = calculate_historic_metrics(row)
    
    # Calcola velocity score
    velocity = velocity_index(row)
    
    # Condizione 1: Prezzo corrente ≤ 90% della media 90d
    is_low_price = metrics['dev_90d'] <= thresholds['dev_90d']
    
    # Condizione 2: Buona liquidità (velocity minima)
    good_velocity = velocity >= thresholds['velocity_min']
    
    # Condizione 3: Non Amazon dominante (facoltativo)
    amazon_share = row.get('Buy Box: % Amazon 90 days', 100)
    if pd.isna(amazon_share):
        amazon_share = 100
    low_amazon = amazon_share <= 80
    
    # Condizione 4: Non OOS prolungato
    oos_90d = row.get('Buy Box: 90 days OOS', 0)
    if pd.isna(oos_90d):
        oos_90d = 0
    reasonable_oos = oos_90d <= 30  # max 30% OOS
    
    # Condizione 5: Prezzo corrente deve essere valido
    valid_price = metrics['current'] > 0
    
    return (is_low_price and good_velocity and low_amazon and 
            reasonable_oos and valid_price)


def momentum_index(row: pd.Series) -> float:
    """
    Score momentum/trend (0-100) per pricing storico
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        float: Punteggio momentum 0-100
    """
    metrics = calculate_historic_metrics(row)
    
    # Controlla validità dei dati
    if metrics['current'] <= 0:
        return 0.0
    
    base_score = 50.0
    
    # Bonus se prezzo è vicino ai minimi storici (entro 10%)
    if metrics['lowest'] > 0:
        near_low_bonus = 20 if metrics['current'] <= metrics['lowest'] * 1.1 else 0
    else:
        near_low_bonus = 0
    
    # Bonus se trend positivo recente (prezzo sale da minimo)
    # Se dev_30d > dev_90d significa che il prezzo recente è più vicino alla media
    trend_bonus = 15 if metrics['dev_30d'] > metrics['dev_90d'] else 0
    
    # Penalità se volatile (spread alto tra min/max)
    if metrics['highest'] > 0 and metrics['lowest'] > 0:
        volatility = (metrics['highest'] - metrics['lowest']) / metrics['highest']
        volatility_penalty = -10 if volatility > 0.5 else 0
    else:
        volatility_penalty = 0
    
    # Bonus se molto sotto media 90d (opportunità maggiore)
    deep_discount_bonus = 0
    if metrics['dev_90d'] < -0.20:  # >20% sotto media
        deep_discount_bonus = 10
    elif metrics['dev_90d'] < -0.15:  # >15% sotto media
        deep_discount_bonus = 5
    
    final_score = base_score + near_low_bonus + trend_bonus + volatility_penalty + deep_discount_bonus
    
    return max(0.0, min(100.0, final_score))


def risk_index(row: pd.Series) -> float:
    """
    Score rischio (0-100, più alto = meno rischio)
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        float: Punteggio rischio 0-100 (alto = sicuro)
    """
    base_score = 70.0
    
    # Penalità per return rate alto
    return_rate = row.get('Return Rate', 0)
    if pd.isna(return_rate):
        return_rate = 0
    return_penalty = -20 if return_rate > 15 else (-10 if return_rate > 10 else 0)
    
    # Penalità per rating basso
    rating = row.get('Reviews: Rating', 4.0)
    if pd.isna(rating):
        rating = 4.0
    rating_penalty = -15 if rating < 3.5 else (-5 if rating < 4.0 else 0)
    
    # Penalità per dimensioni/peso elevati (proxy: FBA fee alta)
    fba_fee = row.get('FBA Pick&Pack Fee', 2.0)
    if pd.isna(fba_fee):
        fba_fee = 2.0
    size_penalty = -10 if fba_fee > 5.0 else (-5 if fba_fee > 3.5 else 0)
    
    # Bonus per numero review alto (più dati = meno rischio)
    review_count = row.get('Reviews: Count', 0)
    if pd.isna(review_count):
        review_count = 0
    review_bonus = 10 if review_count > 1000 else (5 if review_count > 100 else 0)
    
    # Penalità per brand sconosciuto (se campo Brand è vuoto)
    brand = row.get('Brand', '')
    if pd.isna(brand) or brand == '' or brand.lower() in ['unknown', 'generic']:
        brand_penalty = -8
    else:
        brand_penalty = 0
    
    final_score = (base_score + return_penalty + rating_penalty + 
                  size_penalty + review_bonus + brand_penalty)
    
    return max(0.0, min(100.0, final_score))


def find_historic_deals(df: pd.DataFrame, params: Dict[str, float] = None) -> pd.DataFrame:
    """
    Trova tutti gli affari storici nel dataset
    
    Args:
        df: DataFrame con i dati dei prodotti
        params: Parametri per i criteri di selezione
        
    Returns:
        DataFrame con gli affari storici ordinati per opportunity score
    """
    if params is None:
        params = {'dev_90d': -0.10, 'velocity_min': 40}
    
    if df.empty:
        return pd.DataFrame()
    
    # Crea una copia per evitare modifiche al DataFrame originale
    df_copy = df.copy()
    
    # Applica le funzioni di analytics
    df_copy['is_historic_deal'] = df_copy.apply(
        lambda row: is_historic_deal(row, params), axis=1
    )
    df_copy['momentum_score'] = df_copy.apply(momentum_index, axis=1)
    df_copy['risk_score'] = df_copy.apply(risk_index, axis=1)
    
    # Aggiungi metriche storiche per debugging/analysis
    historic_metrics = df_copy.apply(calculate_historic_metrics, axis=1)
    df_copy['price_deviation_90d'] = historic_metrics.apply(lambda x: x['dev_90d'])
    df_copy['current_vs_avg_90d'] = historic_metrics.apply(
        lambda x: f"{x['current']:.2f} vs {x['avg_90d']:.2f}" if x['avg_90d'] > 0 else "N/A"
    )
    
    # Filtra solo gli affari storici
    historic_deals = df_copy[df_copy['is_historic_deal'] == True].copy()
    
    if historic_deals.empty:
        return historic_deals
    
    # Calcola opportunity score se non presente
    if 'opportunity_score' not in historic_deals.columns:
        # Import scoring functions se necessario
        from scoring import profit_score, competition_index
        
        # Calcola un opportunity score semplificato
        historic_deals['velocity_score'] = historic_deals.apply(velocity_index, axis=1)
        historic_deals['competition_score'] = historic_deals.apply(competition_index, axis=1)
        
        # Usa metriche esistenti per calcolare profit score approssimativo
        historic_deals['estimated_profit_score'] = 60  # placeholder
        
        # Opportunity score semplificato
        historic_deals['opportunity_score'] = (
            historic_deals['velocity_score'] * 0.3 +
            historic_deals['momentum_score'] * 0.3 +
            historic_deals['risk_score'] * 0.2 +
            historic_deals['competition_score'] * 0.2
        )
    
    # Ordina per opportunity score decrescente
    historic_deals = historic_deals.sort_values('opportunity_score', ascending=False)
    
    return historic_deals


def validate_historic_data(row: pd.Series) -> Dict[str, bool]:
    """
    Valida la presenza e qualità dei dati storici
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        Dict con risultati della validazione
    """
    required_columns = [
        'Buy Box 🚚: Current',
        'Buy Box 🚚: 30 days avg.',
        'Buy Box 🚚: 90 days avg.',
        'Buy Box 🚚: Lowest',
        'Buy Box 🚚: Highest'
    ]
    
    validation_results = {}
    
    for col in required_columns:
        value = row.get(col)
        validation_results[col] = not (pd.isna(value) or value <= 0)
    
    # Calcola score complessivo di qualità dati
    valid_count = sum(validation_results.values())
    validation_results['data_quality_score'] = valid_count / len(required_columns)
    validation_results['has_sufficient_data'] = validation_results['data_quality_score'] >= 0.6
    
    return validation_results


def analyze_price_trends(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analizza i trend di prezzo nel dataset
    
    Args:
        df: DataFrame con i dati dei prodotti
        
    Returns:
        Dict con statistiche sui trend
    """
    if df.empty:
        return {'products_analyzed': 0}
    
    trends_data = []
    
    for _, row in df.iterrows():
        metrics = calculate_historic_metrics(row)
        
        if metrics['current'] > 0:
            trends_data.append({
                'asin': row.get('ASIN', ''),
                'current_price': metrics['current'],
                'dev_30d': metrics['dev_30d'],
                'dev_90d': metrics['dev_90d'],
                'dev_180d': metrics['dev_180d'],
                'price_range': metrics['highest'] - metrics['lowest'] if metrics['highest'] > metrics['lowest'] else 0
            })
    
    if not trends_data:
        return {'products_analyzed': 0}
    
    trends_df = pd.DataFrame(trends_data)
    
    # Statistiche sui trend
    analysis = {
        'products_analyzed': len(trends_df),
        'avg_deviation_30d': trends_df['dev_30d'].mean(),
        'avg_deviation_90d': trends_df['dev_90d'].mean(),
        'avg_deviation_180d': trends_df['dev_180d'].mean(),
        'products_below_90d_avg': len(trends_df[trends_df['dev_90d'] < 0]),
        'products_significantly_below': len(trends_df[trends_df['dev_90d'] < -0.10]),
        'avg_price_range': trends_df['price_range'].mean(),
        'median_current_price': trends_df['current_price'].median()
    }
    
    # Percentuali
    total = analysis['products_analyzed']
    if total > 0:
        analysis['pct_below_90d_avg'] = analysis['products_below_90d_avg'] / total * 100
        analysis['pct_significantly_below'] = analysis['products_significantly_below'] / total * 100
    else:
        analysis['pct_below_90d_avg'] = 0
        analysis['pct_significantly_below'] = 0
    
    return analysis


def get_deal_quality_score(row: pd.Series) -> float:
    """
    Calcola un punteggio di qualità complessivo per un affare storico
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        float: Punteggio qualità 0-100
    """
    if not is_historic_deal(row):
        return 0.0
    
    # Componenti del punteggio
    momentum = momentum_index(row)
    risk = risk_index(row)
    velocity = velocity_index(row)
    
    # Metriche storiche
    metrics = calculate_historic_metrics(row)
    
    # Bonus per sconto profondo
    discount_bonus = 0
    if metrics['dev_90d'] < -0.20:
        discount_bonus = 15
    elif metrics['dev_90d'] < -0.15:
        discount_bonus = 10
    elif metrics['dev_90d'] < -0.10:
        discount_bonus = 5
    
    # Punteggio finale pesato
    quality_score = (
        momentum * 0.25 +
        risk * 0.25 +
        velocity * 0.25 +
        50 * 0.25  # base score component
    ) + discount_bonus
    
    return max(0.0, min(100.0, quality_score))


def detect_historic_deals(df):
    """
    Identifica opportunità eccezionali basate su pattern storici
    """
    historic_deals = []
    
    for _, row in df.iterrows():
        signals = 0
        deal_info = {
            'asin': row.get('ASIN', ''),
            'title': row.get('Title', ''),
            'signals': [],
            'signal_count': 0
        }
        
        # Signal 1: Prezzo al minimo storico
        current_price = row.get('Buy Box 🚚: Current', 0)
        lowest_price = row.get('Buy Box 🚚: Lowest', 0)
        if current_price > 0 and lowest_price > 0 and current_price <= lowest_price * 1.05:
            signals += 2
            deal_info['signals'].append('Near historic low price')
            
        # Signal 2: Amazon fuori stock
        amazon_oos = row.get('Amazon: 90 days OOS', 0)
        if pd.notna(amazon_oos) and amazon_oos > 50:
            signals += 2
            deal_info['signals'].append('Amazon frequently out of stock')
            
        # Signal 3: Alta stabilità prezzi (bassa volatilità)
        std_dev = row.get('Buy Box: Standard Deviation 30 days', 0)
        avg_30d = row.get('Buy Box 🚚: 30 days avg.', 1)
        if std_dev > 0 and avg_30d > 0 and std_dev < avg_30d * 0.05:
            signals += 1
            deal_info['signals'].append('Low price volatility')
            
        # Signal 4: Rank in miglioramento
        current_rank = row.get('Sales Rank: Current', 999999)
        avg_rank_30d = row.get('Sales Rank: 30 days avg.', current_rank)
        if current_rank > 0 and avg_rank_30d > 0 and current_rank < avg_rank_30d * 0.8:
            signals += 1
            deal_info['signals'].append('Improving sales rank')
            
        # Signal 5: Pochi competitor
        winner_count = row.get('Buy Box: Winner Count 30 days', row.get('Buy Box: Winner Count', 10))
        if pd.notna(winner_count) and winner_count < 5:
            signals += 1
            deal_info['signals'].append('Low competition')
            
        # Signal 6: Prezzo sotto media 90d significativo
        avg_90d = row.get('Buy Box 🚚: 90 days avg.', current_price)
        if current_price > 0 and avg_90d > 0:
            discount_pct = (avg_90d - current_price) / avg_90d
            if discount_pct > 0.15:  # >15% sotto media
                signals += 2
                deal_info['signals'].append(f'Significant discount vs 90d avg ({discount_pct:.1%})')
            elif discount_pct > 0.10:  # >10% sotto media
                signals += 1
                deal_info['signals'].append(f'Good discount vs 90d avg ({discount_pct:.1%})')
        
        # Signal 7: Alta qualità prodotto
        rating = row.get('Reviews: Rating', 0)
        review_count = row.get('Reviews: Rating Count', 0)
        if rating >= 4.0 and review_count >= 100:
            signals += 1
            deal_info['signals'].append('High quality product')
        
        # Signal 8: Bassa dominanza Amazon
        amazon_share = row.get('Buy Box: % Amazon 90 days', 100)
        if pd.notna(amazon_share) and amazon_share < 60:
            signals += 1
            deal_info['signals'].append('Low Amazon dominance')
        
        # Soglia per considerare un "historic deal"
        if signals >= 4:
            deal_info['signal_count'] = signals
            deal_info['current_price'] = current_price
            deal_info['avg_90d_price'] = avg_90d
            deal_info['lowest_price'] = lowest_price
            deal_info['discount_vs_90d'] = (avg_90d - current_price) / avg_90d if avg_90d > 0 else 0
            deal_info['sales_rank'] = current_rank
            deal_info['rating'] = rating
            deal_info['review_count'] = review_count
            
            # Calcola score qualità
            deal_info['quality_score'] = min(100, signals * 15)  # Max 100
            
            historic_deals.append(deal_info)
    
    # Converte in DataFrame e ordina per signal count e quality score
    if historic_deals:
        deals_df = pd.DataFrame(historic_deals)
        deals_df = deals_df.sort_values(['signal_count', 'quality_score'], ascending=[False, False])
        return deals_df
    else:
        return pd.DataFrame()


def analyze_deal_patterns(df):
    """
    Analizza pattern comuni negli affari storici rilevati
    """
    deals = detect_historic_deals(df)
    
    if deals.empty:
        return {
            'total_deals': 0,
            'patterns': {},
            'summary': 'No historic deals detected'
        }
    
    # Analizza pattern comuni
    patterns = {}
    
    # Pattern 1: Distribuzione segnali
    signal_distribution = {}
    for _, deal in deals.iterrows():
        for signal in deal['signals']:
            signal_distribution[signal] = signal_distribution.get(signal, 0) + 1
    
    patterns['signal_frequency'] = signal_distribution
    
    # Pattern 2: Range di prezzi
    patterns['price_stats'] = {
        'avg_current_price': deals['current_price'].mean(),
        'avg_discount_vs_90d': deals['discount_vs_90d'].mean(),
        'min_signals': deals['signal_count'].min(),
        'max_signals': deals['signal_count'].max(),
        'avg_quality_score': deals['quality_score'].mean()
    }
    
    # Pattern 3: Qualità prodotti
    high_quality_deals = deals[(deals['rating'] >= 4.0) & (deals['review_count'] >= 100)]
    patterns['quality_analysis'] = {
        'high_quality_deals': len(high_quality_deals),
        'pct_high_quality': len(high_quality_deals) / len(deals) * 100,
        'avg_rating_all_deals': deals['rating'].mean(),
        'avg_reviews_all_deals': deals['review_count'].mean()
    }
    
    return {
        'total_deals': len(deals),
        'patterns': patterns,
        'deals_data': deals,
        'summary': f'Found {len(deals)} historic deals with avg {deals["signal_count"].mean():.1f} signals each'
    }


def generate_risk_recommendation(risk_level):
    """
    Genera raccomandazioni basate sul livello di rischio Amazon
    """
    recommendations = {
        'CRITICAL': "⛔ AVOID - Amazon domina completamente questo mercato. Rischio altissimo di price war.",
        'HIGH': "⚠️ CAUTION - Alta probabilità di competizione Amazon. Considera solo con margini molto alti.",
        'MEDIUM': "🟡 MONITOR - Competizione Amazon moderata. Monitora attentamente i prezzi Amazon.",
        'LOW': "✅ PROCEED - Bassa presenza Amazon. Buona opportunità di arbitraggio."
    }
    return recommendations.get(risk_level, "Unknown risk level")


def assess_amazon_competition_risk(row):
    """
    Valuta rischio competizione Amazon
    """
    # Estrai dati con fallback sicuri
    amazon_dominance = row.get('Buy Box: % Amazon 365 days', row.get('Buy Box: % Amazon 90 days', 0))
    amazon_oos_count = row.get('Amazon: OOS Count 90 days', 0)
    amazon_avg_price = row.get('Amazon: 365 days avg.', row.get('Amazon: Current', 999999))
    current_buybox = row.get('Buy Box 🚚: Current', 0)
    prime_eligible = row.get('Prime Eligible (Buy Box)', 'No')
    
    # Gestione valori NaN
    if pd.isna(amazon_dominance):
        amazon_dominance = 0
    if pd.isna(amazon_oos_count):
        amazon_oos_count = 0
    if pd.isna(amazon_avg_price):
        amazon_avg_price = 999999
    if pd.isna(current_buybox):
        current_buybox = 0
    if pd.isna(prime_eligible):
        prime_eligible = 'No'
    
    risk_factors = {
        'amazon_dominance': amazon_dominance > 60,
        'frequent_restocks': amazon_oos_count < 5,
        'price_matching': abs(amazon_avg_price - current_buybox) < 10 if amazon_avg_price < 999999 and current_buybox > 0 else False,
        'prime_exclusive': prime_eligible == 'Yes' and amazon_dominance > 40
    }
    
    risk_score = sum(risk_factors.values()) * 25  # 0-100
    
    risk_level = (
        'CRITICAL' if risk_score >= 75 else
        'HIGH' if risk_score >= 50 else
        'MEDIUM' if risk_score >= 25 else
        'LOW'
    )
    
    return {
        'score': risk_score,
        'level': risk_level,
        'factors': risk_factors,
        'recommendation': generate_risk_recommendation(risk_level),
        'details': {
            'amazon_dominance_pct': amazon_dominance,
            'amazon_oos_count': amazon_oos_count,
            'price_difference': abs(amazon_avg_price - current_buybox) if amazon_avg_price < 999999 and current_buybox > 0 else None,
            'prime_eligible': prime_eligible
        }
    }