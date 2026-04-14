"""
calculator.py — Lógica de cálculo de regear.
"""
from __future__ import annotations


def calculate_total(
    slots: list[dict],
    items_db: dict[str, dict[str, int]],
    percentage: float,
) -> tuple[int, int]:
    """
    Calcula el costo total de regear.

    Args:
        slots: Lista de dicts con claves 'item' (str), 'tier' (str), 'enabled' (bool).
        items_db: Diccionario de precios {nombre: {T7: int, T8: int, T9: int, T10: int}}.
        percentage: Porcentaje a aplicar (0.0 – 100.0).

    Returns:
        (total_bruto, total_con_porcentaje) ambos en silver (int).
    """
    total_bruto = 0
    for slot in slots:
        if not slot.get("enabled", True):
            continue
        item = slot.get("item", "")
        tier = slot.get("tier", "T8")
        if not item or item == "None":
            continue
        prices = items_db.get(item, {})
        price = prices.get(tier, 0)
        total_bruto += price

    total_final = int(total_bruto * (percentage / 100.0))
    return total_bruto, total_final
