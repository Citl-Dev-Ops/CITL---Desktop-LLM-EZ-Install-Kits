Write-Host "=== CITL Desktop LLM + Factbook setup & demo ===" -ForegroundColor Cyan

# 1. Work out where we are and where factbook-assistant lives
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$factbookPath = Join-Path $root "factbook-assistant"

if (-not (Test-Path $factbookPath)) {
    Write-Host "ERROR: factbook-assistant folder not found at $factbookPath" -ForegroundColor Red
    Write-Host "Make sure you copied Factbook-Assistant into this repo as 'factbook-assistant'." -ForegroundColor Red
    exit 1
}

Write-Host "Using factbook-assistant at: $factbookPath"
Set-Location $factbookPath

# 2. Pick a Python executable (no 'py' launcher required)
$pythonCmd = $null

# If a venv already exists, prefer its python
if (Test-Path ".\.venv\Scripts\python.exe") {
    $pythonCmd = ".\.venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCmd = "python"
} else {
    Write-Host "ERROR: No 'python' command found in PATH." -ForegroundColor Red
    Write-Host "Install Python 3.x from python.org and re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $pythonCmd"
$pyVersion = & $pythonCmd --version 2>$null
Write-Host "Detected $pyVersion"

# 3. Create virtual environment if it doesn't exist
if (-not (Test-Path ".\.venv")) {
    Write-Host "Creating virtual environment in .venv ..."
    & $pythonCmd -m venv .venv
}

# 4. Activate virtual environment
Write-Host "Activating virtual environment..."
& ".\.venv\Scripts\Activate.ps1"

# Now 'python' and 'pip' should be from the venv
python --version

# 5. Install Python dependencies
Write-Host "Installing Python dependencies into venv..."
pip install --upgrade pip
pip install numpy requests tqdm sounddevice pyttsx3 openai-whisper numba tiktoken torch

# 6. Check for Ollama (optional but recommended)
Write-Host "Checking Ollama..."
$ollamaVersion = & ollama --version 2>$null
if (-not $ollamaVersion) {
    Write-Host "WARNING: Ollama not found. RAG question-answering will not work until Ollama is installed." -ForegroundColor Yellow
} else {
    Write-Host "Ollama: $ollamaVersion"
    Write-Host "Pulling required models (mistral:7b-instruct, nomic-embed-text)..."
    ollama pull mistral:7b-instruct
    ollama pull nomic-embed-text
}

# 7. Build embeddings if missing
if (-not (Test-Path ".\factbook_embeddings.json")) {
    Write-Host "Building Factbook embedding index..."
    python .\build_factbook_index.py
} else {
    Write-Host "factbook_embeddings.json already exists, skipping."
}

if ((Test-Path ".\Introduction to the Law of Property, Estate Planning, and Insurance.txt") -and
    (-not (Test-Path ".\law_embeddings.json"))) {
    Write-Host "Building law_embeddings.json..."
    python .\build_corpus_index.py --src "Introduction to the Law of Property, Estate Planning, and Insurance.txt" --out "law_embeddings.json"
}

if ((Test-Path ".\Nursing Fundamentals 2e.txt") -and
    (-not (Test-Path ".\nursing_embeddings.json"))) {
    Write-Host "Building nursing_embeddings.json..."
    python .\build_corpus_index.py --src "Nursing Fundamentals 2e.txt" --out "nursing_embeddings.json"
}

if ((Test-Path ".\The New Oxford American Dictionary.txt") -and
    (-not (Test-Path ".\dictionary_embeddings.json"))) {
    Write-Host "Building dictionary_embeddings.json..."
    python .\build_corpus_index.py --src "The New Oxford American Dictionary.txt" --out "dictionary_embeddings.json"
}

Write-Host ""
Write-Host "=== Setup complete. Example demo commands: ===" -ForegroundColor Green
Write-Host "  cd `"$factbookPath`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python .\query_factbook.py `"capital:laos`""
Write-Host "  python .\citl_multi_rag.py --source all `"Explain what a tort is and give an example related to medication errors.`""
Write-Host "  python .\citl_tts.py"
Write-Host "  python .\citl_transcribe_lecture.py"
