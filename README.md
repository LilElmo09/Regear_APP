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
    ├── data.py          # Capa de datos: DataSource (ABC) + CSVDataSource + APIDataSource
    ├── presets.py       # Gestión de presets: CSVPresetSource + defaults
    ├── calculator.py    # Lógica de cálculo: calculate_total()
    ├── ui_calculator.py # Pestaña 1 — Calculadora de regear
    ├── ui_prices.py     # Pestaña 2 — CRUD de precios
    └── ui_presets.py    # Pestaña 3 — CRUD de presets
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
| Arma      | Armas principales |
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

## Pestaña 1 — Calculadora

- Selección de ítem y tier por slot, con checkbox para habilitar/deshabilitar
- Botones T7–T11 para cambiar el tier de todos los slots a la vez
- Tick All / Untick All para habilitar o deshabilitar todos los slots
- Campo de porcentaje y botón CALCULATE
- Grilla de presets: un clic carga el build en los slots

Los precios se cargan automáticamente al iniciar la app si el CSV existe.

## Pestaña 2 — Gestión de Precios

- Tabla con todas las columnas del CSV: **Ítem**, **Categoría**, **API ID**, **T7–T11**
- **Doble clic** en una celda de precio para editar inline
- **"Editar"** abre un diálogo completo para modificar todos los campos del ítem (nombre, categoría, api_id y precios por tier)
- **"+ Nuevo ítem"** abre el mismo diálogo para agregar un ítem nuevo
- **"Eliminar"** elimina el ítem seleccionado
- **"Guardar"** persiste los cambios al CSV
- **"↻ Actualizar"** consulta la AODP API en segundo plano y actualiza todos los precios; muestra una barra de progreso animada mientras carga y el botón se deshabilita hasta que termina
- Barra de búsqueda para filtrar ítems por nombre

## Pestaña 3 — Gestión de Presets

- Tabla con el nombre del preset y los ítems asignados a cada slot
- **"+ Nuevo Preset"** / **"Editar seleccionado"** / **"Eliminar"**
- El diálogo de edición muestra un combobox por slot, filtrado por la categoría correspondiente

## Integración con la AODP API

`APIDataSource` está disponible en `data.py` para obtener precios en vivo desde la [Albion Online Data Project](https://www.albion-online-data.com/).

**Parámetros:** Calidad: `2` (Good), escala temporal: `24h`, últimos `30` días

**Construcción de IDs para la API:**
```
T7  → T7_{api_id}
T8  → T5_{api_id}@3
T9  → T6_{api_id}@3
T10 → T7_{api_id}@3
T11 → T8_{api_id}@3
```

**Comportamiento:**
- Carga datos del CSV al inicializarse (sin llamada a la red)
- `refresh()` agrupa todos los IDs en batches de 50 y los consulta en pocas requests a la AODP, actualizando precios en memoria
- Reintentos automáticos con backoff exponencial (hasta 4 reintentos) si la API devuelve 429
- Cooldown de 60 segundos entre actualizaciones
- Solo consulta ítems que tienen `api_id` en el CSV
- Si la API no responde, los precios del CSV se conservan
- `save()` persiste los precios obtenidos de vuelta al CSV (caché offline)

**Rendimiento:**
| Modo | Requests | Tiempo estimado |
|------|----------|-----------------|
| Antiguo (1 request/ID) | ~1,250 | ~42 min |
| Actual (batch de 50) | ~25 | < 1 min |

## Flujo entre pestañas

```
main.py (RegearApp)
  ├── CalculatorFrame  ←── set_datasource() / refresh_presets()
  ├── PricesFrame      ←── on_data_changed()
  └── PresetsFrame     ←── on_presets_changed()
```

- `_on_prices_data_changed`: cuando se edita/crea/elimina un ítem en Pestaña 2, actualiza los dropdowns de Pestaña 1
- `_on_presets_changed`: cuando se crea/edita/elimina un preset en Pestaña 3, refresca los botones de Pestaña 1

## Dependencias

Solo librería estándar de Python — sin pip, sin requirements.txt:
- `tkinter` + `tkinter.ttk` — GUI
- `csv`, `os`, `abc` — datos y sistema
- `urllib.request`, `json`, `gzip`, `time`, `datetime` — integración con la API AODP
- `threading` — actualización de precios en segundo plano sin bloquear la UI
