import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import openpyxl

import driving_cycle as driving
import power_cycle as power
import state_of_charge as soc
from driving_cycle import plot_daily_profile
from power_cycle import plot_power_profile
from state_of_charge import plot_soc_profile

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

FULL_FILE      = "data/full_activity_profile.xlsx"
ISLANDS        = ["San Cristobal", "Isabela", "Santa Cruz"]
ISLAND_DIR     = {"San Cristobal": "San_Cristobal", "Isabela": "Isabela", "Santa Cruz": "Santa_Cruz"}
ISLAND_ROW     = {"San Cristobal": 12, "Isabela": 13, "Santa Cruz": 14}
VEHICLE_SHEETS = ["SUV", "Truck", "PickUp", "Bus", "Motorcycle", "Micromobilidad"]

BAND_SIZE = 3 * 3600   # segundos por franja de 3h


def run_multi_island_analysis():
    """Corre el ciclo completo para cada vehículo × isla.

    Retorna:
        band_kwh         : dict {island: {sheet: [kWh_b0..kWh_b7]}}
        distances        : dict {island: {sheet: km}}
        grid_p_profiles  : dict {island: {sheet: np.ndarray(86400)}} en kW
        soc_ch_profiles  : dict {island: {sheet: np.ndarray(86400)}} SoC con carga [0-1]
    """
    os.makedirs("results", exist_ok=True)
    distances        = {}
    band_kwh         = {}
    grid_p_profiles  = {}
    soc_ch_profiles  = {}
    driving_profiles = {}

    for island in ISLANDS:
        island_dir = ISLAND_DIR[island]
        dc_folder  = f"results/driving_cycle/{island_dir}"
        pc_folder  = f"results/power_cycle/{island_dir}"
        sc_folder  = f"results/state_of_charge/{island_dir}"
        ov_folder  = f"results/overview/{island_dir}"
        for folder in (dc_folder, pc_folder, sc_folder, ov_folder):
            os.makedirs(folder, exist_ok=True)
        distances[island]        = {}
        band_kwh[island]         = {}
        grid_p_profiles[island]  = {}
        soc_ch_profiles[island]  = {}
        driving_profiles[island] = {}
        print(f"\n{'='*55}")
        print(f"  ISLA: {island}")
        print(f"{'='*55}")

        for sheet in VEHICLE_SHEETS:
            print(f"\n--- {sheet} ---")

            v, frr, theta = driving.generate_driving_profile(FULL_FILE, sheet, island=island)
            p_req, bat_cap = power.calculate_power(v, frr, theta, FULL_FILE, sheet)
            soc_no, _, _, _ = soc.calculate_soc(p_req, bat_cap, FULL_FILE, sheet, island=island)
            soc_ch, _, _, final_s, grid_e, grid_p = soc.calculate_soc_with_charging(
                p_req, bat_cap, FULL_FILE, sheet, island=island)

            dist_km = float(np.sum(v) / 3600.0)
            distances[island][sheet]        = dist_km
            driving_profiles[island][sheet] = (v.copy(), frr.copy(), theta.copy())

            band_kwh[island][sheet] = [
                float(np.sum(grid_p[i * BAND_SIZE:(i + 1) * BAND_SIZE]) / 3600)
                for i in range(8)
            ]
            grid_p_profiles[island][sheet]  = grid_p.copy()
            soc_ch_profiles[island][sheet]  = soc_ch.copy()

            print(f"  Distancia: {dist_km:.2f} km | Grid: {grid_e:.2f} kWh | SoC final: {final_s*100:.1f}%")

            safe_name = sheet.replace(" ", "_")
            time_h    = np.arange(86400) / 3600.0

            plot_daily_profile(v, sheet, island,
                               save_path=f"{dc_folder}/{safe_name}.png")
            plot_power_profile(p_req, sheet, island,
                               save_path=f"{pc_folder}/{safe_name}.png")
            plot_soc_profile(soc_no, soc_ch, bat_cap, grid_e, final_s, sheet, island,
                             save_path=f"{sc_folder}/{safe_name}.png")

            # --- Operational Overview (velocidad + potencia + SoC) ---
            fig1, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)
            ax1.plot(time_h, v, color="blue", linewidth=0.8)
            ax1.set_title(f"Model: {sheet} [{island}] — Operational Overview", fontsize=13)
            ax1.set_ylabel("Speed (km/h)")
            ax1.grid(True, linestyle="--", alpha=0.5)

            p_traction = np.where(p_req > 0, p_req, 0)
            p_regen    = np.where(p_req < 0, p_req, 0)
            ax2.plot(time_h, p_traction, color="red",    linewidth=0.6, label="Traction",  alpha=0.8)
            ax2.fill_between(time_h, p_traction, 0, color="red", alpha=0.15)
            ax2.plot(time_h, p_regen,    color="purple", linewidth=0.6, label="Regen",     alpha=0.8)
            ax2.fill_between(time_h, p_regen, 0, color="purple", alpha=0.15)
            ax2.plot(time_h, grid_p,     color="orange", linewidth=1.2, label="Grid",      linestyle="--")
            ax2.fill_between(time_h, grid_p, 0, color="orange", alpha=0.3)
            ax2.axhline(0, color="black", linewidth=0.8)
            ax2.set_ylabel("Power (kW)")
            ax2.legend(loc="upper right", fontsize="small", frameon=True)
            ax2.grid(True, linestyle="--", alpha=0.5)

            ax3.plot(time_h, soc_ch * 100, color="green", linewidth=1.5, label="SoC (with charging)")
            ax3.fill_between(time_h, soc_ch * 100, color="green", alpha=0.1)
            ax3.set_ylabel("SoC (%)")
            ax3.set_ylim(-5, 105)
            ax3.set_xlabel("Hora del día (h)")
            ax3.grid(True, linestyle="--", alpha=0.5)
            ax3.legend()

            plt.xlim(0, 24)
            plt.xticks(np.arange(0, 25, 1))
            fig1.tight_layout()
            fig1.savefig(f"{ov_folder}/{safe_name}_operational_overview.png", dpi=150)
            plt.close(fig1)

            # --- Charging Cycle (SoC sin/con carga) ---
            fig2, (ax_t, ax_b) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
            min_soc = np.nanmin(soc_no * 100)
            ax_t.plot(time_h, soc_no * 100, color="red", label="Sin carga (autonomía teórica)")
            ax_t.fill_between(time_h, soc_no * 100, color="red", alpha=0.1)
            ax_t.axhline(0, color="black", linewidth=1)
            ax_t.set_title(f"{sheet} [{island}] — Charging Cycle", fontsize=13)
            ax_t.set_ylabel("SoC (%)")
            ax_t.set_ylim(min(min_soc - 10, -10), 110)
            ax_t.grid(True, alpha=0.3)
            ax_t.legend()

            ax_b.plot(time_h, soc_ch * 100, color="green", label="Con carga de red")
            ax_b.fill_between(time_h, soc_ch * 100, color="green", alpha=0.1)
            ax_b.set_ylabel("SoC (%)")
            ax_b.set_xlabel("Hora del día (h)")
            ax_b.set_ylim(-5, 105)
            ax_b.grid(True, alpha=0.3)
            ax_b.legend()

            plt.xlim(0, 24)
            plt.xticks(np.arange(0, 25, 1))
            fig2.tight_layout()
            fig2.savefig(f"{ov_folder}/{safe_name}_charging_cycle.png", dpi=150)
            plt.close(fig2)

    # --- Escribir distancias en Q12:Q14 de cada hoja ---
    wb = openpyxl.load_workbook(FULL_FILE)
    for sheet in VEHICLE_SHEETS:
        ws = wb[sheet]
        for island, q_row in ISLAND_ROW.items():
            ws.cell(row=q_row, column=17, value=round(distances[island][sheet], 2))
    wb.save(FULL_FILE)
    print(f"\nDistancias guardadas en {FULL_FILE} (Q12:Q14 por hoja)")
    print("Imagenes guardadas en results/")

    return band_kwh, distances, grid_p_profiles, soc_ch_profiles, driving_profiles


if __name__ == "__main__":
    run_multi_island_analysis()
