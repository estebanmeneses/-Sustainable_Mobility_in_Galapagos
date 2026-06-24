# Simulación de Demanda Energética — Flota EV Galápagos

Modelo de simulación en Python que estima la **potencia y energía diaria** requerida por la red eléctrica para cargar cada tipo de vehículo expuesto y de una flota completa de vehículos eléctricos en las Islas Galápagos (San Cristóbal, Isabela, Santa Cruz). Combina ciclos de conducción estandarizados, perfiles de actividad por tipo de vehículo y proyecciones de flota por escenario (Bajo / Medio / Alto) para el período 2019–2050.

---

## Estructura del proyecto

```
Code/
├── main.py                    Punto de entrada — corre el análisis completo
├── vehicle_cycle.py           Simulación por vehículo × isla (ciclo + carga + SoC)
├── fleet_power.py             Escala resultados por flota; genera potencia/energía en MW
├── driving_cycle.py           Genera perfil de velocidad de 24 h a partir del activity profile
├── power_cycle.py             Calcula potencia mecánica requerida (tracción + regen)
├── state_of_charge.py         Simula el estado de carga de la batería con y sin carga
├── utils.py                   Funciones auxiliares compartidas
├── config.py                  Parámetros globales editables (velocidades, potencias de carga…)
│
├── data/                      Datos de entrada  →  ver data/README.md
│   ├── full_activity_profile.xlsx                Perfil de actividad y parámetros técnicos por vehículo
│   ├── Prospectiva_Transporte_T_Galapagos.xlsx   Proyecciones de flota por escenario
│   └── Justificacion.docx                        Análisis y justificación de los perfiles de actividad
│
├── data_cycles/               Ciclos de conducción estandarizados
│   ├── data_class1/2/3.csv    WLTC clases 1–3 (vehículos livianos, masa ≤ 6 000 kg)
│   ├── data_whvc.csv          WHVC (vehículos pesados, masa > 6 000 kg)
│   ├── wltc_loader.py         Cargador del ciclo WLTC
│   └── whvc_loader.py         Cargador del ciclo WHVC
│
├── elevation_data/            Perfiles de elevación de rutas por isla
│   ├── San_Cristobal/
│   ├── Isabela/
│   └── Santa_Cruz/
│
├── output/                    Archivos generados por el código (no editar manualmente)
│   ├── energia_por_vehiculo.xlsx   Energía consumida en kWh por franja horaria (8 franjas × 32 años)
│   ├── fleet_results.pkl           Resultados de flota serializados (potencia + energía)
│   └── plot_fleet_query.py         Script de exploración interactiva de resultados
│
├── results/                   Gráficas generadas automáticamente
│   ├── driving_cycle/         Perfil de velocidad diaria por vehículo e isla
│   │   ├── San_Cristobal/
│   │   ├── Isabela/
│   │   └── Santa_Cruz/
│   ├── power_cycle/           Perfil de potencia mecánica por vehículo e isla
│   │   ├── San_Cristobal/
│   │   ├── Isabela/
│   │   └── Santa_Cruz/
│   ├── state_of_charge/       SoC sin carga y con carga de red por vehículo e isla
│   │   ├── San_Cristobal/
│   │   ├── Isabela/
│   │   └── Santa_Cruz/
│   ├── overview/              Vista combinada (velocidad + potencia + SoC) por vehículo e isla
│   │   ├── San_Cristobal/
│   │   ├── Isabela/
│   │   └── Santa_Cruz/
│   └── fleet_power/           Potencia y energía de flota completa por isla y año
│
└── archive/                   Código obsoleto (no se usa en el pipeline activo)
```

---

## Pipeline de cálculo

```
python main.py
       │
       ├─ vehicle_cycle.run_multi_island_analysis()
       │       Para cada isla × tipo de vehículo:
       │       driving_cycle    →  velocidad 24 h (WLTC o WHVC según masa)
       │       power_cycle      →  potencia mecánica requerida
       │       state_of_charge  →  SoC + potencia de red (grid_p, kW)
       │       → Guarda gráficas en results/
       │       → Retorna band_kwh, distances, grid_p_profiles
       │
       ├─ write_energy_excel(band_kwh)
       │       Escribe output/energia_por_vehiculo.xlsx
       │       (8 franjas de 3 h, mismos kWh para todos los años 2019–2050)
       │
       └─ fleet_power.run(grid_p_profiles)
               Para cada escenario × isla:
               grid_p [kW] × conteo de flota → potencia total [MW]
               cumsum → energía acumulada [MWh]
               → Guarda output/fleet_results.pkl
               → Genera gráficas en results/fleet_power/
```

**Selección automática de ciclo de conducción:**
- Masa > 6 000 kg → **WHVC** (urbano máx. 35 km/h · carretera máx. 80 km/h)
- Masa ≤ 6 000 kg → **WLTC** clase 1 / 2 / 3 según PMR (≤22 / ≤34 / >34)

**Tipo de ruta en el activity profile:**
- `Low` → ciclo urbano
- `Medium` → ciclo de carretera
- `Mixed` → 25% urbano · 25% carretera · 25% urbano · 25% carretera

---

## Cómo usar

### 1. Ajustar los datos de entrada

- **Perfil de actividad y parámetros técnicos** → `data/full_activity_profile.xlsx`
  Horarios de conducción, tipo de vía, rutas de elevación, ventanas de carga y parámetros técnicos del vehículo.
  Consultar **[data/README.md](data/README.md)** para la descripción detallada de cada columna.

- **Proyecciones de flota** → `data/Prospectiva_Transporte_T_Galapagos.xlsx`
  Contiene 3 hojas (`Flota_low_text`, `Flota_medium_text`, `Flota_high_text`) con el número de vehículos eléctricos por tipo, isla y año.

### 2. Ajustar parámetros globales (`config.py`)

| Parámetro | Descripción | Valor por defecto |
|---|---|---|
| `SPEED_LIMIT_URBAN` | Velocidad máxima ciclo urbano (km/h) | 35 |
| `SPEED_LIMIT_RURAL` | Velocidad máxima ciclo carretera (km/h) | 80 |
| `FRR_ASPHALTED` | Coeficiente de resistencia rodadura — asfalto | 0.01 |
| `FRR_GRAVEL` | Coeficiente de resistencia rodadura — ripio | 0.025 |
| `CHARGING_POWERS` | Potencias de carga por tipo (kW) | Fast=80, Semi-Fast=25, Home=8, … |
| `CHARGING_EFFICIENCY` | Eficiencia de carga | 0.9 |

### 3. Ajustar el año de las gráficas de flota (`fleet_power.py`)

```python
PLOT_YEAR = 2030   # ← cambiar al año deseado (2019–2050)
```

### 4. Correr el análisis completo

```bash
python main.py
```

Genera todos los outputs (Excel, pkl, gráficas PNG) en las carpetas `output/` y `results/`.

### 5. Explorar resultados interactivamente (`output/plot_fleet_query.py`)

Editar las 3 variables al inicio del archivo:

```python
YEAR     = 2030
ISLAND   = "Santa Cruz"   # "San Cristobal" | "Isabela" | "Santa Cruz" | "Galápagos"
SCENARIO = "High"         # "Low" | "Medium" | "High"
```

Luego ejecutar:

```bash
python output/plot_fleet_query.py
```

Muestra la gráfica de potencia + energía para esa combinación y deja los arrays
`potencia_mw` y `energia_mwh` (86 400 valores, uno por segundo del día) disponibles en memoria.

> **Nota:** requiere que `output/fleet_results.pkl` exista (se genera al correr `main.py`).

---

## Outputs generados

| Archivo / carpeta | Descripción |
|---|---|
| `output/energia_por_vehiculo.xlsx` | Energía consumida en kWh por isla, vehículo y franja horaria (8 franjas de 3 h) |
| `output/fleet_results.pkl` | Arrays de potencia [MW] y energía [MWh] para toda la flota — 32 años × 86 400 s × 3 escenarios × 4 zonas |
| `results/driving_cycle/<Isla>/<Vehículo>.png` | Perfil de velocidad diaria (24 h + zoom de detalle) |
| `results/power_cycle/<Isla>/<Vehículo>.png` | Potencia mecánica requerida (tracción y regeneración) |
| `results/state_of_charge/<Isla>/<Vehículo>.png` | SoC sin carga (autonomía teórica) y con carga de red |
| `results/overview/<Isla>/<Vehículo>_operational_overview.png` | Vista combinada: velocidad + potencia + SoC |
| `results/overview/<Isla>/<Vehículo>_charging_cycle.png` | Ciclo de carga completo (sin/con red) |
| `results/fleet_power/<Isla>_<Año>.png` | Potencia y energía de la flota completa por escenario |
