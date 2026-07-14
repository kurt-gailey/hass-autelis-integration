"""The fixtures are real captures. Assert their load-bearing quirks survived.

If one of these fails, the fixture was corrupted -- not the code. Restore the capture;
do not adjust the test.
"""

from tests.conftest import load_fixture, load_xml


def test_jandy_169_has_empty_aux1_while_cleaner_carries_the_state():
    """Upstream issue #3's signature.

    When a cleaner is assigned to AUX1, the Jandy unit blanks <aux1> and routes the
    circuit's state through <cleaner> -- while names.xml still calls aux1 "Cleaner".
    Building entities from names.xml is what produced a phantom switch.
    """
    equipment = load_xml("jandy_169_status.xml").find("equipment")
    assert equipment.find("aux1").text is None
    assert equipment.find("cleaner").text == "0"

    names = load_xml("jandy_169_names.xml").find("equipment")
    assert names.find("aux1").text == "Cleaner"


def test_jandy_1617_exposes_macros_htpmp_and_auxx():
    """Tags that appear in no vendor doc. They must be ignored, not turned into switches."""
    equipment = load_xml("jandy_1617_status.xml").find("equipment")
    assert equipment.find("macro1").text == "0"
    assert equipment.find("auxx").text == "0"
    assert equipment.find("htpmp") is not None


def test_jandy_aux_runs_to_23_not_15():
    """The docs describe aux1-aux15; real RS hardware emits 23."""
    equipment = load_xml("jandy_169_status.xml").find("equipment")
    assert equipment.find("aux23") is not None


def test_hayward_has_no_setpoints_and_absent_aux_are_empty():
    root = load_xml("hayward_1011_status.xml")
    temp = root.find("temp")

    # No setpoint exists to read -- which is half of why Hayward gets no climate entity.
    assert temp.find("poolsp") is None
    assert temp.find("spasp") is None

    # Empty tag == equipment not installed.
    assert temp.find("solartemp").text is None
    assert root.find("equipment").find("aux8").text is None
    assert root.find("equipment").find("aux5").text == "1"


def test_pentair_puts_heat_under_temp_not_equipment():
    """The Pentair trap: reading <equipment> for poolht would KeyError."""
    root = load_xml("pentair_1611_status.xml")
    assert root.find("equipment").find("poolht") is None
    assert root.find("temp").find("poolht").text == "0"
    assert root.find("temp").find("soltemp") is not None   # NOT solartemp


def test_hayward_settings_page_carries_the_owners_aux_labels():
    """Hayward serves no names.xml, but the owner's labels are not unavailable --
    they live on the Setup page, editable and persisted on the unit."""
    html = load_fixture("hayward_1011_settings.htm")
    assert 'id="aux1label" value="Pool Lights"' in html
    assert 'id="aux5label" value="Cleaner"' in html
    assert 'id="aux6label" value="AUX5"' in html   # installed but unassigned
