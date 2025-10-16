import json
import numpy as np
import os
from embeddings_connector import EMBEDDINGConnector
import pickle

# Charger les métadonnées
with open("data/metadata.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)
                         
# Initialiser le connecteur d'embeddings
embedding_connector = EMBEDDINGConnector()

# Construire les textes à embedder
entries = []
textes = []
for item in metadata:
    workspace = item["workspace"]
    report = item["report"]
    report_url = item["report_url"]
    for page in item["pages"]:
        entry = {
            "workspace": workspace,
            "report": report,
            "report_url": report_url,
            "page": page["name"]
        }
        entries.append(entry)
        textes.append(f"Report : '{report}', Page : '{page}'")

# Embedder les textes en utilisant la méthode generate_embeddings
embeddings = []
for text in textes:
    embedding = embedding_connector.generate_embeddings(text=text)
    embeddings.append(embedding)

# Convertir les embeddings en tableau NumPy
embeddings = np.array(embeddings)

# Sauvegarder les embeddings et les métadonnées associées
np.save("data/metadata_embeddings.npy", embeddings)
with open("data/metadata_entries.pkl", "wb") as f:
    pickle.dump(entries, f)

print("Embeddings generated and saved successfully.")
