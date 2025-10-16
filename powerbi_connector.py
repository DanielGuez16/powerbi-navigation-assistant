import os
import json
import requests
import pandas as pd
import urllib3
from dotenv import load_dotenv
from tqdm import tqdm
import re

class PowerBIClient:
    """Client pour interagir avec l'API REST de Power BI."""

    def __init__(self):
        """Initialise le client Power BI."""
        load_dotenv()
        self.tenant_id = os.environ.get("powerbi-tenant-id")
        self.client_id = os.environ.get("powerbi-client-id")
        self.client_secret = os.environ.get("powerbi-client-secret")
        self.base_url = "https://api.powerbi.com/v1.0/myorg"
        
        # Disable HTTPS warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Obtenir le token d'accès
        self.access_token = self.get_access_token()
        self.errors = []  # Attribut pour stocker les erreurs

    def get_access_token(self):
        """Récupère le token d'accès pour l'API Power BI."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default"
        }
        
        proxies = {
            "http": os.getenv("business-http-proxy"),
            "https": os.getenv("business-https-proxy")
        } if os.getenv("http-proxy") and os.getenv("https-proxy") else None
        
        try:
            response = requests.post(url, headers=headers, data=data, proxies=proxies)
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            print(f"Erreur lors de la récupération du token : {e}")
            raise

    def get_workspaces(self):
        """Récupère la liste des workspaces disponibles."""
        proxies = {
            "http": os.getenv("BUSINESS_HTTP_PROXY"),
            "https": os.getenv("BUSINESS_HTTPS_PROXY")
        } if os.getenv("HTTP_PROXY") and os.getenv("HTTPS_PROXY") else None

        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            groups_resp = requests.get(f"{self.base_url}/groups", headers=headers, proxies=proxies, verify=False)
            groups_resp.raise_for_status()
            return groups_resp.json()["value"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append("Erreur 400 lors de la récupération des workspaces")
            else:
                print(f"Erreur lors de la récupération des workspaces : {e}")
            return []

    def get_reports_from_workspace(self, group_id):
        """Récupère les rapports d'un workspace donné."""
        proxies = {
            "http": os.getenv("business-http-proxy"),
            "https": os.getenv("business-https-proxy")
        } if os.getenv("http-proxy") and os.getenv("https-proxy") else None
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            reports_resp = requests.get(f"{self.base_url}/groups/{group_id}/reports", headers=headers, proxies=proxies, verify=False)
            reports_resp.raise_for_status()
            return reports_resp.json()["value"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append(f"Erreur 400 lors de la récupération des rapports du workspace {group_id}")
            else:
                print(f"Erreur lors de la récupération des rapports du workspace {group_id} : {e}")
            return []

    def get_report_pages(self, group_id, report_id):
        """Récupère les pages d'un rapport spécifique."""
        proxies = {
            "http": os.getenv("business-http-proxy"),
            "https": os.getenv("business-https-proxy")
        } if os.getenv("http-proxy") and os.getenv("https-proxy") else None
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            pages_resp = requests.get(f"{self.base_url}/groups/{group_id}/reports/{report_id}/pages", headers=headers, proxies=proxies, verify=False)
            pages_resp.raise_for_status()
            return [{"name": p["displayName"]} for p in pages_resp.json().get("value", [])]  # Retourne les pages si tout va bien
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append(f"Erreur 400 lors de la récupération des pages du rapport {report_id} dans le workspace {group_id}")
            else:
                self.errors.append(f"Erreur lors de la récupération des pages du rapport {report_id} dans le workspace {group_id} : {e}")

            return []  # Retourne une liste vide si une erreur se produit

    def get_reports_with_pages(self):
        """Récupère les rapports avec leurs pages associées dans tous les workspaces."""
        enriched_data = []
        workspaces = self.get_workspaces()

        for group in tqdm(workspaces, desc="Traitement des workspaces", unit="workspace"):
            group_id = group.get('id')
            group_name = group.get('name')
            
            try:
                reports = self.get_reports_from_workspace(group_id)
            except Exception as e:
                self.errors.append(f"Erreur lors de la récupération des rapports pour le workspace {group_name} ({group_id}): {e}")
                continue  # Passe au prochain workspace

            for report in tqdm(reports, desc=f"Traitement des rapports dans {group_name}", unit="report", leave=False):
                report_id = report.get('id')
                report_name = report.get('name')
                report_url = report.get("webUrl", "")
                
                try:
                    pages = self.get_report_pages(group_id=group_id, report_id=report_id)
                    enriched_data.append({
                        "workspace": group_name,
                        "report": report_name,
                        "report_url": report_url,
                        "pages": pages
                    })
                except Exception as e:
                    self.errors.append(f"Erreur lors de la récupération des pages du rapport {report_name} ({report_id}) dans le workspace {group_name}: {e}")
                    continue  # Passe au prochain rapport

        return enriched_data

    def extract_report_workspace_names(self, error_list):
        """Extrait les noms des rapports et des workspaces à partir d'une liste d'erreurs."""
        proxies = {
            "http": os.getenv("business-http-proxy"),
            "https": os.getenv("business-https-proxy")
        } if os.getenv("http-proxy") and os.getenv("https-proxy") else None
        report_workspace_pairs = []

        # Expression régulière pour capturer le rapport et l'ID du workspace
        pattern = r"rapport ([\w-]+) dans le workspace ([\w-]+)"

        for error in error_list:
            match = re.search(pattern, error)
            if match:
                report_id = match.group(1)
                workspace_id = match.group(2)
                report_workspace_pairs.append({
                    "report_id": report_id,
                    "workspace_id": workspace_id
                })
        for item in report_workspace_pairs:
            group_id = item.get('workspace_id')
            report_id = item.get('report_id')
            """Récupère les pages d'un rapport spécifique."""
            headers = {"Authorization": f"Bearer {self.access_token}"}
        
            pages_resp = requests.get(f"{self.base_url}/groups/{group_id}", headers=headers, proxies=proxies, verify=False)

            pages_resp.raise_for_status()
            print(pages_resp.json()["name"])

        return report_workspace_pairs

    @staticmethod
    def enrich_metadata_with_excel(metadata_path, excel_path, output_path):
        """Enrichit les métadonnées avec des données provenant d'un fichier Excel."""
        df = pd.read_excel(excel_path)
        mapping = {
            (str(row["workspace"]).strip(), str(row["report"]).strip()): {
                "contact": str(row["contact"]).strip(),
                "description": str(row["description"]).strip()
            }
            for _, row in df.iterrows()
        }

        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        for entry in metadata:
            key = (entry.get("workspace"), entry.get("report"))
            if key in mapping:
                entry["contact"] = mapping[key]["contact"]
                entry["description"] = mapping[key]["description"]
            else:
                entry["contact"] = None
                entry["description"] = None

        with open(output_path, "w") as f:
            json.dump(metadata, f, indent=4, ensure_ascii=False)

        print(f"✅ {len(metadata)} rapports enrichis avec contact et description.")


if __name__ == "__main__":

    client = PowerBIClient()
    access_token = client.get_access_token()
    metadata = client.get_reports_with_pages()
    
    os.makedirs("data", exist_ok=True)
    with open("data/metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Sauvegarde des erreurs dans 'powerbi_api_errors.json'
    if client.errors:
        with open("data/powerbi_api_errors.json", "w", encoding="utf-8") as f:
            json.dump(client.errors, f, indent=2, ensure_ascii=False)

    print("Métadonnées Power BI exportées dans data/metadata.json")
    # Affichage d'un message si des erreurs ont été enregistrées
    if client.errors:
        print("Erreurs rencontrées lors de l'appel de l'API Power BI exportées dans data/powerbi_api_errors.json")
    """
    with open("data/powerbi_api_errors.json", "r", encoding="utf-8") as f:
        errors = json.load(f)
    report_workspace_names = client.extract_report_workspace_names(errors)
    print(report_workspace_names)

    # PowerBIClient.enrich_metadata_with_excel(
    #     metadata_path="data/metadata.json",
    #     excel_path="report_contacts.xlsx",
    #     output_path="data/enriched_metadata.json"
    # )"""
