import os
import sys
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SPEED_LIMIT_URBAN, SPEED_LIMIT_RURAL


def load_whvc_cycle():
    """Carga y escala el ciclo WHVC (vehículos pesados).

    La columna 'time' contiene tiempo acumulado en segundos (timestamps).
    Se ordenan los puntos, se normaliza el eje de tiempo a 0 e interpola
    a resolución de 1 segundo.

    Retorna (urban_phase, rural_phase) como DataFrames con columna 'Speed'
    escaladas a los límites de velocidad de Galápagos.
    """
    csv_path = os.path.join("data_cycles", "data_whvc.csv")
    df = pd.read_csv(csv_path, header=None, names=["zone", "time", "speed"])

    urban_raw = df[df["zone"] == "Urban"].sort_values("time").reset_index(drop=True)
    rural_raw = df[df["zone"] == "Rural"].sort_values("time").reset_index(drop=True)

    def to_1sec_profile(phase_df: pd.DataFrame) -> pd.DataFrame:
        times  = phase_df["time"].values
        speeds = phase_df["speed"].values
        t0     = times[0]
        times_norm = times - t0                     # normalizar a 0
        t_end  = int(np.ceil(times_norm[-1]))
        t_uniform = np.arange(0, t_end + 1)
        f = interp1d(times_norm, speeds, kind="linear",
                     bounds_error=False,
                     fill_value=(speeds[0], speeds[-1]))
        return pd.DataFrame({"Speed": f(t_uniform).astype(float)})

    urban = to_1sec_profile(urban_raw)
    rural = to_1sec_profile(rural_raw)

    urban["Speed"] = urban["Speed"] * (SPEED_LIMIT_URBAN / urban["Speed"].max())
    rural["Speed"] = rural["Speed"] * (SPEED_LIMIT_RURAL / rural["Speed"].max())

    return urban, rural
