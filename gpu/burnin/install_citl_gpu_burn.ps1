param(
    [int]$Seconds = 600  # default 10 minutes
)

$ErrorActionPreference = "Stop"

Write-Host "[CITL] GPU Burn helper starting..." -ForegroundColor Cyan

# Global kill switch if we ever need it
if ($env:CITL_DISABLE_GPU_BURN -eq "1") {
    Write-Warning "[CITL] CITL_DISABLE_GPU_BURN=1 - GPU burn disabled. Exiting."
    exit 0
}

# 1) Check NVIDIA tools
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if (-not $nvidiaSmi) {
    Write-Error "[CITL] nvidia-smi not found in PATH. Install NVIDIA drivers / CUDA toolkit first."
    exit 1
}

$nvcc = Get-Command nvcc -ErrorAction SilentlyContinue
if (-not $nvcc) {
    Write-Error "[CITL] nvcc (CUDA compiler) not found in PATH. Install CUDA Toolkit before running gpu-burn."
    exit 1
}

# 2) Guardrails so we don't fry tiny GPUs (Cannakit-class, etc.)
try {
    $info = & $nvidiaSmi.Path --query-gpu=name,memory.total --format=csv,noheader
    if ($info) {
        $first  = $info.Split("`n")[0].Trim()
        $parts  = $first.Split(",")
        $gpuName = $parts[0].Trim()
        $memField = $parts[1].Trim()
        $memMiB   = [int]($memField.Split(" ")[0])

        Write-Host "[CITL] Detected GPU: $gpuName ($memMiB MiB)" -ForegroundColor Yellow

        
        if ($memMiB -lt 6000) {
            Write-Warning "[CITL] GPU has only $memMiB MiB VRAM. This looks like a low-power / lab device."
            $ans = Read-Host "[CITL] Type YES in all caps to run gpu-burn anyway"
            if ($ans -ne "YES") {
                Write-Host "[CITL] Aborting GPU burn." -ForegroundColor Cyan
                exit 0
            }
        }
    }
}
catch {
    Write-Warning "[CITL] Could not query GPU info via nvidia-smi. Continuing without the extra guardrail."
}

# 3) Locate gpu-burn sources
$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$gpuBurnDir = Join-Path $scriptDir "gpu-burn"

if (-not (Test-Path $gpuBurnDir)) {
    Write-Error "[CITL] gpu-burn directory not found at $gpuBurnDir. Make sure gpu-burn-master.zip was extracted here."
    exit 1
}

Push-Location $gpuBurnDir
try {
    # 4) Build gpu_burn.exe once if needed
    if (-not (Test-Path ".\gpu_burn.exe")) {
        Write-Host "[CITL] Building gpu_burn.exe with nvcc..." -ForegroundColor Cyan
        & $nvcc.Path "gpu_burn.cu" -O3 -o "gpu_burn.exe"
    }

    # 5) Run the burn
    Write-Host "[CITL] Running gpu_burn.exe for $Seconds seconds on all GPUs..." -ForegroundColor Cyan
    .\gpu_burn.exe $Seconds

    Write-Host "[CITL] GPU burn completed." -ForegroundColor Green
}
finally {
    Pop-Location
}