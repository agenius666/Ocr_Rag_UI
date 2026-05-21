"""Streamlit application entrypoint.
Streamlit 应用启动入口。
"""

from .services import *
from .ui.upload import render_upload_tab
from .ui.search import render_search_tab
from .ui.compliance import render_compliance_tab
from .ui.batch_excel import render_batch_excel_tab
from .ui.settings import render_settings_tab
from .ui.model_status import render_model_status_tab
from .ui.library import render_library_tab


def run_app() -> None:
    """Render the full Streamlit UI on every rerun.
    每次 Streamlit 重跑时重新渲染完整页面。
    """
    ensure_session_defaults()
    render_global_styles()
    st.title(
        localized_text(
            "OCR + BGE-M3 + Qdrant + Local LLM",
            "OCR + BGE-M3 + Qdrant + 本地大模型",
            "OCR + BGE-M3 + Qdrant + 本地大模型",
        )
    )
    st.caption(
        localized_text(
            "Upload policies, regulatory requirements, and enterprise materials. The app parses them into Qdrant, then uses a local LLM API for Q&A and compliance gap analysis.",
            "上传制度、监管要求和企业资料，解析后写入 Qdrant 向量库，再调用本地大模型接口做问答和合规差距分析。",
            "上傳制度、監管要求和企業資料，解析後寫入 Qdrant 向量庫，再調用本地大模型接口做問答和合規差距分析。",
        )
    )

    tab_upload, tab_search, tab_compliance, tab_batch, tab_config, tab_models, tab_manage = st.tabs(
        [
            localized_text("Ingest", "上传入库", "上傳入庫"),
            localized_text("RAG Chat", "检索问答", "檢索問答"),
            localized_text("Compliance", "合规分析", "合規分析"),
            localized_text("Batch Analysis", "批量分析", "批次分析"),
            localized_text("Settings", "配置中心", "配置中心"),
            localized_text("Model Status", "模型状态", "模型狀態"),
            localized_text("Document Library", "文档库管理", "文件庫管理"),
        ]
    )

    with tab_upload:
        render_upload_tab()

    with tab_search:
        render_search_tab()

    with tab_compliance:
        render_compliance_tab()

    with tab_batch:
        render_batch_excel_tab()

    with tab_config:
        render_settings_tab()

    with tab_models:
        render_model_status_tab()

    with tab_manage:
        render_library_tab()
