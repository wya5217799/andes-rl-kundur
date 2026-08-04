param(
    [Parameter(Mandatory = $true)]
    [int]$TrainingProcessId
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$wslRoot = '/mnt/e/Projects/andes-rl-kundur'
$pipelineRoot = Join-Path $repoRoot 'results/r293_pipeline'
$logRoot = Join-Path $pipelineRoot 'logs'
$statusRoot = Join-Path $pipelineRoot 'status'
New-Item -ItemType Directory -Force -Path $logRoot, $statusRoot | Out-Null

$completeMarker = Join-Path $statusRoot 'complete'
$failedMarker = Join-Path $statusRoot 'failed'
if ((Test-Path $completeMarker) -or (Test-Path $failedMarker)) {
    throw 'R293 post-training pipeline already has a terminal marker'
}

function Invoke-WslStage {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$LogName
    )
    $logPath = Join-Path $logRoot $LogName
    & wsl.exe @Arguments *> $logPath
    if ($LASTEXITCODE -ne 0) {
        throw "WSL stage failed with exit code $LASTEXITCODE; see $logPath"
    }
}

try {
    Wait-Process -Id $TrainingProcessId -ErrorAction SilentlyContinue
    $trainingStatus = Join-Path $repoRoot 'results/r293_prior_residual_training/status'
    if (Test-Path (Join-Path $trainingStatus 'failed')) {
        throw 'R293 training failed; downstream stages remain blocked'
    }
    if (-not (Test-Path (Join-Path $trainingStatus 'complete'))) {
        throw 'R293 training process exited without a complete marker'
    }

    Invoke-WslStage -Arguments @(
        '--cd', $wslRoot,
        '/home/wya/andes_venv/bin/python',
        'scripts/andes_scratch.py',
        'scripts/run_r293_fresh_bank.py',
        'prepare'
    ) -LogName 'fresh_prepare.log'
    Invoke-WslStage -Arguments @(
        '--cd', $wslRoot,
        'bash', 'scripts/run_r293_fresh_bank_unattended.sh'
    ) -LogName 'fresh_run.log'
    if (-not (Test-Path (Join-Path $repoRoot 'results/r293_fresh_bank/status/complete'))) {
        throw 'R293 fresh-bank screen exited without a complete marker'
    }

    Invoke-WslStage -Arguments @(
        '--cd', $wslRoot,
        '/home/wya/andes_venv/bin/python',
        'scripts/andes_scratch.py',
        'scripts/run_r293_formal.py',
        'prepare'
    ) -LogName 'formal_prepare.log'
    Invoke-WslStage -Arguments @(
        '--cd', $wslRoot,
        'bash', 'scripts/run_r293_formal_unattended.sh'
    ) -LogName 'formal_run.log'
    if (-not (Test-Path (Join-Path $repoRoot 'results/r293_formal_evaluation/status/complete'))) {
        throw 'R293 formal evaluation exited without a complete marker'
    }
    New-Item -ItemType File -Force -Path $completeMarker | Out-Null
}
catch {
    $_ | Out-String | Set-Content -Path $failedMarker -Encoding utf8
    throw
}
