"""Document library management page UI.
文档库管理页面 UI。
"""

from ..services import *
from .components import *


def render_library_tab() -> None:
    st.subheader("文档库管理")
    st.write(translate_text("当前 Qdrant Collection："), COLLECTION_NAME)
    render_library_summary()

    if st.button("刷新文件摘要", key="refresh_summary"):
        st.rerun()

    summary_rows = get_file_summary_rows()
    if summary_rows:
        st.dataframe(summary_rows, width="stretch")
    else:
        st.info(localized_text("The document library is empty.", "当前文档库为空。", "當前文件庫為空。"))

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
    with st.expander("查看去重记录", expanded=False):
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
        try:
            backup_bytes = create_vector_library_backup()
            st.download_button(
                "导出文档库备份",
                data=backup_bytes,
                file_name=f"ocr_rag_backup_{time.strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip",
                key="download_vector_backup",
            )
        except Exception as e:
            st.error(localized_text(f"Failed to generate backup: {e}", f"生成备份失败：{e}", f"生成備份失敗：{e}"))

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
    if st.button("清空 Qdrant 向量库", key="clear_qdrant"):
        try:
            deleted_count = count_chunks()
            if deleted_count:
                recreate_qdrant_collection()
                delete_all_ingested_file_records()
                st.success(localized_text(f"Deleted {deleted_count} chunks.", f"已删除 {deleted_count} 个 chunk。", f"已刪除 {deleted_count} 個 chunk。"))
            else:
                delete_all_ingested_file_records()
                st.info(localized_text("The current vector store is empty.", "当前向量库为空。", "當前向量庫為空。"))
        except Exception as e:
            st.error(localized_text(f"Clear failed: {e}", f"清空失败：{e}", f"清空失敗：{e}"))
