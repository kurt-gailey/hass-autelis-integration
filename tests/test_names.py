from custom_components.autelis_pool.names import (
    is_placeholder,
    parse_aux_labels_html,
    parse_names_xml,
)
from tests.conftest import load_fixture, load_xml


def test_hayward_labels_come_from_the_setup_page():
    """Hayward has no names.xml -- but the owner's labels are not unavailable.

    They live on the Setup page, editable and persisted on the unit. Renaming an aux
    there flows into Home Assistant, exactly as names.xml does for Jandy.
    """
    labels = parse_aux_labels_html(load_fixture("hayward_1011_settings.htm"))
    assert labels["aux1"] == "Pool Lights"
    assert labels["aux5"] == "Cleaner"
    assert labels["aux6"] == "AUX5"      # unassigned, still the placeholder
    assert len(labels) == 15


def test_malformed_html_yields_no_labels_rather_than_raising():
    """A scrape failure must degrade to default names, never break setup."""
    assert parse_aux_labels_html("<html>nope</html>") == {}
    assert parse_aux_labels_html("") == {}


def test_jandy_labels_come_from_names_xml():
    labels = parse_names_xml(load_xml("jandy_169_names.xml"))
    assert labels["aux1"] == "Cleaner"
    assert labels["aux3"] == "Air Blower"


def test_names_xml_absent_is_empty_not_an_error():
    assert parse_names_xml(None) == {}


def test_placeholder_detection_across_brands():
    """Each brand spells its 'unassigned' label differently."""
    assert is_placeholder("AUX5")      # Hayward
    assert is_placeholder("AUX9")      # Jandy
    assert is_placeholder("AUX 2")     # Pentair (with a space)
    assert is_placeholder("aux 10")

    assert not is_placeholder("Cleaner")
    assert not is_placeholder("Pool Lights")
    assert not is_placeholder("Not Used")   # a real, deliberate label -- keep it
    assert not is_placeholder("AUX EXTRA")  # named, just oddly
