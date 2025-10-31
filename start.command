
#!/bin/bash
# Avvio rapido per Mac
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv || exit 1
fi
source .venv/bin/activate
pip install -r requirements.txt
python app.py
