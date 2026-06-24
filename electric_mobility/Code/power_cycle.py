import numpy as np
import matplotlib.pyplot as plt

from utils import load_vehicle_params


def calculate_power(v_24h, frr_profile, theta_24, excel_file, sheet_name):
    """Calcula el perfil de potencia eléctrica requerida para el vehículo dado."""
    tech_params = load_vehicle_params(excel_file, sheet_name)

    m = float(tech_params.get("Total Mass", 2300.0))
    Cd = float(tech_params.get("Drag Coefficient", 0.35))
    A = float(tech_params.get("Frontal Area", 2.8))
    eta_mot = float(tech_params.get("Motor efficiency", 0.90))
    eta_reg = float(tech_params.get("Generator efficiency", 0.70))
    k_rec = float(tech_params.get("Recovery factor", 0.50))
    battery_capacity_kwh = float(tech_params.get("Battery Capacity", 80.0))
    print(f"Parameters for {sheet_name}: Mass={m} kg, Cd={Cd}, A={A} m², "
          f"Motor Eff={eta_mot}, Reg Eff={eta_reg}, Recovery Factor={k_rec}, "
          f"Battery Cap={battery_capacity_kwh} kWh")

    g = 9.81
    rho = 1.225

    v_ms = v_24h / 3.6
    accel = np.diff(v_ms, prepend=0)

    F_roll = m * g * frr_profile * np.cos(theta_24)
    F_aero = 0.5 * rho * Cd * A * v_ms**2
    F_grad = m * g * np.sin(theta_24)
    F_accel = m * accel

    F_total = F_roll + F_aero + F_grad + F_accel
    p_wheels_kw = (F_total * v_ms) / 1000.0
    p_req_kw = np.zeros_like(p_wheels_kw)
    p_req_kw[p_wheels_kw > 0] = p_wheels_kw[p_wheels_kw > 0] / eta_mot
    p_req_kw[p_wheels_kw < 0] = p_wheels_kw[p_wheels_kw < 0] * eta_reg * k_rec

    return p_req_kw, battery_capacity_kwh


def plot_power_profile(p_req, sheet, island, zoom_start=14, zoom_end=17, save_path=None):
    time_axis = np.arange(86400) / 3600.0
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

    ax1.plot(time_axis, p_req, color="black", linewidth=0.7, alpha=0.3)
    ax1.fill_between(time_axis, p_req, 0, where=(p_req > 0),
                     color="tab:red", alpha=0.4, label="Power Demand (Traction)")
    ax1.fill_between(time_axis, p_req, 0, where=(p_req < 0),
                     color="tab:green", alpha=0.4, label="Energy Recovery (Regeneration)")
    ax1.axhline(0, color="black", linewidth=0.7)
    ax1.set_title(f"Required Electric Power Profile - {sheet} [{island}]", fontsize=14)
    ax1.set_ylabel("Power (kW)")
    ax1.set_xlim(0, 24)
    ax1.set_xticks(np.arange(0, 25, 1))
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(loc="upper right", frameon=True)

    zoom_mask = (time_axis >= zoom_start) & (time_axis <= zoom_end)
    ax2.plot(time_axis[zoom_mask], p_req[zoom_mask], color="black", linewidth=1)
    ax2.fill_between(time_axis[zoom_mask], p_req[zoom_mask], 0, where=(p_req[zoom_mask] > 0),
                     color="tab:red", alpha=0.3)
    ax2.fill_between(time_axis[zoom_mask], p_req[zoom_mask], 0, where=(p_req[zoom_mask] < 0),
                     color="tab:green", alpha=0.3)
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title(f"Power Detail ({zoom_start}h - {zoom_end}h)", fontsize=13)
    ax2.set_xlabel("Time of day (h)")
    ax2.set_ylabel("Power (kW)")
    ax2.grid(True, linestyle="--", alpha=0.6)

    plt.tight_layout()
    plt.subplots_adjust(hspace=0.25)
    if save_path:
        fig.savefig(save_path, dpi=150)
        plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":
    from driving_cycle import generate_driving_profile

    # ── Configuración ──────────────────────────────────────
    SHEET        = "PickUp"
    ISLAND       = "Santa Cruz"
    ZOOM_START_H = 14
    ZOOM_END_H   = 17
    # ───────────────────────────────────────────────────────

    FILE = "data/full_activity_profile.xlsx"
    v, frr, theta = generate_driving_profile(FILE, SHEET, island=ISLAND)
    p_req, cap = calculate_power(v, frr, theta, FILE, SHEET)
    plot_power_profile(p_req, SHEET, ISLAND, zoom_start=ZOOM_START_H, zoom_end=ZOOM_END_H)
