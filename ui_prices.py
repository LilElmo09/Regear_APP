"""
ui_prices.py — Pestaña 2: Gestión de Precios (CRUD).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from data import CSVDataSource, TIERS


class PricesFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, ds: CSVDataSource | None = None,
                 on_data_changed=None):
        super().__init__(parent)
        self._ds: CSVDataSource | None = ds
        self._on_data_changed = on_data_changed  # callback para notificar cambios
        self._build_ui()
        if self._ds:
            self._populate()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        # ── Barra superior ──────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        # Fuente (CSV / API)
        self._source_var = tk.StringVar(value="CSV")
        ttk.Radiobutton(top, text="CSV", variable=self._source_var,
                        value="CSV").grid(row=0, column=0, padx=(0, 4))
        ttk.Radiobutton(top, text="API (Próximamente)", variable=self._source_var,
                        value="API", state="disabled").grid(row=0, column=1, padx=(0, 12))

        ttk.Button(top, text="Guardar", command=self._save).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Recargar", command=self._reload).grid(row=0, column=3, padx=4)

        # Búsqueda
        ttk.Label(top, text="Buscar:").grid(row=0, column=4, padx=(16, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ttk.Entry(top, textvariable=self._search_var, width=20).grid(row=0, column=5)

        # ── Treeview ────────────────────────────────────────────────────
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("item",) + tuple(TIERS)
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="browse")
        self._tree.heading("item", text="Ítem")
        self._tree.column("item", width=200, anchor="w")
        for t in TIERS:
            self._tree.heading(t, text=t)
            self._tree.column(t, width=90, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(side="left", fill="both", expand=True)

        self._tree.bind("<Double-1>", self._on_double_click)

        # ── Botones CRUD ────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="+ Nuevo ítem", command=self._create_item).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Eliminar",     command=self._delete_item).pack(side="left", padx=4)

        # Widget de edición inline (oculto inicialmente)
        self._edit_entry = ttk.Entry(self._tree)
        self._edit_entry.bind("<Return>", self._commit_edit)
        self._edit_entry.bind("<Escape>", lambda e: self._edit_entry.place_forget())
        self._editing: tuple | None = None  # (iid, column_index)

    # ---------------------------------------------------------------- populate
    def set_datasource(self, ds: CSVDataSource) -> None:
        self._ds = ds
        self._populate()

    def _populate(self) -> None:
        if self._ds is None:
            return
        self._tree.delete(*self._tree.get_children())
        query = self._search_var.get().lower()
        for name, prices in self._ds.get_all().items():
            if query and query not in name.lower():
                continue
            values = (name,) + tuple(prices.get(t, 0) for t in TIERS)
            self._tree.insert("", "end", iid=name, values=values)

    def _on_search(self, *_) -> None:
        self._populate()

    # ─────────────────────────────────────── inline edit (double-click)
    def _on_double_click(self, event: tk.Event) -> None:
        region = self._tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id = self._tree.identify_column(event.x)
        col_idx = int(col_id.replace("#", "")) - 1  # 0-based
        if col_idx == 0:  # nombre no editable inline
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            return

        tier = TIERS[col_idx - 1]
        current_val = self._tree.set(iid, col_id)

        bbox = self._tree.bbox(iid, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        self._edit_entry.place(x=x, y=y, width=w, height=h)
        self._edit_entry.delete(0, "end")
        self._edit_entry.insert(0, current_val)
        self._edit_entry.focus_set()
        self._editing = (iid, col_idx, tier)

    def _commit_edit(self, _=None) -> None:
        if self._editing is None or self._ds is None:
            return
        iid, col_idx, tier = self._editing
        raw = self._edit_entry.get().strip()
        try:
            price = int(raw)
        except ValueError:
            messagebox.showerror("Error", "El precio debe ser un número entero.")
            return
        self._ds.update(iid, tier, price)
        col_id = f"#{col_idx + 1}"
        self._tree.set(iid, col_id, str(price))
        self._edit_entry.place_forget()
        self._editing = None
        if self._on_data_changed:
            self._on_data_changed()

    # ──────────────────────────────────────────────────────── CRUD botones
    def _create_item(self) -> None:
        dialog = _ItemDialog(self, title="Nuevo ítem")
        self.wait_window(dialog)
        if dialog.result is None or self._ds is None:
            return
        name, prices = dialog.result
        if name in self._ds.get_all():
            messagebox.showerror("Error", f"El ítem '{name}' ya existe.")
            return
        self._ds.create(name, prices)
        values = (name,) + tuple(prices.get(t, 0) for t in TIERS)
        self._tree.insert("", "end", iid=name, values=values)
        if self._on_data_changed:
            self._on_data_changed()

    def _delete_item(self) -> None:
        sel = self._tree.selection()
        if not sel or self._ds is None:
            return
        iid = sel[0]
        if not messagebox.askyesno("Confirmar", f"¿Eliminar '{iid}'?"):
            return
        self._ds.delete(iid)
        self._tree.delete(iid)
        if self._on_data_changed:
            self._on_data_changed()

    def _save(self) -> None:
        if self._ds is None:
            messagebox.showwarning("Sin datos", "No hay datos cargados.")
            return
        self._ds.save()
        messagebox.showinfo("Guardado", "Precios guardados correctamente.")

    def _reload(self) -> None:
        if self._ds is None:
            messagebox.showwarning("Sin datos", "No hay datos cargados.")
            return
        self._ds.reload()
        self._populate()


# ─────────────────────────────────────────────────── Dialog para nuevo ítem
class _ItemDialog(tk.Toplevel):
    def __init__(self, parent, title="Ítem"):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Nombre:").grid(row=0, column=0, padx=8, pady=4, sticky="e")
        self._name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self._name_var, width=24).grid(row=0, column=1, padx=8, pady=4)

        self._price_vars: dict[str, tk.StringVar] = {}
        for i, tier in enumerate(TIERS):
            ttk.Label(self, text=f"Precio {tier}:").grid(row=i + 1, column=0, padx=8, pady=3, sticky="e")
            var = tk.StringVar(value="0")
            ttk.Entry(self, textvariable=var, width=12).grid(row=i + 1, column=1, padx=8, pady=3)
            self._price_vars[tier] = var

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=len(TIERS) + 1, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Guardar",   command=self._ok    ).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancelar",  command=self.destroy).pack(side="left", padx=6)

    def _ok(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "El nombre no puede estar vacío.", parent=self)
            return
        prices = {}
        for tier, var in self._price_vars.items():
            try:
                prices[tier] = int(var.get().strip())
            except ValueError:
                messagebox.showerror("Error", f"Precio inválido para {tier}.", parent=self)
                return
        self.result = (name, prices)
        self.destroy()
