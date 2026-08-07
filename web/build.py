#!/usr/bin/env python3
# =============================================================================
#  DKMA MONSTER  --  Web dashboard generator (stdlib only)
#  Turns data/oem_registry.json into a self-hostable, searchable static site
#  (a dontkillmyapp.com-style guide) so the docs can never drift from the tools.
#
#  Usage:   python3 web/build.py            # writes site into web/site/
#           python3 web/build.py --out DIR
# =============================================================================
import argparse
import html
import json
import os
import re
import shutil
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "..", "data", "oem_registry.json")

# ---- user-facing guidance per step id (the registry stores tech; we add UX) --
STEP_GUIDE = {
    "autostart": ("Enable Autostart",
        "Find this app in the Autostart list and turn its toggle ON. This lets it "
        "start itself in the background \u2014 the single most important setting."),
    "battery_profile": ("Set battery to \u201cNo restrictions\u201d",
        "Change this app's battery mode from \u201cBattery saver\u201d to "
        "\u201cNo restrictions\u201d so the system won't sleep it."),
    "app_details": ("App info \u2192 allow background",
        "Open the app's info page and enable options like \u201cAutostart,\u201d "
        "\u201cKeep running after screen off\u201d and battery \u201cUnrestricted.\u201d"),
    "sleeping_apps": ("Remove from Sleeping apps",
        "Make sure this app is NOT listed under \u201cSleeping apps\u201d or "
        "\u201cDeep sleeping apps.\u201d Remove it if present."),
    "protected_apps": ("Protect the app / App launch",
        "Switch the app to \u201cManage manually,\u201d then enable Auto-launch, "
        "Secondary launch and Run in background."),
    "startup_manager": ("Allow auto-launch",
        "Allow this app to launch automatically in the Startup manager."),
    "startup": ("Allow auto-launch",
        "Allow this app to launch automatically in the Startup manager."),
    "chain": ("Disable deep optimization",
        "Turn off \u201cDeep optimization\u201d / \u201cAdvanced optimization\u201d "
        "for this app."),
    "recent_lock": ("Lock in Recents + don't optimize",
        "Lock the app card in Recent apps, and set Battery optimization to "
        "\u201cDon't optimize.\u201d"),
    "chain_launch": ("Disable deep optimization",
        "Turn off deep/advanced optimization for this app."),
    "stamina": ("Exclude from STAMINA",
        "Add this app to the exceptions of STAMINA / battery-saver mode."),
    "security": ("Allow background from Security",
        "In the Security app, allow this app to keep running in the background."),
    "auto_start": ("Enable auto-start",
        "Allow this app to auto-start via the device's Mobile/Phone Manager."),
    "battery_opt": ("Battery optimization \u2192 Don't optimize",
        "In the battery-optimization list, set this app to \u201cDon't optimize.\u201d"),
}

def guide(step):
    """Prefer the JSON's own hint (single source of truth); fall back to the
    curated STEP_GUIDE copy, then to the raw title."""
    sid = step.get("id", "")
    if step.get("hint"):
        # Use the friendly STEP_GUIDE title if we have one, else the raw title.
        title = STEP_GUIDE.get(sid, (step.get("title", sid), ""))[0]
        return title, step["hint"]
    title, body = STEP_GUIDE.get(sid, (step.get("title", sid),
        "Open this settings screen and allow the app to run in the background."))
    return title, body

# ---- tiny html helpers ------------------------------------------------------
def esc(s): return html.escape(str(s), quote=True)

CSS = """
/* ===== DKMA Monster - Linacre theme (Ink Black + Amber Core/Glow) ===== */
:root{
  --ink:#0b0b0d; --ink2:#111116; --panel:#15151c; --panel2:#1b1b24;
  --line:#26262f; --line2:#33333f;
  --text:#f4f2ee; --muted:#9a9aa6; --dim:#6c6c78;
  --amber:#f5a524; --amber2:#ff8f00; --amber-soft:rgba(245,165,36,.14);
  --glow:0 0 24px rgba(245,165,36,.28); --glow-sm:0 0 12px rgba(245,165,36,.22);
  --ok:#3ddc84; --warn:#f5a524; --err:#ff5c6c;
  --grad:linear-gradient(135deg,#f5a524,#ff8f00);
  --mono:ui-monospace,'SF Mono',SFMono-Regular,'JetBrains Mono',Menlo,Consolas,monospace;
  --sans:'Space Grotesk','Segoe UI',Roboto,system-ui,-apple-system,sans-serif;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:var(--sans);background:var(--ink);color:var(--text);line-height:1.6;
  background-image:radial-gradient(1200px 500px at 78% -8%,rgba(245,165,36,.10),transparent 60%),
    radial-gradient(900px 500px at 0% 0%,rgba(245,165,36,.05),transparent 55%);
  background-attachment:fixed;}
a{color:var(--amber);text-decoration:none}a:hover{text-decoration:underline}

/* glassmorphism sticky header */
header.top{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:14px;padding:14px 26px;
  border-bottom:1px solid var(--line);background:rgba(11,11,13,.72);backdrop-filter:blur(12px) saturate(140%);
  -webkit-backdrop-filter:blur(12px) saturate(140%);}
header.top .logo{width:34px;height:34px;display:grid;place-items:center;font-size:16px;font-weight:800;color:var(--ink);
  background:var(--grad);clip-path:polygon(25% 5%,75% 5%,100% 50%,75% 95%,25% 95%,0% 50%);
  box-shadow:var(--glow-sm);animation:breathe 3.6s ease-in-out infinite}
@keyframes breathe{0%,100%{box-shadow:0 0 10px rgba(245,165,36,.20)}50%{box-shadow:0 0 22px rgba(245,165,36,.45)}}
header.top h1{font-size:16px;margin:0;font-weight:700;letter-spacing:.2px}
header.top h1 a{color:var(--text)}
header.top .tag{margin-left:auto;color:var(--dim);font-size:12px;font-family:var(--mono)}

/* amber pulse-line divider */
.pulse{height:1px;border:0;margin:0;background:linear-gradient(90deg,transparent,var(--amber),transparent);
  opacity:.5;box-shadow:0 0 8px rgba(245,165,36,.4)}

.wrap{max-width:1060px;margin:0 auto;padding:30px 26px 10px}

/* hex-grid hero */
.hero{position:relative;padding:26px 0 26px;overflow:hidden}
.hero::before{content:"";position:absolute;inset:-40px -20px auto auto;width:280px;height:220px;opacity:.5;
  background-image:
   linear-gradient(60deg,transparent 46%,rgba(245,165,36,.16) 47%,rgba(245,165,36,.16) 53%,transparent 54%),
   linear-gradient(-60deg,transparent 46%,rgba(245,165,36,.16) 47%,rgba(245,165,36,.16) 53%,transparent 54%);
  background-size:26px 46px;-webkit-mask-image:radial-gradient(circle at 70% 30%,#000,transparent 70%);
  mask-image:radial-gradient(circle at 70% 30%,#000,transparent 70%);pointer-events:none}
.kicker{font-family:var(--mono);font-size:12px;color:var(--amber);letter-spacing:.12em;text-transform:uppercase;
  display:inline-flex;align-items:center;gap:8px;margin-bottom:12px}
.kicker::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--amber);box-shadow:var(--glow-sm);
  animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.hero h2{font-size:34px;line-height:1.12;margin:0 0 12px;font-weight:700;letter-spacing:-.02em}
.hero h2 .amber{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{color:var(--muted);max-width:66ch;font-size:15.5px}

/* terminal prompt line */
.term{font-family:var(--mono);font-size:13px;background:var(--ink2);border:1px solid var(--line);border-radius:12px;
  padding:12px 14px;margin:16px 0 0;color:var(--muted);box-shadow:inset 0 0 0 1px rgba(255,255,255,.02)}
.term .p{color:var(--amber)} .term .c{color:var(--dim)}

.search{width:100%;padding:14px 16px;background:var(--panel2);color:var(--text);border:1px solid var(--line);
  border-radius:12px;font-size:16px;margin:14px 0 24px;font-family:var(--mono);transition:.15s}
.search:focus{outline:none;border-color:var(--amber);box-shadow:var(--glow-sm)}

.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
.card{display:block;position:relative;background:linear-gradient(180deg,var(--panel),var(--ink2));
  border:1px solid var(--line);border-radius:16px;padding:18px;transition:.18s;overflow:hidden}
.card::after{content:"";position:absolute;inset:0;border-radius:16px;padding:1px;background:transparent;pointer-events:none;transition:.18s}
.card:hover{transform:translateY(-3px);border-color:var(--amber);box-shadow:var(--glow);text-decoration:none}
.card .name{font-weight:700;font-size:16px;color:var(--text)}
.card .meta{color:var(--muted);font-size:12.5px;margin-top:6px}
.badge{display:inline-block;background:var(--amber-soft);border:1px solid rgba(245,165,36,.35);border-radius:999px;
  padding:3px 11px;font-size:11.5px;color:var(--amber);margin-top:12px;font-family:var(--mono)}

.crumb{color:var(--muted);font-size:13px;margin-bottom:6px;font-family:var(--mono)}
.severity{display:flex;gap:10px;align-items:center;background:var(--amber-soft);
  border:1px solid rgba(245,165,36,.4);color:#ffe0a8;border-radius:12px;padding:11px 14px;font-size:13.5px;margin:8px 0 22px}

.step{background:linear-gradient(180deg,var(--panel),var(--ink2));border:1px solid var(--line);border-radius:16px;
  padding:20px;margin-bottom:14px;transition:.15s}
.step:hover{border-color:var(--line2)}
.step .head{display:flex;gap:14px;align-items:flex-start}
.step .n{width:34px;height:34px;flex:0 0 auto;display:grid;place-items:center;font-weight:800;color:var(--ink);
  background:var(--grad);box-shadow:var(--glow-sm);
  clip-path:polygon(25% 5%,75% 5%,100% 50%,75% 95%,25% 95%,0% 50%)}
.step h3{margin:0;font-size:17px;font-weight:700}
.step p{margin:8px 0 0;color:var(--text)}
.step .why{color:var(--muted);font-size:13.5px}
details{margin-top:14px;border-top:1px dashed var(--line);padding-top:12px}
summary{cursor:pointer;color:var(--amber);font-size:13px;font-family:var(--mono)}
code,.mono{font-family:var(--mono);font-size:12.5px;background:var(--ink2);border:1px solid var(--line);
  border-radius:6px;padding:2px 7px;color:#ffd591;display:inline-block;margin:3px 0}

.callout{background:var(--ink2);border:1px solid var(--line);border-left:3px solid var(--amber);
  border-radius:0 14px 14px 0;padding:16px 18px;margin:20px 0;color:var(--muted);font-size:14px;box-shadow:var(--glow-sm)}
.callout b{color:var(--text)}
.tools{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 4px}
.tool{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px 14px;font-size:13px}
.tool b{color:var(--amber)}

footer{border-top:1px solid var(--line);color:var(--dim);font-size:12.5px;padding:26px;text-align:center;line-height:1.8;margin-top:20px}
footer a{color:var(--amber)}
.top3{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0 22px}
@media(max-width:680px){.top3{grid-template-columns:1fr}.hero h2{font-size:27px}}
.top3 .t{background:linear-gradient(180deg,var(--panel),var(--ink2));border:1px solid var(--line);border-radius:14px;padding:16px;transition:.15s}
.top3 .t:hover{border-color:var(--amber);box-shadow:var(--glow-sm)}
.top3 .t b{display:block;color:var(--amber);margin-bottom:4px;font-family:var(--mono);font-size:13px}
.pillrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.pill{background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 11px;font-size:12px;color:var(--muted);font-family:var(--mono)}

/* ===== Self-hosted font (no render-blocking Google Fonts) =====
   Space Grotesk is a variable font (SIL OFL). One file covers 400-700. */
@font-face{font-family:'Space Grotesk';font-style:normal;font-weight:400 700;font-display:swap;src:url('/dkma-monster/fonts/space-grotesk-latin.woff2') format('woff2')}

/* ===== Accessibility ===== */
.skip-link{position:absolute;left:-999px;top:0;z-index:100;background:var(--amber);color:#0b0b0d;padding:10px 16px;border-radius:0 0 10px 0;font-weight:700}
.skip-link:focus{left:0}
.visually-hidden{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid var(--amber);outline-offset:2px;border-radius:6px}
#main:focus{outline:none}
@media (prefers-reduced-motion: reduce){*,*::before,*::after{animation:none!important;transition:none!important}}

/* ===== Header star link ===== */
.starlink{margin-left:auto;color:var(--amber);font-family:var(--mono);font-size:13px;border:1px solid rgba(245,165,36,.4);padding:5px 12px;border-radius:999px}
.starlink:hover{background:rgba(245,165,36,.14);text-decoration:none}

/* ===== Hero CTAs ===== */
.cta-row{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0 6px}
.cta-row a{min-height:44px;display:inline-flex;align-items:center;padding:11px 18px;border-radius:12px;font-weight:600}
.btn-primary{background:linear-gradient(135deg,var(--amber),var(--amber2));color:#0b0b0d;box-shadow:var(--glow-sm)}
.btn-primary:hover{box-shadow:var(--glow);text-decoration:none}
.btn-ghost{border:1px solid var(--line);color:var(--text)}
.btn-ghost:hover{border-color:var(--amber);text-decoration:none}

/* ===== Share row ===== */
.share{margin-top:22px;color:var(--muted);font-size:14px}
.share a{color:var(--amber);font-family:var(--mono)}
.backtop{display:inline-block;margin-top:14px;color:var(--muted);font-family:var(--mono);font-size:13px}

/* ===== FAQ ===== */
.faq{margin:26px 0}
.faq details{background:linear-gradient(180deg,var(--panel),var(--ink2));border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}
.faq summary{color:var(--text);font-weight:600}

/* ===== Contrast fix: --dim was ~4.0:1 (fails AA) ===== */
:root{--dim:#8f8f9c}
"""

BASE_URL = "https://dlinacre.github.io/dkma-monster"
DEFAULT_DESC = ("DKMA Monster - stop aggressive OEM battery managers from killing "
                "your Android apps. Per-brand keep-alive guides plus automation tools.")

SOFTWARE_APP_LD = {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "DKMA Monster",
    "applicationCategory": "DeveloperApplication",
    "operatingSystem": "Android, Windows, macOS, Linux",
    "description": DEFAULT_DESC,
    "url": "https://dlinacre.github.io/dkma-monster/",
    "codeRepository": "https://github.com/DLinacre/dkma-monster",
    "license": "https://opensource.org/licenses/MIT",
    "softwareVersion": "1.0.0",
    "author": {"@type": "Person", "name": "David Linacre", "url": "https://www.linacre.site/"},
    "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
}
FAQ_LD = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {"@type": "Question", "name": "Why does my phone kill apps in the background?",
         "acceptedAnswer": {"@type": "Answer", "text": "Many Android makers add aggressive, undocumented battery managers that stop background apps. DKMA Monster gives you the exact per-brand settings and automation to prevent it."}},
        {"@type": "Question", "name": "Do I need root?",
         "acceptedAnswer": {"@type": "Answer", "text": "No. Most fixes are guided manual toggles. Root and a Magisk module are offered for fully-automatic, reboot-persistent setup."}},
        {"@type": "Question", "name": "Is it free and open source?",
         "acceptedAnswer": {"@type": "Answer", "text": "Yes - MIT-licensed and fully open source on GitHub."}},
    ],
}

def page(title, body, rel="", desc=DEFAULT_DESC, canonical=None, jsonld=None):
    """Full page with SEO/OG/canonical, self-hosted font, a11y landmarks."""
    canonical = canonical or (BASE_URL + "/")
    og_image = BASE_URL + "/og.png"
    ld = ""
    if jsonld:
        for obj in jsonld:
            ld += ('<script type="application/ld+json">'
                   + json.dumps(obj, ensure_ascii=False) + "</script>\n")
    dot = "\u00b7"; mdash = "\u2014"; star = "\u2b50"
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(desc)}">
<title>{esc(title)}</title>
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="DKMA Monster">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og_image}">
<link rel="icon" href="{rel}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{rel}favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="{rel}apple-touch-icon.png">
<link rel="manifest" href="{rel}manifest.webmanifest">
<meta name="theme-color" content="#0b0b0d">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data: https://img.shields.io https://raw.githubusercontent.com; style-src 'self' 'unsafe-inline'; font-src 'self'; script-src 'self' 'unsafe-inline'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'">
{ld}<style>{CSS}</style>
</head><body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="top">
  <nav aria-label="Primary" style="display:contents">
    <span class="logo" aria-hidden="true">DK</span>
    <h1><a href="{rel}index.html">DKMA Monster</a></h1>
    <a class="starlink" href="https://github.com/DLinacre/dkma-monster" rel="noopener">{star} Star</a>
  </nav>
</header>
<hr class="pulse">
<main id="main" tabindex="-1">
{body}
</main>
<hr class="pulse">
<footer>
  Generated from <code>data/oem_registry.json</code> {mdash} the single source the
  ADB installer, desktop GUI, root script, Magisk module and in-app library share,
  so it can never drift.<br>
  Knowledge distilled from the community at dontkillmyapp.com {dot} Built {date.today().isoformat()}.<br>
  <strong>Built by David Linacre</strong> {dot} <a href="https://www.linacre.site/">linacre.site</a>
</footer>
</body></html>"""

# ---- index page -------------------------------------------------------------
def build_index(reg):
    cards = []
    for o in reg["oems"]:
        nsteps = len(o["steps"])
        brands = ", ".join(sorted(set(o["match"].get("brand", []) or
                                      o["match"].get("manufacturer", []))))
        cards.append(f"""
        <a class="card" href="oem/{esc(o['id'])}.html" data-name="{esc(o['label'].lower())} {esc(brands.lower())}">
          <div class="name">{esc(o['label'])}</div>
          <div class="meta">{esc(brands.title())}</div>
          <span class="badge">{nsteps} step{'s' if nsteps!=1 else ''}</span>
        </a>""")
    ncount = len(reg["oems"])
    body = f"""
    <div class="wrap">
      <div class="hero">
        <div class="kicker">Don't kill my app</div>
        <h2>Stop your phone from <span class="amber">killing your apps</span></h2>
        <p>Aggressive, undocumented OEM battery managers silently kill background
        apps on many Android phones. Pick your brand for exact, tested steps \u2014 or
        automate it all with the DKMA Monster CLI, desktop GUI, or root/Magisk tools.</p>
        <div class="term"><span class="p">$</span> dkma <span class="c"># detect \u00b7 grant \u00b7 guide \u00b7 verify</span></div>
        <div class="cta-row">
          <a class="btn-primary" href="https://github.com/DLinacre/dkma-monster#quick-start">Get the installer \u2192</a>
          <a class="btn-ghost" href="#grid">Find your brand \u2193</a>
        </div>
      </div>
      <div class="top3">
        <div class="t"><b>01 / Autostart ON</b>Let the app start in the background.</div>
        <div class="t"><b>02 / Battery Unrestricted</b>No battery-saver limits.</div>
        <div class="t"><b>03 / Keep running</b>Don't stop after screen off.</div>
      </div>
      <h2 class="visually-hidden">Find your phone brand</h2>
      <label for="q" class="visually-hidden">Search {ncount} supported phone brands</label>
      <input class="search" id="q" type="search" aria-describedby="q-help"
             placeholder="/ search your brand (Xiaomi, Samsung, OPPO\u2026)"
             oninput="filter()" autofocus>
      <p id="q-help" class="visually-hidden">Type a brand name to filter the list below.</p>
      <p id="q-count" class="plabel" role="status" aria-live="polite"></p>
      <div class="grid" id="grid">{''.join(cards)}</div>
      <p id="q-empty" class="muted" style="display:none">No match \u2014 try the
        <a href="oem/generic.html">Generic (stock Android) guide \u2192</a></p>
      <div class="callout">
        <b>Prefer to automate?</b> Run <code>python3 adb/dkma.py com.your.app</code>
        (or the desktop GUI <code>python3 gui/server.py</code>) to grant everything
        possible over ADB and open each screen for you. Root users get full
        automation via <code>root/dkma-root.sh</code> and the Magisk module.
      </div>

      <section class="faq" aria-labelledby="faq-h">
        <h2 id="faq-h">Frequently asked questions</h2>
        <details><summary>Why does my phone kill apps in the background?</summary>
          <p class="why">Many Android makers (Xiaomi, Huawei, OPPO, vivo, Samsung and
          others) add aggressive, undocumented battery managers that stop background
          apps to save power. DKMA Monster gives you the exact per-brand settings and
          automation to prevent it.</p></details>
        <details><summary>Do I need root?</summary>
          <p class="why">No. Most fixes are guided manual toggles. Root and a Magisk
          module are offered for fully-automatic, reboot-persistent setup.</p></details>
        <details><summary>Is it free and open source?</summary>
          <p class="why">Yes \u2014 MIT-licensed and fully open source on GitHub.</p></details>
        <details><summary>Which brands are supported?</summary>
          <p class="why">{ncount} device families plus a generic fallback \u2014 including
          Xiaomi/Redmi/POCO, Samsung, Huawei/Honor, OPPO, vivo, OnePlus, realme and more.</p></details>
      </section>

      <div class="share">Found this useful?
        <a rel="noopener" href="https://twitter.com/intent/tweet?text=Stop%20your%20phone%20killing%20apps%20with%20DKMA%20Monster&url={BASE_URL}/">Share on X</a> \u00b7
        <a rel="noopener" href="https://www.reddit.com/submit?url={BASE_URL}/&title=DKMA%20Monster">Reddit</a> \u00b7
        <a rel="noopener" href="https://github.com/DLinacre/dkma-monster">\u2b50 Star on GitHub</a>
      </div>
    </div>
    <script>
    function filter(){{
      var v=document.getElementById('q').value.toLowerCase();
      var shown=0, cards=document.querySelectorAll('#grid .card');
      cards.forEach(function(c){{
        var ok=c.getAttribute('data-name').indexOf(v)>-1;
        c.style.display = ok ? '' : 'none'; if(ok) shown++;
      }});
      document.getElementById('q-count').textContent = shown + ' of ' + cards.length + ' brands';
      document.getElementById('q-empty').style.display = shown ? 'none' : '';
    }}
    document.addEventListener('keydown',function(e){{
      if(e.key==='/' && document.activeElement.id!=='q'){{
        e.preventDefault(); document.getElementById('q').focus();
      }}
    }});
    // UA-based brand auto-suggest (progressive enhancement)
    (function(){{
      var map=[[/redmi|poco|xiaomi|miui/i,'xiaomi'],[/samsung|sm-/i,'samsung'],
        [/huawei|honor/i,'huawei'],[/oppo|cph/i,'oppo'],[/vivo|iqoo/i,'vivo'],
        [/oneplus/i,'oneplus'],[/realme|rmx/i,'realme'],
        [/tecno|infinix|itel/i,'tecno_infinix_itel'],[/pixel/i,'google'],
        [/moto|motorola|lenovo/i,'motorola'],[/nothing/i,'nothing'],
        [/asus/i,'asus'],[/meizu/i,'meizu'],[/sony|xperia/i,'sony'],[/nokia/i,'nokia']];
      var ua=navigator.userAgent||'', hit=map.find(function(m){{return m[0].test(ua);}});
      if(!hit) return;
      var grid=document.getElementById('grid'); if(!grid) return;
      var a=document.createElement('a'); a.href='oem/'+hit[1]+'.html'; a.className='card';
      a.setAttribute('role','note');
      a.innerHTML='<div class="name">\U0001f4f1 Looks like your phone \u2014 open its guide</div>'+
        '<div class="meta">Auto-detected from your browser \u00b7 tap to continue</div>';
      grid.parentNode.insertBefore(a, grid);
    }})();
    </script>"""
    return page("DKMA Monster \u2014 Keep your Android apps alive", body,
                jsonld=[SOFTWARE_APP_LD, FAQ_LD])

# ---- per-OEM page -----------------------------------------------------------
def component_pretty(comp):
    # "pkg/activity" -> readable
    if "/" in comp:
        pkg, act = comp.split("/", 1)
        return pkg, act
    return comp, ""

def build_oem(reg, o):
    steps_html = []
    for i, s in enumerate(o["steps"], 1):
        title, why = guide(s)
        comps = s.get("components", [])
        used = s.get("use")
        adv = ""
        if comps:
            rows = "".join(
                f"<div><code>{esc(c)}</code></div>" for c in comps)
            adv = f"""<details><summary>Developer: settings screen(s) opened</summary>
                     <div style="margin-top:8px">{rows}
                     <div class="why" style="margin-top:6px">The tools try these in
                     order and fall back to the app's info page.</div></div></details>"""
        elif used:
            adv = f"""<details><summary>Developer: intent used</summary>
                     <div style="margin-top:8px"><code>{esc(used)}</code></div></details>"""
        steps_html.append(f"""
        <div class="step">
          <div class="head"><div class="n">{i}</div>
            <div><h3>{esc(title)}</h3>
            <p class="why">{esc(why)}</p></div>
          </div>
          {adv}
        </div>""")

    brands = ", ".join(sorted(set(
        (o["match"].get("brand", []) + o["match"].get("manufacturer", [])))))
    pills = "".join(f'<span class="pill">{esc(b)}</span>' for b in
                    sorted(set(o["match"].get("brand", []) +
                               o["match"].get("manufacturer", []))))
    body = f"""
    <div class="wrap">
      <div class="crumb"><a href="../index.html">\u2190 All brands</a></div>
      <div class="hero">
        <div class="kicker">Keep-alive guide</div>
        <h2>{esc(o['label'])}</h2>
        <div class="pillrow">{pills}</div>
      </div>
      <div class="severity">\u26a0\ufe0f These settings have no public API \u2014 you set
        them once by hand (or fully automate with root). It takes about a minute.</div>

      {''.join(steps_html)}

      <div class="callout">
        <b>Automate this brand:</b><br>
        <div class="tools">
          <div class="tool"><b>CLI:</b> <code>python3 adb/dkma.py com.your.app</code></div>
          <div class="tool"><b>GUI:</b> <code>python3 gui/server.py</code></div>
          <div class="tool"><b>Root:</b> <code>sh root/dkma-root.sh com.your.app</code></div>
        </div>
        The CLI/GUI grant Doze whitelist, standby bucket and background appops
        automatically, then open each screen above for you to confirm.
      </div>

      <div class="share">Did this fix it?
        <a rel="noopener" href="https://twitter.com/intent/tweet?text=Stopped%20my%20{esc(o['label'])}%20phone%20killing%20apps%20with%20DKMA%20Monster&url={BASE_URL}/oem/{esc(o['id'])}.html">Share on X</a> \u00b7
        <a rel="noopener" href="https://www.reddit.com/submit?url={BASE_URL}/oem/{esc(o['id'])}.html&title=Keep%20apps%20alive%20on%20{esc(o['label'])}">Reddit</a> \u00b7
        <a rel="noopener" href="https://github.com/DLinacre/dkma-monster">\u2b50 Star</a>
      </div>
      <a class="backtop" href="#main">\u2191 Back to top</a>
    </div>"""
    # Per-page description + canonical + HowTo structured data
    step_titles = ", ".join(guide(s)[0] for s in o["steps"][:3])
    desc = (f"Stop {o['label']} from killing your apps in the background. "
            f"Tested keep-alive steps: {step_titles}.")
    canonical = f"{BASE_URL}/oem/{o['id']}.html"
    howto = {
        "@context": "https://schema.org", "@type": "HowTo",
        "name": f"Stop {o['label']} from killing your app in the background",
        "description": desc, "totalTime": "PT2M",
        "step": [{"@type": "HowToStep", "position": i,
                  "name": guide(s)[0], "text": guide(s)[1]}
                 for i, s in enumerate(o["steps"], 1)],
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "All brands", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": o["label"], "item": canonical},
        ],
    }
    return page(f"{o['label']} \u2014 keep apps alive | DKMA Monster", body,
                rel="../", desc=desc, canonical=canonical,
                jsonld=[howto, breadcrumb])

# ---- driver -----------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "site"))
    args = ap.parse_args()

    with open(REGISTRY, encoding="utf-8") as f:
        reg = json.load(f)

    out = args.out
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "oem"), exist_ok=True)

    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_index(reg))

    for o in reg["oems"]:
        with open(os.path.join(out, "oem", f"{o['id']}.html"), "w",
                  encoding="utf-8") as f:
            f.write(build_oem(reg, o))

    write_seo_and_assets(out, reg)

    n = len(reg["oems"])
    print(f"Built site into {out}/  ({n} brand pages + index + SEO assets)")
    return 0


FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    '<polygon points="25,5 75,5 100,50 75,95 25,95 0,50" fill="#f5a524"/>'
    '<polygon points="30,12 70,12 90,50 70,88 30,88 10,50" fill="#0b0b0d"/>'
    '<text x="50" y="63" font-family="monospace" font-size="34" font-weight="bold" '
    'fill="#f5a524" text-anchor="middle">DK</text></svg>'
)

def write_seo_and_assets(out, reg):
    from datetime import date as _date
    today = _date.today().isoformat()
    urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/oem/{o['id']}.html" for o in reg["oems"]]
    items = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{today}</lastmod>"
        f"<changefreq>monthly</changefreq>"
        f"<priority>{'1.0' if u.endswith('/') else '0.8'}</priority></url>"
        for u in urls)
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + items + "\n</urlset>\n")
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n")
    with open(os.path.join(out, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)
    with open(os.path.join(out, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        f.write(json.dumps({
            "name": "DKMA Monster", "short_name": "DKMA",
            "description": DEFAULT_DESC,
            "start_url": "/dkma-monster/", "display": "standalone",
            "background_color": "#0b0b0d", "theme_color": "#0b0b0d",
            "icons": [{"src": "favicon.svg", "sizes": "any", "type": "image/svg+xml"}],
        }, indent=2))
    with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
        f.write(build_404())
    # Copy branded banner as og.png if present in .github/
    banner = os.path.join(HERE, "..", ".github", "banner.png")
    if os.path.exists(banner):
        import shutil as _sh
        _sh.copyfile(banner, os.path.join(out, "og.png"))
    # Copy self-hosted fonts if present in web/fonts/
    fonts_src = os.path.join(HERE, "fonts")
    if os.path.isdir(fonts_src):
        import shutil as _sh
        dst = os.path.join(out, "fonts"); os.makedirs(dst, exist_ok=True)
        for fn in os.listdir(fonts_src):
            _sh.copyfile(os.path.join(fonts_src, fn), os.path.join(dst, fn))
    print("  + robots.txt, sitemap.xml, favicon.svg, manifest, 404.html"
          + (", og.png" if os.path.exists(banner) else "")
          + (", fonts/" if os.path.isdir(fonts_src) else ""))


def build_404():
    return ('<!DOCTYPE html><html lang="en"><head>'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>404 \u2014 DKMA Monster</title><style>'
            "body{margin:0;min-height:100vh;display:grid;place-items:center;text-align:center;"
            "font-family:'Space Grotesk',system-ui,sans-serif;background:#0b0b0d;color:#f4f2ee;"
            "background-image:radial-gradient(900px 400px at 70% -10%,rgba(245,165,36,.12),transparent 60%)}"
            ".h{font-size:72px;margin:0;background:linear-gradient(135deg,#f5a524,#ff8f00);"
            "-webkit-background-clip:text;background-clip:text;color:transparent}"
            "p{color:#9a9aa6} a{color:#f5a524;font-weight:700}</style></head><body><main>"
            '<p class="h">404</p><h1>This page got killed in the background \U0001f9df</h1>'
            "<p>The page you wanted isn't here.</p>"
            '<p><a href="/dkma-monster/">\u2190 Back to DKMA Monster</a></p>'
            "</main></body></html>")

if __name__ == "__main__":
    raise SystemExit(main())
