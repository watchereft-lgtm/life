# Запуск приложения локально на Windows.
# Создаёт окружение .venv, ставит зависимости и поднимает Streamlit.
#
#   .\run.ps1                  # обычный запуск на порту 8501
#   .\run.ps1 -Port 8600       # другой порт
#   .\run.ps1 -SkipInstall     # не переустанавливать зависимости
#
# Если PowerShell запрещает запуск скриптов:
#   powershell -ExecutionPolicy Bypass -File .\run.ps1

param(
    [int]$Port = 8501,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$venv = Join-Path $root ".venv"
if (-not (Test-Path $venv)) {
    Write-Host "Создаю окружение .venv..."
    python -m venv $venv
}

$python = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Не найден $python. Установите Python 3.10+ с python.org и повторите."
}

if (-not $SkipInstall) {
    Write-Host "Ставлю зависимости из requirements.txt..."
    & $python -m pip install --upgrade pip
    & $python -m pip install -r (Join-Path $root "requirements.txt")
}

Write-Host "Открываю http://localhost:$Port ..."
& $python -m streamlit run (Join-Path $root "game_of_life.py") --server.port $Port
