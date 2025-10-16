import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import json
import pickle
from sklearn.metrics.pairwise import cosine_similarity

from utils.llm_connector import LLMConnector
llm = LLMConnector()

from utils.prompt_pbi import generate_prompt, generate_prompt_rag
from utils.prompt_finance import prompt_finance
from utils.prompt_free import generate_prompt_free
from front.src.prompts import prompts

from utils.embeddings_connector import EMBEDDINGConnector
embedding_connector = EMBEDDINGConnector()


# Filtrer les métadonnées en fonction de l'équipe choisie
def filter_metadata_by_team(metadata, mapping, team):
    """
    Description de ta fonction: Filtre les métadonnées en fonction de l'équipe spécifiée
    metadata : Liste de métadonnées à filtrer
    mapping : Dictionnaire mappant les équipes aux espaces de travail
    team : Nom de l'équipe à filtrer
    Return: Liste de métadonnées filtrées associées à l'équipe spécifiée
    """
    workspaces = mapping.get(team, [])
    return [item for item in metadata if item["workspace"] in workspaces]

def filter_embeddings_by_team_in_memory(
    embeddings_path,
    metadata_path,
    mapping,
    target_team
):
    """
    Description de ta fonction: Filtre les embeddings et les entrées de métadonnées basés sur l'équipe cible
    embeddings_path : Chemin d'accès au fichier contenant les embeddings
    metadata_path : Chemin d'accès au fichier contenant les entrées de métadonnées
    mapping : Dictionnaire mappant les équipes aux espaces de travail
    target_team : Nom de l'équipe cible pour filtrage
    Return: Un tuple contenant les embeddings filtrés et les entrées de métadonnées filtrées
    """
    # Chargement
    metadata_embeddings = np.load(embeddings_path)
    with open(metadata_path, "rb") as f:
        metadata_entries = pickle.load(f)
    team_mapping = mapping

    target_workspaces = set(ws.strip() for ws in team_mapping.get(target_team, []))
    print(f"Workspaces de la team : {list(target_workspaces)}")

    # Construction du filtre
    filtered_embeddings = []
    filtered_entries = []

    for i, entry in enumerate(metadata_entries):
        workspace = entry.get("workspace", "").strip()
        if workspace in target_workspaces:
            embedding = metadata_embeddings[i]

            if isinstance(embedding, list):
                embedding = np.array(embedding)
            if embedding.ndim == 1:
                filtered_embeddings.append(embedding)
                filtered_entries.append(entry)
            else:
                print(f"Embedding ignoré (shape incorrecte : {embedding.shape}) pour {workspace}")
    
    if not filtered_embeddings:
        raise ValueError(f"Aucun embedding validé pour la team '{target_team}'")

    filtered_embeddings = np.vstack(filtered_embeddings)

    print(f"✅ {len(filtered_entries)} entrées filtrées pour la team '{target_team}'.")

    return filtered_embeddings, filtered_entries

# Fonction pour faire le mapping entre nom de rapport et lien url du rapport
def build_report_link_map(enriched_data):
    """
    Description de ta fonction: Crée un mappage entre les noms de rapports et leurs URL
    enriched_data : Liste des données enrichies contenant des informations de rapport
    Return: Dictionnaire mappant les noms de rapports à leurs URLs respectives
    """
    return {
        entry["report"]: entry["report_url"]
        for entry in enriched_data
        if entry.get("report_url")
    }

def load_metadata(path="data/metadata.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    
metadata = load_metadata()

def build_metadata_embeddings_from_pages(data):
    """
    Description de ta fonction: Construit des embeddings à partir des pages de rapports et sauvegarde les résultats
    data : Données contenant les rapports et leurs pages
    Return: None
    """
    all_embeddings = []
    all_metadata_entries = []

    for report_entry in data:
        workspace = report_entry.get("workspace", "")
        report = report_entry.get("report", "")
        report_url = report_entry.get("report_url", "")
        pages = report_entry.get("pages", [])

        for page in pages:
            page_name = page.get("name", "")
            text_repr = f"{workspace} - {report} - {page_name}"

            embedding = embedding_connector.generate_embeddings(
                text=text_repr,
            )

            all_embeddings.append(embedding)
            all_metadata_entries.append({
                "workspace": workspace,
                "report": report,
                "page": page_name,
                "report_url": report_url,
                "text_repr": text_repr
            })

    # Sauvegarde
    np.save("data/metadata_embeddings.npy", np.array(all_embeddings))
    with open("data/metadata_entries.pkl", "wb") as f:
        pickle.dump(all_metadata_entries, f)

    print(f"✅ {len(all_embeddings)} pages traitées et embeddings sauvegardés.")


embeddings_path="data/metadata_embeddings.npy"
metadata_path="data/metadata_entries.pkl"

# Chargement
metadata_embeddings = np.load(embeddings_path)
with open(metadata_path, "rb") as f:
    metadata_entries = pickle.load(f)


def get_top_k_pages(query, k, metadata_embeddings=metadata_embeddings, metadata_entries=metadata_entries):
    """
    Description de ta fonction: Récupère les k meilleures pages correspondant à une requête
    query : Requête utilisateur pour laquelle trouver les pages les plus pertinentes
    k : Nombre de pages à retourner
    metadata_embeddings : Embeddings des métadonnées pour calculer la similarité
    metadata_entries : Entrées de métadonnées correspondantes
    Return: Liste des k meilleures pages enrichies
    """
    # Embedding de la query
    query_embedding = embedding_connector.generate_embeddings(
        text=query
    )
    query_embedding = np.array(query_embedding).reshape(1, -1)

    # Similarité
    similarities = cosine_similarity(query_embedding, metadata_embeddings)[0]
    top_k_indices = np.argsort(similarities)[-k:][::-1]

    # Résultats enrichis
    top_k_results = []
    for i in top_k_indices:
        entry = metadata_entries[i].copy()
        entry["similarity"] = float(similarities[i])
        top_k_results.append(entry)

    return top_k_results

# Smart search with AI API and Embedding API calls
def ask_iagen_rag(query, model='gpt-4o-2024-08-06', k=50,  intro = prompts["BOAT"]["intro"] , instructions = prompts["BOAT"]["instructions"], metadata_embeddings=metadata_embeddings, metadata_entries=metadata_entries):
    """
    Description de ta fonction: Effectue une recherche intelligente en utilisant une API AI et des appels d'embedding
    query : Requête utilisateur à traiter
    model : Modèle AI à utiliser pour la génération de réponse
    k : Nombre de résultats à récupérer
    intro : Introduction pour le prompt
    instructions : Instructions pour le prompt
    metadata_embeddings : Embeddings des métadonnées pour la recherche
    metadata_entries : Entrées de métadonnées correspondantes
    Return: Réponse générée par le modèle AI
    """
        # Charger index, entries, modèle

    entries = get_top_k_pages(query=query, k=50, metadata_embeddings=metadata_embeddings, metadata_entries=metadata_entries)

    top_matches = []
    for entry in entries:
        workspace = entry["workspace"]
        report = entry["report"]
        page = entry["page"]
        top_matches.append(
            {"workspace": workspace,
                "report": report,
                "page":page
                })

    prompt = generate_prompt_rag(top_matches, intro, instructions)
    enhanced_query = "Here is the user query :"
    enhanced_query += query

    response = llm.get_llm_response(
        context_prompt=prompt,
        user_prompt=enhanced_query,
        outputMaxTokens=1000,
        modelID=model,
    )

    print(response)
    return response

# General question about finance
def ask_iagen(query, model='gpt-4o-2024-08-06', intro = prompts["natixis_bpce_assistant"]["intro"] , instructions = prompts["natixis_bpce_assistant"]["instructions"]):
    """
    Description de ta fonction: Traite une question générale sur les finances
    query : Requête utilisateur à traiter
    model : Modèle AI à utiliser pour la génération de réponse
    intro : Introduction pour le prompt
    instructions : Instructions pour le prompt
    Return: Réponse générée par le modèle AI
    """
    prompt = generate_prompt_free(query, intro, instructions)

    response = llm.get_llm_response(
        context_prompt=prompt,
        user_prompt=query,
        outputMaxTokens=1000,
        modelID=model,
    )
    print(response)
    return response

# Smart search with AI API call only
def ask_iagen_naive(query, model='gpt-4o-2024-08-06', intro = prompts["BOAT"]["intro"] , instructions = prompts["BOAT"]["instructions"], data = metadata):
        
    """Description de ta fonction: Effectue une recherche simple en utilisant uniquement les appels API AI
    query : Requête utilisateur à traiter
    model : Modèle AI à utiliser pour la génération de réponse
    intro : Introduction pour le prompt
    instructions : Instructions pour le prompt
    data : Données à utiliser pour la recherche
    Return: Réponse générée par le modèle AI """

    top_matches = []
    for entry in data:
        workspace = entry["workspace"]
        report = entry["report"]
        for page in entry["pages"]:
            top_matches.append(
                {"workspace": workspace,
                 "report": report,
                 "page":page["name"]
                 })
            

    prompt = generate_prompt(top_matches, intro, instructions)
    enhanced_query = "Here is the user query :"
    enhanced_query += query

    response = llm.get_llm_response(
        context_prompt=prompt,
        user_prompt=enhanced_query,
        outputMaxTokens=1000,
        modelID=model,
    )

    print(response)
    return response


# Potential future function to analyze financial data (dans le cas où on aurait les données Power BI)
def ask_iagen_finance(query, model='gpt-4o-2024-08-06', intro = prompts["BOAT"]["intro"] , instructions = prompts["BOAT"]["instructions"]):
    metadata = load_metadata()

    top_matches = []
    for entry in metadata:
        workspace = entry["workspace"]
        report = entry["report"]
        for page in entry["page"]:
            top_matches.append(
                {"workspace": workspace,
                 "report": report,
                 "page":page
                 })
            

    prompt = prompt_finance(query, top_matches, intro, instructions)

    response = llm.get_llm_response(
        user_prompt=prompt,
        outputMaxTokens=1000,
        modelID=model,
    )

    print(response) 

    return response



if __name__  ==  '__main__':
    res = get_top_k_pages(query = "Where is gap ?", k = 30)
    #response = ask_iagen_rag(query = "Where is the gap ?")
    print(res)




