"""Load and persist team glossaries from a local directory or SharePoint.

The Streamlit app calls ``read_glossary(path)`` and ``save_glossary(df, path)``.
By default this reads/writes a local Excel file under ``data/glossaries/``.
If the ``USE_SHAREPOINT`` environment variable is truthy, the same calls are
delegated to ``SharePointClient`` instead — useful in enterprise deployments
where glossaries live in a SharePoint document library.
"""
from __future__ import annotations

import os
from io import BytesIO

import openpyxl
import pandas as pd

USE_SHAREPOINT = os.environ.get("USE_SHAREPOINT", "false").lower() in {"1", "true", "yes"}


def _read_local(path: str) -> bytes:
    abs_path = path if os.path.isabs(path) else os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Glossary file not found: {abs_path}")
    with open(abs_path, "rb") as f:
        return f.read()


def _write_local(path: str, binary: bytes) -> str:
    abs_path = path if os.path.isabs(path) else os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "wb") as f:
        f.write(binary)
    return abs_path


def _excel_bytes_to_dict(binary: bytes) -> list[dict]:
    workbook = openpyxl.load_workbook(BytesIO(binary))
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    return [
        {headers[i]: row[i] for i in range(len(headers))}
        for row in sheet.iter_rows(min_row=2, values_only=True)
    ]


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return buf.getvalue()


def read_glossary(path: str) -> pd.DataFrame:
    """Read a glossary Excel file and return it as a DataFrame."""
    if USE_SHAREPOINT:
        from sharepoint_connector import SharePointClient

        client = SharePointClient()
        binary = client.read_binary_file(path)
    else:
        binary = _read_local(path)
    rows = _excel_bytes_to_dict(binary)
    return pd.DataFrame(rows)


def save_glossary(df: pd.DataFrame, path: str) -> str | None:
    """Persist a DataFrame back to the glossary store.

    Returns a URL/path to the saved artefact (or ``None`` if not applicable).
    """
    binary = _df_to_excel_bytes(df)
    if USE_SHAREPOINT:
        from sharepoint_connector import SharePointClient

        client = SharePointClient()
        return client.save_binary_in_sharepoint(binary, path, get_link=True)
    return _write_local(path, binary)
