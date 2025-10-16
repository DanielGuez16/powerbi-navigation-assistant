import streamlit as st
import os
import sys
from logging import Logger
import re
import json
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO
import base64
import time
import pickle
import numpy as np
import pandas as pd
from io import BytesIO

load_dotenv()

if "env" not in st.session_state:
    st.session_state.env = os.getenv("ENV", "dev")

# Pour accéder au module local
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Imports internes
from app.pbi_query import ask_iagen_finance, load_metadata, filter_metadata_by_team, load_metadata, ask_iagen_rag, filter_embeddings_by_team_in_memory, build_report_link_map
from src.constants import Streamlit
from utils.sharepoint_connector import SharePointClient
from utils.feedback_logger import enregistrer_feedback
from src.prompts import prompts
from src.glossary_path import glossary

client = SharePointClient()

# Configuration de la page
st.set_page_config(
    page_title="Power BI Navigation Assistant",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="expanded"  # Sidebar étendue par défaut
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

# Liste des équipes disponibles
TEAMS = {
    "BOAT": "",
    "Data Management": "",
    "FDS": "",
    "Autre": ""
}

# Fonction pour convertir une image en base64
def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def load_metadata(path="data/metadata.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    logo_path = os.path.join("front", "src", "bpce_logo.png")
    logo = Image.open(logo_path)
    logo_base64 = image_to_base64(logo)

    st.markdown(
        f"""
        <style>
            .login-content {{
                max-width: 400px;
                margin: 0 auto;
                padding: 1rem;
            }}
            .logo-container {{
                text-align: center;
                margin-bottom: 2rem;
            }}
            .team-button {{
                width: 100%;
                margin: 0.5rem 0;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px;
                text-align: center;
                transition: all 0.2s;
            }}
            .team-button:hover {{
                border-color: #714A80;
                background-color: #f8f9fa;
            }}
            .title {{
                color: #2c3e50;
                text-align: center;
                margin-bottom: 1.5rem;
            }}
            .subtitle {{
                color: #555;
                text-align: center;
                margin-bottom: 2rem;
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-content">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="logo-container">'
        f'<img src="data:image/png;base64,{logo_base64}" style="height:60px;"/>'
        f'</div>',
        unsafe_allow_html=True
    )

    st.markdown('<h2 class="title">Power BI Navigation Assistant</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Select your team</p>', unsafe_allow_html=True)

    for team, emoji in TEAMS.items():
        if st.button(
            f"{emoji} {team}",
            key=f"team_{team}",
            use_container_width=True
        ):
            st.session_state['team'] = team
            st.session_state['connected'] = True
            st.session_state['messages'] = []
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

def build_enhanced_context():
    team = st.session_state['team']
    base_context = "Here are knowledge that can help the research:\n"
    file_path = glossary.get(team, [])
    
    try:
        # Lire le fichier binaire
        binary_content = client.read_binary_file(file_path)

        # Lire le contenu du fichier Excel
        excel_data = client.read_excel_file_as_dict(binary_content)

        # Convertir en DataFrame pour l'affichage et l'édition
        df = pd.DataFrame(excel_data)

        # Afficher le DataFrame dans Streamlit
        st.subheader(Streamlit.EXCEL)
        edited_df = st.data_editor(df, key="data_editor")  # Permet de modifier les données directement

        # Lorsque l'utilisateur est satisfait de ses modifications, il peut cliquer sur le bouton pour sauvegarder
        if st.button("Update modifications"):
            
            # Mettre à jour le fichier Excel avec les nouvelles données
            link = client.save_dataframe_in_sharepoint(df = edited_df, path = file_path, get_link=True)
            
            st.success(f"Excel updated ! Accessible at : {link}")

        # Construire le contexte à partir des données
        for row in edited_df.to_dict(orient='records'):
            base_context += str(row) + "\n"  # Ajoute chaque ligne de données au contexte
            
    except Exception as e:
        st.error(f"An error occurred: {e}")

    return base_context

def build_enhanced_context2():
    """Construit le contexte pour l'IA avec les ressources personnalisées et permet la modification des données Excel."""
    base_context = "Here are knowledge that can help the research:\n"
    file_path = "PowerBI x AI/BOAT/glossaire_boat.xlsx"

    try:
        # Lire le fichier binaire
        binary_content = client.read_binary_file(file_path)

        # Lire le contenu du fichier Excel
        excel_data = client.read_excel_file_as_dict(binary_content)

        # Convertir en DataFrame pour l'affichage et l'édition
        df = pd.DataFrame(excel_data)

        # Afficher le DataFrame dans Streamlit
        st.write("### Données de l'Excel")
        edited_df = st.data_editor(df, key="data_editor")  # Permet de modifier les données directement

        # Lorsque l'utilisateur est satisfait de ses modifications, il peut cliquer sur le bouton pour sauvegarder
        if st.button("Sauvegarder les modifications"):
            # Convertir le DataFrame mis à jour en liste de dictionnaires
            updated_data = edited_df.to_dict(orient='records')
            updated_excel_content = client.update_excel_file(binary_content, updated_data)
            
            # Sauvegarder le fichier Excel mis à jour sur SharePoint
            link = client.save_binary_in_sharepoint(updated_excel_content, file_path, get_link=True)
            st.success(f"Fichier Excel mis à jour ! Accessible à : {link}")

        # Construire le contexte à partir des données
        for row in edited_df.to_dict(orient='records'):
            base_context += str(row) + "\n"  # Ajoute chaque ligne de données au contexte
            
    except Exception as e:
        st.error(f"An error occurred: {e}")

    return base_context

def build_enhanced_context1():
    """Construit le contexte pour l'IA avec les ressources personnalisées"""
    base_context = f"""
 \n Here are knowledge that can helps the research :
    """
    file_path = "PowerBI x AI/BOAT/glossaire_boat.xlsx"  

    try:
        # Lire le fichier binaire
        binary_content = client.read_binary_file(file_path)

        # Lire le contenu du fichier Excel
        excel_data = client.read_excel_file_as_dict(binary_content)

        # Afficher les données lues
        for row in excel_data:
            base_context.append(row)
    except Exception as e:
        print(f"An error occurred: {e}")
    return base_context


# Page du chatbot
def chat_page():
    team = st.session_state['team']
    metadata = load_metadata("data/metadata.json")
    mapping = load_metadata("data/team_workspace_mapping.json")

    filtered_metadata = filter_metadata_by_team(metadata=metadata, mapping=mapping, team=team)

    embeddings_path="data/metadata_embeddings.npy"
    metadata_path="data/metadata_entries.pkl"

    metadata_embeddings, metadata_entries = filter_embeddings_by_team_in_memory(embeddings_path=embeddings_path, metadata_path=metadata_path, mapping=mapping, target_team=team)

    report_link_map = build_report_link_map(filtered_metadata)

    intro = prompts[team]["intro"]
    instructions = prompts[team]["instructions"]

    st.sidebar.image(Streamlit.BPCE_LOGO_URL, width=300)
    st.sidebar.title(Streamlit.MODE_LABEL)
    

    search_mode = st.sidebar.radio(Streamlit.PARAM, options=Streamlit.MODES)

    st.sidebar.title(Streamlit.MODEL_LABEL)
    model_choice = st.sidebar.selectbox(Streamlit.IAS, options=Streamlit.IA_MODELS)

    if st.sidebar.button("Display Power BI stats"):
        ws_count, rs_count, ps_count = power_bi_stats(filtered_metadata)

        # Utiliser des colonnes pour afficher les statistiques
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.sidebar.metric("Total Workspaces", ws_count)
        
        with col2:
            st.sidebar.metric("Total Reports", rs_count)
        
        with col3:
            st.sidebar.metric("Total Pages", ps_count)

    if st.sidebar.button(Streamlit.CLEAR_HISTORY):
        st.session_state['messages'] = []

    st.markdown(
        f'<h2>Power BI Navigation Assistant : <span class="team-badge">{st.session_state["team"]} {TEAMS[st.session_state["team"]]}</span></h2>',
        unsafe_allow_html=True
    )

    with st.expander("Display Glossary"):
        context = build_enhanced_context()
    intro += context

    with st.form(key='chat_form', clear_on_submit=True):
        user_input = st.text_input("Your message:", key='input', placeholder="Where is the report on consolidated debts...")
        submit_button = st.form_submit_button(label='Send')

    if submit_button and user_input:

        with st.spinner("Analyzing..."):
            if search_mode == Streamlit.MODES[0]:
                response = ask_iagen_rag(query=user_input, model=model_choice, k=50,  intro=intro, instructions=instructions, metadata_embeddings=metadata_embeddings, metadata_entries=metadata_entries)
            else:
                response = ask_iagen_finance(user_input, model_choice)
        print(response)
        matched_links = []     
        for title, url in report_link_map.items():
            if re.search(re.escape(title), response, re.IGNORECASE):
                matched_links.append((title, url))

        if matched_links:
            complete_response = "Here are the links of the suggested reports:<br><br>"
            for title, url in matched_links:
                complete_response += f"<div style='margin: 5px 0;'><b>{title}</b> : <a href='{url}' target='_blank'>{title}</a></div>"
            complete_response += f"<br><br>{response}"

        st.session_state['messages'].append({"role": "assistant", "content": complete_response})
        st.session_state['messages'].append({"role": "user", "content": user_input})

        # Rerun to refresh the page
        st.rerun()

    # Styles CSS pour les messages
    st.markdown("""
        <style>
            .user-message {
                background-color: #714A80; /* Couleur Fond */
                border-radius: 8px;
                padding: 15px; /* Padding pour l'espace intérieur */
                margin: 5px 0;
                border: 1px solid #ffffff; /* Couleur Bordure */
                color: #ffffff; /* Couleur du texte */
                font-size: 16px; /* Taille de police */
                line-height: 1.5; /* Hauteur de ligne */
                max-width: 100%; /* Largeur maximale de la boîte */
                box-sizing: border-box; /* Inclut le padding et la bordure dans la largeur */
                word-wrap: break-word; /* Gère le retour à la ligne des longs mots */
            }
            .bot-message {
                background-color: #f3e9f7; /* Couleur Fond */
                border-radius: 8px;
                padding: 15px; /* Padding pour l'espace intérieur */
                margin: 5px 0;
                border: 1px solid #714A80; /* Couleur Bordure */
                color: #714A80; /* Couleur du texte */
                font-size: 16px; /* Taille de police */
                line-height: 1.5; /* Hauteur de ligne */
                max-width: 100%; /* Largeur maximale de la boîte */
                box-sizing: border-box; /* Inclut le padding et la bordure dans la largeur */
                word-wrap: break-word; /* Gère le retour à la ligne des longs mots */
            }
        </style>
    """, unsafe_allow_html=True)


    # Affichage des messages dans le conteneur de chat
    if st.session_state['messages']:
        for message in reversed(st.session_state['messages']):
            if message['role'] == 'user':
                st.write(f"<div class='user-message'>{message['content']}</div>", unsafe_allow_html=True)
            else:
                st.write(f"<div class='bot-message'>{message['content']}</div>", unsafe_allow_html=True)

    # st.markdown("---")
    
    # with st.expander(Streamlit.FEEDBACK):
    #     if st.session_state['messages']:
    #         last_user_msg = next((m["content"] for m in reversed(st.session_state['messages']) if m["role"] == "user"), "")
    #         last_assistant_msg = next((m["content"] for m in reversed(st.session_state['messages']) if m["role"] == "assistant"), "")

    #         selected_issues = st.multiselect(
    #             Streamlit.QUESTION,
    #             Streamlit.ISSUES
    #         )

    #         commentaire = st.text_area(Streamlit.COM)

    #         if st.button(Streamlit.SEND):
    #             enregistrer_feedback(last_user_msg, last_assistant_msg, selected_issues, commentaire)
    #             st.success(Streamlit.THANKS)

# Fonction de déconnexion dans la sidebar
def logout_button():
    with st.sidebar:
        if st.button("Log out"):
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
        logout_button()
        chat_page()

if __name__ == "__main__":
    main()
