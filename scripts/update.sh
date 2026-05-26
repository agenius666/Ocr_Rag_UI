#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

REPO_GITEE_URL="${DOC_RAG_GITEE_REPO_URL:-https://gitee.com/agenius66/ocr_-rag_-ui.git}"

unique_words() {
  awk 'NF && !seen[$0]++'
}

pull_with_fallback() {
  local branch
  local repo
  local candidate_branch
  local repos=()
  local branches=()

  say "Updating source code..." "正在更新源码..." "正在更新原始碼..."
  if git pull --ff-only; then
    return 0
  fi

  say \
    "Default Git remote update failed. Trying Gitee fallback..." \
    "默认 Git 源更新失败，正在尝试 Gitee 备用仓库..." \
    "預設 Git 來源更新失敗，正在嘗試 Gitee 備用倉庫..."

  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [ "$branch" = "HEAD" ]; then
    branch=""
  fi

  if git remote 2>/dev/null | grep -qx "gitee"; then
    repos+=("gitee")
  fi
  repos+=("$REPO_GITEE_URL")

  while IFS= read -r candidate_branch; do
    branches+=("$candidate_branch")
  done < <(printf '%s\n%s\n%s\n' "$branch" "main" "master" | unique_words)

  while IFS= read -r repo; do
    for candidate_branch in "${branches[@]}"; do
      printf '%s%s %s\n' "$(msg 'Trying fallback: ' '尝试备用仓库：' '嘗試備用倉庫：')" "$repo" "$candidate_branch"
      if git pull --ff-only "$repo" "$candidate_branch"; then
        return 0
      fi
    done
  done < <(printf '%s\n' "${repos[@]}" | unique_words)

  say \
    "Source update failed. Please check your network or update manually from GitHub/Gitee." \
    "源码更新失败。请检查网络，或从 GitHub/Gitee 手动更新。" \
    "原始碼更新失敗。請檢查網路，或從 GitHub/Gitee 手動更新。"
  return 1
}

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

  if ! pull_with_fallback; then
    return 1
  fi

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
