import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
import os

from config import FRR_ASPHALTED, FRR_GRAVEL
from utils import to_sec, load_vehicle_params, extract_island_data
from data_cycles.wltc_loader import load_wltc_cycle
from data_cycles.whvc_loader import load_whvc_cycle

ISLAND_FOLDER = {
    "San Cristobal": "San_Cristobal",
    "Isabela":       "Isabela",
    "Santa Cruz":    "Santa_Cruz",
}


def fill_window(profile_array, start_time, end_time, phase_data):
    t_start, t_end = to_sec(start_time), to_sec(end_time)
    duration = t_end - t_start
    if duration <= 0:
        return profile_array
    n_reps = duration // len(phase_data)
    remainder = duration % len(phase_data)
    tiled_data = np.tile(phase_data, int(n_reps))
    if remainder > 0:
        tiled_data = np.concatenate([tiled_data, phase_data[:int(remainder)]])
    profile_array[t_start:t_end] = tiled_data
    return profile_array


def calculate_split_time(start_t, end_t, fraction):
    s_start, s_end = to_sec(start_t), to_sec(end_t)
    s_res = s_start + int((s_end - s_start) * fraction)
    return f"{s_res // 3600:02d}:{(s_res % 3600) // 60:02d}:{s_res % 60:02d}"


def load_and_resample_theta(csv_name, target_duration, island_folder=""):
    if island_folder:
        file_path = os.path.join("elevation_data", island_folder, f"{csv_name}.csv")
    else:
        file_path = os.path.join("elevation_data", f"{csv_name}.csv")
    try:
        df_route = pd.read_csv(file_path)
        orig_time = df_route["time_s"].values
        orig_theta = df_route["theta_rad"].values
        new_time = np.linspace(0, orig_time[-1], target_duration)
        f_interp = interp1d(orig_time, orig_theta, fill_value="extrapolate")
        return f_interp(new_time)
    except FileNotFoundError:
        print(f"Warning: File {csv_name}.csv not found. Using theta=0.")
        return np.zeros(target_duration)


def generate_driving_profile(file_path, sheet_name, island=None):
    """Genera v_24h, frr_profile y theta_24h para una hoja (y opcionalmente una isla)."""
    tech_params = load_vehicle_params(file_path, sheet_name)
    pmr  = float(tech_params.get("Power to Tare Mass Ratio (PMR)", 0))
    mass = float(tech_params.get("Total Mass", 0))

    use_whvc = mass > 6000

    if use_whvc:
        cycle_label = "WHVC"
        city_phase, highway_phase = load_whvc_cycle()
    else:
        if pmr <= 22:
            v_class, class_num = "Class 1", 1
        elif pmr <= 34:
            v_class, class_num = "Class 2", 2
        else:
            v_class, class_num = "Class 3", 3
        cycle_label = f"WLTC {v_class}"
        city_phase, highway_phase = load_wltc_cycle(class_num)

    print(f"Vehicle on sheet '{sheet_name}' — Mass: {mass:.0f} kg, PMR: {pmr:.2f} — Cycle: {cycle_label}")

    island_folder = ISLAND_FOLDER.get(island, "") if island else ""
    city_vel    = city_phase["Speed"].values
    highway_vel = highway_phase["Speed"].values

    v_24h = np.zeros(86400)
    frr_profile = np.zeros(86400)
    theta_24h = np.zeros(86400)

    if island is not None:
        activity_df, _ = extract_island_data(file_path, sheet_name, island)
    else:
        activity_df = pd.read_excel(file_path, sheet_name=sheet_name)

    for _, row in activity_df.iterrows():
        start_t, end_t = row.iloc[0], row.iloc[1]
        route_type = str(row.iloc[2]).strip().lower()
        road_quality = str(row.iloc[3]).strip().lower()
        elevation_route = str(row.iloc[4]).strip()

        t_start_idx, t_end_idx = to_sec(start_t), to_sec(end_t)
        duration = t_end_idx - t_start_idx
        if duration <= 0:
            continue

        frr_profile[t_start_idx:t_end_idx] = FRR_ASPHALTED if road_quality == "asphalted" else FRR_GRAVEL

        if route_type == "low":
            v_24h = fill_window(v_24h, start_t, end_t, city_vel)
        elif route_type == "medium":
            v_24h = fill_window(v_24h, start_t, end_t, highway_vel)
        elif route_type == "mixed":
            m1 = calculate_split_time(start_t, end_t, 0.25)
            m2 = calculate_split_time(start_t, end_t, 0.50)
            m3 = calculate_split_time(start_t, end_t, 0.75)
            v_24h = fill_window(v_24h, start_t, m1, city_vel)
            v_24h = fill_window(v_24h, m1, m2, highway_vel)
            v_24h = fill_window(v_24h, m2, m3, city_vel)
            v_24h = fill_window(v_24h, m3, end_t, highway_vel)

        if elevation_route not in ("-", "nan"):
            theta_24h[t_start_idx:t_end_idx] = load_and_resample_theta(elevation_route, duration, island_folder)

    return v_24h, frr_profile, theta_24h


def plot_daily_profile(v_24h, sheet, island, zoom_start=14, zoom_end=17, save_path=None):
    time_h = np.arange(86400) / 3600.0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    ax1.plot(time_h, v_24h, color="black", linewidth=0.7, label="Vehicle Speed")
    ax1.set_title(f"Daily Activity Profile - {sheet} [{island}]")
    ax1.set_ylabel("Speed (km/h)")
    ax1.set_xlim(0, 24)
    ax1.set_xticks(range(0, 25))
    ax1.legend(loc="upper right", frameon=True)
    ax1.grid(True, linestyle="--", alpha=0.5)

    mask = (time_h >= zoom_start) & (time_h <= zoom_end)
    ax2.plot(time_h[mask], v_24h[mask], color="red", linewidth=0.8)
    ax2.set_title(f"Speed Detail ({zoom_start}h - {zoom_end}h)")
    ax2.set_ylabel("Speed (km/h)")
    ax2.set_xlabel("Time of Day (h)")
    ax2.set_xlim(zoom_start, zoom_end)
    ax2.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    # ── Configuración ──────────────────────────────────────
    SHEET        = "PickUp"
    ISLAND       = "Santa Cruz"
    ZOOM_START_H = 14
    ZOOM_END_H   = 17
    # ───────────────────────────────────────────────────────

    v_24h, _, _ = generate_driving_profile("data/full_activity_profile.xlsx", SHEET, island=ISLAND)
    print(f"Total Distance: {np.sum(v_24h) / 3600.0:.2f} km")
    plot_daily_profile(v_24h, SHEET, ISLAND, zoom_start=ZOOM_START_H, zoom_end=ZOOM_END_H)
