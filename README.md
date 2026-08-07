<p align="center"><img src="https://raw.githubusercontent.com/LIN4CRE/dkma-monster/main/.github/banner.png" alt="dkma-monster banner" width="100%"></p>

<div align="center">

# 🧟 DKMA Monster

### Stop aggressive OEM battery managers from killing your Android apps.

A universal, multi-vector **"Don't Kill My App!"** toolkit — one shared OEM
knowledge base powering a CLI, a desktop GUI, a self-hostable web guide, root &
Magisk installers, an Android library, and a Kotlin Multiplatform module.

<br>

![License](https://img.shields.io/badge/license-MIT-f5a524)
![OEMs](https://img.shields.io/badge/OEMs-15%20families-f5a524)
![Deps](https://img.shields.io/badge/runtime%20deps-0-3ddc84)
![Python](https://img.shields.io/badge/python-3.x-f5a524)
![Platforms](https://img.shields.io/badge/Android%20·%20iOS%20·%20JVM%20·%20JS-KMP-f5a524)
![CI](https://img.shields.io/badge/CI-single--source%20drift%20guard-3ddc84)

<br>

[![Stars](https://img.shields.io/github/stars/LIN4CRE/dkma-monster?style=social)](https://github.com/DLinacre/dkma-monster/stargazers)
[![Live guide](https://img.shields.io/badge/live%20guide-online-3ddc84)](https://dlinacre.github.io/dkma-monster/)
[![Latest release](https://img.shields.io/github/v/release/LIN4CRE/dkma-monster)](https://github.com/DLinacre/dkma-monster/releases)

**⭐ If DKMA Monster saved your background app, please [star the repo](https://github.com/DLinacre/dkma-monster) — it helps others find it.**

<sub>Built by <b>David Linacre</b> · <a href="https://www.linacre.site/">linacre.site</a></sub>

</div>

---

## Why this exists

Android's biggest reliability problem isn't Android — it's what OEMs bolt on top.
Xiaomi (MIUI/HyperOS), Huawei, OPPO, vivo, Samsung and others ship aggressive,
**undocumented** background killers with **no public API**. Your alarm, tracker,
messenger or sync silently dies and users blame *your* app.

DKMA Monster attacks the problem from **every angle at once**, all driven by a
single source of truth — [`data/oem_registry.json`](data/oem_registry.json).

| Vector | What it does | Automatic? |
|---|---|---|
| 🔌 **ADB installer** (`adb/dkma.py`) | Detects the OEM, grants what ADB can, opens each vendor screen, then **verifies each step** | Semi (taps for UI-only toggles) |
| 🖥️ **Desktop GUI** (`gui/server.py`) | Point-and-click front end over the ADB engine: plug in phone → pick app → **Fix** | Semi (browser-driven) |
| 🧿 **Root installer** (`root/dkma-root.sh`) | Flips appops / doze / standby / vendor autostart with `su` | ✅ Fully |
| 🧩 **Magisk module** (`magisk/`) | Re-applies keep-alive settings on **every boot** for a package list | ✅ Fully, persistent |
| 📱 **Android library** (`android/`) | In-app guided wizard + **authoritative MIUI autostart read** | Semi (guided) |
| 🧬 **KMP module** (`kmp/`) | Share the registry + detection across Android / iOS / JVM / JS | Library |
| 🌐 **Web dashboard** (`web/build.py`) | Generates a searchable, self-hostable keep-alive guide from the registry | — |
| 🧠 **OEM registry** (`data/oem_registry.json`) | Single source of truth — components + fallbacks for 15 OEM families | — |

### Coverage (15 OEM families)
Xiaomi / Redmi / POCO · Samsung · Huawei / Honor · OPPO · vivo / iQOO · OnePlus ·
realme · Meizu · ASUS · Sony · Nokia / HMD · Google / Android One · Motorola /
Lenovo · Nothing · Tecno / Infinix / itel — plus a **generic fallback** for
anything unknown.

---

## ⚠️ The honest truth (no snake oil)

On a **stock, non-rooted** phone, no tool can silently flip Autostart, "MIUI
optimizations", "protected apps" or the per-app battery profile — they are
**UI-only toggles with no API**, by vendor design. So:

- **Without root** → DKMA does every automatable grant (Doze whitelist, standby
  bucket, background appops), *drives you straight to each remaining toggle*
  (≈1 minute of tapping), then **verifies what it can** (see below).
- **With root / Magisk** → nearly everything becomes fully automatic and
  **survives reboots**.

Anyone promising a stock, no-root, zero-tap "fix" is either using root or lying.

### Per-step verification
After each step, DKMA re-reads device state to *prove* whether it worked, and is
honest when it can't:

| Step | Proven via | API? |
|---|---|---|
| battery optimization / stamina | `dumpsys deviceidle whitelist` | ✅ |
| background / keep-running | appop `RUN_ANY_IN_BACKGROUND` + standby bucket | ✅ |
| autostart | appop `AUTO_START` (MIUI) / `DkmaAutostart` reflection | ⚠️ ROM-dependent |
| MIUI optimizations / protected apps / battery profile | *no readable state* | ❌ → honestly flagged |

---

## Quick start

### 1. ADB installer (any OS, no root)
```bash
# prerequisites: adb on PATH + USB debugging enabled on the phone
python3 adb/dkma.py com.your.app          # detect OEM → grant → guide → verify
python3 adb/dkma.py com.your.app --tui     # interactive checklist (arrow keys)
python3 adb/dkma.py com.your.app --auto    # grants only, no pauses
python3 adb/dkma.py com.your.app --dry-run # print commands, change nothing
python3 adb/dkma.py com.your.app --json    # machine-readable report (CI/QA)
python3 adb/dkma.py --list                 # list connected devices
```
Exit codes: `0` ok · `1` usage/device error · `2` adb missing · `3` partial.

### 2. Desktop GUI (point-and-click, no root)
```bash
python3 gui/server.py                      # opens http://127.0.0.1:8765
```
Plug in the phone, pick the app, click **Fix everything** (or **Dry run**).
Preview the UI without a phone: open [`gui/preview.html`](gui/preview.html).

### 3. Web dashboard (self-hostable guide)
```bash
python3 web/build.py                       # generate the site into web/site/
python3 -m http.server -d web/site 8080    # optional local preview
```
Static output — host on GitHub Pages, Netlify, Cloudflare Pages, S3, or open
[`web/site/index.html`](web/site/index.html) directly.

### 4. Root installer (fully automatic)
```bash
adb push root/dkma-root.sh /sdcard/
adb shell "su -c 'sh /sdcard/dkma-root.sh com.your.app'"
```

### 5. Magisk module (persistent, survives reboots)
```bash
cd magisk && sh build-zip.sh               # → dkma-monster-magisk.zip
# flash in Magisk, then add packages to /data/adb/dkma/apps.list and reboot
```

### 6. Android library + Compose wizard (developers)
```kotlin
// zero-dependency engine
if (DkmaMonster.needsAttention(context)) {
    DkmaMonster.runGuidedSetup(activity)   // opens each required screen in order
}

// or the ready-made Compose wizard UI kit
setContent { MaterialTheme { DkmaWizardScreen(onFinish = { finish() }) } }

// authoritative MIUI/HyperOS autostart read (no external dependency)
when (DkmaAutostart.getState(context)) {
    DkmaAutostart.State.ENABLED  -> { /* proven ON  → don't nag */ }
    DkmaAutostart.State.DISABLED -> { /* proven OFF → send to Autostart screen */ }
    else -> { /* unknown/unsupported → fall back to guiding */ }
}
```
See [`android/README.md`](android/README.md). For multiplatform apps, use the
[`kmp/`](kmp/README.md) module instead.

---

## Architecture — one source of truth

```
                    data/oem_registry.json   ← edit ONLY this
                              │
   ┌───────────────┬──────────┼───────────┬──────────────────┬─────────────┐
   ▼               ▼          ▼           ▼                  ▼             ▼
 adb/dkma.py   gui/server.py  web/build.py   tools/gen_*.py        root/  · magisk/
 (reads JSON)  (reads JSON)   (reads JSON)   → DkmaRegistry.kt (Android)
                                             → DkmaRegistryData.kt (KMP)
```

- The **CLI, GUI and web generator read the JSON directly**, so they can't drift.
- The **Android & KMP libraries** can't read the file at build time, so
  `tools/build_all.py` generates their registries from it — and
  `tools/build_all.py --check` (run in CI) fails the build if they're stale.

```bash
python3 tools/build_all.py          # regenerate every derived artifact
python3 tools/build_all.py --check  # CI: validate + fail on drift
```

---

## Repository layout

```
dkma-monster/
├── data/oem_registry.json     # 🧠 single source of truth (15 OEMs)
├── adb/dkma.py                # cross-platform ADB installer (TUI/JSON/dry-run/verify)
├── gui/                       # desktop GUI: stdlib server + HTML front end (+ preview)
├── web/build.py               # static-site generator → web/site/
├── android/                   # DkmaMonster, DkmaAutostart, DkmaWizard, DkmaRegistry(gen)
├── kmp/                       # Kotlin Multiplatform module (common + android/jvm/ios/js)
├── root/dkma-root.sh          # fully-automatic root installer
├── magisk/                    # persistent Magisk module + build-zip.sh
├── tools/                     # codegen + single-source build/drift orchestrator
├── docs/                      # HOW-IT-WORKS · CONTRIBUTING · ROADMAP
└── .github/workflows/ci.yml   # registry validation + drift guard + compiles
```

---

## The 3 settings that fix ~95% of cases
1. **Autostart / auto-launch → ON**
2. **Battery → Unrestricted / No restrictions**
3. **Keep running after screen off → ON**

Plus: for genuinely long-lived work, run a **foreground service** — the most
reliable pattern on aggressive OEMs regardless of these toggles.

---

## Contributing

The most valuable contribution is **accurate vendor Activity names** for new ROM
versions. It's a one-file edit + regenerate:

1. Edit [`data/oem_registry.json`](data/oem_registry.json)
   (see [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)).
2. Run `python3 tools/build_all.py`.
3. Commit the JSON **and** the regenerated files.

CI drift-checks everything, so nothing can fall out of sync.

## Credits

Knowledge distilled from the community effort at
[dontkillmyapp.com](https://dontkillmyapp.com) and the
[MIUI-autostart](https://github.com/XomaDev/MIUI-autostart) technique.
Design language inspired by and built by **David Linacre** ·
[linacre.site](https://www.linacre.site/).

## License

[MIT](LICENSE) — do whatever, no warranty. Killing OEM battery managers is a
public service.
