"""Reusable Streamlit UI components shared by pages.
页面共享的 Streamlit UI 组件。
"""

from ..services import *


def render_search_results(search_results: List[Dict[str, Any]]) -> None:
    separator = " | "
    for i, item in enumerate(search_results, start=1):
        metadata = item["metadata"]
        distance = item["distance"]
        retrieval_source = item.get("retrieval_source", "vector")
        rerank_score = item.get("rerank_score")
        extra_parts = [
            f"{localized_text('Source', '来源', '來源')} {retrieval_source}",
        ]
        if rerank_score is not None:
            extra_parts.append(f"{localized_text('Rerank', '重排', '重排')} {rerank_score:.4f}")
        if item.get("coverage_relaxed"):
            extra_parts.append(localized_text("Coverage supplement", "覆盖补充", "覆蓋補充"))
        if metadata.get("merged_count"):
            extra_parts.append(
                f"{localized_text('Merged', '合并', '合併')} {metadata.get('merged_count')} "
                f"{localized_text('chunks', '段', '段')}"
            )
        doc_category_name = translate_text(metadata.get("doc_category_name", source_label("unknown_type")))
        title = (
            f"{source_label('material')} {i}{separator}{doc_category_name}{separator}{metadata.get('file_name')}{separator}"
            f"{source_label('chunk_index')} {metadata.get('chunk_index')}{separator}"
            f"{localized_text('Distance', '距离', '距離')} {distance}{separator}{separator.join(extra_parts)}"
        )
        with st.expander(title):
            st.write(item["content"])
            st.json(metadata)


def extract_missing_info_items(answer: str) -> List[str]:
    if not answer:
        return []
    match = re.search(
        r"#{1,4}\s*(资料不足清单|資料不足清單|Missing Materials)\s*(.*)",
        answer,
        flags=re.S | re.I,
    )
    if not match:
        return []
    section_text = match.group(2)
    next_heading = re.search(r"\n#{1,4}\s+", section_text)
    if next_heading:
        section_text = section_text[: next_heading.start()]
    items = []
    for line in section_text.splitlines():
        cleaned = re.sub(r"^\s*[-*•\d.、）)]+", "", line).strip()
        if cleaned and not cleaned.startswith("|"):
            items.append(cleaned)
    return items


def write_rows_to_sheet(sheet, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        sheet.append([source_label("none")])
        return
    headers = list(rows[0].keys())
    sheet.append(headers)
    for row in rows:
        sheet.append([row.get(header, "") for header in headers])


def evidence_rows_for_report(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for index, item in enumerate(results, start=1):
        metadata = item.get("metadata") or {}
        rows.append(
            {
                localized_text("No.", "序号", "序號"): index,
                source_label("document_type"): translate_text(metadata.get("doc_category_name", "")),
                source_label("source_file"): metadata.get("file_name", ""),
                source_label("source_location"): describe_source(metadata),
                source_label("chunk_index"): metadata.get("chunk_index", ""),
                localized_text("Merged Chunks", "合并片段", "合併片段"): metadata.get("merged_chunk_indices", ""),
                localized_text("Distance", "距离", "距離"): item.get("distance", ""),
                localized_text("Rerank Score", "重排分数", "重排分數"): item.get("rerank_score", ""),
                source_label("content"): item.get("content", ""),
            }
        )
    return rows


def build_compliance_report_excel(
    answer: str,
    structured_rows: List[Dict[str, Any]],
    regulation_results: List[Dict[str, Any]],
    enterprise_results: List[Dict[str, Any]],
    retrieval_query: str,
) -> bytes:
    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = localized_text("Summary", "分析摘要", "分析摘要")
    summary_sheet.append([localized_text("Generated At", "生成时间", "生成時間"), time.strftime("%Y-%m-%d %H:%M:%S")])
    summary_sheet.append([localized_text("Retrieval Query", "检索问题", "檢索問題"), retrieval_query])
    summary_sheet.append([])
    summary_sheet.append([localized_text("Answer", "回答正文", "回答正文")])
    for line in (answer or "").splitlines():
        summary_sheet.append([line])

    table_sheet = workbook.create_sheet(localized_text("Structured Analysis", "结构化分析表", "結構化分析表")[:31])
    write_rows_to_sheet(table_sheet, structured_rows)

    missing_sheet = workbook.create_sheet(source_label("missing_materials")[:31])
    missing_items = extract_missing_info_items(answer)
    if missing_items:
        missing_sheet.append([
            localized_text("No.", "序号", "序號"),
            localized_text("Materials To Supplement", "需补充资料", "需補充資料"),
        ])
        for index, item in enumerate(missing_items, start=1):
            missing_sheet.append([index, item])
    else:
        missing_sheet.append([
            localized_text(
                "No explicit missing-materials list was generated",
                "无明确资料不足清单",
                "無明確資料不足清單",
            )
        ])

    reg_sheet = workbook.create_sheet(localized_text("Regulatory Evidence", "监管证据", "監管證據")[:31])
    write_rows_to_sheet(reg_sheet, evidence_rows_for_report(regulation_results))

    ent_sheet = workbook.create_sheet(localized_text("Enterprise Evidence", "企业证据", "企業證據")[:31])
    write_rows_to_sheet(ent_sheet, evidence_rows_for_report(enterprise_results))

    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def normalize_chat_markdown(content: str) -> str:
    """Normalize common LLM markdown glitches before rendering.
    渲染前修正常见的大模型 Markdown 输出问题。
    """
    text = str(content or "").replace("\r\n", "\n").replace("\r", "\n")

    # Some local models collapse Markdown table line breaks into "||".
    # 部分本地模型会把 Markdown 表格换行压缩成 "||"，这里尽量恢复为多行表格。
    if "||" in text and re.search(r"\|[^\n]+\|\|", text):
        text = re.sub(r"\s*\|\|\s*", "|\n| ", text)

    normalized_lines = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            normalized_lines.append(re.sub(r"\s*<br\s*/?>\s*", "；", line, flags=re.I))
        else:
            normalized_lines.append(re.sub(r"<br\s*/?>", "\n", line, flags=re.I))

    return "\n".join(normalized_lines).strip()


def render_chat_content(content: str) -> None:
    normalized_content = normalize_chat_markdown(content)
    if normalized_content:
        st.markdown(normalized_content)


def render_rag_chat_panel(messages: List[Dict[str, Any]], panel_key: Optional[str] = None) -> None:
    chat_panel = st.container(height=CHAT_PANEL_HEIGHT, border=True, key=panel_key)
    with chat_panel:
        if not messages:
            st.info(
                localized_text(
                    "Context is retained after you ask a question. Each turn retrieves materials again using the current retrieval settings.",
                    "输入问题后会保留上下文；每一轮都会按当前检索设置重新召回资料。",
                    "輸入問題後會保留上下文；每一輪都會按當前檢索設定重新召回資料。",
                )
            )

        for message in messages:
            role = message.get("role", "assistant")
            with st.chat_message(role):
                search_results = message.get("search_results") or []
                render_chat_content(message.get("content", ""))
                if role == "assistant" and message.get("mode_label"):
                    st.caption(f"{localized_text('Mode', '模式', '模式')}: {translate_text(message['mode_label'])}")
                if role == "assistant" and message.get("retrieval_query"):
                    st.caption(f"{localized_text('Retrieval query for this turn', '本轮检索问题', '本輪檢索問題')}: {message['retrieval_query']}")
                if role == "assistant" and message.get("retrieval_sub_queries"):
                    st.caption(
                        f"{localized_text('Decomposed sub-questions', '拆解子问题', '拆解子問題')}: "
                        + "; ".join(message["retrieval_sub_queries"])
                    )
                if role == "assistant" and message.get("query_rewrite_error"):
                    st.caption(
                        localized_text(
                            "Query rewrite failed; searched with the original question: ",
                            "问题改写失败，已使用原问题检索：",
                            "問題改寫失敗，已使用原問題檢索：",
                        )
                        + str(message["query_rewrite_error"])
                    )
                if role == "assistant" and message.get("query_decompose_error"):
                    st.caption(
                        localized_text(
                            "Query decomposition failed; heuristic decomposition was used: ",
                            "问题拆解失败，已使用启发式拆解：",
                            "問題拆解失敗，已使用啟發式拆解：",
                        )
                        + str(message["query_decompose_error"])
                    )
                if role == "assistant" and search_results:
                    with st.expander(localized_text("Retrieved Materials For This Turn", "本轮检索资料", "本輪檢索資料"), expanded=False):
                        render_search_results(search_results)


def render_compliance_chat_panel(messages: List[Dict[str, Any]], panel_key: Optional[str] = None) -> None:
    chat_panel = st.container(height=CHAT_PANEL_HEIGHT, border=True, key=panel_key)
    with chat_panel:
        if not messages:
            st.info(
                localized_text(
                    "Context is retained after you ask a compliance question. Each turn retrieves regulatory and enterprise materials separately.",
                    "输入合规分析问题后会保留上下文；每一轮都会分别检索监管资料和企业资料。",
                    "輸入合規分析問題後會保留上下文；每一輪都會分別檢索監管資料和企業資料。",
                )
            )

        for message_index, message in enumerate(messages):
            role = message.get("role", "assistant")
            with st.chat_message(role):
                regulation_results = message.get("regulation_results") or []
                enterprise_results = message.get("enterprise_results") or []
                render_chat_content(message.get("content", ""))
                structured_rows = message.get("structured_rows") or []
                if role == "assistant" and structured_rows:
                    with st.expander(localized_text("Structured Compliance Analysis", "结构化合规分析表", "結構化合規分析表"), expanded=True):
                        st.dataframe(structured_rows, width="stretch", hide_index=True)
                if role == "assistant" and (structured_rows or regulation_results or enterprise_results):
                    report_bytes = build_compliance_report_excel(
                        answer=message.get("content", ""),
                        structured_rows=structured_rows,
                        regulation_results=regulation_results,
                        enterprise_results=enterprise_results,
                        retrieval_query=message.get("retrieval_query", ""),
                    )
                    st.download_button(
                        localized_text("Export This Compliance Analysis To Excel", "导出本轮合规分析 Excel", "匯出本輪合規分析 Excel"),
                        data=report_bytes,
                        file_name=f"compliance_report_{message_index + 1}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"download_compliance_report_{message_index}",
                    )
                if role == "assistant" and message.get("mode_label"):
                    st.caption(f"{localized_text('Mode', '模式', '模式')}: {translate_text(message['mode_label'])}")
                if role == "assistant" and message.get("retrieval_query"):
                    st.caption(f"{localized_text('Retrieval query for this turn', '本轮检索问题', '本輪檢索問題')}: {message['retrieval_query']}")
                if role == "assistant" and message.get("retrieval_sub_queries"):
                    st.caption(
                        f"{localized_text('Decomposed sub-questions', '拆解子问题', '拆解子問題')}: "
                        + "; ".join(message["retrieval_sub_queries"])
                    )
                if role == "assistant" and message.get("query_rewrite_error"):
                    st.caption(
                        localized_text(
                            "Query rewrite failed; searched with the original question: ",
                            "问题改写失败，已使用原问题检索：",
                            "問題改寫失敗，已使用原問題檢索：",
                        )
                        + str(message["query_rewrite_error"])
                    )
                if role == "assistant" and message.get("query_decompose_error"):
                    st.caption(
                        localized_text(
                            "Query decomposition failed; heuristic decomposition was used: ",
                            "问题拆解失败，已使用启发式拆解：",
                            "問題拆解失敗，已使用啟發式拆解：",
                        )
                        + str(message["query_decompose_error"])
                    )

                if role == "assistant" and (regulation_results or enterprise_results):
                    with st.expander(localized_text("Evidence For This Turn", "本轮证据", "本輪證據"), expanded=False):
                        evidence_col1, evidence_col2 = st.columns(2)
                        with evidence_col1:
                            st.markdown(f"##### {source_label('regulations')}")
                            if regulation_results:
                                render_search_results(regulation_results)
                            else:
                                st.info(localized_text("No regulatory evidence", "无监管证据", "無監管證據"))
                        with evidence_col2:
                            st.markdown(f"##### {source_label('enterprise')}")
                            if enterprise_results:
                                render_search_results(enterprise_results)
                            else:
                                st.info(localized_text("No enterprise evidence", "无企业证据", "無企業證據"))


def render_library_summary() -> None:
    total_count = count_chunks()
    regulation_count = count_chunks("regulation")
    enterprise_count = count_chunks("enterprise")
    general_count = count_chunks("general")

    col_total, col_reg, col_ent, col_general = st.columns(4)
    col_total.metric(localized_text("Total Chunks", "总 chunk", "總 chunk"), total_count)
    col_reg.metric(source_label("regulations"), regulation_count)
    col_ent.metric(source_label("enterprise"), enterprise_count)
    col_general.metric(localized_text("Other Materials", "其他资料", "其他資料"), general_count)


def render_result_dataframe(rows: List[Dict[str, Any]], max_rows: int = 200) -> None:
    if not rows:
        return

    st.dataframe(rows[:max_rows], width="stretch", hide_index=True)
    if len(rows) > max_rows:
        st.caption(
            localized_text(
                f"Showing the first {max_rows} rows out of {len(rows)}.",
                f"仅展示前 {max_rows} 行，共 {len(rows)} 行。",
                f"僅展示前 {max_rows} 行，共 {len(rows)} 行。",
            )
        )


TASK_STATUS_LABELS = {
    "running": localized_text("Running", "运行中", "執行中"),
    "pause_requested": localized_text("Pausing", "暂停中", "暫停中"),
    "paused": localized_text("Paused", "已暂停", "已暫停"),
    "cancel_requested": localized_text("Stopping", "终止中", "終止中"),
    "cancelled": localized_text("Stopped", "已终止", "已終止"),
    "completed": localized_text("Completed", "已完成", "已完成"),
    "success": localized_text("Success", "成功", "成功"),
    "duplicate": localized_text("Duplicate", "重复", "重複"),
    "skipped": localized_text("Skipped", "跳过", "跳過"),
    "unsupported": localized_text("Unsupported", "不支持", "不支援"),
    "failed": localized_text("Failed", "失败", "失敗"),
}


def format_task_status(status: str) -> str:
    return TASK_STATUS_LABELS.get(status, status or source_label("unknown_type"))


def format_task_display_status(task: Dict[str, Any]) -> str:
    status = task.get("status", "")
    if status in ACTIVE_INGEST_STATUSES and not is_ingest_task_actually_active(task):
        return localized_text("Disconnected", "已断开", "已斷開")
    return format_task_status(status)


def render_ingest_task_controls(task: Dict[str, Any]) -> None:
    task_id = task["id"]
    status = task["status"]
    is_live_task = is_ingest_task_actually_active(task)
    control_cols = st.columns([2, 1, 1, 1])
    with control_cols[0]:
        st.caption(
            f"{format_task_display_status(task)} | "
            f"{task['processed_files']}/{task['total_files']} | "
            f"{task['message']}"
        )
    with control_cols[1]:
        if st.button(
            localized_text("Pause", "暂停", "暫停"),
            key=f"pause_task_{task_id}",
            disabled=not is_live_task or status not in {"running"},
        ):
            request_pause_ingest_task(task_id)
            st.rerun()
    with control_cols[2]:
        if st.button(
            localized_text("Resume", "继续", "繼續"),
            key=f"resume_task_{task_id}",
            disabled=not is_live_task or status not in {"paused", "pause_requested"},
        ):
            resume_ingest_task(task_id)
            st.rerun()
    with control_cols[3]:
        if st.button(
            localized_text("Stop", "终止", "終止"),
            key=f"cancel_task_{task_id}",
            disabled=not is_live_task or status not in {"running", "pause_requested", "paused"},
        ):
            request_cancel_ingest_task(task_id)
            st.rerun()


def render_recent_ingest_tasks(expanded: bool = False) -> None:
    recent_tasks = list_ingest_tasks(limit=5)
    has_active_status = any(task.get("status") in ACTIVE_INGEST_STATUSES for task in recent_tasks)
    has_live_task = has_live_ingest_task_in_list(recent_tasks)
    with st.expander(localized_text("Recent Ingestion Tasks", "最近入库任务", "最近入庫任務"), expanded=expanded or has_active_status):
        if not recent_tasks:
            st.info(localized_text("No background ingestion tasks yet.", "暂无后台入库任务。", "暫無後台入庫任務。"))
            return

        title_col, clear_col = st.columns([4, 1])
        with title_col:
            st.markdown(f"##### {localized_text('Task Controls', '任务控制', '任務控制')}")
        with clear_col:
            if st.button(
                localized_text("Clear Task History", "清空任务历史", "清空任務歷史"),
                key="clear_ingest_task_history",
                disabled=has_live_task,
            ):
                delete_all_ingest_tasks()
                st.success(localized_text("Ingestion task history cleared.", "已清空入库任务历史。", "已清空入庫任務歷史。"))
                st.rerun()

        for task in recent_tasks:
            render_ingest_task_controls(task)

        st.markdown(f"##### {localized_text('Task List', '任务列表', '任務列表')}")
        render_result_dataframe(
            [
                {
                    localized_text("Status", "状态", "狀態"): format_task_display_status(task),
                    localized_text("Progress", "进度", "進度"): f"{task['processed_files']}/{task['total_files']}",
                    localized_text("Succeeded", "成功", "成功"): task["success_count"],
                    localized_text("Duplicate", "重复", "重複"): task["duplicate_count"],
                    localized_text("Skipped", "跳过", "跳過"): task["skipped_count"],
                    localized_text("Failed", "失败", "失敗"): task["failed_count"],
                    localized_text("Current File", "当前文件", "當前文件"): task["current_file"],
                    localized_text("Message", "说明", "說明"): task["message"],
                    localized_text("Updated At", "更新时间", "更新時間"): time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.localtime(float(task["updated_at"])),
                    ),
                }
                for task in recent_tasks
            ]
        )

        latest_task_items = list_ingest_task_items(recent_tasks[0]["id"], limit=100)
        if latest_task_items:
            st.markdown(f"##### {localized_text('Latest Task File Details', '最近任务文件明细', '最近任務文件明細')}")
            render_result_dataframe(
                [
                    {
                        source_label("source_file"): item["file_name"],
                        localized_text("Status", "状态", "狀態"): format_task_status(item["status"]),
                        localized_text("Message", "说明", "說明"): item["message"],
                        localized_text("Chunk Count", "chunk 数", "chunk 數"): item["chunk_count"],
                        "SHA256": str(item["sha256"])[:16],
                        localized_text("Updated At", "更新时间", "更新時間"): time.strftime(
                            "%Y-%m-%d %H:%M:%S",
                            time.localtime(float(item["updated_at"])),
                        ),
                    }
                    for item in latest_task_items
                ],
                max_rows=100,
            )


@st.fragment(run_every="2s")
def render_recent_ingest_tasks_live(expanded: bool = False) -> None:
    render_recent_ingest_tasks(expanded=expanded)


def format_session_option(session: Dict[str, Any]) -> str:
    updated_at = time.strftime("%m-%d %H:%M", time.localtime(float(session["updated_at"])))
    return f"{translate_text(session['title'])} | {updated_at}"


def get_session_select_key(session_type: str) -> str:
    return f"{session_type}_session_select"


def get_session_revision_key(session_type: str) -> str:
    return f"{session_type}_session_revision"


def bump_chat_session_revision(session_type: str) -> None:
    revision_key = get_session_revision_key(session_type)
    st.session_state[revision_key] = int(st.session_state.get(revision_key, 0)) + 1


def get_chat_session_revision(session_type: str) -> int:
    return int(st.session_state.get(get_session_revision_key(session_type), 0))


def sync_selected_chat_session(session_type: str) -> None:
    selected_id = st.session_state.get(get_session_select_key(session_type))
    if selected_id:
        set_active_session_id(session_type, selected_id)
        bump_chat_session_revision(session_type)


def create_and_select_chat_session(session_type: str) -> None:
    new_session_id = create_chat_session(session_type)
    set_active_session_id(session_type, new_session_id)
    st.session_state[get_session_select_key(session_type)] = new_session_id
    bump_chat_session_revision(session_type)


def delete_and_select_next_chat_session(session_type: str, session_id: str) -> None:
    delete_chat_session(session_id)
    sessions = list_chat_sessions(session_type)
    next_session_id = sessions[0]["id"] if sessions else create_chat_session(session_type)
    set_active_session_id(session_type, next_session_id)
    st.session_state[get_session_select_key(session_type)] = next_session_id
    bump_chat_session_revision(session_type)


def render_chat_session_controls(session_type: str) -> Tuple[str, List[Dict[str, Any]]]:
    active_id = get_active_session_id(session_type)
    sessions = list_chat_sessions(session_type)
    session_ids = [session["id"] for session in sessions]
    session_by_id = {session["id"]: session for session in sessions}
    if active_id not in session_ids:
        active_id = get_active_session_id(session_type)
        sessions = list_chat_sessions(session_type)
        session_ids = [session["id"] for session in sessions]
        session_by_id = {session["id"]: session for session in sessions}

    select_key = get_session_select_key(session_type)
    if st.session_state.get(select_key) not in session_ids:
        st.session_state[select_key] = active_id

    select_col, new_col, delete_col = st.columns([4, 1, 1])
    with select_col:
        selected_id = st.selectbox(
            localized_text("Current Session", "当前会话", "當前會話"),
            session_ids,
            index=session_ids.index(active_id),
            format_func=lambda session_id: format_session_option(session_by_id[session_id]),
            key=select_key,
            on_change=sync_selected_chat_session,
            args=(session_type,),
        )
    if selected_id != active_id:
        set_active_session_id(session_type, selected_id)
        active_id = selected_id

    with new_col:
        st.button(
            localized_text("New Session", "新建会话", "新建會話"),
            key=f"new_{session_type}_session",
            on_click=create_and_select_chat_session,
            args=(session_type,),
        )

    with delete_col:
        st.button(
            localized_text("Delete Session", "删除会话", "刪除會話"),
            key=f"delete_{session_type}_session",
            on_click=delete_and_select_next_chat_session,
            args=(session_type, active_id),
        )

    messages = get_chat_messages(active_id)
    st.caption(
        localized_text(
            f"Current session has {len(messages)} messages",
            f"当前会话共 {len(messages)} 条消息",
            f"當前會話共 {len(messages)} 條訊息",
        )
    )
    return active_id, messages
