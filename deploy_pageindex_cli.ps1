#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy PageIndex integration to Azure App Service using az CLI.

.DESCRIPTION
    Uploads changed Python files and config to Azure using az webapp deploy,
    installs the pageindex package on the server, restarts the app.

.PARAMETER SetKey
    Set PAGEINDEX_API_KEY in Azure App Service Application Settings.
    Example: .\deploy_pageindex_cli.ps1 -SetKey pi_xxxxxxxxxxxxx

.PARAMETER CheckOnly
    Only check deployment status — no uploads.

.PARAMETER NoRestart
    Skip app restart after deploy.

.EXAMPLE
    .\deploy_pageindex_cli.ps1
    .\deploy_pageindex_cli.ps1 -SetKey pi_xxxxxxxxxxxxx
    .\deploy_pageindex_cli.ps1 -CheckOnly
#>
param(
    [string]$SetKey    = "",
    [switch]$CheckOnly = $false,
    [switch]$NoRestart = $false
)

# ── Config ────────────────────────────────────────────────────────────────────
$RG   = "lawgpt-rg"
$APP  = "lawgpt-backend2024"
$BASE = "C:\Users\LOQ\Downloads\LAW-GPT_new\LAW-GPT_new\LAW-GPT"

$FILES = @(
    @{ Local = "$BASE\kaanoon_test\system_adapters\pageindex_retriever.py";  Remote = "kaanoon_test/system_adapters/pageindex_retriever.py" },
    @{ Local = "$BASE\kaanoon_test\system_adapters\agentic_rag_engine.py";   Remote = "kaanoon_test/system_adapters/agentic_rag_engine.py"  },
    @{ Local = "$BASE\kaanoon_test\system_adapters\unified_advanced_rag.py"; Remote = "kaanoon_test/system_adapters/unified_advanced_rag.py" },
    @{ Local = "$BASE\requirements.txt"; Remote = "requirements.txt" },
    @{ Local = "$BASE\startup.sh";       Remote = "startup.sh" }
)

# ── Colours ───────────────────────────────────────────────────────────────────
function Write-OK    { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green  }
function Write-FAIL  { param($msg) Write-Host "  [!!]  $msg" -ForegroundColor Red    }
function Write-INFO  { param($msg) Write-Host "  [..]  $msg" -ForegroundColor Cyan   }
function Write-WARN  { param($msg) Write-Host "  [??]  $msg" -ForegroundColor Yellow }

Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  LAW-GPT PageIndex Deploy — Azure CLI" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan

# ── Login check ───────────────────────────────────────────────────────────────
Write-Host "`n[AUTH] Checking Azure login..."
$account = az account show --query "name" -o tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-FAIL "Not logged in. Run:  az login"
    exit 1
}
Write-OK "Logged in as: $account"

# ── Check-only mode ───────────────────────────────────────────────────────────
if ($CheckOnly) {
    Write-Host "`n[STATUS] App: $APP (RG: $RG)"
    az webapp show --resource-group $RG --name $APP `
        --query "{State:state, URL:defaultHostName}" --output table

    Write-Host "`n[CONFIG] Checking PAGEINDEX_API_KEY..."
    $kv = az webapp config appsettings list --resource-group $RG --name $APP `
        --query "[?name=='PAGEINDEX_API_KEY'].value" -o tsv 2>&1
    if ($kv) {
        Write-OK "PAGEINDEX_API_KEY is SET (value starts with: $($kv.Substring(0, [Math]::Min(8,$kv.Length)))...)"
    } else {
        Write-WARN "PAGEINDEX_API_KEY is NOT set"
        Write-Host "     Set it: .\deploy_pageindex_cli.ps1 -SetKey pi_xxxxx" -ForegroundColor Yellow
    }

    Write-Host "`n[SERVER] Checking pageindex_retriever.py on server..."
    $checkBody = '{"command":"ls -la /home/site/wwwroot/kaanoon_test/system_adapters/pageindex_retriever.py 2>/dev/null && echo FILE_OK || echo FILE_MISSING","dir":"/home/site/wwwroot"}'
    $result = az rest --method POST `
        --url "https://$APP.scm.azurewebsites.net/api/command" `
        --body $checkBody `
        --headers "Content-Type=application/json" `
        --query "Output" -o tsv 2>&1
    if ($result -match "FILE_OK") { Write-OK "pageindex_retriever.py found on server" }
    else { Write-WARN "pageindex_retriever.py NOT found on server ($result)" }

    Write-Host "`n[SERVER] Checking if pageindex package is installed..."
    $pipBody = '{"command":"ANTENV=$(find /tmp -maxdepth 2 -name antenv -type d 2>/dev/null | head -1); [ -n \"$ANTENV\" ] && \"$ANTENV/bin/python\" -c \"import pageindex; print(getattr(pageindex,chr(95)*2+chr(118)+chr(101)+chr(114)+chr(115)+chr(105)+chr(111)+chr(110)+chr(95)*2,chr(63)))\" 2>&1 || echo NOT_INSTALLED","dir":"/home/site/wwwroot"}'
    $pipResult = az rest --method POST `
        --url "https://$APP.scm.azurewebsites.net/api/command" `
        --body $pipBody `
        --headers "Content-Type=application/json" `
        --query "Output" -o tsv 2>&1
    if ($pipResult -match "NOT_INSTALLED" -or $pipResult -match "No module") {
        Write-WARN "pageindex package not yet installed (will auto-install on next restart via startup.sh)"
    } else {
        Write-OK "pageindex installed: $($pipResult.Trim())"
    }
    exit 0
}

# ── Set API key mode ──────────────────────────────────────────────────────────
if ($SetKey) {
    Write-Host "`n[CONFIG] Setting PAGEINDEX_API_KEY..."
    az webapp config appsettings set `
        --resource-group $RG `
        --name $APP `
        --settings "PAGEINDEX_API_KEY=$SetKey" `
        --output none
    if ($LASTEXITCODE -eq 0) {
        Write-OK "PAGEINDEX_API_KEY set successfully"
        if (-not $NoRestart) {
            Write-Host "`n[RESTART] Restarting app to apply new key..."
            az webapp restart --resource-group $RG --name $APP
            Write-OK "Restarted. Waiting 45s for startup..."
            Start-Sleep -Seconds 45
        }
    } else {
        Write-FAIL "Failed to set PAGEINDEX_API_KEY"
    }
    exit $LASTEXITCODE
}

# ── Full deploy ───────────────────────────────────────────────────────────────
Write-Host "`n[UPLOAD] Deploying files to $APP..."
$allOk = $true

foreach ($f in $FILES) {
    $name = Split-Path $f.Local -Leaf
    if (-not (Test-Path $f.Local)) {
        Write-WARN "Skipping $name — not found locally"
        continue
    }
    $size = (Get-Item $f.Local).Length
    Write-Host ("`n  {0}  {1} bytes  ->  {2}" -f $name, $size, $f.Remote)
    az webapp deploy `
        --resource-group $RG `
        --name $APP `
        --src-path $f.Local `
        --target-path $f.Remote `
        --type static `
        --async true `
        --restart false `
        --output none
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Queued"
    } else {
        Write-FAIL "Upload failed for $name"
        $allOk = $false
    }
}

if (-not $allOk) {
    Write-FAIL "One or more uploads failed. Check az login and resource group."
    exit 1
}

Write-INFO "Waiting 20s for async uploads to settle..."
Start-Sleep -Seconds 20

# ── Install pageindex on server ───────────────────────────────────────────────
Write-Host "`n[INSTALL] Installing pageindex package on server..."
$installCmd = 'ANTENV=$(find /tmp -maxdepth 2 -name antenv -type d 2>/dev/null | head -1); if [ -n "$ANTENV" ]; then "$ANTENV/bin/pip" install pageindex --quiet && echo PAGEINDEX_OK; else echo ANTENV_NOT_FOUND; fi'
$installBody = $installCmd | ConvertTo-Json -Compress
# Wrap in proper JSON object
$installBodyJson = "{""command"":$installBody,""dir"":""/home/site/wwwroot""}"
$installResult = az rest --method POST `
    --url "https://$APP.scm.azurewebsites.net/api/command" `
    --body $installBodyJson `
    --headers "Content-Type=application/json" `
    --query "Output" -o tsv 2>&1
if ($installResult -match "PAGEINDEX_OK") {
    Write-OK "pageindex installed on server"
} elseif ($installResult -match "ANTENV_NOT_FOUND") {
    Write-WARN "antenv not ready yet — startup.sh will install pageindex on next restart"
} else {
    Write-WARN "Install result: $($installResult.Trim())"
    Write-INFO "startup.sh will auto-install pageindex on next app restart"
}

# ── Clear pycache ─────────────────────────────────────────────────────────────
Write-Host "`n[CLEAN] Clearing __pycache__ on server..."
$cleanBody = '{"command":"find /home/site/wwwroot -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; find /tmp -path \"*/kaanoon_test*/__pycache__\" -exec rm -rf {} + 2>/dev/null; echo CACHE_CLEARED","dir":"/home/site/wwwroot"}'
$cleanResult = az rest --method POST `
    --url "https://$APP.scm.azurewebsites.net/api/command" `
    --body $cleanBody `
    --headers "Content-Type=application/json" `
    --query "Output" -o tsv 2>&1
if ($cleanResult -match "CACHE_CLEARED") { Write-OK "pycache cleared" }
else { Write-WARN "Cache clear: $cleanResult" }

# ── Restart ───────────────────────────────────────────────────────────────────
if (-not $NoRestart) {
    Write-Host "`n[RESTART] Restarting $APP..."
    az webapp restart --resource-group $RG --name $APP
    if ($LASTEXITCODE -eq 0) {
        Write-OK "Restarted. Waiting 50s for startup.sh to run (pip install + file patches)..."
        Start-Sleep -Seconds 50
    } else {
        Write-FAIL "Restart failed"
    }
} else {
    Write-INFO "Restart skipped (--NoRestart)"
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  DEPLOY COMPLETE" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Set your PageIndex API key (if not done yet):"
Write-Host "     .\deploy_pageindex_cli.ps1 -SetKey pi_xxxxxxxxxxxxx"
Write-Host "     (Get key at: https://dash.pageindex.ai/api-keys)"
Write-Host ""
Write-Host "  2. Index statute files (run once locally):"
Write-Host "     `$env:PAGEINDEX_API_KEY = 'pi_xxxx'"
Write-Host "     python kaanoon_test/pageindex_ingest.py"
Write-Host ""
Write-Host "  3. Check status anytime:"
Write-Host "     .\deploy_pageindex_cli.ps1 -CheckOnly"
Write-Host ""
