from datetime import datetime
import csv
import os
import time

def enregistrer_feedback(prompt, response, categories, commentaire, path="data/feedback.csv"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    issues = ";".join(categories) if categories else "Aucun"

    os.makedirs(os.path.dirname(path), exist_ok=True)

    for attempt in range(3):
        try:
            file_exists = os.path.isfile(path)

            with open(path, mode='a', encoding="utf-8", newline="") as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(["Horodatage", "Prompt utilisateur", "Réponse de l'IA", "Catégories", "Commentaire"])
                writer.writerow([
                    timestamp,
                    prompt,
                    response,
                    issues,
                    commentaire
                ])
            break # Succés

        except Exception as e:
            time.sleep(1)
            if attempt == 2:
                raise RuntimeError(f"Echec d'écriture dans le fichier feedback : {path}") from e
