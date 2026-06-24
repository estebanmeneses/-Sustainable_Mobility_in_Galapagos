import pandas as pd

ISLANDS = ["San Cristobal", "Isabela", "Santa Cruz"]


def to_sec(s) -> int:
    """Convierte un valor time-like de Excel a segundos del día."""
    if pd.isna(s):
        return 0
    if not isinstance(s, str):
        return s.hour * 3600 + s.minute * 60 + s.second
    parts = list(map(int, s.split(":")))
    if len(parts) == 2:
        return parts[0] * 3600 + parts[1] * 60
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0


def load_vehicle_params(excel_file: str, sheet_name: str) -> dict:
    """Lee los parámetros técnicos del vehículo desde columnas O:P del Excel."""
    params_df = pd.read_excel(excel_file, sheet_name=sheet_name, usecols="O:P")
    params_df.columns = ["param", "value"]
    params_df = params_df.dropna(subset=["param"])
    return {str(k).strip(): v for k, v in zip(params_df["param"], params_df["value"])}


def extract_island_data(file_path: str, sheet_name: str, island_name: str):
    """Extrae filas de actividad y carga para una isla específica de una hoja multi-isla.

    Retorna (activity_df, charging_df) donde:
      activity_df columnas: 0=Start, 1=End, 2=RouteType, 3=RoadQuality, 4=Elevation
      charging_df columnas: 0=Start, 1=End, 2=ChargeType, 3=Explanation
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name)
    col_a = df.iloc[:, 0].astype(str)

    island_rows = df.index[col_a.str.contains(island_name, na=False)].tolist()
    if not island_rows:
        raise ValueError(f"Isla '{island_name}' no encontrada en hoja '{sheet_name}'")
    start_idx = island_rows[0] + 1

    other_islands = [i for i in ISLANDS if i != island_name]
    next_idxs = [r for r in df.index
                 if r > island_rows[0] and any(x in str(df.iloc[r, 0]) for x in other_islands)]
    end_idx = next_idxs[0] if next_idxs else len(df)

    # Cols B-F (posiciones 1-5): Start, End, RouteType, Road, Elevation
    activity_df = df.iloc[start_idx:end_idx, 1:6].reset_index(drop=True).dropna(how="all")
    activity_df.columns = range(5)

    # Cols I-L (posiciones 8-11): Start, End, ChargeType, Explanation
    charging_df = df.iloc[start_idx:end_idx, 8:12].reset_index(drop=True).dropna(how="all")
    charging_df.columns = range(4)

    return activity_df, charging_df
