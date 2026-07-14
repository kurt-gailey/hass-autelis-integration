This is an [Autelis Pool Controller](https://web.archive.org/web/20211218192955/http://autelis.com/) integration for [Home Assistant](https://www.home-assistant.io/).  Since the Autelis Pool Controller is no longer being sold, this is only for those with this device for their pool.  I will continue to update this until I no longer have a working Autelis.  Mine has been working fine since 2013 and I don't currently have plans to replace it with anything different.

If the functionality you want is not available, feel free to send me a PR or put in an issue and I'll respond as I have time.

# Supported controllers

The Autelis Pool Control bridges to several different pool controllers, and each speaks a
noticeably different dialect. The integration works out which one you have from the shape of
its `status.xml` — it never asks you, and it never guesses from the model number (that field
turns out to be the *pool controller's* model, not the Autelis unit's, and it reads `0` while
the controller is disconnected).

| Controller | Status |
| --- | --- |
| Jandy / Zodiac (Aqualink RS) | Supported. Tested against real captures from firmware 1.6.9, 1.6.10 and 1.6.17. |
| Pentair (EasyTouch / Intellitouch) | Supported. Tested against a real capture from firmware 1.6.11. |
| Hayward (AquaLogic / Goldline) | Supported. Tested on live hardware — model 512, firmware 1.0.11. |

Your equipment is **discovered from what your controller actually reports**, so you only get
entities for equipment you actually have. Nothing is hardcoded.

# Hayward: you cannot set temperatures from Home Assistant

This is the one thing a Hayward owner needs to know up front. **On Hayward, the pool and spa
temperature cannot be set from Home Assistant.** That is a limitation of the Autelis firmware,
not of this integration, and all three routes are genuinely closed:

* Hayward's `status.xml` contains **no setpoints at all**, so there is nothing to read.
* Its `set.cgi` **rejects the `temp=` parameter outright** with an HTTP 500 — even on a name
  that definitely exists. It is the parameter the firmware lacks, not the name.
* The heater can only be toggled from the panel's own keypad, and its *enabled* state cannot be
  read back — only whether it is currently *running*.

So on Hayward you get a **Heater Running** sensor rather than a thermostat. Set your
temperatures at the panel. (Jandy and Pentair are unaffected — they get full climate entities.)

# What you get

* A config UI for the host and password of your Autelis controller.
* **Switches** for every circuit your controller reports: pumps, spa mode, cleaner, valves,
  aux outputs, superchlorinate (Hayward), and Jandy macros.
* **Sensors** for pool, spa, air and solar temperature — whichever your controller reports.
* **Climate** entities for pool and spa heat — on Jandy and Pentair. Not Hayward (see above).
* **Binary sensors** for equipment that can be seen but not commanded.

# Naming your equipment

Entity names come from **your controller**, not from this integration:

| Controller | Where you set the names |
| --- | --- |
| Jandy, Pentair | Your controller's own labels, served as `names.xml`. |
| Hayward | The Autelis **Setup** page → *AUX Labels*. |

Rename an output there, reload the integration, and the new name flows through. You can also
rename any entity in Home Assistant itself, as usual — that always wins.

## Outputs you haven't set up

An output can be physically present but not wired to anything, in which case your controller
still reports it under a placeholder name like `AUX5` or `MACRO2`. Those entities **are
created, but disabled by default**. They clutter nothing if you don't use them, and they're one
click away in Home Assistant if you do. Give the output a real name on your controller and it
becomes enabled automatically.

# A note on interlocks

Your pool controller can refuse a command, and it is right to. A cleaner will not start while
the valves are diverted to the spa, for instance. When that happens the switch flips back on
the next poll — that is your controller declining, not the integration failing.

# Not currently supported

* Variable speed pumps (`pumps.xml`)
* Chemistry — ORP, pH, salt (`chem.xml`)
* Colour lights (`lights.cgi`)
* Battery voltage and low-battery (Jandy only)
* Freeze protect

# Known issues

* Some temperatures don't change unless the pump is running. This is a limitation of the pool
  controller, not the Autelis or this integration.
  * Pool and spa temps only update when in that mode — so the spa temp will keep reporting
    whatever the spa was last time its pump ran.
  * Solar temp only updates when the pump is running.
  * Air temp always updates.

# Installation

1. Configure your Autelis first.
   1. Give real names to any Aux outputs or Macros you plan to use — that's how they reach
      Home Assistant, and how they get enabled. Leave the rest at their defaults.
   2. Check the local Autelis web page works and the temperatures look right. This integration
      reports what your controller reports; if it's wrong there, it will be wrong in Home
      Assistant.
2. Install via HACS — follow the [HACS instructions for adding a custom repo](https://www.hacs.xyz/docs/faq/custom_repositories/).
3. In Home Assistant, go to `Settings` → `Devices & Services`.
4. Click **Add Integration** and pick `Autelis Pool Control`.
5. Fill in:
   - **Host** — the hostname or IP of your Autelis device. For a non-standard port, append
     `:<port>` (e.g. `192.168.1.5:8080`).
   - **Password** — the password you use to log into the controller.
