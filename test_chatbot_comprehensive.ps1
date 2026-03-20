# Comprehensive Chatbot Test Suite
# Testing all aspects of the LAW-GPT system

Write-Host "`n================================================================================`n" -ForegroundColor Cyan
Write-Host "🚀 COMPREHENSIVE CHATBOT TEST SUITE" -ForegroundColor Green
Write-Host "`n================================================================================`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:5000"
$testResults = @()
$totalTests = 0
$passedTests = 0
$failedTests = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [object]$Body = $null,
        [int]$Timeout = 60,
        [scriptblock]$Validator = $null
    )
    
    $global:totalTests++
    Write-Host "[TEST $global:totalTests] $Name..." -ForegroundColor Yellow -NoNewline
    
    try {
        $params = @{
            Uri = "$baseUrl$Endpoint"
            Method = $Method
            TimeoutSec = $Timeout
            UseBasicParsing = $true
        }
        
        if ($Body) {
            $params.Body = ($Body | ConvertTo-Json -Depth 10)
            $params.ContentType = "application/json"
        }
        
        $startTime = Get-Date
        $response = Invoke-WebRequest @params
        $elapsed = ((Get-Date) - $startTime).TotalSeconds
        
        if ($response.StatusCode -eq 200) {
            $json = $response.Content | ConvertFrom-Json
            
            if ($Validator) {
                $validationResult = & $Validator $json $elapsed
                if ($validationResult -eq $true) {
                    $global:passedTests++
                    Write-Host " ✅ PASSED ($($elapsed.ToString('F2'))s)" -ForegroundColor Green
                    return @{ Success = $true; Data = $json; Latency = $elapsed }
                } else {
                    $global:failedTests++
                    Write-Host " ❌ FAILED - $validationResult" -ForegroundColor Red
                    return @{ Success = $false; Error = $validationResult; Latency = $elapsed }
                }
            } else {
                $global:passedTests++
                Write-Host " ✅ PASSED ($($elapsed.ToString('F2'))s)" -ForegroundColor Green
                return @{ Success = $true; Data = $json; Latency = $elapsed }
            }
        } else {
            $global:failedTests++
            Write-Host " ❌ FAILED - Status Code: $($response.StatusCode)" -ForegroundColor Red
            return @{ Success = $false; Error = "Status Code: $($response.StatusCode)"; Latency = $elapsed }
        }
    } catch {
        $global:failedTests++
        Write-Host " ❌ FAILED - $($_.Exception.Message)" -ForegroundColor Red
        return @{ Success = $false; Error = $_.Exception.Message; Latency = 0 }
    }
}

# ============================================================================
# PHASE 1: API ENDPOINT TESTS
# ============================================================================
Write-Host "`n📡 PHASE 1: API ENDPOINT TESTS`n" -ForegroundColor Magenta

# Test 1: Health Check (Root endpoint)
$test1 = Test-Endpoint -Name "Root Endpoint Health Check" -Method "GET" -Endpoint "/" -Timeout 5

# Test 2: Stats Endpoint
$test2 = Test-Endpoint -Name "Stats Endpoint" -Method "GET" -Endpoint "/api/stats" -Timeout 5

# Test 3: Examples Endpoint
$test3 = Test-Endpoint -Name "Examples Endpoint" -Method "GET" -Endpoint "/api/examples" -Timeout 5

# ============================================================================
# PHASE 2: FAST LOOKUP TESTS (IPC Sections)
# ============================================================================
Write-Host "`n⚡ PHASE 2: FAST LOOKUP TESTS (IPC Sections)`n" -ForegroundColor Magenta

$ipcSections = @("302", "304", "498A", "379", "406")
foreach ($section in $ipcSections) {
    $test = Test-Endpoint `
        -Name "IPC Section $section Fast Lookup" `
        -Method "POST" `
        -Endpoint "/api/query" `
        -Body @{ question = "What is IPC Section $section?"; category = "general" } `
        -Timeout 5 `
        -Validator {
            param($json, $elapsed)
            if ($elapsed -lt 1.0) {
                if ($json.response -and $json.response.answer -and $json.response.answer.Length -gt 100) {
                    return $true
                }
                return "Response missing or too short"
            }
            return "Too slow: $($elapsed.ToString('F2'))s (expected <1s)"
        }
    $testResults += @{ Test = "IPC Section $section"; Result = $test }
}

# ============================================================================
# PHASE 3: SIMPLE QUERY TESTS
# ============================================================================
Write-Host "`n📝 PHASE 3: SIMPLE QUERY TESTS`n" -ForegroundColor Magenta

$simpleQueries = @(
    "What is FIR?",
    "What is divorce?",
    "What is property?",
    "What is IPC?",
    "What is CrPC?"
)

foreach ($query in $simpleQueries) {
    $test = Test-Endpoint `
        -Name "Simple Query: $($query.Substring(0, [Math]::Min(30, $query.Length)))" `
        -Method "POST" `
        -Endpoint "/api/query" `
        -Body @{ question = $query; category = "general" } `
        -Timeout 30 `
        -Validator {
            param($json, $elapsed)
            if ($elapsed -lt 15.0) {
                if ($json.response -and $json.response.answer -and $json.response.answer.Length -gt 200) {
                    return $true
                }
                return "Response missing or too short"
            }
            return "Too slow: $($elapsed.ToString('F2'))s (expected <15s)"
        }
    $testResults += @{ Test = $query; Result = $test }
}

# ============================================================================
# PHASE 4: COMPLEX QUERY TESTS
# ============================================================================
Write-Host "`n🔍 PHASE 4: COMPLEX QUERY TESTS`n" -ForegroundColor Magenta

$complexQueries = @(
    @{
        Question = "Property ownership rights in India"
        ExpectedTime = 15
    },
    @{
        Question = "How to file a consumer complaint?"
        ExpectedTime = 30
    },
    @{
        Question = "What are the procedures for filing a divorce case under Hindu law?"
        ExpectedTime = 30
    }
)

foreach ($queryObj in $complexQueries) {
    $test = Test-Endpoint `
        -Name "Complex Query: $($queryObj.Question.Substring(0, [Math]::Min(40, $queryObj.Question.Length)))" `
        -Method "POST" `
        -Endpoint "/api/query" `
        -Body @{ question = $queryObj.Question; category = "general" } `
        -Timeout 60 `
        -Validator {
            param($json, $elapsed)
            if ($elapsed -lt $queryObj.ExpectedTime) {
                if ($json.response -and $json.response.answer -and $json.response.answer.Length -gt 300) {
                    return $true
                }
                return "Response missing or too short"
            }
            return "Too slow: $($elapsed.ToString('F2'))s (expected <$($queryObj.ExpectedTime)s)"
        }
    $testResults += @{ Test = $queryObj.Question; Result = $test }
}

# ============================================================================
# PHASE 5: MULTI-PART QUESTION TESTS
# ============================================================================
Write-Host "`n📋 PHASE 5: MULTI-PART QUESTION TESTS`n" -ForegroundColor Magenta

$multiPartQuery = "Questions on CPC Procedures:`n`nQ1: In a Civil Suit, after the plaintiff provides the evidence, what occurs as the next stage in the process, 'cross-examination of the plaintiff' or the 'cross-examination of defendant', which comes first?`n`nQ2: I am appearing party-in-person (as plaintiff) for a case before a quasi-judicial body. The chairperson insists on recording the evidences in Tamil eventhough I asked it to be taken in English. I would like to know what is the current scenario in lower courts and quasi-judicial bodies in Tamil Nadu state with regards to the language to be used in recording evidence in the proceedings?"

$test = Test-Endpoint `
    -Name "Multi-Part Question: CPC Procedures" `
    -Method "POST" `
    -Endpoint "/api/query" `
    -Body @{ question = $multiPartQuery; category = "general" } `
    -Timeout 60 `
    -Validator {
        param($json, $elapsed)
        if ($elapsed -lt 30.0) {
            if ($json.response -and $json.response.answer) {
                $answer = $json.response.answer
                # Check if answer addresses both Q1 and Q2
                $hasQ1 = $answer -match "cross-examination" -or $answer -match "plaintiff" -or $answer -match "defendant"
                $hasQ2 = $answer -match "Tamil" -or $answer -match "English" -or $answer -match "language" -or $answer -match "Order 18"
                if ($hasQ1 -and $hasQ2 -and $answer.Length -gt 500) {
                    return $true
                }
                return "Answer doesn't address both sub-questions or too short"
            }
            return "Response missing"
        }
        return "Too slow: $($elapsed.ToString('F2'))s (expected <30s)"
    }
$testResults += @{ Test = "Multi-Part CPC Question"; Result = $test }

# ============================================================================
# PHASE 6: ERROR HANDLING TESTS
# ============================================================================
Write-Host "`n⚠️ PHASE 6: ERROR HANDLING TESTS`n" -ForegroundColor Magenta

# Test empty query
$test = Test-Endpoint `
    -Name "Empty Query Handling" `
    -Method "POST" `
    -Endpoint "/api/query" `
    -Body @{ question = ""; category = "general" } `
    -Timeout 10 `
    -Validator {
        param($json, $elapsed)
        # Should either return error or handle gracefully
        return $true  # Accept any response as valid error handling
    }
$testResults += @{ Test = "Empty Query"; Result = $test }

# Test very long query
$longQuery = "What is " + ("law " * 100)
$test = Test-Endpoint `
    -Name "Very Long Query Handling" `
    -Method "POST" `
    -Endpoint "/api/query" `
    -Body @{ question = $longQuery; category = "general" } `
    -Timeout 60 `
    -Validator {
        param($json, $elapsed)
        # Should handle long queries without crashing
        return $true
    }
$testResults += @{ Test = "Very Long Query"; Result = $test }

# ============================================================================
# PHASE 7: PERFORMANCE METRICS
# ============================================================================
Write-Host "`n📊 PHASE 7: PERFORMANCE METRICS`n" -ForegroundColor Magenta

$fastLookups = $testResults | Where-Object { $_.Test -like "IPC Section*" -and $_.Result.Success -eq $true }
$simpleQueries = $testResults | Where-Object { $_.Test -in $simpleQueries -and $_.Result.Success -eq $true }
$complexQueries = $testResults | Where-Object { $_.Test -like "Complex Query*" -and $_.Result.Success -eq $true }

if ($fastLookups) {
    $avgFastLookup = ($fastLookups | ForEach-Object { $_.Result.Latency } | Measure-Object -Average).Average
    Write-Host "⚡ Fast Lookups Average: $($avgFastLookup.ToString('F3'))s" -ForegroundColor Cyan
}

if ($simpleQueries) {
    $avgSimple = ($simpleQueries | ForEach-Object { $_.Result.Latency } | Measure-Object -Average).Average
    Write-Host "📝 Simple Queries Average: $($avgSimple.ToString('F2'))s" -ForegroundColor Cyan
}

if ($complexQueries) {
    $avgComplex = ($complexQueries | ForEach-Object { $_.Result.Latency } | Measure-Object -Average).Average
    Write-Host "🔍 Complex Queries Average: $($avgComplex.ToString('F2'))s" -ForegroundColor Cyan
}

# ============================================================================
# FINAL SUMMARY
# ============================================================================
Write-Host "`n================================================================================`n" -ForegroundColor Cyan
Write-Host "📊 TEST SUMMARY`n" -ForegroundColor Green
Write-Host "================================================================================`n" -ForegroundColor Cyan

Write-Host "Total Tests: $global:totalTests" -ForegroundColor White
Write-Host "✅ Passed: $global:passedTests" -ForegroundColor Green
Write-Host "❌ Failed: $global:failedTests" -ForegroundColor Red
Write-Host "Success Rate: $([Math]::Round(($global:passedTests / $global:totalTests) * 100, 2))%`n" -ForegroundColor Yellow

if ($global:failedTests -eq 0) {
    Write-Host "🎉 ALL TESTS PASSED! 🎉`n" -ForegroundColor Green
} else {
    Write-Host "⚠️ Some tests failed. Review the results above.`n" -ForegroundColor Yellow
}

Write-Host "================================================================================`n" -ForegroundColor Cyan

