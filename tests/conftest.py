import sys
import os
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from bs4 import BeautifulSoup


def make_table(headers: list, rows: list, caption: Optional[str] = None) -> object:
    html = '<table class="table table--small">'
    if caption is not None:
        html += f"<caption>{caption}</caption>"
    html += "<thead><tr>"
    for h in headers:
        html += f"<th>{h}</th>"
    html += "</tr></thead><tbody>"
    for row in rows:
        html += "<tr>"
        for cell in row:
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    soup = BeautifulSoup(html, "lxml")
    return soup.find("table")


SCRAPED_AT = datetime(2026, 3, 31, tzinfo=timezone.utc)
PROVIDER_NAME = "EDF"
SLUG = "edf"
SOURCE_URL = "https://selectra.info/energie/fournisseurs/edf/tarifs"

