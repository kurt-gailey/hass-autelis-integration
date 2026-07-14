# Hayward Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Hayward (AquaLogic/Goldline) support to the Autelis Home Assistant integration, without regressing Jandy or Pentair — neither of which we can test on hardware.

**Architecture:** Replace the hardcoded, Jandy-shaped tables in `const.py` with (1) a per-brand `BrandProfile` that declares what each XML tag *is* (its role), and (2) presence-discovery that reads `status.xml` to decide which of those tags are actually *installed*. Discovery decides presence; the profile decides role. A tag the profile doesn't know is ignored, never guessed at.

**Tech Stack:** Python 3.12+, Home Assistant custom component, `pytest` + `pytest-homeassistant-custom-component`, stdlib `xml.etree.ElementTree`.

**Spec:** `docs/superpowers/specs/2026-07-14-hayward-support-design.md` — read it first. It records several inferences that turned out wrong on hardware; do not re-derive them.

## Global Constraints

- **No hardware for Jandy or Pentair.** Every behavioural claim about them must be pinned by a test against a real captured fixture. Do not "improve" Jandy behaviour beyond what the spec authorises.
- **`set.cgi` returning `1` does not mean the write took effect.** It means the name was recognised. Never derive state from a command response; state comes from the next `status.xml` poll.
- **A circuit write can be silently refused by the panel** (interlocks: spa mode, freeze, service mode). Switches must not assume their write landed.
- **Hayward has no climate entity.** No setpoints exist to read or write. Do not add one.
- **Empty XML tag = equipment not installed.** `<aux8></aux8>` means absent, not off.
- **Preserve existing `unique_id` scheme:** `f"autelis {host} {tag}"`. Changing it silently breaks users' dashboards.
- Keep upstream's existing constant names (`AUTELIS_JANDY = 0`, `AUTELIS_PENTAIR = 1`) — this targets a PR to `k-harker/hass-autelis-integration`.
- Do **not** claim in the PR that this fixes upstream issue #3. It was already fixed in release 1.0.6. This work makes that fix independent of the user's name string.

## File Structure

| File | Responsibility |
| --- | --- |
| `custom_components/autelis_pool/brands.py` | **NEW.** `BrandProfile` dataclass, the three profiles, tag→role maps, `detect_brand()`. |
| `custom_components/autelis_pool/names.py` | **NEW.** Per-brand label sources: `names.xml` (Jandy/Pentair) and `settings.htm` (Hayward). Pure parsers. |
| `custom_components/autelis_pool/discovery.py` | **NEW.** `build_inventory()` — turns a parsed `status.xml` + profile + names into a list of `EntityDescriptor`. Pure, no HA imports. |
| `custom_components/autelis_pool/binary_sensor.py` | **NEW.** Read-only equipment (Hayward `poolht`, `waterfall`). |
| `custom_components/autelis_pool/const.py` | Modify. Add `AUTELIS_HAYWARD`, `AUTELIS_UNKNOWN`. Remove `CIRCUITS` / `HEAT_SET` / `TEMP_SENSORS` (they move into `brands.py`). |
| `custom_components/autelis_pool/api.py` | Modify. Brand-aware command construction; tolerate 404 on optional endpoints. |
| `custom_components/autelis_pool/__init__.py` | Modify. Per-config-entry data, brand detection at setup, atomic snapshot rebuild. |
| `custom_components/autelis_pool/switch.py` | Modify. Driven by inventory. Dimmer fix. |
| `custom_components/autelis_pool/sensor.py` | Modify. Driven by inventory. Two bug fixes. |
| `custom_components/autelis_pool/climate.py` | Modify. Brand-aware heat section/param/range. |
| `tests/` | **NEW.** Fixtures (real captures) + unit tests + the entity-manifest regression gate. |

---

### Task 1: Test harness and real fixtures

Nothing can be verified without this, and the fixtures are the entire safety argument for Jandy.

**Files:**
- Create: `requirements_test.txt`, `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`
- Create: `tests/fixtures/{jandy_169_status.xml, jandy_169_names.xml, jandy_1617_status.xml, pentair_1611_status.xml, pentair_1611_names.xml, hayward_1011_status.xml}`
- Modify: `.github/workflows/validate.yaml`

**Interfaces:**
- Produces: `load_fixture(name) -> str` and `load_xml(name) -> Element`, used by every later task.

- [ ] **Step 1: Create the test requirements and pytest config**

`requirements_test.txt`:

```text
pytest>=8.0.0
pytest-homeassistant-custom-component>=0.13.0
```

`pytest.ini` — **`asyncio_mode = auto` is not optional.** Without it every `async def test_`
is collected, skipped, and reported as passing, so the whole async half of this suite would be
green while testing nothing:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 2: Add the real fixtures**

These are **verbatim captures from real hardware**. Do not hand-edit them — their quirks (empty tags, `aux1` blank while `cleaner` carries state) are the whole point.

`tests/fixtures/jandy_169_status.xml` — Jandy Aqualink RS, fw 1.6.9, from upstream issue #3:

```xml
<response>
	<system>
		<runstate>8</runstate>
		<model>6520</model>
		<dip>10000000</dip>
		<opmode>0</opmode>
		<vbat>0</vbat>
		<lowbat>1</lowbat>
		<version>1.6.9</version>
		<time>1749940510</time>
	</system>
	<equipment>
		<pump>1</pump>
		<pumplo></pumplo>
		<spa>0</spa>
		<waterfall></waterfall>
		<cleaner>0</cleaner>
		<poolht2></poolht2>
		<poolht>0</poolht>
		<spaht>0</spaht>
		<solarht>0</solarht>
		<aux1></aux1>
		<aux2>0</aux2>
		<aux3>0</aux3>
		<aux4>0</aux4>
		<aux5>0</aux5>
		<aux6>0</aux6>
		<aux7>0</aux7>
		<aux8></aux8>
		<aux9></aux9>
		<aux10></aux10>
		<aux11></aux11>
		<aux12></aux12>
		<aux13></aux13>
		<aux14></aux14>
		<aux15></aux15>
		<aux16></aux16>
		<aux17></aux17>
		<aux18></aux18>
		<aux19></aux19>
		<aux20></aux20>
		<aux21></aux21>
		<aux22></aux22>
		<aux23></aux23>
	</equipment>
	<temp>
		<poolsp>90</poolsp>
		<poolsp2>60</poolsp2>
		<spasp>98</spasp>
		<pooltemp>86</pooltemp>
		<spatemp>88</spatemp>
		<airtemp>89</airtemp>
		<solartemp>0</solartemp>
		<tempunits>F</tempunits>
	</temp>
</response>
```

`tests/fixtures/jandy_169_names.xml` — note `aux1` = "Cleaner" while `<aux1>` is **empty** in status:

```xml
<response>
	<equipment>
		<aux1>Cleaner</aux1>
		<aux2>Waterfall</aux2>
		<aux3>Air Blower</aux3>
		<aux4>SPA Light</aux4>
		<aux5>Pool Light</aux5>
		<aux6>Not Used</aux6>
		<aux7>Not Used</aux7>
		<aux8>AUX8</aux8>
		<aux9>AUX9</aux9>
		<aux10>AUX10</aux10>
		<aux11>AUX11</aux11>
		<aux12>AUX12</aux12>
		<aux13>AUX13</aux13>
		<aux14>AUX14</aux14>
		<aux15>AUX15</aux15>
		<aux16></aux16>
		<aux17></aux17>
		<aux18></aux18>
		<aux19></aux19>
		<aux20></aux20>
		<aux21></aux21>
		<aux22></aux22>
		<aux23></aux23>
	</equipment>
</response>
```

`tests/fixtures/hayward_1011_status.xml` — live capture, model 512, fw 1.0.11:

```xml
<response>
	<system>
		<model>512</model>
		<opmode>0</opmode>
		<err>0</err>
		<version>1.0.11</version>
		<time>1784046161</time>
	</system>
	<equipment>
		<pump>1</pump>
		<spa>0</spa>
		<waterfall>0</waterfall>
		<valve3>0</valve3>
		<poolht>0</poolht>
		<valve4>0</valve4>
		<aux1>0</aux1>
		<aux2>0</aux2>
		<aux3>0</aux3>
		<aux4>0</aux4>
		<aux5>1</aux5>
		<aux6>0</aux6>
		<aux7>0</aux7>
		<aux8></aux8>
		<aux9></aux9>
		<aux10></aux10>
		<aux11></aux11>
		<aux12></aux12>
		<aux13></aux13>
		<aux14></aux14>
		<aux15></aux15>
		<schlor>0</schlor>
	</equipment>
	<temp>
		<pooltemp>88</pooltemp>
		<spatemp>95</spatemp>
		<airtemp>87</airtemp>
		<solartemp></solartemp>
		<tempunits>F</tempunits>
	</temp>
</response>
```

`tests/fixtures/pentair_1611_status.xml` — Pentair EasyTouch, fw 1.6.11, upstream issue #5. Note `poolht`/`spaht` live under `<temp>`, not `<equipment>`:

```xml
<response>
	<system>
		<runstate>50</runstate>
		<model>13</model>
		<haddr>1</haddr>
		<opmode>0</opmode>
		<freeze>0</freeze>
		<sensor1>0</sensor1>
		<sensor2>0</sensor2>
		<sensor3>0</sensor3>
		<sensor4>0</sensor4>
		<sensor5>0</sensor5>
		<version>1.6.11</version>
		<time>1750771643</time>
		<systime>9,31,4,24,6,25,0,1</systime>
	</system>
	<equipment>
		<circuit1>0</circuit1>
		<circuit2>0</circuit2>
		<circuit3>0</circuit3>
		<circuit4>0</circuit4>
		<circuit5>0</circuit5>
		<circuit6>1</circuit6>
		<circuit7>0</circuit7>
		<circuit8>0</circuit8>
		<circuit9>0</circuit9>
		<circuit10></circuit10>
		<circuit11></circuit11>
		<circuit12></circuit12>
		<circuit13></circuit13>
		<circuit14></circuit14>
		<circuit15></circuit15>
		<circuit16></circuit16>
		<circuit17></circuit17>
		<circuit18></circuit18>
		<circuit19></circuit19>
		<circuit20>0</circuit20>
		<feature1>0</feature1>
		<feature2>0</feature2>
		<feature3>0</feature3>
		<feature4>0</feature4>
		<feature5>0</feature5>
		<feature6>0</feature6>
		<feature7>0</feature7>
		<feature8>0</feature8>
		<feature9></feature9>
		<feature10></feature10>
	</equipment>
	<temp>
		<poolht>0</poolht>
		<spaht>0</spaht>
		<htstatus>0</htstatus>
		<poolsp>68</poolsp>
		<spasp>101</spasp>
		<maxplsp></maxplsp>
		<pooltemp>86</pooltemp>
		<spatemp>86</spatemp>
		<airtemp>82</airtemp>
		<soltemp></soltemp>
		<tempunits>F</tempunits>
		<htpump>0</htpump>
	</temp>
</response>
```

`tests/fixtures/pentair_1611_names.xml`:

```xml
<response>
	<equipment>
		<circuit1>SPA</circuit1>
		<circuit2>LIGHTS</circuit2>
		<circuit3>AUX 2</circuit3>
		<circuit4>AUX 3</circuit4>
		<circuit5>AUX 4</circuit5>
		<circuit6>POOL</circuit6>
		<circuit7>AUX 5</circuit7>
		<circuit8>AUX 6</circuit8>
		<circuit9>POOL HIGH</circuit9>
		<circuit10></circuit10>
		<circuit11></circuit11>
		<circuit12></circuit12>
		<circuit13></circuit13>
		<circuit14></circuit14>
		<circuit15></circuit15>
		<circuit16></circuit16>
		<circuit17></circuit17>
		<circuit18></circuit18>
		<circuit19></circuit19>
		<circuit20>AUX EXTRA</circuit20>
		<feature1>FEATURE 1</feature1>
		<feature2>FEATURE 2</feature2>
		<feature3>FEATURE 3</feature3>
		<feature4>FEATURE 4</feature4>
		<feature5>FEATURE 5</feature5>
		<feature6>FEATURE 6</feature6>
		<feature7>FEATURE 7</feature7>
		<feature8>FEATURE 8</feature8>
		<feature9></feature9>
		<feature10></feature10>
	</equipment>
</response>
```

`tests/fixtures/jandy_1617_status.xml` — Jandy fw 1.6.17 (upstream issue #6). Exists specifically to prove `macro1`–`macro6`, `htpmp` and `auxx` are **ignored**, not turned into switches. There is no `names.xml` for this unit; that is intentional (it exercises the names-absent path):

```xml
<response>
	<system>
		<runstate>8</runstate>
		<model>6520</model>
		<dip>00000000</dip>
		<opmode>0</opmode>
		<vbat>615</vbat>
		<lowbat>0</lowbat>
		<version>1.6.17</version>
		<time>1761053979</time>
	</system>
	<equipment>
		<pump>1</pump>
		<pumplo/>
		<spa>0</spa>
		<waterfall/>
		<cleaner/>
		<poolht2/>
		<poolht>0</poolht>
		<spaht>0</spaht>
		<solarht/>
		<htpmp/>
		<aux1>0</aux1>
		<aux2>0</aux2>
		<aux3>0</aux3>
		<aux4>0</aux4>
		<aux5>0</aux5>
		<aux6>0</aux6>
		<aux7>0</aux7>
		<aux8/>
		<aux9/>
		<aux10/>
		<aux11/>
		<aux12/>
		<aux13/>
		<aux14/>
		<aux15/>
		<aux16/>
		<aux17/>
		<aux18/>
		<aux19/>
		<aux20/>
		<aux21/>
		<aux22/>
		<aux23/>
		<auxx>0</auxx>
		<macro1>0</macro1>
		<macro2>0</macro2>
		<macro3>0</macro3>
		<macro4>0</macro4>
		<macro5>0</macro5>
		<macro6>0</macro6>
	</equipment>
	<temp>
		<poolsp>80</poolsp>
		<poolsp2>60</poolsp2>
		<spasp>100</spasp>
		<pooltemp>78</pooltemp>
		<spatemp>0</spatemp>
		<airtemp>75</airtemp>
		<solartemp>0</solartemp>
		<tempunits>F</tempunits>
	</temp>
</response>
```

- [ ] **Step 3: Write the fixture loader**

`tests/__init__.py` — empty file.

`tests/conftest.py`:

```python
"""Shared test fixtures for the Autelis integration."""

from pathlib import Path
from xml.etree import ElementTree

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Return the raw text of a captured XML fixture."""
    return (FIXTURE_DIR / name).read_text()


def load_xml(name: str) -> ElementTree.Element:
    """Return a parsed captured XML fixture."""
    return ElementTree.fromstring(load_fixture(name))


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of this custom component in every test."""
    return
```

- [ ] **Step 4: Verify the harness runs and the fixtures parse**

Create `tests/test_fixtures.py`:

```python
"""The fixtures are real captures; assert their load-bearing quirks survived."""

from tests.conftest import load_xml


def test_jandy_169_has_empty_aux1_with_cleaner_carrying_state():
    """Issue #3's signature: aux1 is blank, <cleaner> holds the state."""
    equip = load_xml("jandy_169_status.xml").find("equipment")
    assert equip.find("aux1").text is None
    assert equip.find("cleaner").text == "0"


def test_hayward_has_no_setpoints_and_absent_aux_are_empty():
    root = load_xml("hayward_1011_status.xml")
    temp = root.find("temp")
    assert temp.find("poolsp") is None
    assert temp.find("spasp") is None
    assert temp.find("solartemp").text is None
    assert root.find("equipment").find("aux8").text is None


def test_pentair_puts_heat_under_temp_not_equipment():
    root = load_xml("pentair_1611_status.xml")
    assert root.find("equipment").find("poolht") is None
    assert root.find("temp").find("poolht").text == "0"
```

Run: `python -m pytest tests/ -v`
Expected: 3 passed.

- [ ] **Step 5: Add the test job to CI**

Replace `.github/workflows/validate.yaml` with:

```yaml
name: Validate

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  validate-hacs:
    runs-on: "ubuntu-latest"
    steps:
      - name: HACS validation
        uses: "hacs/action@main"
        with:
          category: "integration"

  tests:
    runs-on: "ubuntu-latest"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements_test.txt
      - run: python -m pytest tests/ -v
```

- [ ] **Step 6: Commit**

```bash
git add requirements_test.txt tests/ .github/workflows/validate.yaml
git commit -m "test: add pytest harness and real captured XML fixtures

Fixtures are verbatim captures from real hardware: Jandy 1.6.9 and 1.6.17
(upstream issues #3, #6), Pentair EasyTouch 1.6.11 (issue #5), and a live
Hayward model 512 fw 1.0.11. Their quirks are load-bearing and must not be
hand-edited."
```

---

### Task 2: Brand profiles and detection (`brands.py`)

**Files:**
- Create: `custom_components/autelis_pool/brands.py`
- Modify: `custom_components/autelis_pool/const.py`
- Modify: `custom_components/autelis_pool/__init__.py` (one line — see the note below)
- Test: `tests/test_brands.py`

> **Import-order trap.** `__init__.py` imports `TEMP_SENSORS` from `const.py`. Removing that
> dict here breaks the *package* import, so `tests/test_brands.py` cannot even be collected —
> importing any submodule of `custom_components.autelis_pool` executes its `__init__.py` first.
> The import is **unused** in `__init__.py` (it appears only on the import line), so delete
> `TEMP_SENSORS,` from that import list as part of this task. `switch.py` / `sensor.py` /
> `climate.py` genuinely use the removed dicts and will be broken until their own tasks rewrite
> them — that is expected, and does not block collection, because they are not imported at
> package-init time.

**Interfaces:**
- Produces:
  - `ROLE_CIRCUIT`, `ROLE_READONLY`, `ROLE_HEAT`, `ROLE_SETPOINT`, `ROLE_TEMPERATURE`, `ROLE_IGNORE` (str constants)
  - `HeatSet = namedtuple("HeatSet", "name current_tag setpoint_tag heat_tag")`
  - `BrandProfile` dataclass with `.role(tag) -> str`
  - `PROFILES: dict[int, BrandProfile]`
  - `detect_brand(root: Element) -> int`
- Consumes: `AUTELIS_JANDY`, `AUTELIS_PENTAIR`, `AUTELIS_HAYWARD`, `AUTELIS_UNKNOWN` from `const.py`.

- [ ] **Step 1: Write the failing tests**

`tests/test_brands.py`:

```python
from xml.etree import ElementTree

import pytest

from custom_components.autelis_pool.brands import (
    PROFILES,
    ROLE_CIRCUIT,
    ROLE_HEAT,
    ROLE_IGNORE,
    ROLE_READONLY,
    ROLE_SETPOINT,
    ROLE_TEMPERATURE,
    detect_brand,
)
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
    AUTELIS_UNKNOWN,
)
from tests.conftest import load_xml


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("jandy_169_status.xml", AUTELIS_JANDY),
        ("jandy_1617_status.xml", AUTELIS_JANDY),
        ("pentair_1611_status.xml", AUTELIS_PENTAIR),
        ("hayward_1011_status.xml", AUTELIS_HAYWARD),
    ],
)
def test_detect_brand_from_real_captures(fixture, expected):
    assert detect_brand(load_xml(fixture)) == expected


def test_sparse_xml_is_unknown_not_jandy():
    """A disconnected controller must NOT fall through to Jandy."""
    root = ElementTree.fromstring(
        "<response><system><runstate>1</runstate><model>0</model></system>"
        "<equipment></equipment><temp></temp></response>"
    )
    assert detect_brand(root) == AUTELIS_UNKNOWN


def test_empty_document_is_unknown():
    assert detect_brand(ElementTree.fromstring("<response></response>")) == AUTELIS_UNKNOWN


def test_jandy_roles():
    p = PROFILES[AUTELIS_JANDY]
    assert p.role("pump") == ROLE_CIRCUIT
    assert p.role("cleaner") == ROLE_CIRCUIT
    assert p.role("solarht") == ROLE_CIRCUIT      # upstream exposes this as a switch
    assert p.role("aux23") == ROLE_CIRCUIT        # docs say 15; real RS16 emits 23
    assert p.role("poolht") == ROLE_HEAT
    assert p.role("poolsp") == ROLE_SETPOINT
    assert p.role("pooltemp") == ROLE_TEMPERATURE
    assert p.role("macro1") == ROLE_IGNORE        # set.cgi name unverified
    assert p.role("htpmp") == ROLE_IGNORE
    assert p.role("auxx") == ROLE_IGNORE
    assert p.role("tempunits") == ROLE_IGNORE
    assert p.role("nonsense") == ROLE_IGNORE      # unknown tags are ignored, not guessed


def test_hayward_roles_and_capabilities():
    p = PROFILES[AUTELIS_HAYWARD]
    assert p.supports_climate is False
    assert p.setpoint_param is None               # temp= is rejected with HTTP 500
    # names.xml 404s, but the owner's labels DO exist -- on the Setup page.
    assert p.names_endpoint == "settings.htm"
    assert p.names_format == "html"
    assert p.role("poolht") == ROLE_READONLY      # accepts writes, ignores them
    assert p.role("waterfall") == ROLE_READONLY
    assert p.role("aux5") == ROLE_CIRCUIT         # interlocked, NOT read-only
    assert p.role("schlor") == ROLE_CIRCUIT
    assert p.role("valve3") == ROLE_CIRCUIT
    assert p.solar_temp_tag == "solartemp"


def test_pentair_capabilities():
    p = PROFILES[AUTELIS_PENTAIR]
    assert p.heat_section == "temp"               # NOT equipment, unlike Jandy
    assert p.heat_param == "hval"                 # NOT value=
    assert p.heat_max_mode == 3                   # 3 = solar-only; Jandy tops out at 2
    assert p.solar_temp_tag == "soltemp"          # NOT solartemp
    assert p.role("circuit1") == ROLE_CIRCUIT
    assert p.role("feature10") == ROLE_CIRCUIT


def test_jandy_and_hayward_heat_live_in_equipment():
    assert PROFILES[AUTELIS_JANDY].heat_section == "equipment"
    assert PROFILES[AUTELIS_JANDY].heat_param == "value"
    assert PROFILES[AUTELIS_JANDY].heat_max_mode == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_brands.py -v`
Expected: FAIL — `ModuleNotFoundError: custom_components.autelis_pool.brands`

- [ ] **Step 3: Add the new brand constants**

In `custom_components/autelis_pool/const.py`, replace the `CIRCUITS`, `HEAT_SET` and `TEMP_SENSORS` blocks (they move to `brands.py`) and add:

```python
# Which type of pool controller the Autelis unit is bridged to.
# Jandy/Pentair values match upstream's feature/pentair-support branch.
AUTELIS_JANDY = 0
AUTELIS_PENTAIR = 1
AUTELIS_HAYWARD = 2
AUTELIS_UNKNOWN = -1
```

Leave `DOMAIN`, `AUTELIS_USERNAME`, `PLATFORMS`, `STATE_AUTO`, `STATE_SERVICE`, `MIN_TEMP`, `MAX_TEMP` as they are, and add `Platform.BINARY_SENSOR` to `PLATFORMS`:

```python
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
]
```

- [ ] **Step 4: Write `brands.py`**

```python
"""Per-brand schema and capability profiles for Autelis pool controllers.

Autelis speaks a different XML dialect per controller family. This module is the
single place that knows the differences.

Two ideas keep it honest:

* The profile declares what a tag *is* (its role). Discovery decides whether that
  equipment is *installed*. A tag no profile knows is ignored, never guessed at —
  guessing produces switches that silently do nothing.
* Brand detection requires a positive marker. There is no fall-through default,
  because a disconnected controller emits sparse XML and would be misdetected,
  then persist a wrong entity set into the registry.

See docs/superpowers/specs/2026-07-14-hayward-support-design.md for the evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, NamedTuple
from xml.etree.ElementTree import Element

from .const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
    AUTELIS_UNKNOWN,
)

ROLE_CIRCUIT = "circuit"          # controllable on/off -> switch
ROLE_READONLY = "readonly"        # reports state, refuses writes -> binary_sensor
ROLE_HEAT = "heat"                # owned by the climate entity
ROLE_SETPOINT = "setpoint"        # owned by the climate entity
ROLE_TEMPERATURE = "temperature"  # -> sensor
ROLE_IGNORE = "ignore"            # deliberately not exposed


class HeatSet(NamedTuple):
    """One climate entity: a current temp, a setpoint, and a heat-mode tag."""

    name: str
    current_tag: str
    setpoint_tag: str
    heat_tag: str


@dataclass(frozen=True)
class BrandProfile:
    """Everything that differs between controller families."""

    brand: int
    key: str
    names_endpoint: str | None   # where the owner's labels live
    names_format: str | None     # "xml" (names.xml) or "html" (Hayward's settings.htm)
    setpoint_param: str | None   # "temp", or None where setpoints don't exist
    heat_section: str | None     # which status.xml section holds poolht/spaht
    heat_param: str | None       # "value" (Jandy) or "hval" (Pentair)
    heat_max_mode: int           # highest valid heat mode value
    solar_temp_tag: str | None
    supports_climate: bool
    roles: Mapping[str, str]
    heat_sets: tuple[HeatSet, ...] = ()
    default_names: Mapping[str, str] = field(default_factory=dict)

    def role(self, tag: str) -> str:
        """Role of a tag. Unknown tags are ignored, never guessed at."""
        return self.roles.get(tag, ROLE_IGNORE)


def _roles(**groups: tuple[str, ...]) -> dict[str, str]:
    """Build a tag -> role map from role -> tags groups."""
    return {tag: role for role, tags in groups.items() for tag in tags}


# These reproduce the entity names upstream's TEMP_SENSORS dict produced ("Pool
# Temperature", not "pooltemp"). Without them the refactor would silently rename
# every existing user's temperature sensors.
_TEMP_NAMES = {
    "pooltemp": "Pool Temperature",
    "spatemp": "Spa Temperature",
    "airtemp": "Air Temperature",
    "solartemp": "Solar Temperature",
    "soltemp": "Solar Temperature",   # Pentair spells it differently
}

_JANDY_AUX = tuple(f"aux{n}" for n in range(1, 24))   # docs say 15; real RS16 emits 23
_JANDY_MACRO = tuple(f"macro{n}" for n in range(1, 7))

JANDY = BrandProfile(
    brand=AUTELIS_JANDY,
    key="jandy",
    names_endpoint="names.xml",
    names_format="xml",
    setpoint_param="temp",
    heat_section="equipment",
    heat_param="value",
    heat_max_mode=2,          # 0=Off 1=Enabled 2=On
    solar_temp_tag="solartemp",
    supports_climate=True,
    roles=_roles(
        circuit=("pump", "spa", "waterfall", "cleaner", "solarht", *_JANDY_AUX),
        heat=("poolht", "poolht2", "spaht"),
        setpoint=("poolsp", "poolsp2", "spasp"),
        temperature=("pooltemp", "spatemp", "airtemp", "solartemp"),
        # pumplo/htpmp/auxx: undocumented, always empty in every capture.
        # macroN: status.xml exposes them, but no doc or capture proves what name
        # set.cgi accepts (the wiki only ever documents "1tch3"). Exposing them
        # would ship switches that silently do nothing.
        ignore=("pumplo", "htpmp", "auxx", "tempunits", *_JANDY_MACRO),
    ),
    heat_sets=(
        HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"),
        HeatSet("Spa Heat", "spatemp", "spasp", "spaht"),
    ),
    # Preserves the exact entity names upstream's CIRCUITS and TEMP_SENSORS produced.
    # The aux fallbacks are only reached when names.xml is absent (older firmware);
    # a real Jandy names.xml always wins.
    default_names={
        **_TEMP_NAMES,
        "pump": "Pool",
        "spa": "Spa",
        "solarht": "Solar Heating",
        "cleaner": "Cleaner",
        "waterfall": "Waterfall",
        **{f"aux{n}": f"Aux {n}" for n in range(1, 24)},
    },
)

_PENTAIR_CIRCUITS = tuple(f"circuit{n}" for n in range(1, 21))
_PENTAIR_FEATURES = tuple(f"feature{n}" for n in range(1, 11))

PENTAIR = BrandProfile(
    brand=AUTELIS_PENTAIR,
    key="pentair",
    names_endpoint="names.xml",
    names_format="xml",
    setpoint_param="temp",
    heat_section="temp",      # NOT equipment -- this is the Pentair trap
    heat_param="hval",        # NOT value=
    heat_max_mode=3,          # 3 = solar-only; upstream's 0/1/2 map KeyErrors here
    solar_temp_tag="soltemp",  # NOT solartemp
    supports_climate=True,
    roles=_roles(
        circuit=(*_PENTAIR_CIRCUITS, *_PENTAIR_FEATURES),
        heat=("poolht", "spaht"),
        setpoint=("poolsp", "spasp"),
        temperature=("pooltemp", "spatemp", "airtemp", "soltemp"),
        ignore=("htstatus", "htpump", "maxplsp", "tempunits"),
    ),
    heat_sets=(
        HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"),
        HeatSet("Spa Heat", "spatemp", "spasp", "spaht"),
    ),
    default_names=dict(_TEMP_NAMES),
)

_HAYWARD_AUX = tuple(f"aux{n}" for n in range(1, 16))

HAYWARD = BrandProfile(
    brand=AUTELIS_HAYWARD,
    key="hayward",
    # names.xml 404s, but the owner's aux labels are NOT unavailable -- they live on
    # the Autelis Setup page, editable and persisted on the unit, and the device
    # renders them into the HTML it serves. Rename an aux there and it flows into
    # Home Assistant, exactly as names.xml does for Jandy.
    names_endpoint="settings.htm",
    names_format="html",
    setpoint_param=None,      # any temp= param returns HTTP 500, even on a valid name
    heat_section=None,
    heat_param=None,
    heat_max_mode=0,
    solar_temp_tag="solartemp",
    supports_climate=False,   # no setpoint can be written OR read; see the spec
    roles=_roles(
        # aux5 is a normal circuit. It refused a write during testing only because
        # the pool was in a scheduled spa window and a cleaner cannot run with the
        # valves diverted. Interlocked != read-only.
        circuit=("pump", "spa", "valve3", "valve4", "schlor", *_HAYWARD_AUX),
        # Confirmed read-only by write-and-poll: poolht held 100 polls, waterfall 60.
        # poolht reports RUNNING, not ENABLED.
        readonly=("poolht", "waterfall"),
        temperature=("pooltemp", "spatemp", "airtemp", "solartemp"),
        ignore=("tempunits",),
    ),
    # FALLBACK ONLY. The real aux labels come from settings.htm (see names.py) --
    # they are the owner's, not ours. These are used solely when that scrape fails,
    # so a parse problem degrades to generic names instead of breaking setup.
    #
    # The fixed circuits below are genuinely static: they are the labels the Autelis
    # firmware prints for its own non-aux equipment, and the Setup page offers no way
    # to change them.
    default_names={
        **_TEMP_NAMES,
        "pump": "Filter Pump",
        "spa": "Spa",
        "waterfall": "Waterfall",
        "valve3": "Valve 3",
        "valve4": "Valve 4",
        "poolht": "Heater",
        "schlor": "SuperChlorinate",
        **{f"aux{n}": f"Aux {n}" for n in range(1, 16)},
    },
)

PROFILES: dict[int, BrandProfile] = {
    AUTELIS_JANDY: JANDY,
    AUTELIS_PENTAIR: PENTAIR,
    AUTELIS_HAYWARD: HAYWARD,
}


def _tags(root: Element, section: str) -> set[str]:
    node = root.find(section)
    return set() if node is None else {child.tag for child in node}


def detect_brand(root: Element) -> int:
    """Identify the controller family from the shape of status.xml.

    Never branch on <model>: it is the *pool controller's* model, not the Autelis
    unit's. Pentair documents an enum 0-5 yet real EasyTouch units report 13; Jandy
    reports 4-digit strings (6520, 6525); a disconnected Jandy reports 0.

    Returns AUTELIS_UNKNOWN when no positive marker is found. Callers must treat
    that as "not ready", never as a default brand.
    """
    equipment = _tags(root, "equipment")

    if "circuit1" in equipment:
        return AUTELIS_PENTAIR
    if equipment & {"valve3", "schlor"}:
        return AUTELIS_HAYWARD
    if "cleaner" in equipment:
        return AUTELIS_JANDY

    system = _tags(root, "system")
    if system & {"dip", "vbat", "lowbat"}:
        return AUTELIS_JANDY
    if system & {"haddr", "systime"}:
        return AUTELIS_PENTAIR

    return AUTELIS_UNKNOWN
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_brands.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add custom_components/autelis_pool/brands.py custom_components/autelis_pool/const.py tests/test_brands.py
git commit -m "feat: add per-brand schema profiles and structural brand detection

Detection uses positive markers only; an unidentified controller returns
AUTELIS_UNKNOWN rather than defaulting to Jandy, because a disconnected unit
emits sparse XML that would otherwise be misdetected and persisted.

Never branches on <model>: it is the pool controller's model, not the Autelis
unit's, and reads 0 while disconnected."
```

---

### Task 2b: Label sources (`names.py`)

Where each brand keeps the owner's own names for their equipment.

**Files:**
- Create: `custom_components/autelis_pool/names.py`
- Create: `tests/fixtures/hayward_1011_settings.htm`
- Test: `tests/test_names.py`

**Interfaces:**
- Produces: `parse_names_xml(root) -> dict[str, str]`, `parse_aux_labels_html(html) -> dict[str, str]`, `is_placeholder(label) -> bool`.

- [ ] **Step 1: Capture the Hayward settings fixture**

`tests/fixtures/hayward_1011_settings.htm` — the relevant fragment of the real page (the full
page also contains password fields; only the labels matter, and committing the fragment keeps
the fixture readable):

```html
<form method="post" action="javascript:doSubmit();" name="settings">
<div><label>Model:</label>
<select id="model">
<div>&nbsp;&nbsp;AUX Labels</div>
<div><label>AUX1:</label>
<input maxlength=15 type="text" id="aux1label" value="Pool Lights"/></div>
<div><label>AUX2:</label>
<input maxlength=15 type="text" id="aux2label" value="Spa Lights" /></div>
<div><label>AUX3:</label>
<input maxlength=15 type="text" id="aux3label" value="Blower" /></div>
<div><label>AUX4:</label>
<input maxlength=15 type="text" id="aux4label" value="Waterfall" /></div>
<div><label>AUX5:</label>
<input maxlength=15 type="text" id="aux5label" value="Cleaner" /></div>
<div><label>AUX6:</label>
<input maxlength=15 type="text" id="aux6label" value="AUX5" /></div>
<div><label>AUX7:</label>
<input maxlength=15 type="text" id="aux7label" value="AUX6" /></div>
<div><label>AUX8:</label>
<input maxlength=15 type="text" id="aux8label" value="AUX7" /></div>
<div><label>AUX9:</label>
<input maxlength=15 type="text" id="aux9label" value="AUX8" /></div>
<div><label>AUX10:</label>
<input maxlength=15 type="text" id="aux10label" value="AUX9" /></div>
<div><label>AUX11:</label>
<input maxlength=15 type="text" id="aux11label" value="AUX10" /></div>
<div><label>AUX12:</label>
<input maxlength=15 type="text" id="aux12label" value="AUX11" /></div>
<div><label>AUX13:</label>
<input maxlength=15 type="text" id="aux13label" value="AUX12" /></div>
<div><label>AUX14:</label>
<input maxlength=15 type="text" id="aux14label" value="AUX13" /></div>
<div><label>AUX15:</label>
<input maxlength=15 type="text" id="aux15label" value="AUX14" /></div><br></br>
<div><input type="submit" class="sm" value="Save Changes" /></div>
</form>
```

- [ ] **Step 2: Write the failing tests**

`tests/test_names.py`:

```python
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
```

- [ ] **Step 3: Run to verify it fails**

Run: `python -m pytest tests/test_names.py -v`
Expected: FAIL — `ModuleNotFoundError: ...names`

- [ ] **Step 4: Write `names.py`**

```python
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

# An unassigned relay keeps a placeholder label: "AUX5" (Hayward), "AUX9" (Jandy),
# "AUX 2" (Pentair). The relay is real, the owner just has not wired it to anything.
_PLACEHOLDER = re.compile(r"^aux\s*\d+$", re.IGNORECASE)


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
```

- [ ] **Step 5: Run the tests**

Run: `python -m pytest tests/test_names.py -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add custom_components/autelis_pool/names.py tests/test_names.py tests/fixtures/hayward_1011_settings.htm
git commit -m "feat: read the owner's equipment labels on every brand

Jandy and Pentair serve names.xml. Hayward 404s it -- but its labels are not
unavailable: the Autelis Setup page has an editable AUX Labels form, persisted on the
unit and rendered into the HTML the device serves. An earlier draft mistook those
rendered values for firmware constants; they are the owner's own names.

Renaming an aux in the Autelis UI now flows into Home Assistant on Hayward exactly as
it already does on Jandy. A scrape failure degrades to default labels, never raises."
```

---

### Task 3: Presence-discovery (`discovery.py`)

**Files:**
- Create: `custom_components/autelis_pool/discovery.py`
- Test: `tests/test_discovery.py`

**Interfaces:**
- Consumes: `BrandProfile`, roles, `HeatSet` from Task 2.
- Produces:
  - `EntityDescriptor(platform: str, tag: str, name: str)`
  - `build_inventory(root, profile, names) -> list[EntityDescriptor]`
  - `build_heat_sets(root, profile) -> list[HeatSet]`
  - `snapshot(root, profile) -> dict[str, dict[str, str]]` with keys `"equipment"`, `"temp"`, `"system"`

- [ ] **Step 1: Write the failing tests**

`tests/test_discovery.py`:

```python
from custom_components.autelis_pool.brands import PROFILES
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
)
from custom_components.autelis_pool.discovery import (
    build_heat_sets,
    build_inventory,
    snapshot,
)
from custom_components.autelis_pool.names import parse_aux_labels_html, parse_names_xml
from tests.conftest import load_fixture, load_xml


def _inv(status, brand, names_file=None, settings_file=None):
    names = {}
    if names_file:
        names = parse_names_xml(load_xml(names_file))
    if settings_file:
        names = parse_aux_labels_html(load_fixture(settings_file))
    return build_inventory(load_xml(status), PROFILES[brand], names)


def _tags(inventory, platform):
    return sorted(d.tag for d in inventory if d.platform == platform)


def test_jandy_empty_aux1_produces_no_entity():
    """aux1 is blank in status.xml even though names.xml labels it 'Cleaner'.

    The circuit's state lives in <cleaner>. Building from names.xml is what
    produced the phantom switch in upstream issue #3.
    """
    inv = _inv("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml")
    switches = _tags(inv, "switch")
    assert "aux1" not in switches
    assert "cleaner" in switches


def test_jandy_phantom_is_name_independent():
    """The upstream fix keys off the literal name 'Cleaner'. Ours must not."""
    names = {"aux1": "Polaris", "aux2": "Waterfall"}
    inv = build_inventory(
        load_xml("jandy_169_status.xml"), PROFILES[AUTELIS_JANDY], names
    )
    assert "aux1" not in _tags(inv, "switch")


def test_jandy_absent_equipment_is_skipped():
    inv = _inv("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml")
    switches = _tags(inv, "switch")
    for absent in ("pumplo", "waterfall", "aux8", "aux23"):
        assert absent not in switches


def test_jandy_macros_are_never_switches():
    """macroN is non-empty in 1.6.17, but no one has verified its set.cgi name."""
    inv = _inv("jandy_1617_status.xml", AUTELIS_JANDY)
    switches = _tags(inv, "switch")
    assert not [t for t in switches if t.startswith("macro")]
    assert "htpmp" not in switches
    assert "auxx" not in switches


def test_hayward_readonly_equipment_becomes_binary_sensor():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert _tags(inv, "binary_sensor") == ["poolht", "waterfall"]
    assert "poolht" not in _tags(inv, "switch")


def test_hayward_aux5_is_a_switch():
    """Interlocked during testing, not read-only. See the spec."""
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert "aux5" in _tags(inv, "switch")


def test_hayward_has_no_climate():
    root = load_xml("hayward_1011_status.xml")
    assert build_heat_sets(root, PROFILES[AUTELIS_HAYWARD]) == []


def test_hayward_empty_solartemp_produces_no_sensor():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    assert _tags(inv, "sensor") == ["airtemp", "pooltemp", "spatemp"]


def test_hayward_uses_the_owners_labels_from_the_setup_page():
    """Hayward has no names.xml, but the owner's labels live on the Setup page."""
    inv = _inv(
        "hayward_1011_status.xml",
        AUTELIS_HAYWARD,
        settings_file="hayward_1011_settings.htm",
    )
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["aux1"] == "Pool Lights"
    assert by_tag["aux5"] == "Cleaner"
    assert by_tag["schlor"] == "SuperChlorinate"   # fixed circuit, not an aux


def test_hayward_degrades_to_defaults_if_the_scrape_fails():
    inv = _inv("hayward_1011_status.xml", AUTELIS_HAYWARD)
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["aux1"] == "Aux 1"
    assert by_tag["pump"] == "Filter Pump"


def test_unassigned_relays_are_created_but_disabled():
    """aux6/aux7 are real relays -- the panel has the buttons -- but unassigned.

    Not hidden (someone else may use theirs) and not enabled (this owner does not).
    """
    inv = _inv(
        "hayward_1011_status.xml",
        AUTELIS_HAYWARD,
        settings_file="hayward_1011_settings.htm",
    )
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}

    assert enabled["aux6"] is False   # label is still the placeholder "AUX5"
    assert enabled["aux7"] is False
    assert enabled["aux1"] is True    # "Pool Lights"
    assert enabled["aux5"] is True    # "Cleaner"
    assert enabled["pump"] is True


def test_our_own_fallback_names_do_not_count_as_placeholders():
    """A tag with no DEVICE label tells us nothing -- status.xml says it exists."""
    inv = _inv("jandy_1617_status.xml", AUTELIS_JANDY)   # no names.xml for this unit
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}
    assert enabled["aux1"] is True


def test_pentair_unassigned_circuits_are_disabled():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    enabled = {d.tag: d.enabled_default for d in inv if d.platform == "switch"}
    assert enabled["circuit3"] is False   # "AUX 2" -- a placeholder, with a space
    assert enabled["circuit1"] is True    # "SPA"
    assert enabled["circuit20"] is True   # "AUX EXTRA" -- named, just oddly


def test_pentair_heat_is_found_under_temp():
    heat = build_heat_sets(load_xml("pentair_1611_status.xml"), PROFILES[AUTELIS_PENTAIR])
    assert [h.name for h in heat] == ["Pool Heat", "Spa Heat"]


def test_pentair_uses_soltemp_not_solartemp():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    # soltemp is empty in the capture, so no solar sensor at all.
    assert _tags(inv, "sensor") == ["airtemp", "pooltemp", "spatemp"]


def test_pentair_circuits_and_features_are_switches():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    switches = _tags(inv, "switch")
    assert "circuit1" in switches
    assert "feature8" in switches
    assert "circuit10" not in switches   # empty => not installed
    assert "htstatus" not in switches    # ignored role


def test_names_xml_only_labels_it_does_not_create():
    inv = _inv("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml")
    by_tag = {d.tag: d.name for d in inv}
    assert by_tag["circuit1"] == "SPA"
    assert by_tag["circuit6"] == "POOL"


def test_snapshot_drops_absent_keys():
    """A tag that empties must vanish from the snapshot, not keep its old value."""
    snap = snapshot(load_xml("hayward_1011_status.xml"), PROFILES[AUTELIS_HAYWARD])
    assert "aux8" not in snap["equipment"]
    assert snap["equipment"]["aux5"] == "1"
    assert "solartemp" not in snap["temp"]
    assert snap["temp"]["tempunits"] == "F"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError: ...discovery`

- [ ] **Step 3: Write `discovery.py`**

```python
"""Presence-discovery: which equipment does this controller actually have?

The brand profile says what a tag *is*. This module says whether it *exists*, by
reading status.xml exactly the way the Autelis firmware's own web UI does: a tag
with an empty value is equipment that is not installed.

names.xml is a LABEL SIDE-TABLE. It never creates an entity. On Jandy, a cleaner
assigned to AUX1 leaves <aux1> empty and routes state through <cleaner>, while
names.xml still calls aux1 "Cleaner" -- so building entities from names.xml keys
produces phantom switches backed by nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.etree.ElementTree import Element

from .brands import (
    ROLE_CIRCUIT,
    ROLE_READONLY,
    ROLE_TEMPERATURE,
    BrandProfile,
    HeatSet,
)
from .names import is_placeholder

_SECTIONS = ("system", "equipment", "temp")


@dataclass(frozen=True)
class EntityDescriptor:
    """One entity to create."""

    platform: str   # "switch" | "sensor" | "binary_sensor"
    tag: str
    name: str
    enabled_default: bool = True


def _present(node: Element | None) -> bool:
    """True when the tag exists AND carries a value. Empty => not installed."""
    return node is not None and node.text is not None and node.text.strip() != ""


def snapshot(root: Element, profile: BrandProfile) -> dict[str, dict[str, str]]:
    """Build a fresh state snapshot. Absent tags are absent -- never stale.

    The previous implementation updated dicts in place and never cleared them, so a
    tag that went empty kept its old value and absent equipment still looked
    installed. Discovery reads presence from here, so that had to go.

    Note `is not None` rather than a truth test: an Element with no children is falsy
    today, but Python deprecated that and will make Elements always truthy. `find(x)
    or []` therefore works by accident and is scheduled to break.
    """
    snap: dict[str, dict[str, str]] = {}
    for section in _SECTIONS:
        node = root.find(section)
        snap[section] = (
            {}
            if node is None
            else {
                child.tag: child.text.strip()
                for child in node
                if child.text is not None and child.text.strip() != ""
            }
        )
    return snap


def _label(tag: str, profile: BrandProfile, names: dict[str, str]) -> tuple[str, bool]:
    """Return (name, enabled_default) for a tag.

    A relay can be installed but unassigned -- the owner never wired it to anything --
    in which case the device still hands back a placeholder label ("AUX5", "AUX 2").
    Pools differ wildly: one owner uses no aux at all, another uses every one. So we
    neither hide these nor clutter everyone's dashboard with them. They are created
    DISABLED, one click from being switched on.

    An important asymmetry: only a placeholder that came FROM THE DEVICE means
    "unassigned". Our own fallback names are not evidence of anything, so a tag with no
    device label stays enabled -- status.xml says the equipment is installed, and that
    is all we know.
    """
    if tag in names:
        label = names[tag]
        return label, not is_placeholder(label)
    return profile.default_names.get(tag, tag), True


def build_inventory(
    root: Element, profile: BrandProfile, names: dict[str, str]
) -> list[EntityDescriptor]:
    """Every entity this controller should expose, from what it actually reports."""
    inventory: list[EntityDescriptor] = []

    equipment = root.find("equipment")
    if equipment is not None:
        for child in equipment:
            if not _present(child):
                continue                      # not installed
            role = profile.role(child.tag)
            if role == ROLE_CIRCUIT:
                platform = "switch"
            elif role == ROLE_READONLY:
                platform = "binary_sensor"
            else:
                continue                      # heat/setpoint are climate's; ignore the rest
            name, enabled = _label(child.tag, profile, names)
            inventory.append(EntityDescriptor(platform, child.tag, name, enabled))

    temp = root.find("temp")
    if temp is not None:
        for child in temp:
            if not _present(child):
                continue
            if profile.role(child.tag) != ROLE_TEMPERATURE:
                continue                      # setpoints belong to climate
            name, _ = _label(child.tag, profile, names)
            inventory.append(EntityDescriptor("sensor", child.tag, name))

    return inventory


def build_heat_sets(root: Element, profile: BrandProfile) -> list[HeatSet]:
    """Climate entities, only where the brand and the hardware both support them."""
    if not profile.supports_climate or profile.heat_section is None:
        return []

    heat_node = root.find(profile.heat_section)
    temp_node = root.find("temp")
    if heat_node is None or temp_node is None:
        return []

    return [
        hs
        for hs in profile.heat_sets
        if _present(heat_node.find(hs.heat_tag))
        and _present(temp_node.find(hs.setpoint_tag))
        and _present(temp_node.find(hs.current_tag))
    ]
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_discovery.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/discovery.py tests/test_discovery.py
git commit -m "feat: add presence-discovery driven by status.xml

Entities derive from status.xml state tags; names.xml is only a label side-table.
An empty tag means the equipment is not installed, which is how the Autelis
firmware's own web UI decides what to render.

Snapshots rebuild from scratch each poll, so a tag that empties disappears rather
than keeping a stale value and looking installed."
```

---

### Task 4: Brand-aware API commands (`api.py`)

**Files:**
- Modify: `custom_components/autelis_pool/api.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `BrandProfile` (Task 2).
- Produces:
  - `CommandNotSupported` (exception)
  - module-level `build_command(profile, kind, tag, value) -> str` — pure, so the wire format is testable without HTTP, which matters because we cannot exercise Jandy or Pentair hardware
  - `AutelisPoolAPI.get(endpoint, optional=False)`, `.get_text(endpoint, optional=False)`, `.send(profile, kind, tag, value)`
- Removes: the old `get_status()`, `get_names()` and `control()` helpers.

- [ ] **Step 1: Write the failing tests**

`tests/test_api.py`:

```python
import pytest

from custom_components.autelis_pool.api import CommandNotSupported, build_command
from custom_components.autelis_pool.brands import HAYWARD, JANDY, PENTAIR


def test_circuit_command_is_the_same_on_every_brand():
    assert build_command(JANDY, "circuit", "pump", 1) == "set.cgi?name=pump&value=1"
    assert build_command(HAYWARD, "circuit", "aux5", 0) == "set.cgi?name=aux5&value=0"
    assert build_command(PENTAIR, "circuit", "circuit1", 1) == "set.cgi?name=circuit1&value=1"


def test_jandy_setpoint_uses_temp_param():
    assert build_command(JANDY, "setpoint", "poolsp", 90) == "set.cgi?name=poolsp&temp=90"


def test_hayward_setpoint_is_refused_not_sent():
    """Hayward rejects ANY temp= param with HTTP 500 -- even on a valid name.

    Sending one is not merely useless, it is an error we already know the answer to.
    """
    with pytest.raises(CommandNotSupported):
        build_command(HAYWARD, "setpoint", "poolsp", 90)


def test_hayward_heat_is_refused():
    with pytest.raises(CommandNotSupported):
        build_command(HAYWARD, "heat", "poolht", 1)


def test_jandy_heat_uses_value_param():
    assert build_command(JANDY, "heat", "poolht", 1) == "set.cgi?name=poolht&value=1"


def test_pentair_heat_uses_hval_param():
    assert build_command(PENTAIR, "heat", "poolht", 3) == "set.cgi?name=poolht&hval=3"


def test_no_command_ever_sends_temp_to_hayward():
    """The one bug that would break a real user's controller with a 500."""
    for kind, tag, value in (("circuit", "pump", 1), ("circuit", "schlor", 0)):
        assert "temp=" not in build_command(HAYWARD, kind, tag, value)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_command'`

- [ ] **Step 3: Add command construction to `api.py`**

Add near the top of `custom_components/autelis_pool/api.py`:

```python
from .brands import BrandProfile


class CommandNotSupported(Exception):
    """The brand has no wire format for this command (e.g. Hayward setpoints)."""


def build_command(profile: BrandProfile, kind: str, tag: str, value) -> str:
    """Build a set.cgi query for one command, in this brand's dialect.

    Pure and synchronous so the wire format can be tested without HTTP -- which
    matters, because we cannot exercise Jandy or Pentair hardware.

    Note that a `1` response from set.cgi means the NAME was recognised, not that
    the write took effect. Callers must re-read status.xml; never infer state here.
    """
    if kind == "circuit":
        return f"set.cgi?name={tag}&value={value}"

    if kind == "setpoint":
        if profile.setpoint_param is None:
            raise CommandNotSupported(
                f"{profile.key} has no setpoints; a temp= param returns HTTP 500"
            )
        return f"set.cgi?name={tag}&{profile.setpoint_param}={value}"

    if kind == "heat":
        if profile.heat_param is None:
            raise CommandNotSupported(f"{profile.key} cannot set heat mode via set.cgi")
        return f"set.cgi?name={tag}&{profile.heat_param}={value}"

    raise CommandNotSupported(f"unknown command kind: {kind}")
```

Then replace the body of `AutelisPoolAPI.control()` so it routes through `build_command`, and make `get()` distinguish a 404 (an optional endpoint that simply isn't there) from a real failure:

```python
    async def get(self, endpoint, optional: bool = False):
        """GET an endpoint and return parsed XML, or None.

        `optional=True` means a 404 is an expected answer, not an error: names.xml,
        chem.xml, pumps.xml and lights.xml are later firmware additions and are
        absent on Hayward and on older Jandy units.
        """
        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        url = self.api_url + endpoint
        try:
            response = await self.session.get(url, **kwargs)
            if optional and response.status == 404:
                return None
            response.raise_for_status()

            self.available = True
            self.error_logged = False
            return ElementTree.fromstring(await response.text())
        except Exception as conn_exc:  # pylint: disable=broad-except
            if not self.error_logged:
                _LOGGER.error(
                    "Failed to get Autelis status from %s: %s", endpoint, conn_exc
                )
            self.error_logged = True
            self.available = False
            return None

    async def get_text(self, endpoint, optional: bool = False):
        """GET an endpoint as raw text. Hayward keeps its aux labels in HTML, not XML."""
        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        try:
            response = await self.session.get(self.api_url + endpoint, **kwargs)
            if optional and response.status == 404:
                return None
            response.raise_for_status()
            return await response.text()
        except Exception as conn_exc:  # pylint: disable=broad-except
            # Labels are a nicety; never let them break setup.
            _LOGGER.debug("Could not fetch %s: %s", endpoint, conn_exc)
            return None

    async def send(self, profile, kind, tag, value):
        """Send one command. Returns True only if the device accepted the NAME.

        It does NOT mean the write took effect -- Hayward returns 1 for read-only
        equipment, and any panel may refuse a circuit for interlock reasons. State
        must come from the next status.xml poll.
        """
        endpoint = build_command(profile, kind, tag, value)

        kwargs = {}
        if self.password is not None:
            kwargs = {"auth": BasicAuth(AUTELIS_USERNAME, password=self.password)}

        try:
            response = await self.session.get(self.api_url + endpoint, **kwargs)
            response.raise_for_status()
            self.available = True
            self.error_logged = False
        except Exception as conn_exc:  # pylint: disable=broad-except
            if not self.error_logged:
                _LOGGER.error("Failed to send Autelis command %s: %s", endpoint, conn_exc)
            self.error_logged = True
            self.available = False
            return False

        return (await response.text()).strip() == "1"
```

Delete the old `get_status()` and `get_names()` helpers; `__init__.py` now calls `get("status.xml")` and `get("names.xml", optional=True)` directly.

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_api.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/api.py tests/test_api.py
git commit -m "feat: brand-aware set.cgi command construction

Hayward rejects any temp= parameter with HTTP 500 -- even on a valid name -- so
setpoint and heat commands raise CommandNotSupported there rather than being sent.
Pentair heat uses hval=, Jandy uses value=.

get() now treats a 404 on optional endpoints (names.xml et al) as an expected
answer, since they are later firmware additions absent on Hayward and older Jandy."
```

---

### Task 5: Wire it up in `__init__.py`

**Files:**
- Modify: `custom_components/autelis_pool/__init__.py`
- Test: `tests/test_init.py`

**Interfaces:**
- Produces: `AutelisData` with `.profile`, `.inventory`, `.heat_sets`, `.equipment`, `.sensors`, `.mode`, `.host`, `.api`; stored at `hass.data[DOMAIN][entry.entry_id]`.

- [ ] **Step 1: Write the failing test**

`tests/test_init.py`:

```python
from xml.etree import ElementTree

import pytest

from custom_components.autelis_pool import AutelisData
from custom_components.autelis_pool.const import AUTELIS_HAYWARD, AUTELIS_UNKNOWN
from tests.conftest import load_xml


class _FakeAPI:
    """Stands in for AutelisPoolAPI, which needs a real hass to build a session."""

    def __init__(self, status, names=None):
        self._status, self._names = status, names
        self.available = True

    async def get(self, endpoint, optional=False):
        return self._status if endpoint == "status.xml" else self._names

    async def get_text(self, endpoint, optional=False):
        # Hayward loads its labels from HTML, so _async_load_names() calls this.
        return self._names


async def test_refresh_detects_brand_and_builds_inventory():
    data = AutelisData("1.2.3.4", _FakeAPI(load_xml("hayward_1011_status.xml")))

    await data.async_refresh()

    assert data.profile.brand == AUTELIS_HAYWARD
    assert data.heat_sets == []
    assert data.equipment["aux5"] == "1"
    assert "aux8" not in data.equipment       # absent equipment stays absent


async def test_snapshot_drops_keys_that_go_empty():
    """The old code never cleared its dicts, so absent equipment looked installed."""
    data = AutelisData("1.2.3.4", _FakeAPI(load_xml("hayward_1011_status.xml")))
    await data.async_refresh()
    assert data.equipment["aux5"] == "1"

    emptied = load_xml("hayward_1011_status.xml")
    emptied.find("equipment").find("aux5").text = ""
    data.api = _FakeAPI(emptied)
    await data.async_refresh()

    assert "aux5" not in data.equipment


async def test_unknown_brand_refuses_to_guess():
    data = AutelisData("1.2.3.4", _FakeAPI(ElementTree.fromstring("<response></response>")))

    await data.async_refresh()

    assert data.brand == AUTELIS_UNKNOWN
    assert data.profile is None
    assert data.inventory == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_init.py -v`
Expected: FAIL — `AutelisData` has no `async_refresh` / `profile`.

- [ ] **Step 3: Rewrite `__init__.py`**

```python
"""Autelis pool controller integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util import Throttle

from .api import AutelisPoolAPI
from .brands import PROFILES, detect_brand
from .const import AUTELIS_UNKNOWN, DOMAIN, PLATFORMS, STATE_AUTO, STATE_SERVICE
from .discovery import build_heat_sets, build_inventory, snapshot
from .names import parse_aux_labels_html, parse_names_xml

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


async def async_setup_entry(hass, entry):
    """Set up one Autelis controller."""
    host = entry.data[CONF_HOST]
    password = entry.data[CONF_PASSWORD]
    # The API is injected rather than built inside AutelisData, so the polling and
    # discovery logic can be tested without a running Home Assistant.
    data = AutelisData(host, AutelisPoolAPI(hass, f"http://{host}/", password))

    await data.async_refresh()

    if data.brand == AUTELIS_UNKNOWN:
        # Sparse or unreachable XML. Guessing a brand here would build a wrong
        # entity set and persist it into the registry, so refuse and retry later.
        raise ConfigEntryNotReady(
            f"Could not identify the pool controller at {data.host}. "
            "It may be disconnected or still starting up."
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    """Unload one controller, leaving any others alone."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


class AutelisData:
    """Polls one controller and holds its latest snapshot."""

    def __init__(self, host, api):
        self.host = host
        self.api = api

        self.brand = AUTELIS_UNKNOWN
        self.profile = None
        self.names: dict[str, str] = {}
        self.inventory = []
        self.heat_sets = []
        self.equipment: dict[str, str] = {}
        self.sensors: dict[str, str] = {}
        self.system: dict[str, str] = {}
        self.mode = STATE_SERVICE

    async def async_refresh(self):
        """Poll status.xml and rebuild the snapshot from scratch."""
        status = await self.api.get("status.xml")
        if status is None:
            return

        if self.profile is None:
            # Brand and inventory are resolved ONCE, at setup. Re-running discovery
            # every poll would let a transient sparse response churn the entity
            # registry.
            self.brand = detect_brand(status)
            if self.brand == AUTELIS_UNKNOWN:
                return
            self.profile = PROFILES[self.brand]
            self.names = await self._async_load_names()
            self.inventory = build_inventory(status, self.profile, self.names)
            self.heat_sets = build_heat_sets(status, self.profile)
            _LOGGER.info(
                "Detected %s controller at %s: %d entities",
                self.profile.key,
                self.host,
                len(self.inventory),
            )

        snap = snapshot(status, self.profile)
        self.system, self.equipment, self.sensors = (
            snap["system"],
            snap["equipment"],
            snap["temp"],
        )

        opmode = self.system.get("opmode")
        self.mode = STATE_AUTO if opmode == "0" else STATE_SERVICE

    async def _async_load_names(self) -> dict[str, str]:
        """Fetch the owner's equipment labels, in whichever form this brand keeps them.

        Jandy and Pentair serve names.xml. Hayward 404s that, but keeps its aux labels
        on the Setup page -- editable, persisted on the unit, and rendered into the
        HTML it serves. Either way, these are the OWNER's names, not ours.

        Failure is never fatal: we fall back to generic labels.
        """
        endpoint = self.profile.names_endpoint
        if not endpoint:
            return {}

        if self.profile.names_format == "html":
            return parse_aux_labels_html(
                await self.api.get_text(endpoint, optional=True)
            )
        return parse_names_xml(await self.api.get(endpoint, optional=True))

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        """Throttled refresh, called by entities during their update."""
        await self.async_refresh()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_init.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/__init__.py tests/test_init.py
git commit -m "refactor: per-entry data, brand detection at setup, atomic snapshots

hass.data[DOMAIN] was a single global, so two controllers could not coexist --
untenable now that they can be different brands. Keyed by entry_id.

Brand and inventory resolve once at setup and are cached; re-running discovery on
every poll would let a transient sparse response churn the entity registry.

An unidentified controller raises ConfigEntryNotReady rather than defaulting to
Jandy and persisting a wrong entity set."
```

---

### Task 6: Switch platform

**Files:**
- Modify: `custom_components/autelis_pool/switch.py`
- Test: `tests/test_switch.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_switch.py`:

```python
import pytest

from custom_components.autelis_pool.switch import AutelisCircuit


class _Data:
    def __init__(self, equipment, profile=None):
        self.equipment = equipment
        self.profile = profile
        self.host = "1.2.3.4"
        self.mode = "auto"
        self.api = None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0", False),
        ("1", True),
        ("2", True),      # tri-state: solar heat "on"
        ("25", True),     # dimmer levels are ON -- upstream reads these as Off
        ("50", True),
        ("75", True),
        ("100", True),
    ],
)
def test_is_on_handles_dimmers_and_tristate(value, expected):
    switch = AutelisCircuit(_Data({"aux3": value}), "aux3", "Air Blower")
    assert switch.is_on is expected


def test_missing_equipment_reads_off_not_keyerror():
    """Equipment can vanish from a snapshot; that must not raise."""
    switch = AutelisCircuit(_Data({}), "aux3", "Air Blower")
    assert switch.is_on is False


def test_unique_id_matches_the_existing_scheme():
    """Changing this silently breaks every user's dashboard."""
    switch = AutelisCircuit(_Data({"pump": "1"}), "pump", "Pool")
    assert switch.unique_id == "autelis 1.2.3.4 pump"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_switch.py -v`
Expected: FAIL — dimmer cases return False.

- [ ] **Step 3: Rewrite `switch.py`**

```python
"""Autelis circuit switches."""

from homeassistant.components.switch import SwitchEntity

from .const import _LOGGER, DOMAIN, STATE_AUTO

# 0 = Off. 1 = On. 2 = On (tri-state heat: "enabled" vs "actively heating").
# 25/50/75/100 = a dimmer's level, which also means On -- upstream compares only
# against "1"/"2", so every dimmable Jandy aux currently reads as Off.
_OFF_VALUES = {"", "0"}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a switch for each controllable circuit discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisCircuit(data, item.tag, item.name, item.enabled_default)
            for item in data.inventory
            if item.platform == "switch"
        ],
        True,
    )


class AutelisCircuit(SwitchEntity):
    """One controllable circuit."""

    def __init__(self, data, equipment_name, friendly_name, enabled_default=True):
        self.data = data
        self.equipment_name = equipment_name
        self.friendly_name = friendly_name
        # An installed-but-unassigned relay ("AUX5") is registered and left disabled:
        # it clutters nothing for an owner who never wired it, and is one click away
        # for an owner who did.
        self._attr_entity_registry_enabled_default = enabled_default
        _LOGGER.debug("adding circuit %s (%s)", equipment_name, friendly_name)

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def name(self):
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.equipment_name}"

    @property
    def is_on(self):
        return self.data.equipment.get(self.equipment_name, "0") not in _OFF_VALUES

    async def async_turn_on(self, **kwargs):
        await self._set(1)

    async def async_turn_off(self, **kwargs):
        await self._set(0)

    async def _set(self, value):
        """Send the command, then let the next poll tell us what really happened.

        The panel can refuse a circuit for interlock reasons -- a cleaner will not
        start while the valves are diverted to the spa -- and set.cgi answers "1"
        regardless. So we do not assume the write landed.
        """
        await self.data.api.send(self.data.profile, "circuit", self.equipment_name, value)
        await self.data.async_refresh()

    async def async_update(self):
        await self.data.update()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_switch.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/switch.py tests/test_switch.py
git commit -m "fix: switches are discovery-driven and understand dimmer levels

is_on compared only against '1'/'2', so a Jandy dimmer aux reporting 25/50/75/100
read as Off. Anything that is not empty or '0' is now On.

Switches no longer assume a write landed: the panel can refuse a circuit for
interlock reasons while set.cgi still answers '1', so state comes from the
following poll."
```

---

### Task 7: Sensor platform (and two latent bugs)

**Files:**
- Modify: `custom_components/autelis_pool/sensor.py`
- Test: `tests/test_sensor.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_sensor.py`:

```python
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfTemperature

from custom_components.autelis_pool.sensor import AutelisTemperature


class _Data:
    def __init__(self, sensors):
        self.sensors = sensors
        self.host = "1.2.3.4"


def test_temperature_is_reported_verbatim_not_divided_by_ten():
    """<pooltemp>88</pooltemp> means 88 degrees. Upstream divides by 10."""
    sensor = AutelisTemperature(_Data({"pooltemp": "88", "tempunits": "F"}), "pooltemp", "Pool")
    assert sensor.native_value == 88


def test_device_class_is_actually_set():
    """Upstream does `self.type in (SensorDeviceClass.TEMPERATURE)` -- a SUBSTRING
    test against a string -- so no temperature sensor ever had a device class."""
    sensor = AutelisTemperature(_Data({"pooltemp": "88", "tempunits": "F"}), "pooltemp", "Pool")
    assert sensor.device_class == SensorDeviceClass.TEMPERATURE


def test_celsius_units_are_honoured():
    sensor = AutelisTemperature(_Data({"pooltemp": "30", "tempunits": "C"}), "pooltemp", "Pool")
    assert sensor.native_unit_of_measurement == UnitOfTemperature.CELSIUS


def test_missing_reading_is_none_not_a_crash():
    sensor = AutelisTemperature(_Data({"tempunits": "F"}), "solartemp", "Solar")
    assert sensor.native_value is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_sensor.py -v`
Expected: FAIL — `ImportError: cannot import name 'AutelisTemperature'`

- [ ] **Step 3: Rewrite `sensor.py`**

```python
"""Autelis temperature sensors."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature

from .const import _LOGGER, DOMAIN


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a sensor for each temperature reading discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisTemperature(data, item.tag, item.name)
            for item in data.inventory
            if item.platform == "sensor"
        ],
        True,
    )


class AutelisTemperature(SensorEntity):
    """One temperature reading."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, data, sensor_name, friendly_name):
        self.data = data
        self.sensor_name = sensor_name
        self.friendly_name = friendly_name
        _LOGGER.debug("adding sensor %s (%s)", sensor_name, friendly_name)

    @property
    def name(self):
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.sensor_name}"

    @property
    def native_unit_of_measurement(self):
        if self.data.sensors.get("tempunits") == "C":
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    @property
    def native_value(self):
        """The reading, verbatim.

        The old code divided by 10, which is wrong for this API -- <pooltemp>88</>
        means 88 degrees. It was dead code only because `self.type == "temperature"`
        never matched the capitalised "Temperature" it was given. Fixing the
        capitalisation without removing the division would have broken every reading.
        """
        raw = self.data.sensors.get(self.sensor_name)
        if raw is None or raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    async def async_update(self):
        await self.data.update()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_sensor.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/sensor.py tests/test_sensor.py
git commit -m "fix: temperature sensors get a device class and correct values

Two latent bugs that concealed each other:
- device_class did `self.type in (SensorDeviceClass.TEMPERATURE)`, a substring test
  against a string. 'Temperature' in 'temperature' is False, so NO temperature
  sensor ever had a device class.
- native_value divided the reading by 10, which is wrong for this API. It was dead
  code only because of the same capitalisation mismatch. Fixing either alone would
  have broken every temperature reading."
```

---

### Task 8: Climate platform

**Files:**
- Modify: `custom_components/autelis_pool/climate.py`
- Test: `tests/test_climate.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_climate.py`:

```python
import pytest
from homeassistant.components.climate import HVACAction, HVACMode

from custom_components.autelis_pool.brands import HeatSet, JANDY, PENTAIR
from custom_components.autelis_pool.climate import AutelisHeater, heat_mode_to_hvac


class _Data:
    def __init__(self, profile, equipment, sensors):
        self.profile = profile
        self.equipment = equipment
        self.sensors = sensors
        self.host = "1.2.3.4"
        self.mode = "auto"
        self.api = None


@pytest.mark.parametrize(
    ("value", "mode", "action"),
    [
        (0, HVACMode.OFF, HVACAction.OFF),
        (1, HVACMode.HEAT, HVACAction.IDLE),     # enabled, not firing
        (2, HVACMode.HEAT, HVACAction.HEATING),  # actively heating
        (3, HVACMode.HEAT, HVACAction.IDLE),     # Pentair: solar-only. Upstream KeyErrors.
    ],
)
def test_heat_mode_mapping_covers_pentairs_full_range(value, mode, action):
    assert heat_mode_to_hvac(value) == (mode, action)


def test_jandy_reads_heat_from_equipment():
    data = _Data(JANDY, {"poolht": "2"}, {"pooltemp": "86", "poolsp": "90", "tempunits": "F"})
    entity = AutelisHeater(data, HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"))
    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.hvac_action == HVACAction.HEATING
    assert entity.current_temperature == 86
    assert entity.target_temperature == 90


def test_pentair_reads_heat_from_temp_section():
    """Pentair puts poolht under <temp>. Reading <equipment> would KeyError."""
    data = _Data(PENTAIR, {}, {"poolht": "0", "pooltemp": "86", "poolsp": "68", "tempunits": "F"})
    entity = AutelisHeater(data, HeatSet("Pool Heat", "pooltemp", "poolsp", "poolht"))
    assert entity.hvac_mode == HVACMode.OFF
    assert entity.current_temperature == 86
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_climate.py -v`
Expected: FAIL — `ImportError: cannot import name 'heat_mode_to_hvac'`

- [ ] **Step 3: Rewrite `climate.py`**

```python
"""Autelis heaters, as Home Assistant climate entities.

Hayward has no climate entity: it exposes no setpoint to write OR read, so a
target temperature could never be shown. See the spec.
"""

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature

from .const import _LOGGER, DOMAIN, MAX_TEMP, MIN_TEMP, STATE_AUTO

# 0 = Off, 1 = Enabled (not firing), 2 = On (firing).
# 3 = solar-only, Pentair only. Upstream's map stops at 2 and KeyErrors on it.
_HEAT_MODES = {
    0: (HVACMode.OFF, HVACAction.OFF),
    1: (HVACMode.HEAT, HVACAction.IDLE),
    2: (HVACMode.HEAT, HVACAction.HEATING),
    3: (HVACMode.HEAT, HVACAction.IDLE),
}


def heat_mode_to_hvac(value: int):
    """Map an Autelis heat value to (HVACMode, HVACAction)."""
    return _HEAT_MODES.get(value, (HVACMode.OFF, HVACAction.OFF))


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a climate entity per heat set discovery found (none on Hayward)."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [AutelisHeater(data, heat_set) for heat_set in data.heat_sets], True
    )


class AutelisHeater(ClimateEntity):
    """One heater."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP

    def __init__(self, data, heat_set):
        self.data = data
        self.heat_set = heat_set
        _LOGGER.debug("adding heater %s", heat_set.name)

    @property
    def name(self):
        return self.heat_set.name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.heat_set.current_tag}"

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def temperature_unit(self):
        if self.data.sensors.get("tempunits") == "C":
            return UnitOfTemperature.CELSIUS
        return UnitOfTemperature.FAHRENHEIT

    def _heat_value(self) -> int:
        """Read the heat mode from wherever this brand keeps it.

        Jandy puts poolht/spaht in <equipment>; Pentair puts them in <temp>.
        """
        section = (
            self.data.equipment
            if self.data.profile.heat_section == "equipment"
            else self.data.sensors
        )
        try:
            return int(section.get(self.heat_set.heat_tag, 0))
        except (TypeError, ValueError):
            return 0

    def _temp(self, tag):
        try:
            return int(self.data.sensors.get(tag))
        except (TypeError, ValueError):
            return None

    @property
    def current_temperature(self):
        return self._temp(self.heat_set.current_tag)

    @property
    def target_temperature(self):
        return self._temp(self.heat_set.setpoint_tag)

    @property
    def hvac_mode(self):
        return heat_mode_to_hvac(self._heat_value())[0]

    @property
    def hvac_action(self):
        return heat_mode_to_hvac(self._heat_value())[1]

    async def async_set_hvac_mode(self, hvac_mode):
        # Heaters accept only 0 (Off) and 1 (Enabled); the controller decides when
        # to actually fire, based on the setpoint.
        value = 1 if hvac_mode == HVACMode.HEAT else 0
        await self.data.api.send(
            self.data.profile, "heat", self.heat_set.heat_tag, value
        )
        await self.data.async_refresh()

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        target = max(MIN_TEMP, min(MAX_TEMP, int(temperature)))
        await self.data.api.send(
            self.data.profile, "setpoint", self.heat_set.setpoint_tag, target
        )
        await self.data.async_refresh()

    async def async_update(self):
        await self.data.update()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_climate.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/climate.py tests/test_climate.py
git commit -m "fix: climate reads heat from the right section and handles mode 3

Jandy keeps poolht/spaht in <equipment>; Pentair keeps them in <temp>. The heat
mode map also stopped at 2, so Pentair's mode 3 (solar-only) raised KeyError."
```

---

### Task 9: Binary sensor platform (new)

**Files:**
- Create: `custom_components/autelis_pool/binary_sensor.py`
- Test: `tests/test_binary_sensor.py`

- [ ] **Step 1: Write the failing test**

`tests/test_binary_sensor.py`:

```python
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.autelis_pool.binary_sensor import AutelisReadOnly


class _Data:
    def __init__(self, equipment):
        self.equipment = equipment
        self.host = "1.2.3.4"
        self.mode = "auto"


def test_heater_reports_running_state():
    entity = AutelisReadOnly(_Data({"poolht": "1"}), "poolht", "Heater")
    assert entity.is_on is True
    assert entity.device_class == BinarySensorDeviceClass.HEAT


def test_heater_off():
    assert AutelisReadOnly(_Data({"poolht": "0"}), "poolht", "Heater").is_on is False


def test_name_says_running_so_nobody_mistakes_it_for_a_control():
    """poolht reports whether the heater is RUNNING, not whether it is ENABLED.

    Hayward can toggle heat only via the panel keypad, and the enabled state cannot
    be read back at all -- so this must never look like a switch.
    """
    assert AutelisReadOnly(_Data({"poolht": "0"}), "poolht", "Heater").name == "Heater Running"


def test_non_heat_readonly_has_no_heat_device_class():
    entity = AutelisReadOnly(_Data({"waterfall": "1"}), "waterfall", "Waterfall")
    assert entity.device_class is None
    assert entity.name == "Waterfall"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_binary_sensor.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Write `binary_sensor.py`**

```python
"""Read-only Autelis equipment.

Hayward's poolht and waterfall accept writes and silently ignore them (set.cgi
answers "1" either way -- that response only means the NAME was recognised). They
are reported, never controlled.

poolht reports whether the heater is RUNNING, not whether it is ENABLED. The enabled
state can only be read by pressing the panel's heat toggle, which changes it. So no
honest switch is possible; this is a sensor, and its name says so.
"""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import _LOGGER, DOMAIN, STATE_AUTO

_HEAT_TAGS = {"poolht", "poolht2", "spaht"}
_OFF_VALUES = {"", "0"}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Create a binary sensor for each read-only item discovery found."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities(
        [
            AutelisReadOnly(data, item.tag, item.name)
            for item in data.inventory
            if item.platform == "binary_sensor"
        ],
        True,
    )


class AutelisReadOnly(BinarySensorEntity):
    """One piece of equipment we can see but not command."""

    def __init__(self, data, equipment_name, friendly_name):
        self.data = data
        self.equipment_name = equipment_name
        self.friendly_name = friendly_name
        _LOGGER.debug("adding read-only %s (%s)", equipment_name, friendly_name)

    @property
    def name(self):
        # "Running", not "Heater" -- this reports the burner firing, not a mode you
        # can set. Naming it like a control would misrepresent what it knows.
        if self.equipment_name in _HEAT_TAGS:
            return f"{self.friendly_name} Running"
        return self.friendly_name

    @property
    def unique_id(self):
        return f"autelis {self.data.host} {self.equipment_name}"

    @property
    def device_class(self):
        if self.equipment_name in _HEAT_TAGS:
            return BinarySensorDeviceClass.HEAT
        return None

    @property
    def available(self):
        return self.data.mode == STATE_AUTO

    @property
    def is_on(self):
        return self.data.equipment.get(self.equipment_name, "0") not in _OFF_VALUES

    async def async_update(self):
        await self.data.update()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_binary_sensor.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/binary_sensor.py tests/test_binary_sensor.py
git commit -m "feat: add binary_sensor platform for read-only equipment

Hayward's poolht and waterfall accept writes and ignore them. poolht reports
whether the heater is RUNNING, not ENABLED, and the enabled state cannot be read
without changing it -- so it is a sensor named 'Running', never a switch."
```

---

### Task 10: The entity-manifest regression gate

This is the Jandy safety argument. It is the most important test in the repo.

**Files:**
- Create: `tests/test_manifests.py`

**Interfaces:**
- Consumes: `build_inventory`, `build_heat_sets`, `PROFILES`, and the label parsers from `names.py`.

- [ ] **Step 1: Write the manifest test**

`tests/test_manifests.py`:

```python
"""The entity manifests.

We cannot test Jandy or Pentair on hardware, so this pins EXACTLY which entities
each real capture produces. A reviewer signs these off once; after that, any change
to the entity set for an existing brand has to be deliberate enough to edit this
file.

Deliberately NOT "reproduce master's output exactly": master's Jandy behaviour is
partly what we are fixing, so a parity assertion would either block the fix or be
neutered by carving out the bug. Instead each list is explicit, and the Jandy
manifest is annotated with how it compares to master.
"""

from custom_components.autelis_pool.brands import PROFILES
from custom_components.autelis_pool.const import (
    AUTELIS_HAYWARD,
    AUTELIS_JANDY,
    AUTELIS_PENTAIR,
)
from custom_components.autelis_pool.discovery import build_heat_sets, build_inventory
from custom_components.autelis_pool.names import parse_aux_labels_html, parse_names_xml
from tests.conftest import load_fixture, load_xml


def _manifest(status, brand, names_file=None, settings_file=None):
    """(platform, tag, name, enabled_by_default) for every entity, sorted."""
    names = {}
    if names_file:
        names = parse_names_xml(load_xml(names_file))
    if settings_file:
        names = parse_aux_labels_html(load_fixture(settings_file))

    profile = PROFILES[brand]
    root = load_xml(status)
    entities = sorted(
        (d.platform, d.tag, d.name, d.enabled_default)
        for d in build_inventory(root, profile, names)
    )
    climate = sorted(
        ("climate", h.heat_tag, h.name, True) for h in build_heat_sets(root, profile)
    )
    return entities + climate


# Jandy 1.6.9 (upstream issue #3).
#
# IDENTICAL to what master produces today -- the regression gate. Master reaches the
# same set by a different route: it creates aux switches from names.xml and relies on
# a startswith("Cleaner") filter to skip aux1. We reach it from status.xml, where aux1
# is simply empty. Same answer, but ours does not depend on what the owner named the
# circuit: name it "Polaris" and master grows a phantom switch, while we do not.
JANDY_169 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "solartemp", "Solar Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "aux2", "Waterfall", True),
    ("switch", "aux3", "Air Blower", True),
    ("switch", "aux4", "SPA Light", True),
    ("switch", "aux5", "Pool Light", True),
    ("switch", "aux6", "Not Used", True),   # a deliberate label, not a placeholder
    ("switch", "aux7", "Not Used", True),
    ("switch", "cleaner", "Cleaner", True),
    ("switch", "pump", "Pool", True),
    ("switch", "solarht", "Solar Heating", True),
    ("switch", "spa", "Spa", True),
]

# Jandy 1.6.17. No names.xml for this unit, so labels fall back to defaults/tags.
# Proves macro1-6, htpmp and auxx are ignored rather than becoming dead switches.
JANDY_1617 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "solartemp", "Solar Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    # No names.xml for this unit, so these are OUR fallback labels. That is not
    # evidence the relays are unassigned, so they stay enabled -- status.xml says
    # they are installed, and that is all we know.
    ("switch", "aux1", "Aux 1", True),
    ("switch", "aux2", "Aux 2", True),
    ("switch", "aux3", "Aux 3", True),
    ("switch", "aux4", "Aux 4", True),
    ("switch", "aux5", "Aux 5", True),
    ("switch", "aux6", "Aux 6", True),
    ("switch", "aux7", "Aux 7", True),
    ("switch", "pump", "Pool", True),
    ("switch", "spa", "Spa", True),
]

# Pentair EasyTouch 1.6.11. Entirely NEW -- master crashes on Pentair, so there is no
# prior behaviour to preserve.
PENTAIR_1611 = [
    ("climate", "poolht", "Pool Heat", True),
    ("climate", "spaht", "Spa Heat", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "circuit1", "SPA", True),
    ("switch", "circuit2", "LIGHTS", True),
    ("switch", "circuit20", "AUX EXTRA", True),   # named, just oddly
    ("switch", "circuit3", "AUX 2", False),       # placeholder => unassigned
    ("switch", "circuit4", "AUX 3", False),
    ("switch", "circuit5", "AUX 4", False),
    ("switch", "circuit6", "POOL", True),
    ("switch", "circuit7", "AUX 5", False),
    ("switch", "circuit8", "AUX 6", False),
    ("switch", "circuit9", "POOL HIGH", True),
    ("switch", "feature1", "FEATURE 1", True),
    ("switch", "feature2", "FEATURE 2", True),
    ("switch", "feature3", "FEATURE 3", True),
    ("switch", "feature4", "FEATURE 4", True),
    ("switch", "feature5", "FEATURE 5", True),
    ("switch", "feature6", "FEATURE 6", True),
    ("switch", "feature7", "FEATURE 7", True),
    ("switch", "feature8", "FEATURE 8", True),
]

# Hayward model 512 / fw 1.0.11. Entirely NEW.
# No climate: no setpoint can be written OR read.
# Names are the OWNER's, read from settings.htm -- not firmware constants.
# aux6/aux7 are real relays (the panel has AUX 5 / AUX 6 buttons) but still carry
# placeholder labels, so they are registered and left disabled.
HAYWARD_1011 = [
    ("binary_sensor", "poolht", "Heater", True),
    ("binary_sensor", "waterfall", "Waterfall", True),
    ("sensor", "airtemp", "Air Temperature", True),
    ("sensor", "pooltemp", "Pool Temperature", True),
    ("sensor", "spatemp", "Spa Temperature", True),
    ("switch", "aux1", "Pool Lights", True),
    ("switch", "aux2", "Spa Lights", True),
    ("switch", "aux3", "Blower", True),
    ("switch", "aux4", "Waterfall", True),
    ("switch", "aux5", "Cleaner", True),
    ("switch", "aux6", "AUX5", False),      # unassigned
    ("switch", "aux7", "AUX6", False),      # unassigned
    ("switch", "pump", "Filter Pump", True),
    ("switch", "schlor", "SuperChlorinate", True),
    ("switch", "spa", "Spa", True),
    ("switch", "valve3", "Valve 3", True),
    ("switch", "valve4", "Valve 4", True),
]


def test_jandy_169_manifest():
    assert _manifest("jandy_169_status.xml", AUTELIS_JANDY, "jandy_169_names.xml") == JANDY_169


def test_jandy_1617_manifest():
    assert _manifest("jandy_1617_status.xml", AUTELIS_JANDY) == JANDY_1617


def test_pentair_1611_manifest():
    assert _manifest("pentair_1611_status.xml", AUTELIS_PENTAIR, "pentair_1611_names.xml") == PENTAIR_1611


def test_hayward_1011_manifest():
    assert (
        _manifest(
            "hayward_1011_status.xml",
            AUTELIS_HAYWARD,
            settings_file="hayward_1011_settings.htm",
        )
        == HAYWARD_1011
    )


def test_hayward_has_no_climate_entity():
    assert not [e for e in HAYWARD_1011 if e[0] == "climate"]


def test_jandy_keeps_every_switch_master_created():
    """The regression gate, stated as an explicit claim rather than a diff."""
    master_switches = {
        "pump", "spa", "solarht", "cleaner",   # upstream's CIRCUITS
        "aux2", "aux3", "aux4", "aux5", "aux6", "aux7",  # from names.xml, unfiltered
    }
    ours = {tag for platform, tag, _, _ in JANDY_169 if platform == "switch"}
    assert master_switches == ours


def test_no_existing_jandy_entity_is_disabled():
    """Discovery must not quietly disable an entity a Jandy user already has."""
    assert all(enabled for _, _, _, enabled in JANDY_169)


def test_jandy_entity_names_are_unchanged():
    """Renaming an entity changes its display name in every existing dashboard.

    Upstream's TEMP_SENSORS produced "Pool Temperature"; its CIRCUITS produced
    "Pool", "Spa", "Solar Heating", "Cleaner". Discovery must reproduce those exact
    strings, or every current user's UI labels quietly change under them.
    """
    names = {tag: name for _, tag, name, _ in JANDY_169}
    assert names["pooltemp"] == "Pool Temperature"
    assert names["spatemp"] == "Spa Temperature"
    assert names["airtemp"] == "Air Temperature"
    assert names["solartemp"] == "Solar Temperature"
    assert names["pump"] == "Pool"
    assert names["spa"] == "Spa"
    assert names["solarht"] == "Solar Heating"
    assert names["cleaner"] == "Cleaner"


def test_hayward_names_are_the_owners_not_ours():
    """Read from settings.htm. An earlier draft hardcoded these as firmware constants."""
    names = {tag: name for _, tag, name, _ in HAYWARD_1011}
    assert names["aux1"] == "Pool Lights"
    assert names["aux3"] == "Blower"
    assert names["aux5"] == "Cleaner"
```

- [ ] **Step 2: Run the manifests**

Run: `python -m pytest tests/test_manifests.py -v`
Expected: all pass. **If any manifest differs from what the code produces, do not edit the manifest to match the code until you understand exactly why it changed.** That is the whole point of the file.

- [ ] **Step 3: Run the whole suite**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_manifests.py
git commit -m "test: pin the exact entity manifest for every real capture

We have no Jandy or Pentair hardware, so this is the regression gate: each real
capture's full entity set is written down explicitly. The Jandy 1.6.9 manifest is
identical to what master produces today, reached from status.xml rather than from
names.xml -- so it no longer depends on what the owner named the cleaner."
```

---

### Task 11: Entity registry migration

Discovery removes phantom entities. That must not silently break someone's dashboard.

**Files:**
- Modify: `custom_components/autelis_pool/__init__.py`
- Test: `tests/test_migration.py`

- [ ] **Step 1: Write the failing test**

`tests/test_migration.py`:

```python
"""Phantom entities from the names.xml era must be removed cleanly, not orphaned."""

import pytest

from custom_components.autelis_pool import async_remove_stale_entities


class _Registry:
    def __init__(self, entries):
        self.entries = dict(entries)
        self.removed = []

    def async_remove(self, entity_id):
        self.removed.append(entity_id)
        self.entries.pop(entity_id, None)


class _Entry:
    def __init__(self, unique_id):
        self.unique_id = unique_id


@pytest.mark.asyncio
async def test_removes_entities_no_longer_discovered():
    registry = _Registry(
        {
            "switch.pool": _Entry("autelis 1.2.3.4 pump"),
            "switch.polaris": _Entry("autelis 1.2.3.4 aux1"),  # phantom: aux1 is empty
        }
    )
    live = {"autelis 1.2.3.4 pump"}

    await async_remove_stale_entities(registry, live)

    assert registry.removed == ["switch.polaris"]


@pytest.mark.asyncio
async def test_leaves_entities_from_other_integrations_alone():
    registry = _Registry({"light.kitchen": _Entry("hue-1234")})
    await async_remove_stale_entities(registry, {"autelis 1.2.3.4 pump"})
    assert registry.removed == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_migration.py -v`
Expected: FAIL — `ImportError: cannot import name 'async_remove_stale_entities'`

- [ ] **Step 3: Implement it**

Add to `custom_components/autelis_pool/__init__.py`:

```python
from homeassistant.helpers import entity_registry as er


async def async_remove_stale_entities(registry, live_unique_ids: set[str]) -> None:
    """Remove Autelis entities that discovery no longer produces.

    Building switches from names.xml created entities for aux circuits whose
    status.xml tag was empty -- equipment the owner does not have. They rendered as
    permanently-off switches. Discovery does not produce them, so they must be
    retired rather than left orphaned in the registry.

    Only touches entities whose unique_id is ours ("autelis <host> <tag>").
    """
    for entity_id, entry in list(registry.entries.items()):
        unique_id = entry.unique_id
        if not isinstance(unique_id, str) or not unique_id.startswith("autelis "):
            continue
        if unique_id not in live_unique_ids:
            _LOGGER.info("Removing stale Autelis entity %s (%s)", entity_id, unique_id)
            registry.async_remove(entity_id)
```

And call it at the end of `async_setup_entry`, after the first refresh:

```python
    live = {f"autelis {data.host} {item.tag}" for item in data.inventory}
    live |= {f"autelis {data.host} {hs.current_tag}" for hs in data.heat_sets}
    await async_remove_stale_entities(er.async_get(hass), live)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest tests/test_migration.py -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add custom_components/autelis_pool/__init__.py tests/test_migration.py
git commit -m "feat: retire phantom entities left over from names.xml discovery

Switches built from names.xml included aux circuits whose status.xml tag was empty
-- equipment the owner does not have, rendering as permanently-off switches. They
are removed from the registry rather than left orphaned."
```

---

### Task 12: Documentation and PR preparation

**Files:**
- Modify: `readme.md`, `custom_components/autelis_pool/manifest.json`

- [ ] **Step 1: Bump the version**

In `custom_components/autelis_pool/manifest.json`, set `"version": "1.1.0"` (a feature release with intentional breaking changes to the entity set).

- [ ] **Step 2: Rewrite the readme's support section**

Replace the "Currently this integration supports" section of `readme.md` with:

```markdown
# Supported controllers

The Autelis Pool Control bridges to several different pool controllers, and each
speaks a different dialect. The integration detects which one you have from the
shape of its `status.xml`.

| Controller | Status |
| --- | --- |
| Jandy / Zodiac (Aqualink RS) | Supported. Tested against real captures from firmware 1.6.9, 1.6.10 and 1.6.17. |
| Pentair (EasyTouch / Intellitouch) | Supported. Tested against a real capture from firmware 1.6.11. |
| Hayward (AquaLogic / Goldline) | Supported. Tested on live hardware, model 512, firmware 1.0.11. |

Equipment is discovered from what your controller actually reports, so you only get
entities for equipment you have.

## Hayward: no temperature control

**On Hayward, you cannot set the pool or spa temperature from Home Assistant.** This
is a limitation of the Autelis firmware, not of this integration:

- Hayward's `status.xml` contains no setpoints at all, so there is nothing to read.
- Its `set.cgi` rejects the `temp=` parameter outright (HTTP 500), so there is
  nothing to write.
- The heater can be toggled only from the panel's own keypad, and its *enabled*
  state cannot be read back — only whether it is currently *running*.

So Hayward gets a **Heater Running** sensor rather than a thermostat. Set your
temperatures at the panel.

## Naming your equipment

Entity names come from **your controller**, not from this integration:

| Controller | Where you set the names |
| --- | --- |
| Jandy, Pentair | Your controller's own labels, served as `names.xml`. |
| Hayward | The Autelis **Setup** page → *AUX Labels*. |

Rename an output there and it flows into Home Assistant on the next reload. You can
also rename any entity in Home Assistant itself, as usual — that always wins.

### Unassigned outputs

An AUX relay can be installed but not wired to anything, in which case your controller
still reports it under a placeholder name like `AUX5`. Those entities **are created,
but disabled by default** — they clutter nothing if you don't use them, and are one
click away in Home Assistant if you do. Give the output a real name on your controller
and it will be enabled automatically.

## A note on interlocks

Your pool controller can refuse a command. A cleaner will not start while the valves
are diverted to the spa, for instance. When that happens the switch will flip back on
the next poll — that is the controller declining, not the integration failing.
```

- [ ] **Step 3: Run the full suite one last time**

Run: `python -m pytest tests/ -v`
Expected: all pass.

- [ ] **Step 4: Commit and push**

```bash
git add readme.md custom_components/autelis_pool/manifest.json
git commit -m "docs: document Hayward support and its temperature-control limits"
git push -u origin feature/hayward-support
```

- [ ] **Step 5: Open the PR**

The PR body must be honest about three things, because the maintainer cannot verify Hayward and we cannot verify Jandy:

1. **What was tested where.** Hayward: live hardware. Jandy and Pentair: real captured XML only, pinned by `tests/test_manifests.py`. Say so plainly.
2. **The intentional breaking change.** Phantom aux switches (created from `names.xml` for equipment whose `status.xml` tag is empty) are removed. Users who had them will see them disappear.
3. **Do not claim this fixes issue #3.** It was already fixed in 1.0.6. What changes is that the fix no longer depends on the owner having named the circuit literally "Cleaner".

Also offer the maintainer the four captured fixtures as the lasting value: they are the first test fixtures this repo has ever had, and they let him refactor Jandy without a pool.

---

## Follow-ups (not in this PR)

- **Confirm Hayward `aux5` writes in pool mode.** It refused a write during testing, but the pool was in a scheduled spa window and a cleaner cannot run with the valves diverted. Reasoned, not measured.
- **`DataUpdateCoordinator` migration.** The `Throttle` + per-entity `async_update` model is legacy. Correct to fix, but it rewrites the update path for brands we cannot test, so it belongs in its own PR.
- **Jandy macros.** `macro1`–`macro6` appear in firmware 1.6.17 but no source proves what name `set.cgi` accepts. Needs one experiment on real hardware.
- **Chemistry, VS pumps, light colours.** `chem.xml`, `pumps.xml`, `lights.cgi` all exist. Note that they 404 on some Jandy units, so any implementation must tolerate their absence.

- **Harden XML parsing with `defusedxml`.** The integration parses XML from the pool
  controller with the stdlib `xml.etree.ElementTree` (as upstream already does). Be precise
  about the actual exposure: **XXE is not applicable** — CPython has not processed external
  general entities since 3.7.1. What remains is an entity-expansion DoS (billion-laughs /
  quadratic blowup), which requires an attacker who already controls the device on your LAN
  that you configured with credentials. Real but low. `defusedxml` fixes it in one line
  (`from defusedxml.ElementTree import fromstring`) plus a `"requirements": ["defusedxml"]`
  entry in `manifest.json`. Held out of this PR only because it adds a runtime dependency the
  upstream maintainer may not want bundled with a feature change — raise it with him
  separately.
