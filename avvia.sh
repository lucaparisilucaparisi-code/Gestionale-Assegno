#!/bin/bash
set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   Assegnazione automatica OEPAC - DGC 260/2024         ║"
echo "║   Avvio in corso, attendere...                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")"

# --- Cerca Python ---
if command -v python3 &>/dev/null; then
    PYTHON_CMD=python3
elif command -v python &>/dev/null; then
    PYTHON_CMD=python
else
    echo "[ERRORE] Python non trovato."
    echo "Installa Python 3: https://www.python.org/downloads/"
    exit 1
fi
echo "[OK] Python trovato: $PYTHON_CMD"

# --- Crea ambiente virtuale ---
if [ ! -d "venv" ]; then
    echo "[*] Creazione ambiente virtuale..."
    $PYTHON_CMD -m venv venv
    echo "[OK] Ambiente virtuale creato."
fi

# --- Attiva e installa ---
source venv/bin/activate
echo "[*] Controllo dipendenze..."
pip install -q -r requirements.txt
echo "[OK] Dipendenze installate."

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  L'applicazione si aprira' nel browser."
echo "  Per chiudere, premi CTRL+C."
echo "══════════════════════════════════════════════════════════"
echo ""

streamlit run app.py --server.headless true --server.port 8501
