
        # ============================================================
#  META PIPELINE — DEV TOOLS (dev_tools.ps1)
#  This file now uses $PSScriptRoot so it is portable.
# ============================================================

param (
    [string]$Action = "help"
)

# This automatically detects the folder this script is sitting in
$ROOT = $PSScriptRoot

# ── 1. FIND YOUR WORKING REPO ────────────────────────────────
function Find-Repo {
    Get-ChildItem -Path (Split-Path $ROOT -Parent) -Directory | Select-Object Name
}

# ── 2. FIND FASTAPI ENTRY POINTS ────────────────────────────
function Find-FastAPI {
    Get-ChildItem -Path $ROOT -Recurse -Filter "*.py" |
    Select-String -Pattern "FastAPI|APIRouter|@app\.|@router\." |
    Select-Object Path, LineNumber, Line
}

# ── 3. FIND WHERE A PATTERN LIVES ───────────────────────────
function Find-Pattern {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Pattern
    )
    # The DevOps way: Use ripgrep directly
    Write-Host "🔍 Ripgrep searching codebase for: '$Pattern'..." -ForegroundColor Cyan
    rg --line-number --heading --color=always $Pattern
}

# ── 4. CLEAN HIDDEN CHARACTERS FROM A FILE ──────────────────
function Clean-File {
    param([string]$FilePath)
    $content = Get-Content -Path $FilePath -Raw
    $cleaned = $content -replace '[^\x09\x0A\x0D\x20-\x7E]', ''
    Set-Content -Path $FilePath -Value $cleaned -NoNewline
    Write-Host "✅ Hidden characters removed from $FilePath"
}

# ── 5. ADD ENDPOINT TO api.py ────────────────────────────────
function Add-Endpoint {
    param(
        [string]$FilePath,
        [string]$RoutePattern,
        [string]$ModelName,
        [string]$ModelFields,
        [string]$FunctionName,
        [string]$OrchestratorMethod
    )

    $content = Get-Content -Path $FilePath -Raw

    if ($content -match $ModelName) {
        Write-Host "⚠️  $ModelName already exists — skipping model insert."
    } else {
        $model = "`n`nclass ${ModelName}(BaseModel):`n    $ModelFields"
        $content = $content -replace `
            '(class \w+\(BaseModel\):[\s\S]*?(?=\r?\n\r?\n|\r?\nclass |\r?\n@|\r?\napp\.))',
            "`$1$model"
        Write-Host "✅ $ModelName class inserted."
    }

    if ($content -match [regex]::Escape($RoutePattern)) {
        Write-Host "⚠️  $RoutePattern route already exists — skipping route insert."
    } else {
        $route = @"

@router.post("$RoutePattern")
async def $FunctionName(request: $ModelName, orchestrator = Depends(get_orchestrator)):
    logger.info(f"REQUEST: client_id={request.client_id}")
    try:
        result = orchestrator.$OrchestratorMethod(
            client_id=request.client_id,
            context=request.context
        )
        return {"status": "ok", "client_id": request.client_id, "result": result}
    except Exception as e:
        logger.error(f"FAILED: {e}")
        raise HTTPException(status_code=500, detail=str(e))

"@
        $content = $content -replace "app\.include_router\(router\)", "$route`napp.include_router(router)"
        Write-Host "✅ $RoutePattern route inserted."
    }

    Set-Content -Path $FilePath -Value $content -NoNewline
    Write-Host "✅ Saved: $FilePath"
}

# ── 6. FIX A BAD CONDITION IN ANY FILE ──────────────────────
function Fix-Condition {
    param(
        [string]$FilePath,
        [string]$OldPattern,
        [string]$NewValue
    )
    (Get-Content -Path $FilePath -Raw) -replace $OldPattern, $NewValue |
    Set-Content -Path $FilePath -NoNewline
    Write-Host "✅ Condition fixed in $FilePath"
}

# ── 7. VERIFY PATTERNS EXIST IN A FILE ──────────────────────
function Verify-File {
    param([string]$FilePath, [string]$Pattern)
    Select-String -Path $FilePath -Pattern $Pattern
}

# ── 8. GIT UNDO ─────────────────────────────────────────────
function Git-Undo {
    param([string]$RelativePath)
    Set-Location $ROOT
    git checkout $RelativePath
    Write-Host "✅ Reverted: $RelativePath"
}

# ── HELP ─────────────────────────────────────────────────────
function Show-Help {
    Write-Host @"
Toolbox Loaded. Use the functions listed below:
  Find-Repo | Find-FastAPI | Find-Pattern -Pattern "x"
  Clean-File -FilePath "x" | Verify-File -FilePath "x" -Pattern "y"
  Fix-Condition -FilePath "x" -OldPattern "y" -NewValue "z"
  Git-Undo -RelativePath "x"
"@
}

Show-Help
