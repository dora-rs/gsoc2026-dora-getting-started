param(
    [int] $Port = 3000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $root "build.ps1") -Clean
node (Join-Path $root "tools\serve-book.mjs") --port $Port
