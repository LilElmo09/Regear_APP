"""
data.py — Capa de datos para precios de ítems.
Define DataSource (interfaz abstracta), CSVDataSource y APIDataSource.
"""
from __future__ import annotations

import csv
import datetime
import json
import os
import time
import urllib.request
from abc import ABC, abstractmethod

TIERS = ["T7", "T8", "T9", "T10", "T11"]

# Columnas del CSV que corresponden a cada tier
TIER_COL = {
    "T7": "precio_t7", "T8": "precio_t8",
    "T9": "precio_t9", "T10": "precio_t10", "T11": "precio_t11",
}

# Cabecera del CSV de precios
HEADER = ["nombre", "categoria", "api_id",
          "precio_t7", "precio_t8", "precio_t9", "precio_t10", "precio_t11"]

# Mapeo slot → categoría (None = sin ítems en el CSV)
SLOT_CATEGORY: dict[str, str | None] = {
    "arma":     "Arma",
    "offhand":  "Offhand",
    "casco":    "Casco",
    "armadura": "Armadura",
    "botas":    "Botas",
    "capa":     "Capa",
    "mochila":  "Mochila",
    "comida":   "Comida",
    "montura":  "Montura",
}

# Constantes AODP
AODP_URL      = "https://west.albion-online-data.com/api/v2/stats/prices"
AODP_CITY     = "Lymhurst"
AODP_QUALITY  = 2
AODP_COOLDOWN = 60   # segundos mínimos entre llamadas
AODP_BATCH    = 100  # IDs por request

# Mapeo tier app → (prefijo_albion, sufijo_encantamiento)
TIER_API = {
    "T7":  ("T7", ""),
    "T8":  ("T5", "@3"),
    "T9":  ("T6", "@3"),
    "T10": ("T7", "@3"),
    "T11": ("T8", "@3"),
}

# Keywords para clasificar ítems por categoría (fallback cuando el CSV no tiene categoria)
CATEGORY_KEYWORDS = {
    "Casco":    ["Hood", "Helmet", "Cowl"],
    "Armadura": ["Armor", "Robe", "Jacket"],
    "Botas":    ["Boots", "Sandals", "Shoes"],
    "Offhand":  ["Shield", "Cane", "Mistcaller", "Tome", "Taproot", "Facebreaker"],
    "Montura":  [
        "Caerleon", "Fort Sterling", "Keeper", "Lymhurst", "Martlock",
        "Morgana", "Swiftclaw", "Wild Boar", "Raven", "Divine Owl",
        "Armor Horse",
    ],
}
ALL_CATEGORIES = ["Arma", "Offhand", "Casco", "Armadura", "Botas",
                  "Capa", "Mochila", "Comida", "Montura"]


def _detect_category(name: str) -> str:
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name.lower():
                return cat
    return "Arma"


# ─────────────────────────────────────────────────────────── Interfaz abstracta

class DataSource(ABC):
    @abstractmethod
    def get_all(self) -> dict[str, dict]:
        """Retorna {nombre: {T7: int, ..., T11: int, api_id: str, categoria: str}}"""

    @abstractmethod
    def update(self, name: str, tier: str, price: int) -> None:
        """Actualiza el precio de un ítem en un tier específico."""

    @abstractmethod
    def create(self, name: str, prices: dict[str, int],
               api_id: str = "", categoria: str = "") -> None:
        """Agrega un nuevo ítem con sus precios por tier."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Elimina un ítem por nombre."""

    @abstractmethod
    def save(self) -> None:
        """Persiste los cambios al almacenamiento."""

    def get_items_by_category(self, category: str) -> list[str]:
        """Retorna los nombres de ítems de una categoría específica."""
        return [
            name for name, data in self.get_all().items()
            if data.get("categoria", _detect_category(name)) == category
        ]

    def get_category(self, name: str) -> str:
        data = self.get_all()
        if name in data:
            return data[name].get("categoria", _detect_category(name))
        return _detect_category(name)


# ──────────────────────────────────────────────────────────── CSV datasource

class CSVDataSource(DataSource):
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, dict] = {}
        if os.path.exists(path):
            try:
                self._load()
            except Exception as e:
                raise ValueError(f"Error al leer CSV {path}: {e}")

    def _load(self) -> None:
        self._data = {}
        try:
            with open(self._path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("nombre", "").strip()
                    if not name:
                        continue
                    prices = {t: int(row.get(TIER_COL[t], 0) or 0) for t in TIERS}
                    self._data[name] = {
                        **prices,
                        "api_id":    row.get("api_id", "").strip(),
                        "categoria": (row.get("categoria", "").strip()
                                      or _detect_category(name)),
                    }
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo CSV no encontrado: {self._path}")
        except ValueError as e:
            raise ValueError(f"Error de formato en CSV: {e}")

    def reload(self, path: str | None = None) -> None:
        if path:
            self._path = path
        self._load()

    def get_path(self) -> str:
        return self._path

    def get_all(self) -> dict[str, dict]:
        return dict(self._data)

    def update(self, name: str, tier: str, price: int) -> None:
        if name in self._data and tier in TIERS:
            self._data[name][tier] = price

    def create(self, name: str, prices: dict[str, int],
               api_id: str = "", categoria: str = "") -> None:
        self._data[name] = {
            **{t: prices.get(t, 0) for t in TIERS},
            "api_id":    api_id,
            "categoria": categoria or _detect_category(name),
        }

    def delete(self, name: str) -> None:
        self._data.pop(name, None)

    def save(self) -> None:
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            for name, data in self._data.items():
                writer.writerow({
                    "nombre":    name,
                    "categoria": data.get("categoria", _detect_category(name)),
                    "api_id":    data.get("api_id", ""),
                    **{TIER_COL[t]: data.get(t, 0) for t in TIERS},
                })


# ──────────────────────────────────────────────────────────── API datasource

class APIDataSource(DataSource):
    """
    Obtiene precios de la Albion Online Data Project API.
    Carga datos del CSV al inicializarse (sin llamada a la API).
    Los precios se actualizan solo al llamar a refresh().
    """

    def __init__(self, csv_path: str):
        self._csv = CSVDataSource(csv_path)
        self._data: dict[str, dict] = {k: dict(v)
                                       for k, v in self._csv.get_all().items()}
        self._last_fetch: float = 0.0
        self._status: str = "Sin actualizar — presiona Actualizar"

    # ── API pública ─────────────────────────────────────────────────────────

    def refresh(self) -> dict:
        """
        Consulta la AODP API y actualiza los precios en memoria.
        Respeta un cooldown de AODP_COOLDOWN segundos entre llamadas.
        
        Retorna un dict con estructura:
        {
            'success': bool,
            'message': str,  # Mensaje para mostrar
            'updated': int,  # Precios actualizados
            'errors': list[str],  # Errores
            'items_not_found': list[str],  # Items sin api_id
            'prices_zero': list[str],  # Items con precio 0
        }
        """
        now = time.time()
        elapsed = now - self._last_fetch
        if self._last_fetch > 0 and elapsed < AODP_COOLDOWN:
            remaining = int(AODP_COOLDOWN - elapsed)
            return {
                'success': False,
                'message': f"Espera {remaining}s antes de volver a actualizar",
                'updated': 0,
                'errors': [],
                'items_not_found': [],
                'prices_zero': [],
            }

        # Construir mapa full_api_id → (nombre_item, tier)
        item_map: dict[str, tuple[str, str]] = {}
        items_without_api_id: list[str] = []
        
        for name, data in self._data.items():
            base_id = data.get("api_id", "")
            if not base_id:
                items_without_api_id.append(name)
                continue
            for tier in TIERS:
                prefix, suffix = TIER_API[tier]
                full_id = f"{prefix}_{base_id}{suffix}"
                item_map[full_id] = (name, tier)

        if not item_map:
            return {
                'success': False,
                'message': "Ningún ítem tiene api_id — nada que actualizar",
                'updated': 0,
                'errors': [],
                'items_not_found': items_without_api_id,
                'prices_zero': [],
            }

        ids = list(item_map.keys())
        errors: list[str] = []
        updated = 0
        prices_zero: list[str] = []

        for i in range(0, len(ids), AODP_BATCH):
            batch = ids[i:i + AODP_BATCH]
            url = (f"{AODP_URL}/{','.join(batch)}"
                   f"?locations={AODP_CITY}&qualities={AODP_QUALITY}")
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    for entry in json.loads(resp.read()):
                        full_id = entry.get("item_id", "")
                        price   = entry.get("sell_price_min", 0)
                        if full_id in item_map:
                            name, tier = item_map[full_id]
                            if price > 0:
                                self._data[name][tier] = price
                                updated += 1
                            elif price == 0:
                                prices_zero.append(f"{name} ({tier})")
            except Exception as exc:
                errors.append(str(exc))

        self._last_fetch = time.time()
        
        ts = datetime.datetime.now().strftime("%H:%M")
        if errors:
            message = f"Error: {errors[0]}"
            success = False
        else:
            message = f"Actualizado a las {ts} ({updated} precios)"
            success = True
        
        self._status = message
        return {
            'success': success,
            'message': message,
            'updated': updated,
            'errors': errors,
            'items_not_found': items_without_api_id,
            'prices_zero': prices_zero,
        }

    def get_status(self) -> str:
        return self._status

    # ── DataSource interface ────────────────────────────────────────────────

    def get_path(self) -> str:
        return self._csv.get_path()

    def reload(self, path: str | None = None) -> None:
        if path:
            self._csv.reload(path)
        self._data = {k: dict(v) for k, v in self._csv.get_all().items()}
        self._last_fetch = 0.0
        self._status = "Sin actualizar — presiona Actualizar"

    def get_all(self) -> dict[str, dict]:
        return dict(self._data)

    def update(self, name: str, tier: str, price: int) -> None:
        if name in self._data and tier in TIERS:
            self._data[name][tier] = price

    def create(self, name: str, prices: dict[str, int],
               api_id: str = "", categoria: str = "") -> None:
        self._data[name] = {
            **{t: prices.get(t, 0) for t in TIERS},
            "api_id":    api_id,
            "categoria": categoria or _detect_category(name),
        }

    def delete(self, name: str) -> None:
        self._data.pop(name, None)

    def save(self) -> None:
        """Persiste los precios actualizados de vuelta al CSV (caché offline)."""
        self._csv._data = {k: dict(v) for k, v in self._data.items()}
        self._csv.save()
