"""Model status page UI.
模型状态页面 UI。
"""

from ..services import *
from .components import *


def render_model_status_tab() -> None:
    st.subheader("模型状态 / 下载查询")
    llm_config = get_llm_config()
    qdrant_config = get_qdrant_config()
    active_ocr_config = get_paddleocr_model_config()
    soffice_binary = find_soffice_binary()
    libreoffice_plan = get_libreoffice_install_plan()
    model_rows = [
        {
            localized_text("Component", "组件", "組件"): "PaddleOCR",
            localized_text("Status", "状态", "狀態"): get_paddle_cache_status(),
            localized_text("Purpose", "用途", "用途"): (
                localized_text("Image and scanned PDF OCR; current model: ", "图片和扫描 PDF OCR；当前模型：", "圖片和掃描 PDF OCR；當前模型：")
                + f"{active_ocr_config['det']} / {active_ocr_config['rec']}"
            ),
        },
        {
            localized_text("Component", "组件", "組件"): EMBEDDING_MODEL_NAME,
            localized_text("Status", "状态", "狀態"): get_bge_cache_status(),
            localized_text("Purpose", "用途", "用途"): localized_text("Text vectorization and vector retrieval", "文本向量化和向量检索", "文字向量化和向量檢索"),
        },
        {
            localized_text("Component", "组件", "組件"): RERANKER_MODEL_NAME,
            localized_text("Status", "状态", "狀態"): get_reranker_cache_status(),
            localized_text("Purpose", "用途", "用途"): localized_text("Candidate chunk reranking to improve retrieval precision", "候选片段重排，提升检索精度", "候選片段重排，提升檢索精度"),
        },
        {
            localized_text("Component", "组件", "組件"): "LibreOffice / soffice",
            localized_text("Status", "状态", "狀態"): (
                localized_text(f"Installed: {soffice_binary}", f"已安装：{soffice_binary}", f"已安裝：{soffice_binary}")
                if soffice_binary
                else localized_text(
                    f"Not detected; automatic installation plan: {libreoffice_plan.get('manual', 'None')}",
                    f"未检测到；自动安装方案：{libreoffice_plan.get('manual', '无')}",
                    f"未檢測到；自動安裝方案：{libreoffice_plan.get('manual', '無')}",
                )
            ),
            localized_text("Purpose", "用途", "用途"): localized_text("DOC/PPT/XLS legacy Office file conversion", "DOC/PPT/XLS 老版 Office 文件转换", "DOC/PPT/XLS 舊版 Office 文件轉換"),
        },
        {
            localized_text("Component", "组件", "組件"): "Qdrant",
            localized_text("Status", "状态", "狀態"): (
                localized_text("Mode: ", "模式：", "模式：")
                + qdrant_config["mode"]
                + "; "
                + (
                    localized_text("URL: ", "地址：", "地址：") + qdrant_config["url"]
                    if qdrant_config["mode"] == "http"
                    else localized_text("Path: ", "路径：", "路徑：") + qdrant_config["local_path"]
                )
            ),
            localized_text("Purpose", "用途", "用途"): localized_text("Vector storage and retrieval", "向量存储和检索", "向量儲存和檢索"),
        },
        {
            localized_text("Component", "组件", "組件"): localized_text(
                f"Local LLM endpoint: {llm_config['model']}",
                f"本地大模型接口：{llm_config['model']}",
                f"本地大模型接口：{llm_config['model']}",
            ),
            localized_text("Status", "状态", "狀態"): (
                localized_text("API type: ", "接口类型：", "接口類型：")
                + f"{llm_config.get('api_type', DEFAULT_LLM_API_TYPE)}; "
                + localized_text("Address: ", "地址：", "地址：")
                + f"{llm_config['base_url']}; "
                + localized_text("Fast: ", "快速：", "快速：")
                + f"{llm_config.get('fast_model', llm_config['model'])}; "
                + localized_text("Thinking: ", "思考：", "思考：")
                + f"{llm_config.get('thinking_model', llm_config['model'])}"
            ),
            localized_text("Purpose", "用途", "用途"): localized_text("Q&A and compliance analysis generation", "问答和合规分析生成", "問答和合規分析生成"),
        },
    ]
    st.dataframe(model_rows, width="stretch")

    st.markdown("### 操作")

    with st.container(border=True):
        st.markdown("#### 内存管理")
        if st.button("释放 OCR / BGE-M3 / Reranker 模型缓存", key="clear_model_cache"):
            try:
                load_ocr_model.clear()
                load_embedding_model.clear()
                load_reranker_model.clear()
                release_memory_after_file()
                record_model_event(
                    localized_text("Model Cache", "模型缓存", "模型快取"),
                    localized_text("Completed", "完成", "完成"),
                    localized_text("OCR, BGE-M3, and Reranker caches cleared", "已清理 OCR、BGE-M3 和 Reranker 缓存", "已清理 OCR、BGE-M3 和 Reranker 快取"),
                )
                st.success(localized_text("OCR / BGE-M3 / Reranker model caches released.", "已释放 OCR / BGE-M3 / Reranker 模型缓存。", "已釋放 OCR / BGE-M3 / Reranker 模型快取。"))
            except Exception as e:
                record_model_event(localized_text("Model Cache", "模型缓存", "模型快取"), localized_text("Failed", "失败", "失敗"), str(e))
                st.error(localized_text(f"Failed to release model caches: {e}", f"释放模型缓存失败：{e}", f"釋放模型快取失敗：{e}"))
        if st.button(localized_text("Close Qdrant Client Cache", "关闭 Qdrant 客户端缓存", "關閉 Qdrant 客戶端快取"), key="close_qdrant_client_cache"):
            try:
                close_qdrant_singleton()
                load_qdrant_client.clear()
                release_memory_after_file()
                record_model_event("Qdrant", localized_text("Completed", "完成", "完成"), localized_text("Qdrant client cache closed", "Qdrant 客户端缓存已关闭", "Qdrant 客戶端快取已關閉"))
                st.success(localized_text("Qdrant client cache closed.", "Qdrant 客户端缓存已关闭。", "Qdrant 客戶端快取已關閉。"))
            except Exception as e:
                record_model_event("Qdrant", localized_text("Failed", "失败", "失敗"), str(e))
                st.error(localized_text(f"Failed to close Qdrant client cache: {e}", f"关闭 Qdrant 客户端缓存失败：{e}", f"關閉 Qdrant 客戶端快取失敗：{e}"))

    with st.container(border=True):
        st.markdown("#### PaddleOCR")
        if st.button("预加载 PaddleOCR", key="preload_ocr"):
            try:
                with st.status("正在加载 PaddleOCR...", expanded=True) as status:
                    st.write(localized_text("Checking local cache...", "检查本地缓存...", "檢查本地快取..."))
                    st.write(get_paddle_cache_status())
                    st.write(localized_text("Loading OCR model...", "加载 OCR 模型...", "載入 OCR 模型..."))
                    load_ocr_model()
                    record_model_event("PaddleOCR", localized_text("Completed", "完成", "完成"), localized_text("OCR model is available", "OCR 模型已可用", "OCR 模型已可用"))
                    status.update(label=localized_text("PaddleOCR is available", "PaddleOCR 已可用", "PaddleOCR 已可用"), state="complete")
            except Exception as e:
                record_model_event("PaddleOCR", localized_text("Failed", "失败", "失敗"), str(e))
                st.error(localized_text(f"PaddleOCR loading failed: {e}", f"PaddleOCR 加载失败：{e}", f"PaddleOCR 載入失敗：{e}"))

    with st.container(border=True):
        st.markdown("#### BGE-M3")
        if st.button("预加载 BGE-M3", key="preload_bge"):
            try:
                with st.status("正在加载 BGE-M3...", expanded=True) as status:
                    st.write(localized_text("Checking local cache...", "检查本地缓存...", "檢查本地快取..."))
                    st.write(get_bge_cache_status())
                    st.write(localized_text("Loading embedding model...", "加载 embedding 模型...", "載入 embedding 模型..."))
                    load_embedding_model()
                    st.write(localized_text("Running a test embedding...", "执行一次测试向量化...", "執行一次測試向量化..."))
                    embed_texts([localized_text("Model preload test", "模型预加载测试", "模型預載測試")])
                    record_model_event(EMBEDDING_MODEL_NAME, localized_text("Completed", "完成", "完成"), localized_text("BGE-M3 is available", "BGE-M3 已可用", "BGE-M3 已可用"))
                    status.update(label=localized_text("BGE-M3 is available", "BGE-M3 已可用", "BGE-M3 已可用"), state="complete")
            except Exception as e:
                record_model_event(EMBEDDING_MODEL_NAME, localized_text("Failed", "失败", "失敗"), str(e))
                st.error(localized_text(f"BGE-M3 loading failed: {e}", f"BGE-M3 加载失败：{e}", f"BGE-M3 載入失敗：{e}"))

    with st.container(border=True):
        st.markdown("#### BGE Reranker")
        if st.button("预加载 Reranker", key="preload_reranker"):
            try:
                with st.status("正在加载 Reranker...", expanded=True) as status:
                    st.write(localized_text("Checking local cache...", "检查本地缓存...", "檢查本地快取..."))
                    st.write(get_reranker_cache_status())
                    st.write(localized_text("Loading reranker model...", "加载重排模型...", "載入重排模型..."))
                    reranker = load_reranker_model()
                    st.write(localized_text("Running a test rerank...", "执行一次测试重排...", "執行一次測試重排..."))
                    reranker.predict([[localized_text("Test question", "测试问题", "測試問題"), localized_text("Test chunk", "测试片段", "測試片段")]], show_progress_bar=False)
                    record_model_event(RERANKER_MODEL_NAME, localized_text("Completed", "完成", "完成"), localized_text("Reranker is available", "Reranker 已可用", "Reranker 已可用"))
                    status.update(label=localized_text("Reranker is available", "Reranker 已可用", "Reranker 已可用"), state="complete")
            except Exception as e:
                record_model_event(RERANKER_MODEL_NAME, localized_text("Failed", "失败", "失敗"), str(e))
                st.error(localized_text(f"Reranker loading failed: {e}", f"Reranker 加载失败：{e}", f"Reranker 載入失敗：{e}"))

    with st.container(border=True):
        st.markdown("#### Office 老格式转换")
        soffice_binary = find_soffice_binary()
        if soffice_binary:
            st.success(localized_text(f"LibreOffice is available: {soffice_binary}", f"LibreOffice 已可用：{soffice_binary}", f"LibreOffice 已可用：{soffice_binary}"))
            if st.button("测试 LibreOffice", key="test_libreoffice"):
                try:
                    with st.status("正在测试 LibreOffice...", expanded=True) as status:
                        result = run_subprocess([soffice_binary, "--version"], timeout=60)
                        if result.returncode == 0:
                            version_text = (result.stdout or result.stderr or "").strip()
                            record_model_event("LibreOffice", localized_text("Completed", "完成", "完成"), version_text)
                            status.update(label=localized_text(f"LibreOffice available: {version_text}", f"LibreOffice 可用：{version_text}", f"LibreOffice 可用：{version_text}"), state="complete")
                        else:
                            detail = (result.stderr or result.stdout or "").strip()
                            raise RuntimeError(detail or localized_text("Unknown error", "未知错误", "未知錯誤"))
                except Exception as e:
                    record_model_event("LibreOffice", localized_text("Failed", "失败", "失敗"), str(e))
                    st.error(localized_text(f"LibreOffice test failed: {e}", f"LibreOffice 测试失败：{e}", f"LibreOffice 測試失敗：{e}"))
        else:
            st.warning(
                localized_text(
                    "LibreOffice was not detected. Uploading DOC/PPT/XLS will attempt automatic installation, or you can trigger it here manually.",
                    "未检测到 LibreOffice。上传 DOC/PPT/XLS 时会尝试自动安装，也可以在这里手动触发。",
                    "未檢測到 LibreOffice。上傳 DOC/PPT/XLS 時會嘗試自動安裝，也可以在這裡手動觸發。",
                )
            )
            st.caption(
                localized_text(
                    f"Current system installation plan: {libreoffice_plan.get('manual', 'No available plan')}",
                    f"当前系统安装方案：{libreoffice_plan.get('manual', '无可用方案')}",
                    f"當前系統安裝方案：{libreoffice_plan.get('manual', '無可用方案')}",
                )
            )
            if st.button("自动安装 LibreOffice", key="install_libreoffice"):
                with st.status("正在自动安装 LibreOffice...", expanded=True) as status:
                    st.write(
                        localized_text("Current system: ", "当前系统：", "當前系統：")
                        + str(libreoffice_plan.get("platform", localized_text("Unknown system", "未知系统", "未知系統")))
                    )
                    st.write(
                        localized_text("Install command: ", "安装命令：", "安裝命令：")
                        + str(libreoffice_plan.get("manual", localized_text("No available command", "无可用命令", "無可用命令")))
                    )
                    install_ok, install_message = install_libreoffice_automatically()
                    st.write(install_message)
                    if install_ok:
                        record_model_event("LibreOffice", localized_text("Completed", "完成", "完成"), install_message)
                        status.update(label=localized_text("LibreOffice is available", "LibreOffice 已可用", "LibreOffice 已可用"), state="complete")
                    else:
                        record_model_event("LibreOffice", localized_text("Failed", "失败", "失敗"), install_message)
                        status.update(label=localized_text("LibreOffice automatic installation failed", "LibreOffice 自动安装失败", "LibreOffice 自動安裝失敗"), state="error")

    with st.container(border=True):
        st.markdown("#### 本地大模型")
        saved_model_status_test_mode = get_config_value("model_status_test_mode_label", "快速")
        if saved_model_status_test_mode not in LLM_MODE_OPTIONS:
            saved_model_status_test_mode = "快速"
        model_test_mode_label = st.radio(
            "测试模式",
            list(LLM_MODE_OPTIONS.keys()),
            index=list(LLM_MODE_OPTIONS.keys()).index(saved_model_status_test_mode),
            horizontal=False,
            key="model_status_test_llm_mode_label",
        )
        set_config_value("model_status_test_mode_label", model_test_mode_label)
        model_test_mode = LLM_MODE_OPTIONS[model_test_mode_label]
        if st.button("测试本地大模型", key="test_llm"):
            with st.status("正在测试本地大模型接口...", expanded=True) as status:
                try:
                    active_config = get_llm_config()
                    test_model, test_extra_body = get_llm_mode_config(model_test_mode)
                    st.write(localized_text("Endpoint: ", "接口地址：", "接口地址：") + active_config["base_url"])
                    st.write(localized_text("Model name: ", "模型名称：", "模型名稱：") + test_model)
                    st.write(f"extra_body：{test_extra_body or {}}")
                    reply = test_llm_connection(mode=model_test_mode)
                    record_model_event(localized_text("Local LLM", "本地大模型", "本地大模型"), localized_text("Completed", "完成", "完成"), reply)
                    status.update(label=localized_text(f"Local LLM available: {reply}", f"本地大模型可用：{reply}", f"本地大模型可用：{reply}"), state="complete")
                except Exception as e:
                    record_model_event(localized_text("Local LLM", "本地大模型", "本地大模型"), localized_text("Failed", "失败", "失敗"), str(e))
                    status.update(
                        label=localized_text(
                            f"Local LLM test failed: {e}",
                            f"本地大模型测试失败：{e}",
                            f"本地大模型測試失敗：{e}",
                        ),
                        state="error",
                    )
                    st.error(localized_text(f"Local LLM test failed: {e}", f"本地大模型测试失败：{e}", f"本地大模型測試失敗：{e}"))

    model_events = st.session_state.get("model_events", [])
    if model_events:
        st.markdown(f"### {localized_text('Recent Model Events', '最近模型事件', '最近模型事件')}")
        st.dataframe(model_events[-20:], width="stretch")
