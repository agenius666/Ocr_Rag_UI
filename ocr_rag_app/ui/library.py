"""Document library management page UI.
文档库管理页面 UI。
"""

from ..services import *
from .components import *


def render_library_tab() -> None:
    st.subheader(localized_text("Document Library", "文档库管理", "文件庫管理"))
    st.write(translate_text("当前 Qdrant Collection："), COLLECTION_NAME)
    render_library_summary()

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

    with st.expander("向量库备份 / 导入 / 导出", expanded=False):
        st.caption(
            localized_text(
                "The export contains only the Qdrant vector store (qdrant_db/). It does not include app_state.sqlite3 or original files under uploads.",
                "导出仅包含 Qdrant 向量库（qdrant_db/），不包含 app_state.sqlite3 和 uploads 原始文件。",
                "導出僅包含 Qdrant 向量庫（qdrant_db/），不包含 app_state.sqlite3 和 uploads 原始文件。",
            )
        )
        if st.button(
            localized_text("Generate Vector Store Backup", "生成文档库备份", "生成文件庫備份"),
            key="generate_vector_backup",
        ):
            try:
                st.session_state["vector_backup_bytes"] = create_vector_library_backup()
                st.session_state["vector_backup_name"] = f"ocr_rag_backup_{time.strftime('%Y%m%d_%H%M%S')}.zip"
            except Exception as e:
                st.session_state.pop("vector_backup_bytes", None)
                st.session_state.pop("vector_backup_name", None)
                st.error(localized_text(f"Failed to generate backup: {e}", f"生成备份失败：{e}", f"生成備份失敗：{e}"))

        backup_bytes = st.session_state.get("vector_backup_bytes")
        if backup_bytes:
            st.download_button(
                "导出文档库备份",
                data=backup_bytes,
                file_name=st.session_state.get("vector_backup_name", "ocr_rag_backup.zip"),
                mime="application/zip",
                key="download_vector_backup",
            )

        backup_file = st.file_uploader("导入备份 ZIP", type=["zip"], key="restore_backup_zip")
        confirm_restore = st.checkbox("我确认导入备份并覆盖当前文档库", key="confirm_restore_backup")
        if st.button("导入并覆盖当前文档库", disabled=not backup_file or not confirm_restore, key="restore_vector_backup"):
            try:
                message = restore_vector_library_backup(backup_file)
                st.success(message)
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
