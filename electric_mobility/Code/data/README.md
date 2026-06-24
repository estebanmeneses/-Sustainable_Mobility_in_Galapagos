# Datos de entrada

Esta carpeta contiene los archivos de entrada del modelo:

| Archivo | Descripción |
|---|---|
| `full_activity_profile.xlsx` | Perfil de actividad, carga y parámetros técnicos por vehículo e isla |
| `Prospectiva_Transporte_T_Galapagos.xlsx` | Proyecciones de flota EV por escenario (Low / Medium / High), isla y año |

---

## `full_activity_profile.xlsx`

Este archivo define el comportamiento diario de cada tipo de vehículo: cuándo y cómo se mueve, cuándo se carga, y cuáles son sus parámetros físicos. El código lo lee pero **solo escribe en Q12:Q14** (distancias calculadas); el resto puede editarse libremente.

---

## Estructura del archivo

El libro tiene **6 hojas**, una por tipo de vehículo:

`SUV` · `Truck` · `PickUp` · `Bus` · `Motorcycle` · `Micromobilidad`

Dentro de cada hoja hay **3 bloques apilados**, uno por isla, en este orden:
1. San Cristóbal
2. Isabela
3. Santa Cruz

---

## Sección de actividad (trayectos)

Cada fila representa un trayecto dentro del día. Las columnas son:

| Columna | Contenido | Valores válidos |
|---|---|---|
| A | Etiqueta / descripción del trayecto | texto libre |
| B | Hora de inicio | `HH:MM:SS` |
| C | Hora de fin | `HH:MM:SS` |
| D | Tipo de ruta | `Low` · `Medium` · `Mixed` |
| E | Tipo de vía | `Asphalted` · `Gravel` |
| F | Archivo de elevación (sin `.csv`) | nombre de archivo en `elevation_data/<Isla>/` · `-` si no aplica |
| G | Notas / descripción | texto libre (ignorado por el código) |

**Sobre el tipo de ruta:**
- `Low` → usa el ciclo de conducción urbano (velocidad máx. 35 km/h)
- `Medium` → usa el ciclo de conducción de carretera (velocidad máx. 80 km/h)
- `Mixed` → divide el trayecto en 4 segmentos: Low 25% · Medium 25% · Low 25% · Medium 25%

**Sobre el archivo de elevación:**
- El nombre debe corresponder a un archivo `.csv` dentro de `elevation_data/<Isla>/`
- Si no existe o se pone `-`, el código asume pendiente cero (plano)

---

## Sección de carga

Cada fila define una ventana de carga durante el día:

| Columna | Contenido | Valores válidos |
|---|---|---|
| I | Hora de inicio de carga | `HH:MM:SS` |
| J | Hora de fin de carga | `HH:MM:SS` |
| K | Tipo de cargador | ver tabla abajo |
| L | Notas | texto libre (ignorado) |

**Tipos de cargador disponibles** (definidos en `config.py`):

| Tipo | Potencia |
|---|---|
| `Fast` | 80 kW |
| `Semi-Fast` | 25 kW |
| `Home` | 8 kW |
| `Heavy-vehicle` | 50 kW |
| `Motorcycle` | 0.42 kW |
| `Micromobility` | 0.084 kW |

---

## Parámetros técnicos del vehículo

Se ubican a la derecha de la hoja. La columna O contiene el nombre del parámetro y la columna P su valor numérico.

| Parámetro | Descripción |
|---|---|
| `Total Mass` | Masa total del vehículo [kg] — determina si se usa WLTC o WHVC (umbral: 6 000 kg) |
| `Battery Capacity` | Capacidad de la batería [kWh] |
| `Power to Tare Mass Ratio (PMR)` | Relación potencia/masa en vacío — determina la clase WLTC (1/2/3) |
| `Motor Power` | Potencia máxima del motor [kW] |
| `Drag Coefficient` | Coeficiente aerodinámico (Cd) |
| `Frontal Area` | Área frontal del vehículo [m²] |
| `Wheel Radius` | Radio de la rueda [m] |
| `Regenerative Braking Efficiency` | Eficiencia del frenado regenerativo (0–1) |

---

## Columnas de solo lectura (escritas por el código)

| Celda | Contenido |
|---|---|
| Q12 | Distancia diaria calculada — San Cristóbal [km] |
| Q13 | Distancia diaria calculada — Isabela [km] |
| Q14 | Distancia diaria calculada — Santa Cruz [km] |

> Estas celdas se sobreescriben cada vez que se corre `main.py`. No editarlas manualmente.
