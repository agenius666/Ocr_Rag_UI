# OCR RAG UI

Local OCR + RAG document Q&A and compliance analysis app built with PaddleOCR, BGE-M3, Qdrant, and an OpenAI-compatible local LLM endpoint.

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
Create embeddings with BAAI/bge-m3
↓
Store vectors in local Qdrant
↓
Ask questions or run compliance analysis
↓
Retrieve relevant chunks
↓
Generate answers through an OpenAI-compatible local LLM endpoint
```

### Features

- Upload single files, multiple files, or folders with subfolders.
- Supported formats: `PDF`, `PNG`, `JPG`, `JPEG`, `WEBP`, `BMP`, `DOCX`, `PPTX`, `XLSX`, `DOC`, `PPT`, `XLS`.
- PDF mixed parsing: direct text extraction plus OCR when needed.
- DOCX / PPTX / XLSX parsing with text, tables, and embedded-image OCR.
- Legacy Office files can be converted through LibreOffice.
- `BAAI/bge-m3` embeddings.
- Optional `BAAI/bge-reranker-v2-m3` reranking.
- Local Qdrant vector store.
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

- Python `3.10` or `3.11`
- Windows / macOS / Linux
- A local LLM service that exposes an OpenAI-compatible API

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
LLM_API_KEY=EMPTY
LLM_MODEL=local-model
LLM_FAST_MODEL=local-model
LLM_THINKING_MODEL=local-model
LLM_FAST_EXTRA_BODY={}
LLM_THINKING_EXTRA_BODY={}
```

You can also configure and save these values in the app under `Settings`.

Compatible backends can include OLMX, LM Studio, Ollama, vLLM, or any service exposing an OpenAI-compatible `/v1/chat/completions` endpoint.

### Run

```bash
streamlit run app.py
```

If `streamlit` is not found, run it from the virtual environment:

macOS / Linux:

```bash
./.venv/bin/streamlit run app.py
```

Windows:

```powershell
.venv\Scripts\streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### How To Use

1. Open `Settings`, choose the UI language if needed, and configure the local LLM endpoint.
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
├── app.py                  # Streamlit app
├── rag_utils.py            # Chunking, keyword search, and table helpers
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
├── .streamlit/
│   └── config.toml         # Streamlit config
├── uploads/                # Runtime uploads, not committed
├── qdrant_db/              # Local Qdrant vector store, not committed
├── model_cache/            # Model cache, not committed
└── app_state.sqlite3       # Settings, language, sessions, and tasks, not committed
```

### Models

The app uses:

- PaddleOCR models for images, scanned PDFs, and embedded Office images.
- `BAAI/bge-m3` for embeddings.
- Optional `BAAI/bge-reranker-v2-m3` for reranking retrieved chunks.
- Your configured local LLM endpoint for answer generation. The app does not download Qwen or other chat models by itself.

Model cache paths can be configured in `Settings`.

### Reset And Backup

- `Settings > Reset` clears configurable settings and chat history.
- `Library > Vector Store Backup / Import / Export` can export or restore Qdrant data plus `app_state.sqlite3`.
- `Library > Clear Qdrant Vector Store` clears the vector library and deduplication records.

## 中文

### 项目简介

这是一个本地运行的 OCR + RAG 文档问答与合规分析工具，使用 PaddleOCR、BGE-M3、Qdrant 和 OpenAI 兼容本地大模型接口。

界面默认语言是英文。你可以在“模型配置 / Settings > 语言设置 / Language”中切换为简体中文或繁体中文。语言选择和其他自定义配置会保存到 `app_state.sqlite3`，下次打开不用重复填写。

### 流程

```text
上传 PDF / 图片 / Office 文件
↓
解析文本 + 必要时 OCR
↓
文本切分
↓
BAAI/bge-m3 生成向量
↓
写入本地 Qdrant 向量库
↓
用户提问 / 合规分析
↓
检索相关片段
↓
调用 OpenAI 兼容本地大模型接口生成回答
```

### 功能

- 支持上传单文件、多文件或文件夹，包含子文件夹。
- 支持格式：`PDF`、`PNG`、`JPG`、`JPEG`、`WEBP`、`BMP`、`DOCX`、`PPTX`、`XLSX`、`DOC`、`PPT`、`XLS`。
- PDF 支持文字提取和 OCR 混合解析。
- DOCX / PPTX / XLSX 支持文本、表格和内嵌图片 OCR。
- 老版 Office 文件可通过 LibreOffice 转换后解析。
- 使用 `BAAI/bge-m3` 生成文本向量。
- 可选使用 `BAAI/bge-reranker-v2-m3` 做检索结果重排。
- 使用本地 Qdrant 保存向量库。
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

- Python `3.10` 或 `3.11`
- Windows / macOS / Linux
- 一个提供 OpenAI 兼容接口的本地大模型服务

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
LLM_API_KEY=EMPTY
LLM_MODEL=local-model
LLM_FAST_MODEL=local-model
LLM_THINKING_MODEL=local-model
LLM_FAST_EXTRA_BODY={}
LLM_THINKING_EXTRA_BODY={}
```

也可以在应用里的“模型配置 / Settings”页面直接填写并保存。

只要你的本地模型服务提供 OpenAI 兼容接口即可，例如 OLMX、LM Studio、Ollama、vLLM 等。

### 启动

```bash
streamlit run app.py
```

如果系统找不到 `streamlit`，使用虚拟环境里的命令：

macOS / Linux：

```bash
./.venv/bin/streamlit run app.py
```

Windows：

```powershell
.venv\Scripts\streamlit run app.py
```

浏览器打开：

```text
http://localhost:8501
```

### 使用流程

1. 打开“模型配置 / Settings”，按需选择界面语言，并确认本地大模型接口可用。
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
├── app.py                  # Streamlit 主应用
├── rag_utils.py            # 文本切分、关键词检索、表格解析等工具函数
├── requirements.txt        # Python 依赖
├── .env.example            # 环境变量示例
├── .gitignore              # Git 忽略规则
├── .streamlit/
│   └── config.toml         # Streamlit 配置
├── uploads/                # 运行时上传文件，不提交 Git
├── qdrant_db/              # 本地 Qdrant 向量库，不提交 Git
├── model_cache/            # 模型缓存，不提交 Git
└── app_state.sqlite3       # 配置、语言、会话和任务状态数据库，不提交 Git
```

### 模型说明

本项目会使用：

- PaddleOCR 模型：用于图片、扫描件、PDF 页面和 Office 内嵌图片 OCR。
- `BAAI/bge-m3`：用于文本向量化。
- `BAAI/bge-reranker-v2-m3`：可选，用于检索结果重排。
- 本地大模型：由你配置的 OpenAI 兼容接口提供，本项目不会自动下载 Qwen 或其他聊天模型。

模型保存路径可以在“模型配置 / Settings”页面调整。

### 初始化和备份

- “模型配置 / Settings > 初始化 / Reset”会清空可配置项和历史会话。
- “文档库管理 / Library > 向量库备份 / 导入 / 导出”可以导出或恢复 Qdrant 数据和 `app_state.sqlite3`。
- “文档库管理 / Library > 清空 Qdrant 向量库”会清空向量库和去重记录。
