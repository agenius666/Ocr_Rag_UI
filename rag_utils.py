import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Sequence, Tuple


def split_semantic_chunks(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    text = text.strip()
    if not text:
        return []
    if overlap >= chunk_size:
        raise ValueError("Chunk 重叠必须小于 Chunk 大小。")

    units = split_text_units(text)
    chunks = []
    current = ""

    for unit in units:
        if not unit:
            continue
        if len(unit) > chunk_size:
            if current.strip():
                chunks.append(current.strip())
                current = build_overlap_prefix(current, overlap)
            for part in split_long_unit(unit, chunk_size, overlap):
                chunks.append(part)
            continue

        candidate = f"{current}\n{unit}".strip() if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current.strip():
                chunks.append(current.strip())
                current = build_overlap_prefix(current, overlap)
            current = f"{current}\n{unit}".strip() if current else unit

    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def split_text_units(text: str) -> List[str]:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    units = []
    buffer = []

    for line in lines:
        if not line:
            if buffer:
                units.append("\n".join(buffer).strip())
                buffer = []
            continue

        if is_heading_line(line) and buffer:
            units.append("\n".join(buffer).strip())
            buffer = [line]
        else:
            buffer.append(line)

    if buffer:
        units.append("\n".join(buffer).strip())

    refined_units = []
    for unit in units:
        if len(unit) <= 900:
            refined_units.append(unit)
        else:
            refined_units.extend(split_by_sentence(unit))
    return refined_units


def is_heading_line(line: str) -> bool:
    compact = line.strip()
    if len(compact) > 80:
        return False
    patterns = [
        r"^第[一二三四五六七八九十百千万\d]+[章节条款部分]",
        r"^[一二三四五六七八九十]+[、.．]",
        r"^\d+(\.\d+){0,4}[、.．\s]",
        r"^（[一二三四五六七八九十\d]+）",
        r"^\([一二三四五六七八九十\d]+\)",
    ]
    return any(re.match(pattern, compact) for pattern in patterns)


def split_by_sentence(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？；;])\s*", text)
    return [part.strip() for part in parts if part.strip()]


def split_long_unit(unit: str, chunk_size: int, overlap: int) -> List[str]:
    output = []
    start = 0
    while start < len(unit):
        end = start + chunk_size
        chunk = unit[start:end].strip()
        if chunk:
            output.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
    return output


def build_overlap_prefix(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    return text[-overlap:].strip()


def tokenize_for_search(text: str) -> List[str]:
    text = (text or "").lower()
    tokens = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]", text)
    chinese_phrases = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    for phrase in chinese_phrases:
        max_ngram = min(6, len(phrase))
        for size in range(2, max_ngram + 1):
            tokens.extend(phrase[index : index + size] for index in range(0, len(phrase) - size + 1))
    return tokens


def keyword_rank_documents(
    query: str,
    documents: Sequence[str],
    top_k: int,
) -> List[Tuple[int, float]]:
    query_tokens = tokenize_for_search(query)
    if not query_tokens or not documents:
        return []

    tokenized_docs = [tokenize_for_search(document) for document in documents]
    doc_count = len(tokenized_docs)
    avg_doc_len = sum(len(tokens) for tokens in tokenized_docs) / max(doc_count, 1)
    doc_freq = Counter()
    for tokens in tokenized_docs:
        doc_freq.update(set(tokens))

    query_counter = Counter(query_tokens)
    scored = []
    k1 = 1.5
    b = 0.75
    for doc_index, doc_tokens in enumerate(tokenized_docs):
        if not doc_tokens:
            continue
        term_freq = Counter(doc_tokens)
        doc_len = len(doc_tokens)
        score = 0.0
        for token, query_weight in query_counter.items():
            tf = term_freq.get(token, 0)
            if tf <= 0:
                continue
            idf = math.log(1 + (doc_count - doc_freq[token] + 0.5) / (doc_freq[token] + 0.5))
            denom = tf + k1 * (1 - b + b * doc_len / max(avg_doc_len, 1))
            score += query_weight * idf * (tf * (k1 + 1) / denom)
        if score > 0:
            scored.append((doc_index, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


def reciprocal_rank_merge(
    ranked_lists: Sequence[Iterable[Tuple[str, Dict[str, Any]]]],
    k: int = 60,
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for ranked_items in ranked_lists:
        for rank, (item_id, item) in enumerate(ranked_items, start=1):
            entry = merged.setdefault(
                item_id,
                {
                    "item": item,
                    "rrf_score": 0.0,
                },
            )
            entry["rrf_score"] += 1.0 / (k + rank)
    output = []
    for entry in merged.values():
        item = dict(entry["item"])
        item["rrf_score"] = entry["rrf_score"]
        output.append(item)
    output.sort(key=lambda item: item.get("rrf_score", 0.0), reverse=True)
    return output


def parse_markdown_table(markdown_text: str) -> List[Dict[str, str]]:
    lines = [line.strip() for line in markdown_text.splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 3:
        return []

    header = split_markdown_table_row(table_lines[0])
    separator = split_markdown_table_row(table_lines[1])
    if not header or not all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in separator):
        return []

    rows = []
    for line in table_lines[2:]:
        cells = split_markdown_table_row(line)
        if len(cells) < len(header):
            cells.extend([""] * (len(header) - len(cells)))
        row = {column: cells[index].strip() for index, column in enumerate(header)}
        if any(row.values()):
            rows.append(row)
    return rows


def split_markdown_table_row(row: str) -> List[str]:
    return [cell.strip() for cell in row.strip().strip("|").split("|")]
