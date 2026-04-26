"""Optional SharePoint Online client (Microsoft Graph API).

Used only when ``USE_SHAREPOINT=true`` is set in the environment. For local
development, ``glossary_loader.py`` reads/writes Excel files from the
``data/glossaries/`` directory instead.
"""
import os
from io import BytesIO
from typing import Iterator, Tuple

import openpyxl
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


class SharePointClient:
    """Minimal SharePoint Online client (auth + read/write of files)."""

    def __init__(self) -> None:
        self.client_id = os.environ.get("SHAREPOINT_CLIENT_ID")
        self.client_secret = os.environ.get("SHAREPOINT_CLIENT_SECRET")
        self.tenant_id = os.environ.get("SHAREPOINT_TENANT_ID")
        self.site_hostname = os.environ.get("SHAREPOINT_SITE_HOSTNAME", "")
        self.site_relative_path = os.environ.get("SHAREPOINT_SITE_RELATIVE_PATH", "")

        missing = [
            name
            for name, val in [
                ("SHAREPOINT_CLIENT_ID", self.client_id),
                ("SHAREPOINT_CLIENT_SECRET", self.client_secret),
                ("SHAREPOINT_TENANT_ID", self.tenant_id),
                ("SHAREPOINT_SITE_HOSTNAME", self.site_hostname),
                ("SHAREPOINT_SITE_RELATIVE_PATH", self.site_relative_path),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                "SharePointClient cannot start — missing env vars: " + ", ".join(missing)
            )

        self.session = requests.Session()
        self.session.proxies = {
            "http": os.environ.get("HTTP_PROXY"),
            "https": os.environ.get("HTTPS_PROXY"),
        }
        self.access_token = self.get_access_token()
        self.site_id = self.get_site_id(
            site_hostname=self.site_hostname,
            site_relative_path=self.site_relative_path,
        )

    def get_access_token(self) -> str:
        """Obtains an OAuth2 token for Microsoft Graph API."""
        # Set business proxies to get access token
        business_proxies = {
            "http": os.environ.get("BUSINESS_HTTP_PROXY"),
            "https": os.environ.get("BUSINESS_HTTPS_PROXY"),
        }

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }

        response = requests.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data=data,
            proxies=business_proxies,
            verify=False,
        )
        return response.json().get("access_token")

    def check_token_validity(self) -> str:
        """
        Validates the given access token by making a request to the OAuth2 token endpoint.

        Args:
            access_token (str): The access token to be validated.

        Returns:
            str: The access token if valid, otherwise a new access token is obtained.
        """

        # simple “ping” against Graph API to validate the token
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root"
        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            return self.access_token
        else:
            access_token = self.get_access_token()
            return access_token
        
    def get_site_id(self, site_hostname: str, site_relative_path: str) -> str:
        """Retrieves the SharePoint site ID.

        Args:
            site_hostname (str): SharePoint hostname.
            site_relative_path (str): Relative path of the site.

        Returns:
            str: Site ID.
        """
        full_url = f"https://graph.microsoft.com/v1.0/sites/{site_hostname}:{site_relative_path}"
        response = self.session.get(full_url, headers={"Authorization": f"Bearer {self.access_token}"})
        return response.json().get("id", "")

    def list_folders_in_path(self, path: str) -> list[str]:
        """Lists the folders at a given path.

        Args:
            path (str): Path in the SharePoint document library.

        Returns:
            list[str]: Names of the folders.
        """
        self.access_token = self.check_token_validity()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{path}:/children"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.get(url, headers=headers)
        response.raise_for_status()

        # Retrieve folders from the response
        items = response.json().get("value", [])
        folders = [item for item in items if item.get("folder") is not None]
        return [folder.get("name") for folder in folders]

    def list_files_in_path(self, path: str) -> list[str]:
        """Lists the files at a given path.

        Args:
            path (str): Path in the SharePoint document library.

        Returns:
            list[str]: Names of the files.
        """
        self.access_token = self.check_token_validity()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{path}:/children"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        items = response.json().get("value", [])
        files = [item["name"] for item in items if item.get("file")]
        return files

    # @st.cache_data(show_spinner=False)
    def folder_exists_in_sharepoint(self, folder_path: str) -> bool:
        """Checks if a folder exists in SharePoint.

        Args:
            folder_path (str): Full path of the folder.

        Returns:
            bool: True if it exists, False otherwise.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = self.session.get(url, headers=headers)
        return resp.status_code == 200

    # @st.cache_data(show_spinner=False)
    def file_exists_in_sharepoint(self, file_path: str) -> bool:
        """Checks if a file exists in SharePoint.

        Args:
            file_path (str): Full path of the file.

        Returns:
            bool: True if it exists, False otherwise.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{file_path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        resp = self.session.get(url, headers=headers)
        return resp.status_code == 200

    def delete_folder_in_sharepoint(self, folder_path: str) -> None:
        """Deletes a folder and all its contents in SharePoint.

        Args:
            folder_path (str): Full path of the folder.

        Returns:
            None.
        """
        # Walk through the folder structure and delete files and subfolders
        for current_path, folders, files in self.walk_sharepoint_path(folder_path):
            # Delete all files in the current folder
            for file_name in files:
                file_path = f"{current_path}/{file_name}"
                self.delete_file_in_sharepoint(file_path)

        # Delete all subfolders (in reverse order to ensure proper deletion)
        for current_path, folders, _ in reversed(list(self.walk_sharepoint_path(folder_path))):
            for folder_name in folders:
                subfolder_path = f"{current_path}/{folder_name}"
                url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{subfolder_path}"
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = self.session.delete(url, headers=headers)
                response.raise_for_status()

        # Finally, delete the root folder itself
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{folder_path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = self.session.delete(url, headers=headers)
        response.raise_for_status()

   

    def delete_file_in_sharepoint(self, file_path: str) -> None:
        """Deletes a file in SharePoint.

        Args:
            file_path (str): Full path of the file.

        Returns:
            None.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{file_path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.delete(url, headers=headers)
        response.raise_for_status()

    def walk_sharepoint_path(self, path: str) -> Iterator[Tuple[str, list[str], list[str]]]:
        """Iterator over the hierarchy of a SharePoint path.

        Args:
            path (str): Starting path.

        Yields:
            Iterator[Tuple[str, list[str], list[str]]]: Tuple (path, folders, files).
        """
        folders = self.list_folders_in_path(path)
        files = self.list_files_in_path(path)
        yield path, folders, files

        for folder in folders:
            sub_path = f"{path}/{folder}"
            yield from self.walk_sharepoint_path(sub_path)

    def get_file_last_modified_time(self, file_path: str) -> str:
        """Retrieves the last modified date of a file.

        Args:
            file_path (str): Full path of the file.

        Returns:
            str: Date in ISO 8601 format.
        """
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{file_path}"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.get(url, headers=headers)
        response.raise_for_status()

        last_modified_time = response.json().get("lastModifiedDateTime", "")
        return last_modified_time




    # @st.cache_data(show_spinner=False)
    def read_binary_file(self, path: str) -> bytes:
        """Reads a binary file from a SharePoint site using Microsoft Graph API.

        Args:
            path (str): The relative path to the file in the SharePoint site.

        Returns:
            bytes: The binary content of the file.
        """
        self.access_token = self.check_token_validity()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{path}:/content"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return response.content

    def read_excel_file_as_dict(self, binary_content):
        # Charger le fichier Excel directement depuis le buffer mémoire
        workbook = openpyxl.load_workbook(BytesIO(binary_content))
        sheet = workbook.active  # Obtenir la première feuille de calcul

        # Lire les données de la feuille
        headers = [cell.value for cell in sheet[1]]  # Lire la première ligne comme entêtes
        data = []

        for row in sheet.iter_rows(min_row=2, values_only=True):  # Ignorer la première ligne
            row_dict = {headers[i]: row[i] for i in range(len(headers))}
            data.append(row_dict)

        return data
    
    def update_excel_file(self, df: pd.DataFrame, path: str):
        """Met à jour un fichier Excel sur SharePoint avec les modifications du DataFrame.

        Args:
            df (pd.DataFrame): Le DataFrame contenant les données mises à jour.
            path (str): Le chemin relatif du fichier sur le site SharePoint.
        """
        # Convertir le DataFrame en un fichier Excel temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            df.to_excel(tmp_file.name, index=False)

            # Lire le contenu binaire du fichier temporaire
            with open(tmp_file.name, 'rb') as f:
                binary_content = f.read()

        # Obtenir un token d'accès valide
        self.access_token = self.check_token_validity()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{path}:/content"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

        # Mettre à jour le fichier sur SharePoint
        response = self.session.put(url, headers=headers, data=binary_content)
        response.raise_for_status()  # Vérifier si la requête a réussi

        print("Le fichier Excel a été mis à jour avec succès.")

    def save_binary_in_sharepoint(self, binary_data: bytes, path: str, get_link: bool = False) -> str | None:
        """Saves a binary file to a specified path in SharePoint.

        Args:
            binary_data (bytes): The binary content of the file to be saved.
            path (str): The path in SharePoint where the file will be saved.

        Returns:
            str: The web URL of the saved file.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to save the file fails.
        """
        self.access_token = self.check_token_validity()
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root:/{path}:/content"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        response = self.session.put(url, headers=headers, data=binary_data)
        response.raise_for_status()
        if get_link:
            item = response.json()
            return item.get("webUrl")

    def save_dataframe_in_sharepoint(self, df: pd.DataFrame, path: str, get_link: bool = False) -> str | None:
        """Saves a DataFrame as an Excel file to a specified path in SharePoint.

        Args:
            df (pd.DataFrame): The DataFrame to be saved as an Excel file.
            path (str): The path in SharePoint where the file will be saved.
            get_link (bool): If True, return the web URL of the saved file.

        Returns:
            str: The web URL of the saved file, if get_link is True.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request to save the file fails.
        """
        # Convert the DataFrame to a binary Excel file
        with BytesIO() as output:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            binary_data = output.getvalue()

        # Call the existing method to save the binary data to SharePoint
        return self.save_binary_in_sharepoint(binary_data, path, get_link)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sharepoint_connector.py <relative/path/to/file.xlsx>")
        sys.exit(1)

    client = SharePointClient()
    file_path = sys.argv[1]

    try:
        binary_content = client.read_binary_file(file_path)
        excel_data = client.read_excel_file_as_dict(binary_content)
        df = pd.DataFrame(excel_data)
        print(df)
    except Exception as e:
        print(f"An error occurred: {e}")
