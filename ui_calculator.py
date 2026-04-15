"""
ui_calculator.py — Pestaña 1: Calculadora de Regear.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from calculator import calculate_total
from data import CSVDataSource, TIERS, SLOT_CATEGORY

SLOT_LABELS = ["Arma", "Offhand", "Casco", "Armadura", "Botas", "Capa", "Mochila", "Comida", "Montura"]
DEFAULT_TIER = "T8"
COLS = 3  # slots por fila


class SlotRow:
    """Un slot de equipo: checkbox + combobox de ítem + combobox de tier."""

    def __init__(self, parent: tk.Widget, label: str, item_names: list[str]):
        self.enabled_var = tk.BooleanVar(value=True)
        self.item_var = tk.StringVar(value="None")
        self.tier_var = tk.StringVar(value=DEFAULT_TIER)

        self.frame = ttk.Frame(parent)

        self.chk = ttk.Checkbutton(self.frame, variable=self.enabled_var)
        self.chk.grid(row=0, column=0, padx=(0, 2))

        self.label = ttk.Label(self.frame, text=label, width=8, anchor="e")
        self.label.grid(row=0, column=1, padx=(0, 4))

        self._all_items = ["None"] + item_names
        self.combo_item = ttk.Combobox(
            self.frame, textvariable=self.item_var,
            values=self._all_items, state="readonly", width=22
        )
        self.combo_item.grid(row=0, column=2, padx=(0, 4))

        self.combo_tier = ttk.Combobox(
            self.frame, textvariable=self.tier_var,
            values=TIERS, state="readonly", width=5
        )
        self.combo_tier.grid(row=0, column=3)

    def get_slot(self) -> dict:
        return {
            "item": self.item_var.get(),
            "tier": self.tier_var.get(),
            "enabled": self.enabled_var.get(),
        }

    def set_item(self, name: str) -> None:
        if name in self._all_items:
            self.item_var.set(name)
        else:
            self.item_var.set("None")

    def set_tier(self, tier: str) -> None:
        if tier in TIERS:
            self.tier_var.set(tier)

    def refresh_items(self, item_names: list[str]) -> None:
        self._all_items = ["None"] + item_names
        self.combo_item["values"] = self._all_items
        if self.item_var.get() not in self._all_items:
            self.item_var.set("None")


class CalculatorFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, preset_source):
        super().__init__(parent)
        self._ds: CSVDataSource | None = None
        self._preset_source = preset_source
        self._slots: list[SlotRow] = []
        self._build_ui()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        # ── Zona de slots ──────────────────────────────────────────────
        slots_frame = ttk.LabelFrame(self, text="Equipo")
        slots_frame.pack(fill="x", padx=8, pady=(8, 4))

        for i, label in enumerate(SLOT_LABELS):
            row_idx = i // COLS
            col_idx = i % COLS
            slot = SlotRow(slots_frame, label, [])
            slot.frame.grid(row=row_idx, column=col_idx, padx=8, pady=3, sticky="w")
            self._slots.append(slot)

        # ── Barra de controles ──────────────────────────────────────────
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=8, pady=4)

        # Porcentaje
        ttk.Label(ctrl, text="Porcentaje:").grid(row=0, column=0, padx=(0, 2))
        self._pct_var = tk.StringVar(value="100")
        pct_entry = ttk.Entry(ctrl, textvariable=self._pct_var, width=6)
        pct_entry.grid(row=0, column=1, padx=(0, 2))
        ttk.Label(ctrl, text="%").grid(row=0, column=2, padx=(0, 12))

        # Calcular
        ttk.Button(ctrl, text="CALCULATE", command=self._calculate).grid(row=0, column=3, padx=(0, 16))

        # Tiers globales
        for t in TIERS:
            ttk.Button(ctrl, text=t, width=4,
                       command=lambda tier=t: self._set_all_tiers(tier)
                       ).grid(row=0, column=4 + TIERS.index(t), padx=2)

        # Tick / Untick
        ttk.Button(ctrl, text="Tick All",   command=lambda: self._tick_all(True) ).grid(row=0, column=9, padx=(8, 2))
        ttk.Button(ctrl, text="Untick All", command=lambda: self._tick_all(False)).grid(row=0, column=10, padx=(0, 8))

        # ── Resultado ──────────────────────────────────────────────────
        result_frame = ttk.Frame(self)
        result_frame.pack(fill="x", padx=8, pady=(0, 4))

        self._result_var = tk.StringVar(value="Total: —")
        ttk.Label(result_frame, textvariable=self._result_var,
                  font=("TkDefaultFont", 13, "bold")).pack(side="left")

        # ── Grilla de presets ──────────────────────────────────────────
        self._presets_outer = ttk.LabelFrame(self, text="Presets")
        self._presets_outer.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        self._presets_canvas = tk.Canvas(self._presets_outer, height=180)
        scrollbar = ttk.Scrollbar(self._presets_outer, orient="vertical",
                                  command=self._presets_canvas.yview)
        self._presets_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._presets_canvas.pack(side="left", fill="both", expand=True)

        self._presets_inner = ttk.Frame(self._presets_canvas)
        self._presets_canvas.create_window((0, 0), window=self._presets_inner, anchor="nw")
        self._presets_inner.bind(
            "<Configure>",
            lambda e: self._presets_canvas.configure(
                scrollregion=self._presets_canvas.bbox("all")
            )
        )
        self.refresh_presets()

    # ---------------------------------------------------------------- helpers
    def _set_all_tiers(self, tier: str) -> None:
        for slot in self._slots:
            slot.set_tier(tier)

    def _tick_all(self, value: bool) -> None:
        for slot in self._slots:
            slot.enabled_var.set(value)

    def _calculate(self) -> None:
        if self._ds is None:
            messagebox.showwarning("Sin datos", "No hay precios cargados.")
            return
        try:
            pct = float(self._pct_var.get())
        except ValueError:
            messagebox.showerror("Error", "El porcentaje debe ser un número.")
            return

        slots = [s.get_slot() for s in self._slots]
        items_db = self._ds.get_all()
        bruto, final = calculate_total(slots, items_db, pct)
        self._result_var.set(
            f"Total bruto: {bruto:,} silver   →   Con {pct:.0f}%: {final:,} silver"
        )

    def _refresh_slot_items(self) -> None:
        if self._ds is None:
            return
        for slot_row, label in zip(self._slots, SLOT_LABELS):
            cat = SLOT_CATEGORY.get(label.lower())
            items = self._ds.get_items_by_category(cat) if cat else []
            slot_row.refresh_items(items)

    def _load_preset(self, nombre: str) -> None:
        presets = self._preset_source.get_all()
        slot_map = presets.get(nombre, {})
        for slot_row, label in zip(self._slots, SLOT_LABELS):
            key = label.lower()
            item_name = slot_map.get(key, "") or "None"
            slot_row.set_item(item_name)

    # ─── API pública ───────────────────────────────────────────────────
    def refresh_presets(self) -> None:
        for widget in self._presets_inner.winfo_children():
            widget.destroy()
        presets = self._preset_source.get_all()
        PRESET_COLS = 5
        for idx, nombre in enumerate(presets.keys()):
            r, c = divmod(idx, PRESET_COLS)
            btn = ttk.Button(
                self._presets_inner, text=nombre, width=14,
                command=lambda n=nombre: self._load_preset(n)
            )
            btn.grid(row=r, column=c, padx=4, pady=3)

    def get_datasource(self) -> CSVDataSource | None:
        return self._ds

    def set_datasource(self, ds: CSVDataSource) -> None:
        self._ds = ds
        self._refresh_slot_items()
