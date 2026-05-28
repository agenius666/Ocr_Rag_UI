"""Distillation data generation helpers.
蒸馏数据生成辅助函数。
"""

import random

from .services import *


DISTILLATION_TEXT_FIELDS = ("document", "text", "content", "chunk", "chunk_text", "page_content")
SFT_REQUIRED_FIELDS = ("instruction", "output")
PREFERENCE_REQUIRED_FIELDS = ("prompt", "chosen", "rejected", "judge_reason")


def extract_distillation_text(payload: Dict[str, Any]) -> str:
    """Find chunk text from common Qdrant payload fields.
    从常见 Qdrant payload 字段中查找 chunk 正文。
    """
    for field_name in DISTILLATION_TEXT_FIELDS:
        value = payload.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def format_distillation_source(point: Any, payload: Dict[str, Any]) -> str:
    """Build a compact source label for generated samples.
    为生成样本构造简洁来源标签。
    """
    file_name = payload.get("file_name") or payload.get("source_file") or payload.get("source") or ""
    chunk_index = payload.get("chunk_index")
    point_id = getattr(point, "id", "")
    parts = []
    if file_name:
        parts.append(str(file_name))
    if chunk_index is not None:
        parts.append(f"chunk {chunk_index}")
    if point_id:
        parts.append(f"id {point_id}")
    return " | ".join(parts) if parts else str(point_id)


def collect_distillation_chunk_pool(
    pool_size: int = 500,
    scan_limit: int = 5000,
    doc_category: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Reservoir-sample chunks from the active Qdrant collection.
    从当前 Qdrant collection 中流式蓄水池抽样，避免一次性读取全部 point。
    """
    pool_size = max(1, int(pool_size or 500))
    scan_limit = max(pool_size, int(scan_limit or 5000))
    where = {"doc_category": doc_category} if doc_category else None
    sampled_chunks: List[Dict[str, Any]] = []
    scanned_count = 0

    for point in iter_qdrant_points(where=where, batch_size=256, with_payload=True, with_vectors=False):
        scanned_count += 1
        payload = getattr(point, "payload", None) or {}
        if not isinstance(payload, dict):
            continue
        text = extract_distillation_text(payload)
        if not text:
            continue
        chunk = {
            "id": str(getattr(point, "id", "")),
            "text": text,
            "source": format_distillation_source(point, payload),
            "file_name": payload.get("file_name") or payload.get("source_file") or "",
            "chunk_index": payload.get("chunk_index"),
            "doc_category": payload.get("doc_category", ""),
        }
        if len(sampled_chunks) < pool_size:
            sampled_chunks.append(chunk)
        else:
            replacement_index = random.randint(0, scanned_count - 1)
            if replacement_index < pool_size:
                sampled_chunks[replacement_index] = chunk
        if scanned_count >= scan_limit:
            break
    return sampled_chunks, scanned_count


def format_context_chunks(chunks: List[Dict[str, Any]], max_chars_per_chunk: int = 1500) -> str:
    """Render sampled chunks into a compact LLM context block.
    将抽样 chunk 渲染为紧凑的大模型上下文。
    """
    max_chars_per_chunk = max(300, int(max_chars_per_chunk or 1500))
    parts = []
    for index, chunk in enumerate(chunks, start=1):
        text = str(chunk.get("text", "")).strip()
        if len(text) > max_chars_per_chunk:
            text = text[:max_chars_per_chunk].rstrip() + "..."
        parts.append(
            f"[Chunk {index}]\n"
            f"Source: {chunk.get('source', '')}\n"
            f"Content:\n{text}"
        )
    return "\n\n".join(parts)


def build_sft_distillation_prompt(
    chunks: List[Dict[str, Any]],
    batch_size: int,
    qa_type: str,
    max_chars_per_chunk: int = 1500,
) -> str:
    """Build the SFT JSON generation prompt.
    构造 SFT JSON 生成提示词。
    """
    context_chunks = format_context_chunks(chunks, max_chars_per_chunk=max_chars_per_chunk)
    return f"""
你是一名专业 IT 审计师，现在需要根据给定资料生成高质量的审计训练数据。

语言要求：
{llm_language_instruction()}

要求：
1. 问题必须基于资料内容，不要凭空编造。
2. 答案必须能从资料中找到依据。
3. 每条问答应尽量完整、准确、专业。
4. 避免重复问题。
5. 不要输出无关解释。
6. 必须严格输出 JSON 数组。
7. 不要使用 Markdown 代码块包裹 JSON。
8. 如果资料不足以生成问题，请少生成，不要编造。

资料如下：
{context_chunks}

请生成 {batch_size} 条 {qa_type} 类型的训练数据。

输出格式必须为 JSON 数组：
[
  {{
    "instruction": "问题或任务指令",
    "input": "必要的上下文或补充资料",
    "output": "标准答案",
    "source": "chunk 来源或文档名",
    "type": "{qa_type}"
  }}
]
""".strip()


def build_preference_distillation_prompt(
    chunks: List[Dict[str, Any]],
    batch_size: int,
    qa_type: str,
    max_chars_per_chunk: int = 1500,
) -> str:
    """Build the chosen/rejected preference JSON generation prompt.
    构造 chosen/rejected 偏好数据 JSON 生成提示词。
    """
    context_chunks = format_context_chunks(chunks, max_chars_per_chunk=max_chars_per_chunk)
    return f"""
你是一名专业 IT 审计师和训练数据标注专家。

语言要求：
{llm_language_instruction()}

请根据给定资料生成偏好训练数据。

要求：
1. 问题必须基于资料内容。
2. chosen 必须比 rejected 更准确、更完整、更专业。
3. rejected 可以是不完整、过于笼统、遗漏关键风险点或表达不规范的答案，但不能包含危险内容。
4. 必须说明 chosen 优于 rejected 的原因。
5. 严格输出 JSON 数组。
6. 不要使用 Markdown 代码块包裹 JSON。
7. 如果资料不足以生成问题，请少生成，不要编造。

资料如下：
{context_chunks}

请生成 {batch_size} 条 {qa_type} 类型的偏好数据。

输出格式：
[
  {{
    "prompt": "问题或任务",
    "chosen": "更好的答案",
    "rejected": "较差的答案",
    "judge_reason": "为什么 chosen 更好",
    "source": "chunk 来源或文档名",
    "type": "preference"
  }}
]
""".strip()


def strip_json_code_fence(raw_text: str) -> str:
    """Remove common Markdown fences around JSON.
    移除 JSON 外层常见 Markdown 代码块。
    """
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json|JSON)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_array_response(raw_text: str) -> List[Dict[str, Any]]:
    """Parse an LLM response into a list of JSON objects.
    将大模型响应解析为 JSON 对象列表。
    """
    text = strip_json_code_fence(raw_text)
    if not text:
        raise ValueError(localized_text("Empty model response.", "模型响应为空。", "模型響應為空。"))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(text[start : end + 1])
    if isinstance(parsed, dict):
        for key in ("items", "data", "results"):
            value = parsed.get(key)
            if isinstance(value, list):
                parsed = value
                break
    if not isinstance(parsed, list):
        raise ValueError(localized_text("The model did not return a JSON array.", "模型未返回 JSON 数组。", "模型未返回 JSON 陣列。"))
    return [item for item in parsed if isinstance(item, dict)]


def normalize_generated_text(value: Any) -> str:
    """Normalize generated scalar fields.
    标准化生成字段。
    """
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def validate_sft_items(
    items: List[Dict[str, Any]],
    qa_type: str,
    model_name: str,
    fallback_source: str,
    seen_instructions: set,
) -> List[Dict[str, Any]]:
    """Validate and normalize SFT items.
    校验并标准化 SFT 样本。
    """
    valid_items = []
    for item in items:
        instruction = normalize_generated_text(item.get("instruction"))
        output = normalize_generated_text(item.get("output"))
        if not instruction or not output or instruction in seen_instructions:
            continue
        seen_instructions.add(instruction)
        valid_items.append(
            {
                "id": str(uuid.uuid4()),
                "instruction": instruction,
                "input": normalize_generated_text(item.get("input")),
                "output": output,
                "source": normalize_generated_text(item.get("source")) or fallback_source,
                "type": normalize_generated_text(item.get("type")) or qa_type,
                "model": model_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return valid_items


def validate_preference_items(
    items: List[Dict[str, Any]],
    qa_type: str,
    model_name: str,
    fallback_source: str,
    seen_prompts: set,
) -> List[Dict[str, Any]]:
    """Validate and normalize chosen/rejected preference items.
    校验并标准化 chosen/rejected 偏好样本。
    """
    valid_items = []
    for item in items:
        prompt = normalize_generated_text(item.get("prompt"))
        chosen = normalize_generated_text(item.get("chosen"))
        rejected = normalize_generated_text(item.get("rejected"))
        judge_reason = normalize_generated_text(item.get("judge_reason"))
        if not prompt or not chosen or not rejected or not judge_reason:
            continue
        if chosen == rejected or prompt in seen_prompts:
            continue
        seen_prompts.add(prompt)
        valid_items.append(
            {
                "id": str(uuid.uuid4()),
                "prompt": prompt,
                "chosen": chosen,
                "rejected": rejected,
                "source": normalize_generated_text(item.get("source")) or fallback_source,
                "type": normalize_generated_text(item.get("type")) or qa_type,
                "judge_reason": judge_reason,
                "model": model_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return valid_items


def generate_distillation_batch(
    generation_mode: str,
    chunks: List[Dict[str, Any]],
    batch_size: int,
    qa_type: str,
    llm_mode: str,
    timeout_seconds: int,
    seen_keys: set,
    max_chars_per_chunk: int = 1500,
) -> Tuple[List[Dict[str, Any]], str]:
    """Generate and validate one distillation batch.
    生成并校验一个蒸馏数据批次。
    """
    model_name, _ = get_llm_mode_config(llm_mode)
    fallback_source = "; ".join(chunk.get("source", "") for chunk in chunks if chunk.get("source"))
    if generation_mode == "preference":
        user_prompt = build_preference_distillation_prompt(chunks, batch_size, qa_type, max_chars_per_chunk)
    else:
        user_prompt = build_sft_distillation_prompt(chunks, batch_size, qa_type, max_chars_per_chunk)

    response = create_llm_chat_completion(
        messages=[
            {
                "role": "system",
                "content": localized_text(
                    "You generate strict JSON training data and return JSON only.",
                    "你负责生成严格 JSON 训练数据，只返回 JSON。",
                    "你負責生成嚴格 JSON 訓練資料，只返回 JSON。",
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        mode=llm_mode,
        timeout_seconds=timeout_seconds,
    )
    raw_text = response.choices[0].message.content
    parsed_items = parse_json_array_response(raw_text)
    if generation_mode == "preference":
        return validate_preference_items(parsed_items, qa_type, model_name, fallback_source, seen_keys), raw_text
    return validate_sft_items(parsed_items, qa_type, model_name, fallback_source, seen_keys), raw_text


def build_distillation_jsonl(items: List[Dict[str, Any]]) -> bytes:
    """Build UTF-8 JSONL bytes.
    构造 UTF-8 JSONL 字节。
    """
    return ("\n".join(json.dumps(item, ensure_ascii=False) for item in items) + ("\n" if items else "")).encode("utf-8")


def build_distillation_excel(items: List[Dict[str, Any]], generation_mode: str) -> bytes:
    """Build an Excel review workbook.
    构造用于人工审核的 Excel 工作簿。
    """
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "distillation"
    headers = (
        ["id", "instruction", "input", "output", "source", "type", "model", "created_at"]
        if generation_mode == "sft"
        else ["id", "prompt", "chosen", "rejected", "source", "type", "judge_reason", "model", "created_at"]
    )
    sheet.append(headers)
    for item in items:
        sheet.append([item.get(header, "") for header in headers])
    for column_cells in sheet.columns:
        column_letter = column_cells[0].column_letter
        sheet.column_dimensions[column_letter].width = min(48, max(12, len(str(column_cells[0].value or "")) + 4))
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()
