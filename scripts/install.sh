#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

main() {
  local python_cmd
  local venv_py
  cd "$ROOT_DIR"
  python_cmd="$(find_python_311)" || die "Python 3.11 or newer was not found." "未找到 Python 3.11 或更高版本。" "未找到 Python 3.11 或更高版本。"

  if [ ! -d ".venv" ]; then
    say "Creating virtual environment..." "正在创建虚拟环境..." "正在建立虛擬環境..."
    "$python_cmd" -m venv .venv
  fi

  venv_py="$(venv_python)" || die "Virtual environment Python was not found." "未找到虚拟环境中的 Python。" "未找到虛擬環境中的 Python。"
  say "Upgrading pip..." "正在升级 pip..." "正在升級 pip..."
  "$venv_py" -m pip install --upgrade pip
  say "Installing or repairing dependencies..." "正在安装或修复依赖..." "正在安裝或修復依賴..."
  "$venv_py" -m pip install -r requirements.txt

  chmod +x scripts/*.sh
  if [ -f "start.command" ]; then
    chmod +x start.command
  fi
  if [ -f "start.sh" ]; then
    chmod +x start.sh
  fi
  repair_root_launcher

  say \
    "Dependency installation / repair completed. Start the app from the launcher." \
    "依赖安装/修复完成。请通过 start 启动器启动程序。" \
    "依賴安裝/修復完成。請通過 start 啟動器啟動程式。"
}

main "$@"
