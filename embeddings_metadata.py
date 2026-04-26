"""Bootstrap script: builds metadata_embeddings.npy + metadata_entries.pkl
from data/metadata.json by calling the embeddings API for each report page.

Run once after metadata.json is in place:
    python embeddings_metadata.py
"""
import json
import os
import pickle

import numpy as np

from embeddings_connector import EMBEDDINGConnector

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
METADATA_PATH = os.path.join(DATA_DIR, "metadata.json")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "metadata_embeddings.npy")
ENTRIES_PATH = os.path.join(DATA_DIR, "metadata_entries.pkl")


def main() -> None:
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    embedding_connector = EMBEDDINGConnector()

    entries: list[dict] = []
    textes: list[str] = []
    for item in metadata:
        workspace = item["workspace"]
        report = item["report"]
        report_url = item["report_url"]
        for page in item["pages"]:
            page_name = page["name"]
            entries.append(
                {
                    "workspace": workspace,
                    "report": report,
                    "report_url": report_url,
                    "page": page_name,
                }
            )
            textes.append(f"Report : '{report}', Page : '{page_name}'")

    embeddings = []
    for text in textes:
        embeddings.append(embedding_connector.generate_embeddings(text=text))
    embeddings_arr = np.array(embeddings)

    os.makedirs(DATA_DIR, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings_arr)
    with open(ENTRIES_PATH, "wb") as f:
        pickle.dump(entries, f)

    print(f"✅ {len(embeddings)} embeddings generated and saved to {DATA_DIR}.")


if __name__ == "__main__":
    main()
