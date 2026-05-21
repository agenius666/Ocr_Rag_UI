#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/common.sh"

safe_clean() {
  cd "$ROOT_DIR"
  say "Running safe cleanup..." "正在执行安全清理..." "正在執行安全清理..."
  rm -rf .venv .pytest_cache .mypy_cache .ruff_cache logs tmp temp
  find . -type d -name "__pycache__" -prune -exec rm -rf {} +
  find . -type f -name "*.pyc" -delete
  say "Safe cleanup completed." "安全清理完成。" "安全清理完成。"
}

clean_user_data() {
  cd "$ROOT_DIR"
  confirm_yes \
    "This will delete user data, uploads, OCR output, and vector databases." \
    "将删除用户数据、上传文件、OCR 输出和向量数据库。" \
    "將刪除使用者資料、上傳文件、OCR 輸出和向量資料庫。" || {
      say "Cancelled." "已取消。" "已取消。"
      return 0
    }
  rm -rf data uploads output ocr-output chroma chromadb qdrant_storage qdrant_db
  rm -f app_state.sqlite3 app_state.sqlite3-shm app_state.sqlite3-wal
  say "User data cleanup completed." "用户数据清理完成。" "使用者資料清理完成。"
}

clean_model_cache() {
  confirm_yes \
    "This will delete model caches. Models will be downloaded again on next use." \
    "将删除模型缓存，后续首次使用会重新下载模型。" \
    "將刪除模型快取，後續首次使用會重新下載模型。" || {
      say "Cancelled." "已取消。" "已取消。"
      return 0
    }
  rm -rf "$ROOT_DIR/model_cache"
  rm -rf "$HOME/models/paddleocr"
  rm -rf "$HOME/.paddlex" "$HOME/.paddleocr"
  rm -rf "$HOME/.cache/huggingface" "$HOME/.cache/torch" "$HOME/.cache/modelscope"
  say "Model cache cleanup completed." "模型缓存清理完成。" "模型快取清理完成。"
}

full_uninstall() {
  confirm_yes \
    "Full uninstall step 1: run safe cleanup." \
    "完全卸载第一步：执行安全清理。" \
    "完全卸載第一步：執行安全清理。" || {
      say "Cancelled." "已取消。" "已取消。"
      return 0
    }
  safe_clean
  clean_user_data
  clean_model_cache
  printf '%s%s\n' \
    "$(msg 'Full uninstall flow completed. To remove source code completely, delete this project folder manually: ' '完全卸载流程完成。如需彻底删除源码，请手动删除当前项目文件夹：' '完全卸載流程完成。如需徹底刪除原始碼，請手動刪除目前專案資料夾：')" \
    "$ROOT_DIR"
}

menu() {
  local choice
  while true; do
    printf '\n==== %s ====\n' "$(msg 'Uninstall / Clean' '卸载 / 清理' '卸載 / 清理')"
    printf '1. %s\n' "$(msg 'Safe cleanup: remove virtual environment and temporary files' '安全清理：删除虚拟环境和临时文件' '安全清理：刪除虛擬環境和暫存文件')"
    printf '2. %s\n' "$(msg 'Delete user data / OCR output / vector database' '删除用户数据 / OCR 输出 / 向量数据库' '刪除使用者資料 / OCR 輸出 / 向量資料庫')"
    printf '3. %s\n' "$(msg 'Delete model caches' '删除模型缓存' '刪除模型快取')"
    printf '4. %s\n' "$(msg 'Full uninstall' '完全卸载' '完全卸載')"
    printf '5. %s\n' "$(msg 'Back' '返回' '返回')"
    printf '%s' "$(msg 'Choose [1-5]: ' '请选择 [1-5]：' '請選擇 [1-5]：')"
    read -r choice
    case "$choice" in
      1) safe_clean ;;
      2) clean_user_data ;;
      3) clean_model_cache ;;
      4) full_uninstall ;;
      5) exit 0 ;;
      *) say "Invalid choice." "无效选择。" "無效選擇。" ;;
    esac
  done
}

menu
