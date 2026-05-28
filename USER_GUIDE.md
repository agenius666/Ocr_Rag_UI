# OCR RAG UI User Guide

This guide is provided in English, Simplified Chinese, and Traditional Chinese.

## English

### 1. What This App Does

OCR RAG UI helps you build a local document knowledge base:

1. Upload policies, regulatory requirements, enterprise materials, PDFs, images, Office files, CSV, or TXT.
2. Parse text with structured extraction and OCR when needed.
3. Generate embeddings with the selected BGE embedding model.
4. Store vectors in Qdrant.
5. Ask questions, run compliance gap analysis, or write LLM results back to Excel.

### 2. Start The App

If you installed with the launcher scripts:

- macOS: double-click `start.command`
- Linux: run `bash start.sh`
- Windows: run the generated PowerShell launcher

Manual start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open:

```text
http://127.0.0.1:8501
```

### 3. First-Time Settings

Open **Settings**:

- Language: choose English, Simplified Chinese, or Traditional Chinese.
- Models and paths: choose the embedding/reranker model and set cache locations for PaddleOCR, BGE models, rerankers, and LibreOffice.
- Download and install sources: choose the Hugging Face endpoint for embedding/reranker models, the PaddleOCR model source, and the LibreOffice install source or custom single-command installer.
- Vector store: choose local Qdrant or HTTP/Docker Qdrant.
- Vector store conversion: re-embed stored chunks between `BAAI/bge-m3` and `BAAI/bge-base-zh-v1.5` when you change embedding dimensions.
- Local LLM: configure the OpenAI-compatible or Anthropic-compatible endpoint, API key, model names, and optional `extra_body`.

Settings are saved locally in `app_state.sqlite3`.

### 4. Ingest Documents

Open **Ingest**:

- Choose file upload or folder upload.
- Select document type: regulations/policies, enterprise materials, or other materials.
- Review **Advanced Ingestion Parameters** before processing large files.
- Large PDF, PPT, phone photos, and spreadsheets may use significant memory.
- Duplicate files are skipped by SHA256.

Supported formats include:

```text
PDF, PNG, JPG, JPEG, WEBP, BMP, DOCX, PPTX, XLSX, CSV, TXT, DOC, PPT, XLS
```

Legacy Office files require LibreOffice or system conversion support.

### 5. RAG Chat

Open **RAG Chat**:

- Ask questions about ingested materials.
- Use retrieval settings to control search scope, top-k chunks, distance threshold, hybrid search, reranker, and context turns.
- The answer guidance structure can be edited and saved.

Short casual questions can use general LLM fallback when no materials are retrieved.

### 6. Compliance Analysis

Open **Compliance**:

- Ask compliance or gap-analysis questions.
- The app retrieves regulatory evidence and enterprise evidence separately.
- You can require minimum evidence counts, enable clause-by-clause comparison, and request missing-material lists.
- Results can include structured analysis tables when the model returns Markdown correctly.

### 7. Batch Excel Analysis

Open **Batch Analysis**:

1. Upload one `.xlsx` file.
2. Set the header row.
3. Write a row prompt template, for example:

```text
Analyze supplier {B} against compliance requirement {C}, using the enterprise materials.
```

4. Configure output columns and descriptions.
5. Preview the generated prompt and JSON template.
6. Choose rows, skip rules, retrieval scope, and LLM mode.
7. Start processing. Each row is processed independently and written back to the matching Excel cells.

Use row ranges such as:

```text
2-100
2,5,9-20
```

Leave the row range empty to process all data rows after the header.

### 8. Distillation Data Generation (Advanced)

Open **Distillation Data Generation (Advanced)**:

- Choose `SFT Q&A Data` to generate `instruction/input/output` records.
- Choose `Preference Data chosen/rejected` to generate `prompt/chosen/rejected` records.
- Set target count, samples per batch, chunks per batch, timeout, retry count, and data scope.
- Failed batches are logged and can be skipped while the task continues.
- Export generated records as JSONL for training tools and Excel for manual review.

### 9. Document Library

Open **Document Library**:

- View chunk counts.
- Load file summaries and deduplication records only when needed.
- Export or import vector-store backups.
- Clear the Qdrant vector store only after confirming the secondary checkbox.

### 10. Performance Advice

Recommended defaults:

- Chunk size: 600
- Chunk overlap: 100
- RAG top-k: 3 to 5
- Compliance top-k: 5 to 10 per evidence type
- Image preprocessing: Auto
- Use Qdrant Docker/HTTP when the collection is large

For large files, prefer background ingestion and avoid loading too many huge spreadsheets at once.

### 11. Troubleshooting

- If the local LLM returns 502, check the model server first.
- If Qdrant local warns about large collections, switch to Qdrant Docker or HTTP mode.
- If OCR memory spikes, use lower-memory image preprocessing, PPT rasterization OCR, and PDF mixed mode.
- If upload or ingestion is slow, keep the recent-task panel open and let the background task finish.

---

## 简体中文

### 1. 这个应用做什么

OCR RAG UI 用于搭建本地文档知识库：

1. 上传制度、监管要求、企业资料、PDF、图片、Office 文件、CSV 或 TXT。
2. 通过结构化解析和 OCR 提取文本。
3. 使用所选 BGE 向量模型生成向量。
4. 写入 Qdrant 向量库。
5. 进行检索问答、合规差距分析，或把大模型结果回写到 Excel。

### 2. 启动应用

如果使用启动脚本安装：

- macOS：双击 `start.command`
- Linux：执行 `bash start.sh`
- Windows：执行生成的 PowerShell 启动器

手动启动：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

打开：

```text
http://127.0.0.1:8501
```

### 3. 首次配置

打开 **配置中心**：

- 语言设置：选择 English、简体中文或繁體中文。
- 模型与路径：选择向量模型/重排模型，并设置 PaddleOCR、BGE 模型、重排模型和 LibreOffice 路径。
- 下载与安装源：设置向量模型/Reranker 使用的 Hugging Face 端点、PaddleOCR 模型来源，以及 LibreOffice 安装来源或自定义单条安装命令。
- 向量库连接：选择本地 Qdrant 或 HTTP/Docker Qdrant。
- 向量库模型转换：在 `BAAI/bge-m3` 和 `BAAI/bge-base-zh-v1.5` 之间重新向量化已有 chunk 文本，用于切换不同向量维度。
- 本地大模型：配置 OpenAI 兼容或 Anthropic 兼容接口、API Key、模型名和可选 `extra_body`。

配置会保存在本地 `app_state.sqlite3`。

### 4. 上传入库

打开 **上传入库**：

- 选择文件上传或文件夹上传。
- 选择资料类型：监管要求/规章制度、企业资料或其他资料。
- 处理大文件前请查看 **高级入库参数**。
- 大 PDF、PPT、手机照片和大型表格可能占用较多内存。
- 重复文件会按 SHA256 自动跳过。

支持格式：

```text
PDF, PNG, JPG, JPEG, WEBP, BMP, DOCX, PPTX, XLSX, CSV, TXT, DOC, PPT, XLS
```

老版 Office 文件需要 LibreOffice 或系统转换能力。

### 5. 检索问答

打开 **检索问答**：

- 向已入库资料提问。
- 可设置检索范围、召回片段数量、距离阈值、混合检索、重排模型和上下文轮数。
- 可以编辑并保存回答引导结构。

没有检索到资料时，普通寒暄类问题可以启用本地大模型通用回复。

### 6. 合规分析

打开 **合规分析**：

- 输入合规或差距分析问题。
- 系统会分别检索监管证据和企业证据。
- 可设置最少证据数、按条款逐条对照、资料不足清单等。
- 如果模型返回规范 Markdown，可以渲染为结构化表格。

### 7. 批量 Excel 分析

打开 **批量分析**：

1. 上传一个 `.xlsx` 文件。
2. 设置表头所在行。
3. 编写行级 Prompt 模板，例如：

```text
请根据供应商【{B}】的合规要求【{C}】，结合企业资料进行分析。
```

4. 配置输出列和输出说明。
5. 查看生成的 Prompt 与 JSON 模板。
6. 选择处理行号、跳过规则、检索范围和回答模式。
7. 开始处理。每一行都会独立检索、独立调用模型，并写回对应单元格。

行号范围示例：

```text
2-100
2,5,9-20
```

留空表示处理表头下一行到最后一行。

### 8. 蒸馏数据生成（高级）

打开 **蒸馏数据生成（高级）**：

- 选择 `SFT 问答数据` 可生成 `instruction/input/output` 记录。
- 选择 `偏好数据 chosen/rejected` 可生成 `prompt/chosen/rejected` 记录。
- 可设置目标数量、每批生成数量、每批 chunk 数量、超时时间、重试次数和资料范围。
- 单批失败会记录日志，可跳过失败批次并继续后续生成。
- 生成结果可导出 JSONL 给训练工具使用，也可导出 Excel 进行人工审核。

### 9. 文档库管理

打开 **文档库管理**：

- 查看 chunk 数量。
- 按需加载文件摘要和去重记录。
- 导出或导入向量库备份。
- 清空 Qdrant 向量库前需要勾选二次确认。

### 10. 性能建议

推荐默认值：

- Chunk 大小：600
- Chunk 重叠：100
- 检索问答 top-k：3 到 5
- 合规分析 top-k：每类证据 5 到 10
- 图片预处理：自动
- 大型向量库建议使用 Qdrant Docker/HTTP 模式

处理大文件时建议使用后台入库，不要一次性导入过多超大表格。

### 11. 常见问题

- 本地大模型返回 502：优先检查模型服务是否正常。
- Qdrant Local 提示集合过大：建议切换到 Qdrant Docker 或 HTTP 模式。
- OCR 内存占用过高：使用低内存图片预处理、PPT 栅格化 OCR、PDF 混合模式。
- 上传或入库较慢：保持最近任务面板打开，等待后台任务完成。

---

## 繁體中文

### 1. 這個應用做什麼

OCR RAG UI 用於建立本機文件知識庫：

1. 上傳制度、監管要求、企業資料、PDF、圖片、Office 文件、CSV 或 TXT。
2. 透過結構化解析和 OCR 提取文字。
3. 使用所選 BGE 向量模型生成向量。
4. 寫入 Qdrant 向量庫。
5. 進行檢索問答、合規差距分析，或把大模型結果回寫到 Excel。

### 2. 啟動應用

如果使用啟動腳本安裝：

- macOS：雙擊 `start.command`
- Linux：執行 `bash start.sh`
- Windows：執行生成的 PowerShell 啟動器

手動啟動：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

開啟：

```text
http://127.0.0.1:8501
```

### 3. 首次配置

開啟 **配置中心**：

- 語言設定：選擇 English、简体中文 或 繁體中文。
- 模型與路徑：選擇向量模型/重排模型，並設定 PaddleOCR、BGE 模型、重排模型和 LibreOffice 路徑。
- 下載與安裝源：設定向量模型/Reranker 使用的 Hugging Face 端點、PaddleOCR 模型來源，以及 LibreOffice 安裝來源或自訂單條安裝命令。
- 向量庫連線：選擇本機 Qdrant 或 HTTP/Docker Qdrant。
- 向量庫模型轉換：在 `BAAI/bge-m3` 和 `BAAI/bge-base-zh-v1.5` 之間重新向量化既有 chunk 文字，用於切換不同向量維度。
- 本地大模型：配置 OpenAI 相容或 Anthropic 相容接口、API Key、模型名和可選 `extra_body`。

配置會保存在本機 `app_state.sqlite3`。

### 4. 上傳入庫

開啟 **上傳入庫**：

- 選擇文件上傳或資料夾上傳。
- 選擇資料類型：監管要求/規章制度、企業資料或其他資料。
- 處理大型文件前請查看 **進階入庫參數**。
- 大型 PDF、PPT、手機照片和大型表格可能占用較多記憶體。
- 重複文件會按 SHA256 自動跳過。

支援格式：

```text
PDF, PNG, JPG, JPEG, WEBP, BMP, DOCX, PPTX, XLSX, CSV, TXT, DOC, PPT, XLS
```

舊版 Office 文件需要 LibreOffice 或系統轉換能力。

### 5. 檢索問答

開啟 **檢索問答**：

- 向已入庫資料提問。
- 可設定檢索範圍、召回片段數量、距離閾值、混合檢索、重排模型和上下文輪數。
- 可以編輯並保存回答引導結構。

沒有檢索到資料時，普通寒暄類問題可以啟用本地大模型通用回覆。

### 6. 合規分析

開啟 **合規分析**：

- 輸入合規或差距分析問題。
- 系統會分別檢索監管證據和企業證據。
- 可設定最少證據數、按條款逐條對照、資料不足清單等。
- 如果模型返回規範 Markdown，可以渲染為結構化表格。

### 7. 批次 Excel 分析

開啟 **批次分析**：

1. 上傳一個 `.xlsx` 文件。
2. 設定表頭所在列。
3. 編寫列級 Prompt 模板，例如：

```text
請根據供應商【{B}】的合規要求【{C}】，結合企業資料進行分析。
```

4. 配置輸出欄和輸出說明。
5. 查看生成的 Prompt 與 JSON 模板。
6. 選擇處理列號、跳過規則、檢索範圍和回答模式。
7. 開始處理。每一列都會獨立檢索、獨立調用模型，並寫回對應儲存格。

列號範圍示例：

```text
2-100
2,5,9-20
```

留空表示處理表頭下一列到最後一列。

### 8. 蒸餾資料生成（進階）

開啟 **蒸餾資料生成（進階）**：

- 選擇 `SFT 問答資料` 可生成 `instruction/input/output` 記錄。
- 選擇 `偏好資料 chosen/rejected` 可生成 `prompt/chosen/rejected` 記錄。
- 可設定目標數量、每批生成數量、每批 chunk 數量、逾時時間、重試次數和資料範圍。
- 單批失敗會記錄日誌，可跳過失敗批次並繼續後續生成。
- 生成結果可匯出 JSONL 給訓練工具使用，也可匯出 Excel 進行人工審核。

### 9. 文件庫管理

開啟 **文件庫管理**：

- 查看 chunk 數量。
- 按需載入文件摘要和去重記錄。
- 匯出或匯入向量庫備份。
- 清空 Qdrant 向量庫前需要勾選二次確認。

### 10. 效能建議

推薦預設值：

- Chunk 大小：600
- Chunk 重疊：100
- 檢索問答 top-k：3 到 5
- 合規分析 top-k：每類證據 5 到 10
- 圖片預處理：自動
- 大型向量庫建議使用 Qdrant Docker/HTTP 模式

處理大型文件時建議使用背景入庫，不要一次性匯入過多超大型表格。

### 11. 常見問題

- 本地大模型返回 502：優先檢查模型服務是否正常。
- Qdrant Local 提示集合過大：建議切換到 Qdrant Docker 或 HTTP 模式。
- OCR 記憶體占用過高：使用低記憶體圖片預處理、PPT 柵格化 OCR、PDF 混合模式。
- 上傳或入庫較慢：保持最近任務面板開啟，等待背景任務完成。
