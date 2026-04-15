# RegearApp — Albion Online

Aplicación de escritorio en Python (Tkinter) para calcular costos de regear en Albion Online. Permite pre-configurar builds, calcular el costo total por tier y gestionar los precios e ítems desde la propia interfaz. Soporta precios manuales (CSV) y precios en vivo desde la **Albion Online Data Project API**.

## Cómo ejecutar

```bash
# Instalar dependencias (solo la primera vez)
./instalar.sh

# Lanzar la app
./lanzar.sh
# o manualmente:
cd regear_app && python3 main.py
```

## Estructura del proyecto

```
RegearAPP/
├── instalar.sh                          # Instala dependencias del sistema (tk)
├── lanzar.sh                            # Lanzador rápido (generado por instalar.sh)
├── MAGA Regear Charts - Price Charts.csv # Datos de precios (fuente de verdad + caché API)
└── regear_app/
    ├── main.py          # Punto de entrada — ventana principal con 3 pestañas
    ├── data.py          # Capa de datos: DataSource (ABC) + CSVDataSource + APIDataSource
    ├── presets.py       # Gestión de presets: CSVPresetSource + defaults
    ├── calculator.py    # Lógica de cálculo: calculate_total()
    ├── ui_calculator.py # Pestaña 1 — Calculadora de regear
    ├── ui_prices.py     # Pestaña 2 — CRUD de precios + selector CSV/API
    ├── ui_presets.py    # Pestaña 3 — CRUD de presets
    └── presets.csv      # Builds pre-configurados (generado automáticamente)
```

## Arquitectura

### Capa de datos (`data.py`)
- `DataSource` (ABC): interfaz abstracta con `get_all()`, `update()`, `create()`, `delete()`, `save()`
- `CSVDataSource`: implementa `DataSource` leyendo/escribiendo el CSV de precios
- `APIDataSource`: implementa `DataSource` obteniendo precios en vivo desde la AODP API, con caché en el CSV

### Formato del CSV de precios
```
nombre,categoria,api_id,precio_t7,precio_t8,precio_t9,precio_t10,precio_t11
Bloodletter,Arma,2H_DAGGERPAIR_MORGANA,115000,308000,650000,1450000,0
Stalker Hood,Casco,HEAD_LEATHER_STALKER,71000,169000,255000,460000,0
```
- Con cabecera
- `0` = ítem no disponible en ese tier
- `api_id` = ID base del ítem en la AODP (sin prefijo de tier), usado para consultar precios en vivo

### Tiers soportados
| Columna | Albion Online |
|---------|--------------|
| T7      | T7 base       |
| T8      | T8 base       |
| T9      | T8 + encant. 1 |
| T10     | T8 + encant. 2 |
| T11     | T8 + encant. 3 |

### Categorías de ítems (campo explícito en el CSV)
| Categoría | Descripción |
|-----------|-------------|
| Arma      | Armas principales|
| Offhand   | Escudos, tomos, bastones, etc. |
| Casco     | Cascos, capuchas, capas de mago |
| Armadura  | Armaduras, robas, chaquetas |
| Botas     | Botas, sandalias, zapatos |
| Capa      | Capas |
| Mochila   | Mochilas |
| Comida    | Consumibles de comida |
| Montura   | Monturas |

### Slots de equipo (9 total)
`arma`, `offhand`, `casco`, `armadura`, `botas`, `capa`, `mochila`, `comida`, `montura`

Cada slot muestra **solo los ítems de su categoría** en los dropdowns de la Calculadora y del editor de Presets.

### Lógica del porcentaje
`total_final = Σ(precios ítems habilitados) × (porcentaje / 100)`

El campo `%` representa qué fracción del costo total se calcula (100% = precio completo).

### Presets (`presets.csv`)
- Columnas: `nombre, arma, offhand, casco, armadura, botas, capa, mochila, comida, montura`
- Se genera con presets por defecto si el archivo no existe
- Al crear/editar/eliminar un preset, los botones de la Pestaña 1 se actualizan en tiempo real

## Integración con la AODP API

La app puede obtener precios en vivo desde la [Albion Online Data Project](https://www.albion-online-data.com/).

**Parámetros:**
- Ciudad: `Lymhurst`
- Calidad: `2` (Good)

**Cómo usarla:**
1. Abrir la Pestaña 2 (Gestión de Precios)
2. Seleccionar el radio button **"API (AODP)"**
3. Presionar el botón **"↻ Actualizar"** para obtener precios en vivo

**Comportamiento:**
- Al cambiar a modo API, los precios del CSV se mantienen como caché (sin llamada a la red)
- La llamada a la API ocurre solo al presionar "↻ Actualizar"
- Cooldown de 60 segundos entre actualizaciones para no sobrecargar la API
- Solo se consultan los ítems que tienen `api_id` en el CSV
- Si la API no responde, los precios del CSV se conservan
- Al guardar en modo API, los precios obtenidos se persisten en el CSV

**Construcción de IDs para la API:**
```
T7  → T7_{api_id}
T8  → T8_{api_id}
T9  → T8_{api_id}@1
T10 → T8_{api_id}@2
T11 → T8_{api_id}@3
```

## Flujo entre pestañas

```
main.py (RegearApp)
  ├── CalculatorFrame   ←── on_prices_loaded()  ──→  PricesFrame
  │        ↑                                              ↑
  │   refresh_presets()                    on_data_changed() / on_source_changed()
  │        │                                              │
  └── PresetsFrame  ←── on_presets_changed() ────────────┘
```

- `_on_prices_loaded`: cuando se carga el CSV desde la Calculadora, notifica a Precios y Presets
- `_on_prices_data_changed`: cuando se edita un precio en Pestaña 2, actualiza los dropdowns de Pestaña 1
- `_on_presets_changed`: cuando se crea/edita/elimina un preset en Pestaña 3, refresca los botones de Pestaña 1
- `_on_source_changed`: cuando se cambia entre CSV y API en Pestaña 2, intercambia el datasource en todas las pestañas

## Dependencias

Solo librería estándar de Python — sin pip, sin requirements.txt:
- `tkinter` + `tkinter.ttk` — GUI
- `csv`, `os`, `abc` — datos y sistema
- `urllib.request`, `json`, `time`, `datetime` — integración con la API AODP
