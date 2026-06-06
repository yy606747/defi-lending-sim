$ErrorActionPreference = "Stop"

Set-Location (Split-Path $PSScriptRoot -Parent)

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 main.py --config demo.yaml
} else {
    python main.py --config demo.yaml
}
