"""
ui_prices.py — Pestaña 2: Gestión de Precios (CRUD).
"""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from data import APIDataSource, CSVDataSource, TIERS, ALL_CATEGORIES


class PricesFrame(ttk.Frame):
    def __init__(self, parent: tk.Widget, ds: APIDataSource | CSVDataSource | None = None,
                 on_data_changed=None):
        super().__init__(parent)
        self._ds: APIDataSource | CSVDataSource | None = ds
        self._on_data_changed = on_data_changed
        self._build_ui()
        if self._ds:
            self._populate()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        # ── Barra superior ──────────────────────────────────────────────
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        ttk.Button(top, text="Guardar",      command=self._save      ).grid(row=0, column=0, padx=4)
        self._btn_actualizar = ttk.Button(top, text="↻ Actualizar", command=self._actualizar)
        self._btn_actualizar.grid(row=0, column=1, padx=4)

        self._status_lbl = tk.StringVar(value="")
        ttk.Label(top, textvariable=self._status_lbl,
                  foreground="gray").grid(row=0, column=2, padx=(8, 4))

        self._progress = ttk.Progressbar(top, mode="indeterminate", length=150)
        self._progress.grid(row=0, column=3, padx=(0, 16))
        self._progress.grid_remove()

        ttk.Label(top, text="Buscar:").grid(row=0, column=4, padx=(0, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        ttk.Entry(top, textvariable=self._search_var, width=20).grid(row=0, column=5)

        # ── Treeview ────────────────────────────────────────────────────
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("item", "categoria", "api_id") + tuple(TIERS)
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  selectmode="browse")
        self._tree.heading("item",      text="Ítem")
        self._tree.column ("item",      width=180, anchor="w")
        self._tree.heading("categoria", text="Categoría")
        self._tree.column ("categoria", width=90,  anchor="w")
        self._tree.heading("api_id",    text="API ID")
        self._tree.column ("api_id",    width=200, anchor="w")
        for t in TIERS:
            self._tree.heading(t, text=t)
            self._tree.column(t, width=90, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",  command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(side="left", fill="both", expand=True)

        self._tree.bind("<Double-1>", self._on_double_click)

        # ── Botones CRUD ────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_frame, text="+ Nuevo ítem", command=self._create_item).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Editar",       command=self._edit_item  ).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Eliminar",     command=self._delete_item).pack(side="left", padx=4)

        # Widget de edición inline solo para precios (double-click)
        self._edit_entry = ttk.Entry(self._tree)
        self._edit_entry.bind("<Return>", self._commit_edit)
        self._edit_entry.bind("<Escape>", lambda e: self._edit_entry.place_forget())
        self._editing: tuple | None = None  # (iid, col_idx, tier)

    # ---------------------------------------------------------------- populate
    def set_datasource(self, ds: APIDataSource | CSVDataSource) -> None:
        self._ds = ds
        self._populate()

    def _populate(self) -> None:
        if self._ds is None:
            return
        self._tree.delete(*self._tree.get_children())
        query = self._search_var.get().lower()
        for name, data in self._ds.get_all().items():
            if query and query not in name.lower():
                continue
            values = (
                name,
                data.get("categoria", ""),
                data.get("api_id", ""),
            ) + tuple(data.get(t, 0) for t in TIERS)
            self._tree.insert("", "end", iid=name, values=values)

    def _on_search(self, *_) -> None:
        self._populate()

    # ─────────────────────────────────── actualizar (desde API con caché en CSV)
    def _actualizar(self) -> None:
        if self._ds is None:
            messagebox.showwarning("Sin datos", "No hay datos cargados.")
            return

        if isinstance(self._ds, APIDataSource):
            self._btn_actualizar.config(state="disabled")
            self._progress.grid()
            self._progress.start(10)
            self._status_lbl.set("Actualizando desde API...")

            def _run() -> None:
                result = self._ds.refresh()
                self._ds.save()
                self.after(0, lambda: self._on_refresh_done(result))

            threading.Thread(target=_run, daemon=True).start()
        else:
            self._ds.reload()
            self._status_lbl.set("CSV recargado")
            self._populate()
            if self._on_data_changed:
                self._on_data_changed()

    def _on_refresh_done(self, result: dict) -> None:
        self._progress.stop()
        self._progress.grid_remove()
        self._btn_actualizar.config(state="normal")
        self._status_lbl.set(result['message'])
        self._populate()
        if self._on_data_changed:
            self._on_data_changed()

    # ─────────────────────────────── inline edit double-click (solo precios)
    # Columnas de precio comienzan en el índice 3 (tras item, categoria, api_id)
    _PRICE_COL_OFFSET = 3

    def _on_double_click(self, event: tk.Event) -> None:
        region = self._tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id  = self._tree.identify_column(event.x)
        col_idx = int(col_id.replace("#", "")) - 1  # 0-based
        if col_idx < self._PRICE_COL_OFFSET:
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            return

        tier        = TIERS[col_idx - self._PRICE_COL_OFFSET]
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
        name, categoria, api_id, prices = dialog.result
        if name in self._ds.get_all():
            messagebox.showerror("Error", f"El ítem '{name}' ya existe.")
            return
        self._ds.create(name, prices, api_id=api_id, categoria=categoria)
        values = (name, categoria, api_id) + tuple(prices.get(t, 0) for t in TIERS)
        self._tree.insert("", "end", iid=name, values=values)
        if self._on_data_changed:
            self._on_data_changed()

    def _edit_item(self) -> None:
        sel = self._tree.selection()
        if not sel or self._ds is None:
            messagebox.showwarning("Sin selección", "Selecciona un ítem para editar.")
            return
        old_name  = sel[0]
        all_data  = self._ds.get_all()
        item_data = all_data.get(old_name, {})

        dialog = _ItemDialog(
            self, title=f"Editar: {old_name}",
            initial_name=old_name,
            initial_categoria=item_data.get("categoria", ""),
            initial_api_id=item_data.get("api_id", ""),
            initial_prices={t: item_data.get(t, 0) for t in TIERS},
        )
        self.wait_window(dialog)
        if dialog.result is None:
            return
        new_name, categoria, api_id, prices = dialog.result

        if new_name != old_name and new_name in all_data:
            messagebox.showerror("Error", f"El ítem '{new_name}' ya existe.")
            return

        if new_name != old_name:
            self._ds.delete(old_name)
        self._ds.create(new_name, prices, api_id=api_id, categoria=categoria)
        self._tree.delete(old_name)
        values = (new_name, categoria, api_id) + tuple(prices.get(t, 0) for t in TIERS)
        self._tree.insert("", "end", iid=new_name, values=values)
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


# ──────────────────────────────────────── Dialog para crear / editar ítem
class _ItemDialog(tk.Toplevel):
    def __init__(self, parent, title="Ítem",
                 initial_name="", initial_categoria="", initial_api_id="",
                 initial_prices: dict | None = None):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result = None
        self._initial_name      = initial_name
        self._initial_categoria = initial_categoria
        self._initial_api_id    = initial_api_id
        self._initial_prices    = initial_prices or {}
        self._build()

    def _build(self) -> None:
        row = 0

        ttk.Label(self, text="Nombre:").grid(row=row, column=0, padx=8, pady=4, sticky="e")
        self._name_var = tk.StringVar(value=self._initial_name)
        ttk.Entry(self, textvariable=self._name_var, width=26).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="Categoría:").grid(row=row, column=0, padx=8, pady=4, sticky="e")
        self._cat_var = tk.StringVar(value=self._initial_categoria)
        ttk.Combobox(self, textvariable=self._cat_var, values=ALL_CATEGORIES,
                     state="readonly", width=24).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        ttk.Label(self, text="API ID:").grid(row=row, column=0, padx=8, pady=4, sticky="e")
        self._api_id_var = tk.StringVar(value=self._initial_api_id)
        ttk.Entry(self, textvariable=self._api_id_var, width=26).grid(row=row, column=1, padx=8, pady=4)
        row += 1

        self._price_vars: dict[str, tk.StringVar] = {}
        for tier in TIERS:
            ttk.Label(self, text=f"Precio {tier}:").grid(row=row, column=0, padx=8, pady=3, sticky="e")
            var = tk.StringVar(value=str(self._initial_prices.get(tier, 0)))
            ttk.Entry(self, textvariable=var, width=14).grid(row=row, column=1, padx=8, pady=3)
            self._price_vars[tier] = var
            row += 1

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Guardar",  command=self._ok    ).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="left", padx=6)

    def _ok(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "El nombre no puede estar vacío.", parent=self)
            return
        categoria = self._cat_var.get().strip()
        api_id    = self._api_id_var.get().strip()
        prices = {}
        for tier, var in self._price_vars.items():
            try:
                prices[tier] = int(var.get().strip())
            except ValueError:
                messagebox.showerror("Error", f"Precio inválido para {tier}.", parent=self)
                return
        self.result = (name, categoria, api_id, prices)
        self.destroy()
