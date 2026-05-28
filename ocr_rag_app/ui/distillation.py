"""Advanced distillation data generation page.
高级蒸馏数据生成页面。
"""

import math
import random

from ..distillation import (
    build_distillation_excel,
    build_distillation_jsonl,
    collect_distillation_chunk_pool,
    generate_distillation_batch,
)
from ..services import *


def distillation_scope_options() -> Dict[str, Optional[str]]:
    """Return localized document scope options.
    返回本地化资料范围选项。
    """
    return {
        localized_text("All Materials", "全部资料", "全部資料"): None,
        localized_text("Regulations / Policies", "监管要求 / 规章制度", "監管要求 / 規章制度"): "regulation",
        localized_text("Enterprise Materials", "企业资料", "企業資料"): "enterprise",
        localized_text("Other Materials", "其他资料", "其他資料"): "general",
    }


def distillation_qa_type_options() -> List[str]:
    """Return localized QA type options.
    返回本地化问答类型选项。
    """
    return [
        localized_text("Audit Q&A", "审计问答", "審計問答"),
        localized_text("Policy Explanation", "制度解释", "制度解釋"),
        localized_text("Risk Judgment", "风险判断", "風險判斷"),
        localized_text("Control Testing", "控制测试", "控制測試"),
        localized_text("Remediation Advice", "整改建议", "整改建議"),
        localized_text("Workpaper Drafting", "底稿写作", "底稿寫作"),
    ]


def distillation_mode_options() -> Dict[str, str]:
    """Return localized generation mode options.
    返回本地化生成模式选项。
    """
    return {
        localized_text("SFT Q&A Data", "SFT 问答数据", "SFT 問答資料"): "sft",
        localized_text("Preference Data chosen/rejected", "偏好数据 chosen/rejected", "偏好資料 chosen/rejected"): "preference",
    }


def localized_llm_mode_options() -> Dict[str, str]:
    """Return localized LLM mode options.
    返回本地化大模型模式选项。
    """
    return {
        localized_text("Fast", "快速", "快速"): "fast",
        localized_text("Thinking", "思考", "思考"): "thinking",
    }


def initialize_distillation_state() -> None:
    """Initialize page session state.
    初始化页面会话状态。
    """
    st.session_state.setdefault("distillation_results", [])
    st.session_state.setdefault("distillation_failures", [])
    st.session_state.setdefault("distillation_status", localized_text("Not started", "未开始", "未開始"))
    st.session_state.setdefault("distillation_generation_mode", "sft")


def render_distillation_progress(
    target_count: int,
    generated_count: int,
    batch_index: int,
    success_batches: int,
    failed_batches: int,
    status_text: str,
    model_name: str,
) -> None:
    """Render generation metrics.
    渲染生成指标。
    """
    metric_cols = st.columns(6)
    metric_cols[0].metric(localized_text("Target", "目标数量", "目標數量"), target_count)
    metric_cols[1].metric(localized_text("Generated", "已生成", "已生成"), generated_count)
    metric_cols[2].metric(localized_text("Current Batch", "当前批次", "目前批次"), batch_index)
    metric_cols[3].metric(localized_text("Succeeded", "成功批次", "成功批次"), success_batches)
    metric_cols[4].metric(localized_text("Failed", "失败批次", "失敗批次"), failed_batches)
    metric_cols[5].metric(localized_text("Status", "当前状态", "目前狀態"), status_text)
    st.caption(localized_text("Current model: ", "当前使用模型：", "目前使用模型：") + model_name)


def render_distillation_downloads(results: List[Dict[str, Any]], generation_mode: str) -> None:
    """Render JSONL and Excel download buttons.
    渲染 JSONL 和 Excel 下载按钮。
    """
    if not results:
        return
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    prefix = "distillation_sft" if generation_mode == "sft" else "distillation_preference"
    jsonl_data = build_distillation_jsonl(results)
    excel_data = build_distillation_excel(results, generation_mode)
    col_jsonl, col_excel = st.columns(2)
    with col_jsonl:
        st.download_button(
            localized_text("Download JSONL", "下载 JSONL", "下載 JSONL"),
            data=jsonl_data,
            file_name=f"{prefix}_{timestamp}.jsonl",
            mime="application/jsonl",
            key=f"download_{prefix}_jsonl_{timestamp}",
        )
    with col_excel:
        st.download_button(
            localized_text("Download Excel Review File", "下载 Excel 审核文件", "下載 Excel 審核文件"),
            data=excel_data,
            file_name=f"{prefix}_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_{prefix}_xlsx_{timestamp}",
        )


def run_distillation_generation(
    generation_mode: str,
    target_count: int,
    batch_size: int,
    chunks_per_batch: int,
    qa_type: str,
    llm_mode: str,
    timeout_seconds: int,
    retry_count: int,
    continue_after_failure: bool,
    scope_category: Optional[str],
    pool_size: int,
    scan_limit: int,
    max_chars_per_chunk: int,
) -> None:
    """Run batch generation synchronously with per-batch failure isolation.
    同步执行批量生成，并隔离每批失败。
    """
    results: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    seen_keys: set = set()
    success_batches = 0
    failed_batches = 0
    batch_index = 0
    model_name, _ = get_llm_mode_config(llm_mode)

    st.session_state["distillation_results"] = results
    st.session_state["distillation_failures"] = failures
    st.session_state["distillation_generation_mode"] = generation_mode

    progress_bar = st.progress(0, text=localized_text("Loading chunk pool...", "正在加载 chunk 抽样池...", "正在載入 chunk 抽樣池..."))
    metrics_box = st.empty()
    failure_box = st.empty()

    with st.spinner(localized_text("Sampling chunks from current collection...", "正在从当前 Collection 抽样 chunk...", "正在從目前 Collection 抽樣 chunk...")):
        chunk_pool, scanned_count = collect_distillation_chunk_pool(
            pool_size=pool_size,
            scan_limit=scan_limit,
            doc_category=scope_category,
        )
    if not chunk_pool:
        st.error(
            localized_text(
                "No usable chunk text was found in the current collection.",
                "当前 Collection 中没有找到可用的 chunk 文本。",
                "目前 Collection 中沒有找到可用的 chunk 文字。",
            )
        )
        return

    st.info(
        localized_text(
            f"Loaded {len(chunk_pool)} candidate chunks from {scanned_count} scanned points.",
            f"已从 {scanned_count} 个 point 中加载 {len(chunk_pool)} 个候选 chunk。",
            f"已從 {scanned_count} 個 point 中載入 {len(chunk_pool)} 個候選 chunk。",
        )
    )

    max_batches = max(10, math.ceil(target_count / max(1, batch_size)) * 4)
    while len(results) < target_count and batch_index < max_batches:
        batch_index += 1
        batch_chunks = random.sample(chunk_pool, min(len(chunk_pool), chunks_per_batch))
        status_text = localized_text("Generating", "正在生成", "正在生成")
        progress_bar.progress(
            min(0.99, len(results) / max(1, target_count)),
            text=localized_text(
                f"Batch {batch_index}: generating...",
                f"第 {batch_index} 批：正在生成...",
                f"第 {batch_index} 批：正在生成...",
            ),
        )
        with metrics_box:
            render_distillation_progress(
                target_count,
                len(results),
                batch_index,
                success_batches,
                failed_batches,
                status_text,
                model_name,
            )

        last_error = ""
        batch_success = False
        for attempt in range(retry_count + 1):
            try:
                new_items, _raw_text = generate_distillation_batch(
                    generation_mode=generation_mode,
                    chunks=batch_chunks,
                    batch_size=min(batch_size, target_count - len(results)),
                    qa_type=qa_type,
                    llm_mode=llm_mode,
                    timeout_seconds=timeout_seconds,
                    seen_keys=seen_keys,
                    max_chars_per_chunk=max_chars_per_chunk,
                )
                if not new_items:
                    raise ValueError(
                        localized_text(
                            "The batch returned no valid samples after validation.",
                            "本批次校验后没有有效样本。",
                            "本批次校驗後沒有有效樣本。",
                        )
                    )
                remaining = target_count - len(results)
                results.extend(new_items[:remaining])
                success_batches += 1
                batch_success = True
                break
            except Exception as error:
                last_error = str(error)
                if attempt < retry_count:
                    continue

        if not batch_success:
            failed_batches += 1
            failures.append(
                {
                    localized_text("Batch", "批次", "批次"): batch_index,
                    localized_text("Reason", "原因", "原因"): last_error[:1000],
                    localized_text("Sources", "来源", "來源"): "; ".join(chunk.get("source", "") for chunk in batch_chunks),
                }
            )
            failure_box.dataframe(failures, width="stretch")
            if not continue_after_failure:
                break

        st.session_state["distillation_results"] = results
        st.session_state["distillation_failures"] = failures
        progress_bar.progress(
            min(1.0, len(results) / max(1, target_count)),
            text=localized_text(
                f"Generated {len(results)} / {target_count}",
                f"已生成 {len(results)} / {target_count}",
                f"已生成 {len(results)} / {target_count}",
            ),
        )

    final_status = localized_text("Completed", "已完成", "已完成") if len(results) >= target_count else localized_text("Stopped", "已停止", "已停止")
    st.session_state["distillation_status"] = final_status
    progress_bar.progress(1.0 if results else 0, text=final_status)
    render_distillation_progress(
        target_count,
        len(results),
        batch_index,
        success_batches,
        failed_batches,
        final_status,
        model_name,
    )
    if failures:
        with st.expander(localized_text("Failure Log", "失败日志", "失敗日誌"), expanded=True):
            st.dataframe(failures, width="stretch")
    if results:
        st.success(
            localized_text(
                f"Generated {len(results)} samples.",
                f"已生成 {len(results)} 条样本。",
                f"已生成 {len(results)} 條樣本。",
            )
        )


def render_distillation_tab() -> None:
    """Render the advanced distillation data generation page.
    渲染高级蒸馏数据生成页面。
    """
    initialize_distillation_state()
    st.subheader(localized_text("Distillation Data Generation (Advanced)", "蒸馏数据生成（高级）", "蒸餾資料生成（進階）"))
    st.caption(
        localized_text(
            "Generate SFT or chosen/rejected preference datasets from existing knowledge-base chunks. This page only produces reviewable/exportable data and does not train models.",
            "基于已入库 chunk 生成 SFT 或 chosen/rejected 偏好数据。本页面只生成可审核、可导出的训练数据，不负责训练模型。",
            "基於已入庫 chunk 生成 SFT 或 chosen/rejected 偏好資料。本頁面只生成可審核、可匯出的訓練資料，不負責訓練模型。",
        )
    )

    active_collection = get_active_collection_name()
    active_config = get_llm_config()
    st.info(
        localized_text("Current collection: ", "当前 Collection：", "目前 Collection：")
        + active_collection
        + " | "
        + localized_text("Default model: ", "默认模型：", "預設模型：")
        + active_config.get("model", "")
    )

    mode_labels = distillation_mode_options()
    generation_mode_label = st.selectbox(
        localized_text("Generation Mode", "生成模式", "生成模式"),
        list(mode_labels.keys()),
        index=0 if st.session_state.get("distillation_generation_mode", "sft") == "sft" else 1,
        help=localized_text(
            "SFT produces instruction/input/output data. Preference mode produces prompt/chosen/rejected data.",
            "SFT 会生成 instruction/input/output；偏好模式会生成 prompt/chosen/rejected。",
            "SFT 會生成 instruction/input/output；偏好模式會生成 prompt/chosen/rejected。",
        ),
    )
    generation_mode = mode_labels[generation_mode_label]

    default_batch_size = 3 if generation_mode == "preference" else 5
    config_col1, config_col2, config_col3, config_col4 = st.columns(4)
    with config_col1:
        target_count = st.number_input(
            localized_text("Target Sample Count", "目标生成数量", "目標生成數量"),
            min_value=1,
            max_value=10000,
            value=100,
            step=10,
        )
        batch_size = st.number_input(
            localized_text("Samples Per Batch", "每批生成数量", "每批生成數量"),
            min_value=1,
            max_value=20,
            value=default_batch_size,
            step=1,
        )
    with config_col2:
        chunks_per_batch = st.number_input(
            localized_text("Chunks Per Batch", "每批 chunk 数量", "每批 chunk 數量"),
            min_value=1,
            max_value=20,
            value=5,
            step=1,
            help=localized_text(
                "How many sampled chunks are provided as context for each model call.",
                "每次调用大模型时提供多少个抽样 chunk 作为上下文。",
                "每次調用大模型時提供多少個抽樣 chunk 作為上下文。",
            ),
        )
        timeout_seconds = st.number_input(
            localized_text("Per-Batch Timeout Seconds", "单批请求超时（秒）", "單批請求逾時（秒）"),
            min_value=30,
            max_value=3600,
            value=300,
            step=30,
        )
    with config_col3:
        retry_count = st.number_input(
            localized_text("Retry Count", "失败重试次数", "失敗重試次數"),
            min_value=0,
            max_value=5,
            value=1,
            step=1,
        )
        continue_after_failure = st.checkbox(
            localized_text("Continue After Failed Batch", "失败后继续", "失敗後繼續"),
            value=True,
        )
    with config_col4:
        qa_type = st.selectbox(
            localized_text("Q&A Type", "问答类型", "問答類型"),
            distillation_qa_type_options(),
            index=0,
        )
        llm_mode_labels = localized_llm_mode_options()
        llm_mode_label = st.radio(
            localized_text("Answer Mode", "回答模式", "回答模式"),
            list(llm_mode_labels.keys()),
            horizontal=True,
            index=0,
        )
        llm_mode = llm_mode_labels[llm_mode_label]

    scope_labels = distillation_scope_options()
    scope_label = st.selectbox(
        localized_text("Data Source Scope", "数据来源范围", "資料來源範圍"),
        list(scope_labels.keys()),
        index=0,
        help=localized_text(
            "Samples are drawn from the active Qdrant collection. You can limit sampling by document category.",
            "样本从当前 Qdrant Collection 抽取，可按资料类型限制范围。",
            "樣本從目前 Qdrant Collection 抽取，可按資料類型限制範圍。",
        ),
    )

    with st.expander(localized_text("Advanced Sampling Parameters", "高级抽样参数", "進階抽樣參數"), expanded=False):
        advanced_col1, advanced_col2, advanced_col3 = st.columns(3)
        with advanced_col1:
            pool_size = st.number_input(
                localized_text("Candidate Pool Size", "候选池大小", "候選池大小"),
                min_value=10,
                max_value=10000,
                value=500,
                step=50,
                help=localized_text(
                    "A larger pool improves randomness but scans more vectors.",
                    "候选池越大，随机性越好，但会扫描更多向量。",
                    "候選池越大，隨機性越好，但會掃描更多向量。",
                ),
            )
        with advanced_col2:
            scan_limit = st.number_input(
                localized_text("Max Scanned Chunks", "最大扫描 chunk 数", "最大掃描 chunk 數"),
                min_value=10,
                max_value=200000,
                value=5000,
                step=500,
                help=localized_text(
                    "Upper bound for scanning Qdrant points when building the random pool.",
                    "构建随机候选池时最多扫描多少个 Qdrant point。",
                    "構建隨機候選池時最多掃描多少個 Qdrant point。",
                ),
            )
        with advanced_col3:
            max_chars_per_chunk = st.number_input(
                localized_text("Max Characters Per Chunk", "每个 chunk 最大字符数", "每個 chunk 最大字元數"),
                min_value=300,
                max_value=6000,
                value=1500,
                step=100,
            )

    start_col, clear_col = st.columns([1, 4])
    with start_col:
        start_generation = st.button(
            localized_text("Start Generation", "开始生成", "開始生成"),
            type="primary",
            key="start_distillation_generation",
        )
    with clear_col:
        if st.button(localized_text("Clear Current Results", "清空当前结果", "清空目前結果"), key="clear_distillation_results"):
            st.session_state["distillation_results"] = []
            st.session_state["distillation_failures"] = []
            st.session_state["distillation_status"] = localized_text("Not started", "未开始", "未開始")
            st.rerun()

    if start_generation:
        run_distillation_generation(
            generation_mode=generation_mode,
            target_count=int(target_count),
            batch_size=int(batch_size),
            chunks_per_batch=int(chunks_per_batch),
            qa_type=qa_type,
            llm_mode=llm_mode,
            timeout_seconds=int(timeout_seconds),
            retry_count=int(retry_count),
            continue_after_failure=continue_after_failure,
            scope_category=scope_labels[scope_label],
            pool_size=int(pool_size),
            scan_limit=int(scan_limit),
            max_chars_per_chunk=int(max_chars_per_chunk),
        )

    results = st.session_state.get("distillation_results", [])
    failures = st.session_state.get("distillation_failures", [])
    current_mode = st.session_state.get("distillation_generation_mode", generation_mode)
    if results:
        st.markdown(localized_text("### Generated Data Preview", "### 生成数据预览", "### 生成資料預覽"))
        st.dataframe(results[:200], width="stretch")
        render_distillation_downloads(results, current_mode)
    if failures:
        with st.expander(localized_text("Failure Log", "失败日志", "失敗日誌"), expanded=False):
            st.dataframe(failures, width="stretch")
