#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AVTOMATSKI UNIT TESTI ZA PIPELINE (pytest):
Preverja vse kritične pravilnostne pogoje:
1. Invarianta valut, penijev (GBp -> GBP) in tržne kapitalizacije: |mcap / (p * sh) - 1| < 10 % za vseh 52 podjetij.
2. Popravek tickerja Roche na ROG.SW (in odsotnost napačnega ROP.SW).
3. Prave GICS oznake sektorjev (0 pojavitev generičnega 'Technology / Industrials · Compounder') in 5 ločenih modelov.
4. Enotna formula MoS = (v2 / p - 1) * 100 in zastavica data_check_flag za |MoS| > 100 %.
5. Stroga 3-pogojska vrata za Short (Agent 3): vsak SHORT mora izpolnjevati 3/3 pogoje; nobena ciljna cena ni $1.00.
6. Čakalna vrsta brez placeholderjev (fcf_y = 7.5) in brez podvajanja že analiziranih delnic.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.company_universe import ANALYZED_UNIVERSE, VERIFIED_HUNTER_QUEUE
from pipeline.valuation_engine import evaluate_company, run_10y_fcff_dcf


def test_universe_count_and_roche_ticker():
    assert len(ANALYZED_UNIVERSE) >= 52, f"Pričakovanih vsaj 52 podjetij, najdenih {len(ANALYZED_UNIVERSE)}"
    tickers = [c["t"] for c in ANALYZED_UNIVERSE]
    assert len(tickers) == len(set(tickers)), "Tickerji v ANALYZED_UNIVERSE morajo biti unikatni"
    assert "ROG.SW" in tickers, "Roche mora imeti uradni SIX ticker ROG.SW"
    assert "ROP.SW" not in tickers, "Napačen ticker ROP.SW mora biti odstranjen"


def test_currency_and_mcap_consistency():
    for spec in ANALYZED_UNIVERSE:
        c = evaluate_company(spec)
        tk = c["t"]
        p = c["p"]
        sh = c["sh"]
        mcap = c["mcap"]
        err_ratio = abs(mcap / (p * sh) - 1.0)
        assert err_ratio < 0.10, f"{tk}: kršena invarianta |mcap / (p * sh) - 1| = {err_ratio:.4f} (p={p}, sh={sh}, mcap={mcap})"

        # LSE delnice (.L) morajo biti v GBP (funtih), ne v penijih (2781 ali 1128)
        if tk.endswith(".L"):
            assert c["price_ccy"] == "GBP", f"{tk} mora imeti price_ccy == GBP"
            assert c["quote_unit_factor"] == 0.01, f"{tk} mora imeti quote_unit_factor == 0.01"
            assert p < 150.0, f"{tk} tečaj {p} je še vedno v penijih namesto v GBP!"

        # NVO ADR mora pretvarjati DKK izkaze v USD
        if tk == "NVO":
            assert c["price_ccy"] == "USD" and c["fin_ccy"] == "DKK"
            assert 0.12 < c["fx_fin_to_price"] < 0.17


def test_gics_sectors_and_model_separation():
    valid_gics = {
        "Information Technology", "Health Care", "Financials", "Consumer Discretionary",
        "Consumer Staples", "Industrials", "Energy", "Materials", "Utilities",
        "Communication Services", "Real Estate"
    }
    models_seen = set()
    for spec in ANALYZED_UNIVERSE:
        c = evaluate_company(spec)
        assert "Compounder" not in c["sec"], f"{c['t']} ima še vedno generično oznako Compounder: {c['sec']}"
        assert c["gics_sector"] in valid_gics, f"{c['t']} ima neveljaven GICS sektor: {c['gics_sector']}"
        models_seen.add(c["model_type"])

    assert models_seen == {
        "DCF_COMPOUNDER", "NORMALIZED_CYCLICAL", "EXCESS_RETURN_FIN_INS",
        "NAV_SHIPPING_ENERGY", "PHARMA_PIPELINE"
    }, f"Manjkajo ločeni poslovni modeli: {models_seen}"


def test_mos_formula_and_bounds():
    for spec in ANALYZED_UNIVERSE:
        c = evaluate_company(spec)
        expected_mos = round((c["v2"] / c["p"] - 1.0) * 100.0, 2)
        assert abs(c["mos"] - expected_mos) < 0.05, f"{c['t']}: MoS {c['mos']} != (v2/p - 1) {expected_mos}"
        assert c["mos"] >= -100.0, f"{c['t']}: MoS ne sme biti pod -100 % ({c['mos']})"
        if abs(c["mos"]) > 100.0:
            assert c["data_check_flag"] is True


def test_strict_3_condition_short_gate():
    shorts = []
    for spec in ANALYZED_UNIVERSE:
        c = evaluate_company(spec)
        assert c["short_p"] != 1.00 and c["short_p"] >= round(c["p"] * 0.25, 2), f"{c['t']} ima nerealno ciljno short ceno ({c['short_p']})"
        if c["z"] == "SHORT":
            shorts.append(c["t"])
            sg = c["short_gate"]
            assert sg["conditions_met"] == 3, f"{c['t']} označen kot SHORT brez vseh 3 pogojev ({sg})"
            assert sg["cond1_overvalued"] and sg["cond2_deteriorating"] and sg["cond3_catalyst_borrow"]

    # Kakovostna podjetja (HD, ROG.SW, EXPN.L, EPI-B.ST, SECT-B.ST) NE smejo biti označena kot SHORT
    for quality_tk in ["HD", "ROG.SW", "EXPN.L", "EPI-B.ST", "SECT-B.ST", "SGE.L"]:
        assert quality_tk not in shorts, f"Kakovostno podjetje {quality_tk} ne sme biti označeno kot SHORT!"
    # Število aktivnih shortov mora biti selektivno (med 6 in 14 od 52)
    assert 6 <= len(shorts) <= 14, f"Short selekcija mora biti stroga (najdenih {len(shorts)}: {shorts})"


def test_hunter_queue_no_placeholders():
    clean_q = [q for q in VERIFIED_HUNTER_QUEUE if not q.get("skip")]
    analyzed_set = {c["t"] for c in ANALYZED_UNIVERSE}
    fcf_values = [q["fcf_y"] for q in clean_q]
    assert len(set(fcf_values)) >= 12, "Čakalna vrsta ne sme imeti pavšalnih fcf_y = 7.5 placeholderjev"
    for q in clean_q:
        assert q["t"] not in analyzed_set, f"{q['t']} je že analiziran in ne sme biti v čakalni vrsti"


def test_real_10y_dcf_math():
    iv_low_wacc = run_10y_fcff_dcf(1000.0, [0.05]*10, [0.20]*10, 0.21, 0.03, 0.03, 0.02, 0.08, 0.02, 0.0, 100.0)
    iv_high_wacc = run_10y_fcff_dcf(1000.0, [0.05]*10, [0.20]*10, 0.21, 0.03, 0.03, 0.02, 0.11, 0.02, 0.0, 100.0)
    assert iv_low_wacc > iv_high_wacc > 0.0
