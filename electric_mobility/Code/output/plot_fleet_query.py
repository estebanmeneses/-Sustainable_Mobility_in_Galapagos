import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import fleet_power

# ============================================================
#  CONFIGURACIÓN — editar aquí
# ============================================================
YEAR     = 2050
ISLAND   = "Galápagos"   # "San Cristobal" | "Isabela" | "Santa Cruz" | "Galápagos"
SCENARIO = "High"         # "Low" | "Medium" | "High"
# ============================================================

all_power, all_energy, YEARS = fleet_power.load_results()

y_idx      = YEARS.index(YEAR)
t_seg      = np.arange(86400)
t_h        = t_seg / 3600.0

potencia_mw  = all_power[ISLAND][SCENARIO][y_idx]    # MW, 86400 valores
energia_mwh  = all_energy[ISLAND][SCENARIO][y_idx]   # MWh acumulado, 86400 valores

print(f"Isla: {ISLAND} | Escenario: {SCENARIO} | Año: {YEAR}")
print(f"  Potencia pico:       {potencia_mw.max():.4f} MW")
print(f"  Energía total diaria:{energia_mwh[-1]:.4f} MWh")
print(f"  Arrays listos: potencia_mw[86400], energia_mwh[86400]")

# --- Gráfica ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)
color = fleet_power.SCENARIO_COLORS[SCENARIO]

ax1.plot(t_h, potencia_mw, color=color, linewidth=1.2)
ax1.set_title(f"Potencia — {ISLAND} | {SCENARIO} | {YEAR}")
ax1.set_ylabel("Potencia (MW)")
ax1.grid(True, linestyle="--", alpha=0.4)

ax2.plot(t_h, energia_mwh, color=color, linewidth=1.2)
ax2.set_title("Energía acumulada desde medianoche")
ax2.set_ylabel("Energía (MWh)")
ax2.set_xlabel("Hora del día (h)")
ax2.grid(True, linestyle="--", alpha=0.4)

plt.xlim(0, 24)
plt.xticks(np.arange(0, 25, 1))
fig.tight_layout()
plt.show()
