#!/usr/bin/env bash
# instalar.sh — Instala las dependencias de RegearApp for Albion Online
# Compatible con Arch Linux / CachyOS / Manjaro

set -e

echo "================================================="
echo "  RegearApp — Instalador de dependencias"
echo "================================================="
echo ""

# ── Verificar Python 3 ──────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 no está instalado."
    echo "        Instálalo con: sudo pacman -S python"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "[OK] Python $PYTHON_VERSION encontrado."

# ── Verificar gestor de paquetes ────────────────────────────────────────────
if command -v pacman &>/dev/null; then
    PKG_MANAGER="pacman"
elif command -v apt &>/dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
else
    echo "[AVISO] No se reconoció el gestor de paquetes."
    echo "        Instala manualmente: tk (Tcl/Tk windowing toolkit)"
    PKG_MANAGER="unknown"
fi

echo "[INFO] Gestor de paquetes detectado: $PKG_MANAGER"
echo ""

# ── Instalar tk (Tkinter) ───────────────────────────────────────────────────
echo ">>> Verificando Tkinter (tk)..."

if python3 -c "import tkinter" &>/dev/null; then
    echo "[OK] Tkinter ya está instalado."
else
    echo "[INFO] Tkinter no está disponible. Instalando..."
    case "$PKG_MANAGER" in
        pacman)
            sudo pacman -S --needed --noconfirm tk
            ;;
        apt)
            sudo apt update && sudo apt install -y python3-tk
            ;;
        dnf)
            sudo dnf install -y python3-tkinter
            ;;
        *)
            echo "[ERROR] Instala Tkinter manualmente para tu distribución."
            exit 1
            ;;
    esac

    if python3 -c "import tkinter" &>/dev/null; then
        echo "[OK] Tkinter instalado correctamente."
    else
        echo "[ERROR] No se pudo instalar Tkinter."
        exit 1
    fi
fi

# ── Verificar módulos stdlib usados por la app ─────────────────────────────
echo ""
echo ">>> Verificando módulos de la librería estándar..."

MODULES=("csv" "os" "abc" "tkinter" "tkinter.ttk" "tkinter.filedialog" "tkinter.messagebox")
ALL_OK=true

for mod in "${MODULES[@]}"; do
    if python3 -c "import $mod" &>/dev/null; then
        echo "    [OK] $mod"
    else
        echo "    [ERROR] $mod no disponible"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo ""
    echo "[ERROR] Algunos módulos no están disponibles. Revisa tu instalación de Python."
    exit 1
fi

# ── Verificar archivos del proyecto ────────────────────────────────────────
echo ""
echo ">>> Verificando archivos del proyecto..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR/regear_app"
CSV_FILE="$SCRIPT_DIR/MAGA Regear Charts - Price Charts.csv"

if [ -d "$APP_DIR" ]; then
    echo "    [OK] Carpeta regear_app/ encontrada."
else
    echo "    [ERROR] Carpeta regear_app/ no encontrada en $SCRIPT_DIR"
    exit 1
fi

if [ -f "$CSV_FILE" ]; then
    echo "    [OK] CSV de precios encontrado."
else
    echo "    [AVISO] CSV de precios no encontrado. Podrás cargarlo manualmente desde la app."
fi

# ── Crear lanzador ──────────────────────────────────────────────────────────
echo ""
echo ">>> Creando lanzador (lanzar.sh)..."

cat > "$SCRIPT_DIR/lanzar.sh" << EOF
#!/usr/bin/env bash
# lanzar.sh — Inicia RegearApp for Albion Online
cd "\$(dirname "\${BASH_SOURCE[0]}")/regear_app"
python3 main.py
EOF

chmod +x "$SCRIPT_DIR/lanzar.sh"
echo "    [OK] Lanzador creado: lanzar.sh"

# ── Resumen ─────────────────────────────────────────────────────────────────
echo ""
echo "================================================="
echo "  Instalación completada."
echo ""
echo "  Para iniciar la app ejecuta:"
echo "    ./lanzar.sh"
echo ""
echo "  O manualmente:"
echo "    cd regear_app && python3 main.py"
echo "================================================="
