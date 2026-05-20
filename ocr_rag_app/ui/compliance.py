"""Compliance analysis page UI.
合规分析页面 UI。
"""

from ..services import *
from .components import *


def render_compliance_tab() -> None:
    st.subheader("多轮合规差距分析")
    render_library_summary()
    compliance_session_id, compliance_messages = render_chat_session_controls("compliance")

    with st.expander("分析与检索设置", expanded=False):
        col_reg, col_ent, col_mode, col_context = st.columns([1, 1, 1, 1])
        with col_reg:
            regulation_top_k = st.slider(
                "召回监管 / 规章片段数量",
                min_value=1,
                max_value=20,
                value=get_int_config("compliance_regulation_top_k", DEFAULT_COMPLIANCE_REGULATION_TOP_K),
                step=1,
                key="regulation_top_k",
            )
            set_config_value("compliance_regulation_top_k", regulation_top_k)
        with col_ent:
            enterprise_top_k = st.slider(
                "召回企业资料片段数量",
                min_value=1,
                max_value=20,
                value=get_int_config("compliance_enterprise_top_k", DEFAULT_COMPLIANCE_ENTERPRISE_TOP_K),
                step=1,
                key="enterprise_top_k",
            )
            set_config_value("compliance_enterprise_top_k", enterprise_top_k)
        with col_mode:
            compliance_mode_options = list(LLM_MODE_OPTIONS.keys())
            saved_compliance_mode_label = get_config_value("compliance_mode_label", "快速")
            if saved_compliance_mode_label not in compliance_mode_options:
                saved_compliance_mode_label = "快速"
            compliance_mode_label = st.radio(
                "分析模式",
                compliance_mode_options,
                index=compliance_mode_options.index(saved_compliance_mode_label),
                horizontal=True,
                key="compliance_llm_mode_label",
            )
            set_config_value("compliance_mode_label", compliance_mode_label)
            compliance_mode = LLM_MODE_OPTIONS[compliance_mode_label]
        with col_context:
            compliance_context_turns = st.slider(
                "上下文轮数",
                min_value=0,
                max_value=20,
                value=get_int_config("compliance_context_turns", DEFAULT_CONTEXT_TURNS),
                step=1,
                key="compliance_context_turns_input",
                help="只把最近 N 轮合规分析对话放进模型上下文；历史仍会保存在数据库。",
            )
            set_config_value("compliance_context_turns", compliance_context_turns)

        query_col, threshold_col, distance_col = st.columns([1.2, 1.2, 1])
        with query_col:
            compliance_query_rewrite = st.checkbox(
                "追问补全成完整检索问题",
                value=get_bool_config("compliance_query_rewrite", True),
                key="compliance_query_rewrite_input",
                help="合规多轮分析中把追问补全成完整检索问题。",
            )
            set_bool_config("compliance_query_rewrite", compliance_query_rewrite)
            compliance_query_decompose = st.checkbox(
                "复杂问题拆解后分别检索",
                value=get_bool_config("compliance_query_decompose", DEFAULT_QUERY_DECOMPOSE),
                key="compliance_query_decompose_input",
                help="复杂合规问题会拆成多个子问题分别检索，再合并监管和企业证据。",
            )
            set_bool_config("compliance_query_decompose", compliance_query_decompose)
        with threshold_col:
            compliance_use_distance_threshold = st.checkbox(
                "启用向量距离阈值过滤",
                value=get_bool_config("compliance_use_distance_threshold", True),
                key="compliance_use_distance_threshold_input",
                help="分别过滤监管资料和企业资料里的弱相关片段。",
            )
            set_bool_config("compliance_use_distance_threshold", compliance_use_distance_threshold)
        with distance_col:
            compliance_max_distance = st.slider(
                "最大距离",
                min_value=0.20,
                max_value=2.00,
                value=min(
                    max(get_float_config("compliance_max_distance", DEFAULT_VECTOR_MAX_DISTANCE), 0.20),
                    2.00,
                ),
                step=0.05,
                key="compliance_max_distance_input",
                disabled=not compliance_use_distance_threshold,
            )
            set_config_value("compliance_max_distance", compliance_max_distance)

        strategy_col1, strategy_col2, strategy_col3 = st.columns([1, 1, 1])
        with strategy_col1:
            compliance_use_hybrid = st.checkbox(
                "启用混合检索",
                value=get_bool_config("compliance_use_hybrid", DEFAULT_USE_HYBRID_SEARCH),
                key="compliance_use_hybrid_input",
                help="同时使用向量语义检索和关键词检索，适合条款号、制度名称、部门名称。",
            )
            set_bool_config("compliance_use_hybrid", compliance_use_hybrid)
        with strategy_col2:
            compliance_use_reranker = st.checkbox(
                "启用重排模型",
                value=get_bool_config("compliance_use_reranker", DEFAULT_USE_RERANKER),
                key="compliance_use_reranker_input",
                help="分别对监管资料和企业资料做候选重排；更准但会增加内存和耗时。",
            )
            set_bool_config("compliance_use_reranker", compliance_use_reranker)
        with strategy_col3:
            max_selected_top_k = max(regulation_top_k, enterprise_top_k)
            compliance_fetch_k = st.slider(
                "候选召回数",
                min_value=max_selected_top_k,
                max_value=50,
                value=min(
                    max(get_int_config("compliance_fetch_k", DEFAULT_RETRIEVAL_FETCH_K), max_selected_top_k),
                    50,
                ),
                step=1,
                key="compliance_fetch_k_input",
                help="用于混合检索和重排的候选数量。",
            )
            set_config_value("compliance_fetch_k", compliance_fetch_k)

        coverage_col1, coverage_col2, coverage_col3, coverage_col4 = st.columns([1, 1, 1, 1])
        with coverage_col1:
            compliance_min_regulation_evidence = st.slider(
                "监管最少证据数",
                min_value=0,
                max_value=regulation_top_k,
                value=min(
                    max(
                        get_int_config(
                            "compliance_min_regulation_evidence",
                            DEFAULT_COMPLIANCE_MIN_REGULATION_EVIDENCE,
                        ),
                        0,
                    ),
                    regulation_top_k,
                ),
                step=1,
                key="compliance_min_regulation_evidence_input",
                help="合规分析会尽量保证监管证据不少于该数量；不足时会放宽距离阈值补齐。",
            )
            set_config_value("compliance_min_regulation_evidence", compliance_min_regulation_evidence)
        with coverage_col2:
            compliance_min_enterprise_evidence = st.slider(
                "企业最少证据数",
                min_value=0,
                max_value=enterprise_top_k,
                value=min(
                    max(
                        get_int_config(
                            "compliance_min_enterprise_evidence",
                            DEFAULT_COMPLIANCE_MIN_ENTERPRISE_EVIDENCE,
                        ),
                        0,
                    ),
                    enterprise_top_k,
                ),
                step=1,
                key="compliance_min_enterprise_evidence_input",
                help="合规分析会尽量保证企业资料证据不少于该数量；不足时会放宽距离阈值补齐。",
            )
            set_config_value("compliance_min_enterprise_evidence", compliance_min_enterprise_evidence)
        with coverage_col3:
            compliance_clause_by_clause = st.checkbox(
                "按监管条款逐条对照",
                value=get_bool_config("compliance_clause_by_clause", False),
                key="compliance_clause_by_clause_input",
                help="适合监管条款较清晰的场景，模型会尽量一条监管要求对应一行分析。",
            )
            set_bool_config("compliance_clause_by_clause", compliance_clause_by_clause)
        with coverage_col4:
            compliance_include_missing_list = st.checkbox(
                "输出资料不足清单",
                value=get_bool_config("compliance_include_missing_list", True),
                key="compliance_include_missing_list_input",
                help="要求模型列出还需要补充哪些企业资料，并可一起导出 Excel。",
            )
            set_bool_config("compliance_include_missing_list", compliance_include_missing_list)

        if st.button("清空合规分析对话", key="clear_compliance_chat"):
            clear_chat_session(compliance_session_id)
            st.rerun()

    render_compliance_chat_panel(compliance_messages)

    with st.form("compliance_chat_form", clear_on_submit=True):
        topic = st.text_area(
            "输入合规分析问题",
            placeholder="例如：数据安全管理制度是否满足监管要求？供应商准入流程有什么合规缺口？",
            height=88,
            key="compliance_chat_text",
        )
        send_compliance = st.form_submit_button("发送", type="primary")

    if send_compliance:
        topic = topic.strip()
        if not topic:
            st.warning("请输入分析主题。")
            st.stop()

        chat_history = get_chat_messages(compliance_session_id)
        append_chat_message(compliance_session_id, "user", topic)
        if not chat_history:
            maybe_update_session_title(compliance_session_id, topic)

        regulation_results = []
        enterprise_results = []
        answer = ""
        structured_rows = []
        retrieval_query = topic
        query_rewrite_error = None
        retrieval_sub_queries = []
        query_decompose_error = None

        if count_chunks("regulation") == 0:
            answer = localized_text(
                "Please upload and ingest regulatory requirements or policies first.",
                "请先上传并入库监管要求或规章制度。",
                "請先上傳並入庫監管要求或規章制度。",
            )
        elif count_chunks("enterprise") == 0:
            answer = localized_text(
                "Please upload and ingest enterprise materials first.",
                "请先上传并入库企业资料。",
                "請先上傳並入庫企業資料。",
            )
        else:
            try:
                with st.spinner("正在检索并生成合规分析..."):
                    retrieval_query, query_rewrite_error = maybe_rewrite_retrieval_query(
                        topic,
                        chat_history=chat_history,
                        enabled=compliance_query_rewrite,
                        mode=compliance_mode,
                        context_turns=compliance_context_turns,
                        purpose="compliance",
                    )
                    retrieval_sub_queries, query_decompose_error = decompose_retrieval_query(
                        retrieval_query,
                        enabled=compliance_query_decompose,
                        mode=compliance_mode,
                        purpose="compliance",
                    )
                    regulation_results = search_with_min_coverage(
                        retrieval_sub_queries,
                        top_k=regulation_top_k,
                        min_results=compliance_min_regulation_evidence,
                        doc_category="regulation",
                        max_distance=compliance_max_distance if compliance_use_distance_threshold else None,
                        fetch_k=compliance_fetch_k,
                        use_hybrid=compliance_use_hybrid,
                        use_reranker=compliance_use_reranker,
                    )
                    enterprise_results = search_with_min_coverage(
                        retrieval_sub_queries,
                        top_k=enterprise_top_k,
                        min_results=compliance_min_enterprise_evidence,
                        doc_category="enterprise",
                        max_distance=compliance_max_distance if compliance_use_distance_threshold else None,
                        fetch_k=compliance_fetch_k,
                        use_hybrid=compliance_use_hybrid,
                        use_reranker=compliance_use_reranker,
                    )

                    if not regulation_results:
                        if compliance_use_distance_threshold:
                            answer = localized_text(
                                'No relevant regulatory requirements met the current distance threshold. Increase "Max Distance" in analysis settings or temporarily disable threshold filtering.',
                                "没有检索到满足当前距离阈值的相关监管要求。可以在分析设置里调大“最大距离”或暂时关闭阈值过滤。",
                                "沒有檢索到滿足當前距離閾值的相關監管要求。可以在分析設定裡調大「最大距離」或暫時關閉閾值過濾。",
                            )
                        else:
                            answer = localized_text(
                                "No relevant regulatory requirements were retrieved.",
                                "没有检索到相关监管要求。",
                                "沒有檢索到相關監管要求。",
                            )
                    elif not enterprise_results:
                        if compliance_use_distance_threshold:
                            answer = localized_text(
                                'No relevant enterprise materials met the current distance threshold. Increase "Max Distance" in analysis settings or temporarily disable threshold filtering.',
                                "没有检索到满足当前距离阈值的相关企业资料。可以在分析设置里调大“最大距离”或暂时关闭阈值过滤。",
                                "沒有檢索到滿足當前距離閾值的相關企業資料。可以在分析設定裡調大「最大距離」或暫時關閉閾值過濾。",
                            )
                        else:
                            answer = localized_text(
                                "No relevant enterprise materials were retrieved.",
                                "没有检索到相关企业资料。",
                                "沒有檢索到相關企業資料。",
                            )
                    else:
                        answer = ask_llm_compliance(
                            topic,
                            regulation_results,
                            enterprise_results,
                            chat_history=chat_history,
                            mode=compliance_mode,
                            context_turns=compliance_context_turns,
                            clause_by_clause=compliance_clause_by_clause,
                            include_missing_list=compliance_include_missing_list,
                        )
                        structured_rows = parse_markdown_table(answer)
            except Exception as e:
                answer = localized_text(
                    f"Compliance analysis failed: {e}",
                    f"合规分析失败：{e}",
                    f"合規分析失敗：{e}",
                )

        append_chat_message(
            compliance_session_id,
            "assistant",
            answer,
            {
                "regulation_results": regulation_results,
                "enterprise_results": enterprise_results,
                "structured_rows": structured_rows,
                "retrieval_query": retrieval_query,
                "retrieval_sub_queries": retrieval_sub_queries,
                "query_rewrite_error": query_rewrite_error,
                "query_decompose_error": query_decompose_error,
                "mode": compliance_mode,
                "mode_label": compliance_mode_label,
            },
        )
        st.rerun()
