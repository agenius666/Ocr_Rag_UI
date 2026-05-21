#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

UPDATE_GITHUB_URL="${DOC_RAG_UPDATE_GITHUB_URL:-https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/update/latest.json}"
UPDATE_GITEE_URL="${DOC_RAG_UPDATE_GITEE_URL:-https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/update/latest.json}"
APP_URL="http://127.0.0.1:8501"

version_gt() {
  local left="$1"
  local right="$2"
  local py_cmd
  py_cmd="$(script_python)" || return 1
  "$py_cmd" - "$left" "$right" <<'PY'
import re
import sys

def parts(value):
    return [int(x) for x in re.findall(r"\d+", value or "0")]

left = parts(sys.argv[1])
right = parts(sys.argv[2])
size = max(len(left), len(right))
left += [0] * (size - len(left))
right += [0] * (size - len(right))
raise SystemExit(0 if left > right else 1)
PY
}

download_latest_json() {
  local target="$1"
  : > "$target"
  if [ -n "$UPDATE_GITHUB_URL" ] && curl -fsL "$UPDATE_GITHUB_URL" -o "$target" 2>/dev/null; then
    return 0
  fi
  if [ -n "$UPDATE_GITEE_URL" ] && curl -fsL "$UPDATE_GITEE_URL" -o "$target" 2>/dev/null; then
    return 0
  fi
  return 1
}

json_value() {
  local json_file="$1"
  local key="$2"
  local py_cmd
  py_cmd="$(script_python)" || return 1
  "$py_cmd" - "$json_file" "$key" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)
value = data.get(sys.argv[2], "")
if isinstance(value, list):
    print("\n".join(str(item) for item in value))
else:
    print(value)
PY
}

check_update() {
  local mode="${1:-auto}"
  local tmp_json
  local local_version
  local remote_version
  tmp_json="$(mktemp)"

  if ! download_latest_json "$tmp_json"; then
    say \
      "Unable to check for updates. You can try manual check later." \
      "无法检查更新，可稍后手动检查。" \
      "無法檢查更新，可稍後手動檢查。"
    rm -f "$tmp_json"
    return 0
  fi

  local_version="$(current_version)"
  remote_version="$(json_value "$tmp_json" version)"
  if version_gt "$remote_version" "$local_version"; then
    printf '\n'
    say "New version found." "发现新版本。" "發現新版本。"
    printf '%s%s\n' "$(msg 'Current version: ' '当前版本：' '目前版本：')" "$local_version"
    printf '%s%s\n' "$(msg 'Latest version: ' '最新版本：' '最新版本：')" "$remote_version"
    printf '%s%s\n' "$(msg 'Release date: ' '更新日期：' '更新日期：')" "$(json_value "$tmp_json" date)"
    printf '%s%s\n' "$(msg 'Title: ' '更新标题：' '更新標題：')" "$(json_value "$tmp_json" title)"
    printf '%s\n%s\n' "$(msg 'Notes:' '更新内容：' '更新內容：')" "$(json_value "$tmp_json" notes | sed 's/^/  - /')"
    say "Choose \"Update Source\" in the menu to update." "可在菜单中选择“更新源码”。" "可在選單中選擇「更新原始碼」。"
    printf '\n'
  elif [ "$mode" = "manual" ]; then
    printf '%s%s\n' "$(msg 'Already up to date: ' '当前已是最新版本：' '目前已是最新版本：')" "$local_version"
  else
    say "Already up to date." "当前已是最新版本。" "目前已是最新版本。"
  fi
  rm -f "$tmp_json"
}

open_browser() {
  if command -v open >/dev/null 2>&1; then
    open "$APP_URL" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$APP_URL" >/dev/null 2>&1 || true
  elif command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "$APP_URL" >/dev/null 2>&1 || true
  fi
}

wait_for_app_ready() {
  local max_wait="${DOC_RAG_BROWSER_WAIT_SECONDS:-45}"
  local extra_delay="${DOC_RAG_BROWSER_DELAY_SECONDS:-3}"
  local elapsed=0

  if command -v curl >/dev/null 2>&1; then
    while [ "$elapsed" -lt "$max_wait" ]; do
      if curl -fsS "$APP_URL/_stcore/health" >/dev/null 2>&1 || curl -fsS "$APP_URL" >/dev/null 2>&1; then
        sleep "$extra_delay"
        return 0
      fi
      sleep 1
      elapsed=$((elapsed + 1))
    done
    return 1
  fi

  sleep "${DOC_RAG_BROWSER_FALLBACK_DELAY_SECONDS:-6}"
  return 0
}

open_browser_after_ready() {
  if wait_for_app_ready; then
    open_browser
  else
    say \
      "The app did not become ready in time. Open manually after Streamlit finishes loading: $APP_URL" \
      "程序未在等待时间内就绪。请在 Streamlit 加载完成后手动打开：$APP_URL" \
      "程式未在等待時間內就緒。請在 Streamlit 載入完成後手動開啟：$APP_URL"
  fi
}

start_app() {
  local streamlit_cmd
  cd "$ROOT_DIR"
  streamlit_cmd="$(streamlit_bin)" || {
    say \
      "Virtual environment or Streamlit was not found. Choose \"Install / Repair Dependencies\" first." \
      "未找到虚拟环境或 Streamlit，请先选择“安装/修复依赖”。" \
      "未找到虛擬環境或 Streamlit，請先選擇「安裝/修復依賴」。"
    return 0
  }
  open_browser_after_ready &
  "$streamlit_cmd" run app.py --server.address 127.0.0.1 --server.port 8501
}

show_version() {
  printf '%s%s\n' "$(msg 'Current version: ' '当前版本：' '目前版本：')" "$(current_version)"
  printf '%s%s\n' "$(msg 'Project directory: ' '项目目录：' '專案目錄：')" "$ROOT_DIR"
}

menu() {
  local choice
  while true; do
    printf '\n==== %s ====\n' "$(msg 'DocRAG Launcher' 'DocRAG 启动器' 'DocRAG 啟動器')"
    printf '1. %s\n' "$(msg 'Start App' '启动程序' '啟動程式')"
    printf '2. %s\n' "$(msg 'Check Updates' '检查更新' '檢查更新')"
    printf '3. %s\n' "$(msg 'Update Source' '更新源码' '更新原始碼')"
    printf '4. %s\n' "$(msg 'Install / Repair Dependencies' '安装/修复依赖' '安裝/修復依賴')"
    printf '5. %s\n' "$(msg 'Show Current Version' '查看当前版本' '查看目前版本')"
    printf '6. %s\n' "$(msg 'Uninstall / Clean' '卸载/清理' '卸載/清理')"
    printf '7. %s\n' "$(msg 'Exit' '退出' '退出')"
    printf '%s' "$(msg 'Choose [1-7]: ' '请选择 [1-7]：' '請選擇 [1-7]：')"
    read -r choice
    case "$choice" in
      1) start_app ;;
      2) check_update manual ;;
      3) bash "$SCRIPT_DIR/update.sh" ;;
      4) bash "$SCRIPT_DIR/install.sh" ;;
      5) show_version ;;
      6) bash "$SCRIPT_DIR/uninstall.sh" ;;
      7) exit 0 ;;
      *) say "Invalid choice." "无效选择。" "無效選擇。" ;;
    esac
  done
}

cd "$ROOT_DIR"
check_update auto
menu
