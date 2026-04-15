"""
ui_presets.py — Pestaña 3: Gestión de Presets (CRUD).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from presets import CSVPresetSource, SLOTS
from data import CSVDataSource, SLOT_CATEGORY


class PresetsFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, preset_source: CSVPresetSource,
                 on_presets_changed=None, ds: CSVDataSource | None = None):
        super().__init__(parent)
        self._source = preset_source
        self._on_presets_changed = on_presets_changed
        self._ds: CSVDataSource | None = ds
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        # ── Treeview ────────────────────────────────────────────────────
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        cols = ("nombre",) + tuple(SLOTS)
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="browse")
        self._tree.heading("nombre", text="Nombre Preset")
        self._tree.column("nombre", width=130, anchor="w")
        for slot in SLOTS:
            self._tree.heading(slot, text=slot.capitalize())
            self._tree.column(slot, width=120, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)

        # ── Botones CRUD ────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="+ Nuevo Preset",      command=self._create).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Editar seleccionado", command=self._edit  ).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Eliminar",            command=self._delete).pack(side="left", padx=4)

    # ---------------------------------------------------------------- populate
    def _populate(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for nombre, slot_map in self._source.get_all().items():
            values = (nombre,) + tuple(slot_map.get(s, "") for s in SLOTS)
            self._tree.insert("", "end", iid=nombre, values=values)

    def set_datasource(self, ds: CSVDataSource) -> None:
        self._ds = ds

    # ──────────────────────────────────────────────────────── CRUD botones
    def _create(self) -> None:
        dialog = _PresetDialog(self, title="Nuevo Preset", ds=self._ds)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        nombre, slot_map = dialog.result
        if nombre in self._source.get_all():
            messagebox.showerror("Error", f"Ya existe un preset con el nombre '{nombre}'.")
            return
        self._source.create(nombre, slot_map)
        self._source.save()
        values = (nombre,) + tuple(slot_map.get(s, "") for s in SLOTS)
        self._tree.insert("", "end", iid=nombre, values=values)
        if self._on_presets_changed:
            self._on_presets_changed()

    def _edit(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("Sin selección", "Selecciona un preset para editar.")
            return
        nombre = sel[0]
        presets = self._source.get_all()
        current = presets.get(nombre, {})
        dialog = _PresetDialog(self, title=f"Editar: {nombre}",
                               initial_name=nombre, initial_slots=current, ds=self._ds)
        self.wait_window(dialog)
        if dialog.result is None:
            return
        new_nombre, slot_map = dialog.result

        # Si cambió el nombre, eliminar el viejo y crear el nuevo
        if new_nombre != nombre:
            self._source.delete(nombre)
            self._tree.delete(nombre)
            self._source.create(new_nombre, slot_map)
        else:
            self._source.update(nombre, slot_map)
            self._tree.delete(nombre)

        self._source.save()
        values = (new_nombre,) + tuple(slot_map.get(s, "") for s in SLOTS)
        self._tree.insert("", "end", iid=new_nombre, values=values)
        if self._on_presets_changed:
            self._on_presets_changed()

    def _delete(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        nombre = sel[0]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar preset '{nombre}'?"):
            return
        self._source.delete(nombre)
        self._source.save()
        self._tree.delete(nombre)
        if self._on_presets_changed:
            self._on_presets_changed()


# ─────────────────────────────────────────── Dialog para crear / editar preset
class _PresetDialog(tk.Toplevel):
    def __init__(self, parent, title="Preset", initial_name="",
                 initial_slots: dict | None = None, ds: CSVDataSource | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        self._ds = ds
        self._initial_name = initial_name
        self._initial_slots = initial_slots or {}
        self._build()

    def _build(self) -> None:
        # Nombre del preset
        ttk.Label(self, text="Nombre:").grid(row=0, column=0, padx=8, pady=4, sticky="e")
        self._name_var = tk.StringVar(value=self._initial_name)
        ttk.Entry(self, textvariable=self._name_var, width=26).grid(row=0, column=1, padx=8, pady=4)

        # Un ComboBox por slot, filtrado por categoría
        self._slot_vars: dict[str, tk.StringVar] = {}
        for i, slot in enumerate(SLOTS):
            ttk.Label(self, text=slot.capitalize() + ":").grid(
                row=i + 1, column=0, padx=8, pady=3, sticky="e"
            )
            cat = SLOT_CATEGORY.get(slot)
            if cat and self._ds:
                item_list = [""] + self._ds.get_items_by_category(cat)
            else:
                item_list = [""]
            var = tk.StringVar(value=self._initial_slots.get(slot, ""))
            combo = ttk.Combobox(self, textvariable=var, values=item_list,
                                 state="normal", width=24)
            combo.grid(row=i + 1, column=1, padx=8, pady=3)
            self._slot_vars[slot] = var

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=len(SLOTS) + 1, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Guardar",  command=self._ok    ).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=6)

    def _ok(self) -> None:
        nombre = self._name_var.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre no puede estar vacío.", parent=self)
            return
        slot_map = {slot: var.get().strip() for slot, var in self._slot_vars.items()}
        self.result = (nombre, slot_map)
        self.destroy()
