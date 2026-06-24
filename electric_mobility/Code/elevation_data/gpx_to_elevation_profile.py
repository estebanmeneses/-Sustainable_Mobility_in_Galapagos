import numpy as np
import matplotlib.pyplot as plt
import gpxpy
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
import pandas as pd


def extract_elevation_profile(gpx_file):
    with open(gpx_file, 'r') as f:
        gpx = gpxpy.parse(f)

    distances = [0.0]
    elevations = []
    prev_point = None

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                elevations.append(point.elevation)

                if prev_point:
                    d = point.distance_3d(prev_point)
                    distances.append(distances[-1] + d)

                prev_point = point

    return np.array(distances), np.array(elevations)


def resample_uniform_distance(distances, elevations, step=50):
    """
    Remuestrea a distancia uniforme (ej: cada 50 m)
    """
    new_dist = np.arange(0, distances[-1], step)
    f = interp1d(distances, elevations, fill_value="extrapolate")
    new_elev = f(new_dist)
    return new_dist, new_elev


def theta_from_gpx(distances, elevations):
    """
    Calcula θ(s) con filtrado robusto
    """
    # Filtrado fuerte para evitar ruido en derivada
    window = min(11, len(elevations) - 1)
    if window % 2 == 0:
        window -= 1

    elevations_smooth = savgol_filter(elevations, window, 3)

    dx = np.diff(distances)
    dh = np.diff(elevations_smooth)

    dx[dx < 1e-3] = 1e-3

    slope = dh / dx
    theta = np.arctan(slope)

    # Limitar valores físicamente posibles (±10°)
    theta = np.clip(theta, np.radians(-10), np.radians(10))

    theta = np.append(theta, theta[-1])

    return theta, elevations_smooth


def resample_theta_to_time(theta_dist, distances, total_time_s, dt=1.0):
    total_distance = distances[-1]

    time_axis = np.arange(0, total_time_s, dt)
    distance_time = (time_axis / total_time_s) * total_distance

    f_theta = interp1d(distances, theta_dist, fill_value="extrapolate")
    theta_time = f_theta(distance_time)

    return time_axis, theta_time


def plot_profiles(distances, elevations, theta_dist, time_axis, theta_time):
    fig, axs = plt.subplots(3, 1, figsize=(12, 10))

    theta_dist_deg = np.degrees(theta_dist)
    theta_time_deg = np.degrees(theta_time)

    # Elevación
    axs[0].plot(distances / 1000, elevations)
    axs[0].set_title('Elevation Profile')
    axs[0].set_ylabel('Elevation (m)')
    axs[0].set_xlabel('Distance (km)')
    axs[0].grid(True)

    # Theta vs distancia
    axs[1].plot(distances / 1000, theta_dist_deg)
    axs[1].set_title('Slope Angle θ (vs Distance)')
    axs[1].set_ylabel('Theta (deg)')
    axs[1].set_xlabel('Distance (km)')
    axs[1].grid(True)

    # Theta vs tiempo
    axs[2].plot(time_axis / 3600, theta_time_deg)
    axs[2].set_title('Slope Angle θ (vs Time)')
    axs[2].set_ylabel('Theta (deg)')
    axs[2].set_xlabel('Time (h)')
    axs[2].grid(True)

    plt.tight_layout()
    plt.show()

def save_theta_profile(time_axis, theta_time, filename="Ayora-Bellavista.csv"):
    """
    Guarda los datos de tiempo y ángulo de inclinación en un archivo CSV.
    """
    df = pd.DataFrame({
        'time_s': time_axis,
        'theta_rad': theta_time
    })
    df.to_csv(filename, index=False)
    print(f"Archivo guardado exitosamente como: {filename}")

if __name__ == "__main__":
    gpx_file = "elevation_data/San_Cristobal/La Loberia- Parroquia El Progresso - Puerto Baquerizo Moreno.gpx"

    # 1. Leer GPX
    dist_raw, elev_raw = extract_elevation_profile(gpx_file)

    # 2. Remuestrear (CLAVE)
    dist, elev = resample_uniform_distance(dist_raw, elev_raw, step=50)

    # 3. Calcular theta robusto
    theta_dist, elev_smooth = theta_from_gpx(dist, elev)

    # 4. Mapear a tiempo (ej: 1 hora)
    time_axis, theta_time = resample_theta_to_time(
        theta_dist, dist, total_time_s=3600
    )

    # --- NUEVO PASO: Guardar CSV ---
    save_theta_profile(time_axis, theta_time, "elevation_data/San_Cristobal/Loberia-PuertoBaquerizo.csv")

    # 5. Graficar
    plot_profiles(dist, elev_smooth, theta_dist, time_axis, theta_time)