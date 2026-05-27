# OCR RAG UI

Local OCR + RAG document Q&A and compliance analysis app built with PaddleOCR, configurable BGE embedding/reranker models, Qdrant, and a local LLM endpoint compatible with OpenAI Chat Completions or Anthropic Messages.

Default UI language is English. You can switch to Simplified Chinese or Traditional Chinese in `Settings > Language`. The selected language and other custom settings are saved in `app_state.sqlite3`.

## English

### Workflow

```text
Upload PDF / images / Office files
↓
Extract text and run OCR when needed
↓
Chunk the text
↓
Create embeddings with the selected BGE embedding model
↓
Store vectors in local Qdrant or an HTTP/Docker Qdrant service
↓
Ask questions or run compliance analysis
↓
Retrieve relevant chunks
↓
Generate answers through a local LLM endpoint
```

### Features

- Upload single files, multiple files, or folders with subfolders.
- Supported formats: `PDF`, `PNG`, `JPG`, `JPEG`, `WEBP`, `BMP`, `DOCX`, `PPTX`, `XLSX`, `CSV`, `TXT`, `DOC`, `PPT`, `XLS`.
- PDF mixed parsing: direct text extraction plus OCR when needed.
- DOCX / PPTX / XLSX parsing with text, tables, and embedded-image OCR.
- TXT and CSV parsing with automatic encoding detection for common UTF encodings, GB18030, Big5, and related fallbacks.
- Legacy Office files can be converted through LibreOffice.
- PPT/PPTX can be rasterized to page images and OCRed to reduce memory pressure from complex slide objects.
- Oversized XLSX/XLS files can be skipped by row-count threshold.
- Configurable embedding model: `BAAI/bge-m3` or `BAAI/bge-base-zh-v1.5`.
- Optional reranker: `BAAI/bge-reranker-v2-m3` or `BAAI/bge-reranker-base`.
- Qdrant vector store through local files or HTTP/Docker connection.
- Local-to-HTTP Qdrant migration copies existing vectors without re-OCR or re-embedding.
- Multi-turn RAG chat with saved sessions.
- Multi-turn compliance gap analysis with saved sessions.
- Clause-by-clause comparison between regulations and enterprise evidence.
- Missing-materials list for compliance analysis.
- Excel export for compliance reports.
- Background ingestion queue with pause, resume, and stop.
- SHA256 deduplication and same-name changed-file replacement.
- Configurable model cache paths.
- Model status checks and memory-cache release.
- English, Simplified Chinese, and Traditional Chinese UI.

### Requirements

Recommended:

- Python `3.11` or newer
- Windows / macOS / Linux
- A local LLM service that exposes an OpenAI-compatible API or Anthropic Messages-compatible API

Notes:

- `paddlepaddle` installation can differ across CPU, GPU, Apple Silicon, Windows, macOS, and Linux.
- Legacy `.doc/.ppt/.xls` parsing requires LibreOffice.
- OCR and embedding for large files can use a lot of memory. Start with a small batch first.

### Installation

Go to the project folder:

```bash
cd ocr_rag_ui
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS / Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Local LLM Configuration

Copy the environment template:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` if needed:

```env
LLM_BASE_URL=http://127.0.0.1:27292/v1
LLM_API_TYPE=auto
LLM_API_KEY=EMPTY
LLM_MODEL=local-model
LLM_FAST_MODEL=local-model
LLM_THINKING_MODEL=local-model
LLM_FAST_EXTRA_BODY={}
LLM_THINKING_EXTRA_BODY={}
```

You can also configure and save these values in the app under `Settings`.

Compatible backends can include OLMX, LM Studio, Ollama, vLLM, or any service exposing an OpenAI-compatible `/v1/chat/completions` endpoint or an Anthropic-compatible `/v1/messages` endpoint.

### One-Command Installer

The installer asks for English, Simplified Chinese, or Traditional Chinese at the beginning, then asks for an install directory. Press Enter to use the default path `~/DocRAG`. The selected launcher language is saved locally.

GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.sh | bash
```

Gitee:

```bash
curl -fsSL https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.sh | bash
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.ps1 | iex
```

Windows PowerShell Gitee mirror:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.ps1 | iex
```

### Run With Launcher

```bash
bash scripts/start.sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

The launcher includes `Theme Settings`, which writes the selected `light` or `dark` theme to `.streamlit/config.toml` before Streamlit starts. Restart the app after changing the theme.

Open:

```text
http://127.0.0.1:8501
```

### How To Use

1. Open `Settings`, choose the UI language if needed, then configure model paths, download sources, Qdrant, and the local LLM endpoint.
2. Open `Ingest`, choose the document type:
   - Regulations / Policies
   - Enterprise Materials
   - Other Materials
3. Upload files or folders and click `Start Import`.
4. Use `RAG Chat` to ask questions based on ingested materials.
5. Use `Compliance` to compare regulatory requirements with enterprise evidence.
6. Export an Excel report from a compliance answer when needed.

### Project Structure

```text
ocr_rag_ui/
├── app.py                  # Streamlit startup entry
├── VERSION                 # Local application version
├── update/latest.json      # Release metadata template
├── scripts/                # Install, start, update, and uninstall scripts
│   ├── common.sh           # Shared launcher language and path helpers
│   ├── bootstrap.sh        # First-time installer for macOS / Linux
│   ├── bootstrap.ps1       # First-time installer for Windows PowerShell
│   ├── start.sh            # macOS / Linux launcher and update-check menu
│   ├── start.ps1           # Windows PowerShell launcher and update-check menu
│   ├── install.sh          # Install or repair dependencies
│   ├── update.sh           # Git pull and dependency sync
│   └── uninstall.sh        # Cleanup and uninstall menu
├── ocr_rag_app/
│   ├── __init__.py
│   ├── main.py             # Tab assembly and startup wiring
│   ├── services.py         # Shared infrastructure, state, model loading, Qdrant client
│   ├── document_parsing.py # File upload helpers, Office conversion, OCR, parsers
│   ├── llm_clients.py      # OpenAI-compatible and Anthropic-compatible LLM adapters
│   ├── rag_pipeline.py     # Ingestion, retrieval, query rewriting, answer generation
│   ├── rag_utils.py        # Chunking, keyword search, and table helpers
│   └── ui/                 # Streamlit page modules and shared UI components
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── uploads/                # Runtime uploads, not committed
├── qdrant_db/              # Local Qdrant vector store, not committed
├── model_cache/            # Model cache, not committed
└── app_state.sqlite3       # Settings, language, sessions, and tasks, not committed
```

### Models

The app uses:

- PaddleOCR models for images, scanned PDFs, and embedded Office images.
- `BAAI/bge-m3` or `BAAI/bge-base-zh-v1.5` for embeddings.
- Optional `BAAI/bge-reranker-v2-m3` or `BAAI/bge-reranker-base` for reranking retrieved chunks.
- Your configured local LLM endpoint for answer generation. The app does not download Qwen or other chat models by itself.

Model choices and cache paths can be configured in `Settings`. Because the supported embedding models use different vector dimensions, changing the embedding model switches to the matching Qdrant collection. Use `Settings > Vector Store > Embedding Model Conversion` to re-embed stored chunks between supported collections.

### Download Sources And Local Services

`Settings > Models And Paths` lets you configure both cache paths and download or install sources:

- Embedding and reranker models use `sentence-transformers` / Hugging Face compatible downloads. You can choose the official endpoint, `https://hf-mirror.com`, or a custom Hugging Face-compatible endpoint.
- PaddleOCR uses PaddleX official model downloads. You can choose Hugging Face / PaddlePaddle, ModelScope, Baidu AIStudio, or Paddle BOS. When PaddleOCR uses Hugging Face, the same configured Hugging Face endpoint is applied.
- LibreOffice is not a model. It is resolved through the configured `soffice` path, the system package manager, or a custom single-command install command for your own mirror/internal package source.
- Qdrant can run as a local file store or as an HTTP/Docker service.
- The LLM is always provided by your configured OpenAI-compatible or Anthropic-compatible HTTP endpoint. The app does not download chat models.

### Reset And Backup

- `Settings > Reset` clears configurable settings and chat history.
- `Library > Vector Store Backup / Import / Export` can export or restore Qdrant vector-store data.
- `Library > Clear Qdrant Vector Store` clears the vector library and deduplication records.

## 简体中文

### 项目简介

这是一个本地运行的 OCR + RAG 文档问答与合规分析工具，使用 PaddleOCR、可配置 BGE 向量/重排模型、Qdrant，以及 OpenAI Chat Completions 或 Anthropic Messages 兼容本地大模型接口。

界面默认语言是英文。你可以在“配置中心 / Settings > 语言设置 / Language”中切换为简体中文或繁体中文。语言选择和其他自定义配置会保存到 `app_state.sqlite3`，下次打开不用重复填写。

### 流程

```text
上传 PDF / 图片 / Office 文件
↓
解析文本 + 必要时 OCR
↓
文本切分
↓
使用所选 BGE 向量模型生成向量
↓
写入本地 Qdrant 或 HTTP/Docker Qdrant 向量库
↓
用户提问 / 合规分析
↓
检索相关片段
↓
调用本地大模型接口生成回答
```

### 功能

- 支持上传单文件、多文件或文件夹，包含子文件夹。
- 支持格式：`PDF`、`PNG`、`JPG`、`JPEG`、`WEBP`、`BMP`、`DOCX`、`PPTX`、`XLSX`、`CSV`、`TXT`、`DOC`、`PPT`、`XLS`。
- PDF 支持文字提取和 OCR 混合解析。
- DOCX / PPTX / XLSX 支持文本、表格和内嵌图片 OCR。
- TXT 和 CSV 支持自动识别常见 UTF 编码、GB18030、Big5 及相关兜底编码。
- 老版 Office 文件可通过 LibreOffice 转换后解析。
- PPT/PPTX 可先栅格化为页面图像后 OCR，降低复杂幻灯片对象带来的内存压力。
- 可按行数阈值跳过超大 XLSX/XLS 文件。
- 可选择 `BAAI/bge-m3` 或 `BAAI/bge-base-zh-v1.5` 生成文本向量。
- 可选使用 `BAAI/bge-reranker-v2-m3` 或 `BAAI/bge-reranker-base` 做检索结果重排。
- 支持使用本地文件 Qdrant 或 HTTP/Docker Qdrant 保存向量库。
- 支持将本地 Qdrant 向量点迁移到 HTTP/Docker Qdrant，不需要重新 OCR 或重新生成向量。
- 支持多轮检索问答和历史会话保存。
- 支持多轮合规差距分析和历史会话保存。
- 支持按监管条款逐条对照企业资料。
- 支持输出资料不足清单。
- 支持导出合规分析 Excel 报告。
- 支持后台导入队列、暂停、继续、终止。
- 支持 SHA256 去重和同名变更文件替换旧版本。
- 支持配置模型缓存路径。
- 支持模型状态检查和模型缓存释放。
- 支持英文、简体中文、繁体中文界面。

### 运行环境

推荐：

- Python `3.11` 或更高版本
- Windows / macOS / Linux
- 一个提供 OpenAI 兼容接口或 Anthropic Messages 兼容接口的本地大模型服务

注意：

- `paddlepaddle` 在不同系统、CPU/GPU、Apple Silicon 环境下可能需要选择对应安装版本。
- 老版 `.doc/.ppt/.xls` 解析依赖 LibreOffice。
- 大文件 OCR 和 embedding 会占用较多内存，建议先用小批量文件测试。

### 安装

进入项目目录：

```bash
cd ocr_rag_ui
```

创建虚拟环境：

```bash
python -m venv .venv
```

macOS / Linux 激活：

```bash
source .venv/bin/activate
```

Windows PowerShell 激活：

```powershell
.venv\Scripts\activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 配置本地大模型接口

复制配置模板：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

按需编辑 `.env`：

```env
LLM_BASE_URL=http://127.0.0.1:27292/v1
LLM_API_TYPE=auto
LLM_API_KEY=EMPTY
LLM_MODEL=local-model
LLM_FAST_MODEL=local-model
LLM_THINKING_MODEL=local-model
LLM_FAST_EXTRA_BODY={}
LLM_THINKING_EXTRA_BODY={}
```

也可以在应用里的“配置中心 / Settings”页面直接填写并保存。

本地模型服务可以提供 OpenAI 兼容 `/v1/chat/completions` 接口，也可以提供 Anthropic 兼容 `/v1/messages` 接口，例如 OLMX、LM Studio、Ollama、vLLM 等。

### 一条命令安装

安装器一开始会让用户选择英文、简体中文或繁体中文，然后让用户输入安装目录。直接回车会使用默认路径 `~/DocRAG`，并把启动器语言保存在本地。

GitHub：

```bash
curl -fsSL https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.sh | bash
```

Gitee：

```bash
curl -fsSL https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.sh | bash
```

Windows PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.ps1 | iex
```

Windows PowerShell Gitee 镜像：

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.ps1 | iex
```

### 通过启动器启动

```bash
bash scripts/start.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

启动器内置“主题设置”，会在启动 Streamlit 前把选择的浅色或深色主题写入 `.streamlit/config.toml`。修改主题后请重新启动程序。

浏览器打开：

```text
http://127.0.0.1:8501
```

### 使用流程

1. 打开“配置中心 / Settings”，按需选择界面语言，并配置模型路径、下载来源、Qdrant 和本地大模型接口。
2. 打开“上传入库 / Ingest”，选择资料类型：
   - 监管要求 / 规章制度
   - 企业资料
   - 其他资料
3. 上传文件或文件夹，点击“开始导入文件 / Start Import”。
4. 在“检索问答 / RAG Chat”中基于已入库资料提问。
5. 在“合规分析 / Compliance”中让模型结合监管资料和企业资料做差距分析。
6. 如需报告，可在合规分析回答中导出 Excel。

### 目录说明

```text
ocr_rag_ui/
├── app.py                  # Streamlit 启动入口
├── VERSION                 # 本地版本号
├── update/latest.json      # 版本更新信息模板
├── scripts/                # 安装、启动、更新、卸载脚本
│   ├── common.sh           # 启动器语言和路径公共函数
│   ├── bootstrap.sh        # macOS / Linux 首次安装器
│   ├── bootstrap.ps1       # Windows PowerShell 首次安装器
│   ├── start.sh            # macOS / Linux 启动器和更新检查菜单
│   ├── start.ps1           # Windows PowerShell 启动器和更新检查菜单
│   ├── install.sh          # 安装或修复依赖
│   ├── update.sh           # git pull 和依赖同步
│   └── uninstall.sh        # 清理和卸载菜单
├── ocr_rag_app/
│   ├── __init__.py
│   ├── main.py             # Tab 组装和启动编排
│   ├── services.py         # 共享基础设施、状态、模型加载、Qdrant 客户端
│   ├── document_parsing.py # 文件上传辅助、Office 转换、OCR、解析器
│   ├── llm_clients.py      # OpenAI 兼容和 Anthropic 兼容大模型适配
│   ├── rag_pipeline.py     # 入库、检索、问题改写、回答生成
│   ├── rag_utils.py        # 文本切分、关键词检索、表格解析等工具函数
│   └── ui/                 # Streamlit 页面模块和共享 UI 组件
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量示例
├── .gitignore              # Git 忽略规则
├── uploads/                # 运行时上传文件，不提交 Git
├── qdrant_db/              # 本地 Qdrant 向量库，不提交 Git
├── model_cache/            # 模型缓存，不提交 Git
└── app_state.sqlite3       # 配置、语言、会话和任务状态数据库，不提交 Git
```

### 模型说明

本项目会使用：

- PaddleOCR 模型：用于图片、扫描件、PDF 页面和 Office 内嵌图片 OCR。
- `BAAI/bge-m3` 或 `BAAI/bge-base-zh-v1.5`：用于文本向量化。
- `BAAI/bge-reranker-v2-m3` 或 `BAAI/bge-reranker-base`：可选，用于检索结果重排。
- 本地大模型：由你配置的 OpenAI 兼容或 Anthropic 兼容接口提供，本项目不会自动下载 Qwen 或其他聊天模型。

模型选择和保存路径可以在“配置中心 / Settings”页面调整。由于不同向量模型的维度不同，切换向量模型会切换到对应的 Qdrant Collection；如需复用已有 chunk 文本重新生成向量，可在“配置中心 > 向量库连接 > 向量库模型转换”中执行转换。

### 下载来源与本地服务

“配置中心 / Settings > 模型与路径”可以同时配置缓存路径、下载来源和安装来源：

- 向量模型和 Reranker 通过 `sentence-transformers` / Hugging Face 兼容机制下载，可选择官方端点、`https://hf-mirror.com` 或自定义 Hugging Face 兼容端点。
- PaddleOCR 通过 PaddleX 官方模型机制下载，可选择 Hugging Face / PaddlePaddle、ModelScope 魔搭、百度 AIStudio 或 Paddle BOS。PaddleOCR 下载源为 Hugging Face 时，会复用上面配置的 Hugging Face 端点。
- LibreOffice 不是模型。它通过已配置的 `soffice` 路径、系统包管理器或自定义单条安装命令获取，适合配置镜像源或内网安装命令。
- Qdrant 可使用本地文件库，也可连接 HTTP/Docker Qdrant 服务。
- 本地大模型由你配置的 OpenAI 兼容或 Anthropic 兼容 HTTP 接口提供，本项目不会自动下载聊天模型。

### 初始化和备份

- “配置中心 / Settings > 初始化 / Reset”会清空可配置项和历史会话。
- “文档库管理 / Library > 向量库备份 / 导入 / 导出”可以导出或恢复 Qdrant 向量库数据。
- “文档库管理 / Library > 清空 Qdrant 向量库”会清空向量库和去重记录。

## 繁體中文

### 專案簡介

這是一個本地執行的 OCR + RAG 文件問答與合規分析工具，使用 PaddleOCR、可配置 BGE 向量/重排模型、Qdrant，以及 OpenAI Chat Completions 或 Anthropic Messages 相容本地大模型接口。

介面預設語言是英文。你可以在「Settings > Language」中切換為簡體中文或繁體中文。語言選擇和其他自訂配置會保存到 `app_state.sqlite3`，下次打開不用重複填寫。

### 流程

```text
上傳 PDF / 圖片 / Office 文件
↓
解析文字 + 必要時 OCR
↓
文字切分
↓
使用所選 BGE 向量模型生成向量
↓
寫入本地 Qdrant 或 HTTP/Docker Qdrant 向量庫
↓
使用者提問 / 合規分析
↓
檢索相關片段
↓
調用本地大模型接口生成回答
```

### 功能

- 支援上傳單文件、多文件或資料夾，包含子資料夾。
- 支援格式：`PDF`、`PNG`、`JPG`、`JPEG`、`WEBP`、`BMP`、`DOCX`、`PPTX`、`XLSX`、`CSV`、`TXT`、`DOC`、`PPT`、`XLS`。
- PDF 支援文字提取和 OCR 混合解析。
- DOCX / PPTX / XLSX 支援文字、表格和內嵌圖片 OCR。
- TXT 和 CSV 支援自動識別常見 UTF 編碼、GB18030、Big5 及相關兜底編碼。
- 舊版 Office 文件可通過 LibreOffice 轉換後解析。
- PPT/PPTX 可先柵格化為頁面圖像後 OCR，降低複雜投影片物件帶來的記憶體壓力。
- 可按行數閾值跳過超大 XLSX/XLS 文件。
- 可選擇 `BAAI/bge-m3` 或 `BAAI/bge-base-zh-v1.5` 生成文字向量。
- 可選使用 `BAAI/bge-reranker-v2-m3` 或 `BAAI/bge-reranker-base` 做檢索結果重排。
- 支援使用本地文件 Qdrant 或 HTTP/Docker Qdrant 保存向量庫。
- 支援將本地 Qdrant 向量點遷移到 HTTP/Docker Qdrant，不需要重新 OCR 或重新生成向量。
- 支援多輪檢索問答和歷史會話保存。
- 支援多輪合規差距分析和歷史會話保存。
- 支援按監管條款逐條對照企業資料。
- 支援輸出資料不足清單。
- 支援導出合規分析 Excel 報告。
- 支援後台導入隊列、暫停、繼續、終止。
- 支援 SHA256 去重和同名變更文件替換舊版本。
- 支援配置模型快取路徑。
- 支援模型狀態檢查和模型快取釋放。
- 支援英文、簡體中文、繁體中文介面。

### 執行環境

建議：

- Python `3.11` 或更高版本
- Windows / macOS / Linux
- 一個提供 OpenAI 相容接口或 Anthropic Messages 相容接口的本地大模型服務

注意：

- `paddlepaddle` 在不同系統、CPU/GPU、Apple Silicon 環境下可能需要選擇對應安裝版本。
- 舊版 `.doc/.ppt/.xls` 解析依賴 LibreOffice。
- 大文件 OCR 和 embedding 會佔用較多記憶體，建議先用小批量文件測試。

### 安裝

進入專案目錄：

```bash
cd ocr_rag_ui
```

建立虛擬環境：

```bash
python -m venv .venv
```

macOS / Linux 啟用：

```bash
source .venv/bin/activate
```

Windows PowerShell 啟用：

```powershell
.venv\Scripts\activate
```

安裝依賴：

```bash
pip install -r requirements.txt
```

### 配置本地大模型接口

複製配置模板：

```bash
cp .env.example .env
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
```

按需編輯 `.env`：

```env
LLM_BASE_URL=http://127.0.0.1:27292/v1
LLM_API_TYPE=auto
LLM_API_KEY=EMPTY
LLM_MODEL=local-model
LLM_FAST_MODEL=local-model
LLM_THINKING_MODEL=local-model
LLM_FAST_EXTRA_BODY={}
LLM_THINKING_EXTRA_BODY={}
```

也可以在應用裡的「Settings」頁面直接填寫並保存。

本地模型服務可以提供 OpenAI 相容 `/v1/chat/completions` 接口，也可以提供 Anthropic 相容 `/v1/messages` 接口，例如 OLMX、LM Studio、Ollama、vLLM 等。

### 一條命令安裝

安裝器一開始會讓使用者選擇英文、簡體中文或繁體中文，然後讓使用者輸入安裝目錄。直接 Enter 會使用預設路徑 `~/DocRAG`，並把啟動器語言保存在本地。

GitHub：

```bash
curl -fsSL https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.sh | bash
```

Gitee：

```bash
curl -fsSL https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.sh | bash
```

Windows PowerShell：

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://raw.githubusercontent.com/agenius666/Ocr_Rag_UI/main/scripts/bootstrap.ps1 | iex
```

Windows PowerShell Gitee 鏡像：

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force; irm https://gitee.com/agenius66/ocr_-rag_-ui/raw/master/scripts/bootstrap.ps1 | iex
```

### 通過啟動器啟動

```bash
bash scripts/start.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

啟動器內建「主題設定」，會在啟動 Streamlit 前把選擇的淺色或深色主題寫入 `.streamlit/config.toml`。修改主題後請重新啟動程式。

瀏覽器打開：

```text
http://127.0.0.1:8501
```

### 使用流程

1. 打開 `Settings`，按需選擇介面語言，並配置模型路徑、下載來源、Qdrant 和本地大模型接口。
2. 打開 `Ingest`，選擇資料類型：
   - 監管要求 / 規章制度
   - 企業資料
   - 其他資料
3. 上傳文件或資料夾，點擊 `Start Import`。
4. 在 `RAG Chat` 中基於已入庫資料提問。
5. 在 `Compliance` 中讓模型結合監管資料和企業資料做差距分析。
6. 如需報告，可在合規分析回答中導出 Excel。

### 目錄說明

```text
ocr_rag_ui/
├── app.py                  # Streamlit 啟動入口
├── VERSION                 # 本地版本號
├── update/latest.json      # 版本更新資訊模板
├── scripts/                # 安裝、啟動、更新、卸載腳本
│   ├── common.sh           # 啟動器語言和路徑公共函數
│   ├── bootstrap.sh        # macOS / Linux 首次安裝器
│   ├── bootstrap.ps1       # Windows PowerShell 首次安裝器
│   ├── start.sh            # macOS / Linux 啟動器和更新檢查選單
│   ├── start.ps1           # Windows PowerShell 啟動器和更新檢查選單
│   ├── install.sh          # 安裝或修復依賴
│   ├── update.sh           # git pull 和依賴同步
│   └── uninstall.sh        # 清理和卸載選單
├── ocr_rag_app/
│   ├── __init__.py
│   ├── main.py             # Tab 組裝和啟動編排
│   ├── services.py         # 共享基礎設施、狀態、模型載入、Qdrant 客戶端
│   ├── document_parsing.py # 文件上傳輔助、Office 轉換、OCR、解析器
│   ├── llm_clients.py      # OpenAI 相容和 Anthropic 相容大模型適配
│   ├── rag_pipeline.py     # 入庫、檢索、問題改寫、回答生成
│   ├── rag_utils.py        # 文字切分、關鍵詞檢索、表格解析等工具函數
│   └── ui/                 # Streamlit 頁面模組和共享 UI 元件
├── requirements.txt        # Python 依賴
├── .env.example            # 環境變數示例
├── .gitignore              # Git 忽略規則
├── uploads/                # 執行時上傳文件，不提交 Git
├── qdrant_db/              # 本地 Qdrant 向量庫，不提交 Git
├── model_cache/            # 模型快取，不提交 Git
└── app_state.sqlite3       # 配置、語言、會話和任務狀態資料庫，不提交 Git
```

### 模型說明

本專案會使用：

- PaddleOCR 模型：用於圖片、掃描件、PDF 頁面和 Office 內嵌圖片 OCR。
- `BAAI/bge-m3` 或 `BAAI/bge-base-zh-v1.5`：用於文字向量化。
- `BAAI/bge-reranker-v2-m3` 或 `BAAI/bge-reranker-base`：可選，用於檢索結果重排。
- 本地大模型：由你配置的 OpenAI 相容或 Anthropic 相容接口提供，本專案不會自動下載 Qwen 或其他聊天模型。

模型選擇和保存路徑可以在 `Settings` 頁面調整。由於不同向量模型的維度不同，切換向量模型會切換到對應的 Qdrant Collection；如需複用既有 chunk 文字重新生成向量，可在「配置中心 > 向量庫連線 > 向量庫模型轉換」中執行轉換。

### 下載來源與本地服務

`Settings > Models And Paths` 可以同時配置快取路徑、下載來源和安裝來源：

- 向量模型和 Reranker 透過 `sentence-transformers` / Hugging Face 相容機制下載，可選擇官方端點、`https://hf-mirror.com` 或自訂 Hugging Face 相容端點。
- PaddleOCR 透過 PaddleX 官方模型機制下載，可選擇 Hugging Face / PaddlePaddle、ModelScope 魔搭、百度 AIStudio 或 Paddle BOS。PaddleOCR 下載源為 Hugging Face 時，會複用上面配置的 Hugging Face 端點。
- LibreOffice 不是模型。它透過已配置的 `soffice` 路徑、系統套件管理器或自訂單條安裝命令取得，適合配置鏡像源或內網安裝命令。
- Qdrant 可使用本地文件庫，也可連接 HTTP/Docker Qdrant 服務。
- 本地大模型由你配置的 OpenAI 相容或 Anthropic 相容 HTTP 接口提供，本專案不會自動下載聊天模型。

### 初始化和備份

- `Settings > Reset` 會清空可配置項和歷史會話。
- `Library > Vector Store Backup / Import / Export` 可以導出或恢復 Qdrant 向量庫數據。
- `Library > Clear Qdrant Vector Store` 會清空向量庫和去重記錄。
