"""
UI Polish & Error Handling - Amazon Analyzer Pro
Implementa miglioramenti finali per UX professionale
"""

import streamlit as st
import pandas as pd
import traceback
from typing import Dict, Any, Optional
import plotly.graph_objects as go


# ERROR HANDLING USER-FRIENDLY
def show_user_friendly_error(error_type: str, details: str = "", solution: str = "") -> None:
    """
    Mostra errori comprensibili all'utente con soluzioni suggerite
    
    Args:
        error_type: Tipo di errore (KeyError, ValueError, etc.)
        details: Dettagli specifici dell'errore
        solution: Soluzione suggerita
    """
    error_messages = {
        'KeyError': {
            'title': '🚫 Colonna Mancante nel Dataset',
            'description': 'Il file CSV non contiene una colonna richiesta per l\'analisi.',
            'default_solution': 'Verifica che il file contenga le colonne essenziali: ASIN, Title, Buy Box Current.'
        },
        'ValueError': {
            'title': '⚠️ Formato Dati Non Valido',
            'description': 'I dati nel file non sono nel formato atteso.',
            'default_solution': 'Controlla che i prezzi siano numerici e le date nel formato corretto.'
        },
        'FileNotFoundError': {
            'title': '📁 File Non Trovato',
            'description': 'Il file specificato non è stato trovato.',
            'default_solution': 'Verifica che il file esista e sia accessibile.'
        },
        'PermissionError': {
            'title': '🔒 Permessi Insufficienti',
            'description': 'Non hai i permessi per accedere al file.',
            'default_solution': 'Verifica di avere i permessi di lettura per il file.'
        },
        'UnicodeDecodeError': {
            'title': '📝 Errore di Codifica',
            'description': 'Il file non può essere letto con la codifica corrente.',
            'default_solution': 'Salva il file in formato UTF-8 o CSV standard.'
        },
        'EmptyDataError': {
            'title': '📊 Dataset Vuoto',
            'description': 'Il file caricato non contiene dati validi.',
            'default_solution': 'Carica un file CSV con almeno una riga di dati.'
        }
    }
    
    error_info = error_messages.get(error_type, {
        'title': '❌ Errore Imprevisto',
        'description': 'Si è verificato un errore durante l\'elaborazione.',
        'default_solution': 'Riprova o contatta il supporto se il problema persiste.'
    })
    
    # Container per errore con styling
    with st.container():
        st.markdown(f"""
        <div style="
            background: linear-gradient(45deg, #4d1a1a, #6a2d2d);
            border: 2px solid #ff0000;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            color: #ffffff;
        ">
            <h3 style="margin: 0 0 10px 0; color: #ff6666;">{error_info['title']}</h3>
            <p style="margin: 0 0 15px 0; font-size: 1.1rem;">{error_info['description']}</p>
            
            {f'<div style="background: #1a1a1a; padding: 10px; border-radius: 6px; margin: 10px 0;"><strong>Dettagli:</strong> {details}</div>' if details else ''}
            
            <div style="background: #1a4d1a; padding: 15px; border-radius: 8px; border-left: 4px solid #00ff00;">
                <strong>💡 Soluzione Suggerita:</strong><br>
                {solution or error_info['default_solution']}
            </div>
        </div>
        """, unsafe_allow_html=True)


def create_help_tooltip(content: str, icon: str = "❓") -> str:
    """
    Crea tooltip di aiuto per elementi UI
    
    Args:
        content: Contenuto del tooltip
        icon: Icona da mostrare
        
    Returns:
        str: HTML per tooltip
    """
    tooltip_id = f"tooltip_{hash(content) % 10000}"
    
    return f"""
    <div class="tooltip-container" style="display: inline-block; position: relative;">
        <span class="tooltip-trigger" style="
            background: #ff0000;
            color: white;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            cursor: help;
            margin-left: 5px;
        ">{icon}</span>
        
        <div class="tooltip-content" id="{tooltip_id}" style="
            visibility: hidden;
            position: absolute;
            background: #333333;
            color: white;
            padding: 10px;
            border-radius: 6px;
            font-size: 0.85rem;
            max-width: 250px;
            bottom: 125%;
            left: 50%;
            margin-left: -125px;
            z-index: 1000;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            opacity: 0;
            transition: opacity 0.3s;
        ">
            {content}
            <div style="
                position: absolute;
                top: 100%;
                left: 50%;
                margin-left: -5px;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #333333;
            "></div>
        </div>
    </div>
    
    <style>
    .tooltip-container:hover .tooltip-content {{
        visibility: visible;
        opacity: 1;
    }}
    </style>
    """


def create_info_box(title: str, content: str, box_type: str = "info") -> str:
    """
    Crea info box per parametri critici
    
    Args:
        title: Titolo del box
        content: Contenuto informativo
        box_type: Tipo (info, warning, success, critical)
        
    Returns:
        str: HTML per info box
    """
    colors = {
        'info': {'bg': '#1a1a4d', 'border': '#0066ff', 'icon': 'ℹ️'},
        'warning': {'bg': '#4d4d1a', 'border': '#ffff00', 'icon': '⚠️'},
        'success': {'bg': '#1a4d1a', 'border': '#00ff00', 'icon': '✅'},
        'critical': {'bg': '#4d1a1a', 'border': '#ff0000', 'icon': '🚨'}
    }
    
    color = colors.get(box_type, colors['info'])
    
    return f"""
    <div style="
        background: linear-gradient(45deg, {color['bg']}, {color['bg']}dd);
        border: 2px solid {color['border']};
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: #ffffff;
    ">
        <h4 style="margin: 0 0 8px 0; color: {color['border']};">
            {color['icon']} {title}
        </h4>
        <p style="margin: 0; line-height: 1.4;">{content}</p>
    </div>
    """


def add_responsive_css():
    """Aggiunge CSS responsive e miglioramenti accessibilità"""
    css = """
    <style>
    /* Responsive Design */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }
        
        .stDataFrame {
            font-size: 0.8rem;
        }
        
        .metric-card {
            margin: 5px 0;
            padding: 10px;
        }
        
        .stButton > button {
            width: 100%;
            margin: 5px 0;
        }
        
        .stSelectbox, .stSlider {
            margin-bottom: 1rem;
        }
    }
    
    @media (max-width: 480px) {
        .main .block-container {
            padding: 0.25rem;
        }
        
        .stDataFrame {
            font-size: 0.7rem;
        }
        
        h1 { font-size: 1.8rem; }
        h2 { font-size: 1.4rem; }
        h3 { font-size: 1.2rem; }
    }
    
    /* Accessibility Improvements */
    .stButton > button:focus,
    .stSelectbox > div > div:focus,
    .stSlider > div:focus {
        outline: 2px solid #ff0000;
        outline-offset: 2px;
    }
    
    /* High Contrast for Dark Theme */
    .stMarkdown {
        color: #ffffff;
    }
    
    .stSelectbox > div > div {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #666666;
    }
    
    .stTextInput > div > div > input {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #666666;
    }
    
    /* Smooth Loading Animations */
    .loading-pulse {
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Enhanced Badge Styling */
    .badge-high {
        background: linear-gradient(45deg, #ff0000, #ff3333);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        box-shadow: 0 2px 4px rgba(255,0,0,0.3);
        animation: glow 2s infinite;
    }
    
    .badge-medium {
        background: linear-gradient(45deg, #ff6666, #ff9999);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        box-shadow: 0 2px 4px rgba(255,102,102,0.3);
    }
    
    .badge-low {
        background: linear-gradient(45deg, #666666, #999999);
        color: white;
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        box-shadow: 0 2px 4px rgba(102,102,102,0.3);
    }
    
    @keyframes glow {
        0%, 100% { box-shadow: 0 2px 4px rgba(255,0,0,0.3); }
        50% { box-shadow: 0 4px 12px rgba(255,0,0,0.6); }
    }
    
    /* Consistent Icons and Spacing */
    .icon-button {
        background: none;
        border: none;
        font-size: 1.2rem;
        margin: 0 5px;
        padding: 5px;
        cursor: pointer;
        transition: transform 0.2s;
    }
    
    .icon-button:hover {
        transform: scale(1.1);
    }
    
    /* Enhanced Table Styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .dataframe th {
        background: linear-gradient(45deg, #ff0000, #cc0000);
        color: white;
        font-weight: bold;
        padding: 12px 8px;
        text-align: center;
    }
    
    .dataframe td {
        padding: 10px 8px;
        border-bottom: 1px solid #333333;
    }
    
    .dataframe tr:hover {
        background-color: #2d2d2d;
    }
    
    /* Loading States */
    .loading-container {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        color: #ffffff;
    }
    
    .loading-spinner {
        border: 3px solid #333333;
        border-top: 3px solid #ff0000;
        border-radius: 50%;
        width: 30px;
        height: 30px;
        animation: spin 1s linear infinite;
        margin-right: 10px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    /* Sidebar Enhancements */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a1a, #2d2d2d);
        border-right: 2px solid #ff0000;
    }
    
    /* Focus Management for Keyboard Navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #2d2d2d;
        color: #ffffff;
        border-radius: 4px 4px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #ff0000;
        color: #ffffff;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def create_loading_indicator(message: str = "Elaborazione in corso...") -> str:
    """
    Crea indicatore di caricamento animato
    
    Args:
        message: Messaggio da mostrare
        
    Returns:
        str: HTML per loading indicator
    """
    return f"""
    <div class="loading-container">
        <div class="loading-spinner"></div>
        <span>{message}</span>
    </div>
    """


def create_progress_tracker(current_step: int, total_steps: int, step_names: list) -> str:
    """
    Crea tracker del progresso per workflow multi-step
    
    Args:
        current_step: Step corrente (1-based)
        total_steps: Numero totale di step
        step_names: Nomi degli step
        
    Returns:
        str: HTML per progress tracker
    """
    steps_html = ""
    
    for i, step_name in enumerate(step_names, 1):
        if i < current_step:
            # Step completato
            status = "completed"
            icon = "✅"
            color = "#00ff00"
        elif i == current_step:
            # Step corrente
            status = "current"
            icon = "🔄"
            color = "#ff0000"
        else:
            # Step futuro
            status = "pending"
            icon = "⏳"
            color = "#666666"
        
        steps_html += f"""
        <div style="
            display: flex;
            align-items: center;
            margin: 5px 0;
            padding: 8px;
            background: {'#1a4d1a' if status == 'completed' else '#4d1a1a' if status == 'current' else '#1a1a1a'};
            border-radius: 6px;
            border-left: 3px solid {color};
        ">
            <span style="font-size: 1.2rem; margin-right: 10px;">{icon}</span>
            <span style="color: {color}; font-weight: {'bold' if status != 'pending' else 'normal'};">
                {step_name}
            </span>
        </div>
        """
    
    return f"""
    <div style="
        background: #1a1a1a;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
        border: 1px solid #333333;
    ">
        <h4 style="color: #ff0000; margin-bottom: 10px;">📊 Progresso Analisi</h4>
        {steps_html}
        <div style="
            margin-top: 10px;
            text-align: center;
            color: #cccccc;
            font-size: 0.9rem;
        ">
            Step {current_step} di {total_steps}
        </div>
    </div>
    """


def create_keyboard_shortcuts_panel() -> str:
    """Crea pannello scorciatoie da tastiera per accessibilità"""
    return """
    <div style="
        background: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    ">
        <h4 style="color: #ff0000; margin-bottom: 10px;">⌨️ Scorciatoie da Tastiera</h4>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; font-size: 0.9rem;">
            <div style="display: flex; justify-content: space-between;">
                <span>Ricarica pagina:</span>
                <kbd style="background: #333; color: #fff; padding: 2px 6px; border-radius: 3px;">F5</kbd>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Focus sidebar:</span>
                <kbd style="background: #333; color: #fff; padding: 2px 6px; border-radius: 3px;">Tab</kbd>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Scroll risultati:</span>
                <kbd style="background: #333; color: #fff; padding: 2px 6px; border-radius: 3px;">↑↓</kbd>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Apri help:</span>
                <kbd style="background: #333; color: #fff; padding: 2px 6px; border-radius: 3px;">?</kbd>
            </div>
        </div>
    </div>
    """


def handle_file_upload_errors(uploaded_file) -> Optional[pd.DataFrame]:
    """
    Gestisce errori durante l'upload file con messaggi user-friendly
    
    Args:
        uploaded_file: File caricato da Streamlit
        
    Returns:
        Optional[pd.DataFrame]: DataFrame se successo, None se errore
    """
    if uploaded_file is None:
        return None
        
    try:
        # Verifica dimensione file
        if uploaded_file.size > 50 * 1024 * 1024:  # 50MB
            show_user_friendly_error(
                'ValueError',
                f'File troppo grande: {uploaded_file.size / 1024 / 1024:.1f}MB',
                'Usa file CSV sotto i 50MB o suddividi i dati in file più piccoli.'
            )
            return None
        
        # Verifica estensione
        if not uploaded_file.name.lower().endswith('.csv'):
            show_user_friendly_error(
                'ValueError',
                f'Formato file non supportato: {uploaded_file.name}',
                'Carica solo file CSV. Se hai un file Excel, salvalo come CSV.'
            )
            return None
        
        # Tentativo di lettura CSV
        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            # Riprova con encoding latino
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding='latin-1')
        
        # Verifica contenuto
        if df.empty:
            show_user_friendly_error(
                'EmptyDataError',
                'Il file CSV non contiene dati',
                'Verifica che il file contenga almeno una riga con dati oltre all\'header.'
            )
            return None
        
        # Verifica colonne essenziali
        required_columns = ['ASIN', 'Title']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            show_user_friendly_error(
                'KeyError',
                f'Colonne mancanti: {", ".join(missing_columns)}',
                f'Aggiungi le colonne mancanti: {", ".join(missing_columns)}. Verifica che l\'header sia nella prima riga.'
            )
            return None
        
        # Verifica dati validi in colonne critiche
        if df['ASIN'].isna().sum() > len(df) * 0.5:
            show_user_friendly_error(
                'ValueError',
                'Troppi ASIN mancanti o vuoti',
                'Verifica che la colonna ASIN contenga identificativi prodotto validi.'
            )
            return None
        
        return df
        
    except PermissionError:
        show_user_friendly_error(
            'PermissionError',
            'File in uso da un\'altra applicazione',
            'Chiudi Excel o altre applicazioni che potrebbero aver aperto il file.'
        )
        return None
        
    except Exception as e:
        show_user_friendly_error(
            type(e).__name__,
            str(e),
            'Verifica che il file sia un CSV valido e riprova. Se il problema persiste, contatta il supporto.'
        )
        return None


def create_feature_tour() -> str:
    """Crea tour guidato delle funzionalità"""
    return """
    <div style="
        background: linear-gradient(45deg, #1a1a4d, #2d2d6d);
        border: 2px solid #0066ff;
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        color: #ffffff;
    ">
        <h3 style="margin: 0 0 15px 0; color: #66aaff;">🎯 Guida Rapida</h3>
        
        <div style="margin: 10px 0;">
            <strong>1. 📁 Caricamento Dati</strong><br>
            Carica i tuoi file CSV con dati Amazon. Supportati IT, DE, FR, ES.
        </div>
        
        <div style="margin: 10px 0;">
            <strong>2. ⚙️ Configurazione</strong><br>
            Imposta sconto, strategia acquisto e parametri di analisi.
        </div>
        
        <div style="margin: 10px 0;">
            <strong>3. 📊 Analisi</strong><br>
            Visualizza opportunità con Opportunity Score e filtri avanzati.
        </div>
        
        <div style="margin: 10px 0;">
            <strong>4. 🔍 Dettaglio ASIN</strong><br>
            Analizza singoli prodotti con metriche complete e grafici.
        </div>
        
        <div style="margin: 10px 0;">
            <strong>5. 📥 Export</strong><br>
            Esporta risultati in CSV, crea watchlist JSON o report.
        </div>
        
        <div style="
            background: #1a4d1a;
            padding: 10px;
            border-radius: 6px;
            margin-top: 15px;
            border-left: 3px solid #00ff00;
        ">
            <strong>💡 Suggerimento:</strong> Inizia con file piccoli (< 100 prodotti) per familiarizzare con l'interfaccia.
        </div>
    </div>
    """


def create_accessibility_statement() -> str:
    """Crea dichiarazione di accessibilità"""
    return """
    <div style="
        background: #1a1a1a;
        border: 1px solid #333333;
        border-radius: 8px;
        padding: 15px;
        margin: 20px 0;
        font-size: 0.9rem;
        color: #cccccc;
    ">
        <h4 style="color: #ff0000; margin-bottom: 10px;">♿ Accessibilità</h4>
        <p>Questa applicazione è progettata per essere accessibile:</p>
        <ul style="margin: 10px 0; padding-left: 20px;">
            <li>✅ Navigazione da tastiera supportata</li>
            <li>✅ Contrasto colori ottimizzato per il tema dark</li>
            <li>✅ Testo alternativo per grafici e visualizzazioni</li>
            <li>✅ Layout responsive per dispositivi mobili</li>
            <li>✅ Font leggibili e dimensioni appropriate</li>
        </ul>
        <p style="margin-top: 10px;">
            Per segnalare problemi di accessibilità o suggerimenti: 
            <a href="mailto:support@amazon-analyzer-pro.com" style="color: #ff6666;">support@amazon-analyzer-pro.com</a>
        </p>
    </div>
    """


# Funzioni helper per componenti comuni
def safe_execute(func, error_context: str = "operazione", *args, **kwargs):
    """
    Esegue funzione con gestione errori sicura
    
    Args:
        func: Funzione da eseguire
        error_context: Contesto dell'errore per messaggio user-friendly
        *args, **kwargs: Argomenti per la funzione
        
    Returns:
        Risultato della funzione o None se errore
    """
    try:
        return func(*args, **kwargs)
    except KeyError as e:
        show_user_friendly_error(
            'KeyError',
            f'Colonna mancante durante {error_context}: {str(e)}',
            'Verifica che il dataset contenga tutte le colonne richieste.'
        )
        return None
    except ValueError as e:
        show_user_friendly_error(
            'ValueError',
            f'Valore non valido durante {error_context}: {str(e)}',
            'Controlla che i dati numerici siano nel formato corretto.'
        )
        return None
    except Exception as e:
        show_user_friendly_error(
            type(e).__name__,
            f'Errore durante {error_context}: {str(e)}',
            'Riprova o contatta il supporto se il problema persiste.'
        )
        return None


def create_status_indicator(status: str, message: str) -> str:
    """
    Crea indicatore di stato colorato
    
    Args:
        status: Stato (success, warning, error, info)
        message: Messaggio da mostrare
        
    Returns:
        str: HTML per indicatore
    """
    colors = {
        'success': {'bg': '#1a4d1a', 'border': '#00ff00', 'icon': '✅'},
        'warning': {'bg': '#4d4d1a', 'border': '#ffff00', 'icon': '⚠️'},
        'error': {'bg': '#4d1a1a', 'border': '#ff0000', 'icon': '❌'},
        'info': {'bg': '#1a1a4d', 'border': '#0066ff', 'icon': 'ℹ️'}
    }
    
    color = colors.get(status, colors['info'])
    
    return f"""
    <div style="
        background: {color['bg']};
        border: 1px solid {color['border']};
        border-radius: 6px;
        padding: 10px 15px;
        margin: 10px 0;
        color: #ffffff;
        display: flex;
        align-items: center;
    ">
        <span style="margin-right: 8px; font-size: 1.1rem;">{color['icon']}</span>
        <span>{message}</span>
    </div>
    """


# Export delle funzioni principali
__all__ = [
    'show_user_friendly_error',
    'create_help_tooltip', 
    'create_info_box',
    'add_responsive_css',
    'create_loading_indicator',
    'create_progress_tracker',
    'create_keyboard_shortcuts_panel',
    'handle_file_upload_errors',
    'create_feature_tour',
    'create_accessibility_statement',
    'safe_execute',
    'create_status_indicator'
]