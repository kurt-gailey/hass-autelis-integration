"""Where each brand keeps the owner's own labels for their equipment.

Jandy and Pentair serve names.xml. Hayward does not (it 404s) -- but its labels are
NOT unavailable: the Autelis Setup page has an editable AUX Labels form, persisted on
the unit, and the device renders those values into the HTML it serves. Scraping that
page is how a Hayward owner's names reach Home Assistant.

Scraping HTML is inelegant. It is also safe here in a way it rarely is: Autelis is
defunct, the firmware will never ship again, and the page is frozen. A parse failure
degrades to generic labels and must never raise.
"""

from __future__ import annotations

import re
from xml.etree.ElementTree import Element

# <input maxlength=15 type="text" id="aux1label" value="Pool Lights"/>
_AUX_LABEL = re.compile(
    r'id\s*=\s*"aux(\d+)label"[^>]*?value\s*=\s*"([^"]*)"', re.IGNORECASE
)

# An unassigned output keeps a placeholder label: "AUX5" (Hayward), "AUX9" (Jandy),
# "AUX 2" (Pentair), "MACRO1" (Jandy OneTouch). The output is real; the owner just has
# not wired or configured it. Upstream skips exactly these prefixes.
_PLACEHOLDER = re.compile(r"^(aux|macro)\s*\d+$", re.IGNORECASE)


def is_placeholder(label: str) -> bool:
    """True when a label means 'this relay exists but is unassigned'."""
    return bool(_PLACEHOLDER.match(label.strip()))


def parse_names_xml(root: Element | None) -> dict[str, str]:
    """Parse names.xml -> {tag: label}. Absent (404) is {} , not an error."""
    if root is None:
        return {}
    equipment = root.find("equipment")
    if equipment is None:
        return {}
    return {
        child.tag: child.text.strip()
        for child in equipment
        if child.text is not None and child.text.strip() != ""
    }


def parse_aux_labels_html(html: str | None) -> dict[str, str]:
    """Parse Hayward's settings.htm -> {"aux1": "Pool Lights", ...}.

    Returns {} on anything unexpected. The caller falls back to default names, so a
    firmware we have not seen costs a user their custom labels -- never their setup.
    """
    if not html:
        return {}
    return {
        f"aux{number}": label.strip()
        for number, label in _AUX_LABEL.findall(html)
        if label.strip()
    }
