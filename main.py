"""
main.py — Punto de entrada de RegearApp for Albion Online.
Crea la ventana principal con 3 pestañas: Calculadora, Precios, Presets.
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import ttk

# Asegurar que el directorio actual esté en el path para importaciones relativas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data import CSVDataSource, APIDataSource
from presets import CSVPresetSource
from ui_calculator import CalculatorFrame
from ui_prices import PricesFrame
from ui_presets import PresetsFrame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_CSV = os.path.join(BASE_DIR, "MAGA Regear Charts - Price Charts.csv")
PRESETS_CSV = os.path.join(BASE_DIR, "presets.csv")


class RegearApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RegearApp — Albion Online")
        self.resizable(True, True)
        self.minsize(900, 600)

        # ── Fuentes de datos ────────────────────────────────────────────
        self._preset_source = CSVPresetSource(PRESETS_CSV)

        # Intentar cargar el CSV de precios automáticamente si existe
        self._ds: CSVDataSource | APIDataSource | None = None
        prices_path = os.path.normpath(PRICES_CSV)
        if os.path.exists(prices_path):
            self._ds = CSVDataSource(prices_path)

        # ── Notebook ────────────────────────────────────────────────────
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Pestaña 1 — Calculadora
        self._calc_frame = CalculatorFrame(
            notebook,
            preset_source=self._preset_source,
            on_prices_loaded=self._on_prices_loaded,
        )
        notebook.add(self._calc_frame, text="  Calculadora  ")

        # Pestaña 2 — Gestión de Precios
        self._prices_frame = PricesFrame(
            notebook,
            ds=self._ds,
            on_data_changed=self._on_prices_data_changed,
            on_source_changed=self._on_source_changed,
        )
        notebook.add(self._prices_frame, text="  Gestión de Precios  ")

        # Pestaña 3 — Gestión de Presets
        self._presets_frame = PresetsFrame(
            notebook,
            preset_source=self._preset_source,
            on_presets_changed=self._on_presets_changed,
            ds=self._ds,
        )
        notebook.add(self._presets_frame, text="  Gestión de Presets  ")

        # Si el CSV se cargó automáticamente, notificar a la calculadora
        if self._ds:
            self._calc_frame.set_datasource(self._ds)

    # ─────────────────────────────────────────── Callbacks entre pestañas
    def _on_prices_loaded(self, ds: CSVDataSource) -> None:
        """Llamado cuando el usuario carga el CSV desde la Calculadora."""
        self._ds = ds
        self._prices_frame.set_datasource(ds)
        self._presets_frame.set_datasource(ds)

    def _on_prices_data_changed(self) -> None:
        """Llamado cuando se modifica un precio en la pestaña de Gestión."""
        if self._ds:
            self._calc_frame.set_datasource(self._ds)

    def _on_presets_changed(self) -> None:
        """Llamado cuando se crea/edita/elimina un preset."""
        self._calc_frame.refresh_presets()

    def _on_source_changed(self, source: str) -> None:
        """Llamado cuando el usuario cambia entre fuente CSV y API en Pestaña 2."""
        path = self._ds.get_path() if self._ds else PRICES_CSV
        if source == "API":
            new_ds = APIDataSource(path)   # Solo carga CSV, sin llamada a la API
        else:
            new_ds = CSVDataSource(path)
            new_ds.reload()
        self._ds = new_ds
        self._prices_frame.set_datasource(new_ds)
        self._calc_frame.set_datasource(new_ds)
        self._presets_frame.set_datasource(new_ds)


def main() -> None:
    app = RegearApp()
    app.mainloop()


if __name__ == "__main__":
    main()
