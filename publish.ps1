<#
.SYNOPSIS
    Regenerate the MauLaw digest-review site and publish it to GitHub Pages.

.DESCRIPTION
    Pure script workflow, no AI session required: runs build-site.py against
    cases.json, then commits and pushes site/docs/ (and the manifest/generator
    themselves) to the maulaw-review repo's main branch, which GitHub Pages
    serves from /docs. Every stage fails loudly with a nonzero exit.

.NOTES
    Invoke as a script from anywhere (it resolves paths off $PSScriptRoot),
    e.g. `& C:\Claude\MauLaw\site\publish.ps1` or `.\publish.ps1` from inside
    site\.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$SiteDir = $PSScriptRoot

function Write-Stage { param([string]$Stage) Write-Host ""; Write-Host ">>> stage: $Stage" -ForegroundColor Cyan }
function Fail-Stage {
    param([string]$Stage, [string]$Message)
    Write-Host ""
    Write-Host "=== STAGE FAILED: $Stage ===" -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    exit 1
}

# --------------------------------------------------------------------------
# Stage 1: build -- regenerate site\docs\ from cases.json.
# --------------------------------------------------------------------------
Write-Stage "build"

$CasesJsonPath = Join-Path $SiteDir 'cases.json'
if (-not (Test-Path -LiteralPath $CasesJsonPath -PathType Leaf)) {
    Fail-Stage "build" "Manifest not found: $CasesJsonPath"
}
try {
    $CaseCount = @(Get-Content -LiteralPath $CasesJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json).Count
} catch {
    Fail-Stage "build" "Could not parse manifest: $($_.Exception.Message)"
}

Push-Location $SiteDir
try {
    $BuildOutput = & python (Join-Path $SiteDir 'build-site.py') 2>&1
    $BuildExit = $LASTEXITCODE
} finally {
    Pop-Location
}
Write-Host ($BuildOutput | Out-String)
if ($BuildExit -ne 0) {
    Fail-Stage "build" "build-site.py exited with code ${BuildExit}"
}

$DocsDir = Join-Path $SiteDir 'docs'
if (-not (Test-Path -LiteralPath (Join-Path $DocsDir 'index.html') -PathType Leaf)) {
    Fail-Stage "build" "Expected output not found: $(Join-Path $DocsDir 'index.html')"
}
Write-Host "    built $CaseCount case(s) -> $DocsDir"

# --------------------------------------------------------------------------
# Stage 2: commit -- stage the generator, manifest, and generated docs/, then
# commit. A clean tree (nothing changed since last publish) is not an error.
# --------------------------------------------------------------------------
Write-Stage "commit"

Push-Location $SiteDir
try {
    if (-not (Test-Path -LiteralPath (Join-Path $SiteDir '.git') -PathType Container)) {
        Fail-Stage "commit" "site\ is not a git repository (expected site\.git). Run git init + gh repo create first."
    }

    git add cases.json build-site.py publish.ps1 README.md .gitignore docs
    if ($LASTEXITCODE -ne 0) { Fail-Stage "commit" "git add failed with exit code $LASTEXITCODE" }

    $StatusOutput = git status --porcelain
    if ([string]::IsNullOrWhiteSpace($StatusOutput)) {
        Write-Host "    nothing to commit -- tree already matches last publish"
    } else {
        $CommitMsg = "Publish review site: $CaseCount case(s) ($(Get-Date -Format 'yyyy-MM-dd'))"
        git commit -m $CommitMsg
        if ($LASTEXITCODE -ne 0) { Fail-Stage "commit" "git commit failed with exit code $LASTEXITCODE" }
        Write-Host "    committed: $CommitMsg"
    }
} finally {
    Pop-Location
}

# --------------------------------------------------------------------------
# Stage 3: push.
# --------------------------------------------------------------------------
Write-Stage "push"

Push-Location $SiteDir
try {
    git push
    if ($LASTEXITCODE -ne 0) { Fail-Stage "push" "git push failed with exit code $LASTEXITCODE" }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== publish complete: $CaseCount case(s) ===" -ForegroundColor Green
exit 0
