param(
    [string]$Language = ""
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$LanguageFile = Join-Path $RootDir ".launcher_lang"
$AppUrl = "http://127.0.0.1:8501"
$UpdateGitHubUrl = if ($env:DOC_RAG_UPDATE_GITHUB_URL) { $env:DOC_RAG_UPDATE_GITHUB_URL } else { "https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/update/latest.json" }
$UpdateGiteeUrl = if ($env:DOC_RAG_UPDATE_GITEE_URL) { $env:DOC_RAG_UPDATE_GITEE_URL } else { "https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/update/latest.json" }
$Script:DocRagLang = ""

function Normalize-Language {
    param([string]$Value)
    $Value = "$Value".Trim()
    switch -Regex ($Value) {
        "^(en|EN|english|English)$" { return "en" }
        "^(zh_CN|zh-cn|zh|cn|CN|简体中文)$" { return "zh_CN" }
        "^(zh_TW|zh-tw|tw|TW|繁體中文|繁体中文)$" { return "zh_TW" }
        default { return "" }
    }
}

function Choose-Language {
    $candidate = Normalize-Language $Language
    if (-not $candidate -and $env:DOC_RAG_LANG) {
        $candidate = Normalize-Language $env:DOC_RAG_LANG
    }
    if (-not $candidate -and (Test-Path $LanguageFile)) {
        $candidate = Normalize-Language (Get-Content $LanguageFile -Raw)
    }
    if ($candidate) {
        $Script:DocRagLang = $candidate
        return
    }

    Write-Host "Select language / 选择语言 / 選擇語言:"
    Write-Host "1. English"
    Write-Host "2. 简体中文"
    Write-Host "3. 繁體中文"
    $choice = Read-Host "Please choose [1-3] / 请选择 [1-3]"
    switch ($choice) {
        "2" { $Script:DocRagLang = "zh_CN" }
        "3" { $Script:DocRagLang = "zh_TW" }
        default { $Script:DocRagLang = "en" }
    }
    Set-Content -Path $LanguageFile -Value $Script:DocRagLang -Encoding UTF8
}

function Msg {
    param([string]$En, [string]$ZhCn, [string]$ZhTw)
    switch ($Script:DocRagLang) {
        "en" { return $En }
        "zh_TW" { return $ZhTw }
        default { return $ZhCn }
    }
}

function Say {
    param([string]$En, [string]$ZhCn, [string]$ZhTw)
    Write-Host (Msg $En $ZhCn $ZhTw)
}

function Current-Version {
    $versionFile = Join-Path $RootDir "VERSION"
    if (Test-Path $versionFile) {
        return (Get-Content $versionFile -Raw).Trim()
    }
    return "0.0.0"
}

function Compare-VersionGreater {
    param([string]$Left, [string]$Right)
    $leftParts = [regex]::Matches($Left, "\d+") | ForEach-Object { [int]$_.Value }
    $rightParts = [regex]::Matches($Right, "\d+") | ForEach-Object { [int]$_.Value }
    $max = [Math]::Max($leftParts.Count, $rightParts.Count)
    for ($index = 0; $index -lt $max; $index++) {
        $l = if ($index -lt $leftParts.Count) { $leftParts[$index] } else { 0 }
        $r = if ($index -lt $rightParts.Count) { $rightParts[$index] } else { 0 }
        if ($l -gt $r) { return $true }
        if ($l -lt $r) { return $false }
    }
    return $false
}

function Download-LatestJson {
    foreach ($url in @($UpdateGitHubUrl, $UpdateGiteeUrl)) {
        if ([string]::IsNullOrWhiteSpace($url)) {
            continue
        }
        try {
            return Invoke-RestMethod -Uri $url -UseBasicParsing -TimeoutSec 8 -ErrorAction Stop
        } catch {
        }
    }
    return $null
}

function Check-Update {
    param([string]$Mode = "auto")
    $latest = Download-LatestJson
    if (-not $latest) {
        Say "Unable to check for updates. You can try manual check later." "无法检查更新，可稍后手动检查。" "無法檢查更新，可稍後手動檢查。"
        return
    }

    $localVersion = Current-Version
    $remoteVersion = "$($latest.version)"
    if (Compare-VersionGreater $remoteVersion $localVersion) {
        Write-Host ""
        Say "New version found." "发现新版本。" "發現新版本。"
        Write-Host "$(Msg 'Current version: ' '当前版本：' '目前版本：')$localVersion"
        Write-Host "$(Msg 'Latest version: ' '最新版本：' '最新版本：')$remoteVersion"
        Write-Host "$(Msg 'Release date: ' '更新日期：' '更新日期：')$($latest.date)"
        Write-Host "$(Msg 'Title: ' '更新标题：' '更新標題：')$($latest.title)"
        Write-Host (Msg "Notes:" "更新内容：" "更新內容：")
        foreach ($note in @($latest.notes)) {
            Write-Host "  - $note"
        }
        Say "Choose `"Update Source`" in the menu to update." "可在菜单中选择“更新源码”。" "可在選單中選擇「更新原始碼」。"
        Write-Host ""
    } elseif ($Mode -eq "manual") {
        Write-Host "$(Msg 'Already up to date: ' '当前已是最新版本：' '目前已是最新版本：')$localVersion"
    } else {
        Say "Already up to date." "当前已是最新版本。" "目前已是最新版本。"
    }
}

function Get-PythonInvocation {
    $candidates = @(
        @("py", "-3.13"),
        @("py", "-3.12"),
        @("py", "-3.11"),
        @("python"),
        @("python3")
    )
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
            continue
        }
        $prefix = @()
        if ($candidate.Count -gt 1) {
            $prefix = $candidate[1..($candidate.Count - 1)]
        }
        try {
            & $exe @prefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" *> $null
            if ($LASTEXITCODE -eq 0) {
                return $candidate
            }
        } catch {
        }
    }
    return $null
}

function Invoke-Python {
    param([string[]]$Invocation, [string[]]$Arguments)
    $exe = $Invocation[0]
    $prefix = @()
    if ($Invocation.Count -gt 1) {
        $prefix = $Invocation[1..($Invocation.Count - 1)]
    }
    & $exe @prefix @Arguments
}

function Install-Dependencies {
    Set-Location $RootDir
    $python = Get-PythonInvocation
    if (-not $python) {
        Say "Python 3.11 or newer was not found. Please install Python first." "未找到 Python 3.11 或更高版本，请先安装 Python。" "未找到 Python 3.11 或更高版本，請先安裝 Python。"
        return
    }
    if (-not (Test-Path (Join-Path $RootDir ".venv"))) {
        Say "Creating virtual environment..." "正在创建虚拟环境..." "正在建立虛擬環境..."
        Invoke-Python -Invocation $python -Arguments @("-m", "venv", ".venv")
    }
    $venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Say "Virtual environment was not found." "未找到虚拟环境。" "未找到虛擬環境。"
        return
    }
    Say "Upgrading pip..." "正在升级 pip..." "正在升級 pip..."
    & $venvPython -m pip install --upgrade pip
    Say "Installing project dependencies. This can take a while..." "正在安装项目依赖，这一步可能需要较长时间..." "正在安裝專案依賴，這一步可能需要較長時間..."
    & $venvPython -m pip install -r requirements.txt
}

function Update-Source {
    Set-Location $RootDir
    if (-not (Test-Path (Join-Path $RootDir ".git"))) {
        Say "This does not look like a Git checkout. Download the latest ZIP or rerun bootstrap." "当前目录不是 Git 仓库。请下载最新版 ZIP，或重新运行 bootstrap 安装命令。" "目前目錄不是 Git 倉庫。請下載最新版 ZIP，或重新執行 bootstrap 安裝命令。"
        return
    }
    git pull --ff-only
    if (Test-Path (Join-Path $RootDir ".venv\Scripts\python.exe")) {
        Install-Dependencies
    }
    Say "Update completed. Restart the app if it is running." "更新完成。如程序正在运行，请重启。" "更新完成。如程式正在執行，請重新啟動。"
}

function Start-App {
    Set-Location $RootDir
    $streamlit = Join-Path $RootDir ".venv\Scripts\streamlit.exe"
    if (-not (Test-Path $streamlit)) {
        Say "Virtual environment or Streamlit was not found. Choose `"Install / Repair Dependencies`" first." "未找到虚拟环境或 Streamlit，请先选择“安装/修复依赖”。" "未找到虛擬環境或 Streamlit，請先選擇「安裝/修復依賴」。"
        return
    }
    Start-Job -ArgumentList $AppUrl -ScriptBlock {
        param([string]$Url)
        for ($i = 0; $i -lt 45; $i++) {
            try {
                Invoke-WebRequest -Uri "$Url/_stcore/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop | Out-Null
                Start-Sleep -Seconds 3
                Start-Process $Url
                return
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        Write-Host "Streamlit is still loading. Open manually later: $Url"
    } | Out-Null
    & $streamlit run app.py --server.address 127.0.0.1 --server.port 8501
}

function Safe-Clean {
    Set-Location $RootDir
    foreach ($path in @(".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "logs", "tmp", "temp")) {
        $fullPath = Join-Path $RootDir $path
        if (Test-Path $fullPath) {
            Remove-Item $fullPath -Recurse -Force
        }
    }
    Get-ChildItem -Path $RootDir -Recurse -Force -Include "__pycache__", "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Say "Safe cleanup completed." "安全清理完成。" "安全清理完成。"
}

function Cleanup-Menu {
    Write-Host ""
    Write-Host "1. $(Msg 'Safe cleanup' '安全清理' '安全清理')"
    Write-Host "2. $(Msg 'Return' '返回' '返回')"
    $choice = Read-Host (Msg "Choose [1-2]" "请选择 [1-2]" "請選擇 [1-2]")
    if ($choice -eq "1") {
        Safe-Clean
    }
}

function Show-Version {
    Write-Host "$(Msg 'Current version: ' '当前版本：' '目前版本：')$(Current-Version)"
    Write-Host "$(Msg 'Project directory: ' '项目目录：' '專案目錄：')$RootDir"
}

function Main-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "==== $(Msg 'DocRAG Launcher' 'DocRAG 启动器' 'DocRAG 啟動器') ===="
        Write-Host "1. $(Msg 'Start App' '启动程序' '啟動程式')"
        Write-Host "2. $(Msg 'Check Updates' '检查更新' '檢查更新')"
        Write-Host "3. $(Msg 'Update Source' '更新源码' '更新原始碼')"
        Write-Host "4. $(Msg 'Install / Repair Dependencies' '安装/修复依赖' '安裝/修復依賴')"
        Write-Host "5. $(Msg 'Show Current Version' '查看当前版本' '查看目前版本')"
        Write-Host "6. $(Msg 'Uninstall / Clean' '卸载/清理' '卸載/清理')"
        Write-Host "7. $(Msg 'Exit' '退出' '退出')"
        $choice = Read-Host (Msg "Choose [1-7]" "请选择 [1-7]" "請選擇 [1-7]")
        switch ($choice) {
            "1" { Start-App }
            "2" { Check-Update "manual" }
            "3" { Update-Source }
            "4" { Install-Dependencies }
            "5" { Show-Version }
            "6" { Cleanup-Menu }
            "7" { return }
            default { Say "Invalid choice." "无效选择。" "無效選擇。" }
        }
    }
}

Choose-Language
Set-Location $RootDir
Check-Update "auto"
Main-Menu
