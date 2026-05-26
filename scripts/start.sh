#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

UPDATE_GITHUB_URL="${DOC_RAG_UPDATE_GITHUB_URL:-https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/update/latest.json}"
UPDATE_GITEE_URL="${DOC_RAG_UPDATE_GITEE_URL:-https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/update/latest.json}"
APP_URL="http://127.0.0.1:8501"
THEME_FILE="$ROOT_DIR/.launcher_theme"
STREAMLIT_CONFIG_FILE="$ROOT_DIR/.streamlit/config.toml"

normalize_theme() {
  case "${1:-}" in
    light|Light|LIGHT|浅色|淺色) printf 'light\n' ;;
    dark|Dark|DARK|深色) printf 'dark\n' ;;
    *) return 1 ;;
  esac
}

current_theme() {
  local saved_theme=""
  if [ -f "$THEME_FILE" ] && normalize_theme "$(cat "$THEME_FILE")" >/dev/null 2>&1; then
    normalize_theme "$(cat "$THEME_FILE")"
    return
  fi

  if [ -f "$STREAMLIT_CONFIG_FILE" ]; then
    saved_theme="$(sed -n 's/^[[:space:]]*base[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$STREAMLIT_CONFIG_FILE" | tail -n 1)"
    if normalize_theme "$saved_theme" >/dev/null 2>&1; then
      normalize_theme "$saved_theme"
      return
    fi
  fi

  printf 'light\n'
}

theme_label() {
  case "$(current_theme)" in
    dark) msg "Dark" "深色" "深色" ;;
    *) msg "Light" "浅色" "淺色" ;;
  esac
}

write_streamlit_theme() {
  local theme="$1"
  local py_cmd
  mkdir -p "$(dirname "$STREAMLIT_CONFIG_FILE")"
  py_cmd="$(script_python)" || return 1
  "$py_cmd" - "$STREAMLIT_CONFIG_FILE" "$theme" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
theme = sys.argv[2]
text = path.read_text(encoding="utf-8") if path.exists() else ""
lines = text.splitlines()
out = []
in_theme = False
theme_found = False
base_written = False

for line in lines:
    stripped = line.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        if in_theme and not base_written:
            out.append(f'base = "{theme}"')
            base_written = True
        in_theme = stripped == "[theme]"
        theme_found = theme_found or in_theme
        out.append(line)
        continue
    if in_theme and stripped.startswith("base"):
        out.append(f'base = "{theme}"')
        base_written = True
        continue
    out.append(line)

if not theme_found:
    if out and out[-1].strip():
        out.append("")
    out.extend(["[theme]", f'base = "{theme}"'])
elif in_theme and not base_written:
    out.append(f'base = "{theme}"')

path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
PY
}

apply_saved_theme() {
  local theme
  theme="$(current_theme)"
  printf '%s\n' "$theme" > "$THEME_FILE"
  if ! write_streamlit_theme "$theme"; then
    say \
      "Theme config could not be written. The app will continue with the existing Streamlit theme." \
      "无法写入主题配置，将继续使用现有 Streamlit 主题。" \
      "無法寫入主題配置，將繼續使用現有 Streamlit 主題。"
  fi
}

theme_menu() {
  local choice
  local theme
  while true; do
    printf '\n==== %s ====\n' "$(msg 'Theme Settings' '主题设置' '主題設定')"
    printf '%s%s\n' "$(msg 'Current theme: ' '当前主题：' '目前主題：')" "$(theme_label)"
    printf '1. %s\n' "$(msg 'Light' '浅色' '淺色')"
    printf '2. %s\n' "$(msg 'Dark' '深色' '深色')"
    printf '3. %s\n' "$(msg 'Return' '返回' '返回')"
    printf '%s' "$(msg 'Choose [1-3]: ' '请选择 [1-3]：' '請選擇 [1-3]：')"
    read -r choice
    case "$choice" in
      1) theme="light" ;;
      2) theme="dark" ;;
      3) return 0 ;;
      *) say "Invalid choice." "无效选择。" "無效選擇。"; continue ;;
    esac
    printf '%s\n' "$theme" > "$THEME_FILE"
    write_streamlit_theme "$theme"
    say \
      "Theme saved. Restart the app to apply it if Streamlit is already running." \
      "主题已保存。如果 Streamlit 已在运行，请重启程序后生效。" \
      "主題已儲存。如果 Streamlit 已在執行，請重新啟動程式後生效。"
  done
}

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
  apply_saved_theme
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
    printf '6. %s (%s)\n' "$(msg 'Theme Settings' '主题设置' '主題設定')" "$(theme_label)"
    printf '7. %s\n' "$(msg 'Uninstall / Clean' '卸载/清理' '卸載/清理')"
    printf '8. %s\n' "$(msg 'Exit' '退出' '退出')"
    printf '%s' "$(msg 'Choose [1-8]: ' '请选择 [1-8]：' '請選擇 [1-8]：')"
    read -r choice
    case "$choice" in
      1) start_app ;;
      2) check_update manual ;;
      3) bash "$SCRIPT_DIR/update.sh" ;;
      4) bash "$SCRIPT_DIR/install.sh" ;;
      5) show_version ;;
      6) theme_menu ;;
      7) bash "$SCRIPT_DIR/uninstall.sh" ;;
      8) exit 0 ;;
      *) say "Invalid choice." "无效选择。" "無效選擇。" ;;
    esac
  done
}

cd "$ROOT_DIR"
check_update auto
menu
