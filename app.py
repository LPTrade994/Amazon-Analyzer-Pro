"""
Amazon Analyzer Pro - Streamlit Application
Dark Theme (Black/Red/White)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
import io
import json
from datetime import datetime
import concurrent.futures

# Import our modules
from profit_model import (
    find_best_routes, 
    analyze_route_profitability, 
    create_default_params,
    compute_route_metrics
)
from config import SCORING_WEIGHTS, VAT_RATES, DEFAULT_DISCOUNT, PURCHASE_STRATEGIES, DEBUG_MODE, SHOW_PROGRESS
from analytics import (
    calculate_historic_metrics,
    is_historic_deal,
    momentum_index,
    risk_index,
    get_deal_quality_score,
    find_historic_deals
)
from export import (
    export_consolidated_csv,
    export_executive_summary,
    export_watchlist_json,
    create_summary_report,
    validate_export_data
)

# Page configuration
st.set_page_config(
    page_title="Amazon Analyzer Pro",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Parallel processing functions
def process_asin_batch(asin_batch: list, full_df: pd.DataFrame, params: Dict[str, Any]) -> pd.DataFrame:
    """
    Process a batch of ASINs for cross-market arbitrage
    
    Args:
        asin_batch: List of ASINs to process
        full_df: Complete DataFrame with all markets (needed for cross-market comparison)
        params: Processing parameters
        
    Returns:
        DataFrame with best routes for this ASIN batch
    """
    try:
        if not asin_batch:
            return pd.DataFrame()
        
        # Filter to only include products in this ASIN batch
        batch_df = full_df[full_df['ASIN'].isin(asin_batch)].copy()
        
        if batch_df.empty:
            return pd.DataFrame()
        
        # Use internal find_best_routes function to maintain cross-market logic
        from profit_model import find_best_routes_internal
        routes_df = find_best_routes_internal(batch_df, params)
        
        return routes_df
        
    except Exception as e:
        # Return empty DataFrame on error
        return pd.DataFrame()

def process_asins_parallel(df: pd.DataFrame, params: Dict[str, Any], batch_size: int = 50) -> pd.DataFrame:
    """
    Process ASINs in parallel batches while maintaining cross-market visibility
    
    Args:
        df: Complete DataFrame with all markets
        params: Processing parameters
        batch_size: Number of ASINs per batch
        
    Returns:
        DataFrame with all best routes
    """
    unique_asins = df['ASIN'].unique()
    
    # Split ASINs into batches
    asin_batches = [unique_asins[i:i + batch_size] for i in range(0, len(unique_asins), batch_size)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        # Submit tasks for each ASIN batch
        futures = [
            executor.submit(process_asin_batch, batch, df, params)
            for batch in asin_batches
        ]
        
        # Collect results as they complete
        all_routes = []
        for future in concurrent.futures.as_completed(futures):
            try:
                batch_routes = future.result()
                if not batch_routes.empty:
                    all_routes.append(batch_routes)
            except Exception as e:
                # Skip failed batches
                continue
    
    # Combine all routes
    if all_routes:
        combined_routes = pd.concat(all_routes, ignore_index=True)
        return combined_routes.sort_values('opportunity_score', ascending=False)
    else:
        return pd.DataFrame()

def calculate_killer_metrics(deal_row):
    """
    Calculate killer metrics for historic deals
    
    Returns:
        dict: Dictionary with killer metrics flags and descriptions
    """
    metrics = {
        'price_low_30d': False,
        'ranking_improving': False, 
        'amazon_oos': False,
        'few_competitors': False,
        'descriptions': []
    }
    
    # 🔥 Prezzo al minimo 30gg
    current_price = deal_row.get('Buy Box 🚚: Current', 0)
    min_30d = deal_row.get('Buy Box 🚚: 30 days min.', current_price)
    if current_price > 0 and min_30d > 0 and current_price <= min_30d * 1.02:  # Within 2% of 30d min
        metrics['price_low_30d'] = True
        metrics['descriptions'].append('🔥 Prezzo al minimo 30gg')
    
    # 📈 Ranking in miglioramento
    current_rank = deal_row.get('Sales Rank: Current', 999999)
    avg_rank_30d = deal_row.get('Sales Rank: 30 days avg.', current_rank)
    if current_rank > 0 and avg_rank_30d > 0 and current_rank < avg_rank_30d * 0.8:  # 20% better
        metrics['ranking_improving'] = True
        metrics['descriptions'].append('📈 Ranking migliorando')
    
    # ⚡ Amazon OOS > 70%
    amazon_oos = deal_row.get('Amazon: 90 days OOS', 0)
    if amazon_oos > 70:
        metrics['amazon_oos'] = True
        metrics['descriptions'].append('⚡ Amazon OOS 70%+')
    
    # 💎 Pochi competitor (<5)
    total_offers = deal_row.get('Total Offer Count', 10)
    if total_offers < 5:
        metrics['few_competitors'] = True
        metrics['descriptions'].append('💎 Pochi competitor')
    
    return metrics

def get_deal_risk_alert(deal_row):
    """
    Generate risk alert for a deal
    
    Returns:
        str: Risk level (Low, Medium, High)
    """
    risk_score = 0
    
    # High return rate
    return_rate = deal_row.get('Return Rate', 0)
    if return_rate > 15:
        risk_score += 2
    elif return_rate > 8:
        risk_score += 1
    
    # Low rating
    rating = deal_row.get('Reviews: Rating', 5.0)
    if rating < 3.5:
        risk_score += 2
    elif rating < 4.0:
        risk_score += 1
    
    # High Amazon dominance
    amazon_dominance = deal_row.get('Buy Box: % Amazon 90 days', 0)
    if amazon_dominance > 80:
        risk_score += 1
    
    if risk_score >= 3:
        return "High"
    elif risk_score >= 1:
        return "Medium"
    else:
        return "Low"

def get_roi_indicator(roi):
    """Get emoji indicator for ROI"""
    if roi > 35:
        return "🟢"
    elif roi > 25:
        return "🟡"
    else:
        return "🔴"

def get_score_stars(score):
    """Convert numeric score to star rating"""
    if score >= 90:
        return "⭐⭐⭐⭐⭐"
    elif score >= 80:
        return "⭐⭐⭐⭐"
    elif score >= 70:
        return "⭐⭐⭐"
    elif score >= 60:
        return "⭐⭐"
    else:
        return "⭐"

def get_risk_emoji(risk_level):
    """Get emoji for risk level"""
    risk_map = {
        "Low": "🛡️",
        "Medium": "⚠️", 
        "High": "🚨"
    }
    return risk_map.get(risk_level, "❓")

def get_country_flag(country_code):
    """Get flag emoji for country"""
    flag_map = {
        'it': '🇮🇹',
        'de': '🇩🇪', 
        'fr': '🇫🇷',
        'es': '🇪🇸'
    }
    return flag_map.get(country_code.lower(), '🏳️')

def create_route_display(source, target):
    """Create visual route with flags"""
    source_flag = get_country_flag(source)
    target_flag = get_country_flag(target)
    return f"{source_flag}{source.upper()}→{target_flag}{target.upper()}"

def add_custom_css():
    """Add custom CSS for enhanced UI"""
    st.markdown("""
    <style>
    .big-roi {
        font-size: 2.5em;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
    }
    
    .quick-win-card {
        border: 2px solid #E8E8E8;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    .metric-container {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .tooltip {
        position: relative;
        display: inline-block;
        border-bottom: 1px dotted black;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #555;
        color: white;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        margin-left: -100px;
        opacity: 0;
        transition: opacity 0.3s;
    }
    
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    
    .high-roi { background-color: rgba(144, 238, 144, 0.3) !important; }
    .medium-roi { background-color: rgba(255, 255, 224, 0.3) !important; }
    .low-roi { background-color: rgba(255, 182, 193, 0.3) !important; }
    </style>
    """, unsafe_allow_html=True)

def load_custom_css():
    """Load custom CSS for dark theme"""
    custom_css = """
    <style>
    /* Main theme */
    .main {
        background-color: #000000;
        color: #ffffff;
    }
    
    .stApp {
        background-color: #000000;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #1a1a1a;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(45deg, #1a1a1a, #2d2d2d);
        border: 1px solid #ff0000;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #ff0000;
        margin: 0;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #ffffff;
        margin: 5px 0 0 0;
    }
    
    /* Opportunity badges */
    .opportunity-badge-high {
        background-color: #ff0000;
        color: #ffffff;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    .opportunity-badge-medium {
        background-color: #ff6666;
        color: #000000;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    .opportunity-badge-low {
        background-color: #666666;
        color: #ffffff;
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
    }
    
    /* Headers */
    h1 {
        color: #ff0000;
        border-bottom: 2px solid #ff0000;
        padding-bottom: 10px;
    }
    
    h2, h3 {
        color: #ff0000;
    }
    
    /* Tables */
    .dataframe {
        background-color: #1a1a1a;
        color: #ffffff;
    }
    
    .dataframe th {
        background-color: #ff0000;
        color: #ffffff;
    }
    
    .dataframe td {
        background-color: #2d2d2d;
        color: #ffffff;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #ff0000;
        color: #ffffff;
        border: none;
        border-radius: 4px;
    }
    
    .stButton > button:hover {
        background-color: #cc0000;
        color: #ffffff;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #1a4d1a;
        color: #ffffff;
        border: 1px solid #00ff00;
    }
    
    /* Error messages */
    .stError {
        background-color: #4d1a1a;
        color: #ffffff;
        border: 1px solid #ff0000;
    }
    
    /* Info messages */
    .stInfo {
        background-color: #1a1a4d;
        color: #ffffff;
        border: 1px solid #0066ff;
    }
    
    /* Selectbox and input styling */
    .stSelectbox > div > div {
        background-color: #2d2d2d;
        color: #ffffff;
    }
    
    .stTextInput > div > div > input {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #666666;
    }
    
    .stNumberInput > div > div > input {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #666666;
    }
    
    /* File uploader */
    .stFileUploader > div {
        background-color: #2d2d2d;
        border: 2px dashed #ff0000;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

def create_metric_card(title: str, value: str, delta: str = None):
    """Create a styled metric card"""
    delta_html = f"<div style='color: #00ff00; font-size: 0.8rem;'>{delta}</div>" if delta else ""
    
    metric_html = f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        {delta_html}
    </div>
    """
    return metric_html

def get_opportunity_badge(score: float) -> str:
    """Get styled opportunity badge based on score"""
    if score >= 70:
        return f'<span class="opportunity-badge-high">HIGH ({score:.1f})</span>'
    elif score >= 50:
        return f'<span class="opportunity-badge-medium">MEDIUM ({score:.1f})</span>'
    else:
        return f'<span class="opportunity-badge-low">LOW ({score:.1f})</span>'

def get_score_badge(score: float, label: str = "") -> str:
    """Get colored badge for any score 0-100"""
    color = "#ff0000" if score >= 70 else "#ff6666" if score >= 50 else "#666666"
    text_color = "#ffffff" if score >= 50 else "#ffffff"
    
    display_text = f"{label} {score:.0f}" if label else f"{score:.0f}"
    
    return f'''<span style="
        background-color: {color};
        color: {text_color};
        padding: 4px 8px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 0.8rem;
        display: inline-block;
        margin: 2px;
    ">{display_text}</span>'''

def create_metric_progress_bar(value: float, max_value: float = 100, height: int = 20) -> str:
    """Create HTML progress bar for metrics"""
    percentage = min(100, (value / max_value) * 100)
    color = "#ff0000" if percentage >= 70 else "#ff6666" if percentage >= 50 else "#666666"
    
    return f'''
    <div style="
        width: 100%;
        background-color: #2d2d2d;
        border-radius: 10px;
        height: {height}px;
        margin: 5px 0;
        overflow: hidden;
        border: 1px solid #444444;
    ">
        <div style="
            width: {percentage}%;
            background-color: {color};
            height: 100%;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ffffff;
            font-size: 0.7rem;
            font-weight: bold;
        ">
            {value:.0f}
        </div>
    </div>
    '''

def format_currency(value: float) -> str:
    """Format currency values"""
    if pd.isna(value):
        return "€0.00"
    return f"€{value:,.2f}"

def format_percentage(value: float) -> str:
    """Format percentage values"""
    if pd.isna(value):
        return "0.0%"
    return f"{value:.1f}%"

def create_amazon_links(asin: str) -> str:
    """Create Amazon and Keepa links"""
    if pd.isna(asin) or asin == "":
        return ""
    
    amazon_link = f'<a href="https://www.amazon.it/dp/{asin}" target="_blank">🛒</a>'
    keepa_link = f'<a href="https://keepa.com/#!product/8-{asin}" target="_blank">📊</a>'
    
    return f'{amazon_link} {keepa_link}'

def prepare_consolidated_data(best_routes_df: pd.DataFrame) -> pd.DataFrame:
    """Prepare data for consolidated view with all mandatory columns"""
    if best_routes_df.empty:
        return pd.DataFrame()
    
    # Create a copy for processing
    df = best_routes_df.copy()
    
    # Create Best Route column
    df['Best Route'] = df['source'].str.upper() + '->' + df['target'].str.upper()
    
    # Create Links column
    df['Links'] = df['asin'].apply(create_amazon_links)
    
    # Create Fees breakdown (simplified)
    df['Fees €'] = df['fees'].apply(lambda x: format_currency(x['total']) if isinstance(x, dict) else format_currency(0))
    
    # Select and reorder mandatory columns
    consolidated_columns = [
        'asin', 'title', 'Best Route', 'purchase_price', 'net_cost',
        'target_price', 'Fees €', 'gross_margin_eur', 'gross_margin_pct',
        'roi', 'opportunity_score', 'Links'
    ]
    
    # Ensure all columns exist
    for col in consolidated_columns:
        if col not in df.columns:
            if col in ['Fees €', 'Links', 'Best Route']:
                continue  # Already created above
            else:
                df[col] = 0
    
    # Format columns for display
    df['Purchase Price €'] = df['purchase_price'].apply(format_currency)
    df['Net Cost €'] = df['net_cost'].apply(format_currency)
    df['Target Price €'] = df['target_price'].apply(format_currency)
    df['Gross Margin €'] = df['gross_margin_eur'].apply(format_currency)
    df['Gross Margin %'] = df['gross_margin_pct'].apply(format_percentage)
    df['ROI %'] = df['roi'].apply(format_percentage)
    df['Opportunity Score'] = df['opportunity_score'].apply(get_opportunity_badge)
    
    # Final column selection with proper names
    final_columns = [
        'asin', 'title', 'Best Route', 'Purchase Price €', 'Net Cost €',
        'Target Price €', 'Fees €', 'Gross Margin €', 'Gross Margin %',
        'ROI %', 'Opportunity Score', 'Links'
    ]
    
    display_df = df[final_columns].copy()
    
    # Rename columns for display
    display_df.columns = [
        'ASIN', 'Title', 'Best Route', 'Purchase Price €', 'Net Cost €',
        'Target Price €', 'Fees €', 'Gross Margin €', 'Gross Margin %',
        'ROI %', 'Opportunity Score', 'Links'
    ]
    
    return display_df

@st.cache_data
def create_opportunity_gauge(score: float) -> go.Figure:
    """Create gauge chart for Opportunity Score"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Opportunity Score", 'font': {'color': '#ffffff', 'size': 16}},
        number={'font': {'color': '#ffffff', 'size': 24}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#ffffff"},
            'bar': {'color': "#ff0000" if score > 70 else "#ff6666" if score > 50 else "#666666"},
            'steps': [
                {'range': [0, 50], 'color': "#2d2d2d"},
                {'range': [50, 70], 'color': "#404040"},
                {'range': [70, 100], 'color': "#1a1a1a"}
            ],
            'threshold': {
                'line': {'color': "#ffffff", 'width': 4},
                'thickness': 0.75, 
                'value': 80
            }
        }
    ))
    fig.update_layout(
        height=250, 
        paper_bgcolor="#000000", 
        font_color="#ffffff",
        margin=dict(l=0, r=0, t=40, b=0)
    )
    return fig

@st.cache_data
def create_price_sparkline(row: pd.Series) -> go.Figure:
    """Create sparkline for price trends"""
    # Get historic prices
    current = row.get('Buy Box 🚚: Current', 0)
    avg_30 = row.get('Buy Box 🚚: 30 days avg.', current)
    avg_90 = row.get('Buy Box 🚚: 90 days avg.', current)
    avg_180 = row.get('Buy Box 🚚: 180 days avg.', current)
    lowest = row.get('Buy Box 🚚: Lowest', current)
    highest = row.get('Buy Box 🚚: Highest', current)
    
    if current <= 0:
        # Return empty chart for invalid data
        fig = go.Figure()
        fig.add_annotation(
            text="No price data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="#ffffff", size=14)
        )
        fig.update_layout(
            height=200, 
            paper_bgcolor="#000000", 
            plot_bgcolor="#000000",
            font_color="#ffffff"
        )
        return fig
    
    # Create simulated trend data (in real implementation, use actual historical data)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=180, freq='D')
    
    # Simulate price evolution from avg_180 to current with some noise
    price_trend = []
    for i in range(180):
        progress = i / 179
        # Linear interpolation from avg_180 to current with realistic variation
        base_price = avg_180 + (current - avg_180) * progress
        # Add some realistic noise
        noise = np.random.normal(0, abs(current) * 0.02)
        price = max(0.1, base_price + noise)  # Ensure positive price
        price_trend.append(price)
    
    # Smooth the trend
    price_trend = pd.Series(price_trend).rolling(window=5, center=True).mean().bfill().ffill()
    
    fig = go.Figure()
    
    # Main price line
    fig.add_trace(go.Scatter(
        x=dates, 
        y=price_trend, 
        mode='lines', 
        name='Buy Box Price',
        line=dict(color='#ff0000', width=2),
        hovertemplate='%{x}<br>Price: €%{y:.2f}<extra></extra>'
    ))
    
    # Reference lines
    fig.add_hline(
        y=current, 
        line_dash="solid", 
        line_color="#ffffff", 
        line_width=2,
        annotation_text=f"Current: €{current:.2f}",
        annotation_position="top right"
    )
    
    if avg_90 != current:
        fig.add_hline(
            y=avg_90, 
            line_dash="dash", 
            line_color="#ffaa00", 
            line_width=1,
            annotation_text=f"90d Avg: €{avg_90:.2f}",
            annotation_position="bottom right"
        )
    
    fig.update_layout(
        height=200, 
        paper_bgcolor="#000000", 
        plot_bgcolor="#000000",
        font_color="#ffffff", 
        showlegend=False,
        margin=dict(l=0, r=0, t=20, b=0),
        xaxis=dict(showgrid=False, showticklabels=False),
        yaxis=dict(showgrid=True, gridcolor="#333333", tickformat='.2f')
    )
    return fig

@st.cache_data
def create_progress_bar_chart(value: float, title: str, max_val: float = 100) -> go.Figure:
    """Create horizontal progress bar chart"""
    color = "#ff0000" if value > 70 else "#ff6666" if value > 50 else "#999999"
    
    fig = go.Figure(go.Bar(
        x=[value, max_val - value],
        y=[title],
        orientation='h',
        marker=dict(color=[color, '#2d2d2d']),
        text=[f'{value:.1f}', ''],
        textposition='inside',
        textfont=dict(color='#ffffff', size=14),
        hoverinfo='none'
    ))
    
    fig.update_layout(
        height=60,
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font_color="#ffffff",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(showgrid=False, showticklabels=False, range=[0, max_val]),
        yaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(size=12)),
        barmode='stack'
    )
    return fig

def display_risk_alerts(opportunities_df):
    """
    Mostra alert per prodotti ad alto rischio
    """
    if opportunities_df.empty:
        return
    
    # Prima calcola i risk levels per tutti i prodotti se non già presenti
    if 'risk_level' not in opportunities_df.columns:
        # Aggiungi valutazione rischi per ogni opportunità
        risk_levels = []
        warnings_list = []
        
        for _, row in opportunities_df.iterrows():
            try:
                # Importa le funzioni necessarie
                from profit_model import validate_margin_sustainability
                from analytics import assess_amazon_competition_risk
                
                # Valuta sostenibilità margini
                sustainability = validate_margin_sustainability(row)
                
                # Valuta rischio Amazon
                amazon_risk = assess_amazon_competition_risk(row)
                
                # Determina livello di rischio complessivo
                if (not sustainability['is_sustainable'] or 
                    amazon_risk['level'] in ['HIGH', 'CRITICAL'] or
                    sustainability['sustainability_level'] == 'POOR'):
                    risk_level = 'CRITICAL'
                elif (len(sustainability['warnings']) > 0 or 
                      amazon_risk['level'] == 'MEDIUM' or
                      sustainability['sustainability_level'] == 'MODERATE'):
                    risk_level = 'HIGH'
                else:
                    risk_level = 'LOW'
                
                # Combina warnings
                all_warnings = sustainability['warnings'].copy()
                if amazon_risk['level'] in ['HIGH', 'CRITICAL']:
                    all_warnings.append(f"🔴 Amazon Risk: {amazon_risk['recommendation']}")
                
                risk_levels.append(risk_level)
                warnings_list.append(all_warnings)
                
            except Exception:
                # Fallback in caso di errore
                risk_levels.append('UNKNOWN')
                warnings_list.append(['⚠️ Impossibile valutare il rischio'])
        
        # Aggiungi colonne al dataframe
        opportunities_df = opportunities_df.copy()
        opportunities_df['risk_level'] = risk_levels
        opportunities_df['warnings'] = warnings_list
    
    # Filtra prodotti ad alto rischio
    critical_risks = opportunities_df[
        opportunities_df['risk_level'].isin(['HIGH', 'CRITICAL'])
    ]
    
    if not critical_risks.empty:
        st.warning(f"⚠️ {len(critical_risks)} prodotti con rischio elevato rilevati")
        
        with st.expander("🚨 Visualizza Alert Dettagliati", expanded=False):
            for idx, row in critical_risks.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    title = row.get('title', row.get('Title', 'N/A'))
                    asin = row.get('asin', row.get('ASIN', 'N/A'))
                    st.write(f"**{title[:50]}{'...' if len(str(title)) > 50 else ''}**")
                    st.caption(f"ASIN: {asin}")
                
                with col2:
                    risk_level = row['risk_level']
                    risk_color = "🔴" if risk_level == "CRITICAL" else "🟠"
                    st.write(f"Risk: **{risk_color} {risk_level}**")
                    
                    # Mostra prime 3 warnings per spazio
                    warnings = row.get('warnings', [])
                    for warning in warnings[:3]:
                        st.caption(f"• {warning}")
                    
                    if len(warnings) > 3:
                        st.caption(f"... e altri {len(warnings) - 3} warning")
                
                with col3:
                    button_key = f"risk_detail_{asin}_{idx}"
                    if st.button("📋 Dettagli", key=button_key, help="Mostra dettagli completi del rischio"):
                        st.session_state[f'show_risk_detail_{asin}'] = True
                
                # Mostra dettagli espansi se richiesto
                if st.session_state.get(f'show_risk_detail_{asin}', False):
                    with st.container():
                        st.markdown("**📊 Analisi Rischio Completa:**")
                        
                        # ROI e margini
                        roi = row.get('roi', 0)
                        margin = row.get('gross_margin_pct', 0)
                        st.write(f"• ROI: {roi:.1f}% | Margine: {margin:.1f}%")
                        
                        # ROI validation warning
                        if roi > 50:
                            st.warning('⚠️ ROI elevato - Verificare manualmente prima dell\'acquisto')
                        
                        # Tutti i warnings
                        st.write("**⚠️ Tutti gli Alert:**")
                        for warning in warnings:
                            st.write(f"  {warning}")
                        
                        # Chiudi dettagli
                        if st.button("❌ Chiudi Dettagli", key=f"close_detail_{asin}_{idx}"):
                            st.session_state[f'show_risk_detail_{asin}'] = False
                            st.rerun()
                
                st.divider()
    
    return opportunities_df  # Ritorna il dataframe arricchito


def get_asin_detail_data(asin: str, df: pd.DataFrame, best_routes: pd.DataFrame) -> Dict[str, Any]:
    """Get detailed data for selected ASIN"""
    # Find the product in original data
    product_row = df[df['ASIN'] == asin].iloc[0] if asin in df['ASIN'].values else None
    
    # Find the route data
    route_row = best_routes[best_routes['asin'] == asin].iloc[0] if asin in best_routes['asin'].values else None
    
    if product_row is None:
        return None
    
    # Calculate analytics metrics
    historic_metrics = calculate_historic_metrics(product_row)
    is_deal = is_historic_deal(product_row)
    momentum = momentum_index(product_row)
    risk = risk_index(product_row)
    
    # Get opportunity score from route data if available
    opportunity_score = route_row['opportunity_score'] if route_row is not None else 0
    velocity_score = route_row['velocity_score'] if route_row is not None else 0
    
    return {
        'product_row': product_row,
        'route_row': route_row,
        'historic_metrics': historic_metrics,
        'is_historic_deal': is_deal,
        'momentum_score': momentum,
        'risk_score': risk,
        'opportunity_score': opportunity_score,
        'velocity_score': velocity_score
    }

def main():
    """Main application function"""
    load_custom_css()
    
    # Header - come specificato nel prompt
    st.title("📊 Amazon Analyzer Pro")
    st.markdown("---")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # File upload - multipli CSV/XLSX
        st.subheader("📁 Data Upload")
        uploaded_files = st.file_uploader(
            "Upload Keepa datasets",
            type=['csv', 'xlsx'],
            accept_multiple_files=True,
            help="Carica i file di export Keepa (CSV o XLSX)"
        )
        
        # Analysis parameters
        st.subheader("🎯 Analysis Parameters")
        
        purchase_strategy = st.selectbox(
            "Purchase Strategy",
            PURCHASE_STRATEGIES,
            index=0,
            help="Select which price column to use for purchasing"
        )
        
        scenario = st.selectbox(
            "Sale Scenario",
            ["Short", "Medium", "Long"],
            index=1,
            help="Short: Quick turnover, Medium: Balanced, Long: Patient approach"
        )
        
        mode = st.selectbox(
            "Fulfillment Mode",
            ["FBA", "FBM"],
            index=0,
            help="Choose fulfillment method"
        )
        
        # Discount slider direttamente nella sidebar principale
        discount = st.slider(
            "Discount %",
            min_value=0,
            max_value=40,
            value=21,
            step=1,
            help="Purchase discount percentage"
        )
        
        st.sidebar.markdown("### 🌍 Filtri Geografici")

        # Multi-select per flessibilità massima
        purchase_countries = st.sidebar.multiselect(
            "Paese di Acquisto Preferito",
            options=['Tutti', 'IT', 'DE', 'FR', 'ES', 'UK'],
            default=['Tutti'],
            help="Seleziona uno o più paesi dove preferisci acquistare"
        )
        
        # 🎯 SMART FILTERS SECTION
        st.sidebar.markdown("### 🎯 Filtri Rapidi")
        
        preset_filter = st.sidebar.radio(
            "Preset",
            ["Tutti", "🔥 Hot Deals", "👍 Safe Bets", "🎲 High Risk/Reward", "💎 Hidden Gems"],
            help="Filtri predefiniti per diversi stili di trading"
        )
        
        # Advanced parameters
        with st.expander("🔧 Advanced Settings"):
            
            
            inbound_logistics = st.number_input(
                "Inbound Logistics Cost €",
                min_value=0.0,
                max_value=10.0,
                value=2.0,
                step=0.1,
                help="Cost for inbound logistics per unit"
            )
            
            min_roi = st.slider(
                "Minimum ROI %",
                min_value=0.0,
                max_value=100.0,
                value=10.0,
                step=5.0,
                help="Minimum ROI required for opportunities"
            )
            
            min_margin = st.slider(
                "Minimum Margin %",
                min_value=0.0,
                max_value=50.0,
                value=15.0,
                step=2.5,
                help="Minimum gross margin required"
            )
        
        # Scoring weights - sezione Advanced Scoring come richiesto
        with st.expander("⚙️ Advanced Scoring"):
            st.write("Adjust component weights for Opportunity Score:")
            
            profit_weight = st.slider("Profit Weight", 0.1, 0.8, SCORING_WEIGHTS['profit'], 0.05)
            velocity_weight = st.slider("Velocity Weight", 0.1, 0.5, SCORING_WEIGHTS['velocity'], 0.05)
            competition_weight = st.slider("Competition Weight", 0.1, 0.3, SCORING_WEIGHTS['competition'], 0.05)
            
            # Normalize weights
            total_weight = profit_weight + velocity_weight + competition_weight
            if total_weight != 1.0:
                st.info(f"Weights normalized to sum to 1.0 (current sum: {total_weight:.2f})")
        
        st.markdown("---")
        st.markdown("**Made with ❤️ for Amazon FBA**")
    
    # Main content area
    if uploaded_files:
        # Debug: mostra info sui file caricati
        st.write("Files uploaded:")
        for f in uploaded_files:
            if DEBUG_MODE:
                st.write(f"- {f.name} (size: {f.size} bytes, type: {type(f)})")
        
        try:
            # Load data usando la funzione robusta da loaders.py
            with st.spinner("Loading data..."):
                from loaders import load_data
                df = load_data(uploaded_files)
            
            if not df.empty:
                if 'source_market' not in df.columns:
                    st.error("❌ CRITICAL: source_market column missing from main dataset!")
                    st.stop()
                else:
                    unique_markets = df['source_market'].unique()
                    asin_count = len(df['ASIN'].unique())
                    st.success(f"Dataset caricato: {len(df)} righe, {asin_count} ASIN unici, mercati: {list(unique_markets)}")
                    
                    # DEBUG: Check data quality before analysis
                    if DEBUG_MODE:
                        st.write("=== DATASET QUALITY CHECK ===")
                        st.write(f"Columns: {list(df.columns[:10])}...")  # Show first 10 columns
                        st.write(f"Source markets: {df['source_market'].value_counts().to_dict()}")
                        st.write(f"ASINs per market: {df.groupby('source_market')['ASIN'].nunique().to_dict()}")
                        
                        # Check pricing columns
                        price_cols = ['Buy Box 🚚: Current', 'Amazon: Current', 'New FBA: Current']
                        for col in price_cols:
                            if col in df.columns:
                                valid_prices = df[col][df[col] > 0].count()
                                st.write(f"{col}: {valid_prices} valid prices out of {len(df)}")
                        
                        # Check for cross-market ASINs
                        asin_markets = df.groupby('ASIN')['source_market'].nunique()
                        multi_market_asins = asin_markets[asin_markets > 1].count()
                        st.write(f"ASINs available in multiple markets: {multi_market_asins}")
                        st.write("=== END QUALITY CHECK ===")
            
            # Prepare parameters
            params = create_default_params()
            params.update({
                'purchase_strategy': purchase_strategy,
                'scenario': scenario,
                'mode': mode,
                'discount': discount / 100,  # Converte da percentuale
                'inbound_logistics': inbound_logistics,
                'min_roi_pct': min_roi,
                'min_margin_pct': min_margin,
                'scoring_weights': {
                    'profit': profit_weight / total_weight,
                    'velocity': velocity_weight / total_weight,
                    'competition': competition_weight / total_weight,
                    'momentum': 0.0,
                    'risk': 0.0,
                    'ops': 0.0
                }
            })
            
            # Analysis section
            st.header("📊 Analysis Results")
            
            with st.spinner("Analisi cross-market in corso..."):
                if DEBUG_MODE:
                    st.write("=== STARTING ANALYSIS ===")
                    st.write(f"DataFrame shape: {df.shape}")
                    st.write(f"Params: {params}")
                
                # Check if parallel processing is beneficial
                unique_markets = df['source_market'].unique()
                total_products = len(df)
                unique_asins = df['ASIN'].nunique()
                
                if DEBUG_MODE:
                    st.write(f"Analysis setup: {unique_asins} ASINs, {total_products} products, {len(unique_markets)} markets")
                
                if unique_asins > 10000 and total_products > 20000:  # Disable parallel processing for now
                    # Use parallel processing for large datasets with many ASINs
                    if DEBUG_MODE:
                        st.info(f"Using parallel ASIN processing: {unique_asins} ASINs across {len(unique_markets)} markets")
                    
                    best_routes = process_asins_parallel(df, params, batch_size=25)
                    
                    if DEBUG_MODE:
                        st.success(f"Parallel processing completed: {len(best_routes)} routes found")
                    
                else:
                    # Use standard processing for smaller datasets
                    if DEBUG_MODE:
                        st.info(f"Using standard processing: {unique_asins} ASINs, {total_products} products")
                    
                    try:
                        best_routes = find_best_routes(df, params)
                        if DEBUG_MODE:
                            st.write(f"Standard processing completed: {len(best_routes)} routes found")
                    except Exception as e:
                        if DEBUG_MODE:
                            st.error(f"Error in find_best_routes: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                        best_routes = pd.DataFrame()
                
                if DEBUG_MODE:
                    st.write("=== ANALYSIS RESULTS ===")
                    st.write(f"Best routes shape: {best_routes.shape if hasattr(best_routes, 'shape') else 'No shape'}")
                    if not best_routes.empty:
                        st.write(f"Route columns: {list(best_routes.columns)}")
                        st.write(f"Sample routes: {best_routes.head(2).to_dict()}")
                
                # Get profitability analysis
                try:
                    analysis = analyze_route_profitability(df, params)
                    if DEBUG_MODE:
                        st.write(f"Analysis completed: {analysis.get('summary', 'No summary')}")
                except Exception as e:
                    if DEBUG_MODE:
                        st.error(f"Error in analyze_route_profitability: {str(e)}")
                    analysis = {'total_products': len(df), 'profitable_products': 0}
            
            if not best_routes.empty:
                st.success(f"Analisi completata: {len(best_routes)} opportunità cross-market trovate")
            else:
                st.warning("Nessuna opportunità di arbitraggio trovata con i parametri correnti")
            
            if not best_routes.empty:
                # Enhanced KPI Dashboard
                st.subheader("📊 Dashboard Overview")
                
                # Calculate historic deals from original data
                historic_deals_df = find_historic_deals(df)
                
                # 4 colonne principali KPI
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    total_asins = len(best_routes)
                    st.metric("🎯 ASIN Analizzati", total_asins)
                
                with col2:
                    historic_count = len(historic_deals_df)
                    historic_pct = f"{historic_count/total_asins*100:.1f}%" if total_asins > 0 else "0%"
                    st.metric("🔥 Affari Storici", historic_count, delta=historic_pct)
                
                with col3:
                    avg_score = analysis['avg_opportunity_score']
                    score_label = "Alto" if avg_score > 60 else "Medio" if avg_score > 40 else "Basso"
                    st.metric("⭐ Score Medio", f"{avg_score:.1f}", delta=score_label)
                
                with col4:
                    best_roi = best_routes['roi'].max() if 'roi' in best_routes.columns else 0
                    st.metric("💰 Miglior ROI", f"{best_roi:.1f}%")
                    
                    # ROI validation warning for best ROI
                    if best_roi > 50:
                        st.warning('⚠️ ROI >50% - Verificare')
                
                st.markdown("---")
                
                # Add custom CSS
                add_custom_css()
                
                # 🔥 REDESIGNED AFFARI STORICI - TOTAL UI OVERHAUL
                if len(historic_deals_df) > 0:
                    # Merge historic deals with best routes for complete data
                    enhanced_deals = []
                    
                    for _, deal in historic_deals_df.iterrows():
                        asin = deal.get('ASIN', deal.get('asin', ''))
                        
                        # Find matching route
                        matching_route = best_routes[best_routes['asin'] == asin]
                        if not matching_route.empty:
                            route_data = matching_route.iloc[0]
                            
                            # Combine deal and route data
                            enhanced_deal = {
                                'asin': asin,
                                'title': deal.get('Title', ''),
                                'route': route_data.get('route', ''),
                                'buy_price': route_data.get('purchase_price', 0),
                                'net_cost': route_data.get('net_cost', 0),
                                'sell_price': route_data.get('target_price', 0),
                                'profit_eur': route_data.get('net_profit', 0),
                                'roi_pct': route_data.get('roi', 0),
                                'score': route_data.get('opportunity_score', 0),
                                'source_market': route_data.get('source_market', ''),
                                'target_market': route_data.get('target_market', ''),
                                'original_deal': deal
                            }
                            
                            # Skip same-country routes and apply preset filters
                            valid_deal = (enhanced_deal['source_market'].lower() != enhanced_deal['target_market'].lower() 
                                        and enhanced_deal['roi_pct'] > 0)
                            
                            if valid_deal:
                                # Apply sidebar preset filters
                                if preset_filter == "🔥 Hot Deals":
                                    if enhanced_deal['roi_pct'] > 35:
                                        enhanced_deals.append(enhanced_deal)
                                elif preset_filter == "👍 Safe Bets":
                                    risk = get_deal_risk_alert(deal)
                                    if enhanced_deal['score'] > 80 and risk == 'Low':
                                        enhanced_deals.append(enhanced_deal)
                                elif preset_filter == "🎲 High Risk/Reward":
                                    risk = get_deal_risk_alert(deal)
                                    if enhanced_deal['roi_pct'] > 40 and risk == 'High':
                                        enhanced_deals.append(enhanced_deal)
                                elif preset_filter == "💎 Hidden Gems":
                                    if enhanced_deal['score'] > 75 and enhanced_deal['roi_pct'] > 20:
                                        killer_metrics = calculate_killer_metrics(deal)
                                        if len(killer_metrics['descriptions']) >= 2:
                                            enhanced_deals.append(enhanced_deal)
                                else:  # "Tutti"
                                    enhanced_deals.append(enhanced_deal)
                    
                    if enhanced_deals:
                        # Sort by score descending
                        enhanced_deals.sort(key=lambda x: x['score'], reverse=True)
                        
                        st.subheader("🔥 Affari Storici Dashboard")
                        
                        # 📊 1. AGGREGATE METRICS AT TOP
                        st.markdown("### 📊 Metriche Aggregate")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        total_opportunities = len(enhanced_deals)
                        avg_roi = sum(d['roi_pct'] for d in enhanced_deals) / len(enhanced_deals)
                        avg_score = sum(d['score'] for d in enhanced_deals) / len(enhanced_deals)
                        hot_deals_count = len([d for d in enhanced_deals if d['roi_pct'] > 40])
                        
                        with col1:
                            st.metric("🎯 Opportunità Totali", total_opportunities, delta=f"+{total_opportunities}")
                        with col2:
                            st.metric("💰 ROI Medio", f"{avg_roi:.1f}%", delta=f"{avg_roi-25:.1f}%")
                        with col3:
                            st.metric("⭐ Score Medio", f"{avg_score:.0f}", delta=f"{avg_score-70:.0f}")
                        with col4:
                            st.metric("🔥 Hot Deals (>40% ROI)", hot_deals_count, delta=hot_deals_count)
                        
                        # 🏆 2. DEAL OF THE DAY
                        st.markdown("### 🏆 Deal of the Day")
                        best_deal = enhanced_deals[0]
                        route_display = create_route_display(best_deal['source_market'], best_deal['target_market'])
                        
                        st.success(f"**{best_deal['title'][:60]}...** | {route_display} | ROI {best_deal['roi_pct']:.1f}% | SCORE {best_deal['score']:.0f}")
                        
                        # ROI validation warning for best deal
                        if best_deal['roi_pct'] > 50:
                            st.warning('⚠️ ROI elevato - Verificare manualmente prima dell\'acquisto')
                        
                        # ⚡ 3. TOP 5 QUICK WINS SECTION
                        st.markdown("### ⚡ Top 5 Quick Wins")
                        
                        quick_wins = enhanced_deals[:5]
                        for i, deal in enumerate(quick_wins):
                            with st.container():
                                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                                
                                with col1:
                                    title_short = deal['title'][:40] + "..." if len(deal['title']) > 40 else deal['title']
                                    route_visual = create_route_display(deal['source_market'], deal['target_market'])
                                    st.markdown(f"**{title_short}**")
                                    st.caption(f"{route_visual} | ASIN: {deal['asin']}")
                                
                                with col2:
                                    roi_indicator = get_roi_indicator(deal['roi_pct'])
                                    st.markdown(f"<div class='big-roi'>{roi_indicator} {deal['roi_pct']:.1f}%</div>", unsafe_allow_html=True)
                                
                                with col3:
                                    score_stars = get_score_stars(deal['score'])
                                    st.markdown(f"**Score:** {score_stars}")
                                    st.caption(f"{deal['score']:.0f}/100")
                                
                                with col4:
                                    if st.button("🔍 Analizza", key=f"analyze_{deal['asin']}_{i}"):
                                        st.success(f"Analyzing {deal['asin']}...")
                        
                        st.markdown("---")
                        
                        # 📋 4. ENHANCED TABLE WITH HIGHLIGHTING
                        st.markdown("### 📋 Tabella Dettagliata")
                        
                        # Create enhanced table data
                        table_data = []
                        
                        for deal in enhanced_deals[:20]:  # Top 20
                            killer_metrics = calculate_killer_metrics(deal['original_deal'])
                            risk_alert = get_deal_risk_alert(deal['original_deal'])
                            
                            # Visual indicators
                            roi_emoji = get_roi_indicator(deal['roi_pct'])
                            score_stars = get_score_stars(deal['score'])
                            risk_emoji = get_risk_emoji(risk_alert)
                            route_visual = create_route_display(deal['source_market'], deal['target_market'])
                            
                            # Killer metrics display
                            killer_display = ' '.join(killer_metrics['descriptions']) if killer_metrics['descriptions'] else '-'
                            
                            table_data.append({
                                'ASIN': deal['asin'],
                                'Titolo': deal['title'][:40] + "..." if len(deal['title']) > 40 else deal['title'],
                                'Route': route_visual,
                                'Buy €': f"{deal['buy_price']:.2f}",
                                'Net Cost €': f"{deal['net_cost']:.2f}",
                                'Sell €': f"{deal['sell_price']:.2f}",
                                'Profit €': f"{deal['profit_eur']:.2f}",
                                'ROI': f"{roi_emoji} {deal['roi_pct']:.1f}%",
                                'Score': f"{score_stars} ({deal['score']:.0f})",
                                'Killer Metrics': killer_display,
                                'Risk': f"{risk_emoji} {risk_alert}"
                            })
                        
                        if table_data:
                            df_display = pd.DataFrame(table_data)
                            
                            # Apply highlighting based on ROI
                            def highlight_roi_rows(row):
                                roi_val = float(row['ROI'].split()[-1].rstrip('%'))
                                if roi_val > 35:
                                    return ['background-color: rgba(144, 238, 144, 0.3)'] * len(row)
                                elif roi_val > 25:
                                    return ['background-color: rgba(255, 255, 224, 0.3)'] * len(row)
                                else:
                                    return ['background-color: rgba(255, 182, 193, 0.2)'] * len(row)
                            
                            # Display styled table
                            styled_df = df_display.style.apply(highlight_roi_rows, axis=1)
                            st.dataframe(styled_df, use_container_width=True, hide_index=True)
                            
                            st.caption(f"📊 Showing top 20 of {len(enhanced_deals)} historic deals | Filter: {preset_filter}")
                            
                            # Enhanced Legend
                            st.markdown("""
                            **Legenda:**
                            🟢 ROI >35% | 🟡 ROI 25-35% | 🔴 ROI <25% | ⭐ Score rating | 🛡️ Low risk | ⚠️ Medium risk | 🚨 High risk
                            """)
                        else:
                            st.info("Nessun deal trovato con il preset selezionato.")
                    else:
                        st.info(f"Nessun deal trovato con il preset '{preset_filter}'.")
                else:
                    st.info("ℹ️ Nessun affare storico rilevato con i parametri correnti.")
                
                st.markdown("---")
                
                # Charts section
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📈 Route Distribution")
                    route_data = pd.DataFrame(
                        list(analysis['route_distribution'].items()),
                        columns=['Route', 'Count']
                    )
                    
                    fig_routes = px.bar(
                        route_data,
                        x='Route',
                        y='Count',
                        title="Products by Best Route",
                        color_discrete_sequence=['#ff0000']
                    )
                    fig_routes.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig_routes, use_container_width=True)
                
                with col2:
                    st.subheader("💰 ROI vs Opportunity Score")
                    fig_scatter = px.scatter(
                        best_routes,
                        x='roi',
                        y='opportunity_score',
                        color='gross_margin_pct',
                        size='target_price',
                        hover_data=['asin', 'title'],
                        title="Opportunity Analysis",
                        color_continuous_scale='Reds'
                    )
                    fig_scatter.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font_color='white'
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                
                # Consolidated Multi-Market View
                st.subheader("📋 Consolidated Multi-Market View")
                
                # Enhanced Filters Section
                st.subheader("🔧 Filtri Avanzati")
                
                # Basic filters (always visible)
                st.markdown("**Filtri Base:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    min_score_filter = st.slider(
                        "Min Opportunity Score",
                        min_value=0,
                        max_value=100,
                        value=50,
                        step=5,
                        help="Filter products by minimum opportunity score"
                    )
                
                with col2:
                    min_roi_filter = st.slider(
                        "Min ROI %",
                        min_value=0,
                        max_value=100,
                        value=10,
                        step=5,
                        help="Filter products by minimum ROI percentage"
                    )
                
                with col3:
                    max_amazon_dominance = st.slider(
                        "Max Amazon Dominance %",
                        min_value=0,
                        max_value=100,
                        value=80,
                        step=5,
                        help="Filter products by maximum Amazon buy box dominance"
                    )
                
                # Advanced filters (expandable)
                with st.expander("⚙️ Filtri Dettagliati", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        min_velocity = st.slider("Min Velocity Score", 0, 100, 30)
                        max_amazon_share = st.slider("Max Amazon Share %", 0, 100, 80)
                    
                    with col2:
                        min_rating = st.slider("Min Rating", 1.0, 5.0, 3.5, 0.1)
                        max_return_rate = st.slider("Max Return Rate %", 0, 50, 20)
                    
                    with col3:
                        only_historic_deals = st.checkbox("Solo Affari Storici")
                        only_prime_eligible = st.checkbox("Solo Prime Eligible")
                
                # Apply all filters to the data
                filtered_routes = best_routes.copy()
                original_count = len(filtered_routes)
                
                # Basic filters
                filtered_routes = filtered_routes[filtered_routes['opportunity_score'] >= min_score_filter]
                filtered_routes = filtered_routes[filtered_routes['roi'] >= min_roi_filter]
                
                # CRITICAL: Filter out same-country routes and zero/negative ROI
                if 'source_market' in filtered_routes.columns and 'target_market' in filtered_routes.columns:
                    # Remove same-country routes (IT->IT, DE->DE, etc.)
                    filtered_routes = filtered_routes[
                        filtered_routes['source_market'].str.lower() != filtered_routes['target_market'].str.lower()
                    ]
                    
                # Remove routes with ROI <= 0 (impossible/invalid)
                filtered_routes = filtered_routes[filtered_routes['roi'] > 0]
                
                # Logica di filtering geografico
                if 'Tutti' not in purchase_countries and len(purchase_countries) > 0:
                    # Filtra DOPO il calcolo di tutte le route
                    filtered_routes = filtered_routes[
                        filtered_routes['source'].str.upper().isin(purchase_countries)
                    ]
                
                # Add additional data from original dataset for advanced filtering
                if not df.empty and 'ASIN' in df.columns:
                    # Create mapping for additional data - handle duplicate ASINs
                    additional_data = {}
                    for col in ['Buy Box: % Amazon 90 days', 'Reviews Rating', 'Return Rate', 'Prime Eligible']:
                        if col in df.columns:
                            # Use groupby to handle duplicate ASINs - take mean of numeric values
                            try:
                                if pd.api.types.is_numeric_dtype(df[col]):
                                    additional_data[col] = df.groupby('ASIN')[col].mean().to_dict()
                                else:
                                    # For non-numeric, take first value
                                    additional_data[col] = df.groupby('ASIN')[col].first().to_dict()
                            except Exception:
                                # Fallback: create empty mapping
                                additional_data[col] = {}
                    
                    # Add velocity scores if not present
                    if 'velocity_score' not in filtered_routes.columns:
                        velocity_scores = {}
                        for _, row in df.iterrows():
                            asin = row.get('ASIN')
                            if asin:
                                try:
                                    from analytics import velocity_index
                                    velocity_scores[asin] = velocity_index(row)
                                except Exception:
                                    velocity_scores[asin] = 0
                        filtered_routes['velocity_score'] = filtered_routes['asin'].map(velocity_scores).fillna(0)
                    
                    # Apply Amazon dominance filter
                    if 'Buy Box: % Amazon 90 days' in additional_data:
                        filtered_routes['amazon_dominance'] = filtered_routes['asin'].map(additional_data['Buy Box: % Amazon 90 days']).fillna(0)
                        filtered_routes = filtered_routes[filtered_routes['amazon_dominance'] <= max_amazon_dominance]
                    
                    # Apply advanced filters
                    if min_velocity > 0:
                        filtered_routes = filtered_routes[filtered_routes['velocity_score'] >= min_velocity]
                    
                    if max_amazon_share < 100:
                        if 'amazon_dominance' in filtered_routes.columns:
                            filtered_routes = filtered_routes[filtered_routes['amazon_dominance'] <= max_amazon_share]
                    
                    if min_rating > 1.0:
                        if 'Reviews Rating' in additional_data:
                            filtered_routes['rating'] = filtered_routes['asin'].map(additional_data['Reviews Rating']).fillna(0)
                            filtered_routes = filtered_routes[filtered_routes['rating'] >= min_rating]
                    
                    if max_return_rate < 50:
                        if 'Return Rate' in additional_data:
                            filtered_routes['return_rate'] = filtered_routes['asin'].map(additional_data['Return Rate']).fillna(0)
                            filtered_routes = filtered_routes[filtered_routes['return_rate'] <= max_return_rate]
                    
                    if only_historic_deals:
                        # Filter only historic deals
                        historic_asins = set(historic_deals_df['ASIN'].tolist() if 'ASIN' in historic_deals_df.columns else 
                                           historic_deals_df['asin'].tolist() if 'asin' in historic_deals_df.columns else [])
                        filtered_routes = filtered_routes[filtered_routes['asin'].isin(historic_asins)]
                    
                    if only_prime_eligible:
                        if 'Prime Eligible' in additional_data:
                            filtered_routes['prime_eligible'] = filtered_routes['asin'].map(additional_data['Prime Eligible']).fillna(False)
                            filtered_routes = filtered_routes[filtered_routes['prime_eligible'] == True]
                
                # Sort by Opportunity Score descending
                filtered_routes = filtered_routes.sort_values('opportunity_score', ascending=False)
                
                # Enhanced filter results display
                filtered_count = len(filtered_routes)
                filter_rate = filtered_count / original_count * 100 if original_count > 0 else 0
                
                # Mostra info su quante opportunità sono state filtrate geograficamente
                if 'Tutti' not in purchase_countries and len(purchase_countries) > 0:
                    st.info(f"🌍 Mostrando solo opportunità con acquisto in: {', '.join(purchase_countries)}")
                
                if filtered_count < original_count:
                    st.info(f"📊 Mostrando {filtered_count} di {original_count} ASIN ({filter_rate:.1f}% - {original_count - filtered_count} filtrati)")
                else:
                    st.info(f"📊 Mostrando tutti i {filtered_count} ASIN")
                
                if not filtered_routes.empty:
                    # Prepare consolidated data
                    consolidated_df = prepare_consolidated_data(filtered_routes)
                    
                    # Display risk alerts for high-risk opportunities
                    filtered_routes_with_risk = display_risk_alerts(filtered_routes)
                    
                    # Configure st.dataframe with column configuration
                    column_config = {
                        'ASIN': st.column_config.TextColumn('ASIN', width=120),
                        'Title': st.column_config.TextColumn('Title', width=300),
                        'Best Route': st.column_config.TextColumn('Best Route', width=100),
                        'Purchase Price €': st.column_config.TextColumn('Purchase Price €', width=130),
                        'Net Cost €': st.column_config.TextColumn('Net Cost €', width=110),
                        'Target Price €': st.column_config.TextColumn('Target Price €', width=120),
                        'Fees €': st.column_config.TextColumn('Fees €', width=80),
                        'Gross Margin €': st.column_config.TextColumn('Gross Margin €', width=130),
                        'Gross Margin %': st.column_config.TextColumn('Gross Margin %', width=120),
                        'ROI %': st.column_config.TextColumn('ROI %', width=80),
                        'Opportunity Score': st.column_config.TextColumn('Opportunity Score', width=150),
                        'Links': st.column_config.TextColumn('Links', width=80)
                    }
                    
                    # Display consolidated table
                    st.dataframe(
                        consolidated_df,
                        column_config=column_config,
                        hide_index=True,
                        use_container_width=True,
                        height=600
                    )
                    
                    # ASIN Selection for Detail Panel
                    st.markdown("---")
                    st.subheader("🔍 ASIN Detail Analysis")
                    
                    # Get available ASINs
                    available_asins = consolidated_df['ASIN'].tolist()
                    
                    if available_asins:
                        # Initialize session state for selected ASIN
                        if 'selected_asin' not in st.session_state:
                            st.session_state.selected_asin = None
                        
                        # ASIN selection with radio button
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            selected_asin = st.selectbox(
                                "Select ASIN for detailed analysis:",
                                options=[None] + available_asins,
                                format_func=lambda x: "Select an ASIN..." if x is None else x,
                                key="asin_selector"
                            )
                            
                            if selected_asin:
                                st.session_state.selected_asin = selected_asin
                        
                        with col2:
                            if st.session_state.selected_asin:
                                # Show selected product title
                                selected_title = consolidated_df[consolidated_df['ASIN'] == st.session_state.selected_asin]['Title'].iloc[0]
                                st.info(f"Selected: **{selected_title[:50]}{'...' if len(selected_title) > 50 else ''}**")
                        
                        # Detail Panel
                        if st.session_state.selected_asin:
                            with st.expander(f"🔎 Dettaglio ASIN: {st.session_state.selected_asin}", expanded=True):
                                # Get detail data
                                detail_data = get_asin_detail_data(st.session_state.selected_asin, df, filtered_routes)
                                
                                if detail_data:
                                    # A) METRICHE CHIAVE (4 colonne)
                                    st.markdown("### 📊 Key Metrics")
                                    
                                    col1, col2, col3, col4 = st.columns(4)
                                    
                                    with col1:
                                        # Opportunity Score Gauge
                                        gauge_fig = create_opportunity_gauge(detail_data['opportunity_score'])
                                        st.plotly_chart(gauge_fig, use_container_width=True)
                                    
                                    with col2:
                                        # ROI % with delta
                                        route_row = detail_data['route_row']
                                        current_roi = route_row['roi'] if route_row is not None else 0
                                        avg_roi = analysis['avg_roi']
                                        delta_roi = current_roi - avg_roi
                                        
                                        st.metric(
                                            label="ROI %",
                                            value=f"{current_roi:.1f}%",
                                            delta=f"{delta_roi:+.1f}%" if abs(delta_roi) > 0.1 else None
                                        )
                                    
                                    with col3:
                                        # Velocity Score Progress Bar
                                        st.markdown("**Velocity Score**")
                                        velocity_fig = create_progress_bar_chart(detail_data['velocity_score'], "Velocity")
                                        st.plotly_chart(velocity_fig, use_container_width=True)
                                    
                                    with col4:
                                        # Risk Score Progress Bar
                                        st.markdown("**Risk Score**")
                                        risk_fig = create_progress_bar_chart(detail_data['risk_score'], "Risk")
                                        st.plotly_chart(risk_fig, use_container_width=True)
                                    
                                    st.markdown("---")
                                    
                                    # B) BREAKDOWN CALCOLI
                                    st.subheader("💰 Breakdown Economico")
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.markdown("**📉 Costi**")
                                        
                                        if route_row is not None:
                                            st.metric("Purchase Price", f"€{route_row['purchase_price']:.2f}")
                                            st.metric("Net Cost", f"€{route_row['net_cost']:.2f}")
                                            
                                            # Fees breakdown
                                            fees = route_row.get('fees', {})
                                            if isinstance(fees, dict):
                                                st.write("**Fee Breakdown:**")
                                                if fees.get('referral', 0) > 0:
                                                    if DEBUG_MODE:
                                                        st.write(f"- Referral: €{fees['referral']:.2f}")
                                                if fees.get('fba', 0) > 0:
                                                    if DEBUG_MODE:
                                                        st.write(f"- FBA: €{fees['fba']:.2f}")
                                                if fees.get('shipping', 0) > 0:
                                                    if DEBUG_MODE:
                                                        st.write(f"- Shipping: €{fees['shipping']:.2f}")
                                                if DEBUG_MODE:
                                                    st.write(f"- **Total Fees: €{fees.get('total', 0):.2f}**")
                                    
                                    with col2:
                                        st.markdown("**📈 Ricavi**")
                                        
                                        if route_row is not None:
                                            st.metric("Target Price", f"€{route_row['target_price']:.2f}")
                                            st.metric("Gross Margin", f"€{route_row['gross_margin_eur']:.2f}")
                                            st.metric("Gross Margin %", f"{route_row['gross_margin_pct']:.1f}%")
                                            st.metric("ROI", f"{route_row['roi']:.1f}%")
                                            
                                            # ROI validation warning
                                            if route_row['roi'] > 50:
                                                st.warning('⚠️ ROI elevato - Verificare manualmente')
                                    
                                    st.markdown("---")
                                    
                                    # C) ANALISI STORICA
                                    st.subheader("📈 Analisi Prezzi Storici")
                                    
                                    # Historic deal flag
                                    if detail_data['is_historic_deal']:
                                        st.success("🔥 **AFFARE STORICO IDENTIFICATO!**")
                                        st.write("Questo prodotto presenta un'opportunità di mean reversion.")
                                    
                                    # Sparkline chart
                                    product_row = detail_data['product_row']
                                    sparkline_fig = create_price_sparkline(product_row)
                                    st.plotly_chart(sparkline_fig, use_container_width=True)
                                    
                                    # Historic metrics table
                                    historic_metrics = detail_data['historic_metrics']
                                    
                                    metrics_data = {
                                        'Period': ['Current', '30 days avg', '90 days avg', '180 days avg'],
                                        'Price (€)': [
                                            f"€{historic_metrics['current']:.2f}",
                                            f"€{historic_metrics['avg_30d']:.2f}",
                                            f"€{historic_metrics['avg_90d']:.2f}",
                                            f"€{historic_metrics['avg_180d']:.2f}"
                                        ],
                                        'Deviation': [
                                            "0.0%",
                                            f"{historic_metrics['dev_30d']:.1%}",
                                            f"{historic_metrics['dev_90d']:.1%}",
                                            f"{historic_metrics['dev_180d']:.1%}"
                                        ]
                                    }
                                    
                                    metrics_df = pd.DataFrame(metrics_data)
                                    st.dataframe(metrics_df, hide_index=True, use_container_width=True)
                                    
                                    st.markdown("---")
                                    
                                    # D) CONCORRENZA
                                    st.subheader("⚔️ Buy Box Dynamics")
                                    
                                    col1, col2, col3 = st.columns(3)
                                    
                                    with col1:
                                        # Amazon dominance
                                        amazon_dominance = product_row.get('Buy Box: % Amazon 90 days', 0)
                                        if pd.isna(amazon_dominance):
                                            amazon_dominance = 0
                                        
                                        st.markdown("**Amazon Dominance**")
                                        dominance_fig = create_progress_bar_chart(amazon_dominance, "Amazon %")
                                        st.plotly_chart(dominance_fig, use_container_width=True)
                                    
                                    with col2:
                                        # Competition metrics
                                        winner_count = product_row.get('Buy Box: Winner Count', 0)
                                        oos_pct = product_row.get('Buy Box: 90 days OOS', 0)
                                        
                                        st.metric("Winner Count", f"{winner_count:.0f}")
                                        st.metric("OOS %", f"{oos_pct:.1f}%")
                                    
                                    with col3:
                                        # Additional metrics
                                        offer_count = product_row.get('Offers: Count', 0)
                                        prime_eligible = "Yes" if product_row.get('Prime Eligible', False) else "No"
                                        
                                        st.metric("Offer Count", f"{offer_count:.0f}" if not pd.isna(offer_count) else "N/A")
                                        st.metric("Prime Eligible", prime_eligible)
                                    
                                    st.markdown("---")
                                    
                                    # E) LINK ESTERNI
                                    st.subheader("🔗 External Links")
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        # Amazon link
                                        amazon_url = f"https://www.amazon.it/dp/{st.session_state.selected_asin}"
                                        st.markdown(
                                            f'<a href="{amazon_url}" target="_blank" style="text-decoration:none;">'
                                            f'<div style="background-color:#ff0000;color:#ffffff;padding:10px;border-radius:5px;text-align:center;margin:5px;">'
                                            f'🛒 Apri su Amazon'
                                            f'</div></a>',
                                            unsafe_allow_html=True
                                        )
                                    
                                    with col2:
                                        # Keepa link
                                        keepa_url = f"https://keepa.com/#!product/8-{st.session_state.selected_asin}"
                                        st.markdown(
                                            f'<a href="{keepa_url}" target="_blank" style="text-decoration:none;">'
                                            f'<div style="background-color:#666666;color:#ffffff;padding:10px;border-radius:5px;text-align:center;margin:5px;">'
                                            f'📊 Vedi su Keepa'
                                            f'</div></a>',
                                            unsafe_allow_html=True
                                        )
                                
                                else:
                                    st.error("Unable to load detail data for this ASIN.")
                    else:
                        st.info("No products available for detailed analysis.")
                    
                else:
                    st.warning("⚠️ No products match the current filter criteria. Try adjusting the filters.")
                
                # Enhanced Export Section
                st.subheader("📥 Export e Watchlist")
                
                # Prepare current parameters for export
                current_params = {
                    'discount': discount,
                    'purchase_strategy': purchase_strategy,
                    'scenario': scenario,
                    'mode': mode,
                        'inbound_logistics': inbound_logistics,
                    'scoring_weights': {
                        'profit': profit_weight / total_weight,
                        'velocity': velocity_weight / total_weight,
                        'competition': competition_weight / total_weight
                    }
                }
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**📊 Export Completo**")
                    if st.button("📊 Prepara Export CSV", key="prepare_csv_export"):
                        try:
                            # Prepare export data from filtered routes (not consolidated display data)
                            export_df = filtered_routes.copy()
                            
                            # Add display columns for export
                            export_df['Best Route'] = export_df['source'].str.upper() + '->' + export_df['target'].str.upper()
                            export_df['Purchase Price €'] = export_df['purchase_price']
                            export_df['Net Cost €'] = export_df['net_cost']
                            export_df['Target Price €'] = export_df['target_price']
                            export_df['Gross Margin €'] = export_df['gross_margin_eur']
                            export_df['Gross Margin %'] = export_df['gross_margin_pct']
                            export_df['ROI %'] = export_df['roi']
                            export_df['Opportunity Score'] = export_df['opportunity_score']
                            
                            # Add additional analytics data
                            if not df.empty:
                                for idx, row in export_df.iterrows():
                                    asin = row['asin']
                                    original_row = df[df['ASIN'] == asin]
                                    
                                    if not original_row.empty:
                                        original_data = original_row.iloc[0]
                                        
                                        # Add analytics scores with error handling
                                        try:
                                            from analytics import velocity_index, risk_index, momentum_index, is_historic_deal
                                            export_df.loc[idx, 'velocity_score'] = velocity_index(original_data)
                                            export_df.loc[idx, 'risk_score'] = risk_index(original_data)
                                            export_df.loc[idx, 'momentum_score'] = momentum_index(original_data)
                                            export_df.loc[idx, 'is_historic_deal'] = is_historic_deal(original_data)
                                        except Exception as e:
                                            # Set default values if analytics fail
                                            export_df.loc[idx, 'velocity_score'] = 0
                                            export_df.loc[idx, 'risk_score'] = 0
                                            export_df.loc[idx, 'momentum_score'] = 0
                                            export_df.loc[idx, 'is_historic_deal'] = False
                                        
                                        # Add market data
                                        export_df.loc[idx, 'amazon_share'] = original_data.get('Buy Box: % Amazon 90 days', 0)
                                        export_df.loc[idx, 'sales_rank'] = original_data.get('Sales Rank: Current', 0)
                            
                            # Rename ASIN column for consistency
                            export_df['ASIN'] = export_df['asin']
                            export_df['Title'] = export_df['title']
                            
                            csv_data = export_consolidated_csv(export_df, action_ready=True)
                            
                            # Info about enhanced exports
                            st.info("""
                            **🚀 Enhanced Action-Ready Exports:**
                            • **CSV**: Action Required, Budget Needed, Expected Profit 30d, Break Even Units + Summary Row
                            • **Executive Summary**: Top 10 opportunities, investment analysis, 30/60/90-day ROI projections
                            • **Auto-sorted by ROI** for immediate business decisions
                            """)
                            
                            col_csv, col_exec = st.columns(2)
                            
                            with col_csv:
                                st.download_button(
                                    label="⬇️ CSV Action-Ready",
                                    data=csv_data,
                                    file_name=f"amazon_analyzer_action_ready_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                    mime="text/csv",
                                    key="download_csv"
                                )
                            
                            with col_exec:
                                # Generate Executive Summary
                                exec_summary = export_executive_summary(export_df, params)
                                st.download_button(
                                    label="📊 Executive Summary",
                                    data=exec_summary.encode('utf-8'),
                                    file_name=f"executive_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                                    mime="text/markdown",
                                    key="download_executive"
                                )
                            
                        except Exception as e:
                            st.error(f"Errore durante l'export CSV: {e}")
                
                with col2:
                    st.markdown("**📋 Watchlist**")
                    
                    # Initialize watchlist in session state
                    if 'watchlist_asins' not in st.session_state:
                        st.session_state.watchlist_asins = []
                    
                    # Multiselect for ASIN selection
                    available_asins = filtered_routes['asin'].tolist() if not filtered_routes.empty else []
                    
                    selected_asins = st.multiselect(
                        "Seleziona ASIN per Watchlist",
                        options=available_asins,
                        default=st.session_state.watchlist_asins,
                        key="watchlist_selector",
                        help="Seleziona uno o più ASIN per creare una watchlist personalizzata"
                    )
                    
                    # Update session state
                    st.session_state.watchlist_asins = selected_asins
                    
                    if selected_asins:
                        st.info(f"🔖 {len(selected_asins)} ASIN selezionati")
                        
                        if st.button("📋 Export Watchlist JSON", key="export_watchlist"):
                            try:
                                # Prepare data for watchlist export - use actual route data not display data
                                watchlist_routes = filtered_routes[filtered_routes['asin'].isin(selected_asins)].copy()
                                
                                # Add necessary display columns for export
                                watchlist_routes['ASIN'] = watchlist_routes['asin']
                                watchlist_routes['Title'] = watchlist_routes['title']
                                watchlist_routes['Best Route'] = watchlist_routes['source'].str.upper() + '->' + watchlist_routes['target'].str.upper()
                                watchlist_routes['Purchase Price €'] = watchlist_routes['purchase_price']
                                watchlist_routes['Net Cost €'] = watchlist_routes['net_cost']
                                watchlist_routes['Target Price €'] = watchlist_routes['target_price']
                                watchlist_routes['Gross Margin €'] = watchlist_routes['gross_margin_eur']
                                watchlist_routes['Gross Margin %'] = watchlist_routes['gross_margin_pct']
                                watchlist_routes['ROI %'] = watchlist_routes['roi']
                                watchlist_routes['Opportunity Score'] = watchlist_routes['opportunity_score']
                                
                                json_data = export_watchlist_json(selected_asins, watchlist_routes, current_params)
                                
                                st.download_button(
                                    label="⬇️ Download Watchlist",
                                    data=json_data,
                                    file_name=f"watchlist_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                                    mime="application/json",
                                    key="download_watchlist"
                                )
                                
                            except Exception as e:
                                st.error(f"Errore durante l'export watchlist: {e}")
                    else:
                        st.info("Seleziona alcuni ASIN per creare una watchlist")
                
                with col3:
                    st.markdown("**📄 Report Summary**")
                    if st.button("📄 Genera Report", key="generate_report"):
                        try:
                            # Prepare report data - use actual numeric data not formatted display data
                            report_df = filtered_routes.copy()
                            
                            # Add display columns for report
                            report_df['ASIN'] = report_df['asin']
                            report_df['Title'] = report_df['title']
                            report_df['Best Route'] = report_df['source'].str.upper() + '->' + report_df['target'].str.upper()
                            report_df['Opportunity Score'] = report_df['opportunity_score']
                            report_df['ROI %'] = report_df['roi']
                            
                            # Add is_historic_deal flag for report
                            if not df.empty:
                                historic_flags = {}
                                for _, row in df.iterrows():
                                    asin = row.get('ASIN')
                                    if asin:
                                        try:
                                            historic_flags[asin] = is_historic_deal(row)
                                        except Exception:
                                            historic_flags[asin] = False
                                
                                report_df['is_historic_deal'] = report_df['asin'].map(historic_flags).fillna(False)
                            
                            report_md = create_summary_report(report_df, current_params)
                            
                            st.download_button(
                                label="⬇️ Download Report MD",
                                data=report_md.encode('utf-8'),
                                file_name=f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                                mime="text/markdown",
                                key="download_report"
                            )
                            
                        except Exception as e:
                            st.error(f"Errore durante la generazione del report: {e}")
                
                # Validation info
                if not filtered_routes.empty:
                    with st.expander("ℹ️ Informazioni Export", expanded=False):
                        # Use actual data for validation, not display formatted data
                        validation_df = filtered_routes.copy()
                        validation_df['ASIN'] = validation_df['asin']
                        validation_df['Title'] = validation_df['title']
                        validation_df['Opportunity Score'] = validation_df['opportunity_score']
                        validation_df['ROI %'] = validation_df['roi']
                        
                        validation = validate_export_data(validation_df)
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Statistiche Dati:**")
                            if DEBUG_MODE:
                                st.write(f"- Righe: {validation['stats'].get('total_rows', 0)}")
                            if DEBUG_MODE:
                                st.write(f"- Colonne: {validation['stats'].get('total_columns', 0)}")
                            if DEBUG_MODE:
                                st.write(f"- Validazione: {'OK' if validation['is_valid'] else 'Errori'}")
                        
                        with col2:
                            if validation['warnings']:
                                st.write("**Avvisi:**")
                                for warning in validation['warnings']:
                                    st.write(f"- ⚠️ {warning}")
                            
                            if validation['errors']:
                                st.write("**Errori:**")
                                for error in validation['errors']:
                                    st.write(f"- ❌ {error}")
                
            else:
                st.warning("⚠️ No profitable opportunities found with current parameters. Try adjusting the minimum ROI and margin requirements.")
                
                # Show analysis anyway for debugging
                st.info(f"""
                **Analysis Summary:**
                - Total products analyzed: {analysis['total_products']}
                - Products meeting criteria: {analysis['profitable_products']}
                - Try lowering the minimum ROI or margin requirements in the sidebar.
                """)
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Please make sure your CSV file contains the required columns for Amazon product data.")
    
    else:
        # Welcome message
        st.info("👋 Welcome to Amazon Analyzer Pro!")
        st.markdown("""
        **Get started:**
        1. 📁 Upload your Amazon product data CSV file using the sidebar
        2. ⚙️ Configure analysis parameters
        3. 📊 View profitable arbitrage opportunities
        4. 📥 Export results for further analysis
        
        **Features:**
        - 🎯 Multi-market arbitrage analysis (IT, DE, FR, ES)
        - 💰 Complete P&L calculations with fees
        - 🚀 Opportunity scoring system
        - 📈 Interactive charts and visualizations
        - 📊 Customizable parameters and filters
        """)
        
        # Show sample data format
        with st.expander("📋 Required CSV Format"):
            st.markdown("""
            Your CSV file should contain these columns:
            - `ASIN`: Product identifier
            - `Title`: Product title
            - `Buy Box 🚚: Current`: Current buy box price
            - `Amazon: Current`: Amazon price
            - `Sales Rank: Current`: Sales rank
            - `Reviews Rating`: Product rating
            - `Buy Box: % Amazon 90 days`: Amazon buy box percentage
            - `Buy Box: Winner Count`: Number of buy box winners
            - Additional pricing and metrics columns...
            """)

if __name__ == "__main__":
    main()