"""Upload and ingestion page UI.
上传入库页面 UI。
"""

from ..services import *
from .components import *


def render_upload_tab() -> None:
    st.subheader("上传文件并写入向量库")
    upload_mode_options = ["文件 / 多文件", "文件夹（含子文件夹）"]
    saved_upload_mode = get_config_value("upload_mode_label", upload_mode_options[0])
    if saved_upload_mode not in upload_mode_options:
        saved_upload_mode = upload_mode_options[0]
    upload_mode_label = st.radio(
        "上传方式",
        upload_mode_options,
        index=upload_mode_options.index(saved_upload_mode),
        horizontal=True,
        key="upload_mode_label",
    )
    set_config_value("upload_mode_label", upload_mode_label)

    accept_multiple_files = "directory" if upload_mode_label == "文件夹（含子文件夹）" else True
    upload_button_label = translate_text("选择文件夹" if accept_multiple_files == "directory" else "选择文件")
    st.markdown(
        f"""
        <style>
        section[data-testid="stFileUploaderDropzone"] button p {{
            display: none !important;
        }}
        section[data-testid="stFileUploaderDropzone"] button::after {{
            content: "{upload_button_label}";
            font-size: 1rem;
            line-height: 1.5;
            margin-left: 0.45rem;
        }}
        section[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderFileLimit"],
        section[data-testid="stFileUploaderDropzone"] [data-testid="stFileUploaderDropzoneInstructions"],
        section[data-testid="stFileUploaderDropzone"] small {{
            display: none !important;
        }}
        div[data-testid="stFileUploader"] div[data-testid="stFileUploaderFile"],
        section[data-testid="stFileUploaderDropzone"] div[data-testid="stFileUploaderFile"] {{
            display: none !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    uploaded_items = st.file_uploader(
        "上传文件或文件夹",
        accept_multiple_files=accept_multiple_files,
        key=f"source_uploader_{accept_multiple_files}",
        help=localized_text(
            f"Supported formats: {SUPPORTED_TYPE_LABEL}. Folder mode includes files in subfolders.",
            f"支持格式：{SUPPORTED_TYPE_LABEL}。文件夹模式会包含子文件夹中的文件。",
            f"支援格式：{SUPPORTED_TYPE_LABEL}。資料夾模式會包含子資料夾中的文件。",
        ),
    )
    uploaded_files = uploaded_items or []
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]
    st.caption(
        localized_text(
            f"Supported formats: {SUPPORTED_TYPE_LABEL}. Unsupported files will be listed in batch results.",
            f"支持格式：{SUPPORTED_TYPE_LABEL}。不支持的文件会在批量处理结果中列出。",
            f"支援格式：{SUPPORTED_TYPE_LABEL}。不支援的文件會在批次處理結果中列出。",
        )
    )
    if any(uploaded_file and is_legacy_office_file(get_uploaded_relative_name(uploaded_file)) for uploaded_file in uploaded_files):
        soffice_binary = find_soffice_binary()
        if soffice_binary:
            st.caption(
                localized_text(
                    f"Legacy Office files detected. LibreOffice will be used for conversion: {soffice_binary}",
                    f"检测到老版 Office 文件，将使用 LibreOffice 转换：{soffice_binary}",
                    f"偵測到舊版 Office 文件，將使用 LibreOffice 轉換：{soffice_binary}",
                )
            )
        else:
            st.warning(
                localized_text(
                    "Legacy Office files detected. LibreOffice was not found. DOC can be converted with textutil on macOS; PPT/XLS require LibreOffice.",
                    "检测到老版 Office 文件。当前未找到 LibreOffice；DOC 在 macOS 可尝试用 textutil 转换，PPT/XLS 需要安装 LibreOffice。",
                    "偵測到舊版 Office 文件。目前未找到 LibreOffice；DOC 在 macOS 可嘗試用 textutil 轉換，PPT/XLS 需要安裝 LibreOffice。",
                )
            )

    category_options = list(DOC_CATEGORY_OPTIONS.keys())
    saved_category_label = get_config_value("upload_doc_category_label", category_options[0])
    if saved_category_label not in category_options:
        saved_category_label = category_options[0]
    category_label = st.radio(
        "资料类型",
        category_options,
        index=category_options.index(saved_category_label),
        horizontal=True,
        key="upload_doc_category_label",
    )
    set_config_value("upload_doc_category_label", category_label)
    doc_category = DOC_CATEGORY_OPTIONS[category_label]
    doc_label = st.text_input(
        "资料名称 / 备注",
        value="",
        placeholder="批量上传时留空会使用各自文件名",
    )
    ocr_enhance = st.checkbox(
        "启用 Office 内嵌图片 OCR",
        value=get_bool_config("upload_ocr_enhance", True),
        key="upload_ocr_enhance",
        help=localized_text(
            "DOCX/PPTX/XLSX embedded images are extracted and OCRed. For PDF OCR behavior, see PDF OCR Mode below.",
            "DOCX/PPTX/XLSX 会提取内嵌图片并 OCR。PDF 的 OCR 策略请看下面的 PDF OCR 模式。",
            "DOCX/PPTX/XLSX 會提取內嵌圖片並 OCR。PDF 的 OCR 策略請看下面的 PDF OCR 模式。",
        ),
    )
    set_bool_config("upload_ocr_enhance", ocr_enhance)
    ppt_visual_ocr = st.checkbox(
        "将 PPT/PPTX 栅格化后 OCR",
        value=get_bool_config("ppt_visual_ocr", True),
        key="upload_ppt_visual_ocr",
        help=localized_text(
            "Rasterization-based OCR renders each slide to a static page through LibreOffice, then OCRs the page image. This avoids Python parsing complex presentation objects and usually lowers memory pressure, but editable text structure is not preserved.",
            "栅格化 OCR 会先通过 LibreOffice 将每页幻灯片渲染成静态页面，再对页面图像 OCR。这样可避免 Python 解析复杂演示文稿对象，通常能降低内存压力，但不会保留可编辑文本结构。",
            "柵格化 OCR 會先透過 LibreOffice 將每頁投影片渲染成靜態頁面，再對頁面圖像 OCR。這樣可避免 Python 解析複雜簡報物件，通常能降低記憶體壓力，但不會保留可編輯文字結構。",
        ),
    )
    set_bool_config("ppt_visual_ocr", ppt_visual_ocr)
    auto_unload_models_after_ingest = st.checkbox(
        "入库完成后自动释放 OCR / BGE-M3 模型缓存",
        value=get_bool_config("auto_unload_models_after_ingest", False),
        key="auto_unload_models_after_ingest",
        help=localized_text(
            "Useful for machines with limited memory. Models will be reloaded on the next ingestion or retrieval.",
            "适合内存较小的机器；下次入库或检索会重新加载模型。",
            "適合記憶體較小的機器；下次入庫或檢索會重新載入模型。",
        ),
    )
    set_bool_config("auto_unload_models_after_ingest", auto_unload_models_after_ingest)
    replace_changed_same_name = st.checkbox(
        "同名文件变更时替换旧版本",
        value=get_bool_config("replace_changed_same_name", True),
        key="replace_changed_same_name_input",
        help=localized_text(
            "When a file at the same path has a different SHA256, old chunks and deduplication records are deleted before writing the new version.",
            "同一路径文件 SHA256 变化时，会先删除旧 chunk 和去重记录，再写入新版本。",
            "同一路徑文件 SHA256 變化時，會先刪除舊 chunk 和去重記錄，再寫入新版本。",
        ),
    )
    set_bool_config("replace_changed_same_name", replace_changed_same_name)
    background_ingest = st.checkbox(
        "后台入库队列",
        value=get_bool_config("background_ingest", DEFAULT_BACKGROUND_INGEST),
        key="background_ingest_input",
        help=localized_text(
            "After submission, a single in-app worker processes files in the background. The page remains usable and supports pause, resume, and stop.",
            "提交后由应用内单 worker 后台处理，页面可继续操作，并支持暂停、继续和终止。",
            "提交後由應用內單 worker 後台處理，頁面可繼續操作，並支援暫停、繼續和終止。",
        ),
    )
    set_bool_config("background_ingest", background_ingest)
    skip_large_excel = st.checkbox(
        "跳过超大 Excel 文件",
        value=get_bool_config("skip_large_excel", False),
        key="skip_large_excel_input",
        help="启用后，XLSX 和 XLS 的工作表最大行号合计超过阈值时会直接跳过，不解析、不切分、不写入向量库。",
    )
    set_bool_config("skip_large_excel", skip_large_excel)
    saved_excel_row_limit = max(get_int_config("excel_row_limit", 100000), 1)
    excel_row_limit = int(
        st.number_input(
            "Excel 最大行数",
            min_value=1,
            max_value=2_000_000,
            value=saved_excel_row_limit,
            step=10000,
            disabled=not skip_large_excel,
            key="excel_row_limit_input",
            help="超过该行数的 XLSX/XLS 文件会跳过入库。按所有工作表 max_row 合计计算。",
        )
    )
    set_config_value("excel_row_limit", excel_row_limit)
    active_ocr_config = get_paddleocr_model_config()
    st.caption(
        localized_text("Current PaddleOCR model: ", "当前 PaddleOCR 模型：", "當前 PaddleOCR 模型：")
        + f"{translate_text(get_paddleocr_model_label())} | {active_ocr_config['det']} / {active_ocr_config['rec']}"
    )

    pdf_ocr_mode_labels = list(PDF_OCR_MODE_OPTIONS.keys())
    saved_pdf_ocr_mode_label = get_config_value("upload_pdf_ocr_mode_label", pdf_ocr_mode_labels[0])
    if saved_pdf_ocr_mode_label not in pdf_ocr_mode_labels:
        saved_pdf_ocr_mode_label = pdf_ocr_mode_labels[0]
    pdf_ocr_mode_label = st.selectbox(
        "PDF OCR 模式",
        pdf_ocr_mode_labels,
        index=pdf_ocr_mode_labels.index(saved_pdf_ocr_mode_label),
        key="upload_pdf_ocr_mode_label",
        help=localized_text(
            "Smart OCR only processes PDF pages with little direct text. Force OCR is most complete, but large PDFs can be slow and memory-intensive.",
            "智能 OCR 只处理文字很少的 PDF 页。强制每页 OCR 最完整，但大 PDF 可能非常慢且占内存。",
            "智慧 OCR 只處理文字很少的 PDF 頁。強制每頁 OCR 最完整，但大 PDF 可能非常慢且佔記憶體。",
        ),
    )
    set_config_value("upload_pdf_ocr_mode_label", pdf_ocr_mode_label)
    pdf_ocr_mode = PDF_OCR_MODE_OPTIONS[pdf_ocr_mode_label]
    auto_install_libreoffice = st.checkbox(
        "缺少 LibreOffice 时自动下载安装转换工具",
        value=get_bool_config("auto_install_libreoffice", True),
        key="auto_install_libreoffice",
        help=localized_text(
            "Automatically converts legacy DOC/PPT/XLS Office files. Windows/Linux may require administrator privileges.",
            "用于自动转换 DOC/PPT/XLS 老版 Office 文件。Windows/Linux 可能需要管理员权限。",
            "用於自動轉換 DOC/PPT/XLS 舊版 Office 文件。Windows/Linux 可能需要管理員權限。",
        ),
    )
    set_bool_config("auto_install_libreoffice", auto_install_libreoffice)

    col1, col2 = st.columns(2)
    with col1:
        saved_chunk_size = min(max(get_int_config("upload_chunk_size", 600), 300), 1500)
        chunk_size = st.slider(
            "Chunk 大小",
            min_value=300,
            max_value=1500,
            value=saved_chunk_size,
            step=100,
            key="upload_chunk_size",
        )
        set_config_value("upload_chunk_size", chunk_size)
    with col2:
        overlap_max = min(300, chunk_size - 50)
        saved_overlap = min(max(get_int_config("upload_overlap", 100), 0), overlap_max)
        overlap = st.slider(
            "Chunk 重叠",
            min_value=0,
            max_value=overlap_max,
            value=saved_overlap,
            step=50,
            key="upload_overlap",
        )
        set_config_value("upload_overlap", overlap)

    ingest_notice = st.session_state.pop("ingest_notice", "")
    if ingest_notice:
        st.success(ingest_notice)
    if has_active_ingest_task() or ingest_notice:
        render_recent_ingest_tasks_live(expanded=bool(ingest_notice))
    else:
        render_recent_ingest_tasks(expanded=False)

    if uploaded_files:
        upload_support_rows = []
        unsupported_upload_rows = []
        for item in uploaded_files:
            relative_name = get_uploaded_relative_name(item)
            can_process, support_message = get_upload_support_status(relative_name, auto_install_libreoffice)
            if ppt_visual_ocr and get_file_extension_from_name(relative_name) in {"ppt", "pptx"} and not find_soffice_binary():
                can_process = bool(auto_install_libreoffice)
                support_message = localized_text(
                    "PPT/PPTX rasterization OCR requires LibreOffice; it will be installed automatically if possible.",
                    "PPT/PPTX 栅格化 OCR 需要 LibreOffice；导入前会尽量自动安装。",
                    "PPT/PPTX 柵格化 OCR 需要 LibreOffice；導入前會盡量自動安裝。",
                ) if auto_install_libreoffice else localized_text(
                    "PPT/PPTX rasterization OCR requires LibreOffice. Disable this option or install LibreOffice first.",
                    "PPT/PPTX 栅格化 OCR 需要 LibreOffice。请关闭该选项或先安装 LibreOffice。",
                    "PPT/PPTX 柵格化 OCR 需要 LibreOffice。請關閉該選項或先安裝 LibreOffice。",
                )
            row = {
                source_label("source_file"): relative_name,
                localized_text("File Type", "文件类型", "文件類型"): (Path(relative_name).suffix.lower().lstrip(".") or localized_text("No extension", "无扩展名", "無副檔名")).upper(),
                localized_text("Status", "状态", "狀態"): localized_text("Processable", "可处理", "可處理") if can_process else localized_text("Unsupported", "不支持", "不支援"),
                localized_text("Message", "说明", "說明"): support_message,
            }
            upload_support_rows.append(row)
            if not can_process:
                unsupported_upload_rows.append(row)

        processable_count = len(upload_support_rows) - len(unsupported_upload_rows)
        pending_count = len(uploaded_files) - processable_count
        st.info(
            localized_text(
                f"{len(uploaded_files)} files selected. {processable_count} can be processed and {pending_count} will be skipped or marked unsupported. Duplicate files are skipped automatically by SHA256 after processing starts.",
                f"已选择 {len(uploaded_files)} 个文件，其中当前可处理 {processable_count} 个，待跳过/不支持 {pending_count} 个。开始处理后会按 SHA256 自动跳过重复文件。",
                f"已選擇 {len(uploaded_files)} 個文件，其中目前可處理 {processable_count} 個，待跳過/不支援 {pending_count} 個。開始處理後會按 SHA256 自動跳過重複文件。",
            )
        )
        if unsupported_upload_rows:
            with st.expander(
                localized_text(
                    f"Unsupported Files ({len(unsupported_upload_rows)})",
                    f"不支持的文件（{len(unsupported_upload_rows)}）",
                    f"不支援的文件（{len(unsupported_upload_rows)}）",
                ),
                expanded=True,
            ):
                render_result_dataframe(unsupported_upload_rows, max_rows=200)

        if st.button("开始导入文件", type="primary", key="upload_ingest"):
            has_legacy_office = any(is_legacy_office_file(get_uploaded_relative_name(item)) for item in uploaded_files)
            needs_presentation_rasterizer = ppt_visual_ocr and any(
                get_file_extension_from_name(get_uploaded_relative_name(item)) in {"ppt", "pptx"}
                for item in uploaded_files
            )
            if (has_legacy_office or needs_presentation_rasterizer) and not find_soffice_binary() and auto_install_libreoffice:
                with st.status(
                    localized_text(
                        "LibreOffice was not detected. Attempting automatic installation...",
                        "未检测到 LibreOffice，正在尝试自动下载安装...",
                        "未偵測到 LibreOffice，正在嘗試自動下載安裝...",
                    ),
                    expanded=True,
                ) as status:
                    install_plan = get_libreoffice_install_plan()
                    st.write(
                        localized_text("Current system: ", "当前系统：", "當前系統：")
                        + str(install_plan.get("platform", localized_text("Unknown system", "未知系统", "未知系統")))
                    )
                    st.write(
                        localized_text("Install command: ", "安装命令：", "安裝命令：")
                        + str(install_plan.get("manual", localized_text("No available command", "无可用命令", "無可用命令")))
                    )
                    install_ok, install_message = install_libreoffice_automatically()
                    st.write(install_message)
                    if install_ok:
                        status.update(label=localized_text("LibreOffice is available", "LibreOffice 已可用", "LibreOffice 已可用"), state="complete")
                    else:
                        status.update(label=localized_text("LibreOffice automatic installation failed", "LibreOffice 自动安装失败", "LibreOffice 自動安裝失敗"), state="error")

            if background_ingest:
                batch_id = uuid.uuid4().hex
                task_id = create_ingest_task(len(uploaded_files))
                file_specs = []
                for uploaded_file in uploaded_files:
                    relative_name = get_uploaded_relative_name(uploaded_file)
                    file_specs.append(
                        {
                            "relative_name": relative_name,
                            "file_path": save_uploaded_file(uploaded_file, batch_id=batch_id),
                            "sha256": calculate_uploaded_file_sha256(uploaded_file),
                        }
                    )
                runtime = load_ingest_executor()
                future = runtime["executor"].submit(
                    run_background_ingest_task,
                    task_id,
                    file_specs,
                    {
                        "doc_category": doc_category,
                        "doc_label": doc_label,
                        "chunk_size": chunk_size,
                        "overlap": overlap,
                        "ocr_enhance": ocr_enhance,
                        "pdf_ocr_mode": pdf_ocr_mode,
                        "ppt_visual_ocr": ppt_visual_ocr,
                        "replace_changed_same_name": replace_changed_same_name,
                        "skip_large_excel": skip_large_excel,
                        "excel_row_limit": excel_row_limit,
                        "auto_unload_models_after_ingest": auto_unload_models_after_ingest,
                    },
                )
                runtime["futures"][task_id] = future
                update_ingest_task(task_id, message=localized_text("Background task submitted", "后台任务已提交", "後台任務已提交"))
                st.session_state["ingest_notice"] = localized_text(
                    'Background ingestion task submitted. View progress under "Recent Ingestion Tasks"; the page remains usable.',
                    "后台入库任务已提交。可在“最近入库任务”里查看进度，页面可以继续操作。",
                    "後台入庫任務已提交。可在「最近入庫任務」裡查看進度，頁面可以繼續操作。",
                )
                st.rerun()

            batch_id = uuid.uuid4().hex
            success_rows = []
            unsupported_rows = []
            skipped_rows = []
            failed_rows = []
            duplicate_rows = []
            progress_bar = st.progress(0, text=localized_text("Preparing files...", "准备处理文件...", "準備處理文件..."))
            status_box = st.empty()
            total_files = len(uploaded_files)
            task_id = create_ingest_task(total_files)

            def sync_ingest_task(processed_files: int, current_file: str, message: str, status: str = "running") -> None:
                update_ingest_task(
                    task_id,
                    status=status,
                    processed_files=processed_files,
                    success_count=len(success_rows),
                    duplicate_count=len(duplicate_rows),
                    skipped_count=len(skipped_rows) + len(unsupported_rows),
                    failed_count=len(failed_rows),
                    current_file=current_file,
                    message=message,
                )

            for file_index, uploaded_file in enumerate(uploaded_files, start=1):
                relative_name = get_uploaded_relative_name(uploaded_file)
                processing_message = localized_text(
                    f"Processing {file_index}/{total_files}: {relative_name}",
                    f"正在处理 {file_index}/{total_files}：{relative_name}",
                    f"正在處理 {file_index}/{total_files}：{relative_name}",
                )
                status_box.info(processing_message)
                sync_ingest_task(
                    file_index - 1,
                    relative_name,
                    localized_text(f"Processing: {relative_name}", f"正在处理：{relative_name}", f"正在處理：{relative_name}"),
                )
                progress_bar.progress(
                    (file_index - 1) / total_files,
                    text=processing_message,
                )

                if not is_supported_upload(relative_name):
                    ext = Path(relative_name).suffix.lower() or localized_text("No extension", "无扩展名", "無副檔名")
                    unsupported_rows.append(
                        {
                            source_label("source_file"): relative_name,
                            localized_text("Reason", "原因", "原因"): localized_text(
                                f"Unsupported file type: {ext}",
                                f"不支持的文件类型：{ext}",
                                f"不支援的文件類型：{ext}",
                            ),
                        }
                    )
                    progress_bar.progress(file_index / total_files, text=localized_text(f"Skipped: {relative_name}", f"已跳过：{relative_name}", f"已跳過：{relative_name}"))
                    sync_ingest_task(
                        file_index,
                        relative_name,
                        localized_text(f"Skipped unsupported file: {relative_name}", f"已跳过不支持文件：{relative_name}", f"已跳過不支援文件：{relative_name}"),
                    )
                    record_ingest_task_item(
                        task_id,
                        relative_name,
                        "unsupported",
                        localized_text(f"Unsupported file type: {ext}", f"不支持的文件类型：{ext}", f"不支援的文件類型：{ext}"),
                    )
                    continue

                file_sha256 = calculate_uploaded_file_sha256(uploaded_file)
                existing_file = get_duplicate_ingested_file(file_sha256)
                if existing_file:
                    duplicate_rows.append(
                        {
                            source_label("source_file"): relative_name,
                            localized_text("Already Ingested File", "已入库文件", "已入庫文件"): existing_file.get("file_name", ""),
                            source_label("document_type"): translate_text(DOC_CATEGORY_NAMES.get(
                                existing_file.get("doc_category", ""),
                                existing_file.get("doc_category", ""),
                            )),
                            localized_text("Chunk Count", "chunk 数", "chunk 數"): existing_file.get("chunk_count", 0),
                            "SHA256": file_sha256[:16],
                        }
                    )
                    duplicate_message = localized_text(
                        f"Skipped duplicate file: {relative_name}",
                        f"已跳过重复文件：{relative_name}",
                        f"已跳過重複文件：{relative_name}",
                    )
                    progress_bar.progress(file_index / total_files, text=duplicate_message)
                    sync_ingest_task(file_index, relative_name, duplicate_message)
                    record_ingest_task_item(
                        task_id,
                        relative_name,
                        "duplicate",
                        localized_text("Skipped duplicate file", "已跳过重复文件", "已跳過重複文件"),
                        chunk_count=int(existing_file.get("chunk_count", 0) or 0),
                        file_sha256=file_sha256,
                    )
                    continue

                if is_legacy_office_file(relative_name):
                    ext = get_file_extension_from_name(relative_name)
                    can_convert, conversion_message = get_legacy_conversion_status(ext)
                    if not can_convert:
                        unsupported_rows.append(
                            {
                                source_label("source_file"): relative_name,
                                localized_text("Reason", "原因", "原因"): conversion_message,
                            }
                        )
                        progress_bar.progress(file_index / total_files, text=localized_text(f"Skipped: {relative_name}", f"已跳过：{relative_name}", f"已跳過：{relative_name}"))
                        sync_ingest_task(
                            file_index,
                            relative_name,
                            localized_text(f"Skipped unconvertible file: {relative_name}", f"已跳过无法转换文件：{relative_name}", f"已跳過無法轉換文件：{relative_name}"),
                        )
                        record_ingest_task_item(task_id, relative_name, "unsupported", conversion_message, file_sha256=file_sha256)
                        continue

                if ppt_visual_ocr and get_file_extension_from_name(relative_name) in {"ppt", "pptx"} and not find_soffice_binary():
                    message = localized_text(
                        "PPT/PPTX rasterization OCR requires LibreOffice.",
                        "PPT/PPTX 栅格化 OCR 需要 LibreOffice。",
                        "PPT/PPTX 柵格化 OCR 需要 LibreOffice。",
                    )
                    unsupported_rows.append({source_label("source_file"): relative_name, localized_text("Reason", "原因", "原因"): message})
                    progress_bar.progress(file_index / total_files, text=localized_text(f"Skipped: {relative_name}", f"已跳过：{relative_name}", f"已跳過：{relative_name}"))
                    sync_ingest_task(file_index, relative_name, message)
                    record_ingest_task_item(task_id, relative_name, "unsupported", message, file_sha256=file_sha256)
                    continue

                try:
                    deleted_chunks = 0
                    file_path = save_uploaded_file(uploaded_file, batch_id=batch_id)

                    def extraction_progress(message: str) -> None:
                        status_box.info(f"{relative_name}: {message}")
                        sync_ingest_task(file_index - 1, relative_name, message)

                    try:
                        file_path, spreadsheet_row_count = prepare_spreadsheet_for_ingest(
                            relative_name=relative_name,
                            file_path=file_path,
                            skip_large_excel=skip_large_excel,
                            excel_row_limit=excel_row_limit,
                            progress_callback=extraction_progress,
                        )
                        if spreadsheet_row_count is not None:
                            status_box.info(
                                localized_text(
                                    f"{relative_name}: Excel row count checked: {spreadsheet_row_count}",
                                    f"{relative_name}：Excel 行数检查完成：{spreadsheet_row_count}",
                                    f"{relative_name}：Excel 行數檢查完成：{spreadsheet_row_count}",
                                )
                            )
                    except SpreadsheetRowLimitExceeded as e:
                        skipped_rows.append(
                            {
                                source_label("source_file"): relative_name,
                                localized_text("Reason", "原因", "原因"): str(e),
                            }
                        )
                        record_ingest_task_item(
                            task_id,
                            relative_name,
                            "skipped",
                            str(e),
                            file_sha256=file_sha256,
                        )
                        progress_bar.progress(file_index / total_files, text=localized_text(f"Skipped: {relative_name}", f"已跳过：{relative_name}", f"已跳過：{relative_name}"))
                        sync_ingest_task(file_index, relative_name, str(e))
                        release_memory_after_file()
                        continue

                    sections = extract_document_sections(
                        file_path,
                        ocr_enhance=ocr_enhance,
                        pdf_ocr_mode=pdf_ocr_mode,
                        ppt_visual_ocr=ppt_visual_ocr,
                        progress_callback=extraction_progress,
                    )

                    if not sections_have_text(sections):
                        skipped_rows.append(
                            {
                                source_label("source_file"): relative_name,
                                localized_text("Reason", "原因", "原因"): localized_text(
                                    "No valid text was parsed",
                                    "没有解析到有效文字",
                                    "沒有解析到有效文字",
                                ),
                            }
                        )
                        record_ingest_task_item(
                            task_id,
                            relative_name,
                            "skipped",
                            localized_text("No valid text was parsed", "没有解析到有效文字", "沒有解析到有效文字"),
                            file_sha256=file_sha256,
                        )
                    else:
                        deleted_chunks, _deleted_records = replace_existing_same_name_if_needed(
                            relative_name,
                            file_sha256,
                            enabled=replace_changed_same_name,
                        )
                        if deleted_chunks:
                            status_box.info(
                                localized_text(
                                    f"Replaced old version: {relative_name} (deleted {deleted_chunks} old chunks)",
                                    f"已替换旧版本：{relative_name}（删除 {deleted_chunks} 个旧 chunk）",
                                    f"已替換舊版本：{relative_name}（刪除 {deleted_chunks} 個舊 chunk）",
                                )
                            )
                        chunk_count = add_document_to_vector_store(
                            file_name=relative_name,
                            file_sha256=file_sha256,
                            sections=sections,
                            chunk_size=chunk_size,
                            overlap=overlap,
                            doc_category=doc_category,
                            doc_label=doc_label or relative_name,
                        )
                        if chunk_count > 0:
                            record_ingested_file(
                                file_sha256=file_sha256,
                                file_name=relative_name,
                                doc_category=doc_category,
                                doc_label=doc_label or relative_name,
                                chunk_count=chunk_count,
                            )
                            success_rows.append(
                                {
                                    source_label("source_file"): relative_name,
                                    localized_text("Chunk Count", "chunk 数", "chunk 數"): chunk_count,
                                    source_label("document_type"): translate_text(category_label),
                                    "SHA256": file_sha256[:16],
                                    localized_text("Replaced Old Chunks", "替换旧 chunk", "替換舊 chunk"): deleted_chunks,
                                }
                            )
                            record_ingest_task_item(
                                task_id,
                                relative_name,
                                "success",
                                localized_text(
                                    f"Ingested successfully; wrote {chunk_count} chunks",
                                    f"入库成功，写入 {chunk_count} 个 chunk",
                                    f"入庫成功，寫入 {chunk_count} 個 chunk",
                                ),
                                chunk_count=chunk_count,
                                file_sha256=file_sha256,
                            )
                        else:
                            skipped_rows.append(
                                {
                                    source_label("source_file"): relative_name,
                                    localized_text("Reason", "原因", "原因"): localized_text(
                                        "Parsed successfully, but no ingestible chunks were produced",
                                        "解析成功但没有可入库 chunk",
                                        "解析成功但沒有可入庫 chunk",
                                    ),
                                }
                            )
                            record_ingest_task_item(
                                task_id,
                                relative_name,
                                "skipped",
                                localized_text(
                                    "Parsed successfully, but no ingestible chunks were produced",
                                    "解析成功但没有可入库 chunk",
                                    "解析成功但沒有可入庫 chunk",
                                ),
                                file_sha256=file_sha256,
                            )
                except Exception as e:
                    failed_rows.append(
                        {
                            source_label("source_file"): relative_name,
                            localized_text("Reason", "原因", "原因"): str(e),
                        }
                    )
                    record_ingest_task_item(task_id, relative_name, "failed", str(e), file_sha256=file_sha256)

                done_message = localized_text(f"Completed: {relative_name}", f"已完成：{relative_name}", f"已完成：{relative_name}")
                progress_bar.progress(file_index / total_files, text=done_message)
                sync_ingest_task(file_index, relative_name, done_message)
                release_memory_after_file()

            batch_done_message = localized_text("Batch processing completed", "批量处理完成", "批次處理完成")
            status_box.success(batch_done_message)
            progress_bar.progress(1.0, text=batch_done_message)
            sync_ingest_task(total_files, "", batch_done_message, status="completed")
            if auto_unload_models_after_ingest:
                load_ocr_model.clear()
                load_embedding_model.clear()
                release_memory_after_file()
                st.info(localized_text("OCR / BGE-M3 model cache was released as configured.", "已按设置释放 OCR / BGE-M3 模型缓存。", "已按設定釋放 OCR / BGE-M3 模型快取。"))

            if success_rows:
                st.success(localized_text(f"Successfully ingested {len(success_rows)} files.", f"成功入库 {len(success_rows)} 个文件。", f"成功入庫 {len(success_rows)} 個文件。"))
                render_result_dataframe(success_rows)
            else:
                st.warning(localized_text("No files were ingested successfully in this run.", "本次没有文件成功入库。", "本次沒有文件成功入庫。"))

            if unsupported_rows:
                st.warning(localized_text(f"{len(unsupported_rows)} unsupported files.", f"不支持 {len(unsupported_rows)} 个文件。", f"不支援 {len(unsupported_rows)} 個文件。"))
                render_result_dataframe(unsupported_rows)

            if duplicate_rows:
                st.info(localized_text(f"{len(duplicate_rows)} duplicate files were skipped.", f"重复文件 {len(duplicate_rows)} 个，已跳过。", f"重複文件 {len(duplicate_rows)} 個，已跳過。"))
                render_result_dataframe(duplicate_rows)

            if skipped_rows:
                st.info(localized_text(f"{len(skipped_rows)} files were skipped.", f"跳过 {len(skipped_rows)} 个文件。", f"跳過 {len(skipped_rows)} 個文件。"))
                render_result_dataframe(skipped_rows)

            if failed_rows:
                st.error(localized_text(f"{len(failed_rows)} files failed to process.", f"处理失败 {len(failed_rows)} 个文件。", f"處理失敗 {len(failed_rows)} 個文件。"))
                render_result_dataframe(failed_rows)
