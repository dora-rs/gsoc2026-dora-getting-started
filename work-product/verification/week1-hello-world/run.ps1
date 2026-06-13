param(
    [int] $Seconds = 4,
    [switch] $SkipInstall
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$previousLocation = Get-Location

try {
    Set-Location $root

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        throw "uv was not found on PATH. Install uv first, then open a new PowerShell session."
    }

    $venv = Join-Path $root ".venv"
    $python = Join-Path $venv "Scripts\python.exe"
    $dora = Join-Path $venv "Scripts\dora.exe"

    if (-not (Test-Path $python)) {
        uv venv --seed -p 3.11 $venv
        if ($LASTEXITCODE -ne 0) {
            throw "uv failed to create the local virtual environment."
        }
    }

    if (-not $SkipInstall) {
        & $python -m pip install --upgrade -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            throw "pip failed to install verification requirements."
        }
    }

    if (-not (Test-Path $dora)) {
        throw "Dora CLI was not installed in the local virtual environment."
    }

    Write-Host "== Environment =="
    Write-Host "Example root: <repo>\work-product\verification\week1-hello-world"
    $doraVersion = & $dora --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "dora --version failed."
    }
    $doraVersion | ForEach-Object { Write-Host $_.ToString() }

    $versionCommand = 'import dora, pyarrow, yaml, sys; print("python " + sys.version.split()[0]); print("dora-rs python package " + getattr(dora, "__version__", "unknown")); print("pyarrow " + pyarrow.__version__); print("pyyaml " + yaml.__version__)'
    & $python -c $versionCommand
    if ($LASTEXITCODE -ne 0) {
        throw "Python package version probe failed."
    }

    $logDir = Join-Path $root "logs"
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $logPath = Join-Path $logDir "latest-run.log"
    $duration = "${Seconds}s"

    Write-Host "== Running dataflow for $duration =="
    $runOutput = & $dora run dataflow.yml --uv --stop-after $duration 2>&1
    $exitCode = $LASTEXITCODE
    $runOutput | Set-Content -Path $logPath -Encoding UTF8
    $runOutput | Write-Output

    if ($exitCode -ne 0) {
        throw "dora run failed with exit code $exitCode. See logs\latest-run.log."
    }

    $runText = $runOutput -join "`n"
    if ($runText -notmatch "listener received: Hello from dora-rs") {
        throw "Expected listener output was not found. See logs\latest-run.log."
    }

    Write-Host "Verified: listener output was observed."
}
finally {
    Set-Location $previousLocation
}
