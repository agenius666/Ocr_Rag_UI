"""RAG ingestion, retrieval, query rewriting, and answer generation pipeline.
RAG 入库、检索、问题改写和回答生成流水线。
"""

from .services import *


# =========================
# 文本切分与向量入库
# =========================
def iter_text_chunks(text: str, chunk_size: int = 600, overlap: int = 100):
    yield from split_semantic_chunks(text, chunk_size=chunk_size, overlap=overlap)


def split_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    """
    优先按标题、段落、条款和句子边界切分；超长文本再按字符兜底。
    """
    return list(iter_text_chunks(text, chunk_size=chunk_size, overlap=overlap))


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    用 BGE-M3 生成向量。
    normalize_embeddings=True 一般更适合向量相似度检索。
    """
    embedding_model = load_embedding_model()
    embeddings = embedding_model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=EMBEDDING_BATCH_SIZE,
        convert_to_numpy=True,
    )
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(vector) for vector in embeddings]


def clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = str(value)
    return cleaned


def split_sections(
    sections: List[Dict[str, Any]],
    chunk_size: int,
    overlap: int,
) -> List[Tuple[str, Dict[str, Any]]]:
    chunk_items = []
    for section_index, section in enumerate(sections):
        chunks = split_text(section["text"], chunk_size=chunk_size, overlap=overlap)
        for section_chunk_index, chunk in enumerate(chunks):
            metadata = {
                **section["metadata"],
                "section_index": section_index,
                "section_chunk_index": section_chunk_index,
            }
            chunk_items.append((chunk, metadata))
    return chunk_items


def iter_section_chunks(
    sections: List[Dict[str, Any]],
    chunk_size: int,
    overlap: int,
):
    for section_index, section in enumerate(sections):
        for section_chunk_index, chunk in enumerate(
            iter_text_chunks(section["text"], chunk_size=chunk_size, overlap=overlap)
        ):
            yield chunk, {
                **section["metadata"],
                "section_index": section_index,
                "section_chunk_index": section_chunk_index,
            }


def flush_vector_batch(
    chunks: List[str],
    ids: List[str],
    metadatas: List[Dict[str, Any]],
) -> int:
    if not chunks:
        return 0

    embeddings = embed_texts(chunks)
    models = import_qdrant_models()
    points = [
        models.PointStruct(
            id=ids[index],
            vector=embeddings[index],
            payload={
                "document": chunks[index],
                **metadatas[index],
            },
        )
        for index in range(len(chunks))
    ]
    vector_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )
    written_count = len(chunks)
    del embeddings, points
    chunks.clear()
    ids.clear()
    metadatas.clear()
    gc.collect()
    return written_count


def add_document_to_vector_store(
    file_name: str,
    file_sha256: str,
    sections: List[Dict[str, Any]],
    chunk_size: int,
    overlap: int,
    doc_category: str,
    doc_label: str,
) -> int:
    doc_id = str(uuid.uuid4())
    chunks = []
    ids = []
    metadatas = []
    total_count = 0

    for index, (chunk, section_metadata) in enumerate(
        iter_section_chunks(sections, chunk_size=chunk_size, overlap=overlap)
    ):
        chunks.append(chunk)
        ids.append(str(uuid.uuid4()))
        metadatas.append(
            clean_metadata(
                {
                    **section_metadata,
                    "doc_id": doc_id,
                    "file_sha256": file_sha256,
                    "file_name": file_name,
                    "doc_label": doc_label or file_name,
                    "doc_category": doc_category,
                    "doc_category_name": DOC_CATEGORY_NAMES.get(doc_category, doc_category),
                    "chunk_index": index,
                    "embedding_model": EMBEDDING_MODEL_NAME,
                }
            )
        )

        if len(chunks) >= VECTOR_ADD_BATCH_SIZE:
            total_count += flush_vector_batch(chunks, ids, metadatas)

    total_count += flush_vector_batch(chunks, ids, metadatas)
    return total_count


def run_background_ingest_task(
    task_id: str,
    file_specs: List[Dict[str, Any]],
    settings: Dict[str, Any],
) -> None:
    success_count = 0
    duplicate_count = 0
    skipped_count = 0
    failed_count = 0
    total_files = len(file_specs)

    def sync_task(index: int, current_file: str, message: str, status: str = "running") -> None:
        if status == "running":
            wait_if_task_paused_or_cancelled(task_id)
        update_ingest_task(
            task_id,
            status=status,
            processed_files=index,
            success_count=success_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            current_file=current_file,
            message=message,
        )

    try:
        for file_index, spec in enumerate(file_specs, start=1):
            wait_if_task_paused_or_cancelled(task_id)
            relative_name = spec["relative_name"]
            file_path = spec.get("file_path", "")
            file_sha256 = spec.get("sha256", "")
            sync_task(file_index - 1, relative_name, localized_text("Processing: ", "正在处理：", "正在處理：") + relative_name)

            try:
                wait_if_task_paused_or_cancelled(task_id)
                if not is_supported_upload(relative_name):
                    skipped_count += 1
                    message = localized_text("Unsupported file type: ", "不支持的文件类型：", "不支援的文件類型：") + (
                        Path(relative_name).suffix.lower()
                        or localized_text("No extension", "无扩展名", "無副檔名")
                    )
                    record_ingest_task_item(task_id, relative_name, "unsupported", message, file_sha256=file_sha256)
                    sync_task(file_index, relative_name, message)
                    continue

                existing_file = get_duplicate_ingested_file(file_sha256)
                if existing_file:
                    duplicate_count += 1
                    record_ingest_task_item(
                        task_id,
                        relative_name,
                        "duplicate",
                        localized_text("Duplicate file skipped", "已跳过重复文件", "已跳過重複文件"),
                        chunk_count=int(existing_file.get("chunk_count", 0) or 0),
                        file_sha256=file_sha256,
                    )
                    sync_task(file_index, relative_name, localized_text("Duplicate file skipped: ", "已跳过重复文件：", "已跳過重複文件：") + relative_name)
                    continue

                if is_legacy_office_file(relative_name):
                    ext = get_file_extension_from_name(relative_name)
                    can_convert, conversion_message = get_legacy_conversion_status(ext)
                    if not can_convert:
                        skipped_count += 1
                        record_ingest_task_item(task_id, relative_name, "unsupported", conversion_message, file_sha256=file_sha256)
                        sync_task(file_index, relative_name, conversion_message)
                        continue

                if (
                    bool(settings.get("ppt_visual_ocr", True))
                    and get_file_extension_from_name(relative_name) in {"ppt", "pptx"}
                    and not find_soffice_binary()
                ):
                    skipped_count += 1
                    message = localized_text(
                        "PPT/PPTX rasterization OCR requires LibreOffice.",
                        "PPT/PPTX 栅格化 OCR 需要 LibreOffice。",
                        "PPT/PPTX 柵格化 OCR 需要 LibreOffice。",
                    )
                    record_ingest_task_item(task_id, relative_name, "unsupported", message, file_sha256=file_sha256)
                    sync_task(file_index, relative_name, message)
                    continue

                def extraction_progress(message: str) -> None:
                    sync_task(file_index - 1, relative_name, message)

                try:
                    file_path, spreadsheet_row_count = prepare_spreadsheet_for_ingest(
                        relative_name=relative_name,
                        file_path=file_path,
                        skip_large_excel=bool(settings.get("skip_large_excel", False)),
                        excel_row_limit=int(settings.get("excel_row_limit", 100000)),
                        progress_callback=extraction_progress,
                    )
                    if spreadsheet_row_count is not None:
                        sync_task(
                            file_index - 1,
                            relative_name,
                            localized_text(
                                f"Excel row count checked: {spreadsheet_row_count}",
                                f"Excel 行数检查完成：{spreadsheet_row_count}",
                                f"Excel 行數檢查完成：{spreadsheet_row_count}",
                            ),
                        )
                except SpreadsheetRowLimitExceeded as e:
                    skipped_count += 1
                    message = str(e)
                    record_ingest_task_item(task_id, relative_name, "skipped", message, file_sha256=file_sha256)
                    sync_task(file_index, relative_name, message)
                    continue

                sections = extract_document_sections(
                    file_path,
                    ocr_enhance=bool(settings.get("ocr_enhance", True)),
                    pdf_ocr_mode=str(settings.get("pdf_ocr_mode", "smart")),
                    ppt_visual_ocr=bool(settings.get("ppt_visual_ocr", True)),
                    progress_callback=extraction_progress,
                )

                wait_if_task_paused_or_cancelled(task_id)
                if not sections_have_text(sections):
                    skipped_count += 1
                    message = localized_text("No valid text was extracted", "没有解析到有效文字", "沒有解析到有效文字")
                    record_ingest_task_item(task_id, relative_name, "skipped", message, file_sha256=file_sha256)
                    sync_task(file_index, relative_name, message)
                    continue

                deleted_chunks, _deleted_records = replace_existing_same_name_if_needed(
                    relative_name,
                    file_sha256,
                    enabled=bool(settings.get("replace_changed_same_name", True)),
                )
                chunk_count = add_document_to_vector_store(
                    file_name=relative_name,
                    file_sha256=file_sha256,
                    sections=sections,
                    chunk_size=int(settings.get("chunk_size", 600)),
                    overlap=int(settings.get("overlap", 100)),
                    doc_category=str(settings.get("doc_category", "general")),
                    doc_label=str(settings.get("doc_label") or relative_name),
                )
                if chunk_count > 0:
                    success_count += 1
                    record_ingested_file(
                        file_sha256=file_sha256,
                        file_name=relative_name,
                        doc_category=str(settings.get("doc_category", "general")),
                        doc_label=str(settings.get("doc_label") or relative_name),
                        chunk_count=chunk_count,
                    )
                    replace_note = (
                        localized_text(", replaced old ", "，已替换旧 ", "，已替換舊 ")
                        + f"{deleted_chunks}"
                        + localized_text(" chunks", " 个 chunk", " 個 chunk")
                        if deleted_chunks
                        else ""
                    )
                    record_ingest_task_item(
                        task_id,
                        relative_name,
                        "success",
                        localized_text("Ingested successfully; wrote ", "入库成功，写入 ", "入庫成功，寫入 ")
                        + f"{chunk_count}"
                        + localized_text(" chunks", " 个 chunk", " 個 chunk")
                        + replace_note,
                        chunk_count=chunk_count,
                        file_sha256=file_sha256,
                    )
                    sync_task(file_index, relative_name, localized_text("Ingested successfully: ", "入库成功：", "入庫成功：") + relative_name)
                else:
                    skipped_count += 1
                    message = localized_text(
                        "Parsed successfully, but no ingestible chunks were produced",
                        "解析成功但没有可入库 chunk",
                        "解析成功但沒有可入庫 chunk",
                    )
                    record_ingest_task_item(task_id, relative_name, "skipped", message, file_sha256=file_sha256)
                    sync_task(file_index, relative_name, message)
            except IngestTaskCancelled:
                raise
            except Exception as e:
                failed_count += 1
                record_ingest_task_item(task_id, relative_name, "failed", str(e), file_sha256=file_sha256)
                sync_task(file_index, relative_name, localized_text("Processing failed: ", "处理失败：", "處理失敗：") + str(e))
            finally:
                release_memory_after_file()
    except IngestTaskCancelled:
        update_ingest_task(
            task_id,
            status="cancelled",
            success_count=success_count,
            duplicate_count=duplicate_count,
            skipped_count=skipped_count,
            failed_count=failed_count,
            message=localized_text("Ingestion task stopped", "入库任务已终止", "入庫任務已終止"),
        )
        return

    if settings.get("auto_unload_models_after_ingest"):
        try:
            load_ocr_model.clear()
            load_embedding_model.clear()
            load_reranker_model.clear()
        except Exception:
            pass
        release_memory_after_file()

    sync_task(total_files, "", localized_text("Background ingestion task completed", "后台入库任务完成", "後台入庫任務完成"), status="completed")


# =========================
# 检索与本地大模型回答
# =========================
def count_chunks(doc_category: Optional[str] = None) -> int:
    result = vector_client.count(
        collection_name=COLLECTION_NAME,
        count_filter=build_qdrant_filter({"doc_category": doc_category}) if doc_category else None,
        exact=True,
    )
    return int(result.count)


def default_fetch_k(top_k: int) -> int:
    return max(top_k, min(50, max(DEFAULT_RETRIEVAL_FETCH_K, top_k * 4)))


def query_qdrant_points(
    query_embedding: List[float],
    top_k: int,
    doc_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query_filter = build_qdrant_filter({"doc_category": doc_category}) if doc_category else None
    try:
        result = vector_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        points = getattr(result, "points", result)
    except Exception:
        points = vector_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
    return [payload_to_result(point, score=getattr(point, "score", None)) for point in points]


def keyword_search_vector_store(
    query: str,
    top_k: int,
    doc_category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    points = qdrant_scroll_points(where={"doc_category": doc_category} if doc_category else None, limit=100000)
    ids = [str(point.id) for point in points]
    payloads = [point_payload(point) for point in points]
    docs = [payload.get("document", "") for payload in payloads]
    metadatas = []
    for payload in payloads:
        metadata = dict(payload)
        metadata.pop("document", None)
        metadatas.append(metadata)
    ranked = keyword_rank_documents(query, docs, top_k=top_k)

    output = []
    for doc_index, score in ranked:
        output.append(
            {
                "id": ids[doc_index] if doc_index < len(ids) else str(uuid.uuid4()),
                "content": docs[doc_index],
                "metadata": metadatas[doc_index] if doc_index < len(metadatas) else {},
                "distance": None,
                "keyword_score": score,
                "retrieval_source": "keyword",
            }
        )
    return output


def merge_retrieval_results(
    vector_results: List[Dict[str, Any]],
    keyword_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not keyword_results:
        return vector_results
    if not vector_results:
        return keyword_results

    vector_ranked = [(item["id"], item) for item in vector_results]
    keyword_ranked = [(item["id"], item) for item in keyword_results]
    merged = reciprocal_rank_merge([vector_ranked, keyword_ranked])

    vector_by_id = {item["id"]: item for item in vector_results}
    keyword_by_id = {item["id"]: item for item in keyword_results}
    for item in merged:
        item_id = item["id"]
        if item_id in vector_by_id and item_id in keyword_by_id:
            item["retrieval_source"] = "vector+keyword"
            item["keyword_score"] = keyword_by_id[item_id].get("keyword_score")
            item["distance"] = vector_by_id[item_id].get("distance")
    return merged


def rerank_search_results(query: str, candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    reranker = load_reranker_model()
    pairs = [[query, item["content"]] for item in candidates]
    scores = reranker.predict(pairs, show_progress_bar=False)
    for item, score in zip(candidates, scores):
        item["rerank_score"] = float(score)
    candidates.sort(key=lambda item: item.get("rerank_score", 0.0), reverse=True)
    return candidates[:top_k]


def int_metadata_value(metadata: Dict[str, Any], key: str) -> Optional[int]:
    value = metadata.get(key)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def retrieval_dedupe_key(item: Dict[str, Any]) -> Tuple[Any, ...]:
    metadata = item.get("metadata") or {}
    return (
        metadata.get("file_name", ""),
        metadata.get("source_type", ""),
        metadata.get("page", ""),
        metadata.get("slide", ""),
        metadata.get("sheet", ""),
        metadata.get("row_range", ""),
        metadata.get("table_index", ""),
        metadata.get("image_index", ""),
        metadata.get("section_index", ""),
    )


def merge_retrieval_item_content(existing: Dict[str, Any], item: Dict[str, Any]) -> None:
    existing_content = existing.get("content", "")
    new_content = item.get("content", "")
    if new_content and new_content not in existing_content and len(existing_content) < 3200:
        separator = f"--- {source_label('same_source_neighbor')} ---"
        existing["content"] = f"{existing_content}\n\n{separator}\n\n{new_content}".strip()

    existing_metadata = existing.setdefault("metadata", {})
    new_metadata = item.get("metadata") or {}
    existing_chunks = str(existing_metadata.get("merged_chunk_indices", existing_metadata.get("chunk_index", "")))
    new_chunk = str(new_metadata.get("chunk_index", ""))
    chunk_values = [value for value in [existing_chunks, new_chunk] if value]
    existing_metadata["merged_chunk_indices"] = ",".join(dict.fromkeys(",".join(chunk_values).split(",")))
    existing_metadata["merged_count"] = int(existing_metadata.get("merged_count", 1)) + 1

    if existing.get("distance") is None or (
        item.get("distance") is not None and item.get("distance") < existing.get("distance")
    ):
        existing["distance"] = item.get("distance")


def dedupe_search_results(results: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    output = []
    by_key: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    for item in results:
        key = retrieval_dedupe_key(item)
        existing = by_key.get(key)
        if existing is None:
            if len(output) >= top_k:
                continue
            copied = {
                **item,
                "metadata": dict(item.get("metadata") or {}),
            }
            by_key[key] = copied
            output.append(copied)
        else:
            existing_chunk = int_metadata_value(existing.get("metadata") or {}, "chunk_index")
            new_chunk = int_metadata_value(item.get("metadata") or {}, "chunk_index")
            if existing_chunk is None or new_chunk is None or abs(existing_chunk - new_chunk) <= 2:
                merge_retrieval_item_content(existing, item)
            elif len(output) < top_k:
                copied = {
                    **item,
                    "metadata": dict(item.get("metadata") or {}),
                }
                output.append(copied)
    return output[:top_k]


def search_vector_store(
    query: str,
    top_k: int = 5,
    doc_category: Optional[str] = None,
    max_distance: Optional[float] = None,
    fetch_k: Optional[int] = None,
    use_hybrid: bool = DEFAULT_USE_HYBRID_SEARCH,
    use_reranker: bool = DEFAULT_USE_RERANKER,
) -> List[Dict[str, Any]]:
    available_count = count_chunks(doc_category)
    if available_count <= 0:
        return []

    query_embedding = embed_texts([query])[0]
    n_results = fetch_k if fetch_k is not None else default_fetch_k(top_k)
    vector_results = query_qdrant_points(
        query_embedding,
        top_k=min(max(top_k, n_results), available_count),
        doc_category=doc_category,
    )
    keyword_results = keyword_search_vector_store(query, top_k=n_results, doc_category=doc_category) if use_hybrid else []
    candidates = merge_retrieval_results(vector_results, keyword_results)

    filtered = []
    for item in candidates:
        distance = item.get("distance")
        if max_distance is not None and distance is not None and distance > max_distance:
            if not item.get("keyword_score"):
                continue
        filtered.append(item)

    if use_reranker:
        return dedupe_search_results(rerank_search_results(query, filtered[:n_results], top_k=max(top_k, n_results)), top_k)

    output = []
    for item in filtered:
        output.append(item)
        if len(output) >= n_results:
            break
    return dedupe_search_results(output, top_k)


def is_complex_retrieval_question(question: str) -> bool:
    compact = question.strip()
    if len(compact) >= 60:
        return True
    return any(
        marker in compact.lower()
        for marker in [
            "分别",
            "逐条",
            "對照",
            "对照",
            "以及",
            "并且",
            "並且",
            "同时",
            "同時",
            " and ",
            " compare ",
            " respectively ",
            "、",
            "；",
            ";",
        ]
    )


def heuristic_decompose_question(question: str, max_queries: int = 4) -> List[str]:
    parts = re.split(r"[；;]|以及|并且|並且|同时|同時|分别|分別|、|\band\b", question, flags=re.I)
    queries = [part.strip(" ，,。？?") for part in parts if part.strip(" ，,。？?")]
    if len(queries) <= 1:
        return [question]
    return queries[:max_queries]


def decompose_retrieval_query(
    query: str,
    enabled: bool,
    mode: str,
    purpose: str,
    max_queries: int = 4,
) -> Tuple[List[str], Optional[str]]:
    if not enabled or not is_complex_retrieval_question(query):
        return [query], None

    system_prompt = localized_text(
        f"""
You are a retrieval query decomposer.
Split a complex question into 2 to 4 independent sub-questions that can be searched separately.
Only output one sub-question per line. Do not answer or explain.
If the question does not need decomposition, output the original question.
Output language: {llm_language_name()}.
""",
        """
你是一个检索查询拆解器。
你的任务是把复杂问题拆成 2 到 4 个可以分别检索的简体中文子问题。
只输出子问题，每行一个；不要回答，不要解释。
如果问题不需要拆解，只输出原问题。
""",
        """
你是一個檢索查詢拆解器。
你的任務是把複雜問題拆成 2 到 4 個可以分別檢索的繁體中文子問題。
只輸出子問題，每行一個；不要回答，不要解釋。
如果問題不需要拆解，只輸出原問題。
""",
    )
    purpose_hint = localized_text("Compliance analysis", "合规分析", "合規分析") if purpose == "compliance" else localized_text(
        "Local document Q&A",
        "本地资料问答",
        "本地文件問答",
    )
    user_prompt = localized_text(
        f"""
Purpose:
{purpose_hint}

Original retrieval question:
{query}

Split it into independent, specific sub-questions that are easy to retrieve.
""",
        f"""
用途：
{purpose_hint}

原始检索问题：
{query}

请拆成多个独立、具体、便于检索的子问题。
""",
        f"""
用途：
{purpose_hint}

原始檢索問題：
{query}

請拆成多個獨立、具體、便於檢索的子問題。
""",
    )
    try:
        response = create_llm_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            mode=mode,
        )
        raw_text = (response.choices[0].message.content or "").strip()
        queries = []
        for line in raw_text.splitlines():
            cleaned = re.sub(r"^\s*[-*\d.、）)]+", "", line).strip()
            if cleaned and cleaned not in queries:
                queries.append(cleaned)
        if not queries:
            queries = heuristic_decompose_question(query, max_queries=max_queries)
        return queries[:max_queries], None
    except Exception as e:
        return heuristic_decompose_question(query, max_queries=max_queries), str(e)


def search_vector_store_multi_query(
    queries: List[str],
    top_k: int = 5,
    doc_category: Optional[str] = None,
    max_distance: Optional[float] = None,
    fetch_k: Optional[int] = None,
    use_hybrid: bool = DEFAULT_USE_HYBRID_SEARCH,
    use_reranker: bool = DEFAULT_USE_RERANKER,
) -> List[Dict[str, Any]]:
    cleaned_queries = [query.strip() for query in queries if query and query.strip()]
    if not cleaned_queries:
        return []
    if len(cleaned_queries) == 1:
        return search_vector_store(
            cleaned_queries[0],
            top_k=top_k,
            doc_category=doc_category,
            max_distance=max_distance,
            fetch_k=fetch_k,
            use_hybrid=use_hybrid,
            use_reranker=use_reranker,
        )

    ranked_lists = []
    results_by_id: Dict[str, Dict[str, Any]] = {}
    per_query_top_k = max(top_k, min(fetch_k or default_fetch_k(top_k), 12))
    for sub_query in cleaned_queries:
        sub_results = search_vector_store(
            sub_query,
            top_k=per_query_top_k,
            doc_category=doc_category,
            max_distance=max_distance,
            fetch_k=fetch_k,
            use_hybrid=use_hybrid,
            use_reranker=use_reranker,
        )
        ranked = []
        for item in sub_results:
            item_id = item.get("id", str(uuid.uuid4()))
            copied = dict(item)
            copied["matched_query"] = sub_query
            results_by_id[item_id] = copied
            ranked.append((item_id, copied))
        ranked_lists.append(ranked)

    merged = reciprocal_rank_merge(ranked_lists)
    return dedupe_search_results(merged, top_k)


def search_with_min_coverage(
    queries: List[str],
    top_k: int,
    min_results: int,
    doc_category: str,
    max_distance: Optional[float],
    fetch_k: Optional[int],
    use_hybrid: bool,
    use_reranker: bool,
) -> List[Dict[str, Any]]:
    min_results = max(0, min(min_results, top_k))
    results = search_vector_store_multi_query(
        queries,
        top_k=top_k,
        doc_category=doc_category,
        max_distance=max_distance,
        fetch_k=fetch_k,
        use_hybrid=use_hybrid,
        use_reranker=use_reranker,
    )
    if len(results) >= min_results or max_distance is None:
        return results

    relaxed_results = search_vector_store_multi_query(
        queries,
        top_k=top_k,
        doc_category=doc_category,
        max_distance=None,
        fetch_k=fetch_k,
        use_hybrid=use_hybrid,
        use_reranker=use_reranker,
    )
    existing_ids = {item.get("id") for item in results}
    for item in relaxed_results:
        if len(results) >= min_results:
            break
        if item.get("id") in existing_ids:
            continue
        item["coverage_relaxed"] = True
        results.append(item)
    return dedupe_search_results(results, top_k)


def describe_source(metadata: Dict[str, Any]) -> str:
    parts = []
    if metadata.get("page"):
        parts.append(f"{source_label('page')}: {metadata.get('page')}")
    if metadata.get("slide"):
        parts.append(f"{source_label('slide')}: {metadata.get('slide')}")
    if metadata.get("sheet"):
        parts.append(f"{source_label('sheet')}: {metadata.get('sheet')}")
    if metadata.get("row_range"):
        parts.append(f"{source_label('row')}: {metadata.get('row_range')}")
    if metadata.get("table_index"):
        parts.append(f"{source_label('table')}: {metadata.get('table_index')}")
    if metadata.get("image_index"):
        image_label = f"{source_label('image')}: {metadata.get('image_index')}"
        if metadata.get("image_name"):
            image_label += f" ({metadata.get('image_name')})"
        parts.append(image_label)
    return "；".join(parts) if parts else source_label("none")


def build_context(search_results: List[Dict[str, Any]], title: Optional[str] = None) -> str:
    title = title or source_label("retrieval_materials")
    context_parts = [f"## {title}"]
    for i, item in enumerate(search_results, start=1):
        metadata = item["metadata"]
        content = item["content"]
        file_name = metadata.get("file_name", source_label("unknown_file"))
        chunk_index = metadata.get("chunk_index", source_label("unknown_chunk"))
        doc_category_name = translate_text(metadata.get("doc_category_name", source_label("unknown_type")))
        context_parts.append(
            f"[{source_label('material')} {i}]\n"
            f"{source_label('document_type')}: {doc_category_name}\n"
            f"{source_label('source_file')}: {file_name}\n"
            f"{source_label('chunk_index')}: {chunk_index}\n"
            f"{source_label('source_location')}: {describe_source(metadata)}\n"
            f"{source_label('content')}:\n{content}\n"
        )
    return "\n\n".join(context_parts)


def build_chat_history(
    chat_messages: List[Dict[str, Any]],
    max_messages: int = DEFAULT_CONTEXT_TURNS * 2,
) -> str:
    if not chat_messages or max_messages <= 0:
        return source_label("none")

    history_parts = []
    for message in chat_messages[-max_messages:]:
        role_name = source_label("user") if message.get("role") == "user" else source_label("assistant")
        content = str(message.get("content", "")).strip()
        if content:
            history_parts.append(f"{role_name}: {content}")
    return "\n".join(history_parts) if history_parts else source_label("none")


def rewrite_retrieval_query(
    question: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    mode: str = "fast",
    context_turns: int = DEFAULT_CONTEXT_TURNS,
    purpose: str = "rag",
) -> str:
    history = build_chat_history(chat_history or [], max_messages=context_turns * 2)
    if history == source_label("none"):
        return question

    purpose_hint = localized_text(
        "Compliance gap analysis. Preserve regulatory requirements, policies, enterprise evidence, issue points, and remediation direction.",
        "用于合规差距分析，需要同时覆盖监管要求、规章制度、企业资料、问题点和整改方向。",
        "用於合規差距分析，需要同時覆蓋監管要求、規章制度、企業資料、問題點和整改方向。",
    ) if purpose == "compliance" else localized_text(
        "Local document Q&A. Preserve the entities, policies, matters, and constraints the user truly wants to retrieve.",
        "用于本地文档问答，需要保留用户真正要检索的实体、制度、事项和限定条件。",
        "用於本地文件問答，需要保留使用者真正要檢索的實體、制度、事項和限定條件。",
    )
    system_prompt = localized_text(
        f"""
You are a retrieval query rewriter.
Rewrite the user's current question with the conversation history into one complete query suitable for vector database retrieval.
Only output the rewritten query. Do not answer, explain, or add a list.
If the current question is already complete, keep it as-is or only lightly complete it.
Output language: {llm_language_name()}.
""",
        """
你是一个检索问题改写器。
你的任务是把用户当前问题结合对话历史，改写成一个适合向量数据库检索的完整简体中文问题。
只输出改写后的问题，不要回答，不要解释，不要添加列表。
如果当前问题已经完整，原样或轻微补全即可。
""",
        """
你是一個檢索問題改寫器。
你的任務是把使用者當前問題結合對話歷史，改寫成一個適合向量資料庫檢索的完整繁體中文問題。
只輸出改寫後的問題，不要回答，不要解釋，不要添加列表。
如果當前問題已經完整，原樣或輕微補全即可。
""",
    )
    user_prompt = localized_text(
        f"""
Purpose:
{purpose_hint}

Conversation history:
{history}

Current question:
{question}

Output one complete, clear query suitable for retrieval.
""",
        f"""
用途：
{purpose_hint}

对话历史：
{history}

当前问题：
{question}

请输出一个完整、明确、适合检索的简体中文问题。
""",
        f"""
用途：
{purpose_hint}

對話歷史：
{history}

當前問題：
{question}

請輸出一個完整、明確、適合檢索的繁體中文問題。
""",
    )
    response = create_llm_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        mode=mode,
    )
    rewritten_query = (response.choices[0].message.content or "").strip()
    return rewritten_query or question


def maybe_rewrite_retrieval_query(
    question: str,
    chat_history: Optional[List[Dict[str, Any]]],
    enabled: bool,
    mode: str,
    context_turns: int,
    purpose: str,
) -> Tuple[str, Optional[str]]:
    if not enabled:
        return question, None
    try:
        return rewrite_retrieval_query(
            question,
            chat_history=chat_history,
            mode=mode,
            context_turns=context_turns,
            purpose=purpose,
        ), None
    except Exception as e:
        return question, str(e)


def ask_llm(
    question: str,
    search_results: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, Any]]] = None,
    mode: str = "fast",
    context_turns: int = DEFAULT_CONTEXT_TURNS,
) -> str:
    context = build_context(search_results)
    history = build_chat_history(chat_history or [], max_messages=context_turns * 2)
    system_prompt = localized_text(
        f"""
You are a rigorous local-document Q&A assistant.
Answer only from the retrieved materials provided by the user.
If the materials do not contain a clear answer, say "The current materials do not provide enough information to determine this." Do not fabricate.
Whenever possible, cite source file, chunk number, and source location.
If the conversation history conflicts with the retrieved materials, rely on the retrieved materials.
{llm_language_instruction()}
""",
        """
你是一个严谨的本地文档问答助手。
你只能根据用户提供的【检索资料】回答问题。
如果资料中没有明确答案，请直接说“根据当前资料无法确定”，不要编造。
回答时尽量引用来源文件、片段编号和来源位置。
如果【对话历史】与【检索资料】冲突，以【检索资料】为准。
""",
        """
你是一個嚴謹的本地文件問答助手。
你只能根據使用者提供的【檢索資料】回答問題。
如果資料中沒有明確答案，請直接說「根據當前資料無法確定」，不要編造。
回答時盡量引用來源文件、片段編號和來源位置。
如果【對話歷史】與【檢索資料】衝突，以【檢索資料】為準。
""",
    )
    user_prompt = localized_text(
        f"""
Current conversation history:
{history}

Retrieved materials from the vector database:
{context}

Current user question:
{question}

Answer based on the materials above.
""",
        f"""
下面是当前对话历史：
{history}

下面是从向量数据库检索出来的资料：
{context}

当前用户问题：
{question}

请基于上述资料回答。
""",
        f"""
下面是當前對話歷史：
{history}

下面是從向量資料庫檢索出來的資料：
{context}

當前使用者問題：
{question}

請基於上述資料回答。
""",
    )
    response = create_llm_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        mode=mode,
    )
    return response.choices[0].message.content


def ask_llm_general(
    question: str,
    chat_history: Optional[List[Dict[str, Any]]] = None,
    mode: str = "fast",
    context_turns: int = DEFAULT_CONTEXT_TURNS,
) -> str:
    history = build_chat_history(chat_history or [], max_messages=context_turns * 2)
    system_prompt = localized_text(
        f"""
You are a reliable assistant.
When no local retrieved materials are available, or when the user is only having a general conversation, respond normally.
If the question depends on local documents, enterprise materials, or regulatory requirements, remind the user to upload and ingest the relevant materials first.
{llm_language_instruction()}
""",
        """
你是一个可靠的简体中文助手。
当没有可用的本地检索资料，或用户只是普通交流时，可以进行普通对话。
如果问题涉及用户本地文档、企业资料或监管要求，请提醒用户先上传资料入库。
""",
        """
你是一個可靠的繁體中文助手。
當沒有可用的本地檢索資料，或使用者只是普通交流時，可以進行普通對話。
如果問題涉及使用者本地文件、企業資料或監管要求，請提醒使用者先上傳資料入庫。
""",
    )
    user_prompt = localized_text(
        f"""
Current conversation history:
{history}

Current user question:
{question}
""",
        f"""
下面是当前对话历史：
{history}

当前用户问题：
{question}
""",
        f"""
下面是當前對話歷史：
{history}

當前使用者問題：
{question}
""",
    )
    response = create_llm_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        mode=mode,
    )
    return response.choices[0].message.content


def is_likely_general_chat_question(question: str) -> bool:
    compact_question = "".join(question.strip().lower().split())
    return compact_question in {
        "你好",
        "您好",
        "hello",
        "hi",
        "嗨",
        "在吗",
        "谢谢",
        "感谢",
        "ok",
    }


def ask_llm_compliance(
    topic: str,
    regulation_results: List[Dict[str, Any]],
    enterprise_results: List[Dict[str, Any]],
    chat_history: Optional[List[Dict[str, Any]]] = None,
    mode: str = "fast",
    context_turns: int = DEFAULT_CONTEXT_TURNS,
    clause_by_clause: bool = False,
    include_missing_list: bool = True,
) -> str:
    history = build_chat_history(chat_history or [], max_messages=context_turns * 2)
    regulation_context = build_context(regulation_results, title=source_label("regulations"))
    enterprise_context = build_context(enterprise_results, title=source_label("enterprise"))
    clause_prompt = localized_text(
        "Compare each regulatory clause or requirement against enterprise materials. Each row should analyze only one clause or requirement.",
        "请按监管资料中的条款或要求逐条对照企业资料；每一行只分析一个监管条款或要求。",
        "請按監管資料中的條款或要求逐條對照企業資料；每一行只分析一個監管條款或要求。",
    ) if clause_by_clause else localized_text(
        "Summarize the main compliance gaps around the user's topic.",
        "请围绕用户主题归纳主要合规差距。",
        "請圍繞使用者主題歸納主要合規差距。",
    )
    missing_heading = source_label("missing_materials")
    missing_prompt = (
        localized_text(
            f'After the table, add a "### {missing_heading}" section listing additional enterprise materials needed for further judgment.',
            f"表格后必须追加“### {missing_heading}”，列出为了进一步判断还需要补充的企业资料。",
            f"表格後必須追加「### {missing_heading}」，列出為了進一步判斷還需要補充的企業資料。",
        )
        if include_missing_list
        else ""
    )
    shortage_label = localized_text(
        "Insufficient materials; supplementation required",
        "资料不足，需补充",
        "資料不足，需補充",
    )
    table_columns = localized_text(
        "Issue, Relevant Requirement, Enterprise Evidence, Risk Level, Remediation Recommendation, Sources",
        "问题点、对应监管要求、企业资料证据、风险等级、整改建议、引用来源",
        "問題點、對應監管要求、企業資料證據、風險等級、整改建議、引用來源",
    )
    system_prompt = localized_text(
        f"""
You are a rigorous compliance gap analysis assistant.
You must reference both the regulatory/policy materials and the enterprise materials.
Do not fabricate regulatory requirements, and do not conclude that the enterprise is non-compliant when enterprise evidence is insufficient.
Every conclusion must cite source file, chunk number, and source location from both regulatory and enterprise evidence.
If enterprise evidence is missing for a requirement, mark it as "{shortage_label}".
{clause_prompt}
First output a Markdown table with these columns: {table_columns}.
{missing_prompt}
You may add concise explanatory notes after the table when necessary.
{llm_language_instruction()}
""",
        f"""
你是一个严谨的合规差距分析助手。
你必须同时参考【监管要求 / 规章制度】和【企业资料】。
不要编造监管要求，也不要在企业资料不足时直接判定企业违规。
每个结论都必须引用监管资料和企业资料的来源文件、片段编号、来源位置。
如果企业资料没有对应证据，请标记为“{shortage_label}”。
{clause_prompt}
请先输出 Markdown 表格，列为：{table_columns}。
{missing_prompt}
表格后可以再补充必要说明。
""",
        f"""
你是一個嚴謹的合規差距分析助手。
你必須同時參考【監管要求 / 規章制度】和【企業資料】。
不要編造監管要求，也不要在企業資料不足時直接判定企業違規。
每個結論都必須引用監管資料和企業資料的來源文件、片段編號、來源位置。
如果企業資料沒有對應證據，請標記為「{shortage_label}」。
{clause_prompt}
請先輸出 Markdown 表格，列為：{table_columns}。
{missing_prompt}
表格後可以再補充必要說明。
""",
    )
    user_prompt = localized_text(
        f"""
Current compliance-analysis conversation history:
{history}

Analysis topic:
{topic}

[{source_label("regulations")}]
{regulation_context}

[{source_label("enterprise")}]
{enterprise_context}

Perform the compliance gap analysis based on the materials above.
""",
        f"""
下面是当前合规分析对话历史：
{history}

分析主题：
{topic}

【{source_label("regulations")}】
{regulation_context}

【{source_label("enterprise")}】
{enterprise_context}

请基于上述资料做合规差距分析。
""",
        f"""
下面是當前合規分析對話歷史：
{history}

分析主題：
{topic}

【{source_label("regulations")}】
{regulation_context}

【{source_label("enterprise")}】
{enterprise_context}

請基於上述資料做合規差距分析。
""",
    )
    response = create_llm_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        mode=mode,
    )
    return response.choices[0].message.content


# =========================
# UI 辅助
# =========================
