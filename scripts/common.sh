#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LANGUAGE_FILE="$ROOT_DIR/.launcher_lang"

normalize_language() {
  case "${1:-}" in
    en|EN|english|English) printf 'en\n' ;;
    zh_CN|zh-cn|zh|cn|CN|简体中文) printf 'zh_CN\n' ;;
    zh_TW|zh-tw|tw|TW|繁體中文|繁体中文) printf 'zh_TW\n' ;;
    *) return 1 ;;
  esac
}

choose_language() {
  local saved_lang=""
  local choice=""
  if [ -n "${DOC_RAG_LANG:-}" ] && normalize_language "$DOC_RAG_LANG" >/dev/null 2>&1; then
    DOC_RAG_LANG="$(normalize_language "$DOC_RAG_LANG")"
    return
  fi

  if [ -f "$LANGUAGE_FILE" ] && normalize_language "$(cat "$LANGUAGE_FILE")" >/dev/null 2>&1; then
    saved_lang="$(normalize_language "$(cat "$LANGUAGE_FILE")")"
  fi

  if [ -n "$saved_lang" ] && [ "${DOC_RAG_RESELECT_LANG:-0}" != "1" ]; then
    DOC_RAG_LANG="$saved_lang"
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
  printf '%s\n' "$DOC_RAG_LANG" > "$LANGUAGE_FILE"
}

msg() {
  local en="$1"
  local zh_cn="$2"
  local zh_tw="$3"
  case "${DOC_RAG_LANG:-zh_CN}" in
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

script_python() {
  local candidate
  for candidate in python3.13 python3.12 python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
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

venv_python() {
  if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/python"
  elif [ -x "$ROOT_DIR/.venv/Scripts/python.exe" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/Scripts/python.exe"
  else
    return 1
  fi
}

streamlit_bin() {
  if [ -x "$ROOT_DIR/.venv/bin/streamlit" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/bin/streamlit"
  elif [ -x "$ROOT_DIR/.venv/Scripts/streamlit.exe" ]; then
    printf '%s\n' "$ROOT_DIR/.venv/Scripts/streamlit.exe"
  else
    return 1
  fi
}

current_version() {
  if [ -f "$ROOT_DIR/VERSION" ]; then
    tr -d '[:space:]' < "$ROOT_DIR/VERSION"
  else
    printf '0.0.0'
  fi
}

confirm_yes() {
  local prompt
  prompt="$(msg "$1 Type YES to confirm: " "$2 输入 YES 确认：" "$3 輸入 YES 確認：")"
  local answer
  printf '%s' "$prompt"
  read -r answer
  [ "$answer" = "YES" ]
}

write_unix_root_launcher() {
  local launcher="$1"
  cat > "$launcher" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec bash "scripts/start.sh"
EOF
  chmod +x "$launcher"
}

write_macos_root_launcher() {
  local launcher="$ROOT_DIR/start.command"
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

write_windows_root_launcher() {
  local launcher="$ROOT_DIR/start.ps1"
  cat > "$launcher" <<'EOF'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartScript = Join-Path $Root "scripts\start.ps1"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript
EOF
}

repair_root_launcher() {
  local os_name
  os_name="$(detect_os)"
  case "$os_name" in
    macos) write_macos_root_launcher ;;
    linux) write_unix_root_launcher "$ROOT_DIR/start.sh" ;;
    windows) write_windows_root_launcher ;;
    *) write_unix_root_launcher "$ROOT_DIR/start.sh" ;;
  esac
}

choose_language
