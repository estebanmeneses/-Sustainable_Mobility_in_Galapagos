import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

from utils import to_sec, extract_island_data
from config import CHARGING_POWERS, CHARGING_EFFICIENCY


def calculate_soc(p_req_kw, battery_capacity_kwh, excel_file, sheet_name, island=None):
    """Calcula el perfil de SoC sin carga de red (descarga libre desde el inicio de jornada)."""
    if island is not None:
        activity_df, _ = extract_island_data(excel_file, sheet_name, island)
    else:
        activity_df = pd.read_excel(excel_file, sheet_name=sheet_name)
    first_start_time = activity_df.iloc[0, 0]
    start_sec = to_sec(first_start_time)
    start_hour_dec = start_sec / 3600.0
    print(f"Operational day for {sheet_name} starts at: {first_start_time} ({start_hour_dec:.2f}h)")

    time_step_h = 1.0 / 3600.0
    delta_energy_kwh = p_req_kw * time_step_h

    soc_profile = np.ones(86400)
    if start_sec < 86400:
        cumulative_energy_spent = np.cumsum(delta_energy_kwh[start_sec:])
        soc_profile[start_sec:] = 1.0 - (cumulative_energy_spent / battery_capacity_kwh)

    total_consumed = np.sum(delta_energy_kwh[delta_energy_kwh > 0])
    total_regeneration = np.abs(np.sum(delta_energy_kwh[delta_energy_kwh < 0]))
    final_soc = soc_profile[-1]

    return soc_profile, total_consumed, total_regeneration, final_soc


def calculate_soc_with_charging(p_req_kw, battery_capacity_kwh, excel_file, sheet_name, island=None):
    """Calcula el perfil de SoC con períodos de carga de red leídos desde el Excel."""
    if island is not None:
        activity_df, charging_df = extract_island_data(excel_file, sheet_name, island)
    else:
        activity_df = pd.read_excel(excel_file, sheet_name=sheet_name, usecols="A:E").dropna(how="all")
        charging_df = pd.read_excel(excel_file, sheet_name=sheet_name, usecols="I:L").dropna(how="all")

    start_sec = to_sec(activity_df.iloc[0, 0])

    time_step_h = 1.0 / 3600.0
    time_steps = 86400

    charging_periods = [
        {
            "start": to_sec(row.iloc[0]),
            "end": to_sec(row.iloc[1]),
            "power": CHARGING_POWERS.get(row.iloc[2], 0.0),
        }
        for _, row in charging_df.iterrows()
    ]

    soc_displaced = np.ones(time_steps)
    grid_power_displaced = np.zeros(time_steps)
    current_energy_kwh = battery_capacity_kwh
    total_grid_energy = 0.0

    for i in range(time_steps):
        t_real = (start_sec + i) % 86400

        p_grid = 0.0
        for period in charging_periods:
            if period["start"] > period["end"]:
                if t_real >= period["start"] or t_real <= period["end"]:
                    p_grid = period["power"]
                    break
            else:
                if period["start"] <= t_real <= period["end"]:
                    p_grid = period["power"]
                    break

        if p_grid > 0 and current_energy_kwh < battery_capacity_kwh:
            energy_needed = battery_capacity_kwh - current_energy_kwh
            actual_added = min(p_grid * time_step_h * CHARGING_EFFICIENCY, energy_needed)
            grid_power_displaced[i] = p_grid if actual_added > 0 else 0.0
            current_energy_kwh += actual_added
            total_grid_energy += actual_added / CHARGING_EFFICIENCY
        else:
            grid_power_displaced[i] = 0.0

        current_energy_kwh -= p_req_kw[t_real] * time_step_h
        current_energy_kwh = max(0.0, min(current_energy_kwh, battery_capacity_kwh))
        soc_displaced[i] = current_energy_kwh / battery_capacity_kwh

    soc_profile = np.zeros(time_steps)
    grid_power_profile = np.zeros(time_steps)
    for i in range(time_steps):
        t_real = (start_sec + i) % 86400
        soc_profile[t_real] = soc_displaced[i]
        grid_power_profile[t_real] = grid_power_displaced[i]

    time_step_h = 1.0 / 3600.0
    total_consumed = np.sum(p_req_kw[p_req_kw > 0]) * time_step_h
    total_regeneration = np.abs(np.sum(p_req_kw[p_req_kw < 0])) * time_step_h

    return soc_profile, total_consumed, total_regeneration, soc_profile[-1], total_grid_energy, grid_power_profile


def plot_soc_profile(soc_no, soc_ch, battery_cap, grid_e, final_s, sheet, island, save_path=None):
    time_h = np.arange(86400) / 3600.0
    fig, (ax_t, ax_b) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

    min_soc = np.nanmin(soc_no * 100)
    ax_t.plot(time_h, soc_no * 100, color="red", linewidth=1.5, label="Sin carga (autonomía teórica)")
    ax_t.fill_between(time_h, soc_no * 100, color="red", alpha=0.1)
    ax_t.axhline(0, color="black", linewidth=1)
    ax_t.set_title(f"{sheet} [{island}] — Ciclo de Carga Completo", fontsize=13)
    ax_t.set_ylabel("SoC (%)")
    ax_t.set_ylim(min(min_soc - 10, -10), 110)
    ax_t.grid(True, linestyle="--", alpha=0.4)
    ax_t.legend(loc="upper right")

    ax_b.plot(time_h, soc_ch * 100, color="green", linewidth=1.5, label="Con carga de red")
    ax_b.fill_between(time_h, soc_ch * 100, color="green", alpha=0.1)
    ax_b.set_ylabel("SoC (%)")
    ax_b.set_xlabel("Hora del día (h)")
    ax_b.set_ylim(-5, 105)
    ax_b.grid(True, linestyle="--", alpha=0.4)

    stats_info = (f"Capacidad batería: {battery_cap} kWh\n"
                  f"Energía de red: {grid_e:.2f} kWh\n"
                  f"SoC final: {final_s*100:.1f}%")
    ax_b.text(0.5, 5, stats_info, fontsize=10, verticalalignment="bottom",
              bbox=dict(facecolor="white", alpha=0.8, edgecolor="gray"))
    ax_b.legend(loc="upper right")

    plt.xlim(0, 24)
    plt.xticks(np.arange(0, 25, 1))
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    import driving_cycle as driving
    import power_cycle as power

    # ── Configuración ──────────────────────────────────────
    SHEET  = "PickUp"
    ISLAND = "Santa Cruz"
    # ───────────────────────────────────────────────────────

    FILE = "data/full_activity_profile.xlsx"
    v_profile, frr_profile, theta = driving.generate_driving_profile(FILE, SHEET, island=ISLAND)
    p_req, battery_cap = power.calculate_power(v_profile, frr_profile, theta, FILE, SHEET)
    soc_no, _, _, _                      = calculate_soc(p_req, battery_cap, FILE, SHEET, island=ISLAND)
    soc_ch, _, _, final_s, grid_e, grid_p = calculate_soc_with_charging(p_req, battery_cap, FILE, SHEET, island=ISLAND)
    plot_soc_profile(soc_no, soc_ch, battery_cap, grid_e, final_s, SHEET, ISLAND)
