"""RAG chat page UI.
检索问答页面 UI。
"""

from ..services import *
from .components import *


def render_search_tab() -> None:
    st.subheader("多轮检索问答")
    render_library_summary()
    rag_session_id, rag_messages = render_chat_session_controls("rag")

    with st.expander("对话与检索设置", expanded=False):
        setting_col1, setting_col2, setting_col3, setting_col4 = st.columns([1.2, 1, 1, 1])
        with setting_col1:
            scope_options = ["全部资料", *DOC_CATEGORY_OPTIONS.keys()]
            saved_scope = get_config_value("rag_search_scope_label", "全部资料")
            if saved_scope not in scope_options:
                saved_scope = "全部资料"
            search_scope_label = st.selectbox(
                "检索范围",
                scope_options,
                index=scope_options.index(saved_scope),
                key="rag_search_scope_label",
            )
            set_config_value("rag_search_scope_label", search_scope_label)
            search_category = None if search_scope_label == "全部资料" else DOC_CATEGORY_OPTIONS[search_scope_label]
        with setting_col2:
            top_k = st.slider(
                "召回片段数量",
                min_value=1,
                max_value=20,
                value=get_int_config("rag_top_k", DEFAULT_RAG_TOP_K),
                step=1,
                key="search_top_k",
                help="普通问答建议 3-5，太大会把弱相关片段带进上下文。",
            )
            set_config_value("rag_top_k", top_k)
        with setting_col3:
            mode_options = list(LLM_MODE_OPTIONS.keys())
            saved_mode_label = get_config_value("rag_mode_label", "快速")
            if saved_mode_label not in mode_options:
                saved_mode_label = "快速"
            mode_label = st.radio(
                "回答模式",
                mode_options,
                index=mode_options.index(saved_mode_label),
                horizontal=True,
                key="chat_llm_mode_label",
            )
            set_config_value("rag_mode_label", mode_label)
            chat_mode = LLM_MODE_OPTIONS[mode_label]
        with setting_col4:
            rag_context_turns = st.slider(
                "上下文轮数",
                min_value=0,
                max_value=20,
                value=get_int_config("rag_context_turns", DEFAULT_CONTEXT_TURNS),
                step=1,
                key="rag_context_turns_input",
                help="只把最近 N 轮对话放进模型上下文；历史仍会保存在数据库。",
            )
            set_config_value("rag_context_turns", rag_context_turns)

        allow_general_fallback = st.checkbox(
            "未检索到资料时使用本地大模型普通聊天",
            value=get_bool_config("rag_allow_general_fallback", True),
            key="rag_allow_general_fallback_input",
            help="当向量库无匹配结果时，允许模型按通用对话方式回复；涉及本地文档的问题仍以入库检索结果为准。",
        )
        set_bool_config("rag_allow_general_fallback", allow_general_fallback)

        query_col, threshold_col, distance_col = st.columns([1.2, 1.2, 1])
        with query_col:
            rag_query_rewrite = st.checkbox(
                "追问补全成完整检索问题",
                value=get_bool_config("rag_query_rewrite", True),
                key="rag_query_rewrite_input",
                help="多轮对话中把追问补全成完整问题后再检索。",
            )
            set_bool_config("rag_query_rewrite", rag_query_rewrite)
            rag_query_decompose = st.checkbox(
                "复杂问题拆解后分别检索",
                value=get_bool_config("rag_query_decompose", DEFAULT_QUERY_DECOMPOSE),
                key="rag_query_decompose_input",
                help="问题包含多个事项时，会拆成子问题分别检索后合并证据。",
            )
            set_bool_config("rag_query_decompose", rag_query_decompose)
        with threshold_col:
            rag_use_distance_threshold = st.checkbox(
                "启用向量距离阈值过滤",
                value=get_bool_config("rag_use_distance_threshold", True),
                key="rag_use_distance_threshold_input",
                help="过滤距离过大的弱相关片段；如果经常召回不到，可调大右侧阈值。",
            )
            set_bool_config("rag_use_distance_threshold", rag_use_distance_threshold)
        with distance_col:
            rag_max_distance = st.slider(
                "最大距离",
                min_value=0.20,
                max_value=2.00,
                value=min(max(get_float_config("rag_max_distance", DEFAULT_VECTOR_MAX_DISTANCE), 0.20), 2.00),
                step=0.05,
                key="rag_max_distance_input",
                disabled=not rag_use_distance_threshold,
            )
            set_config_value("rag_max_distance", rag_max_distance)

        strategy_col1, strategy_col2, strategy_col3 = st.columns([1, 1, 1])
        with strategy_col1:
            rag_use_hybrid = st.checkbox(
                "启用混合检索",
                value=get_bool_config("rag_use_hybrid", DEFAULT_USE_HYBRID_SEARCH),
                key="rag_use_hybrid_input",
                help="同时使用向量语义检索和关键词检索，适合制度编号、部门名称、文件名等精确命中。",
            )
            set_bool_config("rag_use_hybrid", rag_use_hybrid)
        with strategy_col2:
            rag_use_reranker = st.checkbox(
                "启用重排模型",
                value=get_bool_config("rag_use_reranker", DEFAULT_USE_RERANKER),
                key="rag_use_reranker_input",
                help="先多召回，再用 BGE reranker 重排；更准但会增加内存和耗时。",
            )
            set_bool_config("rag_use_reranker", rag_use_reranker)
        with strategy_col3:
            rag_fetch_k = st.slider(
                "候选召回数",
                min_value=top_k,
                max_value=50,
                value=min(max(get_int_config("rag_fetch_k", DEFAULT_RETRIEVAL_FETCH_K), top_k), 50),
                step=1,
                key="rag_fetch_k_input",
                help="用于混合检索和重排的候选数量。",
            )
            set_config_value("rag_fetch_k", rag_fetch_k)

        placeholder_col = localized_text("Placeholder", "占位符", "佔位符")
        meaning_col = localized_text("Meaning", "含义", "含義")
        render_prompt_editor(
            "rag",
            default_rag_system_prompt(),
            default_rag_user_prompt_template(),
            localized_text(
                "Available placeholders: {history}, {context}, {question}",
                "可用占位符：{history}、{context}、{question}",
                "可用佔位符：{history}、{context}、{question}",
            ),
            [
                {
                    placeholder_col: "{history}",
                    meaning_col: localized_text(
                        "Recent conversation history sent to the model.",
                        "发送给模型的最近对话历史。",
                        "發送給模型的最近對話歷史。",
                    ),
                },
                {
                    placeholder_col: "{context}",
                    meaning_col: localized_text(
                        "Retrieved materials assembled from the vector store.",
                        "从向量库召回并拼接后的检索资料。",
                        "從向量庫召回並拼接後的檢索資料。",
                    ),
                },
                {
                    placeholder_col: "{question}",
                    meaning_col: localized_text(
                        "The current question used for answering, usually the rewritten retrieval query.",
                        "本轮用于回答的问题，通常是补全后的检索问题。",
                        "本輪用於回答的問題，通常是補全後的檢索問題。",
                    ),
                },
            ],
        )

        if st.button("清空当前对话", key="clear_rag_chat"):
            clear_chat_session(rag_session_id)
            bump_chat_session_revision("rag")
            st.rerun()

    render_rag_chat_panel(rag_messages, panel_key=f"rag_chat_panel_{rag_session_id}_{get_chat_session_revision('rag')}")

    with st.form("rag_chat_form", clear_on_submit=True):
        question = st.text_area(
            "输入问题",
            placeholder=localized_text(
                "Type your question, then click Send",
                "输入问题，点击发送",
                "輸入問題，點擊發送",
            ),
            height=88,
            key="rag_chat_text",
        )
        send_question = st.form_submit_button("发送", type="primary")

    if send_question:
        question = question.strip()
        if not question:
            st.warning("请输入问题。")
            st.stop()

        chat_history = get_chat_messages(rag_session_id)
        append_chat_message(rag_session_id, "user", question)
        if not chat_history:
            maybe_update_session_title(rag_session_id, question)

        retrieval_query = question
        query_rewrite_error = None
        retrieval_sub_queries = []
        query_decompose_error = None
        try:
            with st.spinner("正在生成回答..."):
                current_count = count_chunks(search_category)
                search_results = []
                if allow_general_fallback and is_likely_general_chat_question(question):
                    answer = ask_llm_general(
                        question,
                        chat_history=chat_history,
                        mode=chat_mode,
                        context_turns=rag_context_turns,
                    )
                elif current_count == 0:
                    if allow_general_fallback:
                        answer = ask_llm_general(
                            question,
                            chat_history=chat_history,
                            mode=chat_mode,
                            context_turns=rag_context_turns,
                        )
                    else:
                        answer = localized_text(
                            "There are no ingested chunks in the current search scope. Please upload and ingest materials first.",
                            "当前检索范围没有任何入库 chunk，请先上传资料。",
                            "當前檢索範圍沒有任何入庫 chunk，請先上傳資料。",
                        )
                else:
                    retrieval_query, query_rewrite_error = maybe_rewrite_retrieval_query(
                        question,
                        chat_history=chat_history,
                        enabled=rag_query_rewrite,
                        mode=chat_mode,
                        context_turns=rag_context_turns,
                        purpose="rag",
                    )
                    retrieval_sub_queries, query_decompose_error = decompose_retrieval_query(
                        retrieval_query,
                        enabled=rag_query_decompose,
                        mode=chat_mode,
                        purpose="rag",
                    )
                    search_results = search_vector_store_multi_query(
                        retrieval_sub_queries,
                        top_k=top_k,
                        doc_category=search_category,
                        max_distance=rag_max_distance if rag_use_distance_threshold else None,
                        fetch_k=rag_fetch_k,
                        use_hybrid=rag_use_hybrid,
                        use_reranker=rag_use_reranker,
                    )
                    if not search_results:
                        if allow_general_fallback:
                            answer = ask_llm_general(
                                question,
                                chat_history=chat_history,
                                mode=chat_mode,
                                context_turns=rag_context_turns,
                            )
                        elif rag_use_distance_threshold:
                            answer = localized_text(
                                'No relevant content met the current distance threshold. Increase "Max Distance" in retrieval settings or temporarily disable threshold filtering.',
                                "没有检索到满足当前距离阈值的相关内容。可以在检索设置里调大“最大距离”或暂时关闭阈值过滤。",
                                "沒有檢索到滿足當前距離閾值的相關內容。可以在檢索設定裡調大「最大距離」或暫時關閉閾值過濾。",
                            )
                        else:
                            answer = localized_text(
                                "No relevant content was retrieved.",
                                "没有检索到相关内容。",
                                "沒有檢索到相關內容。",
                            )
                    else:
                        answer = ask_llm(
                            question,
                            search_results,
                            chat_history=chat_history,
                            mode=chat_mode,
                            context_turns=rag_context_turns,
                        )

            append_chat_message(
                rag_session_id,
                "assistant",
                answer,
                {
                    "search_results": search_results,
                    "retrieval_query": retrieval_query,
                    "retrieval_sub_queries": retrieval_sub_queries,
                    "query_rewrite_error": query_rewrite_error,
                    "query_decompose_error": query_decompose_error,
                    "mode": chat_mode,
                    "mode_label": mode_label,
                },
            )
            st.rerun()
        except Exception as e:
            append_chat_message(
                rag_session_id,
                "assistant",
                localized_text(
                    f"Retrieval or answer generation failed: {e}",
                    f"检索或回答失败：{e}",
                    f"檢索或回答失敗：{e}",
                ),
                {
                    "search_results": [],
                    "retrieval_query": retrieval_query,
                    "retrieval_sub_queries": retrieval_sub_queries,
                    "query_rewrite_error": query_rewrite_error,
                    "query_decompose_error": query_decompose_error,
                    "mode": chat_mode,
                    "mode_label": mode_label,
                },
            )
            st.rerun()
