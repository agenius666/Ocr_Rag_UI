"""Settings page UI.
配置中心页面 UI。
"""

from ..services import *
from .components import *


def render_settings_tab() -> None:
    st.subheader(localized_text("Settings", "配置中心", "配置中心"))
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
            st.markdown(localized_text("#### Interface Language", "#### 界面语言", "#### 介面語言"))
            current_language_code = get_ui_language()
            current_language_label = LANGUAGE_LABEL_BY_CODE.get(current_language_code, "English")
            selected_language_label = st.selectbox(
                localized_text("Select Interface Language", "选择界面语言", "選擇介面語言"),
                list(LANGUAGE_OPTIONS.keys()),
                index=list(LANGUAGE_OPTIONS.keys()).index(current_language_label),
                key="ui_language_selector",
            )
            st.caption(
                localized_text(
                    "The language preference is saved in app_state.sqlite3 and will be applied next time.",
                    "语言偏好会保存到 app_state.sqlite3，下次打开会自动生效。",
                    "語言偏好會保存到 app_state.sqlite3，下次打開會自動生效。",
                )
            )
            selected_language_code = LANGUAGE_OPTIONS[selected_language_label]
            if selected_language_code != current_language_code:
                set_config_value("ui_language", selected_language_code)
                st.success(localized_text("Language setting saved.", "语言设置已保存。", "語言設定已保存。"))
                st.rerun()

    with config_model_tab:
        with st.container(border=True):
            st.markdown(localized_text("#### Download And Install Sources", "#### 下载与安装源", "#### 下載與安裝源"))
            st.caption(
                localized_text(
                    "Configure download or installation sources for embedding models, rerankers, PaddleOCR, and LibreOffice.",
                    "配置文本向量化模型、重排模型、PaddleOCR 和 LibreOffice 的下载或安装来源。",
                    "配置文字向量化模型、重排模型、PaddleOCR 和 LibreOffice 的下載或安裝來源。",
                )
            )
            download_config = get_model_download_config()
            download_source_keys = list(MODEL_DOWNLOAD_SOURCE_OPTIONS.keys())
            download_source_labels = [get_model_download_source_label(source) for source in download_source_keys]
            current_download_source = download_config["source"]
            current_download_label = get_model_download_source_label(current_download_source)

            paddle_source_keys = list(PADDLEOCR_MODEL_SOURCE_OPTIONS.keys())
            paddle_source_labels = [get_paddleocr_model_source_label(source) for source in paddle_source_keys]
            current_paddle_source = download_config["paddleocr_source"]
            current_paddle_label = get_paddleocr_model_source_label(current_paddle_source)

            libreoffice_source_keys = list(LIBREOFFICE_INSTALL_SOURCE_OPTIONS.keys())
            libreoffice_source_labels = [get_libreoffice_install_source_label(source) for source in libreoffice_source_keys]
            current_libreoffice_source = download_config["libreoffice_install_source"]
            current_libreoffice_label = get_libreoffice_install_source_label(current_libreoffice_source)

            with st.form("model_download_source_form"):
                source_col1, source_col2 = st.columns(2)
                with source_col1:
                    selected_download_label = st.selectbox(
                        localized_text("Embedding / Reranker Source", "向量模型 / 重排模型下载源", "向量模型 / 重排模型下載源"),
                        download_source_labels,
                        index=download_source_labels.index(current_download_label),
                        key="model_download_source_select",
                        help=localized_text(
                            "Controls Hugging Face compatible downloads used by sentence-transformers for embedding and reranker models.",
                            "控制 sentence-transformers 下载文本向量化模型和重排模型时使用的 Hugging Face 兼容端点。",
                            "控制 sentence-transformers 下載文字向量化模型和重排模型時使用的 Hugging Face 相容端點。",
                        ),
                    )
                    selected_download_source = download_source_keys[download_source_labels.index(selected_download_label)]
                    custom_hf_endpoint = st.text_input(
                        localized_text("Custom Hugging Face Endpoint", "自定义 Hugging Face Endpoint", "自訂 Hugging Face Endpoint"),
                        value=get_custom_hf_endpoint(),
                        key="custom_hf_endpoint_input",
                        placeholder="https://hf-mirror.com",
                        help=localized_text(
                            "Only used when the embedding / reranker source is Custom. PaddleOCR also uses this endpoint when its source is Hugging Face.",
                            "仅当向量模型 / 重排模型下载源选择自定义时使用；PaddleOCR 下载源为 Hugging Face 时也会使用该端点。",
                            "僅當向量模型 / 重排模型下載源選擇自訂時使用；PaddleOCR 下載源為 Hugging Face 時也會使用該端點。",
                        ),
                    )
                with source_col2:
                    selected_paddle_label = st.selectbox(
                        localized_text("PaddleOCR Model Source", "PaddleOCR 模型下载源", "PaddleOCR 模型下載源"),
                        paddle_source_labels,
                        index=paddle_source_labels.index(current_paddle_label),
                        key="paddleocr_model_source_select",
                        help=localized_text(
                            "Controls PaddleX official model downloads for PaddleOCR detection, recognition, and orientation models.",
                            "控制 PaddleOCR 检测、识别、方向分类等 PaddleX 官方模型的下载来源。",
                            "控制 PaddleOCR 偵測、識別、方向分類等 PaddleX 官方模型的下載來源。",
                        ),
                    )
                    selected_paddle_source = paddle_source_keys[paddle_source_labels.index(selected_paddle_label)]
                    effective_hf_endpoint = (
                        custom_hf_endpoint.strip().rstrip("/")
                        if selected_download_source == "custom" and custom_hf_endpoint.strip()
                        else (HF_MIRROR_ENDPOINT if selected_download_source == "hf_mirror" else "https://huggingface.co")
                    )
                    st.caption(
                        localized_text(
                            f"Effective Hugging Face endpoint: {effective_hf_endpoint}",
                            f"生效的 Hugging Face 端点：{effective_hf_endpoint}",
                            f"生效的 Hugging Face 端點：{effective_hf_endpoint}",
                        )
                    )

                libre_col1, libre_col2 = st.columns([1, 2])
                with libre_col1:
                    selected_libreoffice_label = st.selectbox(
                        localized_text("LibreOffice Install Source", "LibreOffice 安装来源", "LibreOffice 安裝來源"),
                        libreoffice_source_labels,
                        index=libreoffice_source_labels.index(current_libreoffice_label),
                        key="libreoffice_install_source_select",
                        help=localized_text(
                            "LibreOffice is installed through the system package manager by default. Choose Custom to use your own mirror or internal package command.",
                            "LibreOffice 默认通过系统包管理器安装；选择自定义后可使用镜像源或内网安装命令。",
                            "LibreOffice 預設透過系統套件管理器安裝；選擇自訂後可使用鏡像源或內網安裝命令。",
                        ),
                    )
                    selected_libreoffice_source = libreoffice_source_keys[libreoffice_source_labels.index(selected_libreoffice_label)]
                with libre_col2:
                    custom_libreoffice_command = st.text_input(
                        localized_text("Custom LibreOffice Install Command", "自定义 LibreOffice 安装命令", "自訂 LibreOffice 安裝命令"),
                        value=get_custom_libreoffice_install_command(),
                        key="custom_libreoffice_install_command_input",
                        placeholder=localized_text(
                            "Example: brew install --cask libreoffice",
                            "示例：brew install --cask libreoffice",
                            "範例：brew install --cask libreoffice",
                        ),
                        help=localized_text(
                            "Only used when the LibreOffice install source is Custom. Use one executable command without shell operators such as &&. The app runs it only when you explicitly click automatic installation.",
                            "仅当 LibreOffice 安装来源选择自定义时使用。请填写单条可执行命令，不支持 && 等 shell 操作符；只有在你主动点击自动安装时才会执行。",
                            "僅當 LibreOffice 安裝來源選擇自訂時使用。請填寫單條可執行命令，不支援 && 等 shell 操作符；只有在你主動點擊自動安裝時才會執行。",
                        ),
                    )

                save_download_source = st.form_submit_button(
                    localized_text("Save Sources", "保存来源配置", "保存來源配置"),
                    type="primary",
                )

            if save_download_source:
                try:
                    save_model_download_config(
                        selected_download_source,
                        custom_hf_endpoint,
                        selected_paddle_source,
                        selected_libreoffice_source,
                        custom_libreoffice_command,
                    )
                    st.success(
                        localized_text(
                            "Download and install sources saved. OCR, embedding, and reranker caches were cleared; the next download/load will use the selected sources.",
                            "下载与安装源已保存，已清理 OCR、向量模型和重排模型加载缓存；下次下载/加载会使用所选来源。",
                            "下載與安裝源已保存，已清理 OCR、向量模型和重排模型載入快取；下次下載/載入會使用所選來源。",
                        )
                    )
                    st.rerun()
                except Exception as e:
                    st.error(
                        localized_text(
                            f"Failed to save download and install sources: {e}",
                            f"保存下载与安装源失败：{e}",
                            f"保存下載與安裝源失敗：{e}",
                        )
                    )

        ocr_col, model_col = st.columns([1, 2])
        with ocr_col:
            with st.container(border=True):
                st.markdown(localized_text("#### OCR Model", "#### OCR 模型", "#### OCR 模型"))
                paddleocr_model_labels = list(PADDLEOCR_MODEL_OPTIONS.keys())
                current_paddleocr_label = get_paddleocr_model_label()
                selected_paddleocr_label = st.selectbox(
                    localized_text("PaddleOCR Model", "PaddleOCR 模型", "PaddleOCR 模型"),
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

        with model_col:
            with st.container(border=True):
                st.markdown(localized_text("#### Embedding And Reranker Models", "#### 向量与重排模型", "#### 向量與重排模型"))
                st.caption(
                    localized_text(
                        "The embedding model controls vector dimensions and the active Qdrant collection. Switching models may point the app to a different vector store.",
                        "文本向量化模型决定向量维度和当前 Qdrant Collection。切换模型后，应用可能会指向另一套向量库。",
                        "文字向量化模型決定向量維度和目前 Qdrant Collection。切換模型後，應用可能會指向另一套向量庫。",
                    )
                )
                with st.form("model_cache_config_form"):
                    embedding_model_names = list(EMBEDDING_MODEL_OPTIONS.keys())
                    embedding_model_labels = [get_embedding_model_label(model_name) for model_name in embedding_model_names]
                    current_embedding_model = get_embedding_model_name()
                    selected_embedding_label = st.selectbox(
                        localized_text("Text Embedding Model", "文本向量化模型", "文字向量化模型"),
                        embedding_model_labels,
                        index=embedding_model_names.index(current_embedding_model),
                        key="embedding_model_name_select",
                        help=localized_text(
                            "Used for text vectorization and vector retrieval. Different models use different vector dimensions, so existing vectors cannot be reused directly.",
                            "用于文本向量化和向量检索。不同模型的向量维度不同，已有向量不能直接混用。",
                            "用於文字向量化和向量檢索。不同模型的向量維度不同，既有向量不能直接混用。",
                        ),
                    )
                    selected_embedding_model = embedding_model_names[embedding_model_labels.index(selected_embedding_label)]
                    reranker_model_names = list(RERANKER_MODEL_OPTIONS.keys())
                    reranker_model_labels = [get_reranker_model_label(model_name) for model_name in reranker_model_names]
                    current_reranker_model = get_reranker_model_name()
                    selected_reranker_label = st.selectbox(
                        localized_text("Candidate Reranker Model", "候选片段重排模型", "候選片段重排模型"),
                        reranker_model_labels,
                        index=reranker_model_names.index(current_reranker_model),
                        key="reranker_model_name_select",
                        help=localized_text(
                            "Only used when reranking is enabled in retrieval settings. Smaller rerankers usually use less memory but may be less accurate.",
                            "仅在检索设置中启用重排时使用。较小的重排模型通常更省内存，但精度可能下降。",
                            "僅在檢索設定中啟用重排時使用。較小的重排模型通常更省記憶體，但精度可能下降。",
                        ),
                    )
                    selected_reranker_model = reranker_model_names[reranker_model_labels.index(selected_reranker_label)]

                    confirm_embedding_switch = True
                    if selected_embedding_model != current_embedding_model:
                        st.warning(
                            localized_text(
                                "You are switching the embedding model. The app will use the collection matched to the new vector dimension. If that collection is empty or your backup uses another dimension, use Vector Store conversion or import a matching backup.",
                                "你正在切换文本向量化模型。应用会使用与新向量维度匹配的 Collection。如果该 Collection 为空，或备份维度不同，请使用向量库模型转换或导入匹配备份。",
                                "你正在切換文字向量化模型。應用會使用與新向量維度匹配的 Collection。如果該 Collection 為空，或備份維度不同，請使用向量庫模型轉換或導入匹配備份。",
                            )
                        )
                        st.info(
                            localized_text(
                                f"Current: {current_embedding_model} -> {get_collection_name_for_embedding_model(current_embedding_model)} ({get_embedding_vector_size(current_embedding_model)}D). New: {selected_embedding_model} -> {get_collection_name_for_embedding_model(selected_embedding_model)} ({get_embedding_vector_size(selected_embedding_model)}D).",
                                f"当前：{current_embedding_model} -> {get_collection_name_for_embedding_model(current_embedding_model)}（{get_embedding_vector_size(current_embedding_model)} 维）。新配置：{selected_embedding_model} -> {get_collection_name_for_embedding_model(selected_embedding_model)}（{get_embedding_vector_size(selected_embedding_model)} 维）。",
                                f"目前：{current_embedding_model} -> {get_collection_name_for_embedding_model(current_embedding_model)}（{get_embedding_vector_size(current_embedding_model)} 維）。新配置：{selected_embedding_model} -> {get_collection_name_for_embedding_model(selected_embedding_model)}（{get_embedding_vector_size(selected_embedding_model)} 維）。",
                            )
                        )
                        confirm_embedding_switch = st.checkbox(
                            localized_text(
                                "I understand that switching the embedding model changes the active vector collection.",
                                "我已了解切换向量模型会改变当前使用的向量库 Collection。",
                                "我已了解切換向量模型會改變目前使用的向量庫 Collection。",
                            ),
                            value=False,
                            key="confirm_embedding_model_switch",
                        )

                    model_cache_root = st.text_input(
                        localized_text("Default Model Root", "默认模型根目录", "預設模型根目錄"),
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
                            localized_text("PaddleOCR Model Directory", "PaddleOCR 模型目录", "PaddleOCR 模型目錄"),
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
                            localized_text("BAAI/bge-m3 Model Directory", "BAAI/bge-m3 模型目录", "BAAI/bge-m3 模型目錄"),
                            value=get_config_value("bge_cache_dir", ""),
                            key="bge_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-m3"),
                            help=localized_text(
                                "Cache directory for BAAI/bge-m3. Leave empty to use the default model root.",
                                "BAAI/bge-m3 的缓存目录；留空则使用默认模型根目录。",
                                "BAAI/bge-m3 的快取目錄；留空則使用預設模型根目錄。",
                            ),
                        )
                        bge_base_cache_dir = st.text_input(
                            localized_text("BAAI/bge-base-zh-v1.5 Model Directory", "BAAI/bge-base-zh-v1.5 模型目录", "BAAI/bge-base-zh-v1.5 模型目錄"),
                            value=get_config_value("bge_base_cache_dir", ""),
                            key="bge_base_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-base-zh-v1.5"),
                            help=localized_text(
                                "Cache directory for BAAI/bge-base-zh-v1.5. This model uses 768-dimensional vectors.",
                                "BAAI/bge-base-zh-v1.5 的缓存目录，该模型使用 768 维向量。",
                                "BAAI/bge-base-zh-v1.5 的快取目錄，該模型使用 768 維向量。",
                            ),
                        )
                    with path_input_col2:
                        reranker_cache_dir = st.text_input(
                            localized_text("BAAI/bge-reranker-v2-m3 Model Directory", "BAAI/bge-reranker-v2-m3 模型目录", "BAAI/bge-reranker-v2-m3 模型目錄"),
                            value=get_config_value("reranker_cache_dir", ""),
                            key="reranker_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-reranker-v2-m3"),
                            help=localized_text(
                                "Cache directory for BAAI/bge-reranker-v2-m3.",
                                "BAAI/bge-reranker-v2-m3 的缓存目录。",
                                "BAAI/bge-reranker-v2-m3 的快取目錄。",
                            ),
                        )
                        reranker_base_cache_dir = st.text_input(
                            localized_text("BAAI/bge-reranker-base Model Directory", "BAAI/bge-reranker-base 模型目录", "BAAI/bge-reranker-base 模型目錄"),
                            value=get_config_value("reranker_base_cache_dir", ""),
                            key="reranker_base_cache_dir_input",
                            placeholder=os.path.join(default_root_for_form, "bge-reranker-base"),
                            help=localized_text(
                                "Cache directory for BAAI/bge-reranker-base.",
                                "BAAI/bge-reranker-base 的缓存目录。",
                                "BAAI/bge-reranker-base 的快取目錄。",
                            ),
                        )
                        soffice_binary_path = st.text_input(
                            localized_text("LibreOffice / soffice Path", "LibreOffice / soffice 路径", "LibreOffice / soffice 路徑"),
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
                        save_model_paths = st.form_submit_button(
                            localized_text("Save Model Settings", "保存模型配置", "保存模型配置"),
                            type="primary",
                        )
                    with path_col_reset:
                        reset_model_paths = st.form_submit_button(localized_text("Restore Defaults", "恢复默认配置", "恢復預設配置"))

                if save_model_paths:
                    try:
                        if not confirm_embedding_switch:
                            raise ValueError(
                                localized_text(
                                    "Please confirm that switching the embedding model changes the active vector collection.",
                                    "请先确认已了解切换向量模型会改变当前使用的向量库 Collection。",
                                    "請先確認已了解切換向量模型會改變目前使用的向量庫 Collection。",
                                )
                            )
                        save_model_cache_config(
                            model_cache_root,
                            paddleocr_cache_dir,
                            bge_cache_dir,
                            bge_base_cache_dir,
                            reranker_cache_dir,
                            reranker_base_cache_dir,
                            soffice_binary_path,
                            selected_embedding_model,
                            selected_reranker_model,
                        )
                        if soffice_binary_path and not find_soffice_binary():
                            st.warning(
                                localized_text(
                                    "Model settings were saved, but the current LibreOffice / soffice path does not point to an executable file.",
                                    "模型配置已保存，但当前 LibreOffice / soffice 路径未检测到可执行文件。",
                                    "模型配置已保存，但當前 LibreOffice / soffice 路徑未檢測到可執行文件。",
                                )
                            )
                        else:
                            st.success(
                                localized_text(
                                    "Model settings saved. Loaded model and vector client caches were cleared; the next load will use the new settings.",
                                    "模型配置已保存，已清理模型和向量客户端缓存；下次加载会使用新配置。",
                                    "模型配置已保存，已清理模型和向量客戶端快取；下次載入會使用新配置。",
                                )
                            )
                        st.rerun()
                    except Exception as e:
                        st.error(localized_text(f"Failed to save model settings: {e}", f"保存模型配置失败：{e}", f"保存模型配置失敗：{e}"))

                if reset_model_paths:
                    try:
                        save_model_cache_config(
                            DEFAULT_MODEL_CACHE_ROOT,
                            "",
                            "",
                            "",
                            "",
                            "",
                            DEFAULT_SOFFICE_BINARY_PATH,
                            EMBEDDING_MODEL_NAME,
                            RERANKER_MODEL_NAME,
                        )
                        st.success(localized_text("Default model settings restored.", "已恢复默认模型配置。", "已恢復預設模型配置。"))
                        st.rerun()
                    except Exception as e:
                        st.error(localized_text(f"Failed to restore default model settings: {e}", f"恢复默认模型配置失败：{e}", f"恢復預設模型配置失敗：{e}"))

                current_download_config = get_model_download_config()
                with st.expander(localized_text("Current Paths", "当前路径", "當前路徑"), expanded=False):
                    st.json(
                        {
                            "embedding_model": get_embedding_model_name(),
                            "embedding_vector_size": get_embedding_vector_size(),
                            "active_collection": get_active_collection_name(),
                            "reranker_model": get_reranker_model_name(),
                            "model_cache_root": get_model_cache_root(),
                            "paddleocr_cache_dir": get_paddleocr_cache_dir(),
                            "bge_m3_cache_dir": get_embedding_cache_dir_for_model("BAAI/bge-m3"),
                            "bge_base_zh_v15_cache_dir": get_embedding_cache_dir_for_model("BAAI/bge-base-zh-v1.5"),
                            "bge_reranker_v2_m3_cache_dir": get_reranker_cache_dir_for_model("BAAI/bge-reranker-v2-m3"),
                            "bge_reranker_base_cache_dir": get_reranker_cache_dir_for_model("BAAI/bge-reranker-base"),
                            "huggingface_download_source": current_download_config["source_label"],
                            "huggingface_endpoint": current_download_config["hf_endpoint"],
                            "paddleocr_model_source": current_download_config["paddleocr_source_label"],
                            "paddleocr_huggingface_endpoint": current_download_config["paddleocr_hf_endpoint"],
                            "libreoffice_install_source": current_download_config["libreoffice_install_source_label"],
                            "custom_libreoffice_install_command": current_download_config["custom_libreoffice_install_command"],
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
                        "active_collection": get_active_collection_name(),
                        "embedding_model": get_embedding_model_name(),
                        "embedding_vector_size": get_embedding_vector_size(),
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

        with st.container(border=True):
            st.markdown(localized_text("#### Embedding Model Conversion", "#### 向量库模型转换", "#### 向量庫模型轉換"))
            st.caption(
                localized_text(
                    "Convert stored chunk text between supported embedding collections by re-embedding. It works with Local and HTTP/Docker Qdrant, and does not run OCR again.",
                    "通过重新向量化已保存的 chunk 文本，在受支持的 embedding collection 之间转换。支持本地和 HTTP/Docker Qdrant，不会重新 OCR。",
                    "透過重新向量化已保存的 chunk 文字，在受支援的 embedding collection 之間轉換。支援本地和 HTTP/Docker Qdrant，不會重新 OCR。",
                )
            )
            conversion_model_names = list(EMBEDDING_MODEL_OPTIONS.keys())
            conversion_model_labels = [get_embedding_model_label(model_name) for model_name in conversion_model_names]
            conv_col1, conv_col2 = st.columns(2)
            with conv_col1:
                source_conversion_label = st.selectbox(
                    localized_text("Source Embedding Model", "来源向量模型", "來源向量模型"),
                    conversion_model_labels,
                    index=conversion_model_names.index("BAAI/bge-m3"),
                    key="conversion_source_embedding_model",
                    help=localized_text(
                        "The collection created by this model will be read as the source.",
                        "读取该模型对应的 Collection 作为转换来源。",
                        "讀取該模型對應的 Collection 作為轉換來源。",
                    ),
                )
                source_conversion_model = conversion_model_names[conversion_model_labels.index(source_conversion_label)]
                recreate_target_collection = st.checkbox(
                    localized_text("Recreate Target Collection Before Conversion", "转换前重建目标 Collection", "轉換前重建目標 Collection"),
                    value=False,
                    key="conversion_recreate_target_collection",
                    help=localized_text(
                        "Enable only when the target collection can be overwritten.",
                        "只有确认目标 Collection 可以覆盖时才勾选。",
                        "只有確認目標 Collection 可以覆蓋時才勾選。",
                    ),
                )
            with conv_col2:
                target_default_index = 1 if len(conversion_model_names) > 1 else 0
                target_conversion_label = st.selectbox(
                    localized_text("Target Embedding Model", "目标向量模型", "目標向量模型"),
                    conversion_model_labels,
                    index=target_default_index,
                    key="conversion_target_embedding_model",
                    help=localized_text(
                        "The app writes converted vectors into the collection matched to this model's dimension.",
                        "转换后的向量会写入目标模型维度匹配的 Collection。",
                        "轉換後的向量會寫入目標模型維度匹配的 Collection。",
                    ),
                )
                target_conversion_model = conversion_model_names[conversion_model_labels.index(target_conversion_label)]
                conversion_batch_size = st.number_input(
                    localized_text("Conversion Batch Size", "转换批大小", "轉換批大小"),
                    min_value=1,
                    max_value=64,
                    value=16,
                    step=1,
                    key="conversion_batch_size",
                    help=localized_text(
                        "Smaller batches use less memory; larger batches may be faster.",
                        "批量越小越省内存，批量越大可能越快。",
                        "批次越小越省記憶體，批次越大可能越快。",
                    ),
                )

            st.info(
                localized_text(
                    f"Source collection: {get_collection_name_for_embedding_model(source_conversion_model)} ({get_embedding_vector_size(source_conversion_model)} dimensions). Target collection: {get_collection_name_for_embedding_model(target_conversion_model)} ({get_embedding_vector_size(target_conversion_model)} dimensions).",
                    f"来源 Collection：{get_collection_name_for_embedding_model(source_conversion_model)}（{get_embedding_vector_size(source_conversion_model)} 维）。目标 Collection：{get_collection_name_for_embedding_model(target_conversion_model)}（{get_embedding_vector_size(target_conversion_model)} 维）。",
                    f"來源 Collection：{get_collection_name_for_embedding_model(source_conversion_model)}（{get_embedding_vector_size(source_conversion_model)} 維）。目標 Collection：{get_collection_name_for_embedding_model(target_conversion_model)}（{get_embedding_vector_size(target_conversion_model)} 維）。",
                )
            )
            if source_conversion_model == target_conversion_model:
                st.warning(localized_text("Choose different source and target models.", "请选择不同的来源和目标模型。", "請選擇不同的來源和目標模型。"))
            if st.button(
                localized_text("Start Embedding Conversion", "开始向量库转换", "開始向量庫轉換"),
                key="start_embedding_conversion",
                disabled=source_conversion_model == target_conversion_model,
                type="primary",
            ):
                progress_box = st.empty()
                try:
                    converted = convert_vector_collection_embeddings(
                        source_model_name=source_conversion_model,
                        target_model_name=target_conversion_model,
                        recreate_target=recreate_target_collection,
                        batch_size=int(conversion_batch_size),
                        progress_callback=lambda count: progress_box.info(
                            localized_text(
                                f"Converted {count} chunks...",
                                f"已转换 {count} 个 chunk...",
                                f"已轉換 {count} 個 chunk...",
                            )
                        ),
                    )
                    get_file_summary_rows.clear()
                    get_cached_library_counts.clear()
                    st.success(
                        localized_text(
                            f"Conversion completed. Converted {converted} chunks.",
                            f"转换完成，已转换 {converted} 个 chunk。",
                            f"轉換完成，已轉換 {converted} 個 chunk。",
                        )
                    )
                except Exception as e:
                    st.error(localized_text(f"Conversion failed: {e}", f"转换失败：{e}", f"轉換失敗：{e}"))

    with config_llm_tab:
        current_config = get_llm_config()
        with st.form("llm_config_form"):
            endpoint_col, mode_col = st.columns([1, 1])
            with endpoint_col:
                st.markdown(localized_text("#### Endpoint", "#### 接口", "#### 接口"))
                api_type_labels = list(LLM_API_TYPE_OPTIONS.keys())
                current_api_type = current_config.get("api_type", DEFAULT_LLM_API_TYPE)
                current_api_type_label = next(
                    (label for label, value in LLM_API_TYPE_OPTIONS.items() if value == current_api_type),
                    "自动识别",
                )
                api_type_label = st.selectbox(
                    localized_text("API Type", "接口类型", "接口類型"),
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
                    localized_text("LLM Base URL", "大模型接口 Base URL", "大模型接口 Base URL"),
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
                    localized_text("Default Model Name", "默认模型名称", "預設模型名稱"),
                    value=current_config["model"],
                    placeholder=localized_text(
                        "Enter the actual model name shown by OLMX / Ollama / LM Studio",
                        "填写 OLMX / Ollama / LM Studio 中显示的真实模型名",
                        "填寫 OLMX / Ollama / LM Studio 中顯示的真實模型名",
                    ),
                )
            with mode_col:
                st.markdown(localized_text("#### Modes", "#### 模式", "#### 模式"))
                fast_model = st.text_input(
                    localized_text("Fast Mode Model", "快速模式模型名", "快速模式模型名"),
                    value=current_config.get("fast_model", current_config["model"]),
                    placeholder=localized_text(
                        "Leave empty to use the default model name",
                        "留空则使用默认模型名称",
                        "留空則使用預設模型名稱",
                    ),
                )
                thinking_model = st.text_input(
                    localized_text("Thinking Mode Model", "思考模式模型名", "思考模式模型名"),
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
                request_timeout = st.number_input(
                    localized_text("Request Timeout Seconds", "请求超时时间（秒）", "請求逾時時間（秒）"),
                    min_value=1,
                    max_value=3600,
                    value=get_llm_request_timeout(),
                    step=10,
                    help=localized_text(
                        "Maximum waiting time for a single LLM request. Long local generations can use 120-300 seconds.",
                        "单次大模型请求的最长等待时间。本地模型生成较慢时可设置为 120-300 秒。",
                        "單次大模型請求的最長等待時間。本地模型生成較慢時可設定為 120-300 秒。",
                    ),
                )

            extra_col1, extra_col2 = st.columns(2)
            with extra_col1:
                fast_extra_body = st.text_area(
                    localized_text("Fast Mode extra_body JSON", "快速模式 extra_body JSON", "快速模式 extra_body JSON"),
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
                    localized_text("Thinking Mode extra_body JSON", "思考模式 extra_body JSON", "思考模式 extra_body JSON"),
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
                save_config = st.form_submit_button(localized_text("Save Settings", "保存配置", "保存配置"), type="primary")
            with col_reset:
                reset_config = st.form_submit_button(localized_text("Restore Defaults", "恢复默认值", "恢復預設值"))

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
                    request_timeout=int(request_timeout),
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
                    request_timeout=DEFAULT_LLM_REQUEST_TIMEOUT,
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
                localized_text("Test Mode", "测试模式", "測試模式"),
                config_test_mode_options,
                index=config_test_mode_options.index(saved_config_test_mode),
                horizontal=True,
                key="config_test_llm_mode_label",
            )
            set_config_value("config_test_mode_label", test_mode_label)
            test_mode = LLM_MODE_OPTIONS[test_mode_label]
            if st.button(localized_text("Test Current Settings", "测试当前配置", "測試當前配置"), key="test_config_llm"):
                with st.status(localized_text("Testing local LLM endpoint...", "正在测试本地大模型接口...", "正在測試本地大模型接口..."), expanded=True) as status:
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
            with st.expander(localized_text("Current Effective Settings", "当前生效配置", "當前生效配置"), expanded=False):
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
                        "request_timeout": active_config.get("request_timeout", str(DEFAULT_LLM_REQUEST_TIMEOUT)),
                    }
                )

    with config_reset_tab:
        with st.container(border=True):
            st.markdown(localized_text("#### Reset Configurable Data", "#### 初始化可配置数据", "#### 初始化可配置資料"))
            st.warning(
                localized_text(
                    "This clears model settings, UI settings, and all chat history. It does not delete the Qdrant library, uploaded files, or ingested vectors.",
                    "这里会清空模型配置、界面设置和所有历史会话；不会删除 Qdrant 文档库、上传文件和已入库向量。",
                    "這裡會清空模型配置、介面設定和所有歷史會話；不會刪除 Qdrant 文件庫、上傳文件和已入庫向量。",
                )
            )
            confirm_reset = st.checkbox(
                localized_text(
                    "I confirm resetting configurable data and chat history.",
                    "我确认要初始化可配置数据和历史会话。",
                    "我確認要初始化可配置資料和歷史會話。",
                ),
                key="confirm_reset_app_state",
            )
            if st.button(localized_text("Reset Configurable Data", "初始化可配置数据", "初始化可配置資料"), type="primary", disabled=not confirm_reset):
                reset_app_state_database()
                st.session_state["app_reset_notice"] = localized_text(
                    "Settings and chat history have been reset.",
                    "已初始化配置和历史会话。",
                    "已初始化配置和歷史會話。",
                )
                st.rerun()
