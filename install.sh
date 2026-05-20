#!/usr/bin/env bash
set -euo pipefail

# Replace these placeholder URLs with your real repositories before distribution.
GITHUB_REPO_URL="https://github.com/example/ocr-rag-ui.git"
GITEE_REPO_URL="https://gitee.com/example/ocr-rag-ui.git"
DEFAULT_PROJECT_DIR="ocr_rag_ui"

LANGUAGE="en"
REPO_URL=""

choose_language() {
  echo "Select language / 选择语言 / 選擇語言:"
  echo "1) English"
  echo "2) 简体中文"
  echo "3) 繁體中文"
  read -r -p "1/2/3 [1]: " choice
  case "${choice:-1}" in
    2) LANGUAGE="zh_CN" ;;
    3) LANGUAGE="zh_TW" ;;
    *) LANGUAGE="en" ;;
  esac
}

msg() {
  local en="$1"
  local zh_cn="$2"
  local zh_tw="$3"
  case "$LANGUAGE" in
    zh_CN) printf '%s\n' "$zh_cn" ;;
    zh_TW) printf '%s\n' "$zh_tw" ;;
    *) printf '%s\n' "$en" ;;
  esac
}

detect_python() {
  if command -v python3 >/dev/null 2>&1; then
    printf 'python3'
  elif command -v python >/dev/null 2>&1; then
    printf 'python'
  else
    msg "Python was not found. Please install Python 3.10+ first." "未找到 Python，请先安装 Python 3.10 或更高版本。" "未找到 Python，請先安裝 Python 3.10 或更高版本。"
    exit 1
  fi
}

venv_python() {
  if [ -x ".venv/bin/python" ]; then
    printf './.venv/bin/python'
  elif [ -x ".venv/Scripts/python.exe" ]; then
    printf './.venv/Scripts/python.exe'
  else
    msg "Virtual environment Python was not found." "未找到虚拟环境中的 Python。" "未找到虛擬環境中的 Python。"
    exit 1
  fi
}

streamlit_command() {
  if [ -x ".venv/bin/streamlit" ]; then
    printf './.venv/bin/streamlit run app.py'
  elif [ -x ".venv/Scripts/streamlit.exe" ]; then
    printf './.venv/Scripts/streamlit.exe run app.py'
  else
    printf 'streamlit run app.py'
  fi
}

choose_repo_url() {
  msg "Choose code source:" "选择代码来源：" "選擇程式碼來源："
  echo "1) GitHub: $GITHUB_REPO_URL"
  echo "2) Gitee : $GITEE_REPO_URL"
  read -r -p "1/2 [1]: " choice
  if [ "${choice:-1}" = "2" ]; then
    REPO_URL="$GITEE_REPO_URL"
  else
    REPO_URL="$GITHUB_REPO_URL"
  fi
}

prepare_project_dir() {
  if [ -f "app.py" ] && [ -f "requirements.txt" ]; then
    msg "Using the current project directory." "使用当前项目目录。" "使用目前專案目錄。"
    return
  fi

  choose_repo_url
  read -r -p "$(msg "Project directory [ocr_rag_ui]: " "项目目录 [ocr_rag_ui]：" "專案目錄 [ocr_rag_ui]：")" project_dir
  project_dir="${project_dir:-$DEFAULT_PROJECT_DIR}"

  if [ -d "$project_dir/.git" ]; then
    msg "Existing repository found. Pulling latest code..." "发现已有仓库，正在拉取最新代码..." "發現已有倉庫，正在拉取最新程式碼..."
    cd "$project_dir"
    git pull --ff-only
  elif [ -d "$project_dir" ]; then
    msg "Target directory already exists but is not a Git repository. Please move it or choose another directory." "目标目录已存在但不是 Git 仓库，请移动它或选择其他目录。" "目標目錄已存在但不是 Git 倉庫，請移動它或選擇其他目錄。"
    exit 1
  else
    msg "Cloning project..." "正在拉取项目代码..." "正在拉取專案程式碼..."
    git clone "$REPO_URL" "$project_dir"
    cd "$project_dir"
  fi
}

install_dependencies() {
  local python_cmd
  local venv_py
  python_cmd="$(detect_python)"
  msg "Creating virtual environment..." "正在创建虚拟环境..." "正在建立虛擬環境..."
  "$python_cmd" -m venv .venv
  venv_py="$(venv_python)"

  msg "Upgrading pip..." "正在升级 pip..." "正在升級 pip..."
  "$venv_py" -m pip install --upgrade pip

  msg "Installing project dependencies. This can take a while because OCR and vector models require native packages." "正在安装项目依赖。OCR 和向量模型依赖较重，可能需要一些时间。" "正在安裝專案依賴。OCR 和向量模型依賴較重，可能需要一些時間。"
  "$venv_py" -m pip install -r requirements.txt
}

main() {
  choose_language
  prepare_project_dir
  install_dependencies
  msg "Installation completed." "安装完成。" "安裝完成。"
  msg "Start command:" "启动命令：" "啟動命令："
  streamlit_command
  echo
}

main "$@"
