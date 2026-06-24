import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SPEED_LIMIT_URBAN, SPEED_LIMIT_RURAL


def load_wltc_cycle(class_num: int):
    """Carga y escala el ciclo WLTC para la clase dada (1, 2 o 3).

    Retorna (city_phase_data, highway_phase_data) como DataFrames con
    las velocidades ya escaladas a los límites de Galápagos.
    """
    csv_path = os.path.join("data_cycles", f"data_class{class_num}.csv")
    df = pd.read_csv(csv_path)

    df_clean = df.drop(0).copy()
    df_clean.columns = ["Phase", "Time", "PhaseTime", "Speed", "Accel_ms2", "Accel_kmhs"]
    df_clean["Time"] = pd.to_numeric(df_clean["Time"])
    df_clean["Speed"] = pd.to_numeric(df_clean["Speed"])

    city = df_clean[df_clean["Phase"] == "Low"].copy().reset_index(drop=True)
    highway = df_clean[df_clean["Phase"] == "Middle"].copy().reset_index(drop=True)

    city["Speed"] = city["Speed"] * (SPEED_LIMIT_URBAN / city["Speed"].max())
    highway["Speed"] = highway["Speed"] * (SPEED_LIMIT_RURAL / highway["Speed"].max())
    highway["Time"] = highway["Time"] - highway["Time"].iloc[0]

    return city, highway
