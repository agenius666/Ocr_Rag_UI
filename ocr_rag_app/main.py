"""Streamlit application entrypoint.
Streamlit 应用启动入口。
"""

from .services import *
from .ui.upload import render_upload_tab
from .ui.search import render_search_tab
from .ui.compliance import render_compliance_tab
from .ui.batch_excel import render_batch_excel_tab
from .ui.distillation import render_distillation_tab
from .ui.settings import render_settings_tab
from .ui.model_status import render_model_status_tab
from .ui.library import render_library_tab


def run_app() -> None:
    """Render only the selected UI section on each rerun.
    每次 Streamlit 重跑时只渲染当前选中的功能区，降低页面重跑成本。
    """
    ensure_session_defaults()
    render_global_styles()
    st.title(
        localized_text(
            "OCR + BGE + Qdrant + Local LLM",
            "OCR + BGE + Qdrant + 本地大模型",
            "OCR + BGE + Qdrant + 本地大模型",
        )
    )
    st.caption(
        localized_text(
            "Upload policies, regulatory requirements, and enterprise materials. The app parses them into Qdrant, then uses a local LLM API for Q&A and compliance gap analysis.",
            "上传制度、监管要求和企业资料，解析后写入 Qdrant 向量库，再调用本地大模型接口做问答和合规差距分析。",
            "上傳制度、監管要求和企業資料，解析後寫入 Qdrant 向量庫，再調用本地大模型接口做問答和合規差距分析。",
        )
    )

    section_labels = {
        "upload": localized_text("Ingest", "上传入库", "上傳入庫"),
        "search": localized_text("RAG Chat", "检索问答", "檢索問答"),
        "compliance": localized_text("Compliance", "合规分析", "合規分析"),
        "batch": localized_text("Batch Analysis", "批量分析", "批次分析"),
        "distillation": localized_text(
            "Distillation Data Generation (Advanced)",
            "蒸馏数据生成（高级）",
            "蒸餾資料生成（進階）",
        ),
        "settings": localized_text("Settings", "配置中心", "配置中心"),
        "models": localized_text("Model Status", "模型状态", "模型狀態"),
        "library": localized_text("Document Library", "文档库管理", "文件庫管理"),
    }
    section_order = list(section_labels.keys())
    with st.container(key="main_navigation_tabs"):
        selected_section = st.radio(
            localized_text("Main Navigation", "主导航", "主導覽"),
            section_order,
            index=section_order.index(st.session_state.get("main_section", "upload"))
            if st.session_state.get("main_section", "upload") in section_order
            else 0,
            format_func=lambda key: section_labels[key],
            horizontal=True,
            label_visibility="collapsed",
            key="main_section",
        )

    if selected_section == "upload":
        render_upload_tab()
    elif selected_section == "search":
        render_search_tab()
    elif selected_section == "compliance":
        render_compliance_tab()
    elif selected_section == "batch":
        render_batch_excel_tab()
    elif selected_section == "distillation":
        render_distillation_tab()
    elif selected_section == "settings":
        render_settings_tab()
    elif selected_section == "models":
        render_model_status_tab()
    elif selected_section == "library":
        render_library_tab()
