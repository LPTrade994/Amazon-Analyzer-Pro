"""
UI/UX Improvements for Amazon Analyzer Pro - Sprint 4
"""

import streamlit as st
import pandas as pd

def add_responsive_css():
    """Add responsive CSS for better mobile/desktop experience"""
    responsive_css = """
    <style>
    /* Responsive layout improvements */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        .metric-card {
            margin: 5px 0;
            padding: 10px;
        }
        
        .metric-value {
            font-size: 1.8rem !important;
        }
        
        /* Mobile-friendly table */
        .dataframe {
            font-size: 0.8rem;
        }
        
        /* Mobile sidebar adjustments */
        .css-1d391kg {
            width: 100% !important;
        }
    }
    
    /* Enhanced visual hierarchy */
    .main-header {
        background: linear-gradient(90deg, #ff0000, #cc0000);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 8px rgba(255,0,0,0.3);
    }
    
    .section-header {
        background: linear-gradient(45deg, #1a1a1a, #2d2d2d);
        border-left: 4px solid #ff0000;
        padding: 15px;
        margin: 20px 0 10px 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* Enhanced metric cards */
    .metric-card-enhanced {
        background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
        border: 2px solid #ff0000;
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
        box-shadow: 0 4px 12px rgba(255,0,0,0.2);
        transition: all 0.3s ease;
    }
    
    .metric-card-enhanced:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(255,0,0,0.3);
        border-color: #ff3333;
    }
    
    /* Status indicators */
    .status-excellent {
        background: linear-gradient(45deg, #ff0000, #ff3333);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        animation: glow 2s infinite;
    }
    
    .status-good {
        background: linear-gradient(45deg, #ff6666, #ff9999);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    .status-poor {
        background: linear-gradient(45deg, #666666, #999999);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255,0,0,0.5); }
        50% { box-shadow: 0 0 20px rgba(255,0,0,0.8); }
    }
    
    /* Enhanced buttons */
    .stButton > button {
        background: linear-gradient(45deg, #ff0000, #cc0000);
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(255,0,0,0.3);
    }
    
    .stButton > button:hover {
        background: linear-gradient(45deg, #cc0000, #990000);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(255,0,0,0.4);
    }
    
    /* Progress indicators */
    .progress-container {
        background: #2d2d2d;
        border-radius: 10px;
        padding: 3px;
        margin: 5px 0;
    }
    
    .progress-bar {
        background: linear-gradient(90deg, #ff0000, #ff6666);
        border-radius: 8px;
        height: 8px;
        transition: width 1s ease;
    }
    
    /* Enhanced alerts */
    .custom-alert-success {
        background: linear-gradient(45deg, #1a4d1a, #2d6a2d);
        border: 1px solid #00ff00;
        border-radius: 8px;
        padding: 15px;
        color: #ffffff;
        margin: 10px 0;
    }
    
    .custom-alert-warning {
        background: linear-gradient(45deg, #4d4d1a, #6a6a2d);
        border: 1px solid #ffff00;
        border-radius: 8px;
        padding: 15px;
        color: #ffffff;
        margin: 10px 0;
    }
    
    .custom-alert-error {
        background: linear-gradient(45deg, #4d1a1a, #6a2d2d);
        border: 1px solid #ff0000;
        border-radius: 8px;
        padding: 15px;
        color: #ffffff;
        margin: 10px 0;
    }
    
    /* Loading animations */
    .loading-spinner {
        border: 4px solid #2d2d2d;
        border-top: 4px solid #ff0000;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin: 20px auto;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Enhanced data tables */
    .dataframe-container {
        background: #1a1a1a;
        border-radius: 8px;
        padding: 10px;
        border: 1px solid #333333;
        overflow-x: auto;
    }
    
    /* Tooltip styles */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 8px;
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
    </style>
    """
    return responsive_css

def create_enhanced_header():
    """Create enhanced header with gradient and better typography"""
    header_html = """
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">
            📊 Amazon Analyzer Pro
        </h1>
        <p style="margin: 10px 0 0 0; font-size: 1.1rem; opacity: 0.9;">
            Analisi Multi-Mercato per Arbitraggio Amazon EU
        </p>
    </div>
    """
    return header_html

def create_section_header(title: str, subtitle: str = "") -> str:
    """Create enhanced section headers"""
    subtitle_html = f"<p style='margin: 5px 0 0 0; opacity: 0.8; font-size: 0.9rem;'>{subtitle}</p>" if subtitle else ""
    
    return f"""
    <div class="section-header">
        <h2 style="margin: 0; color: #ff0000; font-size: 1.5rem;">{title}</h2>
        {subtitle_html}
    </div>
    """

def create_enhanced_metric_card(title: str, value: str, delta: str = None, status: str = "good") -> str:
    """Create enhanced metric cards with status indicators"""
    delta_html = ""
    if delta:
        status_class = f"status-{status}"
        delta_html = f'<div class="{status_class}" style="margin-top: 8px; font-size: 0.8rem;">{delta}</div>'
    
    return f"""
    <div class="metric-card-enhanced">
        <div style="font-size: 2.2rem; font-weight: bold; color: #ff0000; margin-bottom: 5px;">
            {value}
        </div>
        <div style="font-size: 1rem; color: #ffffff;">
            {title}
        </div>
        {delta_html}
    </div>
    """

def create_progress_indicator(percentage: float, label: str) -> str:
    """Create animated progress indicator"""
    return f"""
    <div style="margin: 10px 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="color: #ffffff; font-size: 0.9rem;">{label}</span>
            <span style="color: #ff0000; font-weight: bold;">{percentage:.1f}%</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar" style="width: {min(100, percentage)}%;"></div>
        </div>
    </div>
    """

def create_status_badge(score: float, thresholds: dict = None) -> str:
    """Create status badge based on score"""
    if thresholds is None:
        thresholds = {'excellent': 80, 'good': 60, 'poor': 0}
    
    if score >= thresholds['excellent']:
        status = "excellent"
        text = "ECCELLENTE"
        icon = "🔥"
    elif score >= thresholds['good']:
        status = "good"
        text = "BUONO"
        icon = "👍"
    else:
        status = "poor"
        text = "BASSO"
        icon = "⚠️"
    
    return f'<span class="status-{status}">{icon} {text} ({score:.0f})</span>'

def create_enhanced_alert(message: str, alert_type: str = "info") -> str:
    """Create enhanced alert boxes"""
    icons = {
        'success': '✅',
        'warning': '⚠️',
        'error': '❌',
        'info': 'ℹ️'
    }
    
    icon = icons.get(alert_type, 'ℹ️')
    
    return f"""
    <div class="custom-alert-{alert_type}">
        <strong>{icon} {message}</strong>
    </div>
    """

def create_loading_indicator(message: str = "Caricamento in corso...") -> str:
    """Create loading indicator with spinner"""
    return f"""
    <div style="text-align: center; padding: 20px;">
        <div class="loading-spinner"></div>
        <p style="color: #ffffff; margin-top: 10px;">{message}</p>
    </div>
    """

def add_keyboard_shortcuts_info():
    """Add keyboard shortcuts information"""
    shortcuts_html = """
    <div style="background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #ff0000; margin-bottom: 10px;">⌨️ Scorciatoie da Tastiera</h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.9rem;">
            <div><kbd style="background: #333; padding: 2px 6px; border-radius: 3px;">Ctrl + R</kbd> Ricarica dati</div>
            <div><kbd style="background: #333; padding: 2px 6px; border-radius: 3px;">Ctrl + E</kbd> Export CSV</div>
            <div><kbd style="background: #333; padding: 2px 6px; border-radius: 3px;">Ctrl + W</kbd> Watchlist</div>
            <div><kbd style="background: #333; padding: 2px 6px; border-radius: 3px;">Ctrl + F</kbd> Filtri</div>
        </div>
    </div>
    """
    return shortcuts_html

def create_data_quality_indicator(df: pd.DataFrame) -> str:
    """Create data quality indicator"""
    if df.empty:
        return create_enhanced_alert("Nessun dato caricato", "warning")
    
    total_rows = len(df)
    required_columns = ['ASIN', 'Title', 'Buy Box 🚚: Current']
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        quality_score = 30
        status = "poor"
        message = f"Colonne mancanti: {', '.join(missing_cols)}"
    else:
        # Calculate completeness
        completeness = df[required_columns].notna().all(axis=1).mean() * 100
        
        if completeness >= 95:
            quality_score = 95
            status = "excellent"
            message = "Qualità dati eccellente"
        elif completeness >= 80:
            quality_score = 80
            status = "good"
            message = "Qualità dati buona"
        else:
            quality_score = 60
            status = "poor"
            message = f"Qualità dati insufficiente ({completeness:.1f}% completo)"
    
    return f"""
    <div style="background: #1a1a1a; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #ff0000; margin-bottom: 10px;">📊 Qualità Dati</h4>
        {create_progress_indicator(quality_score, "Completezza Dati")}
        <p style="color: #ffffff; font-size: 0.9rem; margin-top: 5px;">{message}</p>
        <p style="color: #cccccc; font-size: 0.8rem;">Righe: {total_rows:,} | Colonne: {len(df.columns) if not df.empty else 0}</p>
    </div>
    """

def create_quick_actions_panel() -> str:
    """Create quick actions panel for common tasks"""
    return """
    <div style="background: #1a1a1a; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #ff0000; margin-bottom: 15px;">⚡ Azioni Rapide</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
            <button onclick="document.querySelector('[data-testid=stFileUploader]').click()" 
                    style="background: linear-gradient(45deg, #ff0000, #cc0000); color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer;">
                📁 Carica File
            </button>
            <button onclick="alert('Funzione Export attivata')" 
                    style="background: linear-gradient(45deg, #666666, #444444); color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer;">
                📊 Export Rapido
            </button>
            <button onclick="window.scrollTo(0, document.querySelector('.dataframe-container').offsetTop)" 
                    style="background: linear-gradient(45deg, #333333, #555555); color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer;">
                📋 Vai ai Risultati
            </button>
        </div>
    </div>
    """

# Export functions for use in main app
__all__ = [
    'add_responsive_css',
    'create_enhanced_header', 
    'create_section_header',
    'create_enhanced_metric_card',
    'create_progress_indicator',
    'create_status_badge',
    'create_enhanced_alert',
    'create_loading_indicator',
    'add_keyboard_shortcuts_info',
    'create_data_quality_indicator',
    'create_quick_actions_panel'
]