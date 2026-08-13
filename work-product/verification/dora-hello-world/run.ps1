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
    $tools = Join-Path $root ".tools"
    $dora = Join-Path $tools "dora.exe"
    $cliVersion = "1.0.0-rc.4"
    $archiveUrl = "https://github.com/dora-rs/dora/releases/download/v$cliVersion/dora-cli-x86_64-pc-windows-msvc.zip"
    $archiveSha256 = "e881d7b0ec2516aa7e30e6403d6db2e5d8cb7dcbda8e15d820ce38b1b6bc3ece"

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
        New-Item -ItemType Directory -Force -Path $tools | Out-Null
        $archive = Join-Path $tools "dora-cli.zip"
        Invoke-WebRequest -Uri $archiveUrl -OutFile $archive
        $actualSha256 = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualSha256 -ne $archiveSha256) {
            throw "Dora CLI archive checksum mismatch."
        }
        $expanded = Join-Path $tools "expanded"
        Expand-Archive -Path $archive -DestinationPath $expanded -Force
        $candidates = @(Get-ChildItem -LiteralPath $expanded -Recurse -File -Filter "dora.exe")
        if ($candidates.Count -ne 1) {
            throw "Expected exactly one dora.exe in the verified CLI archive."
        }
        Copy-Item -LiteralPath $candidates[0].FullName -Destination $dora
    }

    Write-Host "== Environment =="
    Write-Host "Example root: <repo>\work-product\verification\dora-hello-world"
    $doraVersion = & $dora --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "dora --version failed."
    }
    $doraVersion | ForEach-Object { Write-Host $_.ToString() }

    $versionCommand = 'import importlib.metadata as m, pyarrow, yaml, sys; print("python " + sys.version.split()[0]); print("dora-rs python package " + m.version("dora-rs")); print("pyarrow " + pyarrow.__version__); print("pyyaml " + yaml.__version__)'
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
