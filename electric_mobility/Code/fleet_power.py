import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

FLEET_FILE = "data/Prospectiva_Transporte_T_Galapagos.xlsx"
YEARS      = list(range(2019, 2051))
PLOT_YEAR  = 2030   # editable

SCENARIOS = {
    "Low":    "Flota_low_text",
    "Medium": "Flota_medium_text",
    "High":   "Flota_high_text",
}

SHEET_TO_FLEET = {
    "SUV":            "SUV",
    "Truck":          "Truck",
    "PickUp":         "PickUp",
    "Bus":            "Bus",
    "Motorcycle":     "Motorcycle",
    "Micromobilidad": "Micromobilidad",
}

FLEET_NAME_MAP = {
    "PickUp":         "Camioneta (taxi)-electrica",
    "SUV":            "Vehículo eléctrico -electricidad",
    "Bus":            "Bus y furgoneta - electrica",
    "Motorcycle":     "Motocicleta-electrica",
    "Micromobilidad": "Micromo",
}

HEAVY_TRUCK_ROWS = [
    "Camión- electrico",
    "Especial (tanqueros, volquetas, etc.)-electrica",
]

SCENARIO_COLORS = {
    "Low":    "#5dade2",
    "Medium": "#f39c12",
    "High":   "#27ae60",
}

CALC_ISLANDS = ["San Cristobal", "Isabela", "Santa Cruz", "Galápagos"]

# Nombres exactos en el Excel de prospectiva (con tildes)
ISLAND_EXCEL_NAME = {
    "San Cristobal": "San Cristóbal",
    "Isabela":       "Isabela",
    "Santa Cruz":    "Santa Cruz",
}


def read_island_section(fleet_sheet_name: str, island_name: str) -> pd.DataFrame:
    df    = pd.read_excel(FLEET_FILE, sheet_name=fleet_sheet_name)
    col0  = df.columns[0]
    mask  = df[col0].astype(str).str.contains(island_name, na=False)
    pos   = int(df[mask].index[0])
    section = df.iloc[pos + 1: pos + 17].copy().set_index(col0)
    year_cols = [c for c in section.columns
                 if isinstance(c, (int, float)) and 2019 <= int(c) <= 2050]
    section = section[year_cols].fillna(0)
    section.columns = [int(c) for c in section.columns]
    return section


def get_counts(section: pd.DataFrame, fleet_name: str) -> np.ndarray:
    idx     = section.index.astype(str)
    matches = [i for i in idx if fleet_name.strip().lower() in i.strip().lower()]
    if not matches:
        print(f"    ADVERTENCIA: '{fleet_name}' no encontrado en sección de flota")
        return np.zeros(len(YEARS))
    return section.loc[matches[0]].reindex(YEARS, fill_value=0).values.astype(float)


def run(grid_p_profiles: dict):
    """Calcula la potencia y energía de flota por isla y escenario.

    Args:
        grid_p_profiles: {island: {sheet: np.ndarray(86400)}} en kW

    Returns:
        all_power  : {island: {scenario: np.ndarray(32, 86400)}} en MW
        all_energy : {island: {scenario: np.ndarray(32, 86400)}} en MWh acumulado
    """
    real_islands = ["San Cristobal", "Isabela", "Santa Cruz"]
    all_power    = {isl: {} for isl in CALC_ISLANDS}
    all_energy   = {isl: {} for isl in CALC_ISLANDS}

    for scenario_name, fleet_sheet in SCENARIOS.items():
        print(f"\nEscenario: {scenario_name}")

        for island in real_islands:
            print(f"  {island}...")
            section      = read_island_section(fleet_sheet, ISLAND_EXCEL_NAME[island])
            power_matrix = np.zeros((len(YEARS), 86400))

            for vc_sheet, fleet_key in SHEET_TO_FLEET.items():
                grid_p = grid_p_profiles[island][vc_sheet]   # kW, 86400 elementos

                if fleet_key == "Truck":
                    counts = (get_counts(section, HEAVY_TRUCK_ROWS[0]) +
                              get_counts(section, HEAVY_TRUCK_ROWS[1]))
                else:
                    counts = get_counts(section, FLEET_NAME_MAP[fleet_key])

                for y_idx, count in enumerate(counts):
                    power_matrix[y_idx] += grid_p * count

            power_matrix /= 1000.0   # kW → MW
            all_power[island][scenario_name] = power_matrix

        # Galápagos = suma de las 3 islas
        galapagos = sum(all_power[isl][scenario_name] for isl in real_islands)
        all_power["Galápagos"][scenario_name] = galapagos

    # Energía acumulada en MWh para todas las islas
    for island in CALC_ISLANDS:
        for scenario_name, pm in all_power[island].items():
            em = np.zeros_like(pm)
            for y_idx in range(len(YEARS)):
                em[y_idx] = np.cumsum(pm[y_idx]) / 3600.0
            all_energy[island][scenario_name] = em

    plot_results(all_power, all_energy)
    return all_power, all_energy


def save_results(all_power: dict, all_energy: dict, path: str = "output/fleet_results.pkl") -> None:
    import pickle
    with open(path, "wb") as f:
        pickle.dump({"power": all_power, "energy": all_energy, "years": YEARS}, f)
    print(f"Resultados guardados en {path}")


def load_results(path: str = "output/fleet_results.pkl") -> tuple:
    import pickle
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["power"], data["energy"], data["years"]


def plot_results(all_power: dict, all_energy: dict) -> None:
    import os
    output_dir = os.path.join("results", "fleet_power")
    os.makedirs(output_dir, exist_ok=True)

    year_idx   = YEARS.index(PLOT_YEAR)
    time_h     = np.arange(86400) / 3600.0
    scenarios  = list(SCENARIO_COLORS.keys())   # orden fijo: Low, Medium, High

    for island in CALC_ISLANDS:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), sharex=True)
        fig.suptitle(f"Flota eléctrica — {island} ({PLOT_YEAR})", fontsize=14)

        # Calcular offset vertical como 1.5 % del rango de potencia
        p_vals  = np.concatenate([all_power[island][s][year_idx] for s in scenarios])
        p_range = p_vals.max() - p_vals.min()
        p_step  = p_range * 0.015

        e_vals  = np.concatenate([all_energy[island][s][year_idx] for s in scenarios])
        e_range = e_vals.max() - e_vals.min()
        e_step  = e_range * 0.015

        for i, scenario_name in enumerate(scenarios):
            color  = SCENARIO_COLORS[scenario_name]
            offset = i * p_step
            ax1.plot(time_h, all_power[island][scenario_name][year_idx] + offset,
                     color=color, linewidth=1.2, label=scenario_name)

        ax1.set_ylabel("Potencia (MW)")
        ax1.set_title("Potencia requerida de la red")
        ax1.legend(loc="upper right", frameon=True)
        ax1.grid(True, linestyle="--", alpha=0.4)

        for i, scenario_name in enumerate(scenarios):
            color  = SCENARIO_COLORS[scenario_name]
            offset = i * e_step
            ax2.plot(time_h, all_energy[island][scenario_name][year_idx] + offset,
                     color=color, linewidth=1.2, label=scenario_name)

        ax2.set_ylabel("Energía acumulada (MWh)")
        ax2.set_xlabel("Hora del día (h)")
        ax2.set_title("Energía consumida acumulada desde medianoche")
        ax2.legend(loc="upper left", frameon=True)
        ax2.grid(True, linestyle="--", alpha=0.4)

        plt.xlim(0, 24)
        plt.xticks(np.arange(0, 25, 1))
        fig.tight_layout()

        safe_island = island.replace(" ", "_").replace("á", "a").replace("ó", "o")
        fig.savefig(os.path.join(output_dir, f"{safe_island}_{PLOT_YEAR}.png"), dpi=150)

