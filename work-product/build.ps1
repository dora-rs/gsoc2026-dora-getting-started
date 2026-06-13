param(
    [switch] $Clean
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$book = Join-Path $root "book"

if ($Clean -and (Test-Path $book)) {
    $resolvedBook = (Resolve-Path $book).Path
    if (-not $resolvedBook.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove outside work-product: $resolvedBook"
    }
    Remove-Item -LiteralPath $resolvedBook -Recurse -Force
}

Push-Location $root
try {
    mdbook build .
    mdbook build .\en
    mdbook build .\zh
}
finally {
    Pop-Location
}
