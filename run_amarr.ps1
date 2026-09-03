param(
    [double]$Capital = 427934016,
    [int]$MaxOrders = 5
)

$ErrorActionPreference = "Stop"
$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Project virtual environment not found. Run the setup commands in README.md once."
}

& $python (Join-Path $PSScriptRoot "src\eve_quant\run_advisor.py") `
    --hub amarr `
    --capital $Capital `
    --max-orders $MaxOrders
