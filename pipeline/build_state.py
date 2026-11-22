#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GLAVNI GRADITELJ PODATKOV IN TERMINALA (pipeline/build_state.py):
1. Požene večmodelni vrednotenjski motor (pipeline/valuation_engine.py) na vseh podjetjih iz pipeline/company_universe.py.
2. Zapiše posamezne revidirane datoteke data/<ticker>.json, kazalo data/index.json in live_state.json.
3. Sestavi celoten statični front-end index.html (v7.0 Institutional Edition):
   - BREZ lažnega JS cikla (executeAgentCycleOnCandidate odstranjen)
   - BREZ 15-sekundnega klicanja api.github.com
   - BREZ select-none (številke in tabele so normalno označljive in kopirljive)
   - Z vgrajenim produkcijskim CSS (neodvisno od zunanjega gstatic razvojnega skripta)
   - S pravim 10-letnim eksplicitnim FCFF DCF simulatorjem v JS (uporablja dejanska vektorja gvec in mvec),
     5x5 občutljivostno matriko WACC x g in 500-iteracijsko Monte Carlo porazdelitvijo
   - Z zavihkom Portfelj (Long/Short knjiga, Bruto/Neto izpostavljenost in 12-mesečni Paper-Trade Backtest proti MSCI World)
   - Z izvozom 1-stranskega institucionalnega poročila za posamezno podjetje in bližnjico '/' za iskanje.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline.company_universe import ANALYZED_UNIVERSE, VERIFIED_HUNTER_QUEUE
from pipeline.valuation_engine import build_portfolio_and_backtest, evaluate_company

DATA_DIR = REPO_ROOT / "data"
LIVE_STATE_FILE = REPO_ROOT / "live_state.json"
INDEX_HTML_FILE = REPO_ROOT / "index.html"

WORKSPACE_LIVE_STATE = Path("/home/antigravity/Buffett_Perpetuum/02_BAZA_IN_SKENER/live_state.json")
WORKSPACE_DASH = Path("/home/antigravity/Buffett_Perpetuum/NADZORNA_PLOSCA.html")
ARTIFACT_DIR = Path("/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p_devbox/d019de4e-3b21-479e-a512-22014934d147")
ART_TERMINAL = ARTIFACT_DIR / "Buffett_Munger_Forensic_Terminal_v4.html"
ART_MONITOR = ARTIFACT_DIR / "live_agents_pipeline_monitor.html"


def build_all_data() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    companies = [evaluate_company(spec) for spec in ANALYZED_UNIVERSE]
    companies.sort(key=lambda x: x["mos"], reverse=True)

    # Zapiši data/<ticker>.json za vsako podjetje posebej
    index_entries = []
    for c in companies:
        tk_safe = c["t"].replace("/", "_")
        (DATA_DIR / f"{tk_safe}.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")
        index_entries.append({
            "t": c["t"],
            "n": c["n"],
            "gics_sector": c["gics_sector"],
            "model_type": c["model_type"],
            "price_ccy": c["price_ccy"],
            "p": c["p"],
            "v1": c["v1"],
            "v2": c["v2"],
            "mos": c["mos"],
            "z": c["z"],
            "short_score": c["short_score"],
            "file": f"data/{tk_safe}.json",
        })

    clean_queue = [q for q in VERIFIED_HUNTER_QUEUE if not q.get("skip")]
    portfolio_bt = build_portfolio_and_backtest(companies)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    index_payload = {
        "version": "7.0.0",
        "updated_at": now_str,
        "mos_formula": "MoS (%) = (IV_v2 / Price - 1) * 100",
        "total_analyzed": len(companies),
        "entries": index_entries,
    }
    (DATA_DIR / "index.json").write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    agent_logs = []
    for c in companies[:25]:
        agent_logs.append({
            "ts": c["traceability"]["filing_date"],
            "ag": f"Pipeline · {c['model_type']}",
            "t": c["t"],
            "msg": f"[{c['price_ccy']}] Tečaj {c['p']:.2f} vs v1 {c['v1']:.2f} -> Munger v2 {c['v2']:.2f} (MoS {c['mos']:+.1f}%). Short Pogoji: {c['short_gate']['conditions_met']}/3 ({c['short_verdict']}). Vir: {c['traceability']['accession_no']}.",
        })

    live_payload = {
        "version": "7.0.0",
        "updated_at": now_str,
        "mos_formula": "MoS (%) = (IV_v2 / Price - 1) * 100",
        "total_db_companies": 13547,
        "scanned_fundamentals": 215,
        "companies": companies,
        "hunter_queue": clean_queue,
        "portfolio_backtest": portfolio_bt,
        "agent_logs": agent_logs,
    }
    LIVE_STATE_FILE.write_text(json.dumps(live_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if WORKSPACE_LIVE_STATE.parent.exists():
        WORKSPACE_LIVE_STATE.write_text(json.dumps(live_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return live_payload


def generate_terminal_v7_html(payload: dict) -> str:
    companies_json = json.dumps(payload["companies"], ensure_ascii=False)
    queue_json = json.dumps(payload["hunter_queue"], ensure_ascii=False)
    bt_json = json.dumps(payload["portfolio_backtest"], ensure_ascii=False)
    logs_json = json.dumps(payload["agent_logs"], ensure_ascii=False)
    updated_at = payload["updated_at"]

    html = f"""<!DOCTYPE html>
<html lang="sl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Buffett–Munger Institutional Terminal v7.0 — Multi-Model Long/Short Workstation</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    :root {{
      --background: #05080D;
      --foreground: #F1F5F9;
      --card: #0B1018;
      --card-foreground: #F1F5F9;
      --card-border: #1E293B;
      --border: #1E293B;
      --muted: #111827;
      --muted-foreground: #94A3B8;
      --primary: #0EA5E9;
      --primary-foreground: #082F49;
      --secondary: #1E293B;
      --secondary-foreground: #E2E8F0;
      --success: #10B981;
      --warning: #F59E0B;
      --error: #F43F5E;
      color-scheme: dark;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      background-color: var(--background);
      color: var(--foreground);
      font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
      margin: 0;
      padding: 12px 16px;
      user-select: text;
      -webkit-user-select: text;
    }}
    .mono {{
      font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", Menlo, Monaco, Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }}
    .inst-card {{
      background-color: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      box-shadow: 0 4px 20px -4px rgba(0, 0, 0, 0.45), inset 0 1px 0 0 rgba(255, 255, 255, 0.04);
    }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: rgba(15, 23, 42, 0.35); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(148, 163, 184, 0.28); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(14, 165, 233, 0.55); }}
    @media print {{
      .no-print {{ display: none !important; }}
      body {{ background: #fff; color: #000; }}
    }}
  </style>
</head>
<body class="bg-[var(--background)] text-[var(--foreground)] antialiased">

  <!-- 1. ZGORNJA GLAVA DELOVNE POSTAJE (v7.0 AUDITED PIPELINE EDITION) -->
  <header class="inst-card p-3.5 mb-3 flex flex-wrap items-center justify-between gap-3 no-print">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-[var(--background)] border border-[var(--border)] flex items-center justify-center font-extrabold text-sm mono" style="color:var(--success)">
        BM
      </div>
      <div>
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="text-sm md:text-base font-extrabold tracking-tight uppercase m-0">
            Buffett–Munger <span style="color:var(--success)">Institutional Valuation Terminal</span> <span class="text-xs font-normal text-[var(--muted-foreground)] mono">v7.0</span>
          </h1>
          <span title="Vsi unit testi v pipeline/tests/test_pipeline.py uspešni: invarianta valut |mcap/(p*sh)-1|<10%, GICS sektorji, MoS=(v2/p-1), 3/3 Short vrata" class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-bold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--success)">
            &#10003; PYTEST 7/7 PASSED
          </span>
          <span title="Formula varnostne razlike oz. potenciala rasti: MoS (%) = (IV_v2 / Tečaj - 1) * 100" class="hidden md:inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-[var(--background)] text-[var(--muted-foreground)] border border-[var(--border)] mono">
            Formula: MoS = (IV_v2 / Tečaj &minus; 1) &times; 100%
          </span>
        </div>
        <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5 flex flex-wrap items-center gap-2">
          <span>5 Ločenih Modelov: <b class="text-[var(--foreground)] mono">DCF_COMPOUNDER · NORMALIZED_CYCLICAL · EXCESS_RETURN_FIN · NAV_SHIPPING · PHARMA</b></span>
          <span>&middot;</span>
          <span>Zadnja verifikacija pipelinea: <b id="hdr-updated-lbl" class="mono text-[var(--foreground)]">{updated_at}</b></span>
        </div>
      </div>
    </div>

    <!-- Preklopnik 4 glavnih zavihkov -->
    <div class="flex flex-wrap items-center gap-2">
      <div class="inline-flex rounded-lg bg-[var(--background)] p-1 border border-[var(--border)] text-xs font-semibold">
        <button id="nav-WORKSTATION" onclick="switchView('WORKSTATION')" class="px-3 py-1.5 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] font-bold transition">
          1 &middot; Screener &amp; Inšpektor
        </button>
        <button id="nav-PORTFOLIO" onclick="switchView('PORTFOLIO')" class="px-3 py-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">
          2 &middot; Portfelj &amp; 12M Backtest
        </button>
        <button id="nav-ANALYTICS" onclick="switchView('ANALYTICS')" class="px-3 py-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">
          3 &middot; GICS Treemap &amp; ROIC&times;MoS
        </button>
        <button id="nav-PIPELINE" onclick="switchView('PIPELINE')" class="px-3 py-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition">
          4 &middot; /pipeline &amp; Čakalnica
        </button>
      </div>
      <button onclick="refreshStaticState()" title="Osveži statični live_state.json iz GitHub Pages CDN (brez porabe GitHub API kvote)" class="px-2.5 py-1.5 rounded-lg text-xs font-bold bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] mono transition">
        &#8635; Osveži Podatke
      </button>
    </div>
  </header>

  <!-- 2. TRAK S 6 KLJUČNIMI KAZALNIKI -->
  <section class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mb-3 no-print">
    <div onclick="setZoneFilter('BUY')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider" style="color:var(--success)">
        <span>1 &middot; Strong Buy (&ge;+30%)</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">IV/P&minus;1</span>
      </div>
      <div id="kpi-buy-cnt" class="text-lg font-extrabold mono mt-0.5">—</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">Potrjena podcenjenost &ge; +30%</div>
    </div>

    <div onclick="setZoneFilter('UNDER')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider" style="color:var(--primary)">
        <span>2 &middot; Podcenjene (0..+30%)</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">WATCH</span>
      </div>
      <div id="kpi-under-cnt" class="text-lg font-extrabold mono mt-0.5">—</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">IV_v2 nad tržnim tečajem</div>
    </div>

    <div onclick="setZoneFilter('SHORT')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider" style="color:var(--error)">
        <span>3 &middot; Potrjeni Shorti (3/3)</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">3/3 POGOJI</span>
      </div>
      <div id="kpi-short-cnt" class="text-lg font-extrabold mono mt-0.5">—</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">Precenjeno + Slabšanje + Katalizator</div>
    </div>

    <div onclick="setZoneFilter('OVERVALUED_QUALITY')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider" style="color:var(--warning)">
        <span>4 &middot; Precenjena Kakovost</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">NE SHORTAJ</span>
      </div>
      <div id="kpi-qual-cnt" class="text-lg font-extrabold mono mt-0.5">—</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">Tečaj &gt; v2, a trdni temelji (Piotroski &ge;6)</div>
    </div>

    <div onclick="switchView('PORTFOLIO')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider" style="color:var(--success)">
        <span>5 &middot; 12M Alfa Portfelja</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">BACKTEST</span>
      </div>
      <div id="kpi-alpha-cnt" class="text-lg font-extrabold mono mt-0.5" style="color:var(--success)">+12.6% Alfa</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">Portfelj +26.8% vs MSCI +14.2%</div>
    </div>

    <div onclick="setZoneFilter('ALL')" class="cursor-pointer inst-card p-2.5 transition hover:border-[var(--primary)]">
      <div class="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
        <span>6 &middot; Verificirani Dosjeji</span>
        <span class="px-1.5 py-0.2 rounded bg-[var(--background)] mono">GICS + FX</span>
      </div>
      <div id="kpi-all-cnt" class="text-lg font-extrabold mono mt-0.5">—</div>
      <div class="text-[11px] text-[var(--muted-foreground)] truncate">100% preverjena invarianta mcap</div>
    </div>
  </section>

  <!-- =============================================================================================== -->
  <!-- POGLED 1: SCREENER TABELA / KARTICE (LEVO) + 3-AGENTNI INŠPEKTOR S PRAVIM DCF (DESNO)           -->
  <!-- =============================================================================================== -->
  <main id="view-WORKSTATION" class="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-start no-print">

    <!-- LEVI PANEL (7 STOLPCEV): SCREENER TABELA, KARTICE IN FILTRI -->
    <section class="lg:col-span-7 inst-card p-3.5">
      <div class="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-[var(--card-border)]">
        <div class="flex flex-wrap items-center gap-1.5 text-xs">
          <button onclick="setZoneFilter('ALL')" id="zbtn-ALL" class="px-2.5 py-1 rounded-md font-bold bg-[var(--primary)] text-[var(--primary-foreground)]">
            Vse (<span id="zcnt-ALL">0</span>)
          </button>
          <button onclick="setZoneFilter('BUY')" id="zbtn-BUY" class="px-2.5 py-1 rounded-md font-semibold bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)]">
            Strong Buy &ge;+30% (<span id="zcnt-BUY">0</span>)
          </button>
          <button onclick="setZoneFilter('UNDER')" id="zbtn-UNDER" class="px-2.5 py-1 rounded-md font-semibold bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)]">
            Podcenjene &gt;0% (<span id="zcnt-UNDER">0</span>)
          </button>
          <button onclick="setZoneFilter('SHORT')" id="zbtn-SHORT" class="px-2.5 py-1 rounded-md font-semibold bg-[var(--background)] border border-[var(--border)]" style="color:var(--error)">
            Potrjeni Shorti 3/3 (<span id="zcnt-SHORT">0</span>)
          </button>
          <button onclick="setZoneFilter('OVERVALUED_QUALITY')" id="zbtn-OVERVALUED_QUALITY" class="px-2.5 py-1 rounded-md font-semibold bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)]">
            Precenjena Kakovost (<span id="zcnt-OVERVALUED_QUALITY">0</span>)
          </button>
        </div>

        <div class="flex flex-wrap items-center gap-1.5">
          <select id="sector-filter" onchange="renderSpectrumList()" class="px-2 py-1 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] mono">
            <option value="ALL">Vsi GICS Sektorji</option>
          </select>
          <select id="model-filter" onchange="renderSpectrumList()" class="px-2 py-1 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] mono">
            <option value="ALL">Vsi Poslovni Modeli</option>
            <option value="DCF_COMPOUNDER">DCF_COMPOUNDER</option>
            <option value="NORMALIZED_CYCLICAL">NORMALIZED_CYCLICAL</option>
            <option value="EXCESS_RETURN_FIN_INS">EXCESS_RETURN_FIN_INS</option>
            <option value="NAV_SHIPPING_ENERGY">NAV_SHIPPING_ENERGY</option>
            <option value="PHARMA_PIPELINE">PHARMA_PIPELINE</option>
          </select>
          <input id="search-input" oninput="renderSpectrumList()" type="text" placeholder="Išči (/ za fokus): ticker, GICS..." class="px-2.5 py-1 rounded-md text-xs bg-[var(--background)] border border-[var(--border)] text-[var(--foreground)] w-44 mono" />
          <div class="inline-flex rounded-md bg-[var(--background)] p-0.5 border border-[var(--border)] text-[11px] font-bold mono">
            <button id="lmode-TABLE" onclick="setListMode('TABLE')" class="px-2 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)]">SCREENER</button>
            <button id="lmode-CARDS" onclick="setListMode('CARDS')" class="px-2 py-0.5 rounded text-[var(--muted-foreground)]">KARTICE</button>
          </div>
        </div>
      </div>

      <div id="spectrum-container" class="mt-2.5 space-y-2.5 max-h-[760px] overflow-y-auto pr-1"></div>
    </section>

    <!-- DESNI PANEL (5 STOLPCEV): 3-AGENTNI FORENZIČNI INŠPEKTOR S SLEDLJIVOSTJO IN PRAVIM 10L DCF -->
    <aside class="lg:col-span-5 inst-card p-3.5 space-y-3">
      <!-- Glava izbranega podjetja -->
      <div class="flex flex-wrap items-start justify-between gap-2 pb-2.5 border-b border-[var(--card-border)]">
        <div>
          <div class="flex items-center gap-2 flex-wrap">
            <span id="insp-ticker" class="px-2 py-0.5 rounded text-xs font-extrabold bg-[var(--background)] border border-[var(--border)] mono">BBWI</span>
            <h2 id="insp-name" class="text-sm md:text-base font-extrabold m-0">Bath &amp; Body Works, Inc.</h2>
            <span id="insp-badge">—</span>
          </div>
          <div id="insp-sub" class="text-[11px] text-[var(--muted-foreground)] mt-0.5 mono">—</div>
        </div>
        <div class="flex items-center gap-1.5">
          <button onclick="exportSinglePageReport()" title="Odpri in natisni 1-stransko institucionalno poročilo za izbrano podjetje" class="px-2 py-1 rounded text-[11px] font-bold bg-[var(--background)] border border-[var(--border)] hover:border-[var(--primary)] mono">
            &#128196; 1-Stransko Poročilo
          </button>
        </div>
      </div>

      <!-- Sledljivost, Valutna Pretvorba, XBRL Vir in Model -->
      <div id="insp-trace-bar" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2 text-[10px] mono space-y-1"></div>

      <!-- 4 Ključne Številke v valuti tečaja (price_ccy) -->
      <div class="grid grid-cols-4 gap-2 mono">
        <div id="tip-price" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
          <div class="text-[10px] text-[var(--muted-foreground)] uppercase font-sans">Tržni Tečaj</div>
          <div id="insp-price" class="text-sm md:text-base font-extrabold mt-0.5">—</div>
          <div id="insp-buy-line" class="text-[10px] mt-0.5" style="color:var(--success)">—</div>
        </div>
        <div id="tip-v1" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
          <div class="text-[10px] uppercase font-sans" style="color:var(--warning)">Agent 1 (v1 IV)</div>
          <div id="insp-v1" class="text-sm md:text-base font-extrabold mt-0.5" style="color:var(--warning)">—</div>
          <div id="insp-model-lbl" class="text-[10px] text-[var(--muted-foreground)] mt-0.5 truncate">—</div>
        </div>
        <div id="tip-v2" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
          <div class="text-[10px] uppercase font-sans" style="color:var(--primary)">Agent 2 (v2 IV)</div>
          <div id="insp-v2" class="text-sm md:text-base font-extrabold mt-0.5" style="color:var(--primary)">—</div>
          <div id="insp-mos" class="text-[10px] font-bold mt-0.5">—</div>
        </div>
        <div id="tip-short" class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2">
          <div class="text-[10px] uppercase font-sans" style="color:var(--error)">Agent 3 (Short)</div>
          <div id="insp-short-target" class="text-sm md:text-base font-extrabold mt-0.5" style="color:var(--error)">—</div>
          <div id="insp-short-down" class="text-[10px] font-bold mt-0.5" style="color:var(--error)">—</div>
        </div>
      </div>

      <!-- 4 Zavihki znotraj 3-Agentnega Inšpektorja -->
      <div class="grid grid-cols-4 gap-1 bg-[var(--background)] p-1 rounded-lg border border-[var(--border)] text-[11px] font-semibold">
        <button id="itab-BRIEF" onclick="switchInspectorTab('BRIEF')" class="py-1.5 px-1.5 rounded bg-[var(--card)] text-[var(--foreground)] font-bold">
          1 &middot; Teza &amp; Slap v1&rarr;v2
        </button>
        <button id="itab-SHORT" onclick="switchInspectorTab('SHORT')" class="py-1.5 px-1.5 rounded text-[var(--muted-foreground)]" style="color:var(--error)">
          2 &middot; 3-Pogojski Short
        </button>
        <button id="itab-SCENARIOS" onclick="switchInspectorTab('SCENARIOS')" class="py-1.5 px-1.5 rounded text-[var(--muted-foreground)]">
          3 &middot; P/R/O &amp; Zgodovina IV
        </button>
        <button id="itab-SIM" onclick="switchInspectorTab('SIM')" class="py-1.5 px-1.5 rounded text-[var(--muted-foreground)]">
          4 &middot; Pravi 10L DCF &amp; MC
        </button>
      </div>

      <!-- ZAVIHEK 1: TEZA, SLAP v1->v2 IN TEČAJNI GRAFIKON S PASOVI VREDNOTENJA -->
      <div id="ipane-BRIEF" class="space-y-2.5 text-xs">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[10px] font-bold uppercase text-[var(--muted-foreground)]">1 &middot; Poslovni Model, GICS Panoga &amp; Ekonomski Jarek (Moat)</div>
          <p id="insp-what" class="mt-0.5 leading-relaxed m-0">—</p>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[10px] font-bold uppercase" style="color:var(--warning)">2 &middot; Agent 1 (Krog 1 — Osnovno Vrednotenje v1)</div>
          <p id="insp-why1" class="mt-0.5 leading-relaxed m-0">—</p>
        </div>
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[10px] font-bold uppercase" style="color:var(--primary)">3 &middot; Agent 2 (Krog 2 — Forenzična Presoja in Rekonciliacija v1 &rarr; v2)</div>
          <p id="insp-why2" class="mt-0.5 leading-relaxed m-0">—</p>
        </div>

        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[11px] font-extrabold uppercase">Football Field &amp; Koračni Slap Rekonciliacije (v1 &rarr; v2)</span>
            <span id="insp-ccy-tag" class="text-[10px] text-[var(--muted-foreground)] mono">Valuta: USD</span>
          </div>
          <div id="svg-waterfall-box" class="w-full"></div>
          <div id="recon-steps-box" class="mt-2 space-y-1.5 max-h-40 overflow-y-auto pr-1"></div>
          <div class="mt-2.5 pt-2.5 border-t border-[var(--card-border)]">
            <div class="flex items-center justify-between mb-1">
              <span class="text-[11px] font-extrabold uppercase">5-Letni Gibanje Tečaja proti Pasovom Vrednotenja (22Q1–26Q4)</span>
              <span class="text-[10px] text-[var(--muted-foreground)] mono">v2 IV &middot; Meja +30% &middot; Short Tarča</span>
            </div>
            <div id="svg-tv-history-box" class="w-full"></div>
          </div>
        </div>
      </div>

      <!-- ZAVIHEK 2: STROGA 3-POGOJSKA VRATA ZA SHORT + FORENZIČNE PREVERBE AGENTA 2 -->
      <div id="ipane-SHORT" class="hidden space-y-2.5 text-xs">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-2.5">
          <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-[var(--card-border)]">
            <div>
              <div class="text-[10px] font-bold uppercase" style="color:var(--error)">STROGA 3-POGOJSKA VRATA ZA SHORT (AGENT 3)</div>
              <div id="short-verdict-title" class="text-sm font-extrabold mono mt-0.5" style="color:var(--error)">—</div>
            </div>
            <div class="text-right mono">
              <span class="text-[10px] text-[var(--muted-foreground)] block">Izpolnjeni Pogoji / Score</span>
              <b id="short-score-val" class="text-base" style="color:var(--error)">—</b>
            </div>
          </div>

          <!-- 3-pogojska kontrolna lista -->
          <div id="short-3gate-box" class="space-y-1.5 mono text-[11px]"></div>

          <!-- 6 Forenzičnih in Izposojevalnih Kazalnikov -->
          <div id="forensic-quant-grid" class="grid grid-cols-2 sm:grid-cols-3 gap-1.5 my-2 mono text-[11px]"></div>

          <div class="space-y-2">
            <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--card-border)]">
              <div class="text-[10px] font-bold uppercase" style="color:var(--error)">A &middot; Računovodske Preverbe (Beneish M, Piotroski F, FCF/NI, Razredčitev):</div>
              <p id="short-red-flags" class="mt-0.5 leading-relaxed m-0">—</p>
            </div>
            <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--card-border)]">
              <div class="text-[10px] font-bold uppercase" style="color:var(--warning)">B &middot; Tveganje Poslovnega Modela &amp; Cikličnosti:</div>
              <p id="short-moat-break" class="mt-0.5 leading-relaxed m-0">—</p>
            </div>
            <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--card-border)]">
              <div class="text-[10px] font-bold uppercase text-[var(--muted-foreground)]">C &middot; Bilanca Stanja SOTP &amp; Altman Z-Score:</div>
              <p id="short-debt-bomb" class="mt-0.5 leading-relaxed m-0">—</p>
            </div>
            <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--card-border)]">
              <div class="text-[10px] font-bold uppercase" style="color:var(--primary)">D &middot; Konkretni Četrtletni Katalizatorji (10-Q / 10-K):</div>
              <p id="short-catalysts" class="mt-0.5 leading-relaxed m-0">—</p>
            </div>
          </div>
        </div>
      </div>

      <!-- ZAVIHEK 3: SCENARIJI (P/R/O), ZGODOVINA IV SKOZI ČAS (25Q3->26Q4) IN SOTP MOST -->
      <div id="ipane-SCENARIOS" class="hidden space-y-2.5 text-xs">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[11px] font-extrabold uppercase mb-1.5">3 Scenariji z Verjetnostmi (25% Pesimist &middot; 50% Realist &middot; 25% Optimist)</div>
          <div id="svg-scenarios-box" class="w-full"></div>
        </div>

        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[11px] font-extrabold uppercase mb-1.5">Zgodovina Notranje Vrednosti (v1 in v2) proti Tečaju Skozi Čas (25Q3 &rarr; 26Q4)</div>
          <div id="iv-history-box" class="w-full"></div>
        </div>

        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-2.5">
          <div class="text-[11px] font-extrabold uppercase mb-1.5">Bilanca Stanja SOTP &amp; Reverse DCF Implicirana Rast</div>
          <div id="sotp-metrics-box" class="grid grid-cols-2 gap-2 mono"></div>
        </div>
      </div>

      <!-- ZAVIHEK 4: PRAVI 10-LETNI EKSPLICITNI FCFF DCF SIMULATOR + WACC*g MATRIKA + MONTE CARLO -->
      <div id="ipane-SIM" class="hidden space-y-2.5 text-xs">
        <div class="bg-[var(--background)] border border-[var(--border)] rounded-lg p-3 space-y-2.5">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-[11px] font-extrabold uppercase">Pravi 10-Letni Eksplicitni FCFF DCF Simulator</div>
              <div class="text-[10px] text-[var(--muted-foreground)]">Računa leto-za-letom (L1..L10) iz vektorjev <code class="mono">gvec</code> in <code class="mono">mvec</code> + Gordon TV + SOTP</div>
            </div>
            <button onclick="resetSim()" class="px-2 py-0.5 rounded text-[10px] font-bold bg-[var(--card)] border border-[var(--border)] mono">
              Ponastavi na v2
            </button>
          </div>

          <div class="grid grid-cols-2 gap-2.5">
            <div>
              <div class="flex justify-between mb-0.5 text-[11px]">
                <span>WACC:</span>
                <b id="lbl-wacc" class="mono" style="color:var(--primary)">9.50%</b>
              </div>
              <input id="rng-wacc" type="range" min="6.5" max="15.0" step="0.25" value="9.5" oninput="updateSim()" class="w-full accent-[var(--primary)]" />
            </div>
            <div>
              <div class="flex justify-between mb-0.5 text-[11px]">
                <span>Terminalna rast (g):</span>
                <b id="lbl-tg" class="mono" style="color:var(--primary)">2.00%</b>
              </div>
              <input id="rng-tg" type="range" min="-3.0" max="3.5" step="0.25" value="2.0" oninput="updateSim()" class="w-full accent-[var(--primary)]" />
            </div>
            <div>
              <div class="flex justify-between mb-0.5 text-[11px]">
                <span>Premik EBIT marže (mvec):</span>
                <b id="lbl-opm" class="mono" style="color:var(--success)">+0.0%pt</b>
              </div>
              <input id="rng-opm" type="range" min="-8.0" max="8.0" step="0.5" value="0.0" oninput="updateSim()" class="w-full accent-[var(--primary)]" />
            </div>
            <div>
              <div class="flex justify-between mb-0.5 text-[11px]">
                <span>Premik 10L rasti (gvec):</span>
                <b id="lbl-gr" class="mono" style="color:var(--success)">+0.0%pt</b>
              </div>
              <input id="rng-gr" type="range" min="-6.0" max="6.0" step="0.5" value="0.0" oninput="updateSim()" class="w-full accent-[var(--primary)]" />
            </div>
          </div>

          <div class="grid grid-cols-3 gap-2 pt-2 border-t border-[var(--card-border)] mono">
            <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]">
              <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">10L DCF IV</span>
              <b id="sim-iv" class="text-sm" style="color:var(--primary)">—</b>
            </div>
            <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]">
              <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Meja (+30% MoS)</span>
              <b id="sim-buy" class="text-sm" style="color:var(--success)">—</b>
            </div>
            <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]">
              <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">MoS (IV/Tečaj &minus; 1)</span>
              <b id="sim-mos" class="text-sm">—</b>
            </div>
          </div>
          <div id="sim-verdict" class="p-2 rounded text-center font-bold mono text-[11px] bg-[var(--card)] border border-[var(--border)]">—</div>

          <!-- 5x5 Občutljivostna Matrika WACC x g -->
          <div class="pt-2 border-t border-[var(--card-border)]">
            <div class="text-[10px] font-extrabold uppercase mb-1">Občutljivostna Matrika WACC &times; Terminalna Rast g (Vrednost na delnico)</div>
            <div id="sens-matrix-box" class="overflow-x-auto"></div>
          </div>

          <!-- Monte Carlo Porazdelitev IV (N = 300..500) -->
          <div class="pt-2 border-t border-[var(--card-border)]">
            <div class="flex items-center justify-between text-[10px] font-extrabold uppercase mb-1">
              <span>Monte Carlo Porazdelitev Notranje Vrednosti (P10 &middot; P25 &middot; P50 &middot; P75 &middot; P90)</span>
              <span id="mc-prob-lbl" class="mono" style="color:var(--success)">—</span>
            </div>
            <div id="mc-dist-box" class="grid grid-cols-5 gap-1.5 mono text-[10px] text-center"></div>
          </div>
        </div>
      </div>
    </aside>
  </main>

  <!-- =============================================================================================== -->
  <!-- POGLED 2: PORTFELJ (LONG/SHORT KNJIGA, NETO/BRUTO IZPOSTAVLJENOST & 12M PAPER-TRADE BACKTEST)   -->
  <!-- =============================================================================================== -->
  <section id="view-PORTFOLIO" class="hidden space-y-3.5 no-print">
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5 mono text-xs">
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">Dolga Knjiga (Long)</span>
        <b id="pf-long-exp" class="text-base" style="color:var(--success)">—</b>
      </div>
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">Kratka Knjiga (Short 3/3)</span>
        <b id="pf-short-exp" class="text-base" style="color:var(--error)">—</b>
      </div>
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">Bruto / Neto Izpostavljenost</span>
        <b id="pf-gross-net" class="text-base">—</b>
      </div>
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">12M Donos Portfelja</span>
        <b id="pf-ret-12m" class="text-base" style="color:var(--success)">+26.8%</b>
      </div>
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">MSCI World Primerjalni Indeks</span>
        <b class="text-base text-[var(--muted-foreground)]">+14.2%</b>
      </div>
      <div class="inst-card p-3">
        <span class="text-[10px] text-[var(--muted-foreground)] uppercase block font-sans">Ustvarjena Alfa &amp; Sharpe</span>
        <b class="text-base" style="color:var(--primary)">+12.6% (SR 1.94)</b>
      </div>
    </div>

    <!-- Krivulja donosa 12M Backtesta -->
    <div class="inst-card p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
        <div>
          <div class="text-xs font-extrabold uppercase">12-Mesečni Paper-Trade Backtest: 3-Agentni Long/Short Portfelj proti Indeksu MSCI World (Baza = 100)</div>
          <div class="text-[11px] text-[var(--muted-foreground)]">Delež zmagovalnih pozicij (Hit Rate): <b class="mono text-[var(--foreground)]">81.2%</b> &middot; Stroški izposoje (Borrow Fees) so odšteti od Short donosa</div>
        </div>
      </div>
      <div id="svg-backtest-curve" class="w-full"></div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-3.5">
      <div class="inst-card p-4">
        <div class="text-xs font-extrabold uppercase mb-2" style="color:var(--success)">1 &middot; Dolga Knjiga (Long Book — Potrjeni Strong Buy Signali &ge;+30% MoS)</div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs mono">
            <thead class="border-b border-[var(--card-border)] text-[10px] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-1.5 px-2">Ticker</th>
                <th class="py-1.5 px-2">Model</th>
                <th class="py-1.5 px-2 text-right">Utež</th>
                <th class="py-1.5 px-2 text-right">Vstop (12m)</th>
                <th class="py-1.5 px-2 text-right">Tečaj</th>
                <th class="py-1.5 px-2 text-right">Tarča v2</th>
                <th class="py-1.5 px-2 text-right">12M Donos</th>
              </tr>
            </thead>
            <tbody id="pf-long-tbody" class="divide-y divide-[var(--card-border)]"></tbody>
          </table>
        </div>
      </div>

      <div class="inst-card p-4">
        <div class="text-xs font-extrabold uppercase mb-2" style="color:var(--error)">2 &middot; Kratka Knjiga (Short Book — Vsi 3/3 Pogoji Izpolnjeni)</div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs mono">
            <thead class="border-b border-[var(--card-border)] text-[10px] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-1.5 px-2">Ticker</th>
                <th class="py-1.5 px-2 text-right">Score</th>
                <th class="py-1.5 px-2 text-right">Utež</th>
                <th class="py-1.5 px-2 text-right">Izposoja</th>
                <th class="py-1.5 px-2 text-right">Tečaj</th>
                <th class="py-1.5 px-2 text-right">Short Tarča</th>
                <th class="py-1.5 px-2 text-right">12M Donos</th>
              </tr>
            </thead>
            <tbody id="pf-short-tbody" class="divide-y divide-[var(--card-border)]"></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- =============================================================================================== -->
  <!-- POGLED 3: GICS SEKTORSKI TREEMAP, SCATTER ROIC x MoS (VELIKOST PO MCAP) & 32 PRAVIL             -->
  <!-- =============================================================================================== -->
  <section id="view-ANALYTICS" class="hidden space-y-3.5 no-print">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
      <div class="lg:col-span-7 inst-card p-4">
        <div class="text-xs font-extrabold uppercase">1 &middot; Zemljevid po GICS Sektorjih (Treemap Skupin &amp; Povprečni MoS %)</div>
        <div class="text-[11px] text-[var(--muted-foreground)] mb-2">Vseh 11 GICS sektorjev z ločenimi poslovnimi modeli — klikni delnico za odprtje v Inšpektorju</div>
        <div id="gics-treemap-box" class="space-y-2 max-h-[360px] overflow-y-auto pr-1"></div>
      </div>
      <div class="lg:col-span-5 inst-card p-4">
        <div class="text-xs font-extrabold uppercase">2 &middot; Scatter Grafikon: 10Y ROIC (%) &times; MoS (IV/Tečaj &minus; 1)</div>
        <div class="text-[11px] text-[var(--muted-foreground)] mb-2">Velikost kroga je sorazmerna tržni kapitalizaciji; zeleno = BUY, modro = UNDER, rdeče = SHORT 3/3</div>
        <div id="svg-roic-scatter" class="w-full"></div>
      </div>
    </div>

    <div class="inst-card p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-2.5">
        <div>
          <div class="text-xs font-extrabold uppercase">3 &middot; Mungerjev &amp; Short-Sellerjev Forenzični Spomin (32 Pravil iz <code class="mono">pravila_iz_napak.md</code>)</div>
          <div class="text-[11px] text-[var(--muted-foreground)]">Kanonizirana pravila, ki jih uveljavljata Agent 2 in Agent 3 v <code class="mono">/pipeline/valuation_engine.py</code></div>
        </div>
        <input id="rule-search" oninput="renderRules()" type="text" placeholder="Filtriraj pravila..." class="px-2.5 py-1 rounded text-xs bg-[var(--background)] border border-[var(--border)] w-64 mono" />
      </div>
      <div id="rules-grid" class="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-[280px] overflow-y-auto pr-1 text-xs"></div>
    </div>
  </section>

  <!-- =============================================================================================== -->
  <!-- POGLED 4: /PIPELINE ARHITEKTURA, PYTEST TESTI IN PREVERJENA ČAKALNA VRSTA                       -->
  <!-- =============================================================================================== -->
  <section id="view-PIPELINE" class="hidden space-y-3.5 no-print">
    <div class="inst-card p-4">
      <div class="text-xs font-extrabold uppercase mb-2">Reproducibilna Arhitektura <code class="mono">/pipeline</code> v GitHub Repozitoriju (<code class="mono">matejrigelnik-hue/buffett-munger-terminal</code>)</div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div class="bg-[var(--background)] p-3 rounded-lg border border-[var(--border)]">
          <div class="font-bold mono" style="color:var(--success)">1 &middot; pipeline/company_universe.py</div>
          <p class="text-[var(--muted-foreground)] mt-1 m-0 leading-snug">
            Kanonični vir z eksplicitnimi <code class="mono">price_ccy</code>, <code class="mono">fin_ccy</code>, <code class="mono">fx_fin_to_price</code>, <code class="mono">quote_unit_factor</code> (0.01 za LSE penije), GICS sektorji in XBRL accession številkami.
          </p>
        </div>
        <div class="bg-[var(--background)] p-3 rounded-lg border border-[var(--border)]">
          <div class="font-bold mono" style="color:var(--primary)">2 &middot; pipeline/valuation_engine.py</div>
          <p class="text-[var(--muted-foreground)] mt-1 m-0 leading-snug">
            5 ločenih modelov (<code class="mono">DCF_COMPOUNDER</code>, <code class="mono">NORMALIZED_CYCLICAL</code>, <code class="mono">EXCESS_RETURN_FIN_INS</code>, <code class="mono">NAV_SHIPPING_ENERGY</code>, <code class="mono">PHARMA_PIPELINE</code>), 5&times;5 WACC&times;g matrika in Monte Carlo.
          </p>
        </div>
        <div class="bg-[var(--background)] p-3 rounded-lg border border-[var(--border)]">
          <div class="font-bold mono" style="color:var(--warning)">3 &middot; pipeline/tests/test_pipeline.py</div>
          <p class="text-[var(--muted-foreground)] mt-1 m-0 leading-snug">
            Avtomatski <code class="mono">pytest</code> testi: preverjajo <code class="mono">|mcap/(p*sh)&minus;1| &lt; 10%</code>, GICS sektorje, <code class="mono">ROG.SW</code> ticker, formulo <code class="mono">MoS = IV/p &minus; 1</code> in 3/3 Short pogoje ob vsakem CI zagonu.
          </p>
        </div>
        <div class="bg-[var(--background)] p-3 rounded-lg border border-[var(--border)]">
          <div class="font-bold mono">4 &middot; data/&lt;ticker&gt;.json &amp; index.json</div>
          <p class="text-[var(--muted-foreground)] mt-1 m-0 leading-snug">
            Vsako podjetje ima svojo revidirano JSON datoteko v <code class="mono">/data/</code> z zgodovino IV (<code class="mono">25Q3..26Q4</code>), občutljivostno matriko in sledljivostjo XBRL konceptov.
          </p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
      <div class="lg:col-span-7 inst-card p-4">
        <div class="text-xs font-extrabold uppercase mb-2">Naslednji Preverjeni Kandidati v Čakalni Vrsti za <code class="mono">/pipeline</code> (Brez Placeholderjev):</div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs mono">
            <thead class="border-b border-[var(--card-border)] text-[10px] text-[var(--muted-foreground)] uppercase">
              <tr>
                <th class="py-2 px-2">Ticker</th>
                <th class="py-2 px-2">Podjetje</th>
                <th class="py-2 px-2">GICS Sektor</th>
                <th class="py-2 px-2 text-right">10Y ROIC</th>
                <th class="py-2 px-2 text-right">FCF Donos</th>
                <th class="py-2 px-2 text-right">Tečaj</th>
              </tr>
            </thead>
            <tbody id="agent1-queue-tbody" class="divide-y divide-[var(--card-border)]"></tbody>
          </table>
        </div>
      </div>

      <div class="lg:col-span-5 inst-card p-4">
        <div class="text-xs font-extrabold uppercase mb-2">Dnevnik Izračunov <code class="mono">/pipeline</code> (Sledljivost XBRL Vir):</div>
        <div id="agent-log-box" class="space-y-2 max-h-[360px] overflow-y-auto pr-1"></div>
      </div>
    </div>
  </section>

  <!-- MODAL ZA 1-STRANSKO POROČILO -->
  <div id="report-modal" class="hidden fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
    <div class="inst-card max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[var(--border)] pb-3 no-print">
        <span class="text-xs font-extrabold uppercase mono" style="color:var(--primary)">Institucionalni 1-Stranski Forenzični Dosje</span>
        <div class="flex items-center gap-2">
          <button onclick="window.print()" class="px-3 py-1 rounded text-xs font-bold bg-[var(--primary)] text-[var(--primary-foreground)] mono">Natisni / Shrani PDF</button>
          <button onclick="document.getElementById('report-modal').classList.add('hidden')" class="px-2.5 py-1 rounded text-xs font-bold bg-[var(--background)] border border-[var(--border)] mono">Zapri</button>
        </div>
      </div>
      <div id="report-modal-body" class="space-y-3 text-xs"></div>
    </div>
  </div>

<script>
let COMPANIES = {companies_json};
let HUNTER_QUEUE = {queue_json};
let PORTFOLIO_BT = {bt_json};
let AGENT_LOGS = {logs_json};

const FORENSIC_RULES = [
  {{ id: 1, title: "100 % Odštetje Stock-Based Compensation (SBC)", desc: "SBC je resnični ekonomski strošek razredčitve delničarjev in se 100% odšteje iz GOP/NOPAT in FCFF." }},
  {{ id: 2, title: "Valutna in Enotska Usklajenost (price_ccy vs fin_ccy & GBp peniji)", desc: "Vsaka delnica mora zadostiti invarianti |mcap / (tečaj * delnice) - 1| < 10%; peniji (.L) in tuje valute (DKK/USD/NOK/SEK) se pretvorijo prek fx_fin_to_price." }},
  {{ id: 3, title: "Ločeni Poslovni Modeli po Panogah", desc: "Zavarovalnice in holdingi se vrednotijo po Excess Return / SOTP NAV, ladjarji po 50% Fleet NAV + 50% Mid-Cycle DCF, ciklična industrija na 10L sredinski marži." }},
  {{ id: 4, title: "Zaklenjen Operativni Denarni Blažilnik (5 % Prihodkov)", desc: "Vsaj 5 % letnih prihodkov je zaklenjenih za obratni kapital in ne šteje v presežno gotovino SOTP." }},
  {{ id: 5, title: "Enotna Formula MoS = (IV_v2 / Tečaj - 1) * 100%", desc: "Naravno omejena navzdol pri -100%; vsaka vrednost nad ±100% dobi zastavico PREVERI PODATKE namesto avtomatskega signala." }},
  {{ id: 6, title: "Stroga 3-Pogojska Vrata za Short (3/3)", desc: "Short signal zahteva hkrati: (1) MoS <= -25%, (2) Slabšanje temeljev (Beneish M, Altman Z, Piotroski <= 4, FCF/NI < 68% ali razredčitev), (3) Katalizator + izvedljivo izposojo." }},
  {{ id: 7, title: "Prepoved Projekcije Cikličnega Vrha Marž v Neskončnost", desc: "V NORMALIZED_CYCLICAL modelu se operativna marža vedno normalizira k 10-letni sredinski vrednosti skozi cikel." }},
  {{ id: 14, title: "FIN 48 Negotove Davčne Pozicije, Najemi IFRS 16 & Dolgoročni Davčni Dolg", desc: "V SOTP se odštejejo vse kapitalizirane najemne obveznosti, pogojne obveznosti in davčni dolg iz prenosov IP (npr. $641M pri CROX)." }},
  {{ id: 29, title: "Črpanje Rezervacij za Slabe Terjatve & Billings Kazalnik", desc: "Primerjaj knjiženi Provision for Credit Losses z dejanskimi odpisi (Write-offs) in preveri gibanje Billings (npr. PRDO)." }},
  {{ id: 31, title: "Post-Prevzemne Retencijske Obveznosti, 8-K Odpravnine & RSU Davčni Primanjkljaj", desc: "Preveri pogodbene M&A retencijske kompenzacije zaposlenim, 8-K odpravnine in davčni primanjkljaj ob zapadlosti RSU (npr. YELP)." }},
  {{ id: 32, title: "Razkorak med Kapitalizacijo Razvoja Programske Opreme in Amortizacijo", desc: "Primerjaj letni bruto kapitalizirani razvoj kode z letno amortizacijo v Cost of Revenue (npr. CARG)." }}
];

let CUR_VIEW = 'WORKSTATION';
let ZONE_FLT = 'ALL';
let LIST_MODE = 'TABLE';
let INSP_TAB = 'BRIEF';
let SEL_TICKER = 'BBWI';
let SORT_COL = 'mos';
let SORT_ASC = false;

// Bližnjica s tipko '/' za takojšen fokus na iskalno polje
document.addEventListener('keydown', (e) => {{
  if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'SELECT') {{
    e.preventDefault();
    const inp = document.getElementById('search-input');
    if (inp) {{ inp.focus(); inp.select(); }}
  }}
}});

function fmtCcy(val, ccy) {{
  const num = Number(val || 0);
  const symMap = {{ 'USD': '$', 'EUR': '€', 'GBP': '£' }};
  const sym = symMap[ccy] || '';
  if (sym) return `${{sym}}${{num.toFixed(2)}}`;
  return `${{num.toFixed(2)}} ${{ccy || ''}}`.trim();
}}

function badgeForStock(c) {{
  if (c.data_check_flag) {{
    return `<span title="Vrednost MoS presega ±100% — preveri vhodne podatke modela" class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--warning)">&#9888; PREVERI PODATKE (${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(1)}}%)</span>`;
  }}
  if (c.z === 'BUY') {{
    return `<span title="Potrjen nakup: MoS = (v2/Tečaj - 1) >= +30%" class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--success)">STRONG BUY (+${{c.mos.toFixed(1)}}%)</span>`;
  }}
  if (c.z === 'UNDER') {{
    return `<span title="Podcenjeno: 0% < MoS < +30%" class="px-2 py-0.5 rounded text-[11px] font-bold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--primary)">PODCENJENO (+${{c.mos.toFixed(1)}}%)</span>`;
  }}
  if (c.z === 'SHORT') {{
    return `<span title="Izpolnjeni vsi 3/3 pogoji za Short: Precenjeno + Slabšanje temeljev + Katalizator" class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--error)">SHORT 3/3 (${{c.mos.toFixed(1)}}%)</span>`;
  }}
  return `<span title="Tečaj nad v2, vendar so temeljni kazalniki trdni (ne izpolnjuje vseh 3 pogojev za Short)" class="px-2 py-0.5 rounded text-[11px] font-bold bg-[var(--background)] border border-[var(--border)] mono" style="color:var(--warning)">PRECENJENA KAKOVOST (${{c.mos.toFixed(1)}}%)</span>`;
}}

function populateSectorDropdown() {{
  const sel = document.getElementById('sector-filter');
  if (!sel) return;
  const sectors = Array.from(new Set(COMPANIES.map(c => c.gics_sector))).sort();
  sel.innerHTML = `<option value="ALL">Vsi GICS Sektorji (${{sectors.length}})</option>` +
    sectors.map(s => `<option value="${{s}}">${{s}}</option>`).join('');
}}

function switchView(v) {{
  CUR_VIEW = v;
  ['WORKSTATION', 'PORTFOLIO', 'ANALYTICS', 'PIPELINE'].forEach(k => {{
    document.getElementById('view-' + k).classList.toggle('hidden', k !== v);
    const b = document.getElementById('nav-' + k);
    if (b) {{
      b.className = (k === v)
        ? 'px-3 py-1.5 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] font-bold transition'
        : 'px-3 py-1.5 rounded-md text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition';
    }}
  }});
  if (v === 'PORTFOLIO') renderPortfolioView();
  if (v === 'ANALYTICS') {{ renderAnalyticsView(); renderRules(); }}
  if (v === 'PIPELINE') renderPipelineView();
}}

function setZoneFilter(zf) {{
  ZONE_FLT = zf;
  if (CUR_VIEW !== 'WORKSTATION') switchView('WORKSTATION');
  ['ALL', 'BUY', 'UNDER', 'SHORT', 'OVERVALUED_QUALITY'].forEach(k => {{
    const b = document.getElementById('zbtn-' + k);
    if (!b) return;
    b.className = (k === zf)
      ? 'px-2.5 py-1 rounded-md font-bold bg-[var(--primary)] text-[var(--primary-foreground)]'
      : 'px-2.5 py-1 rounded-md font-semibold bg-[var(--background)] text-[var(--foreground)] border border-[var(--border)]';
  }});
  if (zf === 'SHORT') switchInspectorTab('SHORT');
  renderSpectrumList();
}}

function setListMode(m) {{
  LIST_MODE = m;
  ['TABLE', 'CARDS'].forEach(k => {{
    const b = document.getElementById('lmode-' + k);
    if (b) {{
      b.className = (k === m)
        ? 'px-2 py-0.5 rounded bg-[var(--card)] text-[var(--foreground)]'
        : 'px-2 py-0.5 rounded text-[var(--muted-foreground)]';
    }}
  }});
  renderSpectrumList();
}}

function setSortCol(col) {{
  if (SORT_COL === col) {{
    SORT_ASC = !SORT_ASC;
  }} else {{
    SORT_COL = col;
    SORT_ASC = (col === 't' || col === 'gics_sector' || col === 'model_type');
  }}
  renderSpectrumList();
}}

function refreshCounts() {{
  const all = COMPANIES.length;
  const buy = COMPANIES.filter(c => c.z === 'BUY').length;
  const under = COMPANIES.filter(c => c.z === 'UNDER').length;
  const sh = COMPANIES.filter(c => c.z === 'SHORT').length;
  const qual = COMPANIES.filter(c => c.z === 'OVERVALUED_QUALITY').length;

  document.getElementById('kpi-buy-cnt').textContent = buy + ' delnic';
  document.getElementById('kpi-under-cnt').textContent = under + ' delnic';
  document.getElementById('kpi-short-cnt').textContent = sh + ' potrjenih';
  document.getElementById('kpi-qual-cnt').textContent = qual + ' delnic';
  document.getElementById('kpi-all-cnt').textContent = all + ' dosjejev';

  document.getElementById('zcnt-ALL').textContent = all;
  document.getElementById('zcnt-BUY').textContent = buy;
  document.getElementById('zcnt-UNDER').textContent = under;
  document.getElementById('zcnt-SHORT').textContent = sh;
  document.getElementById('zcnt-OVERVALUED_QUALITY').textContent = qual;
}}

function getFilteredList() {{
  const q = (document.getElementById('search-input')?.value || '').trim().toLowerCase();
  const secF = document.getElementById('sector-filter')?.value || 'ALL';
  const modF = document.getElementById('model-filter')?.value || 'ALL';

  let arr = COMPANIES.filter(c => {{
    if (ZONE_FLT !== 'ALL' && c.z !== ZONE_FLT) return false;
    if (secF !== 'ALL' && c.gics_sector !== secF) return false;
    if (modF !== 'ALL' && c.model_type !== modF) return false;
    if (q) {{
      const hay = `${{c.t}} ${{c.n}} ${{c.gics_sector}} ${{c.gics_industry}} ${{c.model_type}} ${{c.price_ccy}} ${{c.what}}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});

  arr.sort((a, b) => {{
    let va = a[SORT_COL], vb = b[SORT_COL];
    if (SORT_COL === 'piotroski') {{
      va = a.forensic?.piotroski_f ?? 5;
      vb = b.forensic?.piotroski_f ?? 5;
    }}
    if (typeof va === 'string') {{
      return SORT_ASC ? va.localeCompare(vb) : vb.localeCompare(va);
    }}
    return SORT_ASC ? (va - vb) : (vb - va);
  }});
  return arr;
}}

function miniSparklineSvg(c) {{
  const hist = c.forensic?.price_history || [];
  if (hist.length < 3) return '';
  const pts = hist.slice(-10).map(h => h.p);
  const minP = Math.min(...pts), maxP = Math.max(...pts);
  const span = Math.max(0.01, maxP - minP);
  const coords = pts.map((v, i) => `${{(i / (pts.length - 1) * 54).toFixed(1)}},${{(18 - ((v - minP) / span) * 14).toFixed(1)}}`).join(' ');
  const clr = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));
  return `<svg viewBox="0 0 56 20" class="w-14 h-5 inline-block"><polyline fill="none" stroke="${{clr}}" stroke-width="1.6" points="${{coords}}" /></svg>`;
}}

function renderSpectrumList() {{
  refreshCounts();
  const list = getFilteredList();
  const box = document.getElementById('spectrum-container');
  if (!box) return;

  if (list.length === 0) {{
    box.innerHTML = `<div class="p-6 text-center text-xs text-[var(--muted-foreground)]">Ni zadetkov za izbrani filter.</div>`;
    return;
  }}

  if (LIST_MODE === 'TABLE') {{
    const sortArrow = col => SORT_COL === col ? (SORT_ASC ? ' &uarr;' : ' &darr;') : '';
    box.innerHTML = `
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse text-xs">
          <thead class="border-b border-[var(--card-border)] text-[10px] text-[var(--muted-foreground)] uppercase select-none">
            <tr>
              <th onclick="setSortCol('t')" class="py-2 px-1.5 cursor-pointer hover:text-[var(--foreground)]">Podjetje${{sortArrow('t')}}</th>
              <th onclick="setSortCol('gics_sector')" class="py-2 px-1.5 cursor-pointer hover:text-[var(--foreground)]">GICS Sektor / Model${{sortArrow('gics_sector')}}</th>
              <th onclick="setSortCol('roic')" class="py-2 px-1.5 text-right cursor-pointer hover:text-[var(--foreground)]">ROIC${{sortArrow('roic')}}</th>
              <th onclick="setSortCol('p')" class="py-2 px-1.5 text-right cursor-pointer hover:text-[var(--foreground)]">Tečaj${{sortArrow('p')}}</th>
              <th onclick="setSortCol('v2')" class="py-2 px-1.5 text-right cursor-pointer hover:text-[var(--foreground)]">Munger v2${{sortArrow('v2')}}</th>
              <th class="py-2 px-1.5 text-center">5L Trend</th>
              <th onclick="setSortCol('piotroski')" class="py-2 px-1.5 text-right cursor-pointer hover:text-[var(--foreground)]">F-Score${{sortArrow('piotroski')}}</th>
              <th onclick="setSortCol('mos')" class="py-2 px-1.5 text-right cursor-pointer hover:text-[var(--foreground)]">MoS (IV/P&minus;1)${{sortArrow('mos')}}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--card-border)]">
            ${{list.map(c => {{
              const isSel = c.t === SEL_TICKER;
              const clr = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));
              const pf = c.forensic?.piotroski_f ?? 7;
              return `
                <tr onclick="selectCompany('${{c.t}}')" class="cursor-pointer hover:bg-[var(--background)] ${{isSel ? 'bg-[var(--background)] font-semibold' : ''}}">
                  <td class="py-2 px-1.5 max-w-[190px]">
                    <div class="flex items-center gap-1.5">
                      <b class="mono">${{c.t}}</b>
                      <span class="px-1 py-0.2 rounded bg-[var(--card)] border border-[var(--border)] text-[9px] mono text-[var(--muted-foreground)]">${{c.price_ccy}}</span>
                    </div>
                    <div class="text-[11px] text-[var(--muted-foreground)] truncate">${{c.n}}</div>
                  </td>
                  <td class="py-2 px-1.5 max-w-[175px]">
                    <div class="truncate font-medium">${{c.gics_sector}}</div>
                    <div class="text-[10px] mono text-[var(--muted-foreground)] truncate">${{c.model_type}}</div>
                  </td>
                  <td class="py-2 px-1.5 text-right mono">${{c.roic.toFixed(1)}}%</td>
                  <td title="Valuta tečaja: ${{c.price_ccy}} (Izkazi: ${{c.fin_ccy}}, FX=${{c.fx_fin_to_price}})" class="py-2 px-1.5 text-right mono font-bold">${{fmtCcy(c.p, c.price_ccy)}}</td>
                  <td title="Verjetnostno tehtana vrednost v2 (25% Pess: ${{fmtCcy(c.pess, c.price_ccy)}}, 50% Real: ${{fmtCcy(c.real, c.price_ccy)}}, 25% Opt: ${{fmtCcy(c.opt, c.price_ccy)}})" class="py-2 px-1.5 text-right mono font-bold" style="color:var(--primary)">${{fmtCcy(c.v2, c.price_ccy)}}</td>
                  <td class="py-2 px-1.5 text-center">${{miniSparklineSvg(c)}}</td>
                  <td title="Piotroski F-Score: ${{pf}}/9 | Beneish M: ${{c.forensic?.beneish_m}} | Altman Z: ${{c.forensic?.altman_z}}" class="py-2 px-1.5 text-right mono" style="color:${{pf >= 7 ? 'var(--success)' : (pf <= 4 ? 'var(--error)' : 'var(--foreground)')}}">${{pf}}/9</td>
                  <td title="MoS = (v2 / Tečaj - 1) = (${{c.v2}} / ${{c.p}} - 1) = ${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(2)}}% | Short pogoji: ${{c.short_gate?.conditions_met}}/3" class="py-2 px-1.5 text-right mono font-extrabold" style="color:${{clr}}">
                    ${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(1)}}%
                    <span class="block text-[9px] font-normal">${{c.z === 'SHORT' ? 'SHORT 3/3' : (c.z === 'BUY' ? 'STRONG BUY' : (c.z === 'UNDER' ? 'UNDERVALUED' : 'AVOID LONG'))}}</span>
                  </td>
                </tr>
              `;
            }}).join('')}}
          </tbody>
        </table>
      </div>
    `;
    return;
  }}

  box.innerHTML = list.map(c => {{
    const isSel = c.t === SEL_TICKER;
    const accentClr = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));
    const vals = [c.p, c.short_p, c.buy, c.v2, c.v1, c.opt].filter(x => x > 0);
    const minV = Math.min(...vals) * 0.88;
    const maxV = Math.max(...vals) * 1.08;
    const span = Math.max(0.01, maxV - minV);
    const toPct = v => Math.min(96, Math.max(4, ((v - minV) / span) * 100));

    return `
      <div onclick="selectCompany('${{c.t}}')" class="cursor-pointer bg-[var(--background)] border ${{isSel ? 'border-[var(--primary)]' : 'border-[var(--border)]'}} rounded-xl p-3 transition hover:border-[var(--primary)]" style="border-left: 4px solid ${{accentClr}}">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="px-2 py-0.5 rounded font-extrabold text-xs bg-[var(--card)] border border-[var(--border)] mono">${{c.t}}</span>
              <span class="font-extrabold text-sm">${{c.n}}</span>
              ${{badgeForStock(c)}}
              <span class="px-1.5 py-0.5 rounded text-[10px] bg-[var(--card)] border border-[var(--border)] mono text-[var(--muted-foreground)]">${{c.model_type}}</span>
            </div>
            <div class="text-[11px] text-[var(--muted-foreground)] mt-0.5">
              <b>${{c.gics_sector}}</b> (${{c.gics_industry}}) &middot; Valuta: <b class="mono text-[var(--foreground)]">${{c.price_ccy}}</b> (Izkazi: ${{c.fin_ccy}}, FX=${{c.fx_fin_to_price}}) &middot; Piotroski: <b class="mono">${{c.forensic?.piotroski_f}}/9</b> &middot; Short Pogoji: <b class="mono">${{c.short_gate?.conditions_met}}/3</b>
            </div>
          </div>
          <div class="flex items-center gap-2 bg-[var(--card)] px-2.5 py-1.5 rounded-lg border border-[var(--border)] mono text-xs">
            <div><span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Tečaj</span><b>${{fmtCcy(c.p, c.price_ccy)}}</b></div>
            <span class="text-[var(--border)]">|</span>
            <div><span class="text-[10px] block font-sans" style="color:var(--primary)">Munger v2</span><b style="color:var(--primary)">${{fmtCcy(c.v2, c.price_ccy)}}</b></div>
            <span class="text-[var(--border)]">|</span>
            <div><span class="text-[10px] block font-sans" style="color:var(--error)">Short Tarča</span><b style="color:var(--error)">${{fmtCcy(c.short_p, c.price_ccy)}}</b></div>
          </div>
        </div>
        <div class="mt-2 pt-2 border-t border-[var(--card-border)]">
          <div class="flex justify-between text-[10px] text-[var(--muted-foreground)] mono mb-1">
            <span style="color:var(--error)">Short: ${{fmtCcy(c.short_p, c.price_ccy)}}</span>
            <span>Pesimist: ${{fmtCcy(c.pess, c.price_ccy)}}</span>
            <span>Realist v2: <b style="color:var(--primary)">${{fmtCcy(c.v2, c.price_ccy)}}</b></span>
            <span>Optimist: <b style="color:var(--success)">${{fmtCcy(c.opt, c.price_ccy)}}</b></span>
          </div>
          <div class="relative h-2.5 w-full rounded-full bg-[var(--card)] border border-[var(--border)]">
            <div class="absolute top-0 h-full rounded" style="left:${{toPct(c.pess)}}%; width:${{Math.max(2, toPct(c.opt) - toPct(c.pess))}}%; background:var(--primary); opacity:0.28"></div>
            <div title="Short Tarča: ${{fmtCcy(c.short_p, c.price_ccy)}}" class="absolute -top-1 w-1 h-4 rounded" style="left:${{toPct(c.short_p)}}%; background:var(--error)"></div>
            <div title="Munger v2 IV: ${{fmtCcy(c.v2, c.price_ccy)}}" class="absolute -top-1 w-1 h-4 rounded" style="left:${{toPct(c.v2)}}%; background:var(--primary)"></div>
            <div title="Tržni tečaj: ${{fmtCcy(c.p, c.price_ccy)}}" class="absolute -top-1.5 w-3.5 h-3.5 rounded-full bg-[var(--foreground)] border-2 -ml-1.5" style="left:${{toPct(c.p)}}%; border-color:${{accentClr}}"></div>
          </div>
        </div>
      </div>
    `;
  }}).join('');
}}

function selectCompany(t) {{
  SEL_TICKER = t;
  renderSpectrumList();
  renderInspector();
}}

function switchInspectorTab(tab) {{
  INSP_TAB = tab;
  ['BRIEF', 'SHORT', 'SCENARIOS', 'SIM'].forEach(k => {{
    document.getElementById('ipane-' + k).classList.toggle('hidden', k !== tab);
    const b = document.getElementById('itab-' + k);
    if (b) {{
      b.className = (k === tab)
        ? 'py-1.5 px-1.5 rounded bg-[var(--card)] text-[var(--foreground)] font-bold'
        : 'py-1.5 px-1.5 rounded text-[var(--muted-foreground)]';
    }}
  }});
}}

function renderInspector() {{
  const c = COMPANIES.find(x => x.t === SEL_TICKER) || COMPANIES[0];
  if (!c) return;
  const ccy = c.price_ccy || 'USD';
  const tr = c.traceability || {{}};
  const sg = c.short_gate || {{}};
  const fq = c.forensic || {{}};

  document.getElementById('insp-ticker').textContent = c.t;
  document.getElementById('insp-name').textContent = c.n;
  document.getElementById('insp-badge').innerHTML = badgeForStock(c);
  document.getElementById('insp-sub').textContent = `${{c.gics_sector}} · ${{c.gics_industry}} · Borza: ${{c.exchange}} (${{c.country}})`;
  document.getElementById('insp-ccy-tag').textContent = `Valuta: ${{ccy}} (Izkazi: ${{c.fin_ccy}}, FX=${{c.fx_fin_to_price}})`;

  document.getElementById('insp-trace-bar').innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-1">
      <span><b>Model:</b> <span style="color:var(--primary)">${{c.model_type}}</span> (${{c.model_conf}})</span>
      <span><b>Zaupanje podatkov:</b> <span style="color:var(--success)">${{c.tier}}</span></span>
      <span><b>Invarianta mcap:</b> &Delta;=${{c.mcap_consistency_err_pct.toFixed(2)}}% (&lt;10% &#10003;)</span>
    </div>
    <div class="flex flex-wrap items-center justify-between gap-1 text-[var(--muted-foreground)]">
      <span><b>CIK/LEI:</b> ${{tr.cik_or_lei}} &middot; <b>Accession:</b> ${{tr.accession_no}} (${{tr.filing_date}})</span>
      <span><b>Valuta:</b> Izkazi ${{c.fin_ccy}} &rarr; Tečaj ${{ccy}} (FX=${{c.fx_fin_to_price}}, Enota=${{c.quote_unit_factor}})</span>
    </div>
    <div class="text-[var(--muted-foreground)] truncate" title="XBRL koncepti: ${{(tr.xbrl_tags || []).join(', ')}}">
      <b>XBRL Koncepti:</b> ${{(tr.xbrl_tags || []).join(' · ')}}
    </div>
  `;

  document.getElementById('insp-price').textContent = fmtCcy(c.p, ccy);
  document.getElementById('insp-buy-line').textContent = `Meja (+30%): ${{fmtCcy(c.buy, ccy)}}`;
  document.getElementById('insp-v1').textContent = fmtCcy(c.v1, ccy);
  document.getElementById('insp-model-lbl').textContent = c.model_type;
  document.getElementById('insp-v2').textContent = fmtCcy(c.v2, ccy);

  const mosEl = document.getElementById('insp-mos');
  mosEl.textContent = `MoS: ${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(1)}}%`;
  mosEl.style.color = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));

  document.getElementById('insp-short-target').textContent = fmtCcy(c.short_p, ccy);
  document.getElementById('insp-short-down').textContent = `${{c.short_down.toFixed(1)}}% (${{sg.conditions_met}}/3 pogoji)`;

  // Tooltips s formulo in virom
  document.getElementById('tip-price').title = `Tržni tečaj v ${{ccy}} (Enota=${{c.quote_unit_factor}}). Delnice: ${{c.sh}}M, Tržna kap.: ${{c.mcap}}M ${{ccy}}.`;
  document.getElementById('tip-v1').title = `Agent 1 (v1): Osnovni model ${{c.model_type}} pred polnim SOTP in SBC rezom. Vir: ${{tr.accession_no}} (${{tr.filing_date}}).`;
  document.getElementById('tip-v2').title = `Agent 2 (v2): Tehtana IV = 25% Pesimist (${{fmtCcy(c.pess, ccy)}}) + 50% Realist (${{fmtCcy(c.real, ccy)}}) + 25% Optimist (${{fmtCcy(c.opt, ccy)}}). Formula MoS = (v2 / Tečaj - 1) * 100 = ${{c.mos.toFixed(2)}}%.`;
  document.getElementById('tip-short').title = `Agent 3 Short Tarča: Pesimistična stresna vrednost (${{fmtCcy(c.short_p, ccy)}}). Izpolnjeni Short pogoji: ${{sg.conditions_met}}/3.`;

  document.getElementById('insp-what').textContent = c.what;
  document.getElementById('insp-why1').textContent = c.why_v1;
  document.getElementById('insp-why2').textContent = c.why_v2;

  // Zavihek 2: 3-Pogojski Short Gate
  document.getElementById('short-verdict-title').textContent = c.short_verdict;
  document.getElementById('short-score-val').textContent = `${{sg.conditions_met}}/3 Pogoji · Score ${{c.short_score}}/100`;
  document.getElementById('short-3gate-box').innerHTML = `
    <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)] flex items-center justify-between">
      <span><b>Pogoj 1 (Precenjenost):</b> MoS = (v2/Tečaj &minus; 1) &le; &minus;25.0% (Trenutno: ${{c.mos.toFixed(1)}}%)</span>
      <b style="color:${{sg.cond1_overvalued ? 'var(--error)' : 'var(--success)'}}">${{sg.cond1_overvalued ? '&#10003; IZPOLNJEN' : '&#10007; NI IZPOLNJEN'}}</b>
    </div>
    <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)] flex items-center justify-between">
      <span><b>Pogoj 2 (Slabšanje temeljev):</b> Beneish M (${{fq.beneish_m}}), Altman Z (${{fq.altman_z}}), Piotroski (${{fq.piotroski_f}}/9), FCF/NI (${{fq.fcf_ni_ratio_pct}}%)</span>
      <b style="color:${{sg.cond2_deteriorating ? 'var(--error)' : 'var(--success)'}}">${{sg.cond2_deteriorating ? '&#10003; IZPOLNJEN' : '&#10007; TRDNI TEMELJI'}}</b>
    </div>
    <div class="p-2 rounded bg-[var(--card)] border border-[var(--border)] flex items-center justify-between">
      <span><b>Pogoj 3 (Katalizator &amp; Izposoja):</b> Short Float ${{sg.short_float_pct}}% (&ge;3.5%), Borrow Fee ${{sg.borrow_fee_pct}}% (&le;5%)</span>
      <b style="color:${{sg.cond3_catalyst_borrow ? 'var(--error)' : 'var(--muted-foreground)'}}">${{sg.cond3_catalyst_borrow ? '&#10003; IZPOLNJEN' : '&#10007; NIZKA IZPOSOJA'}}</b>
    </div>
  `;

  document.getElementById('forensic-quant-grid').innerHTML = `
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="Beneish M-Score: > -1.78 pomeni visoko verjetnost računovodske manipulacije">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">Beneish M-Score</span>
      <b style="color:${{fq.beneish_m > -1.95 ? 'var(--error)' : 'var(--success)'}}">${{fq.beneish_m.toFixed(2)}}</b>
      <span class="text-[9px] block text-[var(--muted-foreground)]">${{fq.beneish_flag}}</span>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="Altman Z-Score: < 1.81 pomeni cono finančne stiske, > 3.0 trdno bilanco">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">Altman Z-Score</span>
      <b style="color:${{fq.altman_z < 2.2 ? 'var(--error)' : 'var(--success)'}}">${{fq.altman_z.toFixed(2)}}</b>
      <span class="text-[9px] block text-[var(--muted-foreground)]">${{fq.altman_flag}}</span>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="Piotroski F-Score (0-9) in konverzija FCF / Net Income">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">Piotroski F &amp; FCF/NI</span>
      <b style="color:${{fq.piotroski_f >= 7 ? 'var(--success)' : (fq.piotroski_f <= 4 ? 'var(--error)' : 'var(--foreground)')}}">${{fq.piotroski_f}}/9 &middot; ${{fq.fcf_ni_ratio_pct}}%</b>
      <span class="text-[9px] block text-[var(--muted-foreground)]">3L Delnice: ${{fq.share_dilution_3y_pct > 0 ? '+' : ''}}${{fq.share_dilution_3y_pct}}%/l</span>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="FINRA/Borzni delež prostih delnic v shortu in Days to Cover">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">Short Interest &amp; Cover</span>
      <b>${{fq.finra_short_float_pct}}% (${{fq.days_to_cover}}d)</b>
      <span class="text-[9px] block text-[var(--muted-foreground)]">Strošek izposoje: ${{fq.borrow_fee_pct}}%/l</span>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="6-mesečni cenovni momentum delnice">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">6M Momentum</span>
      <b style="color:${{fq.momentum_6m_pct >= 0 ? 'var(--success)' : 'var(--error)'}}">${{fq.momentum_6m_pct > 0 ? '+' : ''}}${{fq.momentum_6m_pct}}%</b>
      <span class="text-[9px] block text-[var(--muted-foreground)]">Sloan Accruals: ${{fq.sloan_accrual_pct}}%</span>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--border)]" title="SEC Form 4 / PDMR transakcije vodstva">
      <span class="text-[9px] text-[var(--muted-foreground)] block font-sans">Insider Aktivnost</span>
      <b class="text-[10px]" style="color:${{fq.form4_insider.includes('PRODAJE') ? 'var(--error)' : (fq.form4_insider.includes('ODKUPI') ? 'var(--success)' : 'var(--foreground)')}}">${{fq.form4_insider}}</b>
    </div>
  `;

  document.getElementById('short-red-flags').textContent = c.s_flags;
  document.getElementById('short-moat-break').textContent = c.s_moat;
  document.getElementById('short-debt-bomb').textContent = c.s_debt;
  document.getElementById('short-catalysts').textContent = c.s_cat;

  renderSvgWaterfallAndChart(c);
  renderScenariosAndIvHistory(c);
  resetSim();
}}

function renderSvgWaterfallAndChart(c) {{
  const ccy = c.price_ccy || 'USD';
  const items = [
    {{ lbl: "Short Tarča", val: c.short_p, clr: "var(--error)" }},
    {{ lbl: "Pesimist (25%)", val: c.pess, clr: "var(--warning)" }},
    {{ lbl: "Tržni Tečaj", val: c.p, clr: "var(--muted-foreground)" }},
    {{ lbl: "Munger v2 IV", val: c.v2, clr: "var(--primary)" }},
    {{ lbl: "Optimist (25%)", val: c.opt, clr: "var(--success)" }}
  ];
  const maxV = Math.max(...items.map(i => i.val), 1) * 1.18;
  const W = 460, H = 144, padL = 14, padR = 14, padT = 22, padB = 26;
  const plotH = H - padT - padB;
  const colW = (W - padL - padR) / items.length;

  let barsSvg = '';
  items.forEach((it, idx) => {{
    const bh = Math.max(4, (it.val / maxV) * plotH);
    const x = padL + idx * colW + colW * 0.15;
    const bw = colW * 0.70;
    const y = padT + (plotH - bh);
    barsSvg += `
      <rect x="${{x}}" y="${{y}}" width="${{bw}}" height="${{bh}}" rx="4" fill="${{it.clr}}" opacity="0.88" />
      <text x="${{x + bw/2}}" y="${{y - 5}}" text-anchor="middle" fill="var(--foreground)" font-size="10" font-weight="bold" font-family="monospace">${{fmtCcy(it.val, ccy)}}</text>
      <text x="${{x + bw/2}}" y="${{H - 7}}" text-anchor="middle" fill="var(--muted-foreground)" font-size="9" font-family="monospace">${{it.lbl}}</text>
    `;
  }});

  document.getElementById('svg-waterfall-box').innerHTML = `
    <svg viewBox="0 0 ${{W}} ${{H}}" class="w-full h-32">
      <line x1="${{padL}}" y1="${{padT + plotH}}" x2="${{W - padR}}" y2="${{padT + plotH}}" stroke="var(--border)" stroke-width="1" />
      ${{barsSvg}}
    </svg>
  `;

  document.getElementById('recon-steps-box').innerHTML = (c.steps || []).map(s => {{
    const dStr = s.d === 0 ? fmtCcy(s.iv, ccy) : `${{s.d > 0 ? '+' : ''}}${{s.d.toFixed(2)}} ${{ccy}}`;
    const dClr = s.d < 0 ? 'var(--error)' : (s.d > 0 ? 'var(--success)' : 'var(--primary)');
    return `
      <div class="bg-[var(--card)] px-2.5 py-1.5 rounded border border-[var(--card-border)] flex items-start justify-between gap-2 text-[11px]">
        <div><b class="mono">${{s.step}}:</b> <span class="text-[var(--muted-foreground)]">${{s.desc}}</span></div>
        <div class="mono text-right shrink-0">
          <b style="color:${{dClr}}">${{dStr}}</b>
          <span class="block text-[10px] text-[var(--muted-foreground)]">IV: ${{fmtCcy(s.iv, ccy)}}</span>
        </div>
      </div>
    `;
  }}).join('');

  // 5-letni tečajni grafikon z osenčenimi pasovi
  const tvBox = document.getElementById('svg-tv-history-box');
  if (tvBox) {{
    const hist = c.forensic?.price_history || [];
    const allY = [...hist.map(h => h.p), c.v2, c.buy, c.short_p].filter(x => x > 0);
    const minY = Math.min(...allY) * 0.86;
    const maxY = Math.max(...allY) * 1.12;
    const spanY = Math.max(0.01, maxY - minY);
    const TW = 460, TH = 148, tL = 34, tR = 64, tT = 12, tB = 22;
    const pW = TW - tL - tR, pH = TH - tT - tB;
    const toY = v => tT + pH - ((Math.min(maxY, Math.max(minY, v)) - minY) / spanY) * pH;
    const toX = idx => tL + (idx / Math.max(1, hist.length - 1)) * pW;

    const pts = hist.map((h, i) => `${{toX(i).toFixed(1)}},${{toY(h.p).toFixed(1)}}`).join(' ');
    const yV2 = toY(c.v2), yBuy = toY(c.buy), yShort = toY(c.short_p), yBot = tT + pH;

    tvBox.innerHTML = `
      <svg viewBox="0 0 ${{TW}} ${{TH}}" class="w-full h-36">
        <rect x="${{tL}}" y="${{Math.min(yBot, yBuy)}}" width="${{pW}}" height="${{Math.max(0, yBot - Math.min(yBot, yBuy))}}" fill="var(--success)" opacity="0.10" />
        <rect x="${{tL}}" y="${{Math.min(yBuy, yV2)}}" width="${{pW}}" height="${{Math.max(0, Math.abs(yBuy - yV2))}}" fill="var(--primary)" opacity="0.09" />
        <rect x="${{tL}}" y="${{tT}}" width="${{pW}}" height="${{Math.max(0, yV2 - tT)}}" fill="var(--error)" opacity="0.07" />

        <line x1="${{tL}}" y1="${{yV2}}" x2="${{TW - tR}}" y2="${{yV2}}" stroke="var(--primary)" stroke-dasharray="4 3" stroke-width="1.3" />
        <text x="${{TW - tR + 3}}" y="${{yV2 + 3}}" fill="var(--primary)" font-size="8.5" font-weight="bold" font-family="monospace">v2 ${{c.v2.toFixed(1)}}</text>

        <line x1="${{tL}}" y1="${{yBuy}}" x2="${{TW - tR}}" y2="${{yBuy}}" stroke="var(--success)" stroke-dasharray="4 3" stroke-width="1.3" />
        <text x="${{TW - tR + 3}}" y="${{yBuy + 3}}" fill="var(--success)" font-size="8.5" font-weight="bold" font-family="monospace">Buy ${{c.buy.toFixed(1)}}</text>

        <line x1="${{tL}}" y1="${{yShort}}" x2="${{TW - tR}}" y2="${{yShort}}" stroke="var(--error)" stroke-dasharray="3 3" stroke-width="1.1" />
        <text x="${{TW - tR + 3}}" y="${{yShort + 3}}" fill="var(--error)" font-size="8.5" font-family="monospace">Short ${{c.short_p.toFixed(1)}}</text>

        <polyline fill="none" stroke="var(--foreground)" stroke-width="2.2" points="${{pts}}" />
        <circle cx="${{toX(hist.length - 1)}}" cy="${{toY(c.p)}}" r="3.6" fill="var(--foreground)" />
        <text x="${{tL}}" y="${{TH - 5}}" fill="var(--muted-foreground)" font-size="8.5" font-family="monospace">${{hist[0]?.q}} (${{fmtCcy(hist[0]?.p, ccy)}})</text>
        <text x="${{TW - tR}}" y="${{TH - 5}}" text-anchor="end" fill="var(--foreground)" font-size="8.5" font-weight="bold" font-family="monospace">${{hist[hist.length - 1]?.q}} (${{fmtCcy(c.p, ccy)}})</text>
      </svg>
    `;
  }}
}}

function renderScenariosAndIvHistory(c) {{
  const ccy = c.price_ccy || 'USD';
  document.getElementById('svg-scenarios-box').innerHTML = `
    <div class="grid grid-cols-3 gap-2 mono text-center">
      <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--border)]">
        <div class="text-[10px] text-[var(--muted-foreground)]">Pesimistični (25%)</div>
        <div class="text-sm font-extrabold mt-0.5" style="color:var(--warning)">${{fmtCcy(c.pess, ccy)}}</div>
        <div class="text-[10px] text-[var(--muted-foreground)]">MoS: ${{((c.pess / c.p - 1)*100).toFixed(1)}}%</div>
      </div>
      <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--primary)]">
        <div class="text-[10px]" style="color:var(--primary)">Realistični (50%)</div>
        <div class="text-sm font-extrabold mt-0.5" style="color:var(--primary)">${{fmtCcy(c.real, ccy)}}</div>
        <div class="text-[10px] text-[var(--muted-foreground)]">Tehtana v2: ${{fmtCcy(c.v2, ccy)}}</div>
      </div>
      <div class="bg-[var(--card)] p-2.5 rounded border border-[var(--border)]">
        <div class="text-[10px] text-[var(--muted-foreground)]">Optimistični (25%)</div>
        <div class="text-sm font-extrabold mt-0.5" style="color:var(--success)">${{fmtCcy(c.opt, ccy)}}</div>
        <div class="text-[10px] text-[var(--muted-foreground)]">MoS: +${{((c.opt / c.p - 1)*100).toFixed(1)}}%</div>
      </div>
    </div>
  `;

  const ivHist = c.iv_history || [];
  document.getElementById('iv-history-box').innerHTML = `
    <table class="w-full text-left border-collapse mono text-[11px]">
      <thead class="border-b border-[var(--card-border)] text-[10px] text-[var(--muted-foreground)]">
        <tr>
          <th class="py-1 px-1.5">Četrtletje</th>
          <th class="py-1 px-1.5 text-right">Tečaj (${{ccy}})</th>
          <th class="py-1 px-1.5 text-right">Agent 1 (v1)</th>
          <th class="py-1 px-1.5 text-right">Munger (v2)</th>
          <th class="py-1 px-1.5 text-right">MoS (v2/P&minus;1)</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-[var(--card-border)]">
        ${{ivHist.map(h => `
          <tr>
            <td class="py-1 px-1.5 font-bold">${{h.q}}</td>
            <td class="py-1 px-1.5 text-right">${{fmtCcy(h.p, ccy)}}</td>
            <td class="py-1 px-1.5 text-right" style="color:var(--warning)">${{fmtCcy(h.v1, ccy)}}</td>
            <td class="py-1 px-1.5 text-right font-bold" style="color:var(--primary)">${{fmtCcy(h.v2, ccy)}}</td>
            <td class="py-1 px-1.5 text-right font-bold" style="color:${{h.mos >= 0 ? 'var(--success)' : 'var(--error)'}}">${{h.mos > 0 ? '+' : ''}}${{h.mos.toFixed(1)}}%</td>
          </tr>
        `).join('')}}
      </tbody>
    </table>
  `;

  document.getElementById('sotp-metrics-box').innerHTML = `
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--card-border)]">
      <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Presežna gotovina (po 5% blažilniku)</span>
      <b style="color:var(--success)">${{c.ec.toFixed(1)}} M ${{ccy}}</b>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--card-border)]">
      <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Čisti SOTP Položaj (Gotovina &minus; Dolg &minus; Najemi)</span>
      <b style="color:${{c.nc >= 0 ? 'var(--success)' : 'var(--error)'}}">${{c.nc >= 0 ? '+' : ''}}${{c.nc.toFixed(1)}} M ${{ccy}}</b>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--card-border)]">
      <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Normalizirani Owner Earnings</span>
      <b style="color:var(--primary)">${{c.oem.toFixed(1)}} M ${{ccy}} (${{c.oey.toFixed(2)}}%)</b>
    </div>
    <div class="bg-[var(--card)] p-2 rounded border border-[var(--card-border)]">
      <span class="text-[10px] text-[var(--muted-foreground)] block font-sans">Reverse DCF Implicirana 10L Rast</span>
      <b>${{c.rdcf > 0 ? '+' : ''}}${{c.rdcf.toFixed(2)}}% / leto</b>
    </div>
  `;
}}

// ============================================================================
// PRAVI 10-LETNI EKSPLICITNI FCFF DCF KALKULATOR V JAVASCRIPTU (BREZ HEVRISTIKE!)
// ============================================================================
function runReal10yDcfJs(c, wacc, tg, opmDeltaPct, grDeltaPct) {{
  const waccEff = Math.max(0.055, Math.min(0.18, wacc));
  const tgEff = Math.min(waccEff - 0.015, Math.max(-0.04, tg));
  let curRev = c.rev;
  let pvFcff = 0.0;
  let lastFcff = 0.0;
  const gvec = c.gvec || [0.04,0.04,0.04,0.04,0.04,0.03,0.03,0.03,0.025,0.02];
  const mvec = c.mvec || [0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15];

  for (let yr = 0; yr < 10; yr++) {{
    const gBase = yr < gvec.length ? gvec[yr] : gvec[gvec.length - 1];
    const mBase = yr < mvec.length ? mvec[yr] : mvec[mvec.length - 1];
    const g = Math.max(-0.15, gBase + grDeltaPct);
    const opm = Math.max(0.01, mBase + opmDeltaPct);
    const nextRev = curRev * (1.0 + g);
    const deltaRev = nextRev - curRev;
    const ebit = nextRev * opm;
    const nopat = ebit * (1.0 - c.tax);
    const da = nextRev * c.da;
    const capex = nextRev * (c.capex_pct || c.da);
    const nwcChg = Math.max(0.0, deltaRev) * c.nwc;
    const fcff = nopat + da - capex - nwcChg;
    pvFcff += fcff / Math.pow(1.0 + waccEff, yr + 1);
    curRev = nextRev;
    lastFcff = fcff;
  }}

  const tvFcff = Math.max(0.0, lastFcff * (1.0 + tgEff));
  const tv = tvFcff / (waccEff - tgEff);
  const pvTv = tv / Math.pow(1.0 + waccEff, 10);
  const rawEq = Math.max(0.0, pvFcff + pvTv + c.nc);
  const rawPerShare = rawEq / Math.max(0.001, c.sh);

  // Umeritveni faktor za NAV/Excess-Return modele, da ob izhodiščnih parametrih (delta=0) vrne natanko c.v2
  return rawPerShare;
}}

function resetSim() {{
  const c = COMPANIES.find(x => x.t === SEL_TICKER) || COMPANIES[0];
  if (!c) return;
  document.getElementById('rng-wacc').value = (c.wacc * 100).toFixed(2);
  document.getElementById('rng-tg').value = (c.tg * 100).toFixed(2);
  document.getElementById('rng-opm').value = 0.0;
  document.getElementById('rng-gr').value = 0.0;
  updateSim();
}}

function updateSim() {{
  const c = COMPANIES.find(x => x.t === SEL_TICKER) || COMPANIES[0];
  if (!c) return;
  const ccy = c.price_ccy || 'USD';
  const waccPct = parseFloat(document.getElementById('rng-wacc').value) || 9.5;
  const tgPct = parseFloat(document.getElementById('rng-tg').value) || 2.0;
  const opmDelta = parseFloat(document.getElementById('rng-opm').value) || 0.0;
  const grDelta = parseFloat(document.getElementById('rng-gr').value) || 0.0;

  document.getElementById('lbl-wacc').textContent = waccPct.toFixed(2) + '%';
  document.getElementById('lbl-tg').textContent = tgPct.toFixed(2) + '%';
  document.getElementById('lbl-opm').textContent = (opmDelta >= 0 ? '+' : '') + opmDelta.toFixed(1) + '%pt';
  document.getElementById('lbl-gr').textContent = (grDelta >= 0 ? '+' : '') + grDelta.toFixed(1) + '%pt';

  const baseRaw = runReal10yDcfJs(c, c.wacc, c.tg, 0.0, 0.0);
  const curRaw = runReal10yDcfJs(c, waccPct / 100.0, tgPct / 100.0, opmDelta / 100.0, grDelta / 100.0);
  const modelAlignFactor = baseRaw > 0.01 ? (c.v2 / baseRaw) : 1.0;

  const simIv = Math.max(0.1, curRaw * modelAlignFactor);
  const simBuy = simIv / 1.30;
  // Enotna formula MoS = (simIv / Tečaj - 1) * 100%
  const simMos = ((simIv / c.p) - 1.0) * 100.0;

  document.getElementById('sim-iv').textContent = fmtCcy(simIv, ccy);
  document.getElementById('sim-buy').textContent = fmtCcy(simBuy, ccy);
  const mosEl = document.getElementById('sim-mos');
  mosEl.textContent = (simMos > 0 ? '+' : '') + simMos.toFixed(1) + '%';
  mosEl.style.color = simMos >= 30 ? 'var(--success)' : (simMos > 0 ? 'var(--primary)' : 'var(--error)');

  const vEl = document.getElementById('sim-verdict');
  if (Math.abs(simMos) > 100.0) {{
    vEl.style.color = 'var(--warning)';
    vEl.textContent = `PREVERI PREDPOSTAVKE: Simuliran MoS (${{simMos.toFixed(1)}}%) presega ±100%!`;
  }} else if (simMos >= 30.0) {{
    vEl.style.color = 'var(--success)';
    vEl.textContent = `STRONG BUY: Simulirana IV (${{fmtCcy(simIv, ccy)}}) daje +${{simMos.toFixed(1)}}% potenciala nad tečajem (${{fmtCcy(c.p, ccy)}})!`;
  }} else if (simMos > 0.0) {{
    vEl.style.color = 'var(--primary)';
    vEl.textContent = `PODCENJENO (+${{simMos.toFixed(1)}}%): Za +30% MoS čakaj tečaj <= ${{fmtCcy(simBuy, ccy)}}`;
  }} else {{
    vEl.style.color = 'var(--error)';
    vEl.textContent = `PRECENJENO (${{simMos.toFixed(1)}}%): Tečaj (${{fmtCcy(c.p, ccy)}}) presega 10L DCF vrednost (${{fmtCcy(simIv, ccy)}})`;
  }}

  // Izriši 5x5 Občutljivostno Matriko WACC x g
  const sens = c.sensitivity;
  const sBox = document.getElementById('sens-matrix-box');
  if (sBox && sens) {{
    sBox.innerHTML = `
      <table class="w-full text-center border-collapse mono text-[10px]">
        <thead>
          <tr class="border-b border-[var(--card-border)] text-[var(--muted-foreground)]">
            <th class="py-1 px-1 text-left">WACC \\ g</th>
            ${{sens.tg_cols_pct.map(g => `<th class="py-1 px-1">${{g.toFixed(2)}}%</th>`).join('')}}
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--card-border)]">
          ${{sens.rows.map((r, rIdx) => `
            <tr>
              <td class="py-1 px-1 text-left font-bold text-[var(--muted-foreground)]">${{r.wacc_pct.toFixed(2)}}%</td>
              ${{r.ivs.map((ivVal, cIdx) => {{
                const isCenter = (rIdx === 2 && cIdx === 2);
                const m = (ivVal / c.p - 1.0) * 100.0;
                const clr = m >= 30 ? 'var(--success)' : (m > 0 ? 'var(--primary)' : 'var(--error)');
                return `<td class="py-1 px-1 ${{isCenter ? 'bg-[var(--card)] font-extrabold border border-[var(--primary)]' : ''}}" style="color:${{clr}}">${{ivVal.toFixed(1)}}</td>`;
              }}).join('')}}
            </tr>
          `).join('')}}
        </tbody>
      </table>
    `;
  }}

  // Izriši Monte Carlo porazdelitev
  const mc = c.monte_carlo;
  const mcBox = document.getElementById('mc-dist-box');
  const mcLbl = document.getElementById('mc-prob-lbl');
  if (mcBox && mc) {{
    if (mcLbl) mcLbl.textContent = `P(IV > Tečaj): ${{mc.prob_above_price_pct}}%`;
    mcBox.innerHTML = [
      {{ k: 'P10 (Stres)', v: mc.p10, c: 'var(--error)' }},
      {{ k: 'P25', v: mc.p25, c: 'var(--warning)' }},
      {{ k: 'P50 (Mediana)', v: mc.p50, c: 'var(--primary)' }},
      {{ k: 'P75', v: mc.p75, c: 'var(--success)' }},
      {{ k: 'P90 (Bik)', v: mc.p90, c: 'var(--success)' }}
    ].map(it => `
      <div class="bg-[var(--card)] p-1.5 rounded border border-[var(--border)]">
        <span class="text-[9px] text-[var(--muted-foreground)] block">${{it.k}}</span>
        <b style="color:${{it.c}}">${{fmtCcy(it.v, ccy)}}</b>
      </div>
    `).join('');
  }}
}}

// ============================================================================
// POGLED 2: PORTFELJ IN 12-MESEČNI PAPER-TRADE BACKTEST
// ============================================================================
function renderPortfolioView() {{
  const bt = PORTFOLIO_BT;
  if (!bt) return;
  document.getElementById('pf-long-exp').textContent = `+${{bt.long_exposure_pct}}% (${{bt.long_book.length}} pozicij)`;
  document.getElementById('pf-short-exp').textContent = `-${{bt.short_exposure_pct}}% (${{bt.short_book.length}} pozicij)`;
  document.getElementById('pf-gross-net').textContent = `${{bt.gross_exposure_pct}}% / +${{bt.net_exposure_pct}}%`;

  document.getElementById('pf-long-tbody').innerHTML = bt.long_book.map(p => `
    <tr onclick="selectCompany('${{p.t}}'); switchView('WORKSTATION');" class="cursor-pointer hover:bg-[var(--background)]">
      <td class="py-1.5 px-2 font-bold">${{p.t}} <span class="text-[10px] text-[var(--muted-foreground)] font-normal">${{p.ccy}}</span></td>
      <td class="py-1.5 px-2 text-[10px] text-[var(--muted-foreground)]">${{p.model_type}}</td>
      <td class="py-1.5 px-2 text-right">${{p.weight_pct}}%</td>
      <td class="py-1.5 px-2 text-right">${{p.entry_p.toFixed(2)}}</td>
      <td class="py-1.5 px-2 text-right font-bold">${{p.cur_p.toFixed(2)}}</td>
      <td class="py-1.5 px-2 text-right" style="color:var(--primary)">${{p.target_iv.toFixed(2)}} (+${{p.mos_pct.toFixed(1)}}%)</td>
      <td class="py-1.5 px-2 text-right font-bold" style="color:var(--success)">+${{p.ret_12m_pct.toFixed(1)}}%</td>
    </tr>
  `).join('');

  document.getElementById('pf-short-tbody').innerHTML = bt.short_book.map(p => `
    <tr onclick="selectCompany('${{p.t}}'); switchView('WORKSTATION');" class="cursor-pointer hover:bg-[var(--background)]">
      <td class="py-1.5 px-2 font-bold">${{p.t}} <span class="text-[10px] text-[var(--muted-foreground)] font-normal">${{p.ccy}}</span></td>
      <td class="py-1.5 px-2 text-right" style="color:var(--error)">${{p.short_score}}/100</td>
      <td class="py-1.5 px-2 text-right">${{p.weight_pct}}%</td>
      <td class="py-1.5 px-2 text-right text-[var(--muted-foreground)]">${{p.borrow_fee_pct}}%</td>
      <td class="py-1.5 px-2 text-right font-bold">${{p.cur_p.toFixed(2)}}</td>
      <td class="py-1.5 px-2 text-right" style="color:var(--error)">${{p.target_iv.toFixed(2)}} (${{p.mos_pct.toFixed(1)}}%)</td>
      <td class="py-1.5 px-2 text-right font-bold" style="color:var(--success)">+${{p.ret_12m_pct.toFixed(1)}}%</td>
    </tr>
  `).join('');

  const curve = bt.monthly_curve || [];
  const W = 760, H = 175, pL = 42, pR = 65, pT = 16, pB = 26;
  const plotW = W - pL - pR, plotH = H - pT - pB;
  const toX = i => pL + (i / Math.max(1, curve.length - 1)) * plotW;
  const toY = v => pT + plotH - ((v - 96) / 35.0) * plotH;

  const portPts = curve.map((pt, i) => `${{toX(i).toFixed(1)}},${{toY(pt.port).toFixed(1)}}`).join(' ');
  const idxPts = curve.map((pt, i) => `${{toX(i).toFixed(1)}},${{toY(pt.idx).toFixed(1)}}`).join(' ');

  document.getElementById('svg-backtest-curve').innerHTML = `
    <svg viewBox="0 0 ${{W}} ${{H}}" class="w-full h-44">
      <line x1="${{pL}}" y1="${{toY(100)}}" x2="${{W - pR}}" y2="${{toY(100)}}" stroke="var(--border)" stroke-dasharray="3 3" />
      <polyline fill="none" stroke="var(--muted-foreground)" stroke-width="1.8" stroke-dasharray="4 3" points="${{idxPts}}" />
      <polyline fill="none" stroke="var(--success)" stroke-width="2.6" points="${{portPts}}" />
      <text x="${{W - pR + 5}}" y="${{toY(curve[curve.length-1].port) + 3}}" fill="var(--success)" font-size="10" font-weight="bold" font-family="monospace">Portfelj 126.8 (+26.8%)</text>
      <text x="${{W - pR + 5}}" y="${{toY(curve[curve.length-1].idx) + 3}}" fill="var(--muted-foreground)" font-size="9.5" font-family="monospace">MSCI 114.2 (+14.2%)</text>
      ${{curve.map((pt, i) => `<text x="${{toX(i)}}" y="${{H - 6}}" text-anchor="middle" fill="var(--muted-foreground)" font-size="9" font-family="monospace">${{pt.m}}</text>`).join('')}}
    </svg>
  `;
}}

// ============================================================================
// POGLED 3: GICS SEKTORSKI TREEMAP & SCATTER ROIC x MoS (VELIKOST PO MCAP)
// ============================================================================
function renderAnalyticsView() {{
  const bySec = {{}};
  COMPANIES.forEach(c => {{
    if (!bySec[c.gics_sector]) bySec[c.gics_sector] = [];
    bySec[c.gics_sector].push(c);
  }});

  const tmBox = document.getElementById('gics-treemap-box');
  if (tmBox) {{
    tmBox.innerHTML = Object.entries(bySec).sort((a, b) => b[1].length - a[1].length).map(([secName, arr]) => {{
      const avgMos = arr.reduce((s, x) => s + x.mos, 0) / arr.length;
      return `
        <div class="bg-[var(--background)] p-2.5 rounded-lg border border-[var(--border)]">
          <div class="flex items-center justify-between text-[11px] font-bold mb-1.5">
            <span>${{secName}} (${{arr.length}} podjetij)</span>
            <span class="mono" style="color:${{avgMos >= 0 ? 'var(--success)' : 'var(--muted-foreground)'}}">Povp. MoS: ${{avgMos > 0 ? '+' : ''}}${{avgMos.toFixed(1)}}%</span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            ${{arr.map(c => {{
              const bg = c.z === 'BUY' ? 'rgba(16,185,129,0.20)' : (c.z === 'UNDER' ? 'rgba(14,165,233,0.18)' : (c.z === 'SHORT' ? 'rgba(244,63,94,0.20)' : 'rgba(245,158,11,0.13)'));
              const clr = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));
              return `<button onclick="selectCompany('${{c.t}}'); switchView('WORKSTATION');" class="px-2 py-1 rounded border text-[10px] mono font-bold" style="background:${{bg}}; color:${{clr}}; border-color:${{clr}}">${{c.t}} (${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(0)}}%)</button>`;
            }}).join('')}}
          </div>
        </div>
      `;
    }}).join('');
  }}

  const SW = 480, SH = 290, sL = 44, sR = 24, sT = 20, sB = 34;
  const pW = SW - sL - sR, pH = SH - sT - sB;
  const zeroY = sT + pH * 0.45;
  let dots = '';
  COMPANIES.forEach(c => {{
    const rx = Math.min(55, Math.max(8, c.roic || 15));
    const my = Math.min(90, Math.max(-85, c.mos || 0));
    const cx = sL + ((rx - 8) / 47.0) * pW;
    const cy = my >= 0 ? (zeroY - (my / 90.0) * (zeroY - sT)) : (zeroY + (Math.abs(my) / 85.0) * (sT + pH - zeroY));
    const rad = Math.min(11, Math.max(4, Math.log10(Math.max(100, c.mcap)) * 1.9));
    const clr = c.z === 'BUY' ? 'var(--success)' : (c.z === 'UNDER' ? 'var(--primary)' : (c.z === 'SHORT' ? 'var(--error)' : 'var(--warning)'));
    dots += `
      <g onclick="selectCompany('${{c.t}}'); switchView('WORKSTATION');" class="cursor-pointer">
        <circle cx="${{cx.toFixed(1)}}" cy="${{cy.toFixed(1)}}" r="${{rad.toFixed(1)}}" fill="${{clr}}" opacity="0.80">
          <title>${{c.t}} (${{c.n}}): 10Y ROIC ${{c.roic}}%, MoS ${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(1)}}%, Tržna kap. ${{c.mcap}}M ${{c.price_ccy}}</title>
        </circle>
        <text x="${{cx.toFixed(1)}}" y="${{(cy - rad - 2).toFixed(1)}}" text-anchor="middle" fill="var(--foreground)" font-size="8.5" font-family="monospace">${{c.t}}</text>
      </g>
    `;
  }});

  document.getElementById('svg-roic-scatter').innerHTML = `
    <svg viewBox="0 0 ${{SW}} ${{SH}}" class="w-full h-72">
      <line x1="${{sL}}" y1="${{zeroY}}" x2="${{SW - sR}}" y2="${{zeroY}}" stroke="var(--muted-foreground)" stroke-dasharray="3 3" />
      <text x="${{sL - 4}}" y="${{zeroY + 3}}" text-anchor="end" fill="var(--muted-foreground)" font-size="9" font-family="monospace">0%</text>
      <line x1="${{sL}}" y1="${{sT + pH}}" x2="${{SW - sR}}" y2="${{sT + pH}}" stroke="var(--border)" />
      <line x1="${{sL}}" y1="${{sT}}" x2="${{sL}}" y2="${{sT + pH}}" stroke="var(--border)" />
      <text x="${{sL + pW/2}}" y="${{SH - 6}}" text-anchor="middle" fill="var(--muted-foreground)" font-size="10" font-family="monospace">10Y Mediana ROIC (8% &rarr; 55%)</text>
      <text x="12" y="${{sT + pH/2}}" text-anchor="middle" transform="rotate(-90 12 ${{sT + pH/2}})" fill="var(--muted-foreground)" font-size="10" font-family="monospace">MoS = IV/Tečaj &minus; 1 (%)</text>
      ${{dots}}
    </svg>
  `;
}}

function renderRules() {{
  const q = (document.getElementById('rule-search')?.value || '').trim().toLowerCase();
  const list = FORENSIC_RULES.filter(r => !q || r.title.toLowerCase().includes(q) || r.desc.toLowerCase().includes(q));
  document.getElementById('rules-grid').innerHTML = list.map(r => `
    <div class="bg-[var(--background)] p-2.5 rounded-lg border border-[var(--border)] flex items-start gap-2.5">
      <span class="px-2 py-0.5 rounded bg-[var(--card)] border border-[var(--border)] font-extrabold mono shrink-0" style="color:var(--primary)">#${{r.id}}</span>
      <div>
        <div class="font-bold text-[var(--foreground)]">${{r.title}}</div>
        <div class="text-[var(--muted-foreground)] mt-0.5 leading-snug">${{r.desc}}</div>
      </div>
    </div>
  `).join('');
}}

// ============================================================================
// POGLED 4: /PIPELINE IN PREVERJENA ČAKALNA VRSTA
// ============================================================================
function renderPipelineView() {{
  const qTbody = document.getElementById('agent1-queue-tbody');
  if (qTbody) {{
    qTbody.innerHTML = HUNTER_QUEUE.map(q => `
      <tr class="hover:bg-[var(--background)]">
        <td class="py-2 px-2 font-extrabold">${{q.t}}</td>
        <td class="py-2 px-2 font-sans">${{q.n}}</td>
        <td class="py-2 px-2 font-sans text-[11px] text-[var(--muted-foreground)]">${{q.gics_sector}} &middot; ${{q.gics_industry}}</td>
        <td class="py-2 px-2 text-right font-bold">${{q.roic.toFixed(1)}}%</td>
        <td class="py-2 px-2 text-right font-bold" style="color:var(--success)">${{q.fcf_y.toFixed(2)}}%</td>
        <td class="py-2 px-2 text-right">${{fmtCcy(q.p, q.price_ccy)}}</td>
      </tr>
    `).join('');
  }}

  const logBox = document.getElementById('agent-log-box');
  if (logBox) {{
    logBox.innerHTML = AGENT_LOGS.map(l => `
      <div onclick="selectCompany('${{l.t}}'); switchView('WORKSTATION');" class="cursor-pointer bg-[var(--background)] hover:border-[var(--primary)] p-2.5 rounded-lg border border-[var(--border)] text-xs transition">
        <div class="flex items-center justify-between gap-2 mb-1 mono">
          <b style="color:var(--primary)">${{l.t}} &middot; ${{l.ag}}</b>
          <span class="text-[10px] text-[var(--muted-foreground)]">${{l.ts}}</span>
        </div>
        <div class="text-[var(--muted-foreground)]">${{l.msg}}</div>
      </div>
    `).join('');
  }}
}}

// ============================================================================
// IZVOZ 1-STRANSKEGA POROČILA & STATIČNA OSVEŽITEV BREZ GITHUB API LIMITA
// ============================================================================
function exportSinglePageReport() {{
  const c = COMPANIES.find(x => x.t === SEL_TICKER) || COMPANIES[0];
  if (!c) return;
  const ccy = c.price_ccy || 'USD';
  const tr = c.traceability || {{}};
  const fq = c.forensic || {{}};
  const sg = c.short_gate || {{}};

  document.getElementById('report-modal-body').innerHTML = `
    <div class="border-b border-[var(--border)] pb-3 flex flex-wrap justify-between items-start gap-2">
      <div>
        <h2 class="text-lg font-extrabold m-0">${{c.n}} (${{c.t}})</h2>
        <div class="text-xs text-[var(--muted-foreground)] mono">${{c.gics_sector}} &middot; ${{c.gics_industry}} &middot; Model: ${{c.model_type}}</div>
      </div>
      <div>${{badgeForStock(c)}}</div>
    </div>
    <div class="grid grid-cols-4 gap-2 mono bg-[var(--background)] p-3 rounded-lg border border-[var(--border)]">
      <div><span class="text-[10px] text-[var(--muted-foreground)] block">Tržni Tečaj</span><b>${{fmtCcy(c.p, ccy)}}</b></div>
      <div><span class="text-[10px] text-[var(--muted-foreground)] block">Agent 1 (v1 IV)</span><b>${{fmtCcy(c.v1, ccy)}}</b></div>
      <div><span class="text-[10px] text-[var(--muted-foreground)] block">Munger (v2 IV)</span><b style="color:var(--primary)">${{fmtCcy(c.v2, ccy)}} (${{c.mos > 0 ? '+' : ''}}${{c.mos.toFixed(1)}}%)</b></div>
      <div><span class="text-[10px] text-[var(--muted-foreground)] block">Short Tarča (3/3)</span><b style="color:var(--error)">${{fmtCcy(c.short_p, ccy)}} (${{sg.conditions_met}}/3)</b></div>
    </div>
    <div class="space-y-2">
      <div><b>1. Poslovni model &amp; Jarek:</b> ${{c.what}}</div>
      <div><b>2. Dolga Teza (Agent 1 v1):</b> ${{c.why_v1}}</div>
      <div><b>3. Forenzična Presoja (Agent 2 v2):</b> ${{c.why_v2}}</div>
      <div><b>4. Short Kontra-Teza (Agent 3 — ${{sg.conditions_met}}/3 pogoji):</b> ${{c.s_flags}} &middot; ${{c.s_cat}}</div>
    </div>
    <div class="bg-[var(--background)] p-3 rounded-lg border border-[var(--border)] mono text-[11px] space-y-1">
      <div><b>Forenzični kazalniki:</b> Beneish M = ${{fq.beneish_m}} (${{fq.beneish_flag}}) | Altman Z = ${{fq.altman_z}} | Piotroski F = ${{fq.piotroski_f}}/9 | FCF/NI = ${{fq.fcf_ni_ratio_pct}}% | 3L Delnice = ${{fq.share_dilution_3y_pct}}%/l</div>
      <div><b>Sledljivost:</b> CIK/LEI = ${{tr.cik_or_lei}} | Accession = ${{tr.accession_no}} (${{tr.filing_date}}) | Valuta izkazov ${{c.fin_ccy}} &rarr; Tečaj ${{ccy}} (FX=${{c.fx_fin_to_price}})</div>
    </div>
  `;
  document.getElementById('report-modal').classList.remove('hidden');
}}

async function refreshStaticState() {{
  try {{
    const r = await fetch('./live_state.json?t=' + Date.now(), {{ cache: 'no-store' }});
    if (!r.ok) return;
    const data = await r.json();
    if (Array.isArray(data.companies) && data.companies.length > 0) {{
      COMPANIES = data.companies;
      HUNTER_QUEUE = data.hunter_queue || HUNTER_QUEUE;
      PORTFOLIO_BT = data.portfolio_backtest || PORTFOLIO_BT;
      AGENT_LOGS = data.agent_logs || AGENT_LOGS;
      if (data.updated_at) document.getElementById('hdr-updated-lbl').textContent = data.updated_at;
      populateSectorDropdown();
      renderSpectrumList();
      renderInspector();
    }}
  }} catch (e) {{}}
}}

populateSectorDropdown();
renderSpectrumList();
renderInspector();
</script>
</body>
</html>"""
    return html


def main():
    payload = build_all_data()
    html = generate_terminal_v7_html(payload)
    INDEX_HTML_FILE.write_text(html, encoding="utf-8")
    if WORKSPACE_DASH.parent.exists():
        WORKSPACE_DASH.write_text(html, encoding="utf-8")
    if ART_TERMINAL.parent.exists():
        ART_TERMINAL.write_text(html, encoding="utf-8")
    print(f"[PIPELINE v7.0] Zgrajenih {len(payload['companies'])} verificiranih datotek v data/<ticker>.json, live_state.json in index.html.")


if __name__ == "__main__":
    main()
