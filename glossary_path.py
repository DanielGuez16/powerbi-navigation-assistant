"""Per-team paths to the glossary Excel file.

By default the glossary is loaded from the local ``data/glossaries/`` directory.
If a SharePoint client is configured (see ``sharepoint_connector.py``), the same
relative path can also resolve against a SharePoint document library.
"""

glossary = {
    "Finance": "data/glossaries/glossary_finance.xlsx",
    "Engineering": "data/glossaries/glossary_engineering.xlsx",
    "Data Management": "data/glossaries/glossary_data_management.xlsx",
    "Other": "",
}
