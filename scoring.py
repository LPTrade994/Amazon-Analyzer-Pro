"""
Opportunity Score System

Calcola un punteggio 0-100 combinando 6 componenti con pesi configurabili.
"""

import pandas as pd
import numpy as np
import math
import streamlit as st
from typing import Dict, Any, Union
from config import SCORING_WEIGHTS

@st.cache_data(ttl=1800)  # Cache for 30 min
def compute_opportunity_scores_cached(df_csv: str, weights_dict: Dict[str, float]) -> pd.Series:
    """
    Cached computation of opportunity scores for entire DataFrame
    
    Args:
        df_csv: DataFrame as CSV string for caching
        weights_dict: Scoring weights dictionary
        
    Returns:
        pd.Series: Opportunity scores for each row
    """
    from io import StringIO
    df = pd.read_csv(StringIO(df_csv))
    
    scores = []
    for _, row in df.iterrows():
        # Calculate individual scores
        profit_sc = profit_score(
            safe_numeric(row.get('gross_margin_pct', 0)),
            safe_numeric(row.get('roi', 0))
        )
        velocity_sc = velocity_index(row)
        competition_sc = competition_index(row)
        
        # Calculate final opportunity score
        opp_score = opportunity_score(profit_sc, velocity_sc, competition_sc, weights_dict)
        scores.append(opp_score)
    
    return pd.Series(scores, index=df.index)

def safe_numeric(value, default=0.0):
    """
    Conversione ultra-sicura per scoring - GARANTISCE sempre ritorno di float
    
    Args:
        value: Any value to convert
        default: Default value if conversion fails
        
    Returns:
        float: Converted numeric value or default (SEMPRE float)
    """
    # GARANTISCE sempre ritorno di float
    try:
        if pd.isna(value) or value is None:
            return float(default)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Gestisci casi problematici specifici
            if value.lower() in ['null', 'none', 'nan', '']:
                return float(default)
            
            # Pulizia robusta
            clean_val = value.replace('€', '').strip()
            
            # Gestisci virgole: se ci sono più di una virgola o punto, è probabilmente separatore migliaia
            if ',' in clean_val and '.' in clean_val:
                # Formato tipo "1,234.56"
                clean_val = clean_val.replace(',', '')
            elif ',' in clean_val and clean_val.count(',') == 1 and len(clean_val.split(',')[1]) <= 2:
                # Formato europeo tipo "1234,56"
                clean_val = clean_val.replace(',', '.')
            elif ',' in clean_val:
                # Separatore migliaia tipo "1,234"
                clean_val = clean_val.replace(',', '')
                
            if clean_val == '':
                return float(default)
            return float(clean_val)
        return float(default)
    except:
        # FALLBACK ASSOLUTO
        return float(default)


def velocity_index(row: pd.Series) -> float:
    """
    Liquidità/Domanda (0-100) con type safety
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        float: Punteggio velocità 0-100
    """
    try:
        # SAFE numeric extraction
        sales_rank = safe_numeric(row.get('Sales Rank: Current', 999999))
        rating = safe_numeric(row.get('Reviews: Rating', 0.0))
        bought_month = safe_numeric(row.get('Bought in past month', 0))
        
        # Base score da sales rank (invertito)
        if sales_rank <= 0:
            rank_score = 0
        elif sales_rank >= 500000:
            rank_score = 10  # Molto basso
        else:
            # Scala logaritmica: rank 1 = 100, rank 100000 = 30
            rank_score = max(10, 100 - (math.log10(sales_rank) * 15))
        
        # Bonus rating
        rating_bonus = max(0, (rating - 3.0) * 10) if rating > 3.0 else 0
        
        # Bonus vendite
        sales_bonus = min(20, bought_month * 0.5) if bought_month > 0 else 0
        
        final_score = rank_score + rating_bonus + sales_bonus
        return max(0, min(100, final_score))
        
    except Exception as e:
        # Fallback sicuro
        return 50.0


def competition_index(row: pd.Series) -> float:
    """
    Dinamiche Buy Box (0-100, più alto = meno competizione) con type safety
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        float: Punteggio competizione 0-100
    """
    try:
        # SAFE numeric extraction
        amazon_pct = safe_numeric(row.get('Buy Box: % Amazon 90 days', 50))
        winner_count = safe_numeric(row.get('Buy Box: Winner Count', 5))
        oos_pct = safe_numeric(row.get('Buy Box: 90 days OOS', 0))
        
        score = 50.0  # Base score
        
        # Penalità per dominanza Amazon
        if amazon_pct > 70:
            score -= 30
        elif amazon_pct > 50:
            score -= 15
        
        # Penalità per troppi competitor
        if winner_count > 10:
            score -= 20
        elif winner_count > 5:
            score -= 10
        
        # Bonus per Out of Stock (opportunità)
        if oos_pct > 10:
            bonus = min(15, (oos_pct - 10) * 0.5)
            score += bonus
        
        return max(0.0, min(100.0, score))
        
    except Exception as e:
        # Fallback sicuro
        return 50.0


def profit_score(gross_margin_pct: float, roi_pct: float) -> float:
    """
    Score profitto (0-100) con type safety
    
    Args:
        gross_margin_pct: Percentuale margine lordo
        roi_pct: Percentuale ROI
        
    Returns:
        float: Punteggio profitto 0-100
    """
    try:
        # SAFE numeric extraction
        roi = safe_numeric(roi_pct, 0.0)
        margin = safe_numeric(gross_margin_pct, 0.0)
        
        # ROI base score (target 60% ROI = 70 punti)
        roi_score = max(0, min(1, roi / 0.60)) * 70
        
        # Penalità per ROI negativo
        if roi < 0:
            roi_score -= 40
        
        # Bonus margine
        margin_bonus = 0
        if margin > 0.35:  # >35%
            margin_bonus = 30
        elif margin > 0.25:  # >25%
            margin_bonus = 15
        
        total_score = roi_score + margin_bonus
        
        return max(0.0, min(100.0, total_score))
        
    except Exception as e:
        # Fallback sicuro
        return 30.0


def opportunity_score(
    profit_score: float, 
    velocity: float, 
    competition: float, 
    weights: Dict[str, float] = None
) -> float:
    """
    Score finale con pesi configurabili
    
    Formula: weights['profit']*profit + weights['velocity']*velocity + weights['competition']*competition
    Per ora usa solo questi 3 componenti (momentum, risk, ops verranno dopo)
    
    Args:
        profit_score: Punteggio profitto 0-100
        velocity: Punteggio velocità 0-100
        competition: Punteggio competizione 0-100
        weights: Dict con pesi per ogni componente (default da config.py)
        
    Returns:
        float: Score finale 0-100
    """
    if weights is None:
        weights = SCORING_WEIGHTS
    
    # Normalizza i pesi per i soli componenti attualmente utilizzati
    total_weight = weights['profit'] + weights['velocity'] + weights['competition']
    
    if total_weight == 0:
        return 0.0
    
    # Calcola score pesato
    weighted_score = (
        (weights['profit'] / total_weight) * profit_score +
        (weights['velocity'] / total_weight) * velocity +
        (weights['competition'] / total_weight) * competition
    )
    
    return max(0.0, min(100.0, weighted_score))


def explain_score(score_components: Dict[str, Any]) -> str:
    """
    Genera spiegazione human-readable del punteggio
    
    Args:
        score_components: Dict contenente tutti i componenti del score
        
    Returns:
        str: Spiegazione dettagliata del punteggio
    """
    profit = score_components.get('profit_score', 0)
    velocity = score_components.get('velocity', 0) 
    competition = score_components.get('competition', 0)
    final_score = score_components.get('final_score', 0)
    
    explanation = f"Opportunity Score: {final_score:.1f}/100\n\n"
    
    # Profit analysis
    explanation += f"Profitto: {profit:.1f}/100 "
    if profit >= 80:
        explanation += "(Eccellente - ROI molto alto)\n"
    elif profit >= 60:
        explanation += "(Buono - ROI solido)\n"
    elif profit >= 40:
        explanation += "(Moderato - ROI accettabile)\n"
    else:
        explanation += "(Basso - ROI insufficiente)\n"
    
    # Velocity analysis
    explanation += f"Velocita: {velocity:.1f}/100 "
    if velocity >= 80:
        explanation += "(Ottima liquidita - vendite rapide)\n"
    elif velocity >= 60:
        explanation += "(Buona liquidita - vendite regolari)\n"
    elif velocity >= 40:
        explanation += "(Liquidita moderata)\n"
    else:
        explanation += "(Bassa liquidita - vendite lente)\n"
    
    # Competition analysis  
    explanation += f"Competizione: {competition:.1f}/100 "
    if competition >= 80:
        explanation += "(Bassa competizione - buone opportunita)\n"
    elif competition >= 60:
        explanation += "(Competizione moderata)\n"
    elif competition >= 40:
        explanation += "(Competizione alta)\n"
    else:
        explanation += "(Competizione molto alta - difficile entrare)\n"
    
    # Overall recommendation
    explanation += f"\nValutazione finale: "
    if final_score >= 80:
        explanation += "Opportunita eccellente"
    elif final_score >= 60:
        explanation += "Opportunita buona"
    elif final_score >= 40:
        explanation += "Opportunita moderata"
    else:
        explanation += "Opportunita scarsa"
    
    return explanation


def calculate_product_score(row: pd.Series) -> Dict[str, float]:
    """
    Calcola tutti i componenti del punteggio per un singolo prodotto
    
    Args:
        row: Pandas Series con i dati del prodotto
        
    Returns:
        Dict contenente tutti i punteggi calcolati
    """
    # Calcola i componenti base
    velocity = velocity_index(row)
    competition = competition_index(row)
    
    # Estrai margine e ROI per il profit score
    gross_margin = row.get('Gross Margin %', 0) / 100 if pd.notna(row.get('Gross Margin %')) else 0
    roi = row.get('ROI %', 0) / 100 if pd.notna(row.get('ROI %')) else 0
    profit = profit_score(gross_margin, roi)
    
    # Calcola score finale
    final_score = opportunity_score(profit, velocity, competition)
    
    return {
        'velocity': velocity,
        'competition': competition, 
        'profit_score': profit,
        'final_score': final_score,
        'gross_margin_pct': gross_margin * 100,
        'roi_pct': roi * 100
    }


def calculate_rank_score(sales_rank: float) -> float:
    """
    Calcola punteggio basato su sales rank
    
    Args:
        sales_rank: Current sales rank
        
    Returns:
        float: Score 0-100 basato su sales rank
    """
    try:
        rank = safe_numeric(sales_rank, 999999)
        
        if rank <= 0:
            return 0.0
        elif rank >= 500000:
            return 10.0  # Molto basso
        else:
            # Scala logaritmica: rank 1 = 100, rank 100000 = 30
            return max(10.0, 100.0 - (math.log10(rank) * 15))
            
    except Exception:
        return 30.0


def calculate_enhanced_score(row, weights):
    """
    Score Components basati su dati Keepa disponibili:
    """
    
    # 1. PROFITABILITY (35% peso)
    roi_score = min(safe_numeric(row.get('roi', 0)) / 50 * 100, 100)  # Cap at 50% ROI
    
    # 2. PRICE STABILITY (25% peso) - NUOVO
    std_dev = safe_numeric(row.get('Buy Box: Standard Deviation 30 days', 0))
    avg_30d = safe_numeric(row.get('Buy Box 🚚: 30 days avg.', 1))
    
    if avg_30d > 0:
        price_cv = std_dev / avg_30d
        stability_score = max(0, 100 - (price_cv * 500))  # CV < 20% = good
    else:
        stability_score = 50.0  # Default when no data
    
    # 3. SALES VELOCITY (20% peso)
    rank_score = calculate_rank_score(safe_numeric(row.get('Sales Rank: Current', 999999)))
    rank_current = safe_numeric(row.get('Sales Rank: Current', 999999))
    rank_30d_avg = safe_numeric(row.get('Sales Rank: 30 days avg.', rank_current))
    
    if rank_30d_avg > 0:
        rank_trend = (rank_30d_avg - rank_current) / rank_30d_avg
        velocity_score = (rank_score * 0.7) + (rank_trend * 100 * 0.3)
    else:
        velocity_score = rank_score
    
    # 4. COMPETITION RISK (10% peso) - NUOVO
    amazon_pct = safe_numeric(row.get('Buy Box: % Amazon 365 days', row.get('Buy Box: % Amazon 90 days', 50)))
    amazon_risk = 100 - min(amazon_pct, 100)
    winner_count = safe_numeric(row.get('Buy Box: Winner Count 30 days', row.get('Buy Box: Winner Count', 5)))
    winner_diversity = min(winner_count / 10 * 100, 100)
    competition_score = (amazon_risk * 0.6) + (winner_diversity * 0.4)
    
    # 5. PRODUCT QUALITY (10% peso)
    rating = safe_numeric(row.get('Reviews: Rating', 0))
    rating_score = (rating / 5) * 100
    review_count = safe_numeric(row.get('Reviews: Rating Count', 0))
    review_count_score = min(review_count / 100, 1) * 100
    quality_score = (rating_score * 0.7) + (review_count_score * 0.3)
    
    # Calcolo finale con pesi configurabili
    final_score = (
        roi_score * weights.get('profitability', 0.35) +
        stability_score * weights.get('stability', 0.25) +
        velocity_score * weights.get('velocity', 0.20) +
        competition_score * weights.get('competition', 0.10) +
        quality_score * weights.get('quality', 0.10)
    )
    
    return {
        'total_score': max(0.0, min(100.0, final_score)),
        'components': {
            'profitability': max(0.0, min(100.0, roi_score)),
            'stability': max(0.0, min(100.0, stability_score)),
            'velocity': max(0.0, min(100.0, velocity_score)),
            'competition': max(0.0, min(100.0, competition_score)),
            'quality': max(0.0, min(100.0, quality_score))
        }
    }