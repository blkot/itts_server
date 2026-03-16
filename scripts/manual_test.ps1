# scripts/manual_test.ps1
# PowerShell version of manual test script for Windows

$ErrorActionPreference = "Stop"
$ApiUrl = if ($env:API_URL) { $env:API_URL } else { "http://localhost:8000" }

Write-Host "=== ITTS Backend Manual Test Suite ===" -ForegroundColor Cyan

# Helper function for JSON pretty print
function Get-FormattedJson($object) {
    $object | ConvertTo-Json -Depth 10
}

# 1. Health check
Write-Host "`n[1] Health check..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$ApiUrl/health" -Method Get
    Get-FormattedJson $response
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 2. Upload bundle
Write-Host "`n[2] Uploading sample ITTS..." -ForegroundColor Yellow
try {
    $fixturePath = "tests/fixtures/spk_1772197182_1772197202988.itts"
    if (-not (Test-Path $fixturePath)) {
        Write-Host "Fixture file not found: $fixturePath" -ForegroundColor Red
        exit 1
    }

    $form = @{
        file = Get-Item -Path $fixturePath
    }
    $uploadResponse = Invoke-RestMethod -Uri "$ApiUrl/api/bundles" -Method Post -Form $form
    $bundleId = $uploadResponse.id
    Write-Host "Uploaded bundle ID: $bundleId" -ForegroundColor Green
    Get-FormattedJson $uploadResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 3. List bundles
Write-Host "`n[3] Listing all bundles..." -ForegroundColor Yellow
try {
    $listResponse = Invoke-RestMethod -Uri "$ApiUrl/api/bundles" -Method Get
    Get-FormattedJson $listResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 4. Get bundle
Write-Host "`n[4] Getting bundle $bundleId..." -ForegroundColor Yellow
try {
    $bundleResponse = Invoke-RestMethod -Uri "$ApiUrl/api/bundles/$bundleId" -Method Get
    Get-FormattedJson $bundleResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 5. Get segments
Write-Host "`n[5] Getting segments..." -ForegroundColor Yellow
try {
    $segmentsResponse = Invoke-RestMethod -Uri "$ApiUrl/api/bundles/$bundleId/segments" -Method Get
    Get-FormattedJson $segmentsResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 6. Search
Write-Host "`n[6] Searching for sample1..." -ForegroundColor Yellow
try {
    $searchResponse = Invoke-RestMethod -Uri "$ApiUrl/api/search?emotion=sample1" -Method Get
    Get-FormattedJson $searchResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 7. List playlists
Write-Host "`n[7] Listing playlists..." -ForegroundColor Yellow
try {
    $playlistsResponse = Invoke-RestMethod -Uri "$ApiUrl/api/playlists" -Method Get
    Get-FormattedJson $playlistsResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 8. Create export
Write-Host "`n[8] Creating export..." -ForegroundColor Yellow
try {
    $exportBody = @{
        bundle_id = $bundleId
        segment_indices = @(0)
        silence_ms = 100
    } | ConvertTo-Json

    $exportResponse = Invoke-RestMethod -Uri "$ApiUrl/api/export" -Method Post -Body $exportBody -ContentType "application/json"
    $jobId = $exportResponse.job_id
    Write-Host "Export job created: $jobId" -ForegroundColor Green
    Get-FormattedJson $exportResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 9. Poll for completion
Write-Host "`n[9] Waiting for export to complete..." -ForegroundColor Yellow
try {
    $maxAttempts = 10
    $attempt = 0
    $completed = $false

    while ($attempt -lt $maxAttempts -and -not $completed) {
        $jobResponse = Invoke-RestMethod -Uri "$ApiUrl/api/jobs/$jobId" -Method Get
        $status = $jobResponse.status

        if ($status -eq "completed") {
            Write-Host "Export completed" -ForegroundColor Green
            $completed = $true
        } elseif ($status -eq "failed") {
            Write-Host "Export failed: $($jobResponse.error_message)" -ForegroundColor Red
            exit 1
        } else {
            Write-Host "Status: $status (progress: $($jobResponse.progress))"
            Start-Sleep -Seconds 1
        }
        $attempt++
    }

    if (-not $completed) {
        Write-Host "Export timed out after $maxAttempts seconds" -ForegroundColor Red
        exit 1
    }

    Get-FormattedJson $jobResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

# 10. List backups
Write-Host "`n[10] Listing backups..." -ForegroundColor Yellow
try {
    $backupsResponse = Invoke-RestMethod -Uri "$ApiUrl/api/backups" -Method Get
    Get-FormattedJson $backupsResponse
} catch {
    Write-Host "Failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== All tests passed ===" -ForegroundColor Green
