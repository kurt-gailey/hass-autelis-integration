# The Autelis local HTTP protocol

Autelis is defunct and its documentation wiki is gone (the command references survive only on
[archive.org](https://web.archive.org/web/20190917102649/http://www.autelis.com/wiki/index.php?title=Pool_Control_HTTP_Command_Reference)).
This is what we know, written down so the next person doesn't have to rediscover it against
live pool equipment.

Everything below was either measured on real hardware or taken from a real device capture. The
test fixtures in `tests/fixtures/` are verbatim captures — Jandy 1.6.9 and 1.6.17, Pentair
EasyTouch 1.6.11, and a live Hayward model 512 / firmware 1.0.11.

## Read this first: `set.cgi` lies about success

**A `1` response from `set.cgi` means the device recognised the NAME. It does not mean the
write took effect.**

```
set.cgi?name=poolht&value=1   ->  1   (HTTP 200)   ... and the heater does not turn on.
set.cgi?name=bogus123&value=1 ->  500 Internal Server Error: Expected data not present
```

On Hayward, `poolht` returns `1` and then holds at `0` across 100 polls. It is read-only; the
firmware simply accepts and discards the write. So **never infer writability from the
response.** The only way to know is to write a value and poll `status.xml` until it changes —
or provably doesn't.

Write latency varies a lot by device class, and a short poll window produces false negatives:

| Device | Time to appear in `status.xml` |
| --- | --- |
| Relays (`aux*`, `schlor`, valves) | ~2–3 polls (~2 s) |
| `spa` (valve motor must physically rotate) | ~13 polls (~10 s) |

## Read this second: read-only and interlocked look identical

A circuit that refuses a write looks *exactly* like a circuit that is read-only: HTTP 200, and
the value never changes. **They cannot be distinguished by a single failed write.**

The cleaner (`aux5` on Hayward) refused a write three times before we understood it:

1. Refused during a scheduled **spa window** — a cleaner cannot run with the valves diverted.
2. Refused with the pool idle, because the **filter pump was off**.
3. Accepted within 2 polls once the pump had run a **five-minute warm-up**.

It was interlocked all along. The pool controller enforces safety rules — no cleaner without
flow, no heater without circulation — and simply declines commands that would violate them.

**If a command seems to be ignored, look at the physical panel's LCD.** It reports the reason,
which the HTTP API never does. (`/keypad.xml` returns the panel's two LCD lines, and reading it
is safe — but see the keypad warning below.)

For the integration, this means: **no switch may trust its own write.** Entity state comes from
the next `status.xml` poll, never from an assumption that the command landed.

## Brand detection: never use `<model>`

The `model` field is the **pool controller's** model, not the Autelis unit's, and it is
useless for identifying the dialect:

* Jandy: a 4-digit string — 6520 and 6525 both seen.
* Pentair: the docs say it is an enum `0-5`. Every real EasyTouch reports **13**.
* Hayward: documented only as "integer". The reference unit reports 512, a value that appears
  in no documentation anywhere.
* A **disconnected** Jandy reports `<model>0</model>`.

Detect by document *shape* instead, and require a positive marker — never fall through to a
default, because a disconnected controller emits sparse XML and would be misdetected, then
persist a wrong entity set into Home Assistant's registry:

```
equipment has "circuit1"            -> Pentair
equipment has "valve3" or "schlor"  -> Hayward
equipment has "cleaner"             -> Jandy
system has dip / vbat / lowbat      -> Jandy
system has haddr / systime          -> Pentair
none of the above                   -> UNKNOWN (refuse; do not guess)
```

## The three dialects

| | Jandy | Pentair | Hayward |
| --- | --- | --- | --- |
| Equipment names | `names.xml` | `names.xml` | **`settings.htm`** (see below) |
| Setpoints (`poolsp`/`spasp`) | in `<temp>` | in `<temp>` | **do not exist** |
| `poolht` / `spaht` live in | `<equipment>` | **`<temp>`** | `<equipment>` (read-only) |
| Set heat mode | `value=` (0/1) | `hval=` (0–3) | keypad only |
| Set setpoint | `temp=<int\|up\|dn>` | `temp=` | **impossible** |
| Solar temp tag | `solartemp` | **`soltemp`** | `solartemp` |
| Circuits | `pump`, `spa`, `cleaner`, `aux1`–`aux23`, `macro1`–`6` | `circuit1`–`20`, `feature1`–`10` | `pump`, `spa`, `valve3/4`, `aux1`–`aux15`, `schlor` |
| Dimmers | `25/50/75/100` via `value=` | `dim=3..10` | none |

Two traps worth naming:

* **Hayward rejects the `temp=` parameter outright.** Even `set.cgi?name=pump&temp=1` — a name
  that certainly exists — returns HTTP 500. It is the *parameter* the firmware lacks, not the
  name.
* **Jandy's aux runs to `aux23`**, though the docs only describe `aux1`–`aux15`.

## Empty tag = equipment not installed

```xml
<aux7>0</aux7>     <!-- installed, currently off -->
<aux8></aux8>      <!-- NOT INSTALLED. Not "off". -->
```

This is how the Autelis firmware's own web UI decides what to render, and it is how this
integration discovers your equipment. It has one subtlety that caused a real bug (upstream
issue #3):

**On Jandy, a cleaner assigned to AUX1 leaves `<aux1>` EMPTY** and routes that circuit's state
through the dedicated `<cleaner>` tag — while `names.xml` still calls `aux1` "Cleaner".

So `names.xml` is a **label side-table**. It must never create an entity, or you get a phantom
switch backed by nothing.

## Where the owner's names live

`names.xml` is undocumented and was a **later firmware addition**, so it 404s on older units.
Treat its absence as normal, not an error. The same goes for `chem.xml`, `pumps.xml` and
`lights.xml`, which 404 on some Jandy units.

**Hayward serves no `names.xml` at all — but its labels are not unavailable.** They live on the
Autelis **Setup** page, are editable, and are persisted on the unit, which renders them into
the HTML it serves:

```html
<input maxlength=15 type="text" id="aux1label" value="Pool Lights"/>
```

Scraping HTML is inelegant, but the vendor is gone and the firmware will never change, so the
page is frozen. Parse it, and fall back to generic labels if that ever fails.

An output can be installed but **unassigned**, in which case the controller returns a
placeholder label — `AUX5` (Hayward), `AUX9` (Jandy), `AUX 2` (Pentair), `MACRO1`. The relay is
real; the owner just hasn't wired it to anything.

## Why Hayward gets no climate entity

Not a design choice — the firmware closes every route, and each was tested:

1. `set.cgi` accepts `poolht` writes and **ignores them** (100 polls, no change).
2. There is **no setpoint to write**: the `temp=` parameter returns HTTP 500.
3. There is **no setpoint to read**: `poolsp`/`spasp` are absent from `status.xml`, so
   `target_temperature` could never be populated.
4. `keypad.cgi?key=19` **is** a real two-state heat toggle (`Heater1 Auto Control` ↔
   `Heater1 Manual Off`) — but `poolht` reports whether the heater is **RUNNING**, not whether
   it is **ENABLED**. (Proven: with heat in Auto Control and the pool above setpoint so the
   burner never lit, `poolht` stayed 0 for 40 polls.) The enabled state can only be read by
   pressing the toggle — which *changes* it.

So a Home Assistant switch would have to either invent its state or toggle a gas heater on
every poll. Hayward gets a **Heater Running** binary sensor instead.

## `keypad.cgi` — handle with care

`keypad.cgi?key=N` presses a key on the **physical panel**. `/keypad.xml` returns the panel's
two LCD lines and is safe to read.

The keys are not idempotent. `key=19` (Heater) is a *toggle*, not a display. It is easy to
mistake it for one, because the panel's LCD reverts to its status rotation after a few seconds
— **that timeout tells you nothing about whether the setting changed.** Assuming otherwise
means silently flipping someone's heater.

## Endpoints

| Endpoint | Notes |
| --- | --- |
| `status.xml` | The only endpoint you can rely on. HTTP Basic auth, user `admin`. |
| `names.xml` | Jandy/Pentair. May 404 (later firmware addition). |
| `settings.htm` | Hayward's aux labels, rendered into the HTML. |
| `set.cgi` | See the warnings at the top of this file. |
| `keypad.xml` | The physical panel's LCD text. Safe to read. |
| `keypad.cgi` | Presses physical panel keys. **Not idempotent.** |
| `chem.xml`, `pumps.xml`, `lights.xml` | Not implemented here. 404 on some units. |
