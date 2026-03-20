# LAW-GPT Full Azure Deployment Script
# Builds deployment zip (respecting .azignore) and deploys with az webapp deploy
#
# Usage: .\deploy_full.ps1

$RG   = "lawgpt-rg"
$APP  = "lawgpt-backend2024"
$ROOT = "C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT"
$ZIP  = "$ROOT\deploy_full_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip"

function Write-Step { param($m) Write-Host "`n>>> $m" -ForegroundColor Cyan }
function Write-OK   { param($m) Write-Host "  [OK] $m"   -ForegroundColor Green  }
function Write-FAIL { param($m) Write-Host "  [!!] $m"   -ForegroundColor Red    }
function Write-INFO { param($m) Write-Host "  [..] $m"   -ForegroundColor White  }

# ── Folders/patterns to EXCLUDE (based on .azignore) ──────────────────────────
$EXCLUDE_DIRS = @(
    ".git", ".github", ".vscode", ".venv", "venv",
    "chroma_db_statutes", "chroma_db_hybrid", "chroma_db_cases",
    "DATA", "PERMANENT_RAG_FILES",
    "CONSUMER_DATA_COLLECTION", "CONSUMER_DATA_COLLECTION.zip",
    "frontend", "node_modules",
    "testsprite_tests", "TEST", "TEST_SPRIT", "tmp",
    "__pycache__", "deployment_bundle",
    "azure_logs", "azure_build_logs", "azure_latest_logs",
    "advance_rag_upcoming_idea",
    "azure_deploy_logs", ".agent", ".clinerules", ".trae",
    "results"
)
$EXCLUDE_EXTS = @(".pyc", ".pyo", ".bin", ".zip", ".exe", ".dll", ".log")
$EXCLUDE_FILES = @("cloudflared.exe", "cloudflared.log", "nul",
    "indian_kanoon_collection.json"   # 32MB pre-downloaded data; Azure queries API directly
)

Write-Step "Building deployment zip: $(Split-Path $ZIP -Leaf)"

# Collect all files to include
$allFiles = Get-ChildItem -LiteralPath $ROOT -Recurse -File | Where-Object {
    $path = $_.FullName
    $relPath = $path.Substring($ROOT.Length + 1)
    
    # Exclude by extension
    if ($EXCLUDE_EXTS -contains $_.Extension) { return $false }
    
    # Exclude by filename
    if ($EXCLUDE_FILES -contains $_.Name) { return $false }
    
    # Exclude files inside excluded dirs
    $topPart = $relPath.Split([IO.Path]::DirectorySeparatorChar)[0]
    if ($EXCLUDE_DIRS -contains $topPart) { return $false }
    
    # Also exclude any path segment that matches excluded dirs
    $parts = $relPath.Split([IO.Path]::DirectorySeparatorChar)
    foreach ($part in $parts) {
        if ($EXCLUDE_DIRS -contains $part) { return $false }
    }
    
    # Exclude tmpclaude-* temp files
    if ($_.Name -match "^tmpclaude-") { return $false }
    if ($relPath -match "\\tmpclaude-") { return $false }
    
    # Exclude *.zip, *.exe, *.bin, *.dll explicitly by name too
    if ($_.Name -match "\.(zip|exe|bin|dll|log)$") { return $false }
    
    return $true
}

Write-INFO "Files to include: $($allFiles.Count)"

# Build zip using .NET for better performance
Add-Type -Assembly "System.IO.Compression.FileSystem"
$zipMode = [System.IO.Compression.ZipArchiveMode]::Create
$zipStream = [System.IO.File]::Open($ZIP, [System.IO.FileMode]::Create, [System.IO.FileAccess]::ReadWrite)
$archive = New-Object System.IO.Compression.ZipArchive($zipStream, $zipMode)

$added = 0
$skipped = 0
foreach ($file in $allFiles) {
    try {
        $relPath = $file.FullName.Substring($ROOT.Length + 1).Replace("\", "/")
        $entry = $archive.CreateEntry($relPath)
        $entryStream = $entry.Open()
        $fileStream  = [System.IO.File]::OpenRead($file.FullName)
        $fileStream.CopyTo($entryStream)
        $fileStream.Close()
        $entryStream.Close()
        $added++
    } catch {
        Write-WARN "  Skip (locked?): $($file.Name) — $_"
        $skipped++
    }
}

$archive.Dispose()
$zipStream.Close()

$zipSizeMB = [math]::Round((Get-Item $ZIP).Length / 1MB, 1)
Write-OK "Zip built: $ZIP ($zipSizeMB MB, $added files, $skipped skipped)"

if ($zipSizeMB -gt 1900) {
    Write-FAIL "Zip exceeds 1900MB (Azure App Service limit). Check exclusions."
    exit 1
}

# ── Deploy ─────────────────────────────────────────────────────────────────────
Write-Step "Deploying to Azure App Service: $APP (RG: $RG)"
Write-INFO "This may take 3-10 minutes..."

$deployResult = az webapp deploy `
    --resource-group $RG `
    --name $APP `
    --src-path $ZIP `
    --type zip `
    --async false `
    2>&1

Write-Host $deployResult -ForegroundColor Gray

if ($LASTEXITCODE -eq 0) {
    Write-OK "Deployment command succeeded!"
} else {
    Write-FAIL "Deployment command returned exit code $LASTEXITCODE"
    Write-INFO "Checking if app is still starting..."
}

# ── Wait for app to come back up ───────────────────────────────────────────────
Write-Step "Waiting for app to start (~60-90s for cold start)..."
$healthUrl = "https://$APP.azurewebsites.net/api/health"
$maxWait = 180
$elapsed = 0
$interval = 15

Start-Sleep -Seconds 30

while ($elapsed -lt $maxWait) {
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 20 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            Write-OK "App is HEALTHY: $($resp.Content.Substring(0, [Math]::Min(120, $resp.Content.Length)))"
            break
        }
        Write-INFO "Status $($resp.StatusCode) — waiting..."
    } catch {
        Write-INFO "[$elapsed`s] Not ready yet: $($_.Exception.Message.Substring(0, [Math]::Min(80, $_.Exception.Message.Length)))"
    }
    Start-Sleep -Seconds $interval
    $elapsed += $interval
}

if ($elapsed -ge $maxWait) {
    Write-FAIL "App did not come up within ${maxWait}s — check logs:"
    Write-INFO "  az webapp log tail --name $APP --resource-group $RG"
} else {
    Write-OK "=== DEPLOYMENT COMPLETE ==="
    Write-INFO "App URL: https://$APP.azurewebsites.net"
}
