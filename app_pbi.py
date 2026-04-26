import base64
import os
import re
import sys
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

if "env" not in st.session_state:
    st.session_state.env = os.getenv("ENV", "dev")

# Make local modules importable (all flat in this directory)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from constants import Streamlit
from glossary_loader import read_glossary, save_glossary
from glossary_path import glossary
from pbi_query import (
    ask_iagen_finance,
    ask_iagen_rag,
    build_report_link_map,
    filter_embeddings_by_team_in_memory,
    filter_metadata_by_team,
    load_metadata,
)
from prompts import prompts

# Configuration de la page
st.set_page_config(
    page_title="Power BI Navigation Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Variables de session
if 'team' not in st.session_state:
    st.session_state['team'] = None
if 'generated' not in st.session_state:
    st.session_state['generated'] = []
if 'past' not in st.session_state:
    st.session_state['past'] = []
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'stats' not in st.session_state:
    st.session_state['stats'] = ""
if "connected" not in st.session_state:
    st.session_state.connected = False
if 'ia_resources' not in st.session_state:
    st.session_state.ia_resources = {
        'glossary':{},
        'uploaded_files':[],
        'custom_rules':""
    }

# Available teams (must match keys in `prompts.py` and `data/team_workspace_mapping.json`)
TEAMS = {
    "Finance": "",
    "Data Management": "",
    "Engineering": "",
    "Other": "",
}

# Fonction pour convertir une image en base64
def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def _data_path(filename: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", filename)


def power_bi_stats(metadata):
    # Initialiser des compteurs
    ws = set()
    rs = 0
    ps = 0

    # Analyser les métadonnées
    for item in metadata:
        # Ajouter le workspace à un set pour éviter les doublons
        ws.add(item["workspace"])
        
        # Compter les rapports
        rs += 1
        
        # Compter les pages
        ps += len(item["pages"])

    # Afficher les résultats
    print(f"Nombre de workspaces: {len(ws)}")
    print(f"Nombre de rapports: {rs}")
    print(f"Nombre de pages: {ps}")
    return len(ws), rs, ps

# Page de Connexion
def login_page():
    logo_path = Streamlit.LOGO_URL
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        logo_base64 = image_to_base64(logo)
    else:
        logo_base64 = ""

    st.markdown(f"""
        <style>
        /* Background global pour le login */
        .stApp {{
            background: linear-gradient(135deg, #f8f9fe 0%, #fefeff 100%);
        }}
        
        .login-container {{
            max-width: 550px;
            margin: 2rem auto;
            padding: 3rem 2.5rem;
            background: white;
            border-radius: 24px;
            box-shadow: 0 20px 60px rgba(107, 33, 141, 0.15);
        }}
        .login-logo {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .login-title {{
            font-size: 2.2rem;
            font-weight: 700;
            text-align: center;
            background: linear-gradient(135deg, #581D74 0%, #9531C4 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            line-height: 1.3;
        }}
        .login-subtitle {{
            color: #666666;
            text-align: center;
            font-size: 1.1rem;
            margin-bottom: 2.5rem;
            font-weight: 400;
        }}
        .stButton > button {{
            background: linear-gradient(135deg, #76279B 0%, #9531C4 100%);
            color: white;
            border: none;
            border-radius: 16px;
            padding: 1.1rem 2rem;
            font-weight: 600;
            font-size: 1.05rem;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(107, 33, 141, 0.2);
            margin: 0.6rem 0;
        }}
        .stButton > button:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 24px rgba(107, 33, 141, 0.35);
            background: linear-gradient(135deg, #6B218D 0%, #9531C4 100%);
        }}
        .stButton > button:active {{
            transform: translateY(-1px);
        }}
        </style>
        
        <div class="login-container">
            <div class="login-logo">
                <img src="data:image/png;base64,{logo_base64}" style="height:90px;"/>
            </div>
            <h1 class="login-title">Power BI Navigation Assistant</h1>
            <p class="login-subtitle">Select your team to continue</p>
        </div>
    """, unsafe_allow_html=True)

    for team, emoji in TEAMS.items():
        if st.button(f"{emoji} {team}", key=f"team_{team}", use_container_width=True):
            st.session_state['team'] = team
            st.session_state['connected'] = True
            st.session_state['messages'] = []
            st.rerun()

def build_enhanced_context():
    team = st.session_state['team']
    base_context = "Here are knowledge that can help the research:\n"
    file_path = glossary.get(team, "")

    if not file_path:
        st.info("No glossary available for this team yet.")
        return base_context

    try:
        df = read_glossary(file_path)

        # Custom CSS pour le glossaire
        st.markdown("""
            <style>
            .glossary-container {
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 16px rgba(107, 33, 141, 0.08);
                border: 1px solid rgba(107, 33, 141, 0.12);
                margin: 1rem 0;
            }
            
            .glossary-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 1.5rem;
                padding-bottom: 1rem;
                border-bottom: 2px solid rgba(107, 33, 141, 0.1);
            }
            
            .glossary-title {
                color: #6B218D;
                font-size: 1.3rem;
                font-weight: 600;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }
            
            .glossary-icon {
                width: 32px;
                height: 32px;
                background: linear-gradient(135deg, #6B218D 0%, #9531C4 100%);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 18px;
            }
            
            .glossary-count {
                background: linear-gradient(135deg, rgba(107, 33, 141, 0.1) 0%, rgba(149, 49, 196, 0.1) 100%);
                color: #6B218D;
                font-size: 0.85rem;
                font-weight: 600;
                padding: 0.4rem 0.85rem;
                border-radius: 12px;
                border: 1px solid rgba(107, 33, 141, 0.2);
            }
            
            .glossary-info {
                background: rgba(81, 160, 162, 0.08);
                border-left: 3px solid #51A0A2;
                border-radius: 8px;
                padding: 1rem 1.25rem;
                margin: 1rem 0 1.5rem 0;
                color: #2c3e50;
                font-size: 0.9rem;
                line-height: 1.6;
            }
            
            /* Style pour le data editor */
            [data-testid="stDataFrame"] {
                border-radius: 12px;
                overflow: hidden;
                border: 1px solid rgba(107, 33, 141, 0.12);
            }
            
            /* Style pour le bouton de mise à jour */
            .update-button-container {
                margin-top: 1.5rem;
                padding-top: 1.5rem;
                border-top: 1px solid rgba(107, 33, 141, 0.1);
                display: flex;
                justify-content: flex-end;
            }
            </style>
        """, unsafe_allow_html=True)

        # Header du glossaire
        st.markdown(f"""
            <div class="glossary-container">
                <div class="glossary-header">
                    <div class="glossary-title">
                        <div class="glossary-icon">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                <path d="M9 7h6M9 11h6M9 15h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                            </svg>
                        </div>
                        Knowledge Base
                    </div>
                    <div class="glossary-count">
                        {len(df)} entries
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Info box
        st.markdown("""
            <div class="glossary-info">
                <strong>About this knowledge base:</strong> This glossary contains domain-specific definitions and concepts that enhance the AI assistant's understanding of your queries. You can edit entries directly in the table below.
            </div>
        """, unsafe_allow_html=True)

        # Afficher le DataFrame éditable avec une config améliorée
        edited_df = st.data_editor(
            df,
            key="data_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            column_config={
                col: st.column_config.TextColumn(
                    col,
                    width="medium",
                    help=f"Edit {col}"
                ) for col in df.columns
            }
        )

        # Bouton de mise à jour stylisé
        st.markdown('<div class="update-button-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col3:
            if st.button("Save Changes", use_container_width=True, type="primary"):
                link = save_glossary(edited_df, file_path)
                st.success("✓ Knowledge base updated successfully!")
                if link and link.startswith("http"):
                    st.caption(f"[View file]({link})")
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Construire le contexte à partir des données
        for row in edited_df.to_dict(orient='records'):
            base_context += str(row) + "\n"
            
    except Exception as e:
        st.error(f"⚠ Error loading knowledge base: {str(e)}")
        st.caption("Please verify that the glossary file exists and is accessible.")

    return base_context

# Page du chatbot
def chat_page():
    team = st.session_state['team']
    metadata = load_metadata(_data_path("metadata.json"))
    mapping = load_metadata(_data_path("team_workspace_mapping.json"))

    filtered_metadata = filter_metadata_by_team(metadata=metadata, mapping=mapping, team=team)

    embeddings_path = _data_path("metadata_embeddings.npy")
    metadata_path = _data_path("metadata_entries.pkl")

    if not (os.path.exists(embeddings_path) and os.path.exists(metadata_path)):
        st.warning(
            "Embeddings not found. Run `python embeddings_metadata.py` once "
            "to bootstrap the index. Smart-search mode is disabled until then."
        )
        metadata_embeddings, metadata_entries = None, None
    else:
        metadata_embeddings, metadata_entries = filter_embeddings_by_team_in_memory(
            embeddings_path=embeddings_path,
            metadata_path=metadata_path,
            mapping=mapping,
            target_team=team,
        )

    report_link_map = build_report_link_map(filtered_metadata)

    intro = prompts[team]["intro"]
    instructions = prompts[team]["instructions"]

    # ============================================
    # CSS GLOBAL ULTRA-PROFESSIONNEL
    # ============================================
    st.markdown("""
        <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* ============================================
        MASQUER LE BOUTON DE COLLAPSE - IMPROVED
        ============================================ */

        /* Masquer tous les éléments de contrôle de la sidebar */
        [data-testid="stSidebarCollapse"],
        [data-testid="collapsedControl"],
        button[kind="header"],
        section[data-testid="stSidebar"] button[kind="header"],
        section[data-testid="stSidebar"] > div > div:first-child > button,
        section[data-testid="stSidebar"] header button,
        [data-testid="stSidebar"] button[aria-label*="close"],
        [data-testid="stSidebar"] button[aria-label*="Close"],
        div[data-testid="stSidebarNav"] + div > button {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0 !important;
            height: 0 !important;
        }

        /* Masquer l'icône chevron/arrow */
        [data-testid="stSidebar"] button svg,
        [data-testid="stSidebar"] header svg {
            display: none !important;
        }

        /* S'assurer que le header de la sidebar n'a pas de padding pour le bouton */
        [data-testid="stSidebar"] > div > div:first-child {
            padding-top: 1rem !important;
        }

        /* Empêcher le collapse via CSS */
        [data-testid="stSidebar"][aria-expanded="false"],
        [data-testid="stSidebar"][aria-expanded="true"] {
            transform: translateX(0) !important;
            margin-left: 0 !important;
        }
                        
        /* ============================================
           FORCER SIDEBAR TOUJOURS OUVERTE
           ============================================ */
        
        /* Largeur sidebar fixe */
        section[data-testid="stSidebar"] {
            min-width: 21rem !important;
            max-width: 21rem !important;
        }
        
        section[data-testid="stSidebar"] > div:first-child {
            min-width: 21rem !important;
            max-width: 21rem !important;
        }

        /* Forcer la sidebar à rester visible avec largeur fixe */
        section[data-testid="stSidebar"] {
            min-width: 21rem !important;
            max-width: 21rem !important;
            width: 21rem !important;
            transform: none !important;
            transition: none !important;
        }
        
        section[data-testid="stSidebar"] > div:first-child {
            min-width: 21rem !important;
            max-width: 21rem !important;
            width: 21rem !important;
        }
        
        /* Empêcher le collapse au clic */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(0) !important;
            visibility: visible !important;
            display: block !important;
        }
        
        /* Ajuster le contenu principal */
        .main {
            margin-left: 21rem !important;
        }
        
        .main .block-container {
            max-width: 1200px;
            padding-left: 2rem;
            padding-right: 2rem;
            margin: 0 auto;
        }
        
        /* ============================================
           CSS PALETTE
           ============================================ */
        :root {
            --primary-purple: #6B218D;
            --secondary-gray: #666666;
            --accent-purple: #805BED;
            --accent-teal: #51A0A2;
            --accent-gold: #987001;
            --accent-pink: #D46EA7;
            --gradient-1: #581D74;
            --gradient-2: #76279B;
            --gradient-3: #9531C4;
            --gradient-4: #AB54D4;
            --gradient-5: #BF7CDE;
            --gradient-6: #D3A5E9;
        }
        
        /* ============================================
           RESET STREAMLIT DEFAULTS
           ============================================ */
        .stApp {
            background: linear-gradient(135deg, #f8f9fe 0%, #fefeff 100%);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* ============================================
           HEADER PRINCIPAL
           ============================================ */
        .main-header {
            background: linear-gradient(135deg, var(--gradient-1) 0%, var(--gradient-3) 100%);
            padding: 1.5rem 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(107, 33, 141, 0.15);
            position: relative;
            overflow: hidden;
        }
        
        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0%, 100% { transform: translateX(-100%); }
            50% { transform: translateX(100%); }
        }
        
        .main-header h1 {
            color: white;
            font-size: 1.8rem;
            font-weight: 600;
            margin: 0;
            position: relative;
            z-index: 1;
        }
        
        .team-badge {
            background: rgba(255,255,255,0.25);
            backdrop-filter: blur(10px);
            padding: 0.4rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            border: 1px solid rgba(255,255,255,0.3);
            display: inline-block;
            margin-left: 1rem;
        }
        
        /* ============================================
           MESSAGES CHAT - STYLE COPILOT
           ============================================ */
        .user-message {
            background: linear-gradient(135deg, var(--gradient-2) 0%, var(--gradient-3) 100%);
            color: white;
            border-radius: 18px 18px 4px 18px;
            padding: 1rem 1.25rem;
            margin: 1rem 0 1rem 45px;
            max-width: 80%;
            margin-left: auto;
            box-shadow: 0 4px 12px rgba(107, 33, 141, 0.2);
            animation: slideInRight 0.3s ease-out;
            position: relative;
            line-height: 1.6;
        }
        
        .user-message::before {
            content: '👤';
            position: absolute;
            right: -40px;
            top: 0;
            width: 32px;
            height: 32px;
            background: var(--gradient-3);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(107, 33, 141, 0.3);
        }
        
        .bot-message {
            background: white;
            color: #2c3e50;
            border-radius: 18px 18px 18px 4px;
            padding: 1rem 1.25rem;
            margin: 1rem 45px 1rem 0;
            max-width: 85%;
            margin-right: auto;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid rgba(107, 33, 141, 0.1);
            animation: slideInLeft 0.3s ease-out;
            position: relative;
            line-height: 1.6;
        }
        
        .bot-message::before {
            content: '🤖';
            position: absolute;
            left: -40px;
            top: 0;
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--accent-teal), var(--accent-purple));
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            box-shadow: 0 2px 8px rgba(81, 160, 162, 0.3);
        }
        
        @keyframes slideInRight {
            from {
                opacity: 0;
                transform: translateX(30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        @keyframes slideInLeft {
            from {
                opacity: 0;
                transform: translateX(-30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        /* ============================================
           POWER BI REPORT CARDS
           ============================================ */
        .reports-section {
            background: linear-gradient(135deg, rgba(107, 33, 141, 0.03) 0%, rgba(149, 49, 196, 0.03) 100%);
            border-radius: 16px;
            padding: 1.5rem;
            margin: 1rem 0 1.5rem 0;
            border: 1px solid rgba(107, 33, 141, 0.15);
            backdrop-filter: blur(10px);
        }
        
        .reports-header {
            color: #6B218D;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid rgba(107, 33, 141, 0.1);
        }
        
        .reports-count {
            background: linear-gradient(135deg, #9531C4 0%, #AB54D4 100%);
            color: white;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.25rem 0.65rem;
            border-radius: 12px;
            margin-left: auto;
            min-width: 24px;
            text-align: center;
        }
        
        .report-card {
            display: block;
            background: white;
            border-radius: 12px;
            margin: 0.75rem 0;
            border: 1.5px solid rgba(107, 33, 141, 0.12);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow: hidden;
            position: relative;
            text-decoration: none;
        }
        
        .report-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, #6B218D 0%, #9531C4 100%);
            transform: scaleY(0);
            transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            transform-origin: bottom;
        }
        
        .report-card:hover {
            transform: translateX(4px);
            border-color: #6B218D;
            box-shadow: 0 8px 24px rgba(107, 33, 141, 0.15);
        }
        
        .report-card:hover::before {
            transform: scaleY(1);
            transform-origin: top;
        }
        
        .report-card:active {
            transform: translateX(2px) scale(0.99);
        }
        
        .report-card-inner {
            display: flex;
            align-items: center;
            padding: 1.25rem;
            gap: 1rem;
        }
        
        .report-icon {
            flex-shrink: 0;
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, rgba(107, 33, 141, 0.1) 0%, rgba(149, 49, 196, 0.1) 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6B218D;
            transition: all 0.3s;
        }
        
        .report-card:hover .report-icon {
            background: linear-gradient(135deg, #6B218D 0%, #9531C4 100%);
            color: white;
            transform: scale(1.05) rotate(-5deg);
        }
        
        .report-info {
            flex: 1;
            min-width: 0;
        }
        
        .report-title {
            color: #2c3e50;
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 0.4rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            transition: color 0.3s;
        }
        
        .report-card:hover .report-title {
            color: #6B218D;
        }
        
        .report-meta {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.85rem;
            color: #666666;
        }
        
        .report-type {
            background: rgba(81, 160, 162, 0.1);
            color: #51A0A2;
            padding: 0.25rem 0.65rem;
            border-radius: 6px;
            font-weight: 500;
            font-size: 0.75rem;
        }
        
        .report-action {
            color: #6B218D;
            font-weight: 500;
            display: flex;
            align-items: center;
            opacity: 0;
            transform: translateX(-8px);
            transition: all 0.3s;
        }
        
        .report-card:hover .report-action {
            opacity: 1;
            transform: translateX(0);
        }
        
        .response-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent 0%, rgba(107, 33, 141, 0.2) 50%, transparent 100%);
            margin: 1.5rem 0 1rem 0;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .report-card {
            animation: fadeInUp 0.4s ease-out backwards;
        }
        
        .report-card:nth-child(2) { animation-delay: 0.05s; }
        .report-card:nth-child(3) { animation-delay: 0.1s; }
        .report-card:nth-child(4) { animation-delay: 0.15s; }
        .report-card:nth-child(5) { animation-delay: 0.2s; }
        
        /* ============================================
           INPUT FORM
           ============================================ */
        .stTextInput > div > div {
            background: white;
            border: 2px solid rgba(107, 33, 141, 0.2);
            border-radius: 24px;
            padding: 0.75rem 1.5rem;
            transition: all 0.3s;
        }
        
        .stTextInput > div > div:focus-within {
            border-color: var(--primary-purple);
            box-shadow: 0 0 0 3px rgba(107, 33, 141, 0.1);
        }
        
        .stTextInput input {
            font-size: 1rem;
        }
        
        /* ============================================
           SUBMIT BUTTON
           ============================================ */
        .stButton > button {
            background: linear-gradient(135deg, var(--gradient-2) 0%, var(--gradient-3) 100%);
            color: white;
            border: none;
            border-radius: 24px;
            padding: 0.75rem 2rem;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s;
            box-shadow: 0 4px 12px rgba(107, 33, 141, 0.3);
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(107, 33, 141, 0.4);
        }
        
        /* ============================================
           SIDEBAR STYLING - LARGEUR FIXE
           ============================================ */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #fefeff 0%, #f8f9fe 100%);
            border-right: 1px solid rgba(107, 33, 141, 0.1);
            min-width: 21rem !important;
            max-width: 21rem !important;
        }
        
        [data-testid="stSidebar"] > div:first-child {
            padding: 2rem 1.25rem;
            min-width: 21rem !important;
            max-width: 21rem !important;
        }
        
        /* Tous les éléments de la sidebar ont une largeur max */
        [data-testid="stSidebar"] * {
            max-width: 100%;
            box-sizing: border-box;
        }
        
        .sidebar-logo-container {
            text-align: center;
            padding: 0 0 1.5rem 0;
            border-bottom: 2px solid rgba(107, 33, 141, 0.1);
            margin-bottom: 1.5rem;
        }
        
        .sidebar-logo-container img {
            max-width: 90%;
            height: auto;
        }
        
        .sidebar-section-header {
            color: #6B218D;
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 1.5rem 0 0.75rem 0;
            padding-left: 0.5rem;
            border-left: 3px solid #9531C4;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .sidebar-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent 0%, rgba(107, 33, 141, 0.2) 50%, transparent 100%);
            margin: 1.5rem 0;
        }
        
        /* Boutons sidebar - largeur contrôlée */
        [data-testid="stSidebar"] .stButton {
            width: 100%;
        }
        
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 10px;
            border: 2px solid rgba(107, 33, 141, 0.2);
            background: white;
            color: #6B218D;
            padding: 0.75rem 1rem;
            font-weight: 600;
            font-size: 0.9rem;
            transition: all 0.3s;
            width: 100%;
            margin: 0.5rem 0;
            white-space: normal;
            word-wrap: break-word;
            line-height: 1.3;
            min-height: 2.5rem;
        }
        
        [data-testid="stSidebar"] .stButton > button:hover {
            background: linear-gradient(135deg, #6B218D 0%, #9531C4 100%);
            border-color: #6B218D;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(107, 33, 141, 0.3);
        }
        
        /* Metrics dans la sidebar - largeur contrôlée */
        [data-testid="stSidebar"] [data-testid="stMetric"] {
            background: white;
            padding: 0.75rem;
            border-radius: 10px;
            border: 2px solid rgba(107, 33, 141, 0.1);
            margin: 0.5rem 0;
            width: 100%;
        }
        
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            color: #666666;
            font-size: 0.8rem;
            font-weight: 500;
        }
        
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            color: #6B218D;
            font-size: 1.3rem;
            font-weight: 700;
        }
        
        /* Selectbox sidebar - largeur contrôlée */
        [data-testid="stSidebar"] .stSelectbox {
            width: 100%;
        }
        
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background: white;
            border: 2px solid rgba(107, 33, 141, 0.15);
            border-radius: 10px;
            transition: all 0.3s;
            width: 100%;
        }
        
        [data-testid="stSidebar"] .stSelectbox > div > div:hover {
            border-color: #6B218D;
        }
        
        /* Radio buttons sidebar - largeur contrôlée */
        [data-testid="stSidebar"] .stRadio {
            width: 100%;
        }
        
        [data-testid="stSidebar"] .stRadio > div {
            width: 100%;
        }
        
        /* ============================================
           EXPANDER
           ============================================ */
        .streamlit-expanderHeader {
            background: white;
            border-radius: 12px;
            border: 1px solid rgba(107, 33, 141, 0.15);
            font-weight: 500;
            color: var(--primary-purple);
        }
        
        /* ============================================
           LOADING SPINNER
           ============================================ */
        .stSpinner > div {
            border-top-color: var(--primary-purple) !important;
        }
        
        /* ============================================
           SUCCESS/ERROR MESSAGES
           ============================================ */
        .stSuccess {
            background: rgba(81, 160, 162, 0.1);
            border-left: 4px solid var(--accent-teal);
            border-radius: 8px;
        }
        
        .stError {
            background: rgba(212, 110, 167, 0.1);
            border-left: 4px solid var(--accent-pink);
            border-radius: 8px;
        }
                
        /* ============================================
        EXPANDER STYLING - IMPROVED
        ============================================ */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, rgba(107, 33, 141, 0.05) 0%, rgba(149, 49, 196, 0.05) 100%);
            border-radius: 12px;
            border: 1.5px solid rgba(107, 33, 141, 0.15);
            font-weight: 600;
            color: #6B218D;
            padding: 1rem 1.25rem;
            transition: all 0.3s;
        }

        .streamlit-expanderHeader:hover {
            background: linear-gradient(135deg, rgba(107, 33, 141, 0.08) 0%, rgba(149, 49, 196, 0.08) 100%);
            border-color: #6B218D;
            box-shadow: 0 4px 12px rgba(107, 33, 141, 0.1);
        }

        .streamlit-expanderHeader svg {
            color: #6B218D;
        }

        /* Style pour le contenu du expander */
        [data-testid="stExpander"] > div:last-child {
            background: #fefeff;
            border: none;
            border-radius: 0 0 12px 12px;
            padding: 0;
        }
        
        /* ============================================
           RESPONSIVE
           ============================================ */
        @media (max-width: 768px) {
            .user-message, .bot-message {
                max-width: 90%;
                margin-left: 0;
                margin-right: 0;
            }
            
            .user-message::before, .bot-message::before {
                display: none;
            }
            
            .report-card-inner {
                padding: 1rem;
            }
            
            .report-icon {
                width: 40px;
                height: 40px;
            }
            
            .report-title {
                font-size: 0.9rem;
            }
            
            .report-action {
                display: none;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # ============================================
    # SIDEBAR ULTRA-PROFESSIONNELLE
    # ============================================
    
    # Logo avec container stylisé
    st.sidebar.markdown('<div class="sidebar-logo-container">', unsafe_allow_html=True)
    if os.path.exists(Streamlit.LOGO_URL):
        st.sidebar.image(Streamlit.LOGO_URL, width=220)
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    # Section : Search Mode
    st.sidebar.markdown('<p class="sidebar-section-header">Search Configuration</p>', unsafe_allow_html=True)
    st.sidebar.markdown('<div style="padding: 0 0.5rem;">', unsafe_allow_html=True)
    search_mode = st.sidebar.radio(
        Streamlit.PARAM,
        options=Streamlit.MODES,
        label_visibility="collapsed"
    )
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # Section : AI Model
    st.sidebar.markdown('<p class="sidebar-section-header">AI Model Selection</p>', unsafe_allow_html=True)
    st.sidebar.markdown('<div style="padding: 0 0.5rem;">', unsafe_allow_html=True)
    model_choice = st.sidebar.selectbox(
        Streamlit.IAS,
        options=Streamlit.IA_MODELS,
        label_visibility="collapsed"
    )
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # Section : Statistics
    st.sidebar.markdown('<p class="sidebar-section-header">Statistics</p>', unsafe_allow_html=True)
    if st.sidebar.button("Display Power BI Stats", use_container_width=True):
        ws_count, rs_count, ps_count = power_bi_stats(filtered_metadata)
        
        st.sidebar.metric("Workspaces", ws_count)
        st.sidebar.metric("Reports", rs_count)
        st.sidebar.metric("Pages", ps_count)

    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    # Section : Actions
    st.sidebar.markdown('<p class="sidebar-section-header">Actions</p>', unsafe_allow_html=True)
    if st.sidebar.button("Clear History", use_container_width=True):
        st.session_state['messages'] = []
        st.rerun()

    # ============================================
    # HEADER
    # ============================================
    st.markdown(f"""
        <div class="main-header">
            <h1>Power BI Navigation Assistant <span class="team-badge">{TEAMS[st.session_state["team"]]} {st.session_state["team"]}</span></h1>
        </div>
    """, unsafe_allow_html=True)

    # ============================================
    # GLOSSARY
    # ============================================
    with st.expander("📚 Display Glossary", expanded=False):
        context = build_enhanced_context()
    intro += context

    # ============================================
    # CHAT INPUT
    # ============================================
    with st.form(key='chat_form', clear_on_submit=True):
        user_input = st.text_input("Your message:", key='input', placeholder="Where is the report on consolidated debts...")
        submit_button = st.form_submit_button(label='Send')

    if submit_button and user_input:
        with st.spinner("Analyzing..."):
            if search_mode == Streamlit.MODES[0]:
                if metadata_embeddings is None or metadata_entries is None:
                    response = (
                        "Smart-search mode requires the embeddings index. "
                        "Run `python embeddings_metadata.py` first, then retry."
                    )
                else:
                    response = ask_iagen_rag(query=user_input, model=model_choice, k=50, intro=intro, instructions=instructions, metadata_embeddings=metadata_embeddings, metadata_entries=metadata_entries)
            else:
                response = ask_iagen_finance(user_input, model_choice)
        
        print(response)
        matched_links = []     
        for title, url in report_link_map.items():
            if re.search(re.escape(title), response, re.IGNORECASE):
                matched_links.append((title, url))

        # Stocker les messages dans l'historique
        st.session_state['messages'].append({"role": "user", "content": user_input})
        st.session_state['messages'].append({"role": "assistant", "content": response})
        
        # Recharger la page pour afficher les messages dans l'ordre correct
        st.rerun()

    # ============================================
    # AFFICHAGE DES MESSAGES
    # ============================================
    if st.session_state['messages']:
        # Regrouper les messages par paires (question/réponse)
        message_pairs = []
        for i in range(0, len(st.session_state['messages']), 2):
            if i+1 < len(st.session_state['messages']):
                # Créer une paire [message utilisateur, message assistant]
                message_pairs.append([st.session_state['messages'][i], st.session_state['messages'][i+1]])
            else:
                # S'il reste un message sans paire, l'ajouter seul
                message_pairs.append([st.session_state['messages'][i]])
        
        # Afficher les paires de messages du plus récent au plus ancien
        for pair in reversed(message_pairs):
            # Afficher d'abord le message utilisateur
            user_message = pair[0]
            st.markdown(f"<div class='user-message'>{user_message['content']}</div>", unsafe_allow_html=True)
            
            # S'il y a une réponse dans la paire
            if len(pair) > 1:
                assistant_message = pair[1]
                
                # Vérifier si la réponse contient des liens vers des rapports
                message_links = []
                for title, url in report_link_map.items():
                    if re.search(re.escape(title), assistant_message['content'], re.IGNORECASE):
                        message_links.append((title, url))
                
                # Si des liens sont trouvés, afficher la section des rapports
                if message_links:
                    for title, url in message_links:
                        st.markdown(f"""
                            <a href='{url}' target='_blank' class='report-card' style='text-decoration: none;'>
                                <div class='report-card-inner'>
                                    <div class='report-icon'>
                                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                                            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
                                            <path d="M7 7h10M7 11h10M7 15h6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                                        </svg>
                                    </div>
                                    <div class='report-info'>
                                        <div class='report-title'>{title}</div>
                                        <div class='report-meta'>
                                            <span class='report-type'>Power BI Report</span>
                                            <span class='report-action'>
                                                Open report
                                                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" style="margin-left: 4px; vertical-align: middle;">
                                                    <path d="M10.5 3.5L3.5 10.5M10.5 3.5H5.5M10.5 3.5V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                                                </svg>
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </a>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)  # Fermer la section
                
                # Afficher la réponse textuelle
                st.markdown(f"<div class='bot-message'>{assistant_message['content']}</div>", unsafe_allow_html=True)

        
# Fonction de déconnexion dans la sidebar
def logout_button():
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.markdown('<p class="sidebar-section-header">Account</p>', unsafe_allow_html=True)
    if st.sidebar.button("Log out", use_container_width=True):
        st.session_state['team'] = None
        st.session_state['generated'] = []
        st.session_state['past'] = []
        st.session_state['messages'] = []
        st.session_state.connected = False
        st.rerun()

# Affichage de la page appropriée
def main():
    if not st.session_state.connected:
        login_page()
    else:
        chat_page()
        logout_button()

if __name__ == "__main__":
    main()