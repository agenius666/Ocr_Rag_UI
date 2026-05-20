"""Streamlit application entrypoint.
Streamlit 应用启动入口。
"""

from .services import *
from .ui.upload import render_upload_tab
from .ui.search import render_search_tab
from .ui.compliance import render_compliance_tab
from .ui.settings import render_settings_tab
from .ui.model_status import render_model_status_tab
from .ui.library import render_library_tab

tab_upload, tab_search, tab_compliance, tab_config, tab_models, tab_manage = st.tabs(
    ["上传入库", "检索问答", "合规分析", "配置中心", "模型状态", "文档库管理"]
)

with tab_upload:
    render_upload_tab()

with tab_search:
    render_search_tab()

with tab_compliance:
    render_compliance_tab()

with tab_config:
    render_settings_tab()

with tab_models:
    render_model_status_tab()

with tab_manage:
    render_library_tab()
