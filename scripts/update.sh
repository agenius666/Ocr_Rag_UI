#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

main() {
  local venv_py
  cd "$ROOT_DIR"
  if [ ! -d ".git" ]; then
    say \
      "This directory is not a Git repository. It may be a ZIP copy." \
      "当前目录不是 Git 仓库，可能是 ZIP 解压版。" \
      "目前目錄不是 Git 倉庫，可能是 ZIP 解壓版。"
    say \
      "Automatic git pull is unavailable. Please download the latest version from GitHub/Gitee or rerun bootstrap." \
      "无法自动 git pull，请前往 GitHub/Gitee 下载最新版，或重新运行 bootstrap 安装命令。" \
      "無法自動 git pull，請前往 GitHub/Gitee 下載最新版，或重新執行 bootstrap 安裝命令。"
    return 0
  fi

  say "Updating source code..." "正在更新源码..." "正在更新原始碼..."
  git pull --ff-only

  if [ -d ".venv" ]; then
    venv_py="$(venv_python)" || {
      say \
        ".venv exists but Python was not found. Choose \"Install / Repair Dependencies\"." \
        "发现 .venv 但未找到 Python，请选择“安装/修复依赖”。" \
        "發現 .venv 但未找到 Python，請選擇「安裝/修復依賴」。"
      return 0
    }
    say "Syncing dependencies..." "正在同步依赖..." "正在同步依賴..."
    "$venv_py" -m pip install -r requirements.txt
  fi

  chmod +x scripts/*.sh
  repair_root_launcher
  say "Update completed. Please restart the app." "更新完成，请重新启动程序。" "更新完成，請重新啟動程式。"
}

main "$@"
