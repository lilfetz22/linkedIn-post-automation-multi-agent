# run_tests.ps1 - Test execution and coverage reporting script for Windows PowerShell
# 
# This script provides convenient shortcuts for running tests with various options.
# It should be run from the project root directory.
#
# Usage:
#   .\run_tests.ps1                    # Run all tests
#   .\run_tests.ps1 -Coverage          # Run with coverage report
#   .\run_tests.ps1 -CoverageHtml      # Generate HTML coverage report
#   .\run_tests.ps1 -Unit              # Run only unit tests
#   .\run_tests.ps1 -Integration       # Run only integration tests
#   .\run_tests.ps1 -Verbose           # Run with verbose output
#   .\run_tests.ps1 -File <path>       # Run specific test file

param(
    [switch]$Coverage,
    [switch]$CoverageHtml,
    [switch]$Unit,
    [switch]$Integration,
    [switch]$Persona,
    [switch]$Verbose,
    [switch]$Help,
    [string]$File = ""
)

# Display help
if ($Help) {
    Write-Host @"
LinkedIn Post Automation - Test Runner Script

Usage:
    .\run_tests.ps1 [options]

Options:
    -Coverage       Run tests with coverage and show missing lines
    -CoverageHtml   Generate HTML coverage report in htmlcov/
    -Unit           Run only unit tests (marker: unit)
    -Integration    Run only integration tests (marker: integration)
    -Persona        Run only persona compliance tests (marker: persona)
    -Verbose        Enable verbose output
    -File <path>    Run a specific test file
    -Help           Show this help message

Examples:
    .\run_tests.ps1                         # Run all tests
    .\run_tests.ps1 -Coverage               # Run with coverage
    .\run_tests.ps1 -CoverageHtml           # Generate HTML report
    .\run_tests.ps1 -Unit -Verbose          # Run unit tests with verbose output
    .\run_tests.ps1 -File tests/test_error_handling.py

"@
    exit 0
}

# Set execution policy for this session (required for venv activation)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# Build pytest command
$pytestArgs = @("tests/")

# Add file if specified
if ($File -ne "") {
    $pytestArgs = @($File)
}

# Add verbose flag
if ($Verbose) {
    $pytestArgs += "-v"
}

# Add marker filters
if ($Unit) {
    $pytestArgs += "-m"
    $pytestArgs += "unit"
}
if ($Integration) {
    $pytestArgs += "-m"
    $pytestArgs += "integration"
}
if ($Persona) {
    $pytestArgs += "-m"
    $pytestArgs += "persona"
}

# Add coverage options
if ($Coverage -or $CoverageHtml) {
    $pytestArgs += "--cov=agents"
    $pytestArgs += "--cov=core"
    $pytestArgs += "--cov=database"
    $pytestArgs += "--cov-report=term-missing"
    
    if ($CoverageHtml) {
        $pytestArgs += "--cov-report=html"
        $pytestArgs += "--cov-report=xml"
    }
}

# Display what we're running
Write-Host "Running: pytest $($pytestArgs -join ' ')" -ForegroundColor Cyan
Write-Host ""

# Run pytest
& python -m pytest $pytestArgs

# Store exit code
$exitCode = $LASTEXITCODE

# Show coverage report location if HTML was generated
if ($CoverageHtml -and $exitCode -eq 0) {
    Write-Host ""
    Write-Host "HTML coverage report generated at: htmlcov/index.html" -ForegroundColor Green
    Write-Host "Open in browser: start htmlcov\index.html" -ForegroundColor Yellow
}

exit $exitCode
