#!/usr/bin/env python3
"""print_dosage.py - Print dosage intermediates for soil_telemetry.csv"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json, math
from core.dosage_calc import plan_fertilizer, irrigation_litres
from core.quality import check_quality
import pandas as pd

df = pd.read_csv(sys.argv[1])
print(f"CSV: {sys.argv[1]}, rows={len(df)}")
print(f"Latest: moisture={df['moisture'].iloc[-1]}, N={df['N'].iloc[-1]}, P={df['P'].iloc[-1]}, K={df['K'].iloc[-1]}")

# Quality
qr = check_quality(df)
print(f"Quality: score={qr.score:.2f}")
for i in qr.issues:
    print(f"  Issue {i.code}: {i.detail}")

# Fertilizer using plan_fertilizer
print("\n--- Fertilizer Dosage (from dosage_calc) ---")
CFG = {
    "supply": {"N": 1.0, "P": 1.0, "K": 1.0},
    "use_eff": {"N": 0.6, "P": 0.5, "K": 0.7},
    "oxide": {"P": 2.29, "K": 1.2},
    "urea_n_fraction": 0.46, "dap_p2o5_fraction": 0.46,
    "dap_n_fraction": 0.18, "mop_k2o_fraction": 0.60,
}
MEAS = {"N": df['N'].iloc[-1], "P": df['P'].iloc[-1], "K": df['K'].iloc[-1]}
REQ = {"N": 100, "P": 50, "K": 60}

r = plan_fertilizer(MEAS, REQ, CFG, 1.0)
print(f"N: deficit={r['deficit_kg_ha']['N']:.2f}, apply_kg_ha={r['apply_elemental_kg_ha']['N']:.2f}")
print(f"  oxide_kg_ha={r['oxide_kg_ha']['P2O5']:.2f} P2O5, {r['oxide_kg_ha']['K2O']:.2f} K2O")
print(f"  kg_ha: urea_gross={r['kg_ha']['urea_gross']:.2f}, dap={r['kg_ha']['dap']:.2f}, mop={r['kg_ha']['mop']:.2f}")
print(f"  kg_area: urea={r['kg_area']['urea_gross']:.2f}, dap={r['kg_area']['dap']:.2f}, mop={r['kg_area']['mop']:.2f}")
print(f"  dap_n_credit={r['kg_ha']['dap_n_credit_kg_n']:.2f} kg N")
print(f"  urea_net={r['kg_ha']['urea_net']:.2f} kg/ha, area_urea_net={r['kg_area']['urea_net']:.2f} kg")

# Irrigation
print("\n--- Irrigation (from dosage_calc) ---")
vwc_now = df['moisture'].iloc[-1]
irr = irrigation_litres(vwc_now, 50, 300, 1.0, 0.9, 8, 5)
print(f"vwc_now={vwc_now}, trigger=50")
print(f"deficit_mm={irr['deficit_mm']:.1f}, daily_mm={irr['daily_mm']:.1f}")
print(f"litres_per_event={irr['litres_per_event']:.0f} L, litres_per_day={irr['litres_per_day']:.0f} L/acre/day")
print(f"10k <= litres_per_day <= 40k: {10_000 <= irr['litres_per_day'] <= 40_000}")