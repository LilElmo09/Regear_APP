"""
data.py — Capa de datos para precios de ítems.
Define DataSource (interfaz abstracta), CSVDataSource y APIDataSource.
"""
from __future__ import annotations

import csv
import datetime
import gzip
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

# Configurar logging para debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('regear_api.log')  # File output
    ]
)
logger = logging.getLogger(__name__)

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
AODP_URL             = "https://west.albion-online-data.com/api/v2/stats/prices"
AODP_CITIES          = ["Lymhurst", "Fort Sterling", "Bridgewatch", "Martlock"]
AODP_QUALITY         = 2
AODP_COOLDOWN        = 60    # Segundos mínimos entre llamadas
AODP_DELAY           = 1.0   # Segundos entre batch requests
AODP_WORKERS         = 1     # No usado directamente (batch es secuencial)
AODP_MAX_RETRIES     = 4     # Reintentos máximos en caso de 429
AODP_RETRY_BASE      = 5.0   # Base para backoff exponencial en segundos
AODP_BATCH_SIZE      = 50    # IDs por batch request (max recomendado ~100)

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


def _parse_error_entry(entry: str) -> tuple[str, str, str]:
    """Parsea 'nombre (tier): motivo' → (nombre, tier, motivo)."""
    try:
        head, reason = entry.split(":", 1)
        head = head.strip()
        reason = reason.strip()
        paren = head.rfind("(")
        if paren != -1 and head.endswith(")"):
            name = head[:paren].strip()
            tier = head[paren + 1:-1].strip()
            return name, tier, reason
        return head, "", reason
    except ValueError:
        return entry, "", ""


def _parse_zero_entry(entry: str) -> tuple[str, str, str]:
    """Parsea 'nombre (tier) — motivo' → (nombre, tier, motivo)."""
    sep = " — "
    if sep in entry:
        head, reason = entry.split(sep, 1)
    else:
        head, reason = entry, ""
    head = head.strip()
    reason = reason.strip()
    paren = head.rfind("(")
    if paren != -1 and head.endswith(")"):
        name = head[:paren].strip()
        tier = head[paren + 1:-1].strip()
        return name, tier, reason
    return head, "", reason


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

    # ── Métodos privados ────────────────────────────────────────────────────

    def _fetch_batch(self, batch_ids: list[str], item_map: dict) -> list[dict]:
        """
        Consulta precios actuales de un lote de full_ids en una sola request.
        Busca en las ciudades configuradas y guarda el sell_price_min más bajo.

        Retorna lista de dicts con estructura:
        {'full_id', 'name', 'tier', 'price', 'error', 'zero_reason'}
        """
        ids_str = ",".join(batch_ids)
        cities_str = urllib.parse.quote(",".join(AODP_CITIES), safe=",")
        url = (f"{AODP_URL}/{ids_str}"
               f"?qualities={AODP_QUALITY}"
               f"&locations={cities_str}")

        logger.debug(f"[Batch {len(batch_ids)} items] URL: {url[:120]}...")

        last_error: str | None = None

        for attempt in range(AODP_MAX_RETRIES + 1):
            try:
                req = urllib.request.Request(url)
                req.add_header('Accept-Encoding', 'gzip')
                req.add_header('User-Agent', 'RegearApp/1.0')

                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    if raw[:2] == b'\x1f\x8b':
                        raw = gzip.decompress(raw)
                    response = json.loads(raw.decode('utf-8'))

                # La API /prices devuelve una entrada por item+ciudad.
                # Guardamos el sell_price_min más bajo entre todas las ciudades.
                price_by_id: dict[str, int] = {}
                if isinstance(response, list):
                    for entry in response:
                        item_id = entry.get("item_id", "")
                        sell_price = entry.get("sell_price_min", 0) or 0
                        if sell_price > 0:
                            if item_id not in price_by_id or sell_price < price_by_id[item_id]:
                                price_by_id[item_id] = sell_price

                # Construir resultados para cada id del batch
                results = []
                for full_id in batch_ids:
                    name, tier = item_map[full_id]
                    if full_id not in price_by_id:
                        logger.warning(f"[{name} ({tier})] ID no encontrado en respuesta del batch")
                        results.append({
                            'full_id': full_id, 'name': name, 'tier': tier,
                            'price': 0, 'error': None, 'zero_reason': "sin respuesta"
                        })
                        continue
                    price = price_by_id[full_id]
                    if price > 0:
                        logger.debug(f"[{name} ({tier})] ✓ {price}")
                        results.append({
                            'full_id': full_id, 'name': name, 'tier': tier,
                            'price': price, 'error': None, 'zero_reason': None
                        })
                    else:
                        results.append({
                            'full_id': full_id, 'name': name, 'tier': tier,
                            'price': 0, 'error': None, 'zero_reason': "precio = 0 o sin datos"
                        })
                return results

            except urllib.error.HTTPError as http_err:
                if http_err.code == 429 and attempt < AODP_MAX_RETRIES:
                    wait = AODP_RETRY_BASE * (2 ** attempt)
                    logger.warning(
                        f"[Batch] 429 recibido, reintento {attempt + 1}/{AODP_MAX_RETRIES} "
                        f"en {wait:.0f}s..."
                    )
                    time.sleep(wait)
                    continue
                last_error = f"HTTP Error {http_err.code}: {http_err.reason}"
                logger.error(f"[Batch] ✗ {last_error}")
                break

            except urllib.error.URLError as url_err:
                last_error = f"URL Error: {url_err.reason}"
                logger.error(f"[Batch] ✗ {last_error}")
                break

            except json.JSONDecodeError as json_err:
                last_error = f"JSON Decode Error: {str(json_err)}"
                logger.error(f"[Batch] ✗ {last_error}")
                break

            except Exception as exc:
                last_error = f"{type(exc).__name__}: {str(exc)}"
                logger.error(f"[Batch] ✗ Error inesperado: {last_error}", exc_info=True)
                break

            finally:
                time.sleep(AODP_DELAY)

        # Si todos los reintentos fallaron, marcar todo el batch como error
        return [
            {
                'full_id': fid, 'name': item_map[fid][0], 'tier': item_map[fid][1],
                'price': 0, 'error': last_error, 'zero_reason': None
            }
            for fid in batch_ids
        ]

    # ── API pública ─────────────────────────────────────────────────────────

    def refresh(self) -> dict:
        """
        Consulta la AODP API endpoint /history y actualiza los precios en memoria.
        Consulta precios actuales del endpoint /prices en múltiples ciudades.
        Guarda el sell_price_min más bajo entre las ciudades configuradas.
        Respeta un cooldown de AODP_COOLDOWN segundos entre llamadas.
        
        Retorna un dict con estructura:
        {
            'success': bool,
            'message': str,  # Mensaje para mostrar
            'updated': int,  # Precios actualizados
            'errors': list[str],  # Errores
            'items_not_found': list[str],  # Items sin api_id
            'prices_zero': list[str],  # Items con precio 0 o sin datos
        }
        """
        logger.info("=" * 70)
        logger.info("INICIANDO ACTUALIZACIÓN DE PRECIOS")
        logger.info("=" * 70)
        
        now = time.time()
        elapsed = now - self._last_fetch
        if self._last_fetch > 0 and elapsed < AODP_COOLDOWN:
            remaining = int(AODP_COOLDOWN - elapsed)
            logger.warning(f"Cooldown activo: {remaining}s restantes")
            return {
                'success': False,
                'message': f"Espera {remaining}s antes de volver a actualizar",
                'updated': 0,
                'errors': [],
                'items_not_found': [],
                'prices_zero': [],
            }

        logger.info(f"Ciudades: {', '.join(AODP_CITIES)}")
        logger.debug(f"Constantes API: WORKERS={AODP_WORKERS}, DELAY={AODP_DELAY}s, COOLDOWN={AODP_COOLDOWN}s")

        # Construir mapa full_api_id → (nombre_item, tier)
        item_map: dict[str, tuple[str, str]] = {}
        items_without_api_id: list[str] = []
        
        logger.info("Construyendo mapa de items...")
        for name, data in self._data.items():
            base_id = data.get("api_id", "")
            if not base_id:
                items_without_api_id.append(name)
                logger.debug(f"Item sin api_id: {name}")
                continue
            for tier in TIERS:
                prefix, suffix = TIER_API[tier]
                full_id = f"{prefix}_{base_id}{suffix}"
                item_map[full_id] = (name, tier)
        
        logger.info(f"Mapa construido: {len(item_map)} items, {len(items_without_api_id)} sin api_id")

        if not item_map:
            logger.error("Ningún ítem tiene api_id — abortando actualización")
            return {
                'success': False,
                'message': "Ningún ítem tiene api_id — nada que actualizar",
                'updated': 0,
                'errors': [],
                'items_not_found': items_without_api_id,
                'prices_zero': [],
            }

        full_ids = list(item_map.keys())
        errors: list[str] = []
        updated = 0
        prices_zero: list[str] = []

        # Dividir en batches y procesar secuencialmente
        batches = [full_ids[i:i + AODP_BATCH_SIZE]
                   for i in range(0, len(full_ids), AODP_BATCH_SIZE)]
        total_batches = len(batches)
        logger.info(f"Procesando {len(full_ids)} IDs en {total_batches} batches de {AODP_BATCH_SIZE}...")

        for batch_num, batch in enumerate(batches, 1):
            logger.info(f"[Batch {batch_num}/{total_batches}] {len(batch)} items...")
            results = self._fetch_batch(batch, item_map)

            for result in results:
                name = result['name']
                tier = result['tier']
                price = result['price']
                error = result['error']
                zero_reason = result['zero_reason']

                if error:
                    errors.append(f"{name} ({tier}): {error}")
                elif price > 0:
                    self._data[name][tier] = price
                    updated += 1
                elif zero_reason:
                    prices_zero.append(f"{name} ({tier}) — {zero_reason}")

        self._last_fetch = time.time()

        logger.info("=" * 70)
        logger.info(f"RESUMEN DE ACTUALIZACIÓN:")
        logger.info(f"  Precios actualizados: {updated}")
        logger.info(f"  Errores: {len(errors)}")
        logger.info(f"  Sin datos: {len(prices_zero)}")
        logger.info(f"  Items sin api_id: {len(items_without_api_id)}")
        logger.info("=" * 70)

        if errors:
            logger.error(f"Errores encontrados ({len(errors)}):")
            for err in errors:
                logger.error(f"  - {err}")

        failed_csv_path = self._write_failed_csv(errors, prices_zero, items_without_api_id)

        ts = datetime.datetime.now().strftime("%H:%M")
        if errors:
            message = f"Actualizado a las {ts} ({updated} precios) — {len(errors)} error(es)"
            success = len(errors) < len(full_ids)  # Éxito parcial si algunos items se actualizaron
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
            'failed_csv_path': failed_csv_path,
        }

    def _write_failed_csv(
        self,
        errors: list[str],
        prices_zero: list[str],
        items_without_api_id: list[str],
    ) -> str | None:
        """
        Escribe un CSV con todos los items/tiers que no se actualizaron.
        Retorna la ruta del CSV generado, o None si no hubo fallos.
        Columnas: nombre, tier, motivo
        """
        rows: list[tuple[str, str, str]] = []

        # errors: "nombre (tier): motivo"
        for entry in errors:
            name, tier, reason = _parse_error_entry(entry)
            rows.append((name, tier, reason))

        # prices_zero: "nombre (tier) — motivo"
        for entry in prices_zero:
            name, tier, reason = _parse_zero_entry(entry)
            rows.append((name, tier, reason))

        # items_without_api_id: solo nombres
        for name in items_without_api_id:
            rows.append((name, "todos los tiers", "sin api_id"))

        if not rows:
            logger.info("No hay items fallidos — no se genera CSV de no actualizados")
            return None

        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        filename = f"precios_no_actualizados_{stamp}.csv"
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, filename)

        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["nombre", "tier", "motivo"])
                writer.writerows(rows)
            logger.info(f"CSV de no actualizados generado: {path} ({len(rows)} filas)")
            return path
        except OSError as e:
            logger.error(f"No se pudo escribir CSV de no actualizados: {e}")
            return None

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
