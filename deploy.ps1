# LAW-GPT PageIndex Deploy Script
# Uses Kudu VFS API (Bearer token) -- no az webapp deploy polling issues
#
# Usage:
#   .\deploy.ps1                        -- upload files + restart
#   .\deploy.ps1 -SetKey pi_xxxxxxxx   -- set PAGEINDEX_API_KEY in App Settings
#   .\deploy.ps1 -CheckOnly            -- status check only
#   .\deploy.ps1 -NoRestart            -- upload but skip restart

param(
    [string]$SetKey    = "",
    [switch]$CheckOnly = $false,
    [switch]$NoRestart = $false
)

$RG   = "lawgpt-rg"
$APP  = "lawgpt-backend2024"
$BASE = "C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT"
$KUDU = "https://lawgpt-backend2024.scm.azurewebsites.net"

$FILES = @(
    @{ L = "$BASE\kaanoon_test\advanced_rag_api_server.py";                R = "kaanoon_test/advanced_rag_api_server.py"              },
    @{ L = "$BASE\kaanoon_test\system_adapters\clarification_engine.py"; R = "kaanoon_test/system_adapters/clarification_engine.py" },
    @{ L = "$BASE\kaanoon_test\system_adapters\pageindex_retriever.py";  R = "kaanoon_test/system_adapters/pageindex_retriever.py" },
    @{ L = "$BASE\kaanoon_test\system_adapters\agentic_rag_engine.py";   R = "kaanoon_test/system_adapters/agentic_rag_engine.py"  },
    @{ L = "$BASE\kaanoon_test\system_adapters\persistent_memory.py";    R = "kaanoon_test/system_adapters/persistent_memory.py"   },
    @{ L = "$BASE\kaanoon_test\system_adapters\unified_advanced_rag.py"; R = "kaanoon_test/system_adapters/unified_advanced_rag.py" },
    @{ L = "$BASE\requirements.txt"; R = "requirements.txt" },
    @{ L = "$BASE\startup.sh";       R = "startup.sh" }
)

function Write-OK   { param($m) Write-Host "  [OK]  $m" -ForegroundColor Green  }
function Write-FAIL { param($m) Write-Host "  [!!]  $m" -ForegroundColor Red    }
function Write-INFO { param($m) Write-Host "  [..]  $m" -ForegroundColor Cyan   }
function Write-WARN { param($m) Write-Host "  [??]  $m" -ForegroundColor Yellow }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  LAW-GPT PageIndex Deploy (Kudu VFS + Azure CLI)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Authenticate via AAD Bearer token (works with Kudu VFS API)
Write-Host "`n[AUTH] Getting AAD Bearer token..."
$token = az account get-access-token --query accessToken -o tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-FAIL "Not logged in. Run: az login"
    exit 1
}
$hdrs = @{ Authorization = "Bearer $token"; "If-Match" = "*" }
$acct = az account show --query "name" -o tsv 2>&1
Write-OK "Authenticated: $acct"

# ------------------------------------------------------------------
# CHECK ONLY
# ------------------------------------------------------------------
if ($CheckOnly) {
    Write-Host "`n[STATUS] App: $APP"
    az webapp show --resource-group $RG --name $APP --query "{State:state,URL:defaultHostName}" --output table

    Write-Host "`n[CONFIG] PAGEINDEX_API_KEY..."
    $kv = az webapp config appsettings list --resource-group $RG --name $APP `
        --query "[?name=='PAGEINDEX_API_KEY'].value" -o tsv 2>&1
    if ($kv) { Write-OK "PAGEINDEX_API_KEY is SET" }
    else { Write-WARN "PAGEINDEX_API_KEY is NOT set. Run: .\deploy.ps1 -SetKey pi_xxxx" }

    Write-Host "`n[FILES] Checking files on server..."
    try {
        $null = Invoke-RestMethod -Uri "$KUDU/api/vfs/site/wwwroot/kaanoon_test/system_adapters/pageindex_retriever.py" `
            -Headers $hdrs -Method Get -ErrorAction Stop
        Write-OK "pageindex_retriever.py present on server"
    } catch { Write-WARN "pageindex_retriever.py NOT found on server" }

    Write-Host "`n[PKG] Checking pageindex package..."
    $cb = @{ command = 'bash -c "find /tmp -maxdepth 3 -name antenv -type d; find /tmp -maxdepth 3 -path */site-packages/pageindex -type d; echo CHECK_DONE"'; dir = "/home/site/wwwroot" } | ConvertTo-Json -Compress
    $cr = Invoke-RestMethod -Uri "$KUDU/api/command" -Method Post -Headers $hdrs -Body $cb -ContentType "application/json"
    Write-Host $cr.Output
    exit 0
}

# ------------------------------------------------------------------
# SET API KEY
# ------------------------------------------------------------------
if ($SetKey) {
    Write-Host "`n[CONFIG] Setting PAGEINDEX_API_KEY..."
    az webapp config appsettings set --resource-group $RG --name $APP `
        --settings "PAGEINDEX_API_KEY=$SetKey" --output none
    if ($LASTEXITCODE -eq 0) {
        Write-OK "API key set successfully"
        if (-not $NoRestart) {
            Write-Host "`n[RESTART] Restarting app..."
            az webapp restart --resource-group $RG --name $APP
            Write-OK "Restarted. Waiting 45s for app startup..."
            Start-Sleep -Seconds 45
        }
    } else { Write-FAIL "Failed to set API key" }
    exit $LASTEXITCODE
}

# ------------------------------------------------------------------
# FULL DEPLOY: Upload files via Kudu VFS
# ------------------------------------------------------------------
Write-Host "`n[UPLOAD] Uploading files via Kudu VFS..."
$allOk = $true
foreach ($f in $FILES) {
    $name = Split-Path $f.L -Leaf
    if (-not (Test-Path $f.L)) { Write-WARN "Skipping $name (not found locally)"; continue }
    $size = (Get-Item $f.L).Length
    Write-Host ("`n  {0} ({1} bytes)" -f $name, $size)
    Write-Host "    -> $($f.R)"
    try {
        $bytes = [IO.File]::ReadAllBytes($f.L)
        $resp  = Invoke-WebRequest -Uri "$KUDU/api/vfs/site/wwwroot/$($f.R)" `
                    -Method Put -Headers $hdrs -Body $bytes `
                    -ContentType "application/octet-stream" -UseBasicParsing
        Write-OK "HTTP $($resp.StatusCode)"
    } catch {
        $sc = $_.Exception.Response.StatusCode.value__
        Write-FAIL "HTTP $sc - $($_.Exception.Message)"
        $allOk = $false
    }
}

if (-not $allOk) { Write-FAIL "One or more uploads failed"; exit 1 }

# ------------------------------------------------------------------
# Try installing pageindex (might not have antenv yet -- startup.sh handles it)
# ------------------------------------------------------------------
Write-Host "`n[INSTALL] Attempting pageindex install on server..."
$icmd = 'bash -c "ANTENV=$(find /tmp -maxdepth 3 -name antenv -type d | head -1); if [ -n \"$ANTENV\" ]; then \"$ANTENV/bin/pip\" install pageindex --quiet && echo PAGEINDEX_OK; else echo ANTENV_NOT_FOUND; fi"'
$ib   = @{ command = $icmd; dir = "/home/site/wwwroot" } | ConvertTo-Json -Compress
try {
    $ir = Invoke-RestMethod -Uri "$KUDU/api/command" -Method Post -Headers $hdrs -Body $ib -ContentType "application/json"
    if ($ir.Output -match "PAGEINDEX_OK") { Write-OK "pageindex installed on server" }
    elseif ($ir.Output -match "ANTENV_NOT_FOUND") { Write-WARN "antenv not ready yet -- startup.sh will install pageindex on next restart" }
    else { Write-WARN "Result: $($ir.Output.Trim())" }
} catch { Write-WARN "Install skipped: $($_.Exception.Message)" }

# ------------------------------------------------------------------
# Clear pycache
# ------------------------------------------------------------------
Write-Host "`n[CLEAN] Clearing __pycache__..."
$cb = @{ command = 'bash -c "find /home/site/wwwroot -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; echo DONE"'; dir = "/home/site/wwwroot" } | ConvertTo-Json -Compress
try {
    $cr = Invoke-RestMethod -Uri "$KUDU/api/command" -Method Post -Headers $hdrs -Body $cb -ContentType "application/json"
    Write-OK "pycache cleared: $($cr.Output.Trim())"
} catch { Write-WARN "Clear failed: $($_.Exception.Message)" }

# ------------------------------------------------------------------
# Restart
# ------------------------------------------------------------------
if (-not $NoRestart) {
    Write-Host "`n[RESTART] Restarting $APP..."
    az webapp restart --resource-group $RG --name $APP
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Restart triggered. Waiting 60s for startup.sh (pip install + file patches)..."
        Start-Sleep -Seconds 60
    } else { Write-FAIL "Restart failed" }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  DEPLOY COMPLETE" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Get your PageIndex API key: https://dash.pageindex.ai/api-keys"
Write-Host "  2. Set it:  .\deploy.ps1 -SetKey pi_xxxxxxxxxxxxx"
Write-Host "  3. Index statutes (run once): python kaanoon_test/pageindex_ingest.py"
Write-Host "  4. Verify: .\deploy.ps1 -CheckOnly"
Write-Host ""
