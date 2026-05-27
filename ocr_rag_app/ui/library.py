"""Document library management page UI.
文档库管理页面 UI。
"""

import os
import time

from ..services import *
from .components import *


SAFE_BROWSER_DOWNLOAD_BYTES = 500 * 1024 * 1024


def format_file_size(size_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def render_library_tab() -> None:
    st.subheader(localized_text("Document Library", "文档库管理", "文件庫管理"))
    st.write(translate_text("当前 Qdrant Collection："), get_active_collection_name())
    render_library_summary()
    library_notice = st.session_state.pop("library_notice", "")
    if library_notice:
        st.success(library_notice)

    show_file_summary = st.toggle(
        localized_text("View File Summary", "查看文件摘要", "查看文件摘要"),
        value=False,
        key="show_library_file_summary",
        help=localized_text(
            "Load the detailed file summary only when this section is opened.",
            "只在打开本区块时加载详细文件摘要，减少页面重跑负载。",
            "只在打開本區塊時載入詳細文件摘要，減少頁面重跑負載。",
        ),
    )
    if show_file_summary:
        with st.container(border=True):
            if st.button(localized_text("Refresh File Summary", "刷新文件摘要", "刷新文件摘要"), key="refresh_summary"):
                get_file_summary_rows.clear()
                st.rerun()
            with st.spinner(localized_text("Loading...", "加载中...", "載入中...")):
                summary_rows = get_file_summary_rows(get_ui_language())
            if summary_rows:
                st.dataframe(summary_rows, width="stretch")
            else:
                st.info(localized_text("The document library is empty.", "当前文档库为空。", "當前文件庫為空。"))

    show_dedup_records = st.toggle(
        localized_text("View Deduplication Records", "查看去重记录", "查看去重記錄"),
        value=False,
        key="show_dedup_records",
        help=localized_text(
            "Load SHA256 deduplication records only when needed.",
            "只在需要时加载 SHA256 去重记录。",
            "只在需要時載入 SHA256 去重記錄。",
        ),
    )
    if show_dedup_records:
        with st.container(border=True):
            with st.spinner(localized_text("Loading...", "加载中...", "載入中...")):
                ingested_rows = [
                    {
                        source_label("source_file"): item["file_name"],
                        source_label("document_type"): translate_text(DOC_CATEGORY_NAMES.get(item["doc_category"], item["doc_category"])),
                        localized_text("Document Name", "资料名称", "資料名稱"): item["doc_label"],
                        localized_text("Chunk Count", "chunk 数", "chunk 數"): item["chunk_count"],
                        "SHA256": item["sha256"][:16],
                        localized_text("Ingested At", "入库时间", "入庫時間"): time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(item["created_at"]))),
                    }
                    for item in list_ingested_files()
                ]
            if ingested_rows:
                st.dataframe(ingested_rows, width="stretch")
            else:
                st.info(localized_text("No deduplication records yet.", "暂无去重记录。", "暫無去重記錄。"))

    with st.expander(localized_text("Vector Store Backup / Import / Export", "向量库备份 / 导入 / 导出", "向量庫備份 / 導入 / 導出"), expanded=False):
        st.caption(
            localized_text(
                "The backup contains the local Qdrant vector store and a SQLite file index export used by file summaries and deduplication records. Original uploaded files under uploads are not included. Docker/HTTP Qdrant should use the Qdrant server snapshot mechanism.",
                "备份包含本地 Qdrant 向量库，以及用于文件摘要和去重记录的 SQLite 文件索引导出；不包含 uploads 原始上传文件。Docker/HTTP Qdrant 请使用 Qdrant 服务端 snapshot 机制。",
                "備份包含本地 Qdrant 向量庫，以及用於文件摘要和去重記錄的 SQLite 文件索引導出；不包含 uploads 原始上傳文件。Docker/HTTP Qdrant 請使用 Qdrant 服務端 snapshot 機制。",
            )
        )
        if st.button(
            localized_text("Generate Vector Store Backup", "生成文档库备份", "生成文件庫備份"),
            key="generate_vector_backup",
        ):
            try:
                backup_path, backup_size = create_vector_library_backup_file()
                st.session_state["vector_backup_path"] = backup_path
                st.session_state["vector_backup_size"] = backup_size
                st.session_state["vector_backup_name"] = os.path.basename(backup_path)
            except Exception as e:
                st.session_state.pop("vector_backup_path", None)
                st.session_state.pop("vector_backup_size", None)
                st.session_state.pop("vector_backup_name", None)
                st.error(localized_text(f"Failed to generate backup: {e}", f"生成备份失败：{e}", f"生成備份失敗：{e}"))

        backup_path = st.session_state.get("vector_backup_path", "")
        backup_size = int(st.session_state.get("vector_backup_size", 0) or 0)
        if backup_path and os.path.isfile(backup_path):
            st.success(
                localized_text(
                    f"Backup ready: {backup_path} ({format_file_size(backup_size)})",
                    f"备份已生成：{backup_path}（{format_file_size(backup_size)}）",
                    f"備份已生成：{backup_path}（{format_file_size(backup_size)}）",
                )
            )
            if backup_size <= SAFE_BROWSER_DOWNLOAD_BYTES:
                with open(backup_path, "rb") as backup_handle:
                    st.download_button(
                        localized_text("Export Library Backup", "导出文档库备份", "導出文件庫備份"),
                        data=backup_handle,
                        file_name=st.session_state.get("vector_backup_name", "ocr_rag_backup.zip"),
                        mime="application/zip",
                        key="download_vector_backup",
                    )
            else:
                st.warning(
                    localized_text(
                        "This backup is large, so browser download is disabled to avoid exhausting Streamlit memory. Copy the ZIP from the path shown above.",
                        "该备份文件较大，为避免 Streamlit 内存耗尽，已关闭浏览器下载。请直接复制上方路径中的 ZIP 文件。",
                        "該備份文件較大，為避免 Streamlit 記憶體耗盡，已關閉瀏覽器下載。請直接複製上方路徑中的 ZIP 文件。",
                    )
                )

        backup_file = st.file_uploader(localized_text("Import Backup ZIP", "导入备份 ZIP", "導入備份 ZIP"), type=["zip"], key="restore_backup_zip")
        local_backup_path = st.text_input(
            localized_text("Or import from local ZIP path", "或从本地 ZIP 路径导入", "或從本地 ZIP 路徑導入"),
            value="",
            key="restore_backup_local_path",
            help=localized_text(
                "Use this when the backup ZIP is too large for browser upload.",
                "当备份 ZIP 过大、不适合浏览器上传时，可填写本机文件路径。",
                "當備份 ZIP 過大、不適合瀏覽器上傳時，可填寫本機文件路徑。",
            ),
        )
        backup_source = backup_file
        local_backup_path_value = normalize_local_path(local_backup_path.strip(), "") if local_backup_path.strip() else ""
        if local_backup_path_value:
            backup_source = local_backup_path_value

        backup_inspection = None
        backup_inspection_error = ""
        if backup_file or (local_backup_path_value and os.path.isfile(local_backup_path_value)):
            try:
                backup_inspection = inspect_vector_library_backup(backup_source)
            except Exception as e:
                backup_inspection_error = str(e)
        elif local_backup_path_value:
            backup_inspection_error = localized_text(
                f"Backup path was not found: {local_backup_path_value}",
                f"未找到备份路径：{local_backup_path_value}",
                f"未找到備份路徑：{local_backup_path_value}",
            )

        backup_mismatch = False
        if backup_inspection:
            backup_mismatch = not (
                backup_inspection.get("matches_active_model") and backup_inspection.get("matches_active_dimension")
            )
            st.json(
                {
                    "backup_embedding_model": backup_inspection.get("embedding_model") or localized_text("Unknown", "未知", "未知"),
                    "backup_vector_size": backup_inspection.get("vector_size"),
                    "backup_collection": backup_inspection.get("collection_name"),
                    "current_embedding_model": get_embedding_model_name(),
                    "current_vector_size": get_embedding_vector_size(),
                    "current_collection": get_active_collection_name(),
                },
                expanded=False,
            )
            if backup_mismatch:
                st.warning(
                    localized_text(
                        "The backup embedding model or vector dimension does not match the current settings. You can switch to the matching embedding model in Settings > Models And Paths, import a matching backup, or import first and then use Settings > Vector Store to convert embeddings.",
                        "备份的向量模型或维度与当前设置不一致。你可以在“配置中心 > 模型与路径”切换到匹配模型，导入匹配备份，或先导入后在“配置中心 > 向量库连接”执行向量库模型转换。",
                        "備份的向量模型或維度與目前設定不一致。你可以在「配置中心 > 模型與路徑」切換到匹配模型，導入匹配備份，或先導入後在「配置中心 > 向量庫連線」執行向量庫模型轉換。",
                    )
                )
        elif backup_inspection_error:
            st.warning(backup_inspection_error)

        confirm_restore = st.checkbox(localized_text("I confirm importing backup and overwriting the current library", "我确认导入备份并覆盖当前文档库", "我確認導入備份並覆蓋當前文件庫"), key="confirm_restore_backup")
        confirm_mismatch_restore = True
        if backup_mismatch:
            confirm_mismatch_restore = st.checkbox(
                localized_text(
                    "I understand the backup model does not match the current embedding setting.",
                    "我已了解备份模型与当前向量模型设置不一致。",
                    "我已了解備份模型與目前向量模型設定不一致。",
                ),
                key="confirm_mismatch_restore_backup",
            )
        restore_ready = bool(backup_file or local_backup_path_value) and confirm_restore and confirm_mismatch_restore and not bool(backup_inspection_error)
        if st.button(localized_text("Import And Overwrite Current Library", "导入并覆盖当前文档库", "導入並覆蓋當前文件庫"), disabled=not restore_ready, key="restore_vector_backup"):
            try:
                if local_backup_path_value:
                    message = restore_vector_library_backup_from_path(local_backup_path_value)
                else:
                    message = restore_vector_library_backup(backup_file)
                get_file_summary_rows.clear()
                get_cached_library_counts.clear()
                st.session_state["library_notice"] = message
                st.rerun()
            except Exception as e:
                st.error(localized_text(f"Failed to import backup: {e}", f"导入备份失败：{e}", f"導入備份失敗：{e}"))

    st.warning(
        localized_text(
            "Clearing the vector store deletes all ingested chunks and SHA256 deduplication records. Original uploaded files are not deleted.",
            "清空向量库会删除所有已入库 chunk 和 SHA256 去重记录，原始上传文件不会删除。",
            "清空向量庫會刪除所有已入庫 chunk 和 SHA256 去重記錄，原始上傳文件不會刪除。",
        )
    )
    confirm_clear_qdrant = st.checkbox(
        localized_text(
            "I understand this will delete all chunks and SHA256 deduplication records.",
            "我确认清空所有 chunk 和 SHA256 去重记录。",
            "我確認清空所有 chunk 和 SHA256 去重記錄。",
        ),
        value=False,
        key="confirm_clear_qdrant",
    )
    if st.button(
        localized_text("Clear Qdrant Vector Store", "清空 Qdrant 向量库", "清空 Qdrant 向量庫"),
        key="clear_qdrant",
        disabled=not confirm_clear_qdrant,
    ):
        try:
            deleted_count = count_chunks()
            if deleted_count:
                recreate_qdrant_collection()
                delete_all_ingested_file_records()
                get_file_summary_rows.clear()
                get_cached_library_counts.clear()
                st.success(localized_text(f"Deleted {deleted_count} chunks.", f"已删除 {deleted_count} 个 chunk。", f"已刪除 {deleted_count} 個 chunk。"))
            else:
                delete_all_ingested_file_records()
                get_file_summary_rows.clear()
                get_cached_library_counts.clear()
                st.info(localized_text("The current vector store is empty.", "当前向量库为空。", "當前向量庫為空。"))
        except Exception as e:
            st.error(localized_text(f"Clear failed: {e}", f"清空失败：{e}", f"清空失敗：{e}"))
