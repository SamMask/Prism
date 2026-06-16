$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory=$true)]
        [string] $Name,
        [Parameter(Mandatory=$true)]
        [scriptblock] $Command
    )

    Write-Output "Loop gate: $Name"
    & $Command
    $code = $LASTEXITCODE
    if ($null -eq $code) {
        $code = 0
    }
    if ($code -ne 0) {
        Write-Error "Loop gate failed at '$Name' (exit $code)."
        exit $code
    }
}

Invoke-Step "git diff --check" {
    git diff --check
}

Invoke-Step "CLAUDE.md / AGENTS.md mirror check" {
    git diff --no-index --exit-code CLAUDE.md AGENTS.md
}

Invoke-Step "pytest tests/ -v" {
    pytest tests/ -v
}

Push-Location "go-shadow"
try {
    Invoke-Step "go test ./..." {
        go test ./...
    }
}
finally {
    Pop-Location
}

Write-Output "Loop gate: passed."
