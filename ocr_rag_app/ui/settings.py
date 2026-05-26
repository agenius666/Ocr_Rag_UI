"""Settings page UI.
配置中心页面 UI。
"""

from ..services import *
from .components import *


def render_settings_tab() -> None:
    st.subheader("配置中心")
    reset_notice = st.session_state.pop("app_reset_notice", "")
    if reset_notice:
        st.success(reset_notice)

    config_language_tab, config_model_tab, config_qdrant_tab, config_llm_tab, config_reset_tab = st.tabs(
        [
            localized_text("Language", "语言设置", "語言設定"),
            localized_text("Models And Paths", "模型与路径", "模型與路徑"),
            localized_text("Vector Store", "向量库连接", "向量庫連線"),
            localized_text("Local LLM", "本地大模型", "本地大模型"),
            localized_text("Reset", "初始化", "初始化"),
        ]
    )

    with config_language_tab:
        with st.container(border=True):
            st.markdown("#### 界面语言")
            current_language_code = get_ui_language()
            current_language_label = LANGUAGE_LABEL_BY_CODE.get(current_language_code, "English")
            selected_language_label = st.selectbox(
                "选择界面语言",
                list(LANGUAGE_OPTIONS.keys()),
                index=list(LANGUAGE_OPTIONS.keys()).index(current_language_label),
                key="ui_language_selector",
            )
            st.caption("语言偏好会保存到 app_state.sqlite3，下次打开会自动生效。")
            selected_language_code = LANGUAGE_OPTIONS[selected_language_label]
            if selected_language_code != current_language_code:
                set_config_value("ui_language", selected_language_code)
                st.success(localized_text("Language setting saved.", "语言设置已保存。", "語言設定已保存。"))
                st.rerun()

    with config_model_tab:
        ocr_col, path_col = st.columns([1, 2])
        with ocr_col:
            with st.container(border=True):
                st.markdown("#### OCR 模型")
                paddleocr_model_labels = list(PADDLEOCR_MODEL_OPTIONS.keys())
                current_paddleocr_label = get_paddleocr_model_label()
                selected_paddleocr_label = st.selectbox(
                    "PaddleOCR 模型",
                    paddleocr_model_labels,
                    index=paddleocr_model_labels.index(current_paddleocr_label),
                    key="config_paddleocr_model_label",
                    help=localized_text(
                        "Server is more accurate but uses more resources. Mobile uses less memory and is faster.",
                        "Server 精度更高但占用更大；Mobile 占用更低、速度更快。",
                        "Server 精度更高但佔用更大；Mobile 佔用更低、速度更快。",
                    ),
                )
                selected_config = PADDLEOCR_MODEL_OPTIONS[selected_paddleocr_label]
                st.caption(localized_text("Detection model: ", "检测模型：", "偵測模型：") + selected_config["det"])
                st.caption(localized_text("Recognition model: ", "识别模型：", "識別模型：") + selected_config["rec"])
                if selected_paddleocr_label != current_paddleocr_label:
                    save_paddleocr_model_label(selected_paddleocr_label)
                    st.success(
                        localized_text(
                            "PaddleOCR model setting saved and OCR cache cleared.",
                            "PaddleOCR 模型配置已保存，OCR 缓存已清理。",
                            "PaddleOCR 模型配置已保存，OCR 快取已清理。",
                        )
                    )
                    st.rerun()

        with path_col:
            with st.container(border=True):
                st.markdown("#### 模型保存路径")
                st.caption(
                    localized_text(
                        "By default, PaddleOCR, BGE-M3, and the reranker are cached under the project's model_cache directory. If a specific path is configured, that path is used first.",
                        "默认会把 PaddleOCR、BGE-M3 和 Reranker 缓存在项目的 model_cache 目录下；单独指定路径后会优先读取指定路径。",
                        "預設會把 PaddleOCR、BGE-M3 和 Reranker 快取在專案的 model_cache 目錄下；單獨指定路徑後會優先讀取指定路徑。",
                    )
                )
                with st.form("model_cache_config_form"):
                    model_cache_root = st.text_input(
                        "默认模型根目录",
                        value=get_model_cache_root(),
                        key="model_cache_root_input",
                        placeholder=DEFAULT_MODEL_CACHE_ROOT,
                        help=localized_text(
                            "When a model-specific path is empty, model cache folders are created under this root.",
                            "未单独指定模型路径时，会在该目录下创建各模型缓存目录。",
                            "未單獨指定模型路徑時，會在該目錄下建立各模型快取目錄。",
                        ),
                    )
                    default_root_for_form = normalize_local_path(model_cache_root, DEFAULT_MODEL_CACHE_ROOT)
                    path_input_col1, path_input_col2 = st.columns(2)
                    with path_input_col1:
                        paddleocr_cache_dir = st.text_input(
                            "PaddleOCR 模型目录",
                            value=get_config_value("paddleocr_cache_dir", ""),
                            key="paddleocr_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "paddlex"),
                            help=localized_text(
                                "Maps to PADDLE_PDX_CACHE_HOME. PaddleOCR official models are cached under official_models in this directory.",
                                "对应 PADDLE_PDX_CACHE_HOME，PaddleOCR 官方模型会缓存到该目录下的 official_models。",
                                "對應 PADDLE_PDX_CACHE_HOME，PaddleOCR 官方模型會快取到該目錄下的 official_models。",
                            ),
                        )
                        bge_cache_dir = st.text_input(
                            "BAAI/bge-m3 模型目录",
                            value=get_config_value("bge_cache_dir", ""),
                            key="bge_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-m3"),
                            help=localized_text(
                                "sentence-transformers/HuggingFace cache directory for BGE-M3.",
                                "BGE-M3 的 sentence-transformers/HuggingFace 缓存目录。",
                                "BGE-M3 的 sentence-transformers/HuggingFace 快取目錄。",
                            ),
                        )
                    with path_input_col2:
                        reranker_cache_dir = st.text_input(
                            "BAAI/bge-reranker-v2-m3 模型目录",
                            value=get_config_value("reranker_cache_dir", ""),
                            key="reranker_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-reranker-v2-m3"),
                            help=localized_text(
                                "sentence-transformers/HuggingFace cache directory for the reranker.",
                                "Reranker 的 sentence-transformers/HuggingFace 缓存目录。",
                                "Reranker 的 sentence-transformers/HuggingFace 快取目錄。",
                            ),
                        )
                        soffice_binary_path = st.text_input(
                            "LibreOffice / soffice 路径",
                            value=get_configured_soffice_path(),
                            key="soffice_binary_path_input",
                            placeholder=localized_text(
                                "Leave empty to auto-detect the system path",
                                "留空则自动搜索系统路径",
                                "留空則自動搜尋系統路徑",
                            ),
                            help=localized_text(
                                "LibreOffice is not a model. Configure the soffice executable file or installation directory here.",
                                "LibreOffice 不是模型，这里配置的是 soffice 可执行文件或安装目录。",
                                "LibreOffice 不是模型，這裡配置的是 soffice 可執行文件或安裝目錄。",
                            ),
                        )

                    path_col_save, path_col_reset = st.columns([1, 1])
                    with path_col_save:
                        save_model_paths = st.form_submit_button("保存模型路径", type="primary")
                    with path_col_reset:
                        reset_model_paths = st.form_submit_button("恢复默认路径")

                if save_model_paths:
                    try:
                        save_model_cache_config(
                            model_cache_root,
                            paddleocr_cache_dir,
                            bge_cache_dir,
                            reranker_cache_dir,
                            soffice_binary_path,
                        )
                        if soffice_binary_path and not find_soffice_binary():
                            st.warning(
                                localized_text(
                                    "Model paths were saved, but the current LibreOffice / soffice path does not point to an executable file.",
                                    "模型路径已保存，但当前 LibreOffice / soffice 路径未检测到可执行文件。",
                                    "模型路徑已保存，但當前 LibreOffice / soffice 路徑未檢測到可執行文件。",
                                )
                            )
                        else:
                            st.success(
                                localized_text(
                                    "Model paths saved. Loaded model caches were cleared; the next load will use the new paths.",
                                    "模型路径已保存，已清理已加载模型缓存；下次加载会使用新路径。",
                                    "模型路徑已保存，已清理已載入模型快取；下次載入會使用新路徑。",
                                )
                            )
                    except Exception as e:
                        st.error(localized_text(f"Failed to save model paths: {e}", f"保存模型路径失败：{e}", f"保存模型路徑失敗：{e}"))

                if reset_model_paths:
                    try:
                        save_model_cache_config(DEFAULT_MODEL_CACHE_ROOT, "", "", "", DEFAULT_SOFFICE_BINARY_PATH)
                        st.success(localized_text("Default model paths restored.", "已恢复默认模型路径。", "已恢復預設模型路徑。"))
                        st.rerun()
                    except Exception as e:
                        st.error(localized_text(f"Failed to restore default model paths: {e}", f"恢复默认模型路径失败：{e}", f"恢復預設模型路徑失敗：{e}"))

                with st.expander("当前路径", expanded=False):
                    st.json(
                        {
                            "model_cache_root": get_model_cache_root(),
                            "paddleocr_cache_dir": get_paddleocr_cache_dir(),
                            "bge_cache_dir": get_bge_cache_dir(),
                            "reranker_cache_dir": get_reranker_cache_dir(),
                            "soffice_binary_path": get_configured_soffice_path() or localized_text("Auto-detect system path", "自动搜索系统路径", "自動搜尋系統路徑"),
                            "detected_soffice": find_soffice_binary() or localized_text("Not detected", "未检测到", "未檢測到"),
                        }
                    )

    with config_qdrant_tab:
        current_qdrant = get_qdrant_config()
        with st.container(border=True):
            st.markdown(localized_text("#### Qdrant Connection", "#### Qdrant 连接", "#### Qdrant 連線"))
            st.caption(
                localized_text(
                    "Use Local for a single-user desktop setup. Use HTTP / Docker when the vector store should run in a separate Qdrant service.",
                    "单机个人使用可选择本地文件库；如果希望向量库独立运行，请选择 HTTP / Docker 服务。",
                    "單機個人使用可選擇本地文件庫；如果希望向量庫獨立運行，請選擇 HTTP / Docker 服務。",
                )
            )
            qdrant_mode_options = {
                localized_text("Local File Store", "本地文件库", "本地文件庫"): "local",
                localized_text("HTTP / Docker Service", "HTTP / Docker 服务", "HTTP / Docker 服務"): "http",
            }
            mode_labels = list(qdrant_mode_options.keys())
            current_mode_label = next(
                (label for label, value in qdrant_mode_options.items() if value == current_qdrant["mode"]),
                mode_labels[0],
            )
            with st.form("qdrant_config_form"):
                mode_label = st.selectbox(
                    localized_text("Connection Mode", "连接方式", "連線方式"),
                    mode_labels,
                    index=mode_labels.index(current_mode_label),
                    key="qdrant_mode_label",
                    help=localized_text(
                        "HTTP mode is compatible with Qdrant Docker and remote Qdrant services.",
                        "HTTP 模式兼容 Qdrant Docker 和远程 Qdrant 服务。",
                        "HTTP 模式相容 Qdrant Docker 和遠端 Qdrant 服務。",
                    ),
                )
                qdrant_mode = qdrant_mode_options[mode_label]
                qdrant_col1, qdrant_col2 = st.columns(2)
                with qdrant_col1:
                    qdrant_local_path = st.text_input(
                        localized_text("Local Qdrant Path", "本地 Qdrant 路径", "本地 Qdrant 路徑"),
                        value=current_qdrant["local_path"],
                        key="qdrant_local_path_input",
                        placeholder=localized_text(
                            "Example: qdrant_db",
                            "例如：qdrant_db",
                            "例如：qdrant_db",
                        ),
                        help=localized_text(
                            "Used only in Local mode. The default is qdrant_db under the project directory.",
                            "仅本地模式使用；默认是项目目录下的 qdrant_db。",
                            "僅本地模式使用；預設是專案目錄下的 qdrant_db。",
                        ),
                    )
                with qdrant_col2:
                    qdrant_url = st.text_input(
                        localized_text("Qdrant HTTP URL", "Qdrant HTTP 地址", "Qdrant HTTP 地址"),
                        value=current_qdrant["url"],
                        key="qdrant_url_input",
                        placeholder=localized_text(
                            "Example: http://127.0.0.1:6333",
                            "例如：http://127.0.0.1:6333",
                            "例如：http://127.0.0.1:6333",
                        ),
                        help=localized_text(
                            "For Docker Qdrant, the usual local URL is http://127.0.0.1:6333.",
                            "Docker Qdrant 本机常用地址是 http://127.0.0.1:6333。",
                            "Docker Qdrant 本機常用地址是 http://127.0.0.1:6333。",
                        ),
                    )
                    qdrant_api_key = st.text_input(
                        localized_text("Qdrant API Key", "Qdrant API Key", "Qdrant API Key"),
                        value=current_qdrant["api_key"],
                        key="qdrant_api_key_input",
                        placeholder=localized_text(
                            "Leave empty if no API key is configured",
                            "未配置 API Key 时留空",
                            "未配置 API Key 時留空",
                        ),
                        help=localized_text(
                            "Leave empty when your local Docker Qdrant has no API key.",
                            "本机 Docker Qdrant 没有鉴权时留空。",
                            "本機 Docker Qdrant 沒有鑑權時留空。",
                        ),
                    )
                qdrant_save_col, qdrant_reset_col = st.columns(2)
                with qdrant_save_col:
                    save_qdrant = st.form_submit_button(localized_text("Save Qdrant Settings", "保存 Qdrant 配置", "保存 Qdrant 配置"), type="primary")
                with qdrant_reset_col:
                    reset_qdrant = st.form_submit_button(localized_text("Restore Default Qdrant Settings", "恢复默认 Qdrant 配置", "恢復預設 Qdrant 配置"))

            if save_qdrant:
                try:
                    save_qdrant_config(qdrant_mode, qdrant_local_path, qdrant_url, qdrant_api_key)
                    try:
                        get_file_summary_rows.clear()
                        get_cached_library_counts.clear()
                    except Exception:
                        pass
                    st.success(
                        localized_text(
                            "Qdrant settings saved. The vector client cache has been reset.",
                            "Qdrant 配置已保存，向量客户端缓存已重置。",
                            "Qdrant 配置已保存，向量客戶端快取已重置。",
                        )
                    )
                    st.rerun()
                except Exception as e:
                    st.error(localized_text(f"Failed to save Qdrant settings: {e}", f"保存 Qdrant 配置失败：{e}", f"保存 Qdrant 配置失敗：{e}"))

            if reset_qdrant:
                save_qdrant_config(DEFAULT_QDRANT_MODE, DEFAULT_QDRANT_LOCAL_PATH, DEFAULT_QDRANT_URL, DEFAULT_QDRANT_API_KEY)
                try:
                    get_file_summary_rows.clear()
                    get_cached_library_counts.clear()
                except Exception:
                    pass
                st.success(localized_text("Default Qdrant settings restored.", "已恢复默认 Qdrant 配置。", "已恢復預設 Qdrant 配置。"))
                st.rerun()

            with st.expander(localized_text("Current Effective Qdrant Settings", "当前生效的 Qdrant 配置", "目前生效的 Qdrant 配置"), expanded=False):
                masked_qdrant = get_qdrant_config()
                st.json(
                    {
                        "mode": masked_qdrant["mode"],
                        "local_path": masked_qdrant["local_path"],
                        "url": masked_qdrant["url"],
                        "api_key": masked_qdrant["api_key"],
                        "collection": COLLECTION_NAME,
                    }
                )

        with st.container(border=True):
            st.markdown(localized_text("#### Local To HTTP Migration", "#### 本地向量库迁移到 HTTP/Docker", "#### 本地向量庫遷移到 HTTP/Docker"))
            st.caption(
                localized_text(
                    "This copies existing vectors and payloads from the local qdrant_db to an HTTP/Docker Qdrant service. It does not reparse files or regenerate embeddings.",
                    "这里会把本地 qdrant_db 已有向量和 payload 复制到 HTTP/Docker Qdrant；不会重新解析文件，也不会重新生成向量。",
                    "這裡會把本地 qdrant_db 已有向量和 payload 複製到 HTTP/Docker Qdrant；不會重新解析文件，也不會重新生成向量。",
                )
            )
            migrate_col1, migrate_col2 = st.columns(2)
            with migrate_col1:
                migrate_source_path = st.text_input(
                    localized_text("Source Local Path", "来源本地路径", "來源本地路徑"),
                    value=current_qdrant["local_path"],
                    key="qdrant_migrate_source_path",
                    placeholder=localized_text(
                        "Example: qdrant_db",
                        "例如：qdrant_db",
                        "例如：qdrant_db",
                    ),
                )
                migrate_recreate = st.checkbox(
                    localized_text("Recreate Target Collection First", "先重建目标 Collection", "先重建目標 Collection"),
                    value=False,
                    key="qdrant_migrate_recreate",
                    help=localized_text(
                        "Enable this only if the target collection can be overwritten.",
                        "只有确认目标 Collection 可以覆盖时才勾选。",
                        "只有確認目標 Collection 可以覆蓋時才勾選。",
                    ),
                )
            with migrate_col2:
                migrate_target_url = st.text_input(
                    localized_text("Target HTTP URL", "目标 HTTP 地址", "目標 HTTP 地址"),
                    value=current_qdrant["url"],
                    key="qdrant_migrate_target_url",
                    placeholder=localized_text(
                        "Example: http://127.0.0.1:6333",
                        "例如：http://127.0.0.1:6333",
                        "例如：http://127.0.0.1:6333",
                    ),
                )
                migrate_target_key = st.text_input(
                    localized_text("Target API Key", "目标 API Key", "目標 API Key"),
                    value=current_qdrant["api_key"],
                    key="qdrant_migrate_target_key",
                    placeholder=localized_text(
                        "Leave empty if the target Qdrant service has no API key",
                        "目标 Qdrant 服务没有 API Key 时留空",
                        "目標 Qdrant 服務沒有 API Key 時留空",
                    ),
                )

            if st.button(localized_text("Copy Local Vectors To HTTP Qdrant", "复制本地向量到 HTTP Qdrant", "複製本地向量到 HTTP Qdrant"), key="migrate_qdrant_to_http"):
                progress_box = st.empty()
                try:
                    copied = migrate_local_qdrant_to_http(
                        target_url=migrate_target_url,
                        target_api_key=migrate_target_key,
                        source_path=migrate_source_path,
                        recreate_target=migrate_recreate,
                        progress_callback=lambda count: progress_box.info(
                            localized_text(
                                f"Copied {count} vector points...",
                                f"已复制 {count} 个向量点...",
                                f"已複製 {count} 個向量點...",
                            )
                        ),
                    )
                    st.success(
                        localized_text(
                            f"Migration completed. Copied {copied} vector points.",
                            f"迁移完成，已复制 {copied} 个向量点。",
                            f"遷移完成，已複製 {copied} 個向量點。",
                        )
                    )
                except Exception as e:
                    st.error(localized_text(f"Migration failed: {e}", f"迁移失败：{e}", f"遷移失敗：{e}"))

    with config_llm_tab:
        current_config = get_llm_config()
        with st.form("llm_config_form"):
            endpoint_col, mode_col = st.columns([1, 1])
            with endpoint_col:
                st.markdown("#### 接口")
                api_type_labels = list(LLM_API_TYPE_OPTIONS.keys())
                current_api_type = current_config.get("api_type", DEFAULT_LLM_API_TYPE)
                current_api_type_label = next(
                    (label for label, value in LLM_API_TYPE_OPTIONS.items() if value == current_api_type),
                    "自动识别",
                )
                api_type_label = st.selectbox(
                    "接口类型",
                    api_type_labels,
                    index=api_type_labels.index(current_api_type_label),
                    key="llm_api_type_label",
                    help=localized_text(
                        "Auto Detect tries OpenAI-compatible chat completions first, then Anthropic Messages. Choose a fixed type if your backend only supports one protocol.",
                        "自动识别会先尝试 OpenAI 兼容 Chat Completions，再尝试 Anthropic Messages。若后端只支持一种协议，可直接指定。",
                        "自動識別會先嘗試 OpenAI 相容 Chat Completions，再嘗試 Anthropic Messages。若後端只支援一種協議，可直接指定。",
                    ),
                )
                api_type = LLM_API_TYPE_OPTIONS[api_type_label]
                base_url = st.text_input(
                    "大模型接口 Base URL",
                    value=current_config["base_url"],
                    placeholder=localized_text("Example: http://127.0.0.1:27292/v1", "例如：http://127.0.0.1:27292/v1", "例如：http://127.0.0.1:27292/v1"),
                )
                api_key = st.text_input(
                    "API Key",
                    value=current_config["api_key"],
                    placeholder=localized_text(
                        "Use EMPTY if no authentication is required",
                        "没有鉴权时可填 EMPTY",
                        "沒有鑑權時可填 EMPTY",
                    ),
                )
                model = st.text_input(
                    "默认模型名称",
                    value=current_config["model"],
                    placeholder=localized_text(
                        "Enter the actual model name shown by OLMX / Ollama / LM Studio",
                        "填写 OLMX / Ollama / LM Studio 中显示的真实模型名",
                        "填寫 OLMX / Ollama / LM Studio 中顯示的真實模型名",
                    ),
                )
            with mode_col:
                st.markdown("#### 模式")
                fast_model = st.text_input(
                    "快速模式模型名",
                    value=current_config.get("fast_model", current_config["model"]),
                    placeholder=localized_text(
                        "Leave empty to use the default model name",
                        "留空则使用默认模型名称",
                        "留空則使用預設模型名稱",
                    ),
                )
                thinking_model = st.text_input(
                    "思考模式模型名",
                    value=current_config.get("thinking_model", current_config["model"]),
                    placeholder=localized_text(
                        "If the backend uses a separate thinking model, enter its name here",
                        "如果后端用不同模型区分快慢，可在这里填思考模型名",
                        "如果後端用不同模型區分快慢，可在這裡填思考模型名",
                    ),
                )
                st.caption(
                    localized_text(
                        "If your backend controls thinking mode through request parameters, configure them in extra_body. Keep {} if unsupported.",
                        "如果后端通过请求参数控制思考模式，可在 extra_body 中配置；不支持时保持 {}。",
                        "如果後端通過請求參數控制思考模式，可在 extra_body 中配置；不支援時保持 {}。",
                    )
                )

            extra_col1, extra_col2 = st.columns(2)
            with extra_col1:
                fast_extra_body = st.text_area(
                    "快速模式 extra_body JSON",
                    value=current_config.get("fast_extra_body", DEFAULT_LLM_EXTRA_BODY),
                    height=90,
                    placeholder=localized_text(
                        'Example: {"enable_thinking": false}',
                        '例如：{"enable_thinking": false}',
                        '例如：{"enable_thinking": false}',
                    ),
                )
            with extra_col2:
                thinking_extra_body = st.text_area(
                    "思考模式 extra_body JSON",
                    value=current_config.get("thinking_extra_body", DEFAULT_LLM_EXTRA_BODY),
                    height=90,
                    placeholder=localized_text(
                        'Example: {"enable_thinking": true}',
                        '例如：{"enable_thinking": true}',
                        '例如：{"enable_thinking": true}',
                    ),
                )

            col_save, col_reset = st.columns([1, 1])
            with col_save:
                save_config = st.form_submit_button("保存配置", type="primary")
            with col_reset:
                reset_config = st.form_submit_button("恢复默认值")

        if save_config:
            try:
                save_llm_config(
                    base_url,
                    api_key,
                    model,
                    api_type=api_type,
                    fast_model=fast_model,
                    thinking_model=thinking_model,
                    fast_extra_body=fast_extra_body,
                    thinking_extra_body=thinking_extra_body,
                )
                st.success(
                    localized_text(
                        "Settings saved to the local database and applied to the current session.",
                        "配置已保存到本地数据库，并已在当前会话生效。",
                        "配置已保存到本地資料庫，並已在當前會話生效。",
                    )
                )
            except Exception as e:
                st.error(localized_text(f"Save failed: {e}", f"保存失败：{e}", f"保存失敗：{e}"))

        if reset_config:
            try:
                save_llm_config(
                    DEFAULT_LLM_BASE_URL,
                    DEFAULT_LLM_API_KEY,
                    DEFAULT_LLM_MODEL,
                    api_type=DEFAULT_LLM_API_TYPE,
                    fast_model=DEFAULT_LLM_MODEL,
                    thinking_model=DEFAULT_LLM_MODEL,
                    fast_extra_body=DEFAULT_LLM_EXTRA_BODY,
                    thinking_extra_body=DEFAULT_LLM_EXTRA_BODY,
                )
                st.success(localized_text("Default settings restored.", "已恢复默认配置。", "已恢復預設配置。"))
                st.rerun()
            except Exception as e:
                st.error(localized_text(f"Restore failed: {e}", f"恢复失败：{e}", f"恢復失敗：{e}"))

        active_config = get_llm_config()
        test_col, active_col = st.columns([1, 2])
        with test_col:
            config_test_mode_options = list(LLM_MODE_OPTIONS.keys())
            saved_config_test_mode = get_config_value("config_test_mode_label", "快速")
            if saved_config_test_mode not in config_test_mode_options:
                saved_config_test_mode = "快速"
            test_mode_label = st.radio(
                "测试模式",
                config_test_mode_options,
                index=config_test_mode_options.index(saved_config_test_mode),
                horizontal=True,
                key="config_test_llm_mode_label",
            )
            set_config_value("config_test_mode_label", test_mode_label)
            test_mode = LLM_MODE_OPTIONS[test_mode_label]
            if st.button("测试当前配置", key="test_config_llm"):
                with st.status("正在测试本地大模型接口...", expanded=True) as status:
                    try:
                        test_model, test_extra_body = get_llm_mode_config(test_mode)
                        st.write(localized_text("Endpoint: ", "接口地址：", "接口地址：") + active_config["base_url"])
                        st.write(localized_text("Model name: ", "模型名称：", "模型名稱：") + test_model)
                        st.write(f"extra_body：{test_extra_body or {}}")
                        reply = test_llm_connection(mode=test_mode)
                        record_model_event(localized_text("Local LLM", "本地大模型", "本地大模型"), localized_text("Completed", "完成", "完成"), reply)
                        status.update(
                            label=localized_text(f"Endpoint available: {reply}", f"接口可用：{reply}", f"接口可用：{reply}"),
                            state="complete",
                        )
                    except Exception as e:
                        record_model_event(localized_text("Local LLM", "本地大模型", "本地大模型"), localized_text("Failed", "失败", "失敗"), str(e))
                        status.update(
                            label=localized_text(
                                f"Endpoint test failed: {e}",
                                f"接口测试失败：{e}",
                                f"接口測試失敗：{e}",
                            ),
                            state="error",
                        )
                        st.error(localized_text(f"Endpoint test failed: {e}", f"接口测试失败：{e}", f"接口測試失敗：{e}"))
        with active_col:
            with st.expander("当前生效配置", expanded=False):
                st.json(
                    {
                        "api_type": active_config.get("api_type", DEFAULT_LLM_API_TYPE),
                        "base_url": active_config["base_url"],
                        "api_key": active_config["api_key"],
                        "model": active_config["model"],
                        "fast_model": active_config.get("fast_model", active_config["model"]),
                        "thinking_model": active_config.get("thinking_model", active_config["model"]),
                        "fast_extra_body": active_config.get("fast_extra_body", DEFAULT_LLM_EXTRA_BODY),
                        "thinking_extra_body": active_config.get("thinking_extra_body", DEFAULT_LLM_EXTRA_BODY),
                    }
                )

    with config_reset_tab:
        with st.container(border=True):
            st.markdown("#### 初始化可配置数据")
            st.warning(
                localized_text(
                    "This clears model settings, UI settings, and all chat history. It does not delete the Qdrant library, uploaded files, or ingested vectors.",
                    "这里会清空模型配置、界面设置和所有历史会话；不会删除 Qdrant 文档库、上传文件和已入库向量。",
                    "這裡會清空模型配置、介面設定和所有歷史會話；不會刪除 Qdrant 文件庫、上傳文件和已入庫向量。",
                )
            )
            confirm_reset = st.checkbox("我确认要初始化可配置数据和历史会话", key="confirm_reset_app_state")
            if st.button("初始化可配置数据", type="primary", disabled=not confirm_reset):
                reset_app_state_database()
                st.session_state["app_reset_notice"] = localized_text(
                    "Settings and chat history have been reset.",
                    "已初始化配置和历史会话。",
                    "已初始化配置和歷史會話。",
                )
                st.rerun()
