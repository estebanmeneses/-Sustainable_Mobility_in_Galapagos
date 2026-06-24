import matplotlib.pyplot as plt
import numpy as np
import pickup_driving_cycle as driving
import power_cycle as power
import state_of_charge as soc
from config import FLEET_COMPOSITION

def run_batch_analysis(excel_file, vehicle_sheets):
    fleet_grid_profiles = {}
    for sheet in vehicle_sheets:
        print(f"\n--- Analizando modelo: {sheet} ---")
        
        # 1. Obtener perfiles de base
        v_24h, frr_profile, theta_24 = driving.generate_driving_profile(excel_file, sheet)
        time_h = np.arange(86400) / 3600.0
        
        # 2. Calcular Potencia requerida y capacidad
        p_req_kw, battery_cap = power.calculate_power(v_24h, frr_profile, theta_24, excel_file, sheet)

        # 3. Calcular perfiles de SoC
        soc_no_charge, _, _, _ = soc.calculate_soc(p_req_kw, battery_cap, excel_file, sheet)
        soc_with_charge, consumed, regen, final_s, grid_energy, grid_p_profile = soc.calculate_soc_with_charging(
            p_req_kw, battery_cap, excel_file, sheet
        )

        # Guardar perfil para el análisis de flota
        fleet_grid_profiles[sheet] = grid_p_profile

        # --- GRÁFICA 1: Perfil Operativo (suspendida) ---
        if True:
            fig1, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12), sharex=True)

            ax1.plot(time_h, v_24h, color='blue', linewidth=0.8)
            ax1.set_title(f'Model: {sheet} - Operational Overview')
            ax1.set_ylabel('Speed (km/h)')
            ax1.grid(True, linestyle='--', alpha=0.5)

            p_traction = np.where(p_req_kw > 0, p_req_kw, 0)
            ax2.plot(time_h, p_traction, color='red', linewidth=0.6, label='Motor Traction (Consumption)', alpha=0.8)
            ax2.fill_between(time_h, p_traction, 0, color='red', alpha=0.15)

            p_regen = np.where(p_req_kw < 0, p_req_kw, 0)
            ax2.plot(time_h, p_regen, color='purple', linewidth=0.6, label='Regenerative Braking (Recovery)', alpha=0.8)
            ax2.fill_between(time_h, p_regen, 0, color='purple', alpha=0.15)

            ax2.plot(time_h, grid_p_profile, color='orange', linewidth=1.2, label='Grid Charging Power', linestyle='--')
            ax2.fill_between(time_h, grid_p_profile, 0, color='orange', alpha=0.3)

            ax2.axhline(0, color='black', linewidth=0.8)
            ax2.set_ylabel('Power (kW)')
            ax2.set_title(f'Power Consumption Profile - {sheet}')
            ax2.grid(True, linestyle='--', alpha=0.5)
            ax2.legend(loc='upper right', fontsize='small', frameon=True, shadow=True)

            ax3.plot(time_h, soc_with_charge * 100, color='green', linewidth=1.5, label='SoC (with Charging)')
            ax3.fill_between(time_h, soc_with_charge * 100, color='green', alpha=0.1)
            ax3.set_title('State of Charge Profile')
            ax3.set_ylabel('SoC (%)')
            ax3.set_ylim(-5, 105)
            ax3.grid(True, linestyle='--', alpha=0.5)
            ax3.legend()

            plt.xlim(0, 24)
            plt.xticks(np.arange(0, 25, 1))
            fig1.tight_layout()

        # --- GRÁFICA 2: Comparativa de Autonomía (suspendida) ---
        if True:
            fig2, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)

            min_soc_val = np.min(soc_no_charge * 100)
            ax_top.plot(time_h, soc_no_charge * 100, color='red', label='Theoretical SoC (No Charging)')
            ax_top.fill_between(time_h, soc_no_charge * 100, color='red', alpha=0.1)
            ax_top.axhline(0, color='black', linewidth=1)
            ax_top.set_title(f'Energy Autonomy: No Charging - Model: {sheet}')
            ax_top.set_ylabel('SoC (%)')
            ax_top.set_ylim(min(min_soc_val - 10, -10), 110)
            ax_top.grid(True, alpha=0.3)
            ax_top.legend()

            ax_bot.plot(time_h, soc_with_charge * 100, color='green', label='Realistic SoC (With Grid Charging)')
            ax_bot.fill_between(time_h, soc_with_charge * 100, color='green', alpha=0.1)
            ax_bot.set_title(f'Operational Energy: Including Planned Charging Periods - Model: {sheet}')
            ax_bot.set_ylabel('SoC (%)')
            ax_bot.set_xlabel('Time of Day (h)')
            ax_bot.set_ylim(-5, 105)
            ax_bot.grid(True, alpha=0.3)
            ax_bot.legend()

            plt.xlim(0, 24)
            plt.xticks(np.arange(0, 25, 1))
            fig2.tight_layout()
        
        # Resumen técnico
        distancia_total = np.sum(v_24h) / 3600.0
        print(f"Total Distance Traveled: {distancia_total:.2f} km")
        print(f"Max Power Request: {np.max(p_req_kw):.2f} kW")
        print(f"Energy taken from Grid: {grid_energy:.2f} kWh")
        print(f"Final SoC (at 23:59): {final_s*100:.2f}%")

    print("\n--- Generando Análisis de Flota Agregada (100 vehículos) ---")
    plot_fleet_total_consumption(fleet_grid_profiles)


def plot_fleet_total_consumption(fleet_data):
    """Grafica la energía consumida por la flota en franjas de 3 horas (kWh apilado por tipo)."""
    n_bands = 8
    band_size = 3 * 3600          # segundos por franja
    time_step_h = 1.0 / 3600.0
    band_labels = [f"{h:02d}:00\n{h+3:02d}:00" for h in range(0, 24, 3)]
    x = np.arange(n_bands)
    bar_width = 1

    _, ax = plt.subplots(figsize=(13, 7))
    bottom = np.zeros(n_bands)
    total_band_energy = np.zeros(n_bands)

    for model, info in FLEET_COMPOSITION.items():
        if model in fleet_data:
            count = info["count"]
            profile = fleet_data[model]
            band_energy = np.array([
                np.sum(profile[i * band_size:(i + 1) * band_size]) * time_step_h * count
                for i in range(n_bands)
            ])
            ax.bar(x, band_energy, bottom=bottom, width=bar_width,
                   label=f'{count}x {model}', color=info["color"],
                   alpha=0.88, edgecolor='gray', linewidth=0.5)
            bottom += band_energy
            total_band_energy += band_energy

    # Valor de kWh encima de cada barra
    for i, val in enumerate(total_band_energy):
        if val > 0:
            ax.text(i, val + total_band_energy.max() * 0.01, f"{val:.1f}",
                    ha='center', va='bottom', fontsize=9, fontweight='bold')

    total_day_energy = total_band_energy.sum()

    ax.set_title('Total Fleet Energy Demand — 3-Hour Bands', fontsize=14)
    ax.set_xlabel('Time of Day', fontsize=12)
    ax.set_ylabel('Energy Demand (kWh)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(band_labels, fontsize=10)
    ax.set_ylim(0, total_band_energy.max() * 1.18)
    ax.grid(True, linestyle='--', alpha=0.4, axis='y')
    ax.legend(loc='upper right', frameon=True)
    ax.text(0.98, 0.97, f"Total Daily Energy: {total_day_energy:.2f} kWh",
            transform=ax.transAxes, ha='right', va='top', fontsize=11,
            bbox=dict(facecolor='white', alpha=0.85, edgecolor='gray'))

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    archivo = 'activity_profile.xlsx'
    hojas_modelos = ['SUV', 'Heavy Truck', 'PickUp', 'Bus', 'Motorcycle', 'Micromobilidad']
    #hojas_modelos = ['PickUp']
    run_batch_analysis(archivo, hojas_modelos)