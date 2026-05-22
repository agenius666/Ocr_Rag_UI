param(
    [string]$InstallDir = "",
    [string]$Language = ""
)

$ErrorActionPreference = "Stop"

$GitHubRepoUrl = $env:DOC_RAG_GITHUB_REPO_URL
if ([string]::IsNullOrWhiteSpace($GitHubRepoUrl)) {
    $GitHubRepoUrl = "https://github.com/agenius666/Ocr_Rag_UI.git"
}

$GiteeRepoUrl = $env:DOC_RAG_GITEE_REPO_URL
if ([string]::IsNullOrWhiteSpace($GiteeRepoUrl)) {
    $GiteeRepoUrl = "https://gitee.com/agenius66/ocr_-rag_-ui.git"
}

$DefaultInstallDir = Join-Path $HOME "DocRAG"
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

function Pause-BeforeExit {
    if (-not [Console]::IsInputRedirected) {
        Write-Host ""
        Read-Host (Msg "Press Enter to close this window" "按 Enter 关闭此窗口" "按 Enter 關閉此視窗") | Out-Null
    }
}

function Fail {
    param([string]$En, [string]$ZhCn, [string]$ZhTw)
    Write-Error (Msg $En $ZhCn $ZhTw)
    Pause-BeforeExit
    exit 1
}

function Refresh-SessionPath {
    $seen = @{}
    $segments = New-Object System.Collections.Generic.List[string]
    $pathSources = @(
        [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine),
        [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User),
        $env:Path,
        "C:\Program Files\Git\cmd",
        "C:\Program Files\Git\bin",
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\Scripts")
    )

    foreach ($source in $pathSources) {
        if ([string]::IsNullOrWhiteSpace($source)) {
            continue
        }
        foreach ($segment in ($source -split ";")) {
            $value = $segment.Trim()
            if ([string]::IsNullOrWhiteSpace($value)) {
                continue
            }
            $key = $value.ToLowerInvariant()
            if (-not $seen.ContainsKey($key)) {
                $seen[$key] = $true
                $segments.Add($value)
            }
        }
    }

    $env:Path = $segments -join ";"
}

function Normalize-InstallPath {
    param([string]$PathValue)
    $value = [string]$PathValue
    $value = $value.Trim()
    $value = $value.Trim([char[]]@('"', "'", [char]0x201C, [char]0x201D, [char]0x2018, [char]0x2019))
    if ($value.StartsWith('"') -and $value.EndsWith('"')) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ($value.StartsWith("'") -and $value.EndsWith("'")) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultInstallDir
    }
    if ($value -eq "~") {
        return $HOME
    }

    $value = [Environment]::ExpandEnvironmentVariables($value)
    if ($value.StartsWith("~/") -or $value.StartsWith('~\')) {
        return (Join-Path $HOME $value.Substring(2))
    }

    try {
        return [System.IO.Path]::GetFullPath($value)
    } catch {
        Fail "Invalid install directory: $value" "安装目录无效：$value" "安裝目錄無效：$value"
    }
}

function Choose-InstallDir {
    if ([string]::IsNullOrWhiteSpace($InstallDir)) {
        Say "Install directory. Press Enter to use the default path:" "请选择安装目录。直接回车使用默认路径：" "請選擇安裝目錄。直接 Enter 使用預設路徑："
        Write-Host "  $DefaultInstallDir"
        $inputPath = Read-Host (Msg "Install directory" "安装目录" "安裝目錄")
        return Normalize-InstallPath $inputPath
    }
    return Normalize-InstallPath $InstallDir
}

function Ensure-Git {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        return
    }

    Say "Git was not found. Trying to install Git with winget..." "未找到 Git，正在尝试使用 winget 安装 Git..." "未找到 Git，正在嘗試使用 winget 安裝 Git..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "Git is required. Please install Git for Windows or install winget first." "需要 Git。请先安装 Git for Windows，或先安装 winget。" "需要 Git。請先安裝 Git for Windows，或先安裝 winget。"
    }

    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
    Refresh-SessionPath
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Fail "Git was installed, but this PowerShell session still cannot find it. Reopen PowerShell and run bootstrap again." "Git 已安装，但当前 PowerShell 会话仍然找不到它。请重新打开 PowerShell 后再次运行安装命令。" "Git 已安裝，但目前 PowerShell 工作階段仍然找不到它。請重新開啟 PowerShell 後再次執行安裝命令。"
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

function Ensure-Python {
    $python = Get-PythonInvocation
    if ($python) {
        return $python
    }

    Say "Python 3.11+ was not found. Trying to install Python 3.12 with winget..." "未找到 Python 3.11+，正在尝试使用 winget 安装 Python 3.12..." "未找到 Python 3.11+，正在嘗試使用 winget 安裝 Python 3.12..."
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail "Python 3.11 or newer is required. Please install Python manually." "需要 Python 3.11 或更高版本。请手动安装 Python。" "需要 Python 3.11 或更高版本。請手動安裝 Python。"
    }

    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    Refresh-SessionPath
    $python = Get-PythonInvocation
    if (-not $python) {
        Fail "Python was installed, but this PowerShell session still cannot find it. Reopen PowerShell and run bootstrap again." "Python 已安装，但当前 PowerShell 会话仍然找不到它。请重新打开 PowerShell 后再次运行安装命令。" "Python 已安裝，但目前 PowerShell 工作階段仍然找不到它。請重新開啟 PowerShell 後再次執行安裝命令。"
    }
    return $python
}

function Clone-Or-UpdateRepo {
    param([string]$TargetDir)
    $parent = Split-Path -Parent $TargetDir
    $root = [System.IO.Path]::GetPathRoot($TargetDir)

    if (-not [string]::IsNullOrWhiteSpace($root) -and -not (Test-Path -LiteralPath $root)) {
        Fail "Install drive or root path does not exist: $root" "安装盘符或根路径不存在：$root" "安裝磁碟或根路徑不存在：$root"
    }

    if (-not [string]::IsNullOrWhiteSpace($parent) -and -not (Test-Path -LiteralPath $parent)) {
        try {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        } catch {
            Fail "Unable to create install parent directory: $parent" "无法创建安装父目录：$parent" "無法建立安裝父目錄：$parent"
        }
    }

    if (Test-Path -LiteralPath $TargetDir -PathType Leaf) {
        Fail "The install path exists but is a file: $TargetDir" "安装路径已存在，但它是文件：$TargetDir" "安裝路徑已存在，但它是檔案：$TargetDir"
    }

    if (Test-Path -LiteralPath (Join-Path $TargetDir ".git")) {
        Say "Existing Git repository found. Pulling latest code..." "发现已有 Git 仓库，正在更新..." "發現已有 Git 倉庫，正在更新..."
        git -C $TargetDir pull --ff-only
        return
    }

    if (Test-Path -LiteralPath $TargetDir) {
        $existingItems = @(Get-ChildItem -LiteralPath $TargetDir -Force -ErrorAction Stop)
        if ($existingItems.Count -gt 0) {
            Fail "The target directory already contains files and is not a Git repository. Please choose an empty directory or an existing DocRAG Git repository." "目标目录已有文件且不是 Git 仓库。请选择空目录，或选择已有的 DocRAG Git 仓库。" "目標目錄已有檔案且不是 Git 倉庫。請選擇空目錄，或選擇已有的 DocRAG Git 倉庫。"
        }
        Say "Empty install directory found. Cloning project into it..." "发现空安装目录，正在把项目拉取到该目录..." "發現空安裝目錄，正在把專案拉取到該目錄..."
    } else {
        Say "Cloning project from GitHub..." "正在从 GitHub 拉取项目源码..." "正在從 GitHub 拉取專案原始碼..."
    }

    git clone $GitHubRepoUrl $TargetDir
    if ($LASTEXITCODE -ne 0) {
        Say "GitHub clone failed. Trying Gitee..." "GitHub 拉取失败，尝试 Gitee..." "GitHub 拉取失敗，嘗試 Gitee..."
        git clone $GiteeRepoUrl $TargetDir
        if ($LASTEXITCODE -ne 0) {
            Fail "Both GitHub and Gitee clone failed." "GitHub 和 Gitee 拉取都失败。" "GitHub 和 Gitee 拉取都失敗。"
        }
    }
}

function Install-Dependencies {
    param([string]$TargetDir, [string[]]$PythonInvocation)
    Set-Location $TargetDir
    if (-not (Test-Path ".venv")) {
        Say "Creating virtual environment..." "正在创建虚拟环境..." "正在建立虛擬環境..."
        Invoke-Python -Invocation $PythonInvocation -Arguments @("-m", "venv", ".venv")
    }

    $venvPython = Join-Path $TargetDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Fail "Virtual environment creation failed." "虚拟环境创建失败。" "虛擬環境建立失敗。"
    }

    Say "Upgrading pip..." "正在升级 pip..." "正在升級 pip..."
    & $venvPython -m pip install --upgrade pip
    Say "Installing project dependencies. This can take a while..." "正在安装项目依赖，这一步可能需要较长时间..." "正在安裝專案依賴，這一步可能需要較長時間..."
    & $venvPython -m pip install -r requirements.txt
    Set-Content -Path (Join-Path $TargetDir ".launcher_lang") -Value $Script:DocRagLang -Encoding UTF8
}

function Write-RootLauncher {
    param([string]$TargetDir)
    $launcher = Join-Path $TargetDir "start.ps1"
    $content = @'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $Root "scripts\start.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript
'@
    Set-Content -Path $launcher -Value $content -Encoding UTF8
    Say "Launch later with: powershell -ExecutionPolicy Bypass -File start.ps1" "以后可启动：右键 start.ps1 选择“使用 PowerShell 运行”，或执行 powershell -ExecutionPolicy Bypass -File start.ps1" "以後可啟動：右鍵 start.ps1 選擇「使用 PowerShell 執行」，或執行 powershell -ExecutionPolicy Bypass -File start.ps1"
}

try {
    Choose-Language
    $ResolvedInstallDir = Choose-InstallDir
    Say "Detected system: Windows PowerShell" "检测到系统：Windows PowerShell" "偵測到系統：Windows PowerShell"
    Say "Install directory: $ResolvedInstallDir" "安装目录：$ResolvedInstallDir" "安裝目錄：$ResolvedInstallDir"
    Ensure-Git
    $PythonInvocation = Ensure-Python
    Clone-Or-UpdateRepo $ResolvedInstallDir
    Install-Dependencies $ResolvedInstallDir $PythonInvocation
    Write-RootLauncher $ResolvedInstallDir
    Say "Installation completed." "安装完成。" "安裝完成。"
    Pause-BeforeExit
} catch {
    Write-Host ""
    Write-Host (Msg "Installation stopped because of an unexpected error:" "安装中止，发生未预期错误：" "安裝中止，發生未預期錯誤：") -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Pause-BeforeExit
    exit 1
}
