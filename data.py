"""
data.py — Capa de datos para precios de ítems.
Define DataSource (interfaz abstracta) y CSVDataSource (implementación CSV).
"""
from __future__ import annotations

import csv
import os
from abc import ABC, abstractmethod

TIERS = ["T7", "T8", "T9", "T10"]

# Keywords para clasificar ítems por categoría
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
# Todo lo que no encaje en las anteriores cae en "Arma"
ALL_CATEGORIES = ["Arma", "Offhand", "Casco", "Armadura", "Botas", "Montura"]


def _detect_category(name: str) -> str:
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name.lower():
                return cat
    return "Arma"


class DataSource(ABC):
    @abstractmethod
    def get_all(self) -> dict[str, dict[str, int]]:
        """Retorna {nombre_item: {T7: int, T8: int, T9: int, T10: int}}"""

    @abstractmethod
    def update(self, name: str, tier: str, price: int) -> None:
        """Actualiza el precio de un ítem en un tier específico."""

    @abstractmethod
    def create(self, name: str, prices: dict[str, int]) -> None:
        """Agrega un nuevo ítem con sus precios por tier."""

    @abstractmethod
    def delete(self, name: str) -> None:
        """Elimina un ítem por nombre."""

    @abstractmethod
    def save(self) -> None:
        """Persiste los cambios al almacenamiento."""

    def get_items_by_category(self, category: str) -> list[str]:
        """Retorna los nombres de ítems cuyo precio en algún tier > 0."""
        items = self.get_all()
        return [
            name for name, prices in items.items()
            if _detect_category(name) == category
        ]

    def get_category(self, name: str) -> str:
        return _detect_category(name)


class CSVDataSource(DataSource):
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, dict[str, int]] = {}
        if os.path.exists(path):
            self._load()

    def _load(self) -> None:
        self._data = {}
        with open(self._path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row or not row[0].strip():
                    continue
                name = row[0].strip()
                prices = {}
                for i, tier in enumerate(TIERS):
                    try:
                        prices[tier] = int(row[i + 1].strip()) if i + 1 < len(row) else 0
                    except (ValueError, IndexError):
                        prices[tier] = 0
                self._data[name] = prices

    def reload(self, path: str | None = None) -> None:
        if path:
            self._path = path
        self._load()

    def get_path(self) -> str:
        return self._path

    def get_all(self) -> dict[str, dict[str, int]]:
        return dict(self._data)

    def update(self, name: str, tier: str, price: int) -> None:
        if name in self._data and tier in TIERS:
            self._data[name][tier] = price

    def create(self, name: str, prices: dict[str, int]) -> None:
        self._data[name] = {t: prices.get(t, 0) for t in TIERS}

    def delete(self, name: str) -> None:
        self._data.pop(name, None)

    def save(self) -> None:
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for name, prices in self._data.items():
                row = [name] + [str(prices.get(t, 0)) for t in TIERS]
                writer.writerow(row)
