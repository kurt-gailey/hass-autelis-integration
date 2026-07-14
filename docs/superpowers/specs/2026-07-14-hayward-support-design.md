# Hayward Support for the Autelis Home Assistant Integration

**Date:** 2026-07-14
**Status:** Approved design, revised after adversarial review, not yet implemented
**Target:** PR to `k-harker/hass-autelis-integration` (from fork `kurt-gailey/hass-autelis-integration`)

## Goal

Add support for Autelis Pool Control units attached to **Hayward** (AquaLogic/Goldline)
pool controllers. The integration currently supports only Jandy/Zodiac, and would crash on a
Hayward unit.

Secondary goal, and the one that constrains the design: **do it without regressing Jandy**,
which we cannot test, because neither the author of this spec nor the reviewer has Jandy
hardware.

## Evidence base

Every claim is either measured on live hardware or taken from a real device capture. Where
something is inferred rather than observed, it says so — and the reader should assume
inferences are wrong until tested, because in this project several of them were.

**Live Hayward** (`172.16.20.27`, `model 512`, firmware `1.0.11`) — probed directly.
Findings about Hayward are findings about *this* unit; see "Known unknowns".

**Real captures from other brands**, from issues on the upstream repo:

| Brand | Firmware | Model | Source |
| --- | --- | --- | --- |
| Jandy Aqualink RS | 1.6.9 | 6520 | upstream issue #3 |
| Jandy Aqualink RS | 1.6.17 | 6520 | upstream issue #6 |
| Jandy Aqualink RS | 1.6.10 | 6525 | HomeSeer forum (archived) |
| Pentair EasyTouch | 1.6.11 | 13 | upstream issue #5 |

**Vendor documentation**: autelis.com is dead, but the HTTP command references for all three
brands survive on the Wayback Machine and corroborate the captures.

### Read this before you infer anything from `set.cgi`

**On Hayward, `set.cgi` returns `1` / HTTP 200 for any recognized equipment name, whether or
not the write does anything.** It is name validation, not acknowledgement. An unknown name
returns HTTP 500 ("Expected data not present").

`set.cgi?name=poolht&value=1` returns success and the heater does not turn on — `poolht`
holds at 0 across 100 polls. **Never infer writability from the response.** Writability below
was established by writing a value and polling `status.xml` until it changed, or provably
didn't.

Write latency varies by device class, and a short poll window produces false negatives:

| Device | Latency to appear in `status.xml` |
| --- | --- |
| Relays (`aux*`, `schlor`, valves) | 2–3 polls (~2s) |
| `spa` (valve motor) | 13 polls (~10s) |
| `poolht` | never (100 polls) — read-only |

Three confident inferences drawn from the Hayward web UI turned out **wrong** when tested:
the heater looked controllable and is not; the spa looked read-only and is not; the keypad
heat key looked like a display and is a real toggle. The map below is measured. Trust it over
the UI, and over this document's own prose.

## Brand differences

| | Jandy | Pentair | Hayward |
| --- | --- | --- | --- |
| `names.xml` | yes (undocumented) | yes | **absent (404)** |
| Setpoints (`poolsp`/`spasp`) | in `<temp>` | in `<temp>` | **absent entirely** |
| `poolht`/`spaht` live in | `<equipment>` | `<temp>` | `<equipment>` (read-only) |
| Heat set command | `value=` (0/1) | `hval=` (0–3) | **none** |
| Setpoint command | `temp=<int\|up\|dn>` | `temp=` | **`temp=` rejected, HTTP 500** |
| Solar temp tag | `solartemp` | `soltemp` | `solartemp` |
| Circuits | `pump`, `spa`, `cleaner`, `aux1`–`aux23`, `macro1`–`6` | `circuit1`–`20`, `feature1`–`10` | `pump`, `spa`, `waterfall`, `valve3`, `valve4`, `aux1`–`aux15`, `schlor` |
| Dimmers | `25/50/75/100` via the ordinary `value=` | `dim=3..10` (separate param) | none |
| Climate entity possible | yes | yes | **no** |

### Hayward capability map — measured

Tested by write-and-poll on the live unit:

| Tag | Result |
| --- | --- |
| `pump`, `spa`, `aux1`–`aux7`, `valve3`, `valve4`, `schlor` | **writable** (all confirmed by write-and-poll) |
| `poolht` | **read-only** (held 100 polls) |
| `waterfall` | **read-only** (held 60 polls) |

### Interlocks: a write can be silently refused without the circuit being read-only

**This is the single most important thing to understand before testing an Autelis.**

`aux5` (the cleaner) once refused a write and held at 0 for 35 polls — a signature *identical*
to read-only `poolht`. It is not read-only. It is **interlocked**, and it took three separate
observations to establish that:

1. It refused during a **scheduled spa window** — a cleaner cannot run with the valves
   diverted to the spa.
2. It refused again with the pool idle, because the **filter pump was off**.
3. It accepted immediately (2 polls) once the pump had been running for a **five-minute
   warm-up** — the condition the pool's owner named from experience.

So a failed write proves nothing on its own. **Read-only and interlocked are
indistinguishable from a single refusal**, and the only way to tell them apart is to satisfy
the interlock and retry. `poolht` and `waterfall` are called read-only above on the strength of
repeated tests under conditions where they *should* have responded; if a future owner reports
them working, believe them over this document.

Two consequences for the implementation:

1. **`aux5` ships as an ordinary circuit switch**, like every other Hayward aux.
2. **No circuit switch may trust its own write.** `set.cgi` returning `1` means "name
   recognised"; the panel may still refuse the command (spa mode, no flow, pump warm-up, freeze
   protection, service mode). Entity state must come from the next poll of `status.xml`, never
   from an assumption that the write landed. The readme tells users a switch flipping back is
   their controller declining, not a bug.

Two consequences the implementation must respect:

1. **`aux5` ships as an ordinary circuit switch**, like every other Hayward aux. Marking it
   read-only for all Hayward owners on the strength of one pool's cleaner interlock would be
   exactly the overgeneralisation this document warns about — and the Hayward firmware's own UI
   offers ON/OFF buttons for it.
2. **No circuit switch may trust its own write.** `set.cgi` returning `1` means "name
   recognised", and the panel may still refuse the command for interlock reasons (spa mode,
   freeze protection, service mode). Entity state must come from the next poll of
   `status.xml`, never from an assumption that the write landed.

This also means **read-only cannot be distinguished from interlocked by a single failed
write.** `poolht` and `waterfall` are called read-only above on the strength of repeated tests
under normal pool-mode conditions; if a future owner reports them responding, believe them.

Other observations:

- **Absent equipment is an empty tag** (`<aux8></aux8>`) on this unit.
- `/keypad.xml` exposes the physical panel's LCD text. Not used by this design.

## Why Hayward gets no climate entity

Every path is closed, and each was tested:

1. **`set.cgi` cannot write the heater.** Returns success; `poolht` never changes.
2. **There is no setpoint to write.** The `temp=` parameter is rejected outright — even
   `set.cgi?name=pump&temp=1` returns HTTP 500, proving the *parameter* is unsupported, not
   the name.
3. **There is no setpoint to read.** `poolsp`/`spasp` are absent from `status.xml`, so even a
   write-only setpoint could never populate `target_temperature`.
4. **The keypad *can* toggle heat — but the state cannot be read back.**

   `keypad.cgi?key=19` **is a real two-state heater toggle**
   (`Heater1 Auto Control` ↔ `Heater1 Manual Off`), confirmed by the vendor doc and by
   testing. So a *write* path exists. What does not exist is a *read* path:
   **`poolht` reports whether the heater is RUNNING, not whether it is ENABLED.** Confirmed —
   with the heater held in `Auto Control` and the pool at 91 °F (above setpoint, so the burner
   never lights), `poolht` stayed 0 across 40 polls.

   The only way to observe heater mode is to *press the toggle and read the resulting LCD
   label* — reading the state requires changing it. A Home Assistant switch cannot be built on
   that: it would have to either invent its state (desyncing the instant anyone touches the
   panel) or toggle a gas heater on every poll.

**Decision: the Hayward heater is a read-only `binary_sensor` reporting "heater running".**
Home Assistant will not offer control whose state it cannot honestly report.

## Architecture

### 1. Brand detection — structural, positive markers, decided once

Model numbers are unusable:

- **`model` is the *pool controller's* model, not the Autelis unit's.** Jandy is "4 digit"
  (6520 and 6525 observed); Pentair documents an enum "0–5" yet every real EasyTouch reports
  **13**; Hayward is documented only as "integer" (ours reports 512, a value that appears in
  no document).
- **It is not stable per device.** An archived Jandy RS16 reports `<model>0</model>` while the
  controller is disconnected (`runstate=1`).

Detect by document shape, and **require a positive marker for every brand** — no fall-through
default:

```text
system has "dip" / "vbat" / "lowbat", or equipment has "cleaner"  -> JANDY
equipment has "circuit1"                                          -> PENTAIR
equipment has "valve3" or "schlor"                                -> HAYWARD
none of the above                                                 -> UNKNOWN
```

**`UNKNOWN` must raise `ConfigEntryNotReady` and create no entities.** An earlier draft used
"else → Jandy", which is unsafe: a disconnected or still-initialising controller emits sparse
XML, and defaulting it to Jandy would build a wrong entity set that then persists in the
entity registry. A brand we cannot positively identify is a brand we refuse to guess at.

**Detection runs once, at config-entry setup, and is cached** — not re-evaluated every poll.
Inventory (which equipment exists) is likewise resolved at setup. Rediscovery happens on
reload. This prevents transient sparse XML from churning the entity registry.

Keeps upstream's `AUTELIS_JANDY = 0` / `AUTELIS_PENTAIR = 1`; adds `AUTELIS_HAYWARD = 2` and
`AUTELIS_UNKNOWN`.

### 2. Discovery decides PRESENCE. The brand profile decides ROLE.

This is the core of the design, and the distinction is load-bearing.

An earlier draft said "any non-empty `<equipment>` tag becomes a switch". **That is wrong**,
and would have shipped:

- **duplicate switches for `poolht`/`spaht`** on Jandy, which the climate entity already owns
- **bogus sensors on Pentair**, where `poolht`/`spaht` live under `<temp>` and would trip a
  naive "numeric temp child → sensor" rule
- **switches for `macro1`–`macro6`** that silently do nothing, since nobody has verified what
  name `set.cgi` accepts for Jandy macros (see Known unknowns)
- **a switch for Hayward `aux5`** that does not actuate

So:

- The **brand profile** declares, per tag, what it *is*: `circuit` (switch), `heat`
  (climate-owned), `setpoint` (climate-owned), `temperature` (sensor), `readonly` (binary
  sensor), or `ignore`.
- **Discovery** consults `status.xml` only to decide whether that equipment is *installed*:
  non-empty value → present; empty → absent, no entity.
- **A tag the profile does not know is ignored, not guessed at.** New firmware tags appear as
  nothing rather than as a broken switch.

A quiet benefit of reading presence from the document: **we never need to know the aux count.**
The Jandy docs describe `aux1`–`aux15`, but a real Aqualink RS16 emits `aux1`–`aux23`.
Presence-discovery picks up whatever the unit reports, where a hardcoded range would silently
truncate.

#### `names.xml` is a label side-table, not an entity source

On Jandy, when a cleaner is assigned to AUX1, the unit reports **`<aux1></aux1>` empty** and
routes that circuit's state through the dedicated `<cleaner>` tag — while `names.xml` still
says `aux1` = "Cleaner". This was the cause of upstream issue #3.

**Issue #3 is already fixed upstream** (release 1.0.6): Kevin added `"cleaner"` to `CIRCUITS`
and a filter that skips any `names.xml` entry starting with `"Cleaner"`. Do **not** claim in the
PR that this work fixes it — it does not, and the maintainer fixed it himself.

What this design changes is that **the existing fix depends on the user's name string.** The
filter matches the literal prefix `"Cleaner"`. An owner who named that aux "Polaris" or
"Sweeper" still gets a phantom `aux1` switch — created from `names.xml`, backed by an empty
`status.xml` tag, permanently reading Off and controlling nothing. That is the original bug,
reachable through a different name.

Therefore **entities derive from `status.xml` state tags only**; `names.xml` is consulted
afterwards, purely to label them. Presence-discovery makes the fix independent of what the
owner called the circuit, and retires the name-prefix filters
(`startswith("AUX")` / `"MACRO"` / `"Cleaner"`) in
[`switch.py:15`](../../../custom_components/autelis_pool/switch.py).

#### `names.xml` may be absent on *any* brand

It is undocumented on the Jandy and Hayward vendor pages, and the Pentair page mentions it
only as a stub. An archived Autelis forum thread explains why: it was **added in a later
firmware revision** and the docs were never updated.

So `names_endpoint` is **"attempt it, tolerate a 404"** for every brand — not "Jandy always has
it". An old Jandy on pre-`names.xml` firmware must degrade to default labels exactly as Hayward
does, not error. Same for `chem.xml` / `pumps.xml` / `lights.xml`, which are confirmed to
**404 on some Jandy units**.

#### Hayward DOES have user-assigned labels — they just aren't in `names.xml`

An earlier draft of this document claimed Hayward's aux labels were "firmware constants baked
into a static `equipment.htm`, identical for every owner". **That is wrong.** The Autelis
Setup page (`settings.htm`) has an editable **AUX Labels** form, persisted on the unit, and the
device renders those labels into the HTML it serves. What looked like hardcoded firmware
strings were this owner's own labels.

So Hayward has a names source; it is HTML rather than XML. `settings.htm` serves:

```html
<input maxlength=15 type="text" id="aux1label" value="Pool Lights"/>
```

The profile therefore gets a **names provider** rather than a fixed `names.xml` endpoint:

| Brand | Names source |
| --- | --- |
| Jandy, Pentair | `names.xml` (may 404 on old firmware) |
| Hayward | `settings.htm`, parsed for `id="auxNlabel" value="..."` |

Parsing HTML is not elegant, but the vendor is defunct and the firmware will never change
again, so the page is effectively frozen. A parse failure degrades to generic labels; it must
never raise.

This also means **renaming an aux in the Autelis web UI flows straight through to Home
Assistant**, which is exactly how Jandy already behaves. The two brands now work the same way.

#### Unassigned relays: created, but disabled by default

An aux can be installed but unassigned. On the reference Hayward, `aux6`/`aux7` are real relays
— `status.xml` reports them and the physical panel has AUX 5 / AUX 6 buttons — but their labels
are still the placeholders `AUX5` / `AUX6`. Jandy and Pentair have the same notion
(`AUX9`, `AUX 2`).

Pools differ: one owner uses no aux at all, another uses every one. So neither hiding them nor
exposing them all is right. Instead: **any circuit whose label still matches the placeholder
pattern `AUX\s*\d+` is created with `entity_registry_enabled_default = False`.** It appears in
the entity registry, disabled, one click from being switched on; it adds no clutter to anyone
who has not wired it up.

Note this changes nothing for Jandy: its unassigned auxes are *also* empty in `status.xml`, so
presence-discovery already excludes them. The rule only bites where a relay is genuinely
installed but unlabelled.

The off-by-one in Hayward's aux numbering is real hardware, not a bug: the panel calls the pool
light **L**, not A1, so Autelis `aux1` = Pool Light, `aux2` = panel **A1** (Spa Light), and so
on up to `aux6` = panel **A5**.

### 3. State snapshots must be rebuilt atomically

`AutelisData.update()` populates `self.sensors` / `self.equipment` **without ever clearing
them** ([`__init__.py:102-116`](../../../custom_components/autelis_pool/__init__.py)). A tag
that becomes empty therefore keeps its previous value, and equipment that has gone away still
looks installed.

That is a latent bug today and a **correctness prerequisite for discovery**, which reads
presence from exactly those dicts. Fix: build a fresh snapshot each poll and swap it in;
absent keys disappear rather than lingering.

### 4. Per-config-entry state

`hass.data[DOMAIN]` currently holds a **single global** `AutelisData`
([`__init__.py:51`](../../../custom_components/autelis_pool/__init__.py)), every platform reads
that singleton, and unload pops the whole domain. Two controllers cannot coexist today, and
multi-brand support makes that indefensible — two units of *different brands* would fight over
one global.

Fix: `hass.data[DOMAIN][entry.entry_id] = data`, and unload only that entry.

**Deliberately deferred:** migrating the `Throttle` + per-entity `async_update` model to a
`DataUpdateCoordinator`. It is the correct Home Assistant pattern and should happen — but it
rewrites the update path for Jandy and Pentair users we cannot test, roughly doubles the diff,
and is orthogonal to Hayward support. Separate PR.

### 5. New platform

`binary_sensor`, for read-only equipment. Naming must not imply control:
`binary_sensor.pool_heater_running` (device class `heat`/`running`), `binary_sensor.waterfall`.
The heater sensor reports **running**, not **enabled** — the name and docs must say so, because
the distinction is the entire reason there is no switch.

## Entity identity and migration

Existing `unique_id`s are `f"autelis {host} {equipment_name}"` across switches, sensors and
climate. Discovery keeps the same scheme, so **most entities keep their identity**. But it
changes *which* entities exist, and that must be handled deliberately rather than discovered by
users:

- **Removed:** phantom switches that `master` creates from `names.xml` for aux circuits whose
  `status.xml` tag is empty (not installed). These render as permanently-off switches today.
- **Changed:** the cleaner-on-AUX1 case (issue #3) — state moves from a broken `aux1` entity to
  the `cleaner` entity.

The implementation must ship an entity-registry migration for renamed unique IDs, and the PR
must call out removals as intentional breaking changes in the release notes. Silently deleting
entities out from under someone's dashboard is not acceptable.

## Bugs fixed on the way through

Pre-existing defects affecting **Jandy users today**, worth calling out in the PR:

1. **[`switch.py:52`](../../../custom_components/autelis_pool/switch.py)** — `is_on` compares
   only to `"1"`/`"2"`, so a Jandy **dimmer** aux reporting `25/50/75/100` reads as **Off**.
2. **[`climate.py:20-34`](../../../custom_components/autelis_pool/climate.py)** —
   `AUTELIS_HEAT_TO_MODE` has keys 0/1/2 only; Pentair's `poolht` ranges **0–3** (3 =
   solar-only) → `KeyError`.
3. **[`sensor.py:61`](../../../custom_components/autelis_pool/sensor.py)** — `device_class`
   does `self.type in (SensorDeviceClass.TEMPERATURE)`, which is a **substring test against a
   string**: `"Temperature" in "temperature"` is `False`, so **no temperature sensor has a
   device class**.
4. **[`sensor.py:71-72`](../../../custom_components/autelis_pool/sensor.py)** — divides the
   reading by 10, which is wrong for this API (`<pooltemp>88</pooltemp>` means 88 °F). It is
   currently dead code only because of the same capitalisation mismatch as #3. **Fixing #3
   without #4 would break every temperature reading.**
5. **Stale state keys** (see Architecture §3) and **single-global `hass.data`** (§4).
6. **Upstream `feature/pentair-support` regressions** — the global `solartemp`→`soltemp` rename
   and the commented-out `CIRCUITS` dict both disappear, since each brand now carries its own
   profile.
7. **Issue #3's fix is made robust** — not fixed here; it was already fixed upstream in 1.0.6.
   But that fix keys off the literal name `"Cleaner"`, so an aux the owner called "Polaris"
   still yields a phantom switch. Presence-discovery makes it name-independent.

## Testing

This is what makes the PR credible to a maintainer who cannot test Hayward, and to us, who
cannot test Jandy.

**Fixtures** — all real captures, committed verbatim:

- `jandy_1.6.9_status.xml` + `jandy_1.6.9_names.xml` (includes the empty-`aux1`/`cleaner` case)
- `jandy_1.6.17_status.xml` (includes `macro1`–`6`, `htpmp`, `auxx`)
- `pentair_1.6.11_status.xml` + `pentair_1.6.11_names.xml`
- `hayward_1.0.11_status.xml` (live capture from this work)

### Entity manifests, not "parity with master"

An earlier draft proposed asserting that the refactor reproduces `master`'s Jandy entity set
**exactly**. That was self-defeating: the same spec says `master`'s Jandy behaviour is *wrong*
and must change (issue #3). Exact parity would either block the fix or be neutered by carving
out the bug.

Instead, each fixture gets an **explicit expected manifest** — every entity, its `unique_id`,
its platform — split into:

- **preserved** — must be identical to `master`. This is the Jandy regression gate.
- **intentionally removed** — with the reason (phantom `names.xml`-only switches).
- **intentionally added** — with the reason.

The manifest is reviewed by a human once and then frozen. A diff against it fails CI. This
states the blast radius on Jandy explicitly instead of asserting there isn't one.

### Behaviour tests (entity-set shape proves almost nothing on its own)

- **Command construction per brand**: Hayward never receives a `temp=` param; Pentair heat uses
  `hval=`; Jandy heat uses `value=` and accepts only 0/1.
- **Brand detection** returns the right brand for each fixture, and `UNKNOWN` →
  `ConfigEntryNotReady` for a sparse/disconnected capture.
- **Empty tags produce no entity**; a tag that *becomes* empty drops out of the snapshot
  (no stale keys).
- **Dimmer values** (`25/50/75/100`) read as On.
- **Climate mode mapping** across the full 0–3 range.
- **Two config entries** of different brands coexist.
- **Entity-registry migration** maps old unique IDs to new.

## Out of scope

Present in the protocol, not needed for Hayward, deliberately deferred: `chem.xml`
(chemistry/ORP/pH), `pumps.xml` (variable-speed pumps), `lights.cgi` colour control, Jandy
macros/OneTouch, dimmers as HA `light` entities, and the `DataUpdateCoordinator` migration.

Macros deserve a specific note: discovery **must not** create switches for `macro1`–`macro6`
even though they appear as non-empty tags, because their `set.cgi` name is unverified (below).
They are `ignore` in the Jandy profile until someone tests them on hardware.

## Known unknowns

Stated plainly, so nobody mistakes them for settled:

1. **RESOLVED — Hayward `aux5` is writable.** Confirmed by write-and-poll: with the pool in
   pool mode and the filter pump running for a five-minute warm-up, the cleaner started within
   2 polls. Its earlier refusals were interlocks (spa mode; then no pump flow), not read-only
   behaviour. Every writable claim in this document is now measured rather than reasoned.
2. **Jandy `macroN` set command.** The vendor doc only documents
   `set.cgi?name=1tch3&value=1`, but real firmware 1.6.17 exposes `<macro1>`–`<macro6>`. Nobody
   has verified which name `set.cgi` accepts. Do not guess.
3. **Celsius.** Every capture found, across every brand, is `tempunits=F`. The existing Celsius
   handling is untested against real hardware.
4. **Hayward findings are from one unit** — model 512, firmware 1.0.11. "Hayward has no
   `names.xml`" is true *of this unit*; so is the shape of the Setup page we scrape for aux
   labels. Fallback behaviour must be tolerant (404 → defaults, unparseable HTML → defaults),
   never asserting universality. A firmware we have not seen should cost an owner their custom
   labels, never their setup.
5. **Hayward heater mode is RESOLVED but recorded here because an earlier draft got it wrong.**
   `keypad.cgi?key=19` is a genuine two-state toggle. It was briefly written off as
   "display only" on the reasoning that the panel LCD reverted to its status rotation by itself
   — **that inference was invalid**: a display timing out says nothing about whether the setting
   changed. The feature is excluded because `poolht` cannot report *enabled* state, not because
   the toggle doesn't work.
6. **RESOLVED, and recorded because an earlier draft got it backwards.** That draft asserted
   Hayward's aux labels were firmware constants "identical for every owner". They are not: they
   are user-editable device configuration, set on the Autelis Setup page and rendered into the
   HTML the unit serves. The labels that looked hardcoded in `equipment.htm` were simply this
   owner's own. Hayward reads its names from `settings.htm`; see "Hayward DOES have
   user-assigned labels", above.

   The lesson generalises: this document's Hayward findings come from one unit, and a string
   that looks like a constant may just be one owner's configuration. Check whether the device
   lets the owner change it before calling it a constant.
