"""Power BI REST API client.

Used by the bootstrap script to crawl every workspace/report/page accessible to
the configured service principal and write the result to ``data/metadata.json``.
"""
import json
import os
import re

import pandas as pd
import requests
import urllib3
from dotenv import load_dotenv
from tqdm import tqdm


def _proxies() -> dict | None:
    if os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
        return {
            "http": os.getenv("BUSINESS_HTTP_PROXY") or os.getenv("HTTP_PROXY"),
            "https": os.getenv("BUSINESS_HTTPS_PROXY") or os.getenv("HTTPS_PROXY"),
        }
    return None


class PowerBIClient:
    """Client for the Power BI REST API."""

    def __init__(self) -> None:
        load_dotenv()
        self.tenant_id = os.environ.get("POWERBI_TENANT_ID")
        self.client_id = os.environ.get("POWERBI_CLIENT_ID")
        self.client_secret = os.environ.get("POWERBI_CLIENT_SECRET")
        self.base_url = "https://api.powerbi.com/v1.0/myorg"

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        self.access_token = self.get_access_token()
        self.errors: list[str] = []

    def get_access_token(self) -> str:
        """Fetch an OAuth2 access token for the Power BI API."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://analysis.windows.net/powerbi/api/.default",
        }

        try:
            response = requests.post(url, headers=headers, data=data, proxies=_proxies())
            response.raise_for_status()
            return response.json()["access_token"]
        except requests.exceptions.RequestException as e:
            print(f"Failed to obtain Power BI access token: {e}")
            raise

    def get_workspaces(self) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = requests.get(
                f"{self.base_url}/groups", headers=headers, proxies=_proxies(), verify=False
            )
            resp.raise_for_status()
            return resp.json()["value"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append("HTTP 400 fetching workspaces")
            else:
                print(f"Error fetching workspaces: {e}")
            return []

    def get_reports_from_workspace(self, group_id: str) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = requests.get(
                f"{self.base_url}/groups/{group_id}/reports",
                headers=headers,
                proxies=_proxies(),
                verify=False,
            )
            resp.raise_for_status()
            return resp.json()["value"]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append(f"HTTP 400 fetching reports for workspace {group_id}")
            else:
                print(f"Error fetching reports for workspace {group_id}: {e}")
            return []

    def get_report_pages(self, group_id: str, report_id: str) -> list[dict]:
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            resp = requests.get(
                f"{self.base_url}/groups/{group_id}/reports/{report_id}/pages",
                headers=headers,
                proxies=_proxies(),
                verify=False,
            )
            resp.raise_for_status()
            return [{"name": p["displayName"]} for p in resp.json().get("value", [])]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                self.errors.append(
                    f"HTTP 400 fetching pages for report {report_id} in workspace {group_id}"
                )
            else:
                self.errors.append(
                    f"Error fetching pages for report {report_id} in workspace {group_id}: {e}"
                )
            return []

    def get_reports_with_pages(self) -> list[dict]:
        """Crawl every accessible workspace and return enriched report metadata."""
        enriched_data: list[dict] = []
        workspaces = self.get_workspaces()

        for group in tqdm(workspaces, desc="Workspaces", unit="workspace"):
            group_id = group.get("id")
            group_name = group.get("name")

            try:
                reports = self.get_reports_from_workspace(group_id)
            except Exception as e:
                self.errors.append(
                    f"Failed to fetch reports for workspace {group_name} ({group_id}): {e}"
                )
                continue

            for report in tqdm(
                reports, desc=f"Reports in {group_name}", unit="report", leave=False
            ):
                report_id = report.get("id")
                report_name = report.get("name")
                report_url = report.get("webUrl", "")

                try:
                    pages = self.get_report_pages(group_id=group_id, report_id=report_id)
                    enriched_data.append(
                        {
                            "workspace": group_name,
                            "report": report_name,
                            "report_url": report_url,
                            "pages": pages,
                        }
                    )
                except Exception as e:
                    self.errors.append(
                        f"Failed to fetch pages for report {report_name} ({report_id}) "
                        f"in workspace {group_name}: {e}"
                    )
                    continue

        return enriched_data

    @staticmethod
    def enrich_metadata_with_excel(metadata_path: str, excel_path: str, output_path: str) -> None:
        """Enrich metadata with contact/description data from an Excel sidecar file."""
        df = pd.read_excel(excel_path)
        mapping = {
            (str(row["workspace"]).strip(), str(row["report"]).strip()): {
                "contact": str(row["contact"]).strip(),
                "description": str(row["description"]).strip(),
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

        print(f"✅ {len(metadata)} reports enriched with contact and description.")


if __name__ == "__main__":
    client = PowerBIClient()
    metadata = client.get_reports_with_pages()

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    with open(os.path.join(data_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    if client.errors:
        with open(os.path.join(data_dir, "powerbi_api_errors.json"), "w", encoding="utf-8") as f:
            json.dump(client.errors, f, indent=2, ensure_ascii=False)
        print(
            f"⚠ {len(client.errors)} errors written to data/powerbi_api_errors.json"
        )

    print(f"✅ Power BI metadata exported to data/metadata.json ({len(metadata)} reports)")
