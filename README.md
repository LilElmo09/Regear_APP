# RegearApp — Albion Online

Aplicación de escritorio en Python (Tkinter) para calcular costos de regear en Albion Online. Permite pre-configurar builds, calcular el costo total por tier y gestionar los precios e ítems desde la propia interfaz.

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
├── MAGA Regear Charts - Price Charts.csv # Datos de precios (fuente de verdad)
└── regear_app/
    ├── main.py          # Punto de entrada — ventana principal con 3 pestañas
    ├── data.py          # Capa de datos: DataSource (ABC) + CSVDataSource
    ├── presets.py       # Gestión de presets: CSVPresetSource + defaults
    ├── calculator.py    # Lógica de cálculo: calculate_total()
    ├── ui_calculator.py # Pestaña 1 — Calculadora de regear
    ├── ui_prices.py     # Pestaña 2 — CRUD de precios
    ├── ui_presets.py    # Pestaña 3 — CRUD de presets
    └── presets.csv      # Builds pre-configurados (generado automáticamente)
```

## Arquitectura

### Capa de datos (`data.py`)
- `DataSource` (ABC): interfaz abstracta con `get_all()`, `update()`, `create()`, `delete()`, `save()`
- `CSVDataSource`: implementa `DataSource` leyendo/escribiendo el CSV de precios
- La interfaz está diseñada para agregar fácilmente una implementación de API en el futuro

### Formato del CSV de precios
```
Nombre_Item, PrecioT7, PrecioT8, PrecioT9, PrecioT10
Bloodletter, 115000, 308000, 650000, 1450000
```
- Sin cabecera
- `0` = ítem no disponible en ese tier
- 118 ítems: armas, cascos, armaduras, botas, offhand, monturas

### Categorías de ítems (inferidas por keywords)
| Categoría | Keywords en el nombre |
|-----------|----------------------|
| Casco     | Hood, Helmet, Cowl   |
| Armadura  | Armor, Robe, Jacket  |
| Botas     | Boots, Sandals, Shoes|
| Offhand   | Shield, Cane, Mistcaller, Tome, Taproot, Facebreaker |
| Montura   | Caerleon, Fort Sterling, Swiftclaw, etc. |
| Arma      | todo lo demás        |

### Slots de equipo (9 total)
`arma`, `offhand`, `casco`, `armadura`, `botas`, `capa`, `mochila`, `comida`, `montura`

### Lógica del porcentaje
`total_final = Σ(precios ítems habilitados) × (porcentaje / 100)`

El campo `%` representa qué fracción del costo total se calcula (100% = precio completo).

### Presets (`presets.csv`)
- Columnas: `nombre, arma, offhand, casco, armadura, botas, capa, mochila, comida, montura`
- Se genera con 28 presets por defecto si el archivo no existe
- Al crear/editar/eliminar un preset, los botones de la Pestaña 1 se actualizan en tiempo real

## Flujo entre pestañas

```
main.py (RegearApp)
  ├── CalculatorFrame   ←── on_prices_loaded()  ──→  PricesFrame
  │        ↑                                              ↑
  │   refresh_presets()                         on_data_changed()
  │        │                                              │
  └── PresetsFrame  ←── on_presets_changed() ────────────┘
```

- `_on_prices_loaded`: cuando se carga el CSV desde la Calculadora, notifica a Precios y Presets
- `_on_prices_data_changed`: cuando se edita un precio en Pestaña 2, actualiza los dropdowns de Pestaña 1
- `_on_presets_changed`: cuando se crea/edita/elimina un preset en Pestaña 3, refresca los botones de Pestaña 1

## Dependencias

Solo librería estándar de Python — sin pip, sin requirements.txt:
- `tkinter` + `tkinter.ttk` — GUI
- `csv`, `os`, `abc` — datos y sistema

Dependencia del sistema: `tk` (paquete del SO)
- Arch/CachyOS/Manjaro: `sudo pacman -S tk`
- Ubuntu/Debian: `sudo apt install python3-tk`
- Fedora: `sudo dnf install python3-tkinter`

## Trabajo futuro

- **Integración con API de Albion Online Data Project**: `data.py` ya tiene la interfaz `DataSource` preparada. Solo hay que implementar `APIDataSource(DataSource)` y conectarla al selector CSV/API de la Pestaña 2.
- El selector de fuente (radio buttons CSV / API) ya existe en la UI — la opción API está deshabilitada con mensaje "Próximamente".
