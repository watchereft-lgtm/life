#!/usr/bin/env bash
# Запуск приложения локально на Linux/macOS.
#   ./run.sh              # порт 8501
#   ./run.sh 8600         # другой порт
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$root"
port="${1:-8501}"

if [ ! -d .venv ]; then
  echo "Создаю окружение .venv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "Открываю http://localhost:${port} ..."
exec python -m streamlit run game_of_life.py --server.port "$port"
