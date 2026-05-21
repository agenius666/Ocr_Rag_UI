#!/usr/bin/env bash
set -euo pipefail

GITHUB_REPO_URL="${DOC_RAG_GITHUB_REPO_URL:-https://github.com/agenius666/Ocr_Rag_UI.git}"
GITEE_REPO_URL="${DOC_RAG_GITEE_REPO_URL:-https://gitee.com/agenius66/ocr_-rag_-ui.git}"
DEFAULT_INSTALL_DIR="$HOME/DocRAG"
INSTALL_DIR="${DOC_RAG_INSTALL_DIR:-}"
DOC_RAG_LANG="${DOC_RAG_LANG:-}"

normalize_language() {
  case "${1:-}" in
    en|EN|english|English) printf 'en\n' ;;
    zh_CN|zh-cn|zh|cn|CN|简体中文) printf 'zh_CN\n' ;;
    zh_TW|zh-tw|tw|TW|繁體中文|繁体中文) printf 'zh_TW\n' ;;
    *) return 1 ;;
  esac
}

choose_language() {
  local choice
  if [ -n "$DOC_RAG_LANG" ] && normalize_language "$DOC_RAG_LANG" >/dev/null 2>&1; then
    DOC_RAG_LANG="$(normalize_language "$DOC_RAG_LANG")"
    return
  fi
  printf 'Select language / 选择语言 / 選擇語言:\n'
  printf '1. English\n'
  printf '2. 简体中文\n'
  printf '3. 繁體中文\n'
  printf 'Please choose [1-3] / 请选择 [1-3]：'
  read -r choice
  case "${choice:-1}" in
    2) DOC_RAG_LANG="zh_CN" ;;
    3) DOC_RAG_LANG="zh_TW" ;;
    *) DOC_RAG_LANG="en" ;;
  esac
}

expand_user_path() {
  local value="$1"
  case "$value" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${value#~/}" ;;
    *) printf '%s\n' "$value" ;;
  esac
}

choose_install_dir() {
  local input_dir
  if [ -n "$INSTALL_DIR" ]; then
    INSTALL_DIR="$(expand_user_path "$INSTALL_DIR")"
    return
  fi

  printf '%s\n' "$(msg \
    "Install directory. Press Enter to use the default path:" \
    "请选择安装目录。直接回车使用默认路径：" \
    "請選擇安裝目錄。直接 Enter 使用預設路徑：")"
  printf '  %s\n' "$DEFAULT_INSTALL_DIR"
  printf '%s' "$(msg \
    "Install directory: " \
    "安装目录：" \
    "安裝目錄：")"
  read -r input_dir
  if [ -z "${input_dir:-}" ]; then
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
  else
    INSTALL_DIR="$(expand_user_path "$input_dir")"
  fi
}

msg() {
  local en="$1"
  local zh_cn="$2"
  local zh_tw="$3"
  case "$DOC_RAG_LANG" in
    en) printf '%s' "$en" ;;
    zh_TW) printf '%s' "$zh_tw" ;;
    *) printf '%s' "$zh_cn" ;;
  esac
}

say() {
  msg "$1" "$2" "$3"
  printf '\n'
}

die() {
  say "Error: $1" "错误：$2" "錯誤：$3" >&2
  exit 1
}

detect_os() {
  local kernel
  kernel="$(uname -s 2>/dev/null || echo unknown)"
  case "$kernel" in
    Darwin*) printf 'macos\n' ;;
    Linux*) printf 'linux\n' ;;
    MINGW*|MSYS*|CYGWIN*) printf 'windows\n' ;;
    *) printf 'unknown\n' ;;
  esac
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "$1 was not found. Please install it first." "未找到 $1，请先安装后再运行。" "未找到 $1，請先安裝後再執行。"
}

find_python_311() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
      then
        printf '%s\n' "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

clone_or_update_repo() {
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [ ! -d "$INSTALL_DIR" ]; then
    say "Cloning project to: $INSTALL_DIR" "正在拉取项目源码到：$INSTALL_DIR" "正在拉取專案原始碼到：$INSTALL_DIR"
    if ! git clone "$GITHUB_REPO_URL" "$INSTALL_DIR"; then
      say "GitHub clone failed. Trying Gitee..." "GitHub 拉取失败，尝试 Gitee..." "GitHub 拉取失敗，嘗試 Gitee..."
      git clone "$GITEE_REPO_URL" "$INSTALL_DIR"
    fi
    return
  fi

  if [ -d "$INSTALL_DIR/.git" ]; then
    say "Existing Git repository found. Pulling latest code: $INSTALL_DIR" "发现已有 Git 仓库，正在更新：$INSTALL_DIR" "發現已有 Git 倉庫，正在更新：$INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
    return
  fi

  die "The target directory exists but is not a Git repository: $INSTALL_DIR" "目录已存在但不是 Git 仓库，不能自动覆盖：$INSTALL_DIR" "目錄已存在但不是 Git 倉庫，不能自動覆蓋：$INSTALL_DIR"
}

venv_python() {
  if [ -x "$INSTALL_DIR/.venv/bin/python" ]; then
    printf '%s\n' "$INSTALL_DIR/.venv/bin/python"
  elif [ -x "$INSTALL_DIR/.venv/Scripts/python.exe" ]; then
    printf '%s\n' "$INSTALL_DIR/.venv/Scripts/python.exe"
  else
    return 1
  fi
}

install_dependencies() {
  local python_cmd
  local venv_py
  python_cmd="$(find_python_311)" || die "Python 3.11 or newer was not found." "未找到 Python 3.11 或更高版本。" "未找到 Python 3.11 或更高版本。"
  cd "$INSTALL_DIR"

  if [ ! -d ".venv" ]; then
    say "Creating virtual environment..." "正在创建虚拟环境..." "正在建立虛擬環境..."
    "$python_cmd" -m venv .venv
  fi

  venv_py="$(venv_python)" || die "Virtual environment creation failed." "虚拟环境创建失败。" "虛擬環境建立失敗。"
  say "Upgrading pip..." "正在升级 pip..." "正在升級 pip..."
  "$venv_py" -m pip install --upgrade pip
  say "Installing project dependencies. This can take a while..." "正在安装项目依赖，这一步可能需要较长时间..." "正在安裝專案依賴，這一步可能需要較長時間..."
  "$venv_py" -m pip install -r requirements.txt
  chmod +x scripts/*.sh
  printf '%s\n' "$DOC_RAG_LANG" > "$INSTALL_DIR/.launcher_lang"
}

write_unix_launcher() {
  local launcher="$1"
  cat > "$launcher" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec bash "scripts/start.sh"
EOF
  chmod +x "$launcher"
}

write_macos_launcher() {
  local launcher="$INSTALL_DIR/start.command"
  cat > "$launcher" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

schedule_terminal_close() {
  if [ "${DOC_RAG_KEEP_TERMINAL_OPEN:-0}" = "1" ]; then
    return 0
  fi
  if [ "$(uname -s 2>/dev/null || true)" != "Darwin" ]; then
    return 0
  fi
  command -v osascript >/dev/null 2>&1 || return 0
  local current_tty
  current_tty="$(tty 2>/dev/null || true)"
  [ -n "$current_tty" ] || return 0
  nohup osascript \
    -e 'delay 0.5' \
    -e 'tell application "Terminal"' \
    -e 'repeat with w in windows' \
    -e 'repeat with t in tabs of w' \
    -e "if (tty of t) is \"$current_tty\" then" \
    -e 'close w' \
    -e 'return' \
    -e 'end if' \
    -e 'end repeat' \
    -e 'end repeat' \
    -e 'end tell' >/dev/null 2>&1 &
}

set +e
bash "scripts/start.sh"
status=$?
schedule_terminal_close
exit "$status"
EOF
  chmod +x "$launcher"
}

write_windows_launcher() {
  local launcher="$INSTALL_DIR/start.bat"
  cat > "$launcher" <<'EOF'
@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:\=/%"
set "BASH_EXE="
if exist "C:\Program Files\Git\bin\bash.exe" set "BASH_EXE=C:\Program Files\Git\bin\bash.exe"
if not defined BASH_EXE if exist "C:\Program Files\Git\usr\bin\bash.exe" set "BASH_EXE=C:\Program Files\Git\usr\bin\bash.exe"
if not defined BASH_EXE (
  echo Git Bash was not found. Please install Git for Windows.
  echo 未找到 Git Bash，请先安装 Git for Windows。
  echo 未找到 Git Bash，請先安裝 Git for Windows。
  pause
  exit /b 1
)
"%BASH_EXE%" -lc "cd \"%PROJECT_DIR%\" && bash scripts/start.sh"
pause
EOF
}

create_launcher() {
  local os_name="$1"
  case "$os_name" in
    macos)
      write_macos_launcher
      say "Launch later by double-clicking: $INSTALL_DIR/start.command" "以后可双击启动：$INSTALL_DIR/start.command" "以後可雙擊啟動：$INSTALL_DIR/start.command"
      ;;
    linux)
      write_unix_launcher "$INSTALL_DIR/start.sh"
      say "Launch later with: bash $INSTALL_DIR/start.sh" "以后可启动：bash $INSTALL_DIR/start.sh" "以後可啟動：bash $INSTALL_DIR/start.sh"
      ;;
    windows)
      write_windows_launcher
      say "Launch later by double-clicking: $INSTALL_DIR/start.bat" "以后可双击启动：$INSTALL_DIR/start.bat" "以後可雙擊啟動：$INSTALL_DIR/start.bat"
      ;;
    *)
      write_unix_launcher "$INSTALL_DIR/start.sh"
      say "Unknown system. A generic launcher was created: bash $INSTALL_DIR/start.sh" "未知系统，已生成通用启动入口：bash $INSTALL_DIR/start.sh" "未知系統，已產生通用啟動入口：bash $INSTALL_DIR/start.sh"
      ;;
  esac
}

main() {
  local os_name
  choose_language
  choose_install_dir
  os_name="$(detect_os)"
  say "Detected system: $os_name" "检测到系统：$os_name" "偵測到系統：$os_name"
  require_command git
  find_python_311 >/dev/null || die "Python 3.11 or newer was not found." "未找到 Python 3.11 或更高版本。" "未找到 Python 3.11 或更高版本。"
  clone_or_update_repo
  install_dependencies
  create_launcher "$os_name"
  say "Installation completed." "安装完成。" "安裝完成。"
}

main "$@"
