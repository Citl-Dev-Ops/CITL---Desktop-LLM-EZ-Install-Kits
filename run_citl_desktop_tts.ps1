Write-Host "=== CITL Desktop: Text-to-Speech (TTS) launcher ===" -ForegroundColor Cyan

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$factbookPath = Join-Path $root "factbook-assistant"
Write-Host "Using factbook-assistant at: $factbookPath"

if (-not (Test-Path $factbookPath)) {
    Write-Host "ERROR: factbook-assistant folder not found." -ForegroundColor Red
    Write-Host "Expected at: $factbookPath" -ForegroundColor Red
    Write-Host "Press Enter to close." -ForegroundColor Yellow
    Read-Host | Out-Null
    return
}

Set-Location $factbookPath

# Find Python
$pythonCmd = $null
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonCmd = ".\.venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} else {
    Write-Host "ERROR: No python found (neither .venv\Scripts\python.exe nor system 'python')." -ForegroundColor Red
    Write-Host "Install Python 3.x and/or create the venv from the Factbook-Assistant repo." -ForegroundColor Red
    Write-Host "Press Enter to close." -ForegroundColor Yellow
    Read-Host | Out-Null
    return
}

Write-Host "Using Python: $pythonCmd"

# Create venv if missing
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment in .venv ..." -ForegroundColor Yellow
    & $pythonCmd -m venv .venv
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        Write-Host "ERROR: venv creation seems to have failed." -ForegroundColor Red
        Write-Host "Press Enter to close." -ForegroundColor Yellow
        Read-Host | Out-Null
        return
    }
    $pythonCmd = ".\.venv\Scripts\python.exe"
    Write-Host "Venv created. Using venv Python: $pythonCmd"
}

Write-Host "Ensuring TTS-related dependencies are installed..." -ForegroundColor Yellow
& $pythonCmd -m pip install --upgrade pip
& $pythonCmd -m pip install numpy requests tqdm sounddevice pyttsx3 openai-whisper numba tiktoken torch

# Optional: display torch / CUDA status (non-fatal)
Write-Host "`nChecking torch / CUDA (informational)..." -ForegroundColor DarkCyan
& $pythonCmd - << 'PYCODE'
import torch
print("Torch version:", getattr(torch, "__version__", "unknown"))
cuda_ok = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
print("CUDA available:", cuda_ok)
PYCODE

# Check TTS script exists
if (-not (Test-Path ".\citl_tts.py")) {
    Write-Host "ERROR: citl_tts.py not found in $factbookPath" -ForegroundColor Red
    Write-Host "Place your TTS script as citl_tts.py in the factbook-assistant folder." -ForegroundColor Red
    Write-Host "Press Enter to close." -ForegroundColor Yellow
    Read-Host | Out-Null
    return
}

Write-Host "`nLaunching TTS tool (citl_tts.py)..." -ForegroundColor Green
& $pythonCmd .\citl_tts.py

Write-Host "`nTTS script finished. Press Enter to close." -ForegroundColor Cyan
Read-Host | Out-Null
