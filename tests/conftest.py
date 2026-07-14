"""Shared test fixtures for the Autelis integration.

The XML/HTML under tests/fixtures/ are verbatim captures from real hardware:

* Jandy Aqualink RS 1.6.9 and 1.6.17 (upstream issues #3 and #6)
* Pentair EasyTouch 1.6.11 (upstream issue #5)
* A live Hayward, model 512, firmware 1.0.11

Nobody here has Jandy or Pentair hardware, so these captures are the only evidence we
have about those brands. Do not hand-edit them to make a test pass.
"""

from pathlib import Path
from xml.etree import ElementTree

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Return the raw text of a captured fixture."""
    return (FIXTURE_DIR / name).read_text()


def load_xml(name: str) -> ElementTree.Element:
    """Return a parsed captured XML fixture."""
    return ElementTree.fromstring(load_fixture(name))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load this custom component in every test."""
    return
