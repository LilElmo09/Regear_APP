"""
presets.py — Gestión de presets (builds pre-configurados).
Almacena y carga los presets desde presets.csv.
"""
from __future__ import annotations

import csv
import os

SLOTS = ["arma", "offhand", "casco", "armadura", "botas", "capa", "mochila", "comida", "montura"]

# Presets por defecto
DEFAULT_PRESETS: dict[str, dict[str, str]] = {
    "Bloodletter":  {"arma": "Bloodletter",  "offhand": "Mistcaller",     "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Grovekeeper":  {"arma": "Grovekeeper",  "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Camlann":      {"arma": "Camlann",      "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Soulscythe":   {"arma": "Soulscythe",   "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Grailseeker":  {"arma": "Grailseeker",  "offhand": "Mistcaller",     "casco": "Specter Hood",  "armadura": "Cleric Robe",      "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "1h Mace":      {"arma": "1h Mace",      "offhand": "Tome of Spells", "casco": "Guardian Helmet","armadura": "Guardian Armor",  "botas": "Guardian Boots",  "capa": "", "mochila": "", "comida": "", "montura": ""},
    "HoJ":          {"arma": "Hand of Justice","offhand": "Tome of Spells","casco": "Judicator Helmet","armadura": "Judicator Armor","botas": "Cleric Sandals",  "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Fallen":       {"arma": "Fallen",       "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Wild":         {"arma": "Wild",         "offhand": "Mistcaller",     "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Blight":       {"arma": "Blight",       "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Shotcaller":   {"arma": "Siegebow",     "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "1h Arcane":    {"arma": "1h Arcane",    "offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Lifecurse":    {"arma": "Lifecurse",    "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Locus":        {"arma": "Locus",        "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Icicle":       {"arma": "Icicle",       "offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Occult":       {"arma": "Occult",       "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Enigmatic":    {"arma": "Enigmatic",    "offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Damnation":    {"arma": "Damnation",    "offhand": "",               "casco": "Specter Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Brimstone":    {"arma": "Brimstone",    "offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Mistpiercer":  {"arma": "Mistpiercer",  "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Energyshaper": {"arma": "Energy Shaper","offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Permafrost":   {"arma": "Permafrost",   "offhand": "Mistcaller",     "casco": "Scholar Cowl",  "armadura": "Scholar Robe",     "botas": "Scholar Sandals", "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Spirithunter": {"arma": "Spirithunter", "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Greataxe":     {"arma": "Greataxe",     "offhand": "",               "casco": "Guardian Helmet","armadura": "Soldier Armor",   "botas": "Guardian Boots",  "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Bridled Fury": {"arma": "Bridled Fury", "offhand": "",               "casco": "Guardian Helmet","armadura": "Soldier Armor",   "botas": "Guardian Boots",  "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Galatine":     {"arma": "Galatine",     "offhand": "",               "casco": "Guardian Helmet","armadura": "Knight Armor",    "botas": "Guardian Boots",  "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Siegebow":     {"arma": "Siegebow",     "offhand": "",               "casco": "Stalker Hood",  "armadura": "Specter Jacket",   "botas": "Stalker Shoes",   "capa": "", "mochila": "", "comida": "", "montura": ""},
    "Realmbreaker": {"arma": "Realmbreaker", "offhand": "",               "casco": "Guardian Helmet","armadura": "Knight Armor",    "botas": "Guardian Boots",  "capa": "", "mochila": "", "comida": "", "montura": ""},
}


class CSVPresetSource:
    def __init__(self, path: str):
        self._path = path
        self._presets: dict[str, dict[str, str]] = {}
        if os.path.exists(path):
            self._load()
        else:
            self._presets = {k: dict(v) for k, v in DEFAULT_PRESETS.items()}
            self.save()

    def _load(self) -> None:
        self._presets = {}
        with open(self._path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("nombre", "").strip()
                if not name:
                    continue
                self._presets[name] = {
                    slot: row.get(slot, "").strip() for slot in SLOTS
                }

    def get_all(self) -> dict[str, dict[str, str]]:
        return {k: dict(v) for k, v in self._presets.items()}

    def create(self, nombre: str, slot_map: dict[str, str]) -> None:
        self._presets[nombre] = {slot: slot_map.get(slot, "") for slot in SLOTS}

    def update(self, nombre: str, slot_map: dict[str, str]) -> None:
        if nombre in self._presets:
            self._presets[nombre] = {slot: slot_map.get(slot, "") for slot in SLOTS}

    def delete(self, nombre: str) -> None:
        self._presets.pop(nombre, None)

    def save(self) -> None:
        with open(self._path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["nombre"] + SLOTS)
            writer.writeheader()
            for nombre, slots in self._presets.items():
                row = {"nombre": nombre}
                row.update(slots)
                writer.writerow(row)
