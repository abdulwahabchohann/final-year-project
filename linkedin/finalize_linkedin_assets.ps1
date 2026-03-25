param(
    [Parameter(Mandatory = $true)]
    [string]$DemoUrl,
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"

if (-not ($DemoUrl -match "^https?://")) {
    throw "DemoUrl must start with http:// or https://"
}

$normalizedDemoUrl = $DemoUrl.Trim().TrimEnd("/")

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$targetFiles = @(
    (Join-Path $scriptDir "caption.txt"),
    (Join-Path $scriptDir "featured_section.md"),
    (Join-Path $scriptDir "project_entry.md")
)

foreach ($file in $targetFiles) {
    if (-not (Test-Path -LiteralPath $file)) {
        throw "Required file not found: $file"
    }

    $original = Get-Content -LiteralPath $file -Raw
    $updated = $original.Replace("[YOUR_RENDER_URL]", $normalizedDemoUrl)

    if ($updated -ne $original) {
        Set-Content -LiteralPath $file -Value $updated
        Write-Host "Updated demo URL in: $file"
    } else {
        Write-Host "No placeholder found in: $file"
    }
}

if (-not $SkipValidation) {
    $validator = Join-Path $scriptDir "validate_links.ps1"
    if (-not (Test-Path -LiteralPath $validator)) {
        throw "validate_links.ps1 not found at $validator"
    }
    & $validator -DemoUrl $normalizedDemoUrl
}

Write-Host "LinkedIn assets finalized."
