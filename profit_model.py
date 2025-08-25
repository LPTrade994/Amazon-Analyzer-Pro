"""
Profit Model System

Calcola metriche economiche complete integrando pricing.py e scoring.py.
"""

import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, Any, List, Tuple
from config import SCORING_WEIGHTS, VAT_RATES, DEFAULT_DISCOUNT, HIDDEN_COSTS
from pricing import select_purchase_price, select_target_price, compute_net_purchase
from scoring import profit_score, velocity_index, competition_index, opportunity_score

@st.cache_data(ttl=1800)  # Cache for 30 min
def calculate_all_routes_cached(df_csv: str, discount: float, strategy: str, scenario: str, mode: str, min_roi: float, min_margin: float) -> pd.DataFrame:
    """
    Cached calculation of all cross-market routes
    
    Args:
        df_csv: DataFrame as CSV string for caching
        discount: Purchase discount
        strategy: Purchase strategy  
        scenario: Pricing scenario
        mode: FBA/FBM mode
        min_roi: Minimum ROI threshold
        min_margin: Minimum margin threshold
        
    Returns:
        pd.DataFrame: Best routes results
    """
    # Reconstruct DataFrame from CSV
    from io import StringIO
    df = pd.read_csv(StringIO(df_csv))
    
    # Recreate params
    params = {
        'purchase_strategy': strategy,
        'scenario': scenario,
        'mode': mode,
        'discount': discount,
        'min_roi_pct': min_roi,
        'min_margin_pct': min_margin,
        'inbound_logistics': 2.0,
        'scoring_weights': SCORING_WEIGHTS
    }
    
    # Call the actual computation
    return find_best_routes_internal(df, params)

def compute_fees(row: pd.Series, sale_price: float, target_locale: str, mode: str = 'FBA') -> Dict[str, float]:
    """
    Calcola TUTTE le fees Amazon correttamente
    """
    if sale_price <= 0:
        return {'referral': 0.0, 'fba': 0.0, 'shipping': 0.0, 'total': 0.0}
    
    # REFERRAL FEE - SEMPRE 15% del prezzo di vendita
    # Non importa cosa dice il dataset, usa sempre 15%
    referral_fee = sale_price * 0.15
    
    # FBA fees (fulfillment)
    if mode == 'FBA':
        # Usa il valore dal dataset o default €3
        fba_fee = float(row.get('FBA Pick&Pack Fee', 3.0))
        shipping_cost = 0  # Incluso in FBA
    else:  # FBM
        fba_fee = 0
        # Calcola shipping per FBM
        weight = row.get('Weight', 0.5)
        if weight < 1:
            shipping_cost = 4.5
        elif weight < 3:
            shipping_cost = 6.5
        else:
            shipping_cost = 9.5
    
    return {
        'referral': referral_fee,
        'fba': fba_fee,
        'shipping': shipping_cost,
        'total': referral_fee + fba_fee + shipping_cost
    }


def compute_route_metrics(
    row: pd.Series, 
    source_locale: str, 
    target_locale: str, 
    params: Dict[str, Any],
    custom_target_price: float = None
) -> Dict[str, Any]:
    """
    Calcola metriche complete per rotta Source→Target
    CON CALCOLI REALI COME AMAZON REVENUE CALCULATOR
    """
    # Usa pricing.py per calcolare costi di acquisto
    purchase_price = select_purchase_price(row, params['purchase_strategy'])
    
    if purchase_price <= 0:
        return {
            'source': source_locale,
            'target': target_locale,
            'purchase_price': 0.0,
            'net_cost': 0.0,
            'target_price': 0.0,
            'fees': {'referral': 0.0, 'fba': 0.0, 'shipping': 0.0, 'total': 0.0},
            'gross_margin_eur': 0.0,
            'gross_margin_pct': 0.0,
            'roi': 0.0,
            'net_profit': 0.0,
            'opportunity_score': 0.0,
            'profit_score': 0.0,
            'velocity_score': 0.0,
            'competition_score': 0.0
        }
    
    # CALCOLO COSTO NETTO CORRETTO
    discount = params.get('discount', 0.21)  # 21% sconto
    source_vat = VAT_RATES.get(source_locale, 0.19)  # IVA source (DE=19%)
    
    # Formula corretta: (prezzo * (1-sconto)) / (1+IVA)
    net_cost = (purchase_price * (1 - discount)) / (1 + source_vat)
    
    # Target price
    if custom_target_price is not None:
        target_price = custom_target_price
    else:
        scenario = params.get('scenario', 'current')
        target_price = select_target_price(row, target_locale, scenario)
    
    if target_price <= 0:
        return {
            'source': source_locale,
            'target': target_locale,
            'purchase_price': purchase_price,
            'net_cost': net_cost,
            'target_price': 0.0,
            'fees': {'referral': 0.0, 'fba': 0.0, 'shipping': 0.0, 'total': 0.0},
            'gross_margin_eur': 0.0,
            'gross_margin_pct': 0.0,
            'roi': 0.0,
            'net_profit': 0.0,
            'opportunity_score': 0.0,
            'profit_score': 0.0,
            'velocity_score': 0.0,
            'competition_score': 0.0
        }
    
    # AGGIUNGI TUTTI I COSTI REALI
    inbound_shipping = params.get('inbound_logistics', 5.0)  # €5 come da tuo esempio
    
    # Fees Amazon (referral + FBA)
    mode = params.get('mode', 'FBA')
    fees = compute_fees(row, target_price, target_locale, mode)
    
    # IMPORTANTE: Amazon Calculator usa target_price_ex_vat per il calcolo delle fees
    # Questo riduce le fees totali
    target_vat = 0.22 if target_locale == 'it' else 0.19  # IT=22%, DE=19%
    target_price_ex_vat = target_price / (1 + target_vat)  # Prezzo senza VAT
    
    # Ricalcola fees sul prezzo ex-VAT per essere più accurati
    fees_ex_vat = compute_fees(row, target_price_ex_vat, target_locale, mode)
    
    # Costi aggiuntivi più conservativi per allinearsi ad Amazon Calculator
    returns_cost = target_price_ex_vat * 0.015  # 1.5% resi (più conservativo)
    storage_cost = target_price_ex_vat * 0.003  # 0.3% storage (più conservativo) 
    misc_costs = 0.25  # Altri costi operativi ridotti ulteriormente
    
    # CALCOLO TOTALE COSTI (come Amazon Seller Central)
    total_costs = (
        net_cost +                    # Costo prodotto dopo sconto e IVA
        inbound_shipping +            # Spedizione verso Amazon (€5)
        fees_ex_vat['referral'] +     # Referral fee su prezzo ex-VAT
        fees_ex_vat['fba'] +          # FBA fee su prezzo ex-VAT
        returns_cost +               # Perdite da resi
        storage_cost +               # Storage mensile
        misc_costs                   # Altri costi
    )
    
    # PROFITTO REALE (target_price_ex_vat già calcolato sopra)
    real_profit = target_price_ex_vat - total_costs
    
    # ROI REALE (basato su investimento iniziale)
    investment = net_cost + inbound_shipping
    real_roi = (real_profit / investment * 100) if investment > 0 else 0
    
    # MARGINE % SUL REVENUE
    real_margin_pct = (real_profit / target_price * 100) if target_price > 0 else 0
    
    # Scoring
    profit_sc = profit_score(real_margin_pct, real_roi)
    velocity_sc = velocity_index(row)
    competition_sc = competition_index(row)
    
    scoring_weights = params.get('scoring_weights', SCORING_WEIGHTS)
    opp_score = opportunity_score(profit_sc, velocity_sc, competition_sc, scoring_weights)
    
    # IMPORTANTE: Restituisci i valori NEI CAMPI GIUSTI!
    return {
        'source': source_locale,
        'target': target_locale,
        'purchase_price': purchase_price,
        'net_cost': net_cost,  # Costo netto dopo sconto/IVA
        'target_price': target_price,
        'fees': fees,
        
        # QUESTI SONO I CAMPI CRITICI - DEVONO ESSERE CORRETTI!
        'gross_margin_eur': real_profit,  # <-- PROFITTO REALE QUI
        'gross_margin_pct': real_margin_pct,
        'roi': real_roi,
        'net_profit': real_profit,  # Duplicato per compatibilità
        
        # Totali per debug
        'total_cost': total_costs,
        'investment': investment,
        
        # Breakdown dettagliato per debug
        'cost_breakdown': {
            'product_net_cost': net_cost,
            'inbound_shipping': inbound_shipping,
            'referral_fee': fees_ex_vat['referral'],
            'fba_fee': fees_ex_vat.get('fba', 0),
            'returns_cost': returns_cost,
            'storage_cost': storage_cost,
            'misc_costs': misc_costs,
            'total_costs': total_costs
        },
        
        # Scores
        'opportunity_score': opp_score,
        'profit_score': profit_sc,
        'velocity_score': velocity_sc,
        'competition_score': competition_sc
    }


def find_best_routes_internal(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    CROSS-MARKET ARBITRAGE: Trova migliori rotte per arbitraggio tra mercati
    
    Args:
        df: DataFrame con dati prodotti multi-mercato
        params: Parametri di configurazione
        
    Returns:
        DataFrame con migliori opportunità di arbitraggio per ASIN
    """
    from config import CROSS_MARKET_MARKUP, DEBUG_MODE
    import streamlit as st
    
    if DEBUG_MODE:
        st.write(f"find_best_routes_internal: Starting with {len(df)} products")
        st.write(f"Available params: {list(params.keys())}")
        st.write(f"Min thresholds: ROI {params.get('min_roi_pct', 0)}%, Margin {params.get('min_margin_pct', 0)}%")
    
    # Raggruppa per ASIN per trovare disponibilità multi-mercato
    asin_groups = df.groupby('ASIN')
    
    if DEBUG_MODE:
        st.write(f"Found {len(asin_groups)} ASIN groups to process")
    
    best_routes = []
    processed_asins = 0
    
    for asin, group in asin_groups:
        processed_asins += 1
        # Mercati dove è disponibile questo ASIN
        available_markets = group['source_market'].unique()
        
        if len(available_markets) < 2:
            continue  # Skip single-market products
        
        if DEBUG_MODE and processed_asins <= 1:  # Debug only first ASIN
            st.write(f"ASIN {asin}: Available in {len(available_markets)} markets: {list(available_markets)}")
            
        best_opportunity = None
        best_score = 0
        routes_tested = 0
        
        # TEST TUTTE LE COMBINAZIONI source -> target per cross-market arbitrage
        for source_market in available_markets:
            source_row = group[group['source_market'] == source_market].iloc[0]
            source_price = select_purchase_price(source_row, params['purchase_strategy'])
            
            if source_price <= 0:
                if DEBUG_MODE and processed_asins <= 1:
                    st.write(f"  {source_market}: No valid source price")
                continue  # Skip se no prezzo valido
                
            if DEBUG_MODE and processed_asins <= 1:
                st.write(f"  {source_market}: Source price €{source_price}")
                
            for target_market in ['it', 'de', 'fr', 'es']:
                if target_market == source_market.lower():
                    continue  # Skip same market
                
                routes_tested += 1
                
                # CRITICAL: Use target market price if available
                target_price = None
                if target_market in [m.lower() for m in available_markets]:
                    # ASIN disponibile anche nel mercato target - usa prezzo reale
                    target_row = group[group['source_market'] == target_market].iloc[0]
                    target_price = select_purchase_price(target_row, params['purchase_strategy'])
                else:
                    # ASIN NON disponibile nel target - stima prezzo con markup
                    markup = CROSS_MARKET_MARKUP.get(target_market, 1.05)
                    target_price = source_price * markup
                
                if DEBUG_MODE and processed_asins <= 1:
                    st.write(f"    Route {source_market}->{target_market}: source €{source_price}, target €{target_price}")
                
                if target_price <= source_price:
                    if DEBUG_MODE and processed_asins <= 1:
                        st.write(f"    → No arbitrage (target <= source)")
                    continue  # No arbitrage opportunity
                
                try:
                    # Calculate route metrics with custom target price
                    route_metrics = compute_route_metrics(
                        source_row, 
                        source_market.lower(), 
                        target_market, 
                        params, 
                        custom_target_price=target_price
                    )
                    
                    current_score = route_metrics['opportunity_score']
                    
                    # Applica filtri minimi
                    min_roi = params.get('min_roi_pct', 0)
                    min_margin = params.get('min_margin_pct', 0)
                    
                    if DEBUG_MODE and processed_asins <= 1:
                        st.write(f"    → Metrics: ROI {route_metrics['roi']:.1f}%, Margin {route_metrics['gross_margin_pct']:.1f}%, Score {current_score:.1f}")
                        st.write(f"    → Filters: ROI>={min_roi}%, Margin>={min_margin}%")
                    
                    passes_filters = (route_metrics['roi'] >= min_roi and 
                                    route_metrics['gross_margin_pct'] >= min_margin)
                    
                    if DEBUG_MODE and processed_asins <= 1:
                        st.write(f"    → Passes filters: {passes_filters}")
                    
                    if (current_score > best_score and passes_filters):
                        
                        best_score = current_score
                        best_opportunity = {
                            'asin': asin,
                            'title': source_row.get('Title', ''),
                            'source_market': source_market.lower(),
                            'target_market': target_market,
                            'route': f"{source_market.upper()}->{target_market.upper()}",
                            **route_metrics
                        }
                        
                        if DEBUG_MODE and processed_asins <= 1:
                            st.write(f"    ✅ NEW BEST for {asin}: {best_opportunity['route']} Score={best_score:.1f}")
                
                except Exception as e:
                    continue  # Skip problematic routes
        
        if best_opportunity:
            # Final validation before adding route
            source_market = best_opportunity.get('source_market', '').lower()
            target_market = best_opportunity.get('target_market', '').lower()
            roi = best_opportunity.get('roi', 0)
            
            # Skip same-country routes and invalid ROI
            if source_market != target_market and roi > 0:
                best_routes.append(best_opportunity)
            elif DEBUG_MODE and processed_asins <= 3:
                st.write(f"⚠️ Skipped invalid route: {source_market}->{target_market}, ROI: {roi}%")
    
    if DEBUG_MODE:
        st.write(f"=== FIND_BEST_ROUTES SUMMARY ===")
        st.write(f"Processed ASINs: {processed_asins}")
        st.write(f"ASINs with multiple markets: {processed_asins - (len(asin_groups) - processed_asins)}")
        st.write(f"Best opportunities found: {len(best_routes)}")
        if len(best_routes) > 0:
            st.write(f"Sample routes: {[r['route'] for r in best_routes[:3]]}")
        st.write("=== END SUMMARY ===")
    
    if best_routes:
        return pd.DataFrame(best_routes)
    else:
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=[
            'asin', 'title', 'source', 'target', 'source_market', 'target_market', 
            'route', 'purchase_price', 'net_cost', 'target_price', 'fees', 
            'gross_margin_eur', 'gross_margin_pct', 'roi', 'opportunity_score', 
            'profit_score', 'velocity_score', 'competition_score'
        ])


def find_best_routes(df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    Public interface for finding best routes with caching
    
    Args:
        df: DataFrame with multi-market product data
        params: Configuration parameters
        
    Returns:
        pd.DataFrame: Best arbitrage opportunities
    """
    # Convert DataFrame to CSV string for caching
    df_csv = df.to_csv(index=False)
    
    # Extract key parameters for cache key
    discount = params.get('discount', 0.21)
    strategy = params.get('purchase_strategy', 'Buy Box Current')
    scenario = params.get('scenario', 'current')
    mode = params.get('mode', 'FBA')
    min_roi = params.get('min_roi_pct', 0)
    min_margin = params.get('min_margin_pct', 0)
    
    # Use cached calculation
    return calculate_all_routes_cached(df_csv, discount, strategy, scenario, mode, min_roi, min_margin)


def analyze_route_profitability(df: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analizza la profittabilità delle rotte per fornire insights
    
    Args:
        df: DataFrame con dati prodotti
        params: Parametri di configurazione
        
    Returns:
        Dict con statistiche e insights sulle rotte
    """
    best_routes_df = find_best_routes(df, params)
    
    if best_routes_df.empty:
        return {
            'total_products': len(df),
            'profitable_products': 0,
            'avg_opportunity_score': 0.0,
            'avg_roi': 0.0,
            'avg_margin': 0.0,
            'route_distribution': {},
            'top_routes': [],
            'summary': "No profitable routes found"
        }
    
    # Statistiche generali
    stats = {
        'total_products': len(df),
        'profitable_products': len(best_routes_df),
        'profitability_rate': len(best_routes_df) / len(df) * 100,
        'avg_opportunity_score': best_routes_df['opportunity_score'].mean(),
        'avg_roi': best_routes_df['roi'].mean(),
        'avg_margin': best_routes_df['gross_margin_pct'].mean(),
    }
    
    # Distribuzione rotte
    best_routes_df['route'] = best_routes_df['source'].str.upper() + '->' + best_routes_df['target'].str.upper()
    route_counts = best_routes_df['route'].value_counts()
    stats['route_distribution'] = route_counts.to_dict()
    
    # Top 10 rotte per score medio
    top_routes = (best_routes_df.groupby('route')
                  .agg({
                      'opportunity_score': 'mean',
                      'roi': 'mean',
                      'gross_margin_pct': 'mean',
                      'asin': 'count'
                  })
                  .rename(columns={'asin': 'product_count'})
                  .sort_values('opportunity_score', ascending=False)
                  .head(10))
    
    stats['top_routes'] = top_routes.to_dict('index')
    
    # Summary
    best_route = route_counts.index[0] if len(route_counts) > 0 else "None"
    stats['summary'] = (f"Found {stats['profitable_products']} profitable products out of {stats['total_products']} "
                       f"({stats['profitability_rate']:.1f}%). "
                       f"Best route: {best_route} with {route_counts.iloc[0]} products.")
    
    return stats


def create_default_params() -> Dict[str, Any]:
    """
    Crea parametri di default per l'analisi
    
    Returns:
        Dict con parametri di configurazione standard
    """
    return {
        'purchase_strategy': 'Buy Box Current',
        'scenario': 'current',
        'mode': 'FBA',
        'discount': DEFAULT_DISCOUNT,
        'inbound_logistics': 2.0,
        'vat_rates': VAT_RATES,
        'scoring_weights': SCORING_WEIGHTS,
        'skip_same_locale': True,  # Skip same source-target routes
        'min_roi_pct': 10.0,  # Minimum 10% ROI
        'min_margin_pct': 15.0,  # Minimum 15% margin
    }


def validate_margin_sustainability(opportunity):
    """
    Verifica sostenibilità margini nel tempo
    """
    warnings = []
    
    # Check 1: Margine troppo alto (possibile errore)
    if opportunity.get('roi', 0) > 80:
        warnings.append("⚠️ ROI > 80% - Verificare accuratezza dati")
    
    # Check 2: Volatilità prezzi alta
    price_volatility = opportunity.get('price_volatility_index', 50)  # Default neutral
    if price_volatility < 40:
        warnings.append("⚠️ Alta volatilità prezzi - Margini instabili")
    
    # Check 3: Competizione Amazon
    amazon_risk = opportunity.get('amazon_risk', {})
    if amazon_risk.get('level', 'LOW') in ['HIGH', 'CRITICAL']:
        warnings.append("⚠️ Alto rischio Amazon - Possibile price war")
    
    # Check 4: Sostenibilità ranking
    sales_rank = opportunity.get('sales_rank', opportunity.get('Sales Rank: Current', 0))
    if sales_rank > 50000:
        warnings.append("⚠️ Ranking elevato - Velocità vendita ridotta")
    
    # Check 5: Margine assoluto troppo basso
    gross_margin_eur = opportunity.get('gross_margin_eur', 0)
    if gross_margin_eur < 5:
        warnings.append("⚠️ Margine assoluto < €5 - Rischio commissioni aggiuntive")
    
    # Check 6: Prezzo target troppo basso
    target_price = opportunity.get('target_price', 0)
    if target_price < 15:
        warnings.append("⚠️ Prezzo vendita < €15 - Margini fragili per fee FBA")
    
    # Calcola confidence score
    confidence = max(0, 100 - (len(warnings) * 15))
    
    # Determina livello di sostenibilità
    if len(warnings) == 0:
        sustainability_level = "EXCELLENT"
        sustainability_color = "🟢"
    elif len(warnings) <= 1:
        sustainability_level = "GOOD"
        sustainability_color = "🟡"
    elif len(warnings) <= 2:
        sustainability_level = "MODERATE"
        sustainability_color = "🟠"
    else:
        sustainability_level = "POOR"
        sustainability_color = "🔴"
    
    return {
        'is_sustainable': len(warnings) <= 1,
        'warnings': warnings,
        'confidence': confidence,
        'sustainability_level': sustainability_level,
        'sustainability_color': sustainability_color,
        'recommendation': generate_sustainability_recommendation(sustainability_level, warnings),
        'checks_performed': 6,
        'checks_passed': 6 - len(warnings)
    }


def generate_sustainability_recommendation(level, warnings):
    """
    Genera raccomandazioni per la sostenibilità dei margini
    """
    base_recommendations = {
        'EXCELLENT': "✅ Margini molto sostenibili. Procedi con fiducia.",
        'GOOD': "👍 Margini sostenibili. Monitoraggio standard.",
        'MODERATE': "⚠️ Margini moderatamente sostenibili. Monitoraggio frequente consigliato.",
        'POOR': "❌ Margini poco sostenibili. Valuta attentamente i rischi."
    }
    
    recommendation = base_recommendations.get(level, "Livello sconosciuto")
    
    if warnings:
        recommendation += f"\n\nAree di attenzione:"
        for warning in warnings:
            recommendation += f"\n• {warning}"
    
    return recommendation


def assess_opportunity_quality(opportunity_data):
    """
    Valutazione complessiva della qualità dell'opportunità
    """
    # Importa funzioni analytics se necessario
    try:
        from analytics import assess_amazon_competition_risk
        from pricing import calculate_price_volatility_index
    except ImportError:
        # Fallback se moduli non disponibili
        pass
    
    # Arricchisci i dati con valutazioni aggiuntive
    enhanced_opportunity = opportunity_data.copy()
    
    # Aggiungi Amazon risk assessment se disponibile
    if 'assess_amazon_competition_risk' in globals():
        try:
            enhanced_opportunity['amazon_risk'] = assess_amazon_competition_risk(opportunity_data)
        except Exception:
            enhanced_opportunity['amazon_risk'] = {'level': 'UNKNOWN', 'score': 50}
    
    # Aggiungi price volatility se disponibile
    if 'calculate_price_volatility_index' in globals():
        try:
            enhanced_opportunity['price_volatility_index'] = calculate_price_volatility_index(opportunity_data)
        except Exception:
            enhanced_opportunity['price_volatility_index'] = 50
    
    # Valuta sostenibilità margini
    sustainability = validate_margin_sustainability(enhanced_opportunity)
    
    # Calcola quality score finale
    base_score = enhanced_opportunity.get('opportunity_score', 0)
    sustainability_adjustment = (sustainability['confidence'] - 50) / 10  # -5 to +5
    amazon_risk_adjustment = -(enhanced_opportunity.get('amazon_risk', {}).get('score', 50) - 50) / 10  # -5 to +5
    
    final_quality_score = min(100, max(0, base_score + sustainability_adjustment + amazon_risk_adjustment))
    
    return {
        'opportunity': enhanced_opportunity,
        'sustainability': sustainability,
        'final_quality_score': final_quality_score,
        'adjustments': {
            'sustainability_adj': sustainability_adjustment,
            'amazon_risk_adj': amazon_risk_adjustment
        }
    }