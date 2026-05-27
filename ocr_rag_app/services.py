"""Shared services, state, parsing, retrieval, and LLM orchestration.
共享服务、状态、解析、检索和大模型编排。
"""

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "true")

import builtins
import csv
import gc
import hashlib
import http.client
import io
import json
import platform
import re
import shutil
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

import fitz
import streamlit as st
from docx import Document
from dotenv import dotenv_values, load_dotenv
from openai import OpenAI
from openpyxl import Workbook, load_workbook
from pptx import Presentation
from .rag_utils import (
    keyword_rank_documents,
    parse_markdown_table,
    reciprocal_rank_merge,
    split_semantic_chunks,
)

try:
    fitz.TOOLS.mupdf_display_errors(False)
except Exception:
    pass

# =========================
# 基础配置
# =========================
load_dotenv()

ENV_FILE = ".env"
APP_DB_FILE = "app_state.sqlite3"
UPLOAD_DIR = "uploads"
QDRANT_DIR = "qdrant_db"
BACKUP_DIR = "backups"
BACKUP_MANIFEST_NAME = "manifest.json"
BACKUP_INGESTED_FILES_NAME = "ingested_files.json"
COLLECTION_NAME = "ocr_rag_docs"
DEFAULT_QDRANT_MODE = "local"
DEFAULT_QDRANT_LOCAL_PATH = QDRANT_DIR
DEFAULT_QDRANT_URL = "http://127.0.0.1:6333"
DEFAULT_QDRANT_API_KEY = ""
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
EMBEDDING_MODEL_OPTIONS = {
    "BAAI/bge-m3": {
        "vector_size": 1024,
        "collection_name": COLLECTION_NAME,
        "cache_key": "bge_cache_dir",
        "default_cache_dir_name": "bge-m3",
        "label": {
            "en": "BAAI/bge-m3 (1024 dimensions, multilingual)",
            "zh_CN": "BAAI/bge-m3（1024 维，多语言）",
            "zh_TW": "BAAI/bge-m3（1024 維，多語言）",
        },
    },
    "BAAI/bge-base-zh-v1.5": {
        "vector_size": 768,
        "collection_name": "ocr_rag_docs_bge_base_zh_v15",
        "cache_key": "bge_base_cache_dir",
        "default_cache_dir_name": "bge-base-zh-v1.5",
        "label": {
            "en": "BAAI/bge-base-zh-v1.5 (768 dimensions, Chinese)",
            "zh_CN": "BAAI/bge-base-zh-v1.5（768 维，中文）",
            "zh_TW": "BAAI/bge-base-zh-v1.5（768 維，中文）",
        },
    },
}
RERANKER_MODEL_OPTIONS = {
    "BAAI/bge-reranker-v2-m3": {
        "cache_key": "reranker_cache_dir",
        "default_cache_dir_name": "bge-reranker-v2-m3",
        "label": {
            "en": "BAAI/bge-reranker-v2-m3",
            "zh_CN": "BAAI/bge-reranker-v2-m3",
            "zh_TW": "BAAI/bge-reranker-v2-m3",
        },
    },
    "BAAI/bge-reranker-base": {
        "cache_key": "reranker_base_cache_dir",
        "default_cache_dir_name": "bge-reranker-base",
        "label": {
            "en": "BAAI/bge-reranker-base",
            "zh_CN": "BAAI/bge-reranker-base",
            "zh_TW": "BAAI/bge-reranker-base",
        },
    },
}
VECTOR_SIZE = EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME]["vector_size"]
EXTRACTED_IMAGE_DIR = os.path.join(UPLOAD_DIR, "extracted_images")
CONVERTED_DIR = os.path.join(UPLOAD_DIR, "converted")
DEFAULT_MODEL_CACHE_ROOT = os.path.abspath("model_cache")
DEFAULT_PADDLEOCR_CACHE_DIR = os.path.join(DEFAULT_MODEL_CACHE_ROOT, "paddlex")
DEFAULT_BGE_CACHE_DIR = os.path.join(DEFAULT_MODEL_CACHE_ROOT, "bge-m3")
DEFAULT_BGE_BASE_CACHE_DIR = os.path.join(DEFAULT_MODEL_CACHE_ROOT, "bge-base-zh-v1.5")
DEFAULT_RERANKER_CACHE_DIR = os.path.join(DEFAULT_MODEL_CACHE_ROOT, "bge-reranker-v2-m3")
DEFAULT_RERANKER_BASE_CACHE_DIR = os.path.join(DEFAULT_MODEL_CACHE_ROOT, "bge-reranker-base")
DEFAULT_SOFFICE_BINARY_PATH = ""
DEFAULT_MODEL_DOWNLOAD_SOURCE = "huggingface"
DEFAULT_CUSTOM_HF_ENDPOINT = ""
DEFAULT_PADDLEOCR_MODEL_SOURCE = "huggingface"
DEFAULT_LIBREOFFICE_INSTALL_SOURCE = "system"
DEFAULT_CUSTOM_LIBREOFFICE_INSTALL_COMMAND = ""
HF_MIRROR_ENDPOINT = "https://hf-mirror.com"
MODEL_DOWNLOAD_SOURCE_OPTIONS = {
    "huggingface": {
        "en": "Hugging Face Official",
        "zh_CN": "Hugging Face 官方",
        "zh_TW": "Hugging Face 官方",
    },
    "hf_mirror": {
        "en": "HF Mirror",
        "zh_CN": "HF Mirror 镜像",
        "zh_TW": "HF Mirror 鏡像",
    },
    "custom": {
        "en": "Custom Hugging Face Endpoint",
        "zh_CN": "自定义 Hugging Face Endpoint",
        "zh_TW": "自訂 Hugging Face Endpoint",
    },
}
PADDLEOCR_MODEL_SOURCE_OPTIONS = {
    "huggingface": {
        "en": "Hugging Face / PaddlePaddle",
        "zh_CN": "Hugging Face / PaddlePaddle",
        "zh_TW": "Hugging Face / PaddlePaddle",
    },
    "modelscope": {
        "en": "ModelScope",
        "zh_CN": "ModelScope 魔搭",
        "zh_TW": "ModelScope 魔搭",
    },
    "aistudio": {
        "en": "Baidu AIStudio",
        "zh_CN": "百度 AIStudio",
        "zh_TW": "百度 AIStudio",
    },
    "bos": {
        "en": "Paddle BOS",
        "zh_CN": "Paddle BOS",
        "zh_TW": "Paddle BOS",
    },
}
LIBREOFFICE_INSTALL_SOURCE_OPTIONS = {
    "system": {
        "en": "System Package Manager",
        "zh_CN": "系统包管理器",
        "zh_TW": "系統套件管理器",
    },
    "custom_command": {
        "en": "Custom Install Command",
        "zh_CN": "自定义安装命令",
        "zh_TW": "自訂安裝命令",
    },
}

DEFAULT_LLM_BASE_URL = "http://127.0.0.1:27292/v1"
DEFAULT_LLM_API_KEY = "EMPTY"
DEFAULT_LLM_MODEL = "local-model"
DEFAULT_LLM_EXTRA_BODY = "{}"
DEFAULT_LLM_API_TYPE = "auto"
LLM_MODE_OPTIONS = {
    "快速": "fast",
    "思考": "thinking",
}
LLM_API_TYPE_OPTIONS = {
    "自动识别": "auto",
    "OpenAI 兼容": "openai",
    "Anthropic Messages": "anthropic",
}
PDF_OCR_MODE_OPTIONS = {
    "智能 OCR（推荐，低内存）": "smart",
    "强制每页 OCR（最全但高内存）": "force",
    "仅提取 PDF 文字（最低内存）": "text",
}
PADDLEOCR_MODEL_OPTIONS = {
    "Server（高精度，占用更高）": {
        "det": "PP-OCRv5_server_det",
        "rec": "PP-OCRv5_server_rec",
    },
    "Mobile（低内存，速度更快）": {
        "det": "PP-OCRv5_mobile_det",
        "rec": "PP-OCRv5_mobile_rec",
    },
}
CHAT_PANEL_HEIGHT = 560
DEFAULT_CONTEXT_TURNS = 6
DEFAULT_RAG_TOP_K = 3
DEFAULT_COMPLIANCE_REGULATION_TOP_K = 6
DEFAULT_COMPLIANCE_ENTERPRISE_TOP_K = 8
DEFAULT_COMPLIANCE_MIN_REGULATION_EVIDENCE = 3
DEFAULT_COMPLIANCE_MIN_ENTERPRISE_EVIDENCE = 3
DEFAULT_VECTOR_MAX_DISTANCE = 0.85
DEFAULT_USE_HYBRID_SEARCH = True
DEFAULT_USE_RERANKER = False
DEFAULT_RETRIEVAL_FETCH_K = 20
DEFAULT_QUERY_DECOMPOSE = True
DEFAULT_BACKGROUND_INGEST = True
EMBEDDING_BATCH_SIZE = 8
VECTOR_ADD_BATCH_SIZE = 32
OCR_PDF_DPI = 120
OCR_MAX_PAGE_SIDE_PIXELS = 1800
OCR_TILE_MAX_SIDE_PIXELS = 3200
OCR_TILE_OVERLAP_PIXELS = 80
OCR_BOX_METADATA_LIMIT = 300
IMAGE_PREPROCESS_MODE_OPTIONS = {
    "auto": {
        "en": "Auto (recommended)",
        "zh_CN": "自动（推荐）",
        "zh_TW": "自動（推薦）",
    },
    "low": {
        "en": "Low memory",
        "zh_CN": "低内存",
        "zh_TW": "低記憶體",
    },
    "balanced": {
        "en": "Balanced",
        "zh_CN": "均衡",
        "zh_TW": "均衡",
    },
    "high": {
        "en": "High accuracy",
        "zh_CN": "高精度",
        "zh_TW": "高精度",
    },
    "off": {
        "en": "Disable image preprocessing",
        "zh_CN": "关闭图片预处理",
        "zh_TW": "關閉圖片預處理",
    },
}
DEFAULT_IMAGE_PREPROCESS_MODE = "auto"
DEFAULT_IMAGE_PREPROCESS_MODE_LABEL = "自动（推荐）"
IMAGE_PREPROCESS_PRESETS = {
    "auto": {"max_side": 2400, "max_pixels": 5_000_000, "jpeg_quality": 90, "grayscale": True},
    "low": {"max_side": 1800, "max_pixels": 3_000_000, "jpeg_quality": 88, "grayscale": True},
    "balanced": {"max_side": 2400, "max_pixels": 5_000_000, "jpeg_quality": 90, "grayscale": True},
    "high": {"max_side": 3200, "max_pixels": 8_000_000, "jpeg_quality": 95, "grayscale": False},
    "off": {"max_side": 0, "max_pixels": 0, "jpeg_quality": 95, "grayscale": False},
}
DEFAULT_PADDLEOCR_MODEL_LABEL = "Server（高精度，占用更高）"
DEFAULT_UI_LANGUAGE = "en"

MODERN_SUPPORTED_TYPES = [
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "webp",
    "bmp",
    "docx",
    "pptx",
    "xlsx",
    "csv",
    "txt",
]
LEGACY_OFFICE_TYPES = ["doc", "ppt", "xls"]
SUPPORTED_TYPES = MODERN_SUPPORTED_TYPES + LEGACY_OFFICE_TYPES
SUPPORTED_TYPE_LABEL = ", ".join(ext.upper() for ext in SUPPORTED_TYPES)

DOC_CATEGORY_OPTIONS = {
    "监管要求 / 规章制度": "regulation",
    "企业资料": "enterprise",
    "其他资料": "general",
}
DOC_CATEGORY_NAMES = {value: key for key, value in DOC_CATEGORY_OPTIONS.items()}
OCR_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(QDRANT_DIR, exist_ok=True)
os.makedirs(EXTRACTED_IMAGE_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)
os.makedirs(DEFAULT_MODEL_CACHE_ROOT, exist_ok=True)

# =========================
# Streamlit 页面
# =========================
GLOBAL_STYLE_CSS = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden; height: 0; position: fixed;}
    [data-testid="stDecoration"] {display: none;}

    .st-key-main_navigation_tabs div[data-testid="stRadio"],
    div[data-testid="stRadio"][aria-label="Main Navigation"],
    div[data-testid="stRadio"][aria-label="主导航"],
    div[data-testid="stRadio"][aria-label="主導覽"] {
        margin-top: 0.35rem;
        margin-bottom: 1.6rem;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] div[role="radiogroup"],
    div[data-testid="stRadio"][aria-label="Main Navigation"] div[role="radiogroup"],
    div[data-testid="stRadio"][aria-label="主导航"] div[role="radiogroup"],
    div[data-testid="stRadio"][aria-label="主導覽"] div[role="radiogroup"] {
        align-items: flex-end;
        gap: 1.45rem;
        border-bottom: 1px solid rgba(49, 51, 63, 0.18);
        padding-bottom: 0;
        min-height: 2.95rem;
        flex-wrap: wrap;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] label,
    div[data-testid="stRadio"][aria-label="Main Navigation"] label,
    div[data-testid="stRadio"][aria-label="主导航"] label,
    div[data-testid="stRadio"][aria-label="主導覽"] label {
        margin: 0 0 -1px 0;
        padding: 0.52rem 0 0.72rem 0;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        background: transparent !important;
        color: #31333f !important;
        font-weight: 600 !important;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] label > div:first-child,
    div[data-testid="stRadio"][aria-label="Main Navigation"] label > div:first-child,
    div[data-testid="stRadio"][aria-label="主导航"] label > div:first-child,
    div[data-testid="stRadio"][aria-label="主導覽"] label > div:first-child {
        display: none !important;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stRadio"][aria-label="Main Navigation"] label:has(input:checked),
    div[data-testid="stRadio"][aria-label="主导航"] label:has(input:checked),
    div[data-testid="stRadio"][aria-label="主導覽"] label:has(input:checked) {
        color: #ff4b4b !important;
        border-bottom-color: #ff4b4b !important;
        font-weight: 700 !important;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] label div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="Main Navigation"] label div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="主导航"] label div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="主導覽"] label div[data-testid="stMarkdownContainer"] p {
        color: inherit !important;
        font-weight: inherit;
        margin-bottom: 0;
    }
    .st-key-main_navigation_tabs div[data-testid="stRadio"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="Main Navigation"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="主导航"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"][aria-label="主導覽"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p {
        color: #ff4b4b !important;
        font-weight: 700 !important;
    }
    .st-key-main_navigation_tabs label:has(input:checked) p {
        color: #ff4b4b !important;
        font-weight: 700 !important;
    }
    </style>
"""


def render_global_styles() -> None:
    """Inject global Streamlit CSS on every rerun.
    每次重跑时注入全局 Streamlit 样式。
    """
    st.markdown(GLOBAL_STYLE_CSS, unsafe_allow_html=True)



def ensure_session_defaults() -> None:
    """Initialize Streamlit session keys used across split modules.
    初始化拆分模块共享使用的 Streamlit 会话键。
    """
    st.session_state.setdefault("model_events", [])


# =========================
# 应用状态数据库
# =========================
def current_timestamp() -> float:
    return time.time()


class AppDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._local = threading.local()
        self._initialize_schema()

    def _new_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._new_connection()
            self._local.conn = conn
        return conn

    def execute(self, *args, **kwargs):
        return self._connection().execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        return self._connection().executemany(*args, **kwargs)

    def commit(self) -> None:
        try:
            self._connection().commit()
        except sqlite3.DatabaseError as exc:
            if "no transaction is active" in str(exc).lower():
                return
            raise

    def close_current_thread_connection(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def _initialize_schema(self) -> None:
        conn = self._new_connection()
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id TEXT PRIMARY KEY,
                session_type TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingested_files (
                sha256 TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                doc_category TEXT NOT NULL,
                doc_label TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_tasks (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                total_files INTEGER NOT NULL,
                processed_files INTEGER NOT NULL,
                success_count INTEGER NOT NULL,
                duplicate_count INTEGER NOT NULL,
                skipped_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                current_file TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_task_items (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                FOREIGN KEY(task_id) REFERENCES ingest_tasks(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_sessions_type_updated "
            "ON chat_sessions(session_type, updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created "
            "ON chat_messages(session_id, created_at ASC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingested_files_updated "
            "ON ingested_files(updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingest_tasks_updated "
            "ON ingest_tasks(updated_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ingest_task_items_task "
            "ON ingest_task_items(task_id, updated_at DESC)"
        )
        conn.commit()
        conn.close()


@st.cache_resource
def load_app_db() -> AppDatabase:
    return AppDatabase(APP_DB_FILE)


app_db = load_app_db()
APP_DB_LOCK = threading.RLock()


def get_config_value(key: str, default: str = "") -> str:
    with APP_DB_LOCK:
        row = app_db.execute(
            "SELECT value FROM app_config WHERE key = ?",
            (key,),
        ).fetchone()
    return str(row["value"]) if row else default


def set_config_value(key: str, value: Any) -> None:
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO app_config (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, str(value), current_timestamp()),
        )
        app_db.commit()


def get_int_config(key: str, default: int) -> int:
    try:
        return int(get_config_value(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_float_config(key: str, default: float) -> float:
    try:
        return float(get_config_value(key, str(default)))
    except (TypeError, ValueError):
        return default


def get_bool_config(key: str, default: bool) -> bool:
    raw_value = get_config_value(key, "true" if default else "false").lower()
    return raw_value in {"1", "true", "yes", "on"}


def set_bool_config(key: str, value: bool) -> None:
    set_config_value(key, "true" if value else "false")


LANGUAGE_OPTIONS = {
    "English": "en",
    "简体中文": "zh_CN",
    "繁體中文": "zh_TW",
}
LANGUAGE_LABEL_BY_CODE = {value: key for key, value in LANGUAGE_OPTIONS.items()}

TRANSLATIONS = {
    "OCR + BGE-M3 + Qdrant + 本地大模型": {
        "en": "OCR + BGE + Qdrant + Local LLM",
        "zh_TW": "OCR + BGE + Qdrant + 本地大模型",
    },
    "上传制度、监管要求和企业资料，解析后写入 Qdrant 向量库，再调用 OpenAI 兼容接口做问答和合规差距分析。": {
        "en": "Upload policies, regulatory requirements, and enterprise materials; parse them into Qdrant, then answer questions and analyze compliance through an OpenAI-compatible local LLM endpoint.",
        "zh_TW": "上傳制度、監管要求和企業資料，解析後寫入 Qdrant 向量庫，再調用 OpenAI 相容接口做問答和合規差距分析。",
    },
    "上传入库": {"en": "Ingest", "zh_TW": "上傳入庫"},
    "检索问答": {"en": "RAG Chat", "zh_TW": "檢索問答"},
    "合规分析": {"en": "Compliance", "zh_TW": "合規分析"},
    "配置中心": {"en": "Settings", "zh_TW": "配置中心"},
    "模型状态": {"en": "Model Status", "zh_TW": "模型狀態"},
    "文档库管理": {"en": "Library", "zh_TW": "文件庫管理"},
    "上传文件并写入向量库": {"en": "Upload And Ingest Files", "zh_TW": "上傳文件並寫入向量庫"},
    "上传方式": {"en": "Upload Mode", "zh_TW": "上傳方式"},
    "文件 / 多文件": {"en": "File / Multiple Files", "zh_TW": "文件 / 多文件"},
    "文件夹（含子文件夹）": {"en": "Folder Including Subfolders", "zh_TW": "資料夾（含子資料夾）"},
    "选择文件夹": {"en": "Choose Folder", "zh_TW": "選擇資料夾"},
    "选择文件": {"en": "Choose Files", "zh_TW": "選擇文件"},
    "上传文件或文件夹": {"en": "Upload Files Or Folder", "zh_TW": "上傳文件或資料夾"},
    "资料类型": {"en": "Document Type", "zh_TW": "資料類型"},
    "监管要求 / 规章制度": {"en": "Regulations / Policies", "zh_TW": "監管要求 / 規章制度"},
    "企业资料": {"en": "Enterprise Materials", "zh_TW": "企業資料"},
    "其他资料": {"en": "Other Materials", "zh_TW": "其他資料"},
    "资料名称 / 备注": {"en": "Document Name / Note", "zh_TW": "資料名稱 / 備註"},
    "启用 Office 内嵌图片 OCR": {"en": "Enable OCR For Office Embedded Images", "zh_TW": "啟用 Office 內嵌圖片 OCR"},
    "入库完成后自动释放 OCR / BGE-M3 模型缓存": {"en": "Release OCR / Embedding Model Cache After Ingestion", "zh_TW": "入庫完成後自動釋放 OCR / 向量模型快取"},
    "同名文件变更时替换旧版本": {"en": "Replace Old Version When Same-Name File Changes", "zh_TW": "同名文件變更時替換舊版本"},
    "后台入库队列": {"en": "Background Ingestion Queue", "zh_TW": "後台入庫隊列"},
    "将 PPT/PPTX 栅格化后 OCR": {"en": "Rasterize PPT/PPTX Then OCR", "zh_TW": "將 PPT/PPTX 柵格化後 OCR"},
    "跳过超大 Excel 文件": {"en": "Skip Oversized Excel Files", "zh_TW": "跳過超大 Excel 文件"},
    "Excel 最大行数": {"en": "Excel Max Rows", "zh_TW": "Excel 最大行數"},
    "PDF OCR 模式": {"en": "PDF OCR Mode", "zh_TW": "PDF OCR 模式"},
    "智能 OCR（推荐，低内存）": {"en": "Smart OCR (Recommended, Low Memory)", "zh_TW": "智慧 OCR（推薦，低記憶體）"},
    "强制每页 OCR（最全但高内存）": {"en": "Force OCR On Every Page (Complete, High Memory)", "zh_TW": "強制每頁 OCR（最完整但高記憶體）"},
    "仅提取 PDF 文字（最低内存）": {"en": "Extract PDF Text Only (Lowest Memory)", "zh_TW": "僅提取 PDF 文字（最低記憶體）"},
    "缺少 LibreOffice 时自动下载安装转换工具": {"en": "Auto Install LibreOffice If Missing", "zh_TW": "缺少 LibreOffice 時自動下載安裝轉換工具"},
    "Chunk 大小": {"en": "Chunk Size", "zh_TW": "Chunk 大小"},
    "Chunk 重叠": {"en": "Chunk Overlap", "zh_TW": "Chunk 重疊"},
    "最近入库任务": {"en": "Recent Ingestion Tasks", "zh_TW": "最近入庫任務"},
    "任务控制": {"en": "Task Controls", "zh_TW": "任務控制"},
    "任务列表": {"en": "Task List", "zh_TW": "任務列表"},
    "最近任务文件明细": {"en": "Latest Task File Details", "zh_TW": "最近任務文件明細"},
    "开始导入文件": {"en": "Start Import", "zh_TW": "開始導入文件"},
    "暂停": {"en": "Pause", "zh_TW": "暫停"},
    "继续": {"en": "Resume", "zh_TW": "繼續"},
    "终止": {"en": "Stop", "zh_TW": "終止"},
    "清空任务历史": {"en": "Clear Task History", "zh_TW": "清空任務歷史"},
    "已清空入库任务历史。": {"en": "Ingestion task history cleared.", "zh_TW": "已清空入庫任務歷史。"},
    "多轮检索问答": {"en": "Multi-Turn RAG Chat", "zh_TW": "多輪檢索問答"},
    "对话与检索设置": {"en": "Chat And Retrieval Settings", "zh_TW": "對話與檢索設定"},
    "检索范围": {"en": "Search Scope", "zh_TW": "檢索範圍"},
    "全部资料": {"en": "All Materials", "zh_TW": "全部資料"},
    "召回片段数量": {"en": "Top-K Chunks", "zh_TW": "召回片段數量"},
    "回答模式": {"en": "Answer Mode", "zh_TW": "回答模式"},
    "快速": {"en": "Fast", "zh_TW": "快速"},
    "思考": {"en": "Thinking", "zh_TW": "思考"},
    "上下文轮数": {"en": "Context Turns", "zh_TW": "上下文輪數"},
    "未检索到资料时使用本地大模型普通聊天": {"en": "Use Local LLM Chat When No Evidence Is Retrieved", "zh_TW": "未檢索到資料時使用本地大模型普通聊天"},
    "追问补全成完整检索问题": {"en": "Rewrite Follow-Ups Into Complete Search Queries", "zh_TW": "追問補全成完整檢索問題"},
    "复杂问题拆解后分别检索": {"en": "Decompose Complex Questions Before Search", "zh_TW": "複雜問題拆解後分別檢索"},
    "启用向量距离阈值过滤": {"en": "Enable Vector Distance Threshold", "zh_TW": "啟用向量距離閾值過濾"},
    "最大距离": {"en": "Max Distance", "zh_TW": "最大距離"},
    "启用混合检索": {"en": "Enable Hybrid Search", "zh_TW": "啟用混合檢索"},
    "启用重排模型": {"en": "Enable Reranker", "zh_TW": "啟用重排模型"},
    "候选召回数": {"en": "Candidate Count", "zh_TW": "候選召回數"},
    "清空当前对话": {"en": "Clear Current Chat", "zh_TW": "清空當前對話"},
    "输入问题": {"en": "Enter Question", "zh_TW": "輸入問題"},
    "发送": {"en": "Send", "zh_TW": "發送"},
    "请输入问题。": {"en": "Please enter a question.", "zh_TW": "請輸入問題。"},
    "多轮合规差距分析": {"en": "Multi-Turn Compliance Gap Analysis", "zh_TW": "多輪合規差距分析"},
    "分析与检索设置": {"en": "Analysis And Retrieval Settings", "zh_TW": "分析與檢索設定"},
    "召回监管 / 规章片段数量": {"en": "Regulation Top-K Chunks", "zh_TW": "召回監管 / 規章片段數量"},
    "召回企业资料片段数量": {"en": "Enterprise Top-K Chunks", "zh_TW": "召回企業資料片段數量"},
    "分析模式": {"en": "Analysis Mode", "zh_TW": "分析模式"},
    "监管最少证据数": {"en": "Minimum Regulation Evidence", "zh_TW": "監管最少證據數"},
    "企业最少证据数": {"en": "Minimum Enterprise Evidence", "zh_TW": "企業最少證據數"},
    "按监管条款逐条对照": {"en": "Compare Clause By Clause", "zh_TW": "按監管條款逐條對照"},
    "输出资料不足清单": {"en": "Output Missing Materials List", "zh_TW": "輸出資料不足清單"},
    "清空合规分析对话": {"en": "Clear Compliance Chat", "zh_TW": "清空合規分析對話"},
    "输入合规分析问题": {"en": "Enter Compliance Analysis Question", "zh_TW": "輸入合規分析問題"},
    "请输入分析主题。": {"en": "Please enter an analysis topic.", "zh_TW": "請輸入分析主題。"},
    "模型与路径": {"en": "Models And Paths", "zh_TW": "模型與路徑"},
    "本地大模型": {"en": "Local LLM", "zh_TW": "本地大模型"},
    "初始化": {"en": "Reset", "zh_TW": "初始化"},
    "OCR 模型": {"en": "OCR Model", "zh_TW": "OCR 模型"},
    "PaddleOCR 模型": {"en": "PaddleOCR Model", "zh_TW": "PaddleOCR 模型"},
    "Server（高精度，占用更高）": {"en": "Server (Higher Accuracy, More Memory)", "zh_TW": "Server（高精度，佔用更高）"},
    "Mobile（低内存，速度更快）": {"en": "Mobile (Lower Memory, Faster)", "zh_TW": "Mobile（低記憶體，速度更快）"},
    "模型保存路径": {"en": "Model Storage Paths", "zh_TW": "模型保存路徑"},
    "默认模型根目录": {"en": "Default Model Root", "zh_TW": "預設模型根目錄"},
    "PaddleOCR 模型目录": {"en": "PaddleOCR Model Directory", "zh_TW": "PaddleOCR 模型目錄"},
    "BAAI/bge-m3 模型目录": {"en": "BAAI/bge-m3 Model Directory", "zh_TW": "BAAI/bge-m3 模型目錄"},
    "BAAI/bge-reranker-v2-m3 模型目录": {"en": "BAAI/bge-reranker-v2-m3 Model Directory", "zh_TW": "BAAI/bge-reranker-v2-m3 模型目錄"},
    "LibreOffice / soffice 路径": {"en": "LibreOffice / soffice Path", "zh_TW": "LibreOffice / soffice 路徑"},
    "保存模型路径": {"en": "Save Model Paths", "zh_TW": "保存模型路徑"},
    "恢复默认路径": {"en": "Restore Default Paths", "zh_TW": "恢復預設路徑"},
    "当前路径": {"en": "Current Paths", "zh_TW": "當前路徑"},
    "接口": {"en": "Endpoint", "zh_TW": "接口"},
    "接口类型": {"en": "API Type", "zh_TW": "接口類型"},
    "自动识别": {"en": "Auto Detect", "zh_TW": "自動識別"},
    "OpenAI 兼容": {"en": "OpenAI-Compatible", "zh_TW": "OpenAI 相容"},
    "Anthropic Messages": {"en": "Anthropic Messages", "zh_TW": "Anthropic Messages"},
    "大模型接口 Base URL": {"en": "LLM Endpoint Base URL", "zh_TW": "大模型接口 Base URL"},
    "OpenAI 兼容接口 Base URL": {"en": "OpenAI-Compatible Base URL", "zh_TW": "OpenAI 相容接口 Base URL"},
    "模型名称": {"en": "Model Name", "zh_TW": "模型名稱"},
    "默认模型名称": {"en": "Default Model Name", "zh_TW": "預設模型名稱"},
    "模式": {"en": "Modes", "zh_TW": "模式"},
    "快速模式模型名": {"en": "Fast Mode Model", "zh_TW": "快速模式模型名"},
    "思考模式模型名": {"en": "Thinking Mode Model", "zh_TW": "思考模式模型名"},
    "快速模式 extra_body JSON": {"en": "Fast Mode extra_body JSON", "zh_TW": "快速模式 extra_body JSON"},
    "思考模式 extra_body JSON": {"en": "Thinking Mode extra_body JSON", "zh_TW": "思考模式 extra_body JSON"},
    "保存配置": {"en": "Save Settings", "zh_TW": "保存配置"},
    "恢复默认值": {"en": "Restore Defaults", "zh_TW": "恢復預設值"},
    "测试模式": {"en": "Test Mode", "zh_TW": "測試模式"},
    "测试当前配置": {"en": "Test Current Settings", "zh_TW": "測試當前配置"},
    "当前生效配置": {"en": "Active Settings", "zh_TW": "當前生效配置"},
    "初始化可配置数据": {"en": "Reset Configurable Data", "zh_TW": "初始化可配置資料"},
    "我确认要初始化可配置数据和历史会话": {"en": "I confirm resetting configurable data and chat history", "zh_TW": "我確認要初始化可配置資料和歷史會話"},
    "模型状态 / 下载查询": {"en": "Model Status / Download Check", "zh_TW": "模型狀態 / 下載查詢"},
    "操作": {"en": "Actions", "zh_TW": "操作"},
    "内存管理": {"en": "Memory Management", "zh_TW": "記憶體管理"},
    "释放 OCR / BGE-M3 / Reranker 模型缓存": {"en": "Release OCR / Embedding / Reranker Cache", "zh_TW": "釋放 OCR / 向量模型 / Reranker 快取"},
    "预加载 PaddleOCR": {"en": "Preload PaddleOCR", "zh_TW": "預載 PaddleOCR"},
    "预加载 BGE-M3": {"en": "Preload Embedding Model", "zh_TW": "預載向量模型"},
    "预加载 Reranker": {"en": "Preload Reranker", "zh_TW": "預載 Reranker"},
    "Office 老格式转换": {"en": "Legacy Office Conversion", "zh_TW": "Office 舊格式轉換"},
    "测试 LibreOffice": {"en": "Test LibreOffice", "zh_TW": "測試 LibreOffice"},
    "自动安装 LibreOffice": {"en": "Auto Install LibreOffice", "zh_TW": "自動安裝 LibreOffice"},
    "测试本地大模型": {"en": "Test Local LLM", "zh_TW": "測試本地大模型"},
    "最近模型事件": {"en": "Recent Model Events", "zh_TW": "最近模型事件"},
    "文档库管理": {"en": "Document Library", "zh_TW": "文件庫管理"},
    "刷新文件摘要": {"en": "Refresh File Summary", "zh_TW": "刷新文件摘要"},
    "查看去重记录": {"en": "View Deduplication Records", "zh_TW": "查看去重記錄"},
    "向量库备份 / 导入 / 导出": {"en": "Vector Store Backup / Import / Export", "zh_TW": "向量庫備份 / 導入 / 導出"},
    "导出文档库备份": {"en": "Export Library Backup", "zh_TW": "導出文件庫備份"},
    "导入备份 ZIP": {"en": "Import Backup ZIP", "zh_TW": "導入備份 ZIP"},
    "我确认导入备份并覆盖当前文档库": {"en": "I confirm importing backup and overwriting the current library", "zh_TW": "我確認導入備份並覆蓋當前文件庫"},
    "导入并覆盖当前文档库": {"en": "Import And Overwrite Current Library", "zh_TW": "導入並覆蓋當前文件庫"},
    "清空 Qdrant 向量库": {"en": "Clear Qdrant Vector Store", "zh_TW": "清空 Qdrant 向量庫"},
    "总 chunk": {"en": "Total Chunks", "zh_TW": "總 chunk"},
    "监管/规章": {"en": "Regulations", "zh_TW": "監管/規章"},
    "新建会话": {"en": "New Chat", "zh_TW": "新建會話"},
    "删除会话": {"en": "Delete Chat", "zh_TW": "刪除會話"},
    "本轮检索资料": {"en": "Retrieved Materials", "zh_TW": "本輪檢索資料"},
    "本轮证据": {"en": "Evidence", "zh_TW": "本輪證據"},
    "监管 / 规章": {"en": "Regulations / Policies", "zh_TW": "監管 / 規章"},
    "无监管证据": {"en": "No regulation evidence", "zh_TW": "無監管證據"},
    "无企业证据": {"en": "No enterprise evidence", "zh_TW": "無企業證據"},
    "结构化合规分析表": {"en": "Structured Compliance Analysis Table", "zh_TW": "結構化合規分析表"},
    "导出本轮合规分析 Excel": {"en": "Export This Analysis To Excel", "zh_TW": "導出本輪合規分析 Excel"},
    "当前 Qdrant Collection：": {"en": "Current Qdrant Collection:", "zh_TW": "當前 Qdrant Collection："},
    "当前文档库为空。": {"en": "The document library is empty.", "zh_TW": "當前文件庫為空。"},
    "暂无去重记录。": {"en": "No deduplication records yet.", "zh_TW": "暫無去重記錄。"},
    "文件": {"en": "File", "zh_TW": "文件"},
    "文件类型": {"en": "File Type", "zh_TW": "文件類型"},
    "可处理": {"en": "Processable", "zh_TW": "可處理"},
    "不支持": {"en": "Unsupported", "zh_TW": "不支援"},
    "支持": {"en": "Supported", "zh_TW": "支援"},
    "状态": {"en": "Status", "zh_TW": "狀態"},
    "进度": {"en": "Progress", "zh_TW": "進度"},
    "成功": {"en": "Succeeded", "zh_TW": "成功"},
    "重复": {"en": "Duplicate", "zh_TW": "重複"},
    "跳过": {"en": "Skipped", "zh_TW": "跳過"},
    "失败": {"en": "Failed", "zh_TW": "失敗"},
    "当前文件": {"en": "Current File", "zh_TW": "當前文件"},
    "说明": {"en": "Message", "zh_TW": "說明"},
    "更新时间": {"en": "Updated At", "zh_TW": "更新時間"},
    "原因": {"en": "Reason", "zh_TW": "原因"},
    "已入库文件": {"en": "Ingested File", "zh_TW": "已入庫文件"},
    "chunk 数": {"en": "Chunk Count", "zh_TW": "chunk 數"},
    "来源格式": {"en": "Source Format", "zh_TW": "來源格式"},
    "资料名称": {"en": "Document Name", "zh_TW": "資料名稱"},
    "入库时间": {"en": "Ingested At", "zh_TW": "入庫時間"},
    "组件": {"en": "Component", "zh_TW": "組件"},
    "用途": {"en": "Purpose", "zh_TW": "用途"},
    "time": {"en": "Time", "zh_TW": "時間"},
    "component": {"en": "Component", "zh_TW": "組件"},
    "status": {"en": "Status", "zh_TW": "狀態"},
    "detail": {"en": "Detail", "zh_TW": "詳情"},
    "运行中": {"en": "Running", "zh_TW": "運行中"},
    "暂停中": {"en": "Pausing", "zh_TW": "暫停中"},
    "已暂停": {"en": "Paused", "zh_TW": "已暫停"},
    "终止中": {"en": "Stopping", "zh_TW": "終止中"},
    "已终止": {"en": "Stopped", "zh_TW": "已終止"},
    "已完成": {"en": "Completed", "zh_TW": "已完成"},
    "完成": {"en": "Completed", "zh_TW": "完成"},
    "未知文件": {"en": "Unknown File", "zh_TW": "未知文件"},
    "未知类型": {"en": "Unknown Type", "zh_TW": "未知類型"},
    "未知": {"en": "Unknown", "zh_TW": "未知"},
    "自动搜索系统路径": {"en": "Auto-detect system path", "zh_TW": "自動搜尋系統路徑"},
    "未检测到": {"en": "Not detected", "zh_TW": "未檢測到"},
    "语言设置": {"en": "Language", "zh_TW": "語言設定"},
    "界面语言": {"en": "UI Language", "zh_TW": "介面語言"},
    "选择界面语言": {"en": "Choose UI Language", "zh_TW": "選擇介面語言"},
    "语言设置已保存。": {"en": "Language setting saved.", "zh_TW": "語言設定已保存。"},
    "语言偏好会保存到 app_state.sqlite3，下次打开会自动生效。": {
        "en": "Language preference is saved to app_state.sqlite3 and will be applied automatically next time.",
        "zh_TW": "語言偏好會保存到 app_state.sqlite3，下次打開會自動生效。",
    },
    "当前会话": {"en": "Current Chat", "zh_TW": "當前會話"},
    "输入问题后会保留上下文；每一轮都会按当前检索设置重新召回资料。": {
        "en": "Context is preserved after you ask a question; each turn retrieves materials using the current retrieval settings.",
        "zh_TW": "輸入問題後會保留上下文；每一輪都會按當前檢索設定重新召回資料。",
    },
    "输入合规分析问题后会保留上下文；每一轮都会分别检索监管资料和企业资料。": {
        "en": "Context is preserved after you ask a compliance question; each turn retrieves regulation and enterprise materials separately.",
        "zh_TW": "輸入合規分析問題後會保留上下文；每一輪都會分別檢索監管資料和企業資料。",
    },
    "批量上传时留空会使用各自文件名": {
        "en": "Leave empty to use each file name for batch upload",
        "zh_TW": "批量上傳時留空會使用各自文件名",
    },
    "没有鉴权时可填 EMPTY": {"en": "Use EMPTY if no authentication is required", "zh_TW": "沒有鑑權時可填 EMPTY"},
    "填写 OLMX / Ollama / LM Studio 中显示的真实模型名": {
        "en": "Use the actual model name shown by OLMX / Ollama / LM Studio",
        "zh_TW": "填寫 OLMX / Ollama / LM Studio 中顯示的真實模型名",
    },
    "留空则使用默认模型名称": {"en": "Leave empty to use the default model name", "zh_TW": "留空則使用預設模型名稱"},
    "如果后端用不同模型区分快慢，可在这里填思考模型名": {
        "en": "If your backend uses a different model for thinking mode, enter it here",
        "zh_TW": "如果後端用不同模型區分快慢，可在這裡填思考模型名",
    },
    "留空则自动搜索系统路径": {"en": "Leave empty to auto-detect system path", "zh_TW": "留空則自動搜尋系統路徑"},
    "当前检索范围没有任何入库 chunk，请先上传资料。": {
        "en": "The current search scope has no ingested chunks. Please upload materials first.",
        "zh_TW": "當前檢索範圍沒有任何入庫 chunk，請先上傳資料。",
    },
    "没有检索到满足当前距离阈值的相关内容。可以在检索设置里调大“最大距离”或暂时关闭阈值过滤。": {
        "en": "No relevant content matched the current distance threshold. Increase Max Distance or temporarily disable threshold filtering in retrieval settings.",
        "zh_TW": "沒有檢索到滿足當前距離閾值的相關內容。可以在檢索設定裡調大「最大距離」或暫時關閉閾值過濾。",
    },
    "没有检索到相关内容。": {"en": "No relevant content was retrieved.", "zh_TW": "沒有檢索到相關內容。"},
    "请先上传并入库监管要求或规章制度。": {
        "en": "Please upload and ingest regulations or policy documents first.",
        "zh_TW": "請先上傳並入庫監管要求或規章制度。",
    },
    "请先上传并入库企业资料。": {
        "en": "Please upload and ingest enterprise materials first.",
        "zh_TW": "請先上傳並入庫企業資料。",
    },
    "没有检索到相关监管要求。": {"en": "No relevant regulation requirements were retrieved.", "zh_TW": "沒有檢索到相關監管要求。"},
    "没有检索到相关企业资料。": {"en": "No relevant enterprise materials were retrieved.", "zh_TW": "沒有檢索到相關企業資料。"},
    "本次没有文件成功入库。": {"en": "No files were ingested successfully this time.", "zh_TW": "本次沒有文件成功入庫。"},
    "当前向量库为空。": {"en": "The current vector store is empty.", "zh_TW": "當前向量庫為空。"},
    "暂无后台入库任务。": {"en": "No background ingestion tasks yet.", "zh_TW": "暫無後台入庫任務。"},
    "启用后，XLSX 和 XLS 的工作表最大行号合计超过阈值时会直接跳过，不解析、不切分、不写入向量库。": {
        "en": "When enabled, XLSX and XLS files are skipped when the combined worksheet max row count exceeds the threshold. They will not be parsed, chunked, or written to the vector store.",
        "zh_TW": "啟用後，XLSX 和 XLS 的工作表最大行號合計超過閾值時會直接跳過，不解析、不切分、不寫入向量庫。",
    },
    "超过该行数的 XLSX/XLS 文件会跳过入库。按所有工作表 max_row 合计计算。": {
        "en": "XLSX/XLS files above this row count are skipped. The count is the sum of max_row across all worksheets.",
        "zh_TW": "超過該行數的 XLSX/XLS 文件會跳過入庫。按所有工作表 max_row 合計計算。",
    },
    "后台入库任务已提交。可在“最近入库任务”里查看进度，页面可以继续操作。": {
        "en": "Background ingestion task submitted. You can track progress in Recent Ingestion Tasks and continue using the page.",
        "zh_TW": "後台入庫任務已提交。可在「最近入庫任務」裡查看進度，頁面可以繼續操作。",
    },
    "普通问答建议 3-5，太大会把弱相关片段带进上下文。": {
        "en": "For general Q&A, 3-5 is recommended. Larger values may add weakly related chunks to the context.",
        "zh_TW": "普通問答建議 3-5，太大會把弱相關片段帶進上下文。",
    },
    "只把最近 N 轮对话放进模型上下文；历史仍会保存在数据库。": {
        "en": "Only the latest N turns are sent to the model context. Full history is still stored in the database.",
        "zh_TW": "只把最近 N 輪對話放進模型上下文；歷史仍會保存在資料庫。",
    },
    "当向量库无匹配结果时，允许模型按通用对话方式回复；涉及本地文档的问题仍以入库检索结果为准。": {
        "en": "When the vector store has no matches, allow the model to reply as a general assistant. Questions about local documents should still rely on ingested retrieval results.",
        "zh_TW": "當向量庫無匹配結果時，允許模型按通用對話方式回覆；涉及本地文件的問題仍以入庫檢索結果為準。",
    },
    "多轮对话中把追问补全成完整问题后再检索。": {
        "en": "In multi-turn chat, complete follow-up questions before retrieval.",
        "zh_TW": "多輪對話中把追問補全成完整問題後再檢索。",
    },
    "问题包含多个事项时，会拆成子问题分别检索后合并证据。": {
        "en": "When a question contains multiple topics, split it into sub-questions, retrieve separately, then merge evidence.",
        "zh_TW": "問題包含多個事項時，會拆成子問題分別檢索後合併證據。",
    },
    "过滤距离过大的弱相关片段；如果经常召回不到，可调大右侧阈值。": {
        "en": "Filter weakly related chunks with large distances. If recall is too sparse, increase the threshold on the right.",
        "zh_TW": "過濾距離過大的弱相關片段；如果經常召回不到，可調大右側閾值。",
    },
    "同时使用向量语义检索和关键词检索，适合制度编号、部门名称、文件名等精确命中。": {
        "en": "Use both vector semantic retrieval and keyword retrieval. Useful for exact hits such as policy numbers, department names, and file names.",
        "zh_TW": "同時使用向量語義檢索和關鍵詞檢索，適合制度編號、部門名稱、文件名等精確命中。",
    },
    "先多召回，再用 BGE reranker 重排；更准但会增加内存和耗时。": {
        "en": "Retrieve more candidates first, then rerank with the BGE reranker. More accurate, but uses more memory and time.",
        "zh_TW": "先多召回，再用 BGE reranker 重排；更準但會增加記憶體和耗時。",
    },
    "用于混合检索和重排的候选数量。": {
        "en": "Candidate count used for hybrid retrieval and reranking.",
        "zh_TW": "用於混合檢索和重排的候選數量。",
    },
    "输入问题，点击发送": {"en": "Enter a question, then click Send", "zh_TW": "輸入問題，點擊發送"},
    "正在生成回答...": {"en": "Generating answer...", "zh_TW": "正在生成回答..."},
    "只把最近 N 轮合规分析对话放进模型上下文；历史仍会保存在数据库。": {
        "en": "Only the latest N compliance-analysis turns are sent to the model context. Full history is still stored in the database.",
        "zh_TW": "只把最近 N 輪合規分析對話放進模型上下文；歷史仍會保存在資料庫。",
    },
    "合规多轮分析中把追问补全成完整检索问题。": {
        "en": "In multi-turn compliance analysis, complete follow-up questions into full retrieval queries.",
        "zh_TW": "合規多輪分析中把追問補全成完整檢索問題。",
    },
    "复杂合规问题会拆成多个子问题分别检索，再合并监管和企业证据。": {
        "en": "Complex compliance questions are split into sub-questions for separate retrieval, then regulatory and enterprise evidence is merged.",
        "zh_TW": "複雜合規問題會拆成多個子問題分別檢索，再合併監管和企業證據。",
    },
    "分别过滤监管资料和企业资料里的弱相关片段。": {
        "en": "Filter weakly related chunks separately in regulatory and enterprise materials.",
        "zh_TW": "分別過濾監管資料和企業資料裡的弱相關片段。",
    },
    "同时使用向量语义检索和关键词检索，适合条款号、制度名称、部门名称。": {
        "en": "Use both vector semantic retrieval and keyword retrieval. Useful for clause numbers, policy names, and department names.",
        "zh_TW": "同時使用向量語義檢索和關鍵詞檢索，適合條款號、制度名稱、部門名稱。",
    },
    "分别对监管资料和企业资料做候选重排；更准但会增加内存和耗时。": {
        "en": "Rerank regulatory and enterprise candidates separately. More accurate, but uses more memory and time.",
        "zh_TW": "分別對監管資料和企業資料做候選重排；更準但會增加記憶體和耗時。",
    },
    "合规分析会尽量保证监管证据不少于该数量；不足时会放宽距离阈值补齐。": {
        "en": "Compliance analysis tries to keep at least this many regulatory evidence chunks. If insufficient, the distance threshold is relaxed to supplement evidence.",
        "zh_TW": "合規分析會盡量保證監管證據不少於該數量；不足時會放寬距離閾值補齊。",
    },
    "合规分析会尽量保证企业资料证据不少于该数量；不足时会放宽距离阈值补齐。": {
        "en": "Compliance analysis tries to keep at least this many enterprise evidence chunks. If insufficient, the distance threshold is relaxed to supplement evidence.",
        "zh_TW": "合規分析會盡量保證企業資料證據不少於該數量；不足時會放寬距離閾值補齊。",
    },
    "适合监管条款较清晰的场景，模型会尽量一条监管要求对应一行分析。": {
        "en": "Best when regulatory clauses are clear. The model will try to analyze one requirement per row.",
        "zh_TW": "適合監管條款較清晰的場景，模型會盡量一條監管要求對應一行分析。",
    },
    "要求模型列出还需要补充哪些企业资料，并可一起导出 Excel。": {
        "en": "Ask the model to list which enterprise materials are still needed; the list can be exported to Excel.",
        "zh_TW": "要求模型列出還需要補充哪些企業資料，並可一起導出 Excel。",
    },
    "例如：数据安全管理制度是否满足监管要求？供应商准入流程有什么合规缺口？": {
        "en": "Example: Does the data security policy meet regulatory requirements? What compliance gaps exist in the supplier onboarding process?",
        "zh_TW": "例如：資料安全管理制度是否滿足監管要求？供應商准入流程有什麼合規缺口？",
    },
    "正在检索并生成合规分析...": {"en": "Retrieving and generating compliance analysis...", "zh_TW": "正在檢索並生成合規分析..."},
    "正在测试本地大模型接口...": {"en": "Testing local LLM endpoint...", "zh_TW": "正在測試本地大模型接口..."},
    "正在加载 PaddleOCR...": {"en": "Loading PaddleOCR...", "zh_TW": "正在載入 PaddleOCR..."},
    "正在加载 BGE-M3...": {"en": "Loading embedding model...", "zh_TW": "正在載入向量模型..."},
    "正在加载 Reranker...": {"en": "Loading Reranker...", "zh_TW": "正在載入 Reranker..."},
    "正在测试 LibreOffice...": {"en": "Testing LibreOffice...", "zh_TW": "正在測試 LibreOffice..."},
    "正在自动安装 LibreOffice...": {"en": "Automatically installing LibreOffice...", "zh_TW": "正在自動安裝 LibreOffice..."},
    "生成备份失败：": {"en": "Failed to generate backup: ", "zh_TW": "生成備份失敗："},
    "导入备份失败：": {"en": "Failed to import backup: ", "zh_TW": "導入備份失敗："},
    "清空失败：": {"en": "Clear failed: ", "zh_TW": "清空失敗："},
    "未单独指定模型路径时，会在该目录下创建各模型缓存目录。": {
        "en": "When model-specific paths are not set, model cache directories are created under this root.",
        "zh_TW": "未單獨指定模型路徑時，會在該目錄下建立各模型快取目錄。",
    },
    "例如：{\"enable_thinking\": false}": {"en": "Example: {\"enable_thinking\": false}", "zh_TW": "例如：{\"enable_thinking\": false}"},
    "例如：{\"enable_thinking\": true}": {"en": "Example: {\"enable_thinking\": true}", "zh_TW": "例如：{\"enable_thinking\": true}"},
}

PHRASE_TRANSLATIONS = {
    "支持格式：": {"en": "Supported formats: ", "zh_TW": "支援格式："},
    "文件夹模式会包含子文件夹中的文件。": {
        "en": "Folder mode includes files in subfolders.",
        "zh_TW": "資料夾模式會包含子資料夾中的文件。",
    },
    "不支持的文件会在批量处理结果中列出。": {
        "en": "Unsupported files will be listed in the batch results.",
        "zh_TW": "不支援的文件會在批量處理結果中列出。",
    },
    "当前会话共 ": {"en": "Current chat has ", "zh_TW": "當前會話共 "},
    " 条消息": {"en": " messages", "zh_TW": " 條訊息"},
    "模式：": {"en": "Mode: ", "zh_TW": "模式："},
    "本轮检索问题：": {"en": "Search query: ", "zh_TW": "本輪檢索問題："},
    "拆解子问题：": {"en": "Sub-queries: ", "zh_TW": "拆解子問題："},
    "问题改写失败，已使用原问题检索：": {
        "en": "Query rewrite failed; using the original question: ",
        "zh_TW": "問題改寫失敗，已使用原問題檢索：",
    },
    "问题拆解失败，已使用启发式拆解：": {
        "en": "Query decomposition failed; using heuristic decomposition: ",
        "zh_TW": "問題拆解失敗，已使用啟發式拆解：",
    },
    "资料 ": {"en": "Material ", "zh_TW": "資料 "},
    "片段 ": {"en": "Chunk ", "zh_TW": "片段 "},
    "距离 ": {"en": "Distance ", "zh_TW": "距離 "},
    "来源 ": {"en": "Source ", "zh_TW": "來源 "},
    "重排 ": {"en": "Rerank ", "zh_TW": "重排 "},
    "覆盖补充": {"en": "coverage supplement", "zh_TW": "覆蓋補充"},
    "合并 ": {"en": "Merged ", "zh_TW": "合併 "},
    "已选择 ": {"en": "Selected ", "zh_TW": "已選擇 "},
    " 个文件，其中当前可处理 ": {"en": " files; processable now: ", "zh_TW": " 個文件，其中當前可處理 "},
    " 个，待跳过/不支持 ": {"en": "; to skip/unsupported: ", "zh_TW": " 個，待跳過/不支援 "},
    " 个。开始处理后会按 SHA256 自动跳过重复文件。": {
        "en": ". Duplicate files will be skipped automatically by SHA256.",
        "zh_TW": " 個。開始處理後會按 SHA256 自動跳過重複文件。",
    },
    "检测到老版 Office 文件，将使用 LibreOffice 转换：": {
        "en": "Legacy Office files detected; LibreOffice will convert them: ",
        "zh_TW": "檢測到舊版 Office 文件，將使用 LibreOffice 轉換：",
    },
    "当前 PaddleOCR 模型：": {"en": "Current PaddleOCR model: ", "zh_TW": "當前 PaddleOCR 模型："},
    "当前系统：": {"en": "Current system: ", "zh_TW": "當前系統："},
    "安装命令：": {"en": "Install command: ", "zh_TW": "安裝命令："},
    "正在处理 ": {"en": "Processing ", "zh_TW": "正在處理 "},
    "正在处理：": {"en": "Processing: ", "zh_TW": "正在處理："},
    "已跳过：": {"en": "Skipped: ", "zh_TW": "已跳過："},
    "已完成：": {"en": "Completed: ", "zh_TW": "已完成："},
    "已跳过重复文件：": {"en": "Skipped duplicate file: ", "zh_TW": "已跳過重複文件："},
    "已跳过不支持文件：": {"en": "Skipped unsupported file: ", "zh_TW": "已跳過不支援文件："},
    "已跳过无法转换文件：": {"en": "Skipped unconvertible file: ", "zh_TW": "已跳過無法轉換文件："},
    "没有解析到有效文字": {"en": "No valid text was extracted", "zh_TW": "沒有解析到有效文字"},
    "解析成功但没有可入库 chunk": {"en": "Parsed successfully, but no ingestible chunks were produced", "zh_TW": "解析成功但沒有可入庫 chunk"},
    "入库成功，写入 ": {"en": "Ingested successfully; wrote ", "zh_TW": "入庫成功，寫入 "},
    " 个 chunk": {"en": " chunks", "zh_TW": " 個 chunk"},
    "成功入库 ": {"en": "Successfully ingested ", "zh_TW": "成功入庫 "},
    "不支持 ": {"en": "Unsupported files: ", "zh_TW": "不支援 "},
    "重复文件 ": {"en": "Duplicate files: ", "zh_TW": "重複文件 "},
    "跳过 ": {"en": "Skipped files: ", "zh_TW": "跳過 "},
    "处理失败 ": {"en": "Failed files: ", "zh_TW": "處理失敗 "},
    " 个文件。": {"en": " files.", "zh_TW": " 個文件。"},
    "已跳过。": {"en": " skipped.", "zh_TW": "已跳過。"},
    "接口地址：": {"en": "Endpoint: ", "zh_TW": "接口地址："},
    "模型名称：": {"en": "Model name: ", "zh_TW": "模型名稱："},
    "接口可用：": {"en": "Endpoint available: ", "zh_TW": "接口可用："},
    "本地大模型可用：": {"en": "Local LLM available: ", "zh_TW": "本地大模型可用："},
    "已删除 ": {"en": "Deleted ", "zh_TW": "已刪除 "},
    " 个 chunk。": {"en": " chunks.", "zh_TW": " 個 chunk。"},
}


def get_ui_language() -> str:
    language = get_config_value("ui_language", DEFAULT_UI_LANGUAGE)
    if language not in LANGUAGE_LABEL_BY_CODE:
        language = DEFAULT_UI_LANGUAGE
    return language


def translate_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    language = get_ui_language()
    if language == "zh_CN":
        return text
    heading_match = re.match(r"^(#{1,6}\s+)(.+)$", text)
    if heading_match:
        return heading_match.group(1) + translate_text(heading_match.group(2))
    translated = TRANSLATIONS.get(text, {}).get(language)
    if translated:
        return translated
    if any("\u4e00" <= char <= "\u9fff" for char in text):
        translated_text = text
        for source, targets in sorted(PHRASE_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True):
            translated_text = translated_text.replace(source, targets.get(language, source))
        return translated_text
    return text


def localized_text(en: str, zh_cn: str, zh_tw: Optional[str] = None) -> str:
    language = get_ui_language()
    if language == "en":
        return en
    if language == "zh_TW":
        return zh_tw or zh_cn
    return zh_cn


def normalize_image_preprocess_mode(value: Any) -> str:
    """Return the stable image preprocessing mode code from saved code or old labels.
    从稳定模式代码或旧版显示文案中解析图片预处理模式代码。
    """
    raw_value = str(value or "").strip()
    if raw_value in IMAGE_PREPROCESS_MODE_OPTIONS:
        return raw_value
    for mode, labels in IMAGE_PREPROCESS_MODE_OPTIONS.items():
        if raw_value in labels.values():
            return mode
    return DEFAULT_IMAGE_PREPROCESS_MODE


def image_preprocess_mode_label(mode: Any) -> str:
    """Return the localized display label for an image preprocessing mode.
    返回图片预处理模式的本地化显示名称。
    """
    normalized_mode = normalize_image_preprocess_mode(mode)
    labels = IMAGE_PREPROCESS_MODE_OPTIONS[normalized_mode]
    language = get_ui_language()
    return labels.get(language) or labels["en"]


def llm_language_name() -> str:
    return localized_text("English", "简体中文", "繁體中文")


def llm_language_instruction() -> str:
    return localized_text(
        "Write the final answer in English. Keep quoted source material unchanged.",
        "请使用简体中文输出最终回答。引用资料原文时保持原文不变。",
        "請使用繁體中文輸出最終回答。引用資料原文時保持原文不變。",
    )


def source_label(label_key: str) -> str:
    labels = {
        "retrieval_materials": ("Retrieved Materials", "检索资料", "檢索資料"),
        "regulations": ("Regulations / Policies", "监管要求 / 规章制度", "監管要求 / 規章制度"),
        "enterprise": ("Enterprise Materials", "企业资料", "企業資料"),
        "material": ("Material", "资料", "資料"),
        "document_type": ("Document Type", "资料类型", "資料類型"),
        "source_file": ("Source File", "来源文件", "來源文件"),
        "chunk_index": ("Chunk Index", "片段编号", "片段編號"),
        "source_location": ("Source Location", "来源位置", "來源位置"),
        "content": ("Content", "内容", "內容"),
        "none": ("None", "无", "無"),
        "unknown_file": ("Unknown File", "未知文件", "未知文件"),
        "unknown_chunk": ("Unknown Chunk", "未知片段", "未知片段"),
        "unknown_type": ("Unknown Type", "未知类型", "未知類型"),
        "user": ("User", "用户", "使用者"),
        "assistant": ("Assistant", "助手", "助手"),
        "page": ("Page", "页码", "頁碼"),
        "slide": ("Slide", "幻灯片", "投影片"),
        "sheet": ("Sheet", "工作表", "工作表"),
        "row": ("Row", "行", "行"),
        "table": ("Table", "表格", "表格"),
        "image": ("Image", "图片", "圖片"),
        "title": ("Title", "标题", "標題"),
        "embedded_image_ocr": ("Embedded Image OCR", "内嵌图片 OCR", "內嵌圖片 OCR"),
        "direct_text": ("Direct Text", "直接提取文本", "直接提取文字"),
        "page_ocr_text": ("Full Page OCR Text", "整页 OCR 文本", "整頁 OCR 文字"),
        "page_prefix": ("Page", "第", "第"),
        "page_suffix": ("", "页", "頁"),
        "slide_page": ("Slide", "页幻灯片", "頁投影片"),
        "word_table": ("Word Table", "Word 表格", "Word 表格"),
        "header_row": ("Header Row", "表头行", "表頭行"),
        "column": ("Column", "列", "欄"),
        "note": ("Notes", "备注", "備註"),
        "worksheet": ("Worksheet", "工作表", "工作表"),
        "same_source_neighbor": ("Adjacent Chunk From Same Source", "同来源相邻片段", "同來源相鄰片段"),
        "missing_materials": ("Missing Materials", "资料不足清单", "資料不足清單"),
    }
    en, zh_cn, zh_tw = labels[label_key]
    return localized_text(en, zh_cn, zh_tw)


def bracketed_label(label_key: str) -> str:
    return f"[{source_label(label_key)}]"


def localize_dataframe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [translate_table_data(row) for row in rows]


def translate_options(options):
    return [translate_text(option) for option in options]


def translate_kwargs(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    translated = dict(kwargs)
    for key in ["help", "placeholder", "text", "label"]:
        if key in translated:
            translated[key] = translate_text(translated[key])
    return translated


def translate_table_data(data: Any) -> Any:
    if isinstance(data, str):
        return translate_text(data)
    if isinstance(data, list):
        return [translate_table_data(item) for item in data]
    if isinstance(data, tuple):
        return tuple(translate_table_data(item) for item in data)
    if isinstance(data, dict):
        return {
            translate_text(key): translate_table_data(value)
            for key, value in data.items()
        }
    return data


def patch_streamlit_i18n() -> None:
    if getattr(st, "_ocr_rag_i18n_patched", False):
        return

    st._ocr_rag_originals = {
        name: getattr(st, name)
        for name in [
            "title",
            "caption",
            "subheader",
            "markdown",
            "button",
            "checkbox",
            "radio",
            "selectbox",
            "text_input",
            "text_area",
            "number_input",
            "file_uploader",
            "form_submit_button",
            "download_button",
            "info",
            "warning",
            "error",
            "success",
            "metric",
            "expander",
            "tabs",
            "slider",
            "status",
            "spinner",
            "progress",
            "dataframe",
            "table",
            "json",
        ]
    }

    def wrap_label_method(name):
        original = st._ocr_rag_originals[name]

        def wrapped(label, *args, **kwargs):
            return original(translate_text(label), *args, **translate_kwargs(kwargs))

        return wrapped

    for method_name in [
        "title",
        "caption",
        "subheader",
        "markdown",
        "button",
        "checkbox",
        "text_input",
        "text_area",
        "number_input",
        "file_uploader",
        "form_submit_button",
        "info",
        "warning",
        "error",
        "success",
        "metric",
        "expander",
        "slider",
        "spinner",
    ]:
        setattr(st, method_name, wrap_label_method(method_name))

    def wrapped_status(label, *args, **kwargs):
        status_object = st._ocr_rag_originals["status"](translate_text(label), *args, **translate_kwargs(kwargs))
        original_update = status_object.update

        def translated_update(*update_args, **update_kwargs):
            if "label" in update_kwargs:
                update_kwargs["label"] = translate_text(update_kwargs["label"])
            elif update_args:
                update_args = (translate_text(update_args[0]), *update_args[1:])
            return original_update(*update_args, **update_kwargs)

        status_object.update = translated_update
        return status_object

    def wrapped_progress(value, *args, **kwargs):
        kwargs = translate_kwargs(kwargs)
        progress_object = st._ocr_rag_originals["progress"](value, *args, **kwargs)
        original_progress = progress_object.progress

        def translated_progress(progress_value, *progress_args, **progress_kwargs):
            progress_kwargs = translate_kwargs(progress_kwargs)
            return original_progress(progress_value, *progress_args, **progress_kwargs)

        progress_object.progress = translated_progress
        return progress_object

    def wrapped_download_button(label, *args, **kwargs):
        return st._ocr_rag_originals["download_button"](translate_text(label), *args, **translate_kwargs(kwargs))

    def wrapped_radio(label, options, *args, **kwargs):
        kwargs = translate_kwargs(kwargs)
        existing_format_func = kwargs.get("format_func")
        if existing_format_func is None:
            kwargs["format_func"] = lambda option: translate_text(option)
        else:
            kwargs["format_func"] = lambda option: translate_text(existing_format_func(option))
        return st._ocr_rag_originals["radio"](translate_text(label), options, *args, **kwargs)

    def wrapped_selectbox(label, options, *args, **kwargs):
        kwargs = translate_kwargs(kwargs)
        existing_format_func = kwargs.get("format_func")
        if existing_format_func is None:
            kwargs["format_func"] = lambda option: translate_text(option)
        else:
            kwargs["format_func"] = lambda option: translate_text(existing_format_func(option))
        return st._ocr_rag_originals["selectbox"](translate_text(label), options, *args, **kwargs)

    def wrapped_tabs(tabs, *args, **kwargs):
        return st._ocr_rag_originals["tabs"](translate_options(tabs), *args, **kwargs)

    def wrapped_dataframe(data=None, *args, **kwargs):
        return st._ocr_rag_originals["dataframe"](translate_table_data(data), *args, **kwargs)

    def wrapped_table(data=None, *args, **kwargs):
        return st._ocr_rag_originals["table"](translate_table_data(data), *args, **kwargs)

    def wrapped_json(body, *args, **kwargs):
        return st._ocr_rag_originals["json"](translate_table_data(body), *args, **kwargs)

    st.download_button = wrapped_download_button
    st.status = wrapped_status
    st.progress = wrapped_progress
    st.radio = wrapped_radio
    st.selectbox = wrapped_selectbox
    st.tabs = wrapped_tabs
    st.dataframe = wrapped_dataframe
    st.table = wrapped_table
    st.json = wrapped_json
    st._ocr_rag_i18n_patched = True


if not get_config_value("ui_language", ""):
    set_config_value("ui_language", DEFAULT_UI_LANGUAGE)

patch_streamlit_i18n()


def normalize_local_path(path_value: str, default: str = "") -> str:
    path_value = (path_value or "").strip()
    if not path_value:
        path_value = default
    if not path_value:
        return ""
    return os.path.abspath(os.path.expanduser(path_value))


def normalize_qdrant_url(url_value: str) -> str:
    """Normalize the HTTP Qdrant endpoint without forcing a trailing slash.
    规范化 HTTP Qdrant 连接地址，不强制保留末尾斜杠。
    """
    url_value = (url_value or "").strip() or DEFAULT_QDRANT_URL
    return url_value.rstrip("/")


def get_qdrant_config() -> Dict[str, str]:
    """Return the active Qdrant connection settings from SQLite.
    从 SQLite 读取当前生效的 Qdrant 连接配置。
    """
    mode = get_config_value("qdrant_mode", DEFAULT_QDRANT_MODE)
    if mode not in {"local", "http"}:
        mode = DEFAULT_QDRANT_MODE
    return {
        "mode": mode,
        "local_path": normalize_local_path(
            get_config_value("qdrant_local_path", DEFAULT_QDRANT_LOCAL_PATH),
            DEFAULT_QDRANT_LOCAL_PATH,
        ),
        "url": normalize_qdrant_url(get_config_value("qdrant_url", DEFAULT_QDRANT_URL)),
        "api_key": get_config_value("qdrant_api_key", DEFAULT_QDRANT_API_KEY).strip(),
    }


def get_qdrant_connection_key(config: Optional[Dict[str, str]] = None) -> str:
    """Build a cache key for the Qdrant singleton.
    为 Qdrant 单例构造缓存键。
    """
    config = config or get_qdrant_config()
    if config["mode"] == "http":
        return f"http::{config['url']}::{bool(config.get('api_key'))}"
    return f"local::{os.path.abspath(config['local_path'])}"


def save_qdrant_config(mode: str, local_path: str, url: str, api_key: str) -> None:
    """Persist Qdrant connection settings and reset the cached client.
    保存 Qdrant 连接配置并重置已缓存客户端。
    """
    mode = mode if mode in {"local", "http"} else DEFAULT_QDRANT_MODE
    local_path = normalize_local_path(local_path, DEFAULT_QDRANT_LOCAL_PATH)
    url = normalize_qdrant_url(url)
    api_key = (api_key or "").strip()
    set_config_value("qdrant_mode", mode)
    set_config_value("qdrant_local_path", local_path)
    set_config_value("qdrant_url", url)
    set_config_value("qdrant_api_key", api_key)
    close_qdrant_singleton()
    try:
        load_qdrant_client.clear()
    except Exception:
        pass


def delete_all_config_values() -> None:
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM app_config")
        app_db.commit()


def get_ingested_file(file_sha256: str) -> Optional[Dict[str, Any]]:
    with APP_DB_LOCK:
        row = app_db.execute(
            """
            SELECT sha256, file_name, doc_category, doc_label, chunk_count, created_at, updated_at
            FROM ingested_files
            WHERE sha256 = ?
            """,
            (file_sha256,),
        ).fetchone()
    return dict(row) if row else None


def list_ingested_files_by_name(file_name: str) -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT sha256, file_name, doc_category, doc_label, chunk_count, created_at, updated_at
            FROM ingested_files
            WHERE file_name = ?
            ORDER BY updated_at DESC
            """,
            (file_name,),
        ).fetchall()
    return [dict(row) for row in rows]


def delete_ingested_file_records_by_name(file_name: str) -> int:
    with APP_DB_LOCK:
        cursor = app_db.execute("DELETE FROM ingested_files WHERE file_name = ?", (file_name,))
        app_db.commit()
    return cursor.rowcount


def record_ingested_file(
    file_sha256: str,
    file_name: str,
    doc_category: str,
    doc_label: str,
    chunk_count: int,
) -> None:
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO ingested_files
                (sha256, file_name, doc_category, doc_label, chunk_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sha256) DO UPDATE SET
                file_name = excluded.file_name,
                doc_category = excluded.doc_category,
                doc_label = excluded.doc_label,
                chunk_count = excluded.chunk_count,
                updated_at = excluded.updated_at
            """,
            (
                file_sha256,
                file_name,
                doc_category,
                doc_label,
                chunk_count,
                now,
                now,
            ),
        )
        app_db.commit()


def list_ingested_files() -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT sha256, file_name, doc_category, doc_label, chunk_count, created_at, updated_at
            FROM ingested_files
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def replace_ingested_file_records(records: List[Dict[str, Any]]) -> int:
    """Replace SHA256 deduplication records with backup contents.
    使用备份内容替换 SHA256 去重记录。
    """
    normalized_records = []
    now = current_timestamp()
    for record in records:
        sha256 = str(record.get("sha256") or record.get("file_sha256") or "").strip()
        if not sha256:
            continue
        normalized_records.append(
            (
                sha256,
                str(record.get("file_name") or ""),
                str(record.get("doc_category") or "general"),
                str(record.get("doc_label") or record.get("file_name") or ""),
                int(record.get("chunk_count") or 0),
                float(record.get("created_at") or now),
                float(record.get("updated_at") or now),
            )
        )

    with APP_DB_LOCK:
        app_db.execute("DELETE FROM ingested_files")
        app_db.executemany(
            """
            INSERT INTO ingested_files
                (sha256, file_name, doc_category, doc_label, chunk_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(sha256) DO UPDATE SET
                file_name = excluded.file_name,
                doc_category = excluded.doc_category,
                doc_label = excluded.doc_label,
                chunk_count = excluded.chunk_count,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at
            """,
            normalized_records,
        )
        app_db.commit()
    return len(normalized_records)


def get_ingested_file_chunk_counts() -> Dict[str, int]:
    """Return chunk counts from SQLite ingestion records.
    从 SQLite 入库记录读取 chunk 统计，避免每次页面重跑都扫描向量库。
    """
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT doc_category, SUM(chunk_count) AS chunk_total
            FROM ingested_files
            GROUP BY doc_category
            """
        ).fetchall()
    counts = {"total": 0, "regulation": 0, "enterprise": 0, "general": 0}
    for row in rows:
        category = row["doc_category"] or "general"
        chunk_total = int(row["chunk_total"] or 0)
        counts[category] = counts.get(category, 0) + chunk_total
        counts["total"] += chunk_total
    return counts


def default_session_title(session_type: str) -> str:
    label = localized_text("RAG Chat", "检索问答", "檢索問答") if session_type == "rag" else localized_text(
        "Compliance",
        "合规分析",
        "合規分析",
    )
    prefix = localized_text("New", "新建", "新建")
    return f"{prefix} {label} {time.strftime('%m-%d %H:%M')}"


def create_chat_session(session_type: str, title: Optional[str] = None) -> str:
    session_id = uuid.uuid4().hex
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO chat_sessions (id, session_type, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, session_type, title or default_session_title(session_type), now, now),
        )
        app_db.commit()
    return session_id


def list_chat_sessions(session_type: str) -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT id, session_type, title, created_at, updated_at
            FROM chat_sessions
            WHERE session_type = ?
            ORDER BY updated_at DESC
            """,
            (session_type,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_active_session_id(session_type: str) -> str:
    state_key = f"active_{session_type}_session_id"
    sessions = list_chat_sessions(session_type)
    session_ids = {session["id"] for session in sessions}
    active_id = st.session_state.get(state_key)
    if active_id in session_ids:
        return active_id

    if sessions:
        active_id = sessions[0]["id"]
    else:
        active_id = create_chat_session(session_type)

    st.session_state[state_key] = active_id
    return active_id


def set_active_session_id(session_type: str, session_id: str) -> None:
    st.session_state[f"active_{session_type}_session_id"] = session_id


def delete_chat_session(session_id: str) -> None:
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        app_db.commit()


def clear_chat_session(session_id: str) -> None:
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        app_db.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        app_db.commit()


def get_chat_messages(session_id: str) -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT role, content, payload, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()
    messages = []
    for row in rows:
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
        except json.JSONDecodeError:
            payload = {}
        messages.append(
            {
                "role": row["role"],
                "content": row["content"],
                **payload,
            }
        )
    return messages


def append_chat_message(
    session_id: str,
    role: str,
    content: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO chat_messages (id, session_id, role, content, payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                session_id,
                role,
                content,
                json.dumps(payload or {}, ensure_ascii=False, default=str),
                now,
            ),
        )
        app_db.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        app_db.commit()


def maybe_update_session_title(session_id: str, first_user_message: str) -> None:
    with APP_DB_LOCK:
        row = app_db.execute(
            "SELECT title FROM chat_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return

    title = str(row["title"])
    if not title.startswith("新建"):
        return

    new_title = first_user_message.strip().replace("\n", " ")[:32]
    if not new_title:
        return

    with APP_DB_LOCK:
        app_db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (new_title, current_timestamp(), session_id),
        )
        app_db.commit()


def delete_all_chat_sessions() -> None:
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM chat_messages")
        app_db.execute("DELETE FROM chat_sessions")
        app_db.commit()


def delete_all_ingested_file_records() -> None:
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM ingested_files")
        app_db.commit()


def create_ingest_task(total_files: int) -> str:
    task_id = uuid.uuid4().hex
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO ingest_tasks (
                id, status, total_files, processed_files, success_count, duplicate_count,
                skipped_count, failed_count, current_file, message, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                "running",
                total_files,
                0,
                0,
                0,
                0,
                0,
                "",
                localized_text("Preparing files", "准备处理文件", "準備處理文件"),
                now,
                now,
            ),
        )
        app_db.commit()
    return task_id


def update_ingest_task(task_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return
    kwargs["updated_at"] = current_timestamp()
    assignments = ", ".join(f"{key} = ?" for key in kwargs)
    values = list(kwargs.values())
    values.append(task_id)
    with APP_DB_LOCK:
        app_db.execute(
            f"UPDATE ingest_tasks SET {assignments} WHERE id = ?",
            values,
        )
        app_db.commit()


def record_ingest_task_item(
    task_id: str,
    file_name: str,
    status: str,
    message: str,
    chunk_count: int = 0,
    file_sha256: str = "",
) -> None:
    now = current_timestamp()
    with APP_DB_LOCK:
        app_db.execute(
            """
            INSERT INTO ingest_task_items (
                id, task_id, file_name, status, message, chunk_count, sha256, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                task_id,
                file_name,
                status,
                message,
                int(chunk_count or 0),
                file_sha256 or "",
                now,
                now,
            ),
        )
        app_db.commit()


def list_ingest_tasks(limit: int = 10) -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT id, status, total_files, processed_files, success_count, duplicate_count,
                   skipped_count, failed_count, current_file, message, created_at, updated_at
            FROM ingest_tasks
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


ACTIVE_INGEST_STATUSES = {"running", "pause_requested", "paused", "cancel_requested"}


def get_live_ingest_future(task_id: str) -> Any:
    """Return the in-process background future, if this app run owns it.
    返回当前进程持有的后台 future；应用重启后旧任务不会再有 future。
    """
    try:
        runtime = load_ingest_executor()
        return runtime.get("futures", {}).get(task_id)
    except Exception:
        return None


def is_ingest_task_actually_active(task: Dict[str, Any]) -> bool:
    """Check whether a persisted task is still backed by a live worker.
    判断数据库里的任务是否真的还有后台线程在执行。
    """
    if not task or task.get("status") not in ACTIVE_INGEST_STATUSES:
        return False
    future = get_live_ingest_future(task.get("id", ""))
    return bool(future is not None and not future.done())


def mark_stale_ingest_tasks_stopped(tasks: List[Dict[str, Any]]) -> bool:
    """Convert stale active-looking tasks into stopped tasks after restart.
    应用重启后，把数据库中残留的“看似运行中”任务归档为已终止。
    """
    changed = False
    for task in tasks:
        if task.get("status") in ACTIVE_INGEST_STATUSES and not is_ingest_task_actually_active(task):
            update_ingest_task(
                task["id"],
                status="cancelled",
                message=localized_text(
                    "Task stopped after app restart or worker exit.",
                    "任务已停止（应用重启或后台 worker 已退出）。",
                    "任務已停止（應用重啟或後台 worker 已退出）。",
                ),
            )
            changed = True
    return changed


def has_active_ingest_task(limit: int = 5) -> bool:
    tasks = list_ingest_tasks(limit=limit)
    return any(task.get("status") in ACTIVE_INGEST_STATUSES for task in tasks)


def has_live_ingest_task_in_list(tasks: List[Dict[str, Any]]) -> bool:
    """Return True only for tasks with a live background worker.
    只有存在真实后台 worker 时才返回 True。
    """
    return any(is_ingest_task_actually_active(task) for task in tasks)


def delete_all_ingest_tasks() -> None:
    with APP_DB_LOCK:
        app_db.execute("DELETE FROM ingest_task_items")
        app_db.execute("DELETE FROM ingest_tasks")
        app_db.commit()


def get_ingest_task(task_id: str) -> Optional[Dict[str, Any]]:
    with APP_DB_LOCK:
        row = app_db.execute(
            """
            SELECT id, status, total_files, processed_files, success_count, duplicate_count,
                   skipped_count, failed_count, current_file, message, created_at, updated_at
            FROM ingest_tasks
            WHERE id = ?
            """,
            (task_id,),
        ).fetchone()
    return dict(row) if row else None


def request_pause_ingest_task(task_id: str) -> None:
    update_ingest_task(
        task_id,
        status="pause_requested",
        message=localized_text(
            "Pause requested. The task will pause after the current file reaches a safe point.",
            "已请求暂停，当前文件处理到安全点后暂停",
            "已請求暫停，當前文件處理到安全點後暫停",
        ),
    )


def resume_ingest_task(task_id: str) -> None:
    update_ingest_task(task_id, status="running", message=localized_text("Background ingestion resumed", "已继续后台入库任务", "已繼續後台入庫任務"))


def request_cancel_ingest_task(task_id: str) -> None:
    update_ingest_task(
        task_id,
        status="cancel_requested",
        message=localized_text(
            "Stop requested. The task will stop after the current step finishes.",
            "已请求终止，当前步骤结束后停止",
            "已請求終止，當前步驟結束後停止",
        ),
    )


class IngestTaskCancelled(RuntimeError):
    pass


def wait_if_task_paused_or_cancelled(task_id: str) -> None:
    while True:
        task = get_ingest_task(task_id)
        status = task.get("status") if task else ""
        if status == "cancel_requested":
            message = localized_text("Ingestion task stopped", "入库任务已终止", "入庫任務已終止")
            update_ingest_task(task_id, status="cancelled", message=message)
            raise IngestTaskCancelled(message)
        if status in {"pause_requested", "paused"}:
            if status == "pause_requested":
                update_ingest_task(task_id, status="paused", message=localized_text("Ingestion task paused", "入库任务已暂停", "入庫任務已暫停"))
            time.sleep(1)
            continue
        return


def list_ingest_task_items(task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    with APP_DB_LOCK:
        rows = app_db.execute(
            """
            SELECT file_name, status, message, chunk_count, sha256, created_at, updated_at
            FROM ingest_task_items
            WHERE task_id = ?
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (task_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def reset_app_state_database() -> None:
    delete_all_config_values()
    delete_all_chat_sessions()
    set_config_value("ui_language", DEFAULT_UI_LANGUAGE)
    save_llm_config(
        DEFAULT_LLM_BASE_URL,
        DEFAULT_LLM_API_KEY,
        DEFAULT_LLM_MODEL,
        api_type=DEFAULT_LLM_API_TYPE,
        fast_model=DEFAULT_LLM_MODEL,
        thinking_model=DEFAULT_LLM_MODEL,
        fast_extra_body=DEFAULT_LLM_EXTRA_BODY,
        thinking_extra_body=DEFAULT_LLM_EXTRA_BODY,
    )
    set_config_value("rag_context_turns", DEFAULT_CONTEXT_TURNS)
    set_config_value("compliance_context_turns", DEFAULT_CONTEXT_TURNS)
    set_config_value("rag_top_k", DEFAULT_RAG_TOP_K)
    set_bool_config("rag_query_rewrite", True)
    set_bool_config("rag_query_decompose", DEFAULT_QUERY_DECOMPOSE)
    set_bool_config("rag_use_distance_threshold", True)
    set_config_value("rag_max_distance", DEFAULT_VECTOR_MAX_DISTANCE)
    set_bool_config("rag_use_hybrid", DEFAULT_USE_HYBRID_SEARCH)
    set_bool_config("rag_use_reranker", DEFAULT_USE_RERANKER)
    set_config_value("rag_fetch_k", DEFAULT_RETRIEVAL_FETCH_K)
    set_config_value("compliance_regulation_top_k", DEFAULT_COMPLIANCE_REGULATION_TOP_K)
    set_config_value("compliance_enterprise_top_k", DEFAULT_COMPLIANCE_ENTERPRISE_TOP_K)
    set_bool_config("compliance_query_rewrite", True)
    set_bool_config("compliance_query_decompose", DEFAULT_QUERY_DECOMPOSE)
    set_config_value("compliance_min_regulation_evidence", DEFAULT_COMPLIANCE_MIN_REGULATION_EVIDENCE)
    set_config_value("compliance_min_enterprise_evidence", DEFAULT_COMPLIANCE_MIN_ENTERPRISE_EVIDENCE)
    set_bool_config("compliance_clause_by_clause", False)
    set_bool_config("compliance_include_missing_list", True)
    set_bool_config("compliance_use_distance_threshold", True)
    set_config_value("compliance_max_distance", DEFAULT_VECTOR_MAX_DISTANCE)
    set_bool_config("compliance_use_hybrid", DEFAULT_USE_HYBRID_SEARCH)
    set_bool_config("compliance_use_reranker", DEFAULT_USE_RERANKER)
    set_config_value("compliance_fetch_k", DEFAULT_RETRIEVAL_FETCH_K)
    set_config_value("model_cache_root", DEFAULT_MODEL_CACHE_ROOT)
    set_config_value("embedding_model_name", EMBEDDING_MODEL_NAME)
    set_config_value("reranker_model_name", RERANKER_MODEL_NAME)
    set_config_value("paddleocr_cache_dir", "")
    set_config_value("bge_cache_dir", "")
    set_config_value("bge_base_cache_dir", "")
    set_config_value("reranker_cache_dir", "")
    set_config_value("reranker_base_cache_dir", "")
    set_config_value("soffice_binary_path", DEFAULT_SOFFICE_BINARY_PATH)
    set_config_value("model_download_source", DEFAULT_MODEL_DOWNLOAD_SOURCE)
    set_config_value("custom_hf_endpoint", DEFAULT_CUSTOM_HF_ENDPOINT)
    set_config_value("paddleocr_model_source", DEFAULT_PADDLEOCR_MODEL_SOURCE)
    set_config_value("libreoffice_install_source", DEFAULT_LIBREOFFICE_INSTALL_SOURCE)
    set_config_value("custom_libreoffice_install_command", DEFAULT_CUSTOM_LIBREOFFICE_INSTALL_COMMAND)
    set_config_value("qdrant_mode", DEFAULT_QDRANT_MODE)
    set_config_value("qdrant_local_path", DEFAULT_QDRANT_LOCAL_PATH)
    set_config_value("qdrant_url", DEFAULT_QDRANT_URL)
    set_config_value("qdrant_api_key", DEFAULT_QDRANT_API_KEY)
    set_bool_config("replace_changed_same_name", True)
    set_bool_config("background_ingest", DEFAULT_BACKGROUND_INGEST)
    set_bool_config("ppt_visual_ocr", True)
    set_bool_config("skip_large_excel", False)
    set_config_value("excel_row_limit", 100000)
    set_config_value("image_preprocess_mode", DEFAULT_IMAGE_PREPROCESS_MODE)
    set_config_value("image_preprocess_mode_label", DEFAULT_IMAGE_PREPROCESS_MODE_LABEL)
    set_bool_config("image_preprocess_custom", False)
    set_config_value("image_preprocess_max_side", IMAGE_PREPROCESS_PRESETS["balanced"]["max_side"])
    set_config_value("image_preprocess_max_pixels", IMAGE_PREPROCESS_PRESETS["balanced"]["max_pixels"])
    set_config_value("image_preprocess_jpeg_quality", IMAGE_PREPROCESS_PRESETS["balanced"]["jpeg_quality"])
    set_bool_config("image_preprocess_grayscale", IMAGE_PREPROCESS_PRESETS["balanced"]["grayscale"])
    apply_model_cache_environment()
    for key in [
        "llm_config",
        "active_rag_session_id",
        "active_compliance_session_id",
        "upload_mode_label",
        "upload_doc_category_label",
        "upload_ocr_enhance",
        "upload_ppt_visual_ocr",
        "auto_unload_models_after_ingest",
        "replace_changed_same_name_input",
        "background_ingest_input",
        "skip_large_excel_input",
        "excel_row_limit_input",
        "image_preprocess_mode",
        "image_preprocess_mode_label",
        "image_preprocess_custom",
        "image_preprocess_max_side",
        "image_preprocess_max_pixels",
        "image_preprocess_jpeg_quality",
        "image_preprocess_grayscale",
        "upload_pdf_ocr_mode_label",
        "paddleocr_model_label",
        "auto_install_libreoffice",
        "upload_chunk_size",
        "upload_overlap",
        "rag_session_select",
        "compliance_session_select",
        "rag_search_scope_label",
        "search_top_k",
        "chat_llm_mode_label",
        "rag_allow_general_fallback_input",
        "rag_query_rewrite_input",
        "rag_query_decompose_input",
        "rag_use_distance_threshold_input",
        "rag_max_distance_input",
        "rag_use_hybrid_input",
        "rag_use_reranker_input",
        "rag_fetch_k_input",
        "rag_context_turns_input",
        "regulation_top_k",
        "enterprise_top_k",
        "compliance_query_rewrite_input",
        "compliance_query_decompose_input",
        "compliance_min_regulation_evidence_input",
        "compliance_min_enterprise_evidence_input",
        "compliance_clause_by_clause_input",
        "compliance_include_missing_list_input",
        "compliance_use_distance_threshold_input",
        "compliance_max_distance_input",
        "compliance_use_hybrid_input",
        "compliance_use_reranker_input",
        "compliance_fetch_k_input",
        "compliance_llm_mode_label",
        "compliance_context_turns_input",
        "config_test_llm_mode_label",
        "llm_api_type_label",
        "config_paddleocr_model_label",
        "embedding_model_name_select",
        "reranker_model_name_select",
        "model_cache_root_input",
        "paddleocr_cache_dir_input",
        "bge_cache_dir_input",
        "bge_base_cache_dir_input",
        "reranker_cache_dir_input",
        "reranker_base_cache_dir_input",
        "soffice_binary_path_input",
        "model_download_source_select",
        "custom_hf_endpoint_input",
        "paddleocr_model_source_select",
        "libreoffice_install_source_select",
        "custom_libreoffice_install_command_input",
        "qdrant_mode_label",
        "qdrant_local_path_input",
        "qdrant_url_input",
        "qdrant_api_key_input",
        "ui_language_selector",
        "model_status_test_llm_mode_label",
    ]:
        st.session_state.pop(key, None)


def get_model_cache_root() -> str:
    return normalize_local_path(get_config_value("model_cache_root", DEFAULT_MODEL_CACHE_ROOT), DEFAULT_MODEL_CACHE_ROOT)


def get_embedding_model_name() -> str:
    model_name = get_config_value("embedding_model_name", EMBEDDING_MODEL_NAME)
    return model_name if model_name in EMBEDDING_MODEL_OPTIONS else EMBEDDING_MODEL_NAME


def get_reranker_model_name() -> str:
    model_name = get_config_value("reranker_model_name", RERANKER_MODEL_NAME)
    return model_name if model_name in RERANKER_MODEL_OPTIONS else RERANKER_MODEL_NAME


def get_embedding_model_label(model_name: Optional[str] = None) -> str:
    model_name = model_name or get_embedding_model_name()
    option = EMBEDDING_MODEL_OPTIONS.get(model_name, EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME])
    return localized_text(option["label"]["en"], option["label"]["zh_CN"], option["label"]["zh_TW"])


def get_reranker_model_label(model_name: Optional[str] = None) -> str:
    model_name = model_name or get_reranker_model_name()
    option = RERANKER_MODEL_OPTIONS.get(model_name, RERANKER_MODEL_OPTIONS[RERANKER_MODEL_NAME])
    return localized_text(option["label"]["en"], option["label"]["zh_CN"], option["label"]["zh_TW"])


def get_embedding_vector_size(model_name: Optional[str] = None) -> int:
    model_name = model_name or get_embedding_model_name()
    option = EMBEDDING_MODEL_OPTIONS.get(model_name, EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME])
    return int(option["vector_size"])


def get_collection_name_for_embedding_model(model_name: Optional[str] = None) -> str:
    model_name = model_name or get_embedding_model_name()
    option = EMBEDDING_MODEL_OPTIONS.get(model_name, EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME])
    return str(option["collection_name"])


def get_active_collection_name() -> str:
    return get_collection_name_for_embedding_model(get_embedding_model_name())


def get_default_cache_dir_for_embedding_model(model_name: str) -> str:
    option = EMBEDDING_MODEL_OPTIONS.get(model_name, EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME])
    return os.path.join(get_model_cache_root(), option["default_cache_dir_name"])


def get_default_cache_dir_for_reranker_model(model_name: str) -> str:
    option = RERANKER_MODEL_OPTIONS.get(model_name, RERANKER_MODEL_OPTIONS[RERANKER_MODEL_NAME])
    return os.path.join(get_model_cache_root(), option["default_cache_dir_name"])


def get_embedding_cache_dir_for_model(model_name: Optional[str] = None) -> str:
    model_name = model_name or get_embedding_model_name()
    option = EMBEDDING_MODEL_OPTIONS.get(model_name, EMBEDDING_MODEL_OPTIONS[EMBEDDING_MODEL_NAME])
    default_path = get_default_cache_dir_for_embedding_model(model_name)
    return normalize_local_path(get_config_value(option["cache_key"], ""), default_path)


def get_reranker_cache_dir_for_model(model_name: Optional[str] = None) -> str:
    model_name = model_name or get_reranker_model_name()
    option = RERANKER_MODEL_OPTIONS.get(model_name, RERANKER_MODEL_OPTIONS[RERANKER_MODEL_NAME])
    default_path = get_default_cache_dir_for_reranker_model(model_name)
    return normalize_local_path(get_config_value(option["cache_key"], ""), default_path)


def get_paddleocr_cache_dir() -> str:
    default_path = os.path.join(get_model_cache_root(), "paddlex")
    return normalize_local_path(get_config_value("paddleocr_cache_dir", ""), default_path)


def get_bge_cache_dir() -> str:
    return get_embedding_cache_dir_for_model(get_embedding_model_name())


def get_reranker_cache_dir() -> str:
    return get_reranker_cache_dir_for_model(get_reranker_model_name())


def get_configured_soffice_path() -> str:
    return normalize_local_path(get_config_value("soffice_binary_path", DEFAULT_SOFFICE_BINARY_PATH), "")


def get_model_download_source() -> str:
    source = get_config_value("model_download_source", DEFAULT_MODEL_DOWNLOAD_SOURCE)
    return source if source in MODEL_DOWNLOAD_SOURCE_OPTIONS else DEFAULT_MODEL_DOWNLOAD_SOURCE


def get_paddleocr_model_source() -> str:
    source = get_config_value("paddleocr_model_source", DEFAULT_PADDLEOCR_MODEL_SOURCE)
    return source if source in PADDLEOCR_MODEL_SOURCE_OPTIONS else DEFAULT_PADDLEOCR_MODEL_SOURCE


def get_libreoffice_install_source() -> str:
    source = get_config_value("libreoffice_install_source", DEFAULT_LIBREOFFICE_INSTALL_SOURCE)
    return source if source in LIBREOFFICE_INSTALL_SOURCE_OPTIONS else DEFAULT_LIBREOFFICE_INSTALL_SOURCE


def get_custom_hf_endpoint() -> str:
    return get_config_value("custom_hf_endpoint", DEFAULT_CUSTOM_HF_ENDPOINT).strip().rstrip("/")


def get_custom_libreoffice_install_command() -> str:
    return get_config_value(
        "custom_libreoffice_install_command",
        DEFAULT_CUSTOM_LIBREOFFICE_INSTALL_COMMAND,
    ).strip()


def get_active_hf_endpoint() -> str:
    source = get_model_download_source()
    if source == "hf_mirror":
        return HF_MIRROR_ENDPOINT
    if source == "custom":
        return get_custom_hf_endpoint()
    return ""


def get_model_download_source_label(source: Optional[str] = None) -> str:
    source = source or get_model_download_source()
    option = MODEL_DOWNLOAD_SOURCE_OPTIONS.get(source, MODEL_DOWNLOAD_SOURCE_OPTIONS[DEFAULT_MODEL_DOWNLOAD_SOURCE])
    return localized_text(option["en"], option["zh_CN"], option["zh_TW"])


def get_paddleocr_model_source_label(source: Optional[str] = None) -> str:
    source = source or get_paddleocr_model_source()
    option = PADDLEOCR_MODEL_SOURCE_OPTIONS.get(source, PADDLEOCR_MODEL_SOURCE_OPTIONS[DEFAULT_PADDLEOCR_MODEL_SOURCE])
    return localized_text(option["en"], option["zh_CN"], option["zh_TW"])


def get_libreoffice_install_source_label(source: Optional[str] = None) -> str:
    source = source or get_libreoffice_install_source()
    option = LIBREOFFICE_INSTALL_SOURCE_OPTIONS.get(source, LIBREOFFICE_INSTALL_SOURCE_OPTIONS[DEFAULT_LIBREOFFICE_INSTALL_SOURCE])
    return localized_text(option["en"], option["zh_CN"], option["zh_TW"])


def get_model_download_config() -> Dict[str, str]:
    source = get_model_download_source()
    endpoint = get_active_hf_endpoint()
    paddle_source = get_paddleocr_model_source()
    libreoffice_source = get_libreoffice_install_source()
    return {
        "source": source,
        "source_label": get_model_download_source_label(source),
        "hf_endpoint": endpoint or "https://huggingface.co",
        "custom_hf_endpoint": get_custom_hf_endpoint(),
        "paddleocr_source": paddle_source,
        "paddleocr_source_label": get_paddleocr_model_source_label(paddle_source),
        "paddleocr_hf_endpoint": endpoint or "https://huggingface.co",
        "libreoffice_install_source": libreoffice_source,
        "libreoffice_install_source_label": get_libreoffice_install_source_label(libreoffice_source),
        "custom_libreoffice_install_command": get_custom_libreoffice_install_command(),
    }


def apply_model_download_environment() -> None:
    """Apply configured model download source settings for future downloads.
    应用模型下载源配置，影响后续模型下载。
    """
    endpoint = get_active_hf_endpoint()
    if endpoint:
        os.environ["HF_ENDPOINT"] = endpoint
    else:
        os.environ.pop("HF_ENDPOINT", None)
    paddle_source = get_paddleocr_model_source()
    os.environ["PADDLE_PDX_MODEL_SOURCE"] = paddle_source
    os.environ["PADDLE_PDX_HUGGING_FACE_ENDPOINT"] = endpoint or "https://huggingface.co"
    refresh_paddlex_download_runtime()


def refresh_paddlex_download_runtime() -> None:
    """Refresh PaddleX module-level download flags after settings change.
    设置变更后刷新 PaddleX 模块级下载参数。
    """
    paddle_source = get_paddleocr_model_source()
    hf_endpoint = get_active_hf_endpoint() or "https://huggingface.co"

    flags_module = sys.modules.get("paddlex.utils.flags")
    if flags_module:
        flags_module.MODEL_SOURCE = paddle_source
        flags_module.HUGGING_FACE_ENDPOINT = hf_endpoint

    official_models_module = sys.modules.get("paddlex.inference.utils.official_models")
    if official_models_module:
        official_models_module.MODEL_SOURCE = paddle_source
        official_models_module.HUGGING_FACE_ENDPOINT = hf_endpoint
        hoster_cls = getattr(official_models_module, "_HuggingFaceModelHoster", None)
        if hoster_cls:
            hoster_cls.healthcheck_url = hf_endpoint
        manager = getattr(official_models_module, "official_models", None)
        if manager:
            manager._hosters = None


def save_model_download_config(
    source: str,
    custom_endpoint: str,
    paddleocr_source: Optional[str] = None,
    libreoffice_source: Optional[str] = None,
    custom_libreoffice_command: Optional[str] = None,
) -> None:
    source = source if source in MODEL_DOWNLOAD_SOURCE_OPTIONS else DEFAULT_MODEL_DOWNLOAD_SOURCE
    paddleocr_source = (
        paddleocr_source
        if paddleocr_source in PADDLEOCR_MODEL_SOURCE_OPTIONS
        else get_paddleocr_model_source()
    )
    libreoffice_source = (
        libreoffice_source
        if libreoffice_source in LIBREOFFICE_INSTALL_SOURCE_OPTIONS
        else get_libreoffice_install_source()
    )
    custom_endpoint = (custom_endpoint or "").strip().rstrip("/")
    custom_libreoffice_command = (custom_libreoffice_command or "").strip()
    if source == "custom":
        parsed_endpoint = urlparse(custom_endpoint)
        if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
            raise ValueError(
                localized_text(
                    "Custom Hugging Face endpoint must start with http:// or https://.",
                    "自定义 Hugging Face Endpoint 必须以 http:// 或 https:// 开头。",
                    "自訂 Hugging Face Endpoint 必須以 http:// 或 https:// 開頭。",
                )
            )
    if libreoffice_source == "custom_command" and not custom_libreoffice_command:
        raise ValueError(
            localized_text(
                "Custom LibreOffice install command cannot be empty.",
                "自定义 LibreOffice 安装命令不能为空。",
                "自訂 LibreOffice 安裝命令不能為空。",
            )
        )
    set_config_value("model_download_source", source)
    set_config_value("custom_hf_endpoint", custom_endpoint)
    set_config_value("paddleocr_model_source", paddleocr_source)
    set_config_value("libreoffice_install_source", libreoffice_source)
    set_config_value("custom_libreoffice_install_command", custom_libreoffice_command)
    apply_model_download_environment()
    try:
        load_ocr_model.clear()
        load_embedding_model.clear()
        load_reranker_model.clear()
        close_qdrant_singleton()
        load_qdrant_client.clear()
    except Exception:
        pass
    release_memory_after_file()


def ensure_model_cache_dirs() -> None:
    model_paths = [
        get_model_cache_root(),
        get_paddleocr_cache_dir(),
        *(get_embedding_cache_dir_for_model(model_name) for model_name in EMBEDDING_MODEL_OPTIONS),
        *(get_reranker_cache_dir_for_model(model_name) for model_name in RERANKER_MODEL_OPTIONS),
    ]
    for path in model_paths:
        if path:
            os.makedirs(path, exist_ok=True)


def refresh_paddlex_cache_runtime() -> None:
    cache_dir = get_paddleocr_cache_dir()
    cache_module = sys.modules.get("paddlex.utils.cache")
    if cache_module:
        cache_module.CACHE_DIR = cache_dir
        cache_module.FUNC_CACHE_DIR = os.path.join(cache_dir, "func_ret")
        cache_module.FILE_LOCK_DIR = os.path.join(cache_dir, "locks")
        cache_module.TEMP_DIR = os.path.join(cache_dir, "temp")
        for path in [
            cache_module.CACHE_DIR,
            cache_module.FUNC_CACHE_DIR,
            cache_module.FILE_LOCK_DIR,
            cache_module.TEMP_DIR,
        ]:
            os.makedirs(path, exist_ok=True)

    official_models_module = sys.modules.get("paddlex.inference.utils.official_models")
    if official_models_module:
        official_models_module.CACHE_DIR = cache_dir
        manager = getattr(official_models_module, "official_models", None)
        if manager:
            manager._save_dir = Path(cache_dir) / "official_models"
            manager._hosters = None


def apply_model_cache_environment() -> None:
    ensure_model_cache_dirs()
    apply_model_download_environment()
    os.environ["PADDLE_PDX_CACHE_HOME"] = get_paddleocr_cache_dir()
    os.environ["HF_HOME"] = os.path.join(get_model_cache_root(), "huggingface")
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = get_model_cache_root()
    refresh_paddlex_cache_runtime()


def save_model_cache_config(
    model_cache_root: str,
    paddleocr_cache_dir: str,
    bge_cache_dir: str,
    bge_base_cache_dir: str,
    reranker_cache_dir: str,
    reranker_base_cache_dir: str,
    soffice_binary_path: str,
    embedding_model_name: Optional[str] = None,
    reranker_model_name: Optional[str] = None,
) -> None:
    model_cache_root = normalize_local_path(model_cache_root, DEFAULT_MODEL_CACHE_ROOT)
    paddleocr_cache_dir = normalize_local_path(paddleocr_cache_dir, "") if paddleocr_cache_dir.strip() else ""
    bge_cache_dir = normalize_local_path(bge_cache_dir, "") if bge_cache_dir.strip() else ""
    bge_base_cache_dir = normalize_local_path(bge_base_cache_dir, "") if bge_base_cache_dir.strip() else ""
    reranker_cache_dir = normalize_local_path(reranker_cache_dir, "") if reranker_cache_dir.strip() else ""
    reranker_base_cache_dir = normalize_local_path(reranker_base_cache_dir, "") if reranker_base_cache_dir.strip() else ""
    soffice_binary_path = normalize_local_path(soffice_binary_path, "")
    embedding_model_name = embedding_model_name or get_embedding_model_name()
    reranker_model_name = reranker_model_name or get_reranker_model_name()
    if embedding_model_name not in EMBEDDING_MODEL_OPTIONS:
        raise ValueError(localized_text("Unknown embedding model.", "未知文本向量化模型。", "未知文字向量化模型。"))
    if reranker_model_name not in RERANKER_MODEL_OPTIONS:
        raise ValueError(localized_text("Unknown reranker model.", "未知重排模型。", "未知重排模型。"))

    set_config_value("model_cache_root", model_cache_root)
    set_config_value("embedding_model_name", embedding_model_name)
    set_config_value("reranker_model_name", reranker_model_name)
    set_config_value("paddleocr_cache_dir", paddleocr_cache_dir)
    set_config_value("bge_cache_dir", bge_cache_dir)
    set_config_value("bge_base_cache_dir", bge_base_cache_dir)
    set_config_value("reranker_cache_dir", reranker_cache_dir)
    set_config_value("reranker_base_cache_dir", reranker_base_cache_dir)
    set_config_value("soffice_binary_path", soffice_binary_path)
    apply_model_cache_environment()
    try:
        load_ocr_model.clear()
        load_embedding_model.clear()
        load_reranker_model.clear()
        close_qdrant_singleton()
        load_qdrant_client.clear()
    except Exception:
        pass
    release_memory_after_file()


apply_model_cache_environment()


def get_paddleocr_model_label() -> str:
    label = get_config_value("paddleocr_model_label", DEFAULT_PADDLEOCR_MODEL_LABEL)
    if label not in PADDLEOCR_MODEL_OPTIONS:
        return DEFAULT_PADDLEOCR_MODEL_LABEL
    return label


def get_paddleocr_model_config() -> Dict[str, str]:
    return PADDLEOCR_MODEL_OPTIONS[get_paddleocr_model_label()]


def save_paddleocr_model_label(label: str) -> None:
    if label not in PADDLEOCR_MODEL_OPTIONS:
        raise ValueError(localized_text("Unknown PaddleOCR model setting", "未知 PaddleOCR 模型配置", "未知 PaddleOCR 模型配置"))
    old_label = get_paddleocr_model_label()
    set_config_value("paddleocr_model_label", label)
    if old_label != label:
        try:
            load_ocr_model.clear()
        except Exception:
            pass
        release_memory_after_file()


def is_embedding_model_cached(model_name: Optional[str] = None) -> bool:
    model_name = model_name or get_embedding_model_name()
    cache_dir = get_embedding_cache_dir_for_model(model_name)
    try:
        if os.path.exists(os.path.join(cache_dir, "modules.json")):
            return True
        from huggingface_hub import try_to_load_from_cache

        cached_path = try_to_load_from_cache(
            model_name,
            "modules.json",
            cache_dir=cache_dir,
        )
        return isinstance(cached_path, str) and os.path.exists(cached_path)
    except Exception:
        return False


def is_bge_model_cached() -> bool:
    return is_embedding_model_cached(get_embedding_model_name())


def is_reranker_model_cached(model_name: Optional[str] = None) -> bool:
    model_name = model_name or get_reranker_model_name()
    cache_dir = get_reranker_cache_dir_for_model(model_name)
    try:
        if os.path.exists(os.path.join(cache_dir, "config.json")):
            return True
        from huggingface_hub import try_to_load_from_cache

        cached_path = try_to_load_from_cache(
            model_name,
            "config.json",
            cache_dir=cache_dir,
        )
        return isinstance(cached_path, str) and os.path.exists(cached_path)
    except Exception:
        return False


# =========================
# 加载模型和数据库
# =========================
MODEL_RESOURCE_CACHE: Dict[Tuple[Any, ...], Any] = {}
MODEL_RESOURCE_LOCK = threading.RLock()


def get_cached_model_resource(cache_key: Tuple[Any, ...], factory: Callable[[], Any]) -> Any:
    """Load heavy ML resources once without depending on Streamlit session context.
    不依赖 Streamlit 会话上下文，只加载一次重型模型资源。
    """
    with MODEL_RESOURCE_LOCK:
        if cache_key not in MODEL_RESOURCE_CACHE:
            MODEL_RESOURCE_CACHE[cache_key] = factory()
        return MODEL_RESOURCE_CACHE[cache_key]


def clear_cached_model_resources(prefix: Optional[str] = None) -> None:
    """Release cached ML resources by prefix.
    按前缀释放已缓存的模型资源。
    """
    with MODEL_RESOURCE_LOCK:
        keys = [
            key for key in MODEL_RESOURCE_CACHE
            if prefix is None or (key and key[0] == prefix)
        ]
        for key in keys:
            MODEL_RESOURCE_CACHE.pop(key, None)
    gc.collect()


def load_ocr_model():
    """
    PaddleOCR 中文模型。
    use_textline_orientation=True 用于处理文字方向。
    lang='ch' 适合中文，也能识别一部分英文。
    """
    cache_key = (
        "ocr",
        get_paddleocr_model_label(),
        get_paddleocr_cache_dir(),
        get_paddleocr_model_source(),
        get_active_hf_endpoint(),
    )

    def factory() -> Any:
        apply_model_cache_environment()
        from paddleocr import PaddleOCR

        ocr_config = get_paddleocr_model_config()
        return PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            text_detection_model_name=ocr_config["det"],
            text_recognition_model_name=ocr_config["rec"],
            text_recognition_batch_size=4,
            text_det_limit_side_len=960,
            lang="ch",
        )

    return get_cached_model_resource(cache_key, factory)


def clear_ocr_model_cache() -> None:
    clear_cached_model_resources("ocr")


load_ocr_model.clear = clear_ocr_model_cache


def load_embedding_model():
    """
    BGE embedding model selected in settings.
    设置页选择的 BGE embedding 模型。
    """
    return load_embedding_model_for(get_embedding_model_name())


def load_embedding_model_for(model_name: str):
    """
    Load a specific sentence-transformers embedding model.
    加载指定的 sentence-transformers 向量模型。
    """
    model_name = model_name if model_name in EMBEDDING_MODEL_OPTIONS else EMBEDDING_MODEL_NAME
    cache_dir = get_embedding_cache_dir_for_model(model_name)
    cache_key = ("bge", model_name, cache_dir, get_active_hf_endpoint())

    def factory() -> Any:
        apply_model_download_environment()
        from sentence_transformers import SentenceTransformer

        model_source = (
            cache_dir
            if os.path.exists(os.path.join(cache_dir, "modules.json"))
            else model_name
        )
        return SentenceTransformer(
            model_source,
            cache_folder=cache_dir,
            local_files_only=is_embedding_model_cached(model_name),
        )

    return get_cached_model_resource(cache_key, factory)


def embed_texts_with_model(texts: List[str], model_name: str) -> List[List[float]]:
    """
    Generate normalized vectors with a specific configured embedding model.
    使用指定的配置模型生成归一化向量。
    """
    embedding_model = load_embedding_model_for(model_name)
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


def clear_embedding_model_cache() -> None:
    clear_cached_model_resources("bge")


load_embedding_model.clear = clear_embedding_model_cache


def load_reranker_model():
    model_name = get_reranker_model_name()
    cache_dir = get_reranker_cache_dir_for_model(model_name)
    cache_key = ("reranker", model_name, cache_dir, get_active_hf_endpoint())

    def factory() -> Any:
        apply_model_download_environment()
        from sentence_transformers import CrossEncoder

        model_source = (
            cache_dir
            if os.path.exists(os.path.join(cache_dir, "config.json"))
            else model_name
        )
        return CrossEncoder(
            model_source,
            max_length=512,
            cache_folder=cache_dir,
            local_files_only=is_reranker_model_cached(model_name),
        )

    return get_cached_model_resource(cache_key, factory)


def clear_reranker_model_cache() -> None:
    clear_cached_model_resources("reranker")


load_reranker_model.clear = clear_reranker_model_cache


def import_qdrant_models():
    from qdrant_client import models

    return models


def build_qdrant_filter(where: Optional[Dict[str, Any]] = None):
    if not where:
        return None
    models = import_qdrant_models()
    return models.Filter(
        must=[
            models.FieldCondition(
                key=key,
                match=models.MatchValue(value=value),
            )
            for key, value in where.items()
        ]
    )


def get_qdrant_collection_vector_size(client: Any, collection_name: str) -> Optional[int]:
    try:
        info = client.get_collection(collection_name)
        vectors_config = info.config.params.vectors
        if hasattr(vectors_config, "size"):
            return int(vectors_config.size)
        if isinstance(vectors_config, dict):
            first_vector = next(iter(vectors_config.values()), None)
            if hasattr(first_vector, "size"):
                return int(first_vector.size)
    except Exception:
        return None
    return None


def ensure_qdrant_collection(
    client,
    collection_name: Optional[str] = None,
    vector_size: Optional[int] = None,
) -> None:
    models = import_qdrant_models()
    collection_name = collection_name or get_active_collection_name()
    vector_size = int(vector_size or get_embedding_vector_size())
    collection_exists = False
    try:
        collection_exists = client.collection_exists(collection_name)
    except Exception:
        try:
            client.get_collection(collection_name)
            collection_exists = True
        except Exception:
            collection_exists = False

    if not collection_exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        return

    existing_size = get_qdrant_collection_vector_size(client, collection_name)
    if existing_size is not None and existing_size != vector_size:
        raise RuntimeError(
            localized_text(
                f"The active Qdrant collection '{collection_name}' uses {existing_size} dimensions, but the selected embedding model expects {vector_size}. Switch to the matching embedding model, import a matching backup, or convert the vector store in Settings > Vector Store.",
                f"当前 Qdrant Collection「{collection_name}」是 {existing_size} 维，但所选文本向量化模型需要 {vector_size} 维。请切换为匹配的模型、导入匹配的备份，或在“配置中心 > 向量库连接”中执行向量库模型转换。",
                f"目前 Qdrant Collection「{collection_name}」是 {existing_size} 維，但所選文字向量化模型需要 {vector_size} 維。請切換為匹配的模型、導入匹配的備份，或在「配置中心 > 向量庫連線」中執行向量庫模型轉換。",
            )
        )


class LockedQdrantClient:
    def __init__(self, client: Any, lock: threading.RLock):
        self._client = client
        self._lock = lock

    def __getattr__(self, name: str) -> Any:
        value = getattr(self._client, name)
        if not callable(value):
            return value

        def locked_call(*args, **kwargs):
            with self._lock:
                return value(*args, **kwargs)

        return locked_call

    def close(self) -> None:
        with self._lock:
            if hasattr(self._client, "close"):
                self._client.close()


def get_qdrant_singleton_state() -> Dict[str, Any]:
    state = getattr(builtins, "_ocr_rag_qdrant_state", None)
    if not state:
        state = {
            "client": None,
            "proxy": None,
            "key": "",
            "lock": threading.RLock(),
        }
        setattr(builtins, "_ocr_rag_qdrant_state", state)
    return state


def close_qdrant_singleton() -> None:
    state = get_qdrant_singleton_state()
    with state["lock"]:
        client = state.get("client")
        if client is not None and hasattr(client, "close"):
            try:
                client.close()
            except Exception:
                pass
        state["client"] = None
        state["proxy"] = None
        state["key"] = ""


def close_stale_qdrant_clients(qdrant_path: str) -> int:
    closed_count = 0
    for obj in gc.get_objects():
        try:
            if type(obj).__name__ != "QdrantClient":
                continue
            local_client = getattr(obj, "_client", None)
            location = getattr(local_client, "location", "")
            if location and os.path.abspath(str(location)) != qdrant_path:
                continue
            if hasattr(obj, "close"):
                obj.close()
                closed_count += 1
        except Exception:
            continue
    if closed_count:
        gc.collect()
    return closed_count


def recreate_qdrant_collection() -> None:
    collection_name = get_active_collection_name()
    try:
        vector_client.delete_collection(collection_name)
    except Exception:
        pass
    ensure_qdrant_collection(vector_client)


@st.cache_resource
def load_qdrant_client():
    from qdrant_client import QdrantClient

    state = get_qdrant_singleton_state()
    qdrant_config = get_qdrant_config()
    qdrant_key = get_qdrant_connection_key(qdrant_config)
    qdrant_path = os.path.abspath(qdrant_config["local_path"])
    with state["lock"]:
        if state.get("client") is not None and state.get("key") == qdrant_key:
            ensure_qdrant_collection(state["proxy"])
            return state["proxy"]

        if state.get("client") is not None:
            try:
                if hasattr(state["client"], "close"):
                    state["client"].close()
            except Exception:
                pass
            state["client"] = None
            state["proxy"] = None
            state["key"] = ""

        try:
            if qdrant_config["mode"] == "http":
                raw_client = QdrantClient(
                    url=qdrant_config["url"],
                    api_key=qdrant_config["api_key"] or None,
                    timeout=60,
                )
            else:
                os.makedirs(qdrant_path, exist_ok=True)
                raw_client = QdrantClient(path=qdrant_path)
        except RuntimeError as e:
            if qdrant_config["mode"] == "local" and "already accessed by another instance of Qdrant client" in str(e):
                if close_stale_qdrant_clients(qdrant_path):
                    try:
                        raw_client = QdrantClient(path=qdrant_path)
                    except RuntimeError as retry_error:
                        raise RuntimeError(
                            localized_text(
                                "The local Qdrant store qdrant_db is already used by another client. This usually means another Streamlit service is open or an old process has not exited. Press Ctrl+C in the terminal that started Streamlit, make sure only one service remains, then restart. If you need multi-process concurrent access, use Qdrant server.",
                                "Qdrant 本地库 qdrant_db 正在被另一个客户端占用。通常是已经打开了另一个 Streamlit 服务或旧进程还没退出。请先在启动 Streamlit 的终端按 Ctrl+C 停掉旧服务，确认只保留一个服务后再启动；如果确实需要多进程并发访问，请改用 Qdrant server。",
                                "Qdrant 本地庫 qdrant_db 正在被另一個客戶端佔用。通常是已經打開了另一個 Streamlit 服務或舊進程還沒退出。請先在啟動 Streamlit 的終端按 Ctrl+C 停掉舊服務，確認只保留一個服務後再啟動；如果確實需要多進程並發訪問，請改用 Qdrant server。",
                            )
                        ) from retry_error
                else:
                    raise RuntimeError(
                        localized_text(
                            "The local Qdrant store qdrant_db is already used by another client. This usually means another Streamlit service is open or an old process has not exited. Press Ctrl+C in the terminal that started Streamlit, make sure only one service remains, then restart. If you need multi-process concurrent access, use Qdrant server.",
                            "Qdrant 本地库 qdrant_db 正在被另一个客户端占用。通常是已经打开了另一个 Streamlit 服务或旧进程还没退出。请先在启动 Streamlit 的终端按 Ctrl+C 停掉旧服务，确认只保留一个服务后再启动；如果确实需要多进程并发访问，请改用 Qdrant server。",
                            "Qdrant 本地庫 qdrant_db 正在被另一個客戶端佔用。通常是已經打開了另一個 Streamlit 服務或舊進程還沒退出。請先在啟動 Streamlit 的終端按 Ctrl+C 停掉舊服務，確認只保留一個服務後再啟動；如果確實需要多進程並發訪問，請改用 Qdrant server。",
                        )
                    ) from e
            raise

        proxy = LockedQdrantClient(raw_client, state["lock"])
        state["client"] = raw_client
        state["proxy"] = proxy
        state["key"] = qdrant_key
        ensure_qdrant_collection(proxy)
        return proxy


class LazyQdrantClient:
    """Proxy Qdrant access so opening the app does not immediately load the vector store.
    延迟代理 Qdrant 访问，避免打开页面时立即加载向量库。
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(load_qdrant_client(), name)

    def close(self) -> None:
        close_qdrant_singleton()


@st.cache_resource
def load_llm_client(base_url: str, api_key: str):
    return OpenAI(base_url=base_url, api_key=api_key, timeout=60)


vector_client = LazyQdrantClient()


@st.cache_resource
def load_ingest_executor():
    return {
        "executor": ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr-rag-ingest"),
        "futures": {},
    }


def qdrant_scroll_points(
    where: Optional[Dict[str, Any]] = None,
    limit: int = 10000,
    with_payload: bool = True,
    with_vectors: bool = False,
    client: Optional[Any] = None,
    collection_name: Optional[str] = None,
) -> List[Any]:
    points = []
    for point in iter_qdrant_points(
        where=where,
        batch_size=min(limit, 256) if limit and limit > 0 else 256,
        with_payload=with_payload,
        with_vectors=with_vectors,
        client=client,
        collection_name=collection_name,
    ):
        points.append(point)
        if limit and limit > 0 and len(points) >= limit:
            break
    return points[:limit] if limit and limit > 0 else points


def iter_qdrant_points(
    where: Optional[Dict[str, Any]] = None,
    batch_size: int = 256,
    with_payload: bool = True,
    with_vectors: bool = False,
    client: Optional[Any] = None,
    collection_name: Optional[str] = None,
) -> Iterator[Any]:
    """Stream points from Qdrant without keeping the whole collection in memory.
    以迭代方式读取 Qdrant point，避免一次性把整个集合放入内存。
    """
    next_page = None
    scroll_filter = build_qdrant_filter(where)
    active_client = client or vector_client
    collection_name = collection_name or get_active_collection_name()
    batch_size = max(1, min(int(batch_size or 256), 1024))
    while True:
        batch, next_page = active_client.scroll(
            collection_name=collection_name,
            scroll_filter=scroll_filter,
            limit=batch_size,
            offset=next_page,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )
        for point in batch:
            yield point
        if next_page is None:
            break


def migrate_local_qdrant_to_http(
    target_url: str,
    target_api_key: str = "",
    source_path: str = DEFAULT_QDRANT_LOCAL_PATH,
    recreate_target: bool = False,
    batch_size: int = 128,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    """Copy existing local Qdrant points to a remote/Docker Qdrant service.
    将本地 Qdrant 已有 point 复制到远程或 Docker Qdrant 服务，不重新解析文档或重新生成向量。
    """
    from qdrant_client import QdrantClient

    models = import_qdrant_models()
    source_path = normalize_local_path(source_path, DEFAULT_QDRANT_LOCAL_PATH)
    if not os.path.isdir(source_path):
        raise FileNotFoundError(
            localized_text(
                f"Local Qdrant path does not exist: {source_path}",
                f"本地 Qdrant 路径不存在：{source_path}",
                f"本地 Qdrant 路徑不存在：{source_path}",
            )
        )

    target_url = normalize_qdrant_url(target_url)
    collection_name = get_active_collection_name()
    vector_size = get_embedding_vector_size()
    source_client = None
    target_client = None
    copied_count = 0
    try:
        active_config = get_qdrant_config()
        if active_config["mode"] == "local" and os.path.abspath(active_config["local_path"]) == os.path.abspath(source_path):
            source_client = load_qdrant_client()
        else:
            source_client = QdrantClient(path=source_path)

        if not source_client.collection_exists(collection_name):
            return 0

        target_client = QdrantClient(url=target_url, api_key=(target_api_key or None), timeout=60)
        if recreate_target:
            try:
                target_client.delete_collection(collection_name)
            except Exception:
                pass

        if not target_client.collection_exists(collection_name):
            target_client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )

        next_page = None
        while True:
            batch, next_page = source_client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=next_page,
                with_payload=True,
                with_vectors=True,
            )
            points = []
            for point in batch:
                vector = getattr(point, "vector", None)
                if vector is None:
                    continue
                points.append(
                    models.PointStruct(
                        id=point.id,
                        vector=vector,
                        payload=getattr(point, "payload", None) or {},
                    )
                )
            if points:
                target_client.upsert(collection_name=collection_name, points=points)
                copied_count += len(points)
                if progress_callback:
                    progress_callback(copied_count)
            del points, batch
            if next_page is None:
                break
        return copied_count
    finally:
        if target_client is not None:
            try:
                target_client.close()
            except Exception:
                pass
        if source_client is not None and source_client is not vector_client and source_client is not get_qdrant_singleton_state().get("proxy"):
            try:
                source_client.close()
            except Exception:
                pass
        release_memory_after_file()


def infer_embedding_model_from_vector_size(vector_size: Optional[int]) -> str:
    if vector_size is None:
        return ""
    for model_name, option in EMBEDDING_MODEL_OPTIONS.items():
        if int(option["vector_size"]) == int(vector_size):
            return model_name
    return ""


def ensure_collection_for_embedding_model(client: Any, model_name: str, recreate: bool = False) -> str:
    models = import_qdrant_models()
    collection_name = get_collection_name_for_embedding_model(model_name)
    vector_size = get_embedding_vector_size(model_name)
    if recreate:
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass
    try:
        exists = client.collection_exists(collection_name)
    except Exception:
        exists = False
    if not exists:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
    else:
        existing_size = get_qdrant_collection_vector_size(client, collection_name)
        if existing_size is not None and existing_size != vector_size:
            raise RuntimeError(
                localized_text(
                    f"Target collection '{collection_name}' uses {existing_size} dimensions, but {model_name} requires {vector_size}.",
                    f"目标 Collection「{collection_name}」是 {existing_size} 维，但 {model_name} 需要 {vector_size} 维。",
                    f"目標 Collection「{collection_name}」是 {existing_size} 維，但 {model_name} 需要 {vector_size} 維。",
                )
            )
    return collection_name


def convert_vector_collection_embeddings(
    source_model_name: str,
    target_model_name: str,
    recreate_target: bool = False,
    batch_size: int = 16,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    """Re-embed stored chunk text from one embedding collection into another.
    从源向量集合读取已保存的 chunk 文本，并用目标 embedding 模型重新向量化写入目标集合。
    """
    if source_model_name not in EMBEDDING_MODEL_OPTIONS:
        raise ValueError(localized_text("Unknown source embedding model.", "未知来源文本向量化模型。", "未知來源文字向量化模型。"))
    if target_model_name not in EMBEDDING_MODEL_OPTIONS:
        raise ValueError(localized_text("Unknown target embedding model.", "未知目标文本向量化模型。", "未知目標文字向量化模型。"))
    if source_model_name == target_model_name:
        raise ValueError(localized_text("Source and target models are the same.", "来源模型和目标模型相同。", "來源模型和目標模型相同。"))

    active_client = load_qdrant_client()
    source_collection = get_collection_name_for_embedding_model(source_model_name)
    target_collection = ensure_collection_for_embedding_model(active_client, target_model_name, recreate=recreate_target)
    try:
        source_exists = active_client.collection_exists(source_collection)
    except Exception:
        source_exists = False
    if not source_exists:
        raise FileNotFoundError(
            localized_text(
                f"Source collection was not found: {source_collection}",
                f"未找到来源 Collection：{source_collection}",
                f"未找到來源 Collection：{source_collection}",
            )
        )

    source_size = get_qdrant_collection_vector_size(active_client, source_collection)
    expected_source_size = get_embedding_vector_size(source_model_name)
    if source_size is not None and source_size != expected_source_size:
        raise RuntimeError(
            localized_text(
                f"Source collection '{source_collection}' uses {source_size} dimensions, but {source_model_name} should use {expected_source_size}.",
                f"来源 Collection「{source_collection}」是 {source_size} 维，但 {source_model_name} 应为 {expected_source_size} 维。",
                f"來源 Collection「{source_collection}」是 {source_size} 維，但 {source_model_name} 應為 {expected_source_size} 維。",
            )
        )

    models = import_qdrant_models()
    pending_docs: List[str] = []
    pending_points: List[Any] = []
    converted_count = 0
    batch_size = max(1, min(int(batch_size or 16), 64))

    def flush_pending() -> None:
        nonlocal converted_count
        if not pending_docs:
            return
        vectors = embed_texts_with_model(pending_docs, target_model_name)
        target_points = []
        now = current_timestamp()
        for point, vector in zip(pending_points, vectors):
            payload = dict(getattr(point, "payload", None) or {})
            payload["embedding_model"] = target_model_name
            payload["embedding_vector_size"] = get_embedding_vector_size(target_model_name)
            payload["converted_from_embedding_model"] = source_model_name
            payload["converted_at"] = now
            target_points.append(
                models.PointStruct(
                    id=point.id,
                    vector=vector,
                    payload=payload,
                )
            )
        if target_points:
            active_client.upsert(collection_name=target_collection, points=target_points)
            converted_count += len(target_points)
            if progress_callback:
                progress_callback(converted_count)
        pending_docs.clear()
        pending_points.clear()
        del vectors, target_points
        gc.collect()

    for point in iter_qdrant_points(
        batch_size=batch_size,
        with_payload=True,
        with_vectors=False,
        client=active_client,
        collection_name=source_collection,
    ):
        payload = dict(getattr(point, "payload", None) or {})
        document_text = str(payload.get("document") or "").strip()
        if not document_text:
            continue
        pending_docs.append(document_text)
        pending_points.append(point)
        if len(pending_docs) >= batch_size:
            flush_pending()
    flush_pending()
    return converted_count


def inspect_vector_library_backup(uploaded_backup) -> Dict[str, Any]:
    """Read backup manifest without extracting the full vector store.
    只读取备份 manifest，不解压完整向量库。
    """
    try:
        if not isinstance(uploaded_backup, (str, os.PathLike)):
            uploaded_backup.seek(0)
    except Exception:
        pass
    with zipfile.ZipFile(uploaded_backup) as archive:
        try:
            with archive.open(BACKUP_MANIFEST_NAME) as manifest_file:
                manifest = json.loads(manifest_file.read().decode("utf-8"))
        except KeyError:
            manifest = {}
    try:
        if not isinstance(uploaded_backup, (str, os.PathLike)):
            uploaded_backup.seek(0)
    except Exception:
        pass
    vector_size = manifest.get("vector_size")
    try:
        vector_size = int(vector_size) if vector_size is not None else None
    except Exception:
        vector_size = None
    model_name = str(manifest.get("embedding_model") or "").strip() or infer_embedding_model_from_vector_size(vector_size)
    return {
        "format": manifest.get("format", ""),
        "version": manifest.get("version", ""),
        "collection_name": manifest.get("active_collection_name") or manifest.get("collection_name", ""),
        "vector_size": vector_size,
        "embedding_model": model_name,
        "matches_active_model": bool(model_name and model_name == get_embedding_model_name()),
        "matches_active_dimension": bool(vector_size is not None and vector_size == get_embedding_vector_size()),
    }


def point_payload(point: Any) -> Dict[str, Any]:
    return dict(getattr(point, "payload", None) or {})


def payload_to_result(point: Any, score: Optional[float] = None, retrieval_source: str = "vector") -> Dict[str, Any]:
    payload = point_payload(point)
    content = payload.pop("document", "")
    distance = None
    if score is not None:
        distance = max(0.0, 1.0 - float(score))
    return {
        "id": str(getattr(point, "id", uuid.uuid4())),
        "content": content,
        "metadata": payload,
        "distance": distance,
        "retrieval_source": retrieval_source,
    }


def delete_vector_chunks_by_where(where: Dict[str, Any]) -> int:
    points = qdrant_scroll_points(where=where, limit=100000)
    point_ids = [point.id for point in points]
    if point_ids:
        models = import_qdrant_models()
        vector_client.delete(
            collection_name=get_active_collection_name(),
            points_selector=models.PointIdsList(points=point_ids),
        )
    return len(point_ids)


def delete_vector_chunks_by_file_name(file_name: str) -> int:
    if not file_name:
        return 0
    return delete_vector_chunks_by_where({"file_name": file_name})


def count_chunks_by_file_sha256(file_sha256: str) -> int:
    if not file_sha256:
        return 0
    try:
        result = vector_client.count(
            collection_name=get_active_collection_name(),
            count_filter=build_qdrant_filter({"file_sha256": file_sha256}),
            exact=True,
        )
        return int(result.count)
    except Exception:
        return 0


def get_duplicate_ingested_file(file_sha256: str) -> Optional[Dict[str, Any]]:
    existing_file = get_ingested_file(file_sha256)
    if existing_file and count_chunks_by_file_sha256(file_sha256) > 0:
        return existing_file
    return None


def replace_existing_same_name_if_needed(file_name: str, file_sha256: str, enabled: bool) -> Tuple[int, int]:
    if not enabled:
        return 0, 0
    same_name_records = [
        record for record in list_ingested_files_by_name(file_name) if record.get("sha256") != file_sha256
    ]
    existing_points = qdrant_scroll_points(where={"file_name": file_name}, limit=100000)
    existing_point_ids = [point.id for point in existing_points]
    if not same_name_records and not existing_point_ids:
        return 0, 0

    if existing_point_ids:
        models = import_qdrant_models()
        vector_client.delete(
            collection_name=get_active_collection_name(),
            points_selector=models.PointIdsList(points=existing_point_ids),
        )
    deleted_chunks = len(existing_point_ids)
    deleted_records = delete_ingested_file_records_by_name(file_name)
    return deleted_chunks, deleted_records


# Local LLM protocol adapters are split out for OpenAI-compatible and Anthropic-compatible backends.
# 本地大模型协议适配单独拆出，便于维护 OpenAI 兼容和 Anthropic 兼容后端。
from .llm_clients import *  # noqa: F401,F403


# =========================
# 模型状态
# =========================
def record_model_event(component: str, status: str, detail: str) -> None:
    ensure_session_defaults()
    st.session_state["model_events"].append(
        {
            "time": time.strftime("%H:%M:%S"),
            "component": translate_text(component),
            "status": translate_text(status),
            "detail": translate_text(detail),
        }
    )
    st.session_state["model_events"] = st.session_state["model_events"][-50:]


def get_bge_cache_status() -> str:
    try:
        if is_bge_model_cached():
            return localized_text("Local cache found: ", "已发现本地缓存：", "已發現本地快取：") + get_bge_cache_dir()
        return localized_text(
            "No complete cache found. First use will download to: ",
            "未发现完整缓存，首次使用会下载到：",
            "未發現完整快取，首次使用會下載到：",
        ) + get_bge_cache_dir()
    except Exception as e:
        return localized_text("Unable to check cache: ", "无法检查缓存：", "無法檢查快取：") + str(e)


def get_reranker_cache_status() -> str:
    try:
        if is_reranker_model_cached():
            return localized_text("Local cache found: ", "已发现本地缓存：", "已發現本地快取：") + get_reranker_cache_dir()
        return localized_text(
            "No complete cache found. First use will download to: ",
            "未发现完整缓存，首次使用会下载到：",
            "未發現完整快取，首次使用會下載到：",
        ) + get_reranker_cache_dir()
    except Exception as e:
        return localized_text("Unable to check cache: ", "无法检查缓存：", "無法檢查快取：") + str(e)


def get_paddle_cache_status() -> str:
    cache_roots = [
        Path(get_paddleocr_cache_dir()) / "official_models",
        Path.home() / ".paddlex" / "official_models",
        Path.home() / ".paddleocr",
        Path.home() / ".cache" / "paddle",
    ]
    existing = []
    for root in cache_roots:
        if root.exists():
            children = [child.name for child in root.iterdir()]
            if children:
                existing.append(
                    f"{root} ({len(children)} {localized_text('items', '项', '項')})"
                )

    if existing:
        return localized_text("Cache found: ", "已发现缓存：", "已發現快取：") + "；".join(existing[:2])
    return localized_text(
        "No obvious cache found. First OCR use will download models.",
        "未发现明显缓存，首次 OCR 会下载",
        "未發現明顯快取，首次 OCR 會下載",
    )


def test_llm_connection(mode: str = "fast") -> str:
    response = create_llm_chat_completion(
        messages=[
            {
                "role": "system",
                "content": localized_text(
                    "You are a connectivity test assistant. Reply only with OK.",
                    "你是连通性测试助手，只回复 OK。",
                    "你是連通性測試助手，只回覆 OK。",
                ),
            },
            {"role": "user", "content": localized_text("Test", "测试", "測試")},
        ],
        temperature=0,
        mode=mode,
    )
    return response.choices[0].message.content or ""


# =========================
# 文件处理函数 / File handling and document parsing
# =========================
# Document parsing is kept in a separate module because PDF, Office, and OCR code grows quickly.
# 文档解析单独放在一个模块里，因为 PDF、Office 和 OCR 逻辑会快速增长。
from .document_parsing import *  # noqa: F401,F403


# RAG ingestion and retrieval pipeline lives outside the infrastructure service module.
# RAG 入库和检索流水线放在基础服务模块之外，便于独立维护。
from .rag_pipeline import *  # noqa: F401,F403


@st.cache_data(ttl=10, show_spinner=False)
def get_file_summary_rows(language_code: str = "") -> List[Dict[str, Any]]:
    """Return file-level summary rows from SQLite instead of scanning Qdrant.
    从 SQLite 返回文件级摘要，避免打开摘要时扫描整个 Qdrant 向量库。
    """
    return [
        {
            source_label("source_file"): item["file_name"],
            source_label("document_type"): translate_text(DOC_CATEGORY_NAMES.get(item["doc_category"], item["doc_category"])),
            localized_text("Source Format", "来源格式", "來源格式"): os.path.splitext(item["file_name"])[1].lstrip(".").lower() or source_label("unknown_type"),
            localized_text("Chunk Count", "chunk 数", "chunk 數"): int(item["chunk_count"] or 0),
            "SHA256": str(item["sha256"])[:16],
        }
        for item in list_ingested_files()
    ]


def ensure_local_qdrant_mode_for_backup(action: str) -> str:
    """Return the local Qdrant path or raise when HTTP mode is active.
    返回本地 Qdrant 路径；若当前为 HTTP 模式则抛出清晰错误。
    """
    qdrant_config = get_qdrant_config()
    if qdrant_config["mode"] != "local":
        raise RuntimeError(
            localized_text(
                f"Vector store {action} currently supports Local Qdrant only. For Docker/HTTP Qdrant, use the Qdrant server's own snapshot/backup mechanism or migrate data to Local mode first.",
                f"向量库{action}当前仅支持本地 Qdrant。Docker/HTTP Qdrant 请使用 Qdrant 服务端自带的 snapshot/backup，或先把数据迁移到本地模式。",
                f"向量庫{action}目前僅支援本地 Qdrant。Docker/HTTP Qdrant 請使用 Qdrant 服務端自帶的 snapshot/backup，或先把資料遷移到本地模式。",
            )
        )
    return qdrant_config["local_path"]


def rebuild_ingested_file_records_from_qdrant() -> int:
    """Rebuild SQLite deduplication records from Qdrant payload metadata.
    根据 Qdrant payload 元数据重建 SQLite 去重记录。
    """
    rows_by_sha: Dict[str, Dict[str, Any]] = {}
    for point in iter_qdrant_points(with_payload=True, with_vectors=False, batch_size=512):
        payload = point_payload(point)
        sha256 = str(payload.get("file_sha256") or "").strip()
        if not sha256:
            continue
        row = rows_by_sha.setdefault(
            sha256,
            {
                "sha256": sha256,
                "file_name": str(payload.get("file_name") or ""),
                "doc_category": str(payload.get("doc_category") or "general"),
                "doc_label": str(payload.get("doc_label") or payload.get("file_name") or ""),
                "chunk_count": 0,
                "created_at": current_timestamp(),
                "updated_at": current_timestamp(),
            },
        )
        row["chunk_count"] += 1
    return replace_ingested_file_records(list(rows_by_sha.values()))


def create_vector_library_backup_file(output_dir: str = BACKUP_DIR) -> Tuple[str, int]:
    def backup_permission_error(file_path: str) -> RuntimeError:
        return RuntimeError(
            localized_text(
                f"Backup could not read {file_path}. Close other programs that may be using the vector store, then retry. If the issue persists, check file permissions.",
                f"备份时无法读取文件：{file_path}。请先关闭可能正在占用向量库的其他程序后重试；如果仍失败，请检查该文件权限。",
                f"備份時無法讀取文件：{file_path}。請先關閉可能正在佔用向量庫的其他程式後重試；如果仍失敗，請檢查該文件權限。",
            )
        )

    def should_skip_backup_file(file_path: str) -> bool:
        file_name = os.path.basename(file_path)
        return file_name in {".lock", ".DS_Store", "Thumbs.db", "desktop.ini"} or file_name.startswith("._")

    def write_backup_file(archive: zipfile.ZipFile, file_path: str, archive_name: str) -> None:
        if should_skip_backup_file(file_path):
            return
        try:
            archive.write(file_path, archive_name)
        except PermissionError as exc:
            raise backup_permission_error(file_path) from exc
        except OSError as exc:
            if getattr(exc, "errno", None) == 13:
                raise backup_permission_error(file_path) from exc
            raise

    source_qdrant_dir = ensure_local_qdrant_mode_for_backup(
        localized_text("backup", "备份", "備份")
    )
    if not os.path.isdir(source_qdrant_dir):
        raise FileNotFoundError(
            localized_text(
                f"Qdrant directory was not found: {source_qdrant_dir}",
                f"未找到 Qdrant 目录：{source_qdrant_dir}",
                f"未找到 Qdrant 目錄：{source_qdrant_dir}",
            )
        )

    try:
        close_qdrant_singleton()
        load_qdrant_client.clear()
    except Exception:
        pass
    gc.collect()

    os.makedirs(output_dir, exist_ok=True)
    backup_path = os.path.abspath(
        os.path.join(output_dir, f"ocr_rag_backup_{time.strftime('%Y%m%d_%H%M%S')}.zip")
    )
    temp_backup_path = backup_path + ".tmp"
    manifest = {
        "format": "ocr_rag_qdrant_backup",
        "version": 2,
        "created_at": current_timestamp(),
        "collection_name": COLLECTION_NAME,
        "active_collection_name": get_active_collection_name(),
        "embedding_model": get_embedding_model_name(),
        "vector_size": get_embedding_vector_size(),
        "available_embedding_models": {
            model_name: {
                "collection_name": get_collection_name_for_embedding_model(model_name),
                "vector_size": get_embedding_vector_size(model_name),
            }
            for model_name in EMBEDDING_MODEL_OPTIONS
        },
        "qdrant_dir": QDRANT_DIR,
        "contains": [QDRANT_DIR, BACKUP_INGESTED_FILES_NAME],
        "notes": {
            "en": "ingested_files.json restores both deduplication records and file summary rows.",
            "zh_CN": "ingested_files.json 同时用于恢复去重记录和文件摘要。",
            "zh_TW": "ingested_files.json 同時用於恢復去重記錄和文件摘要。",
        },
    }
    try:
        with zipfile.ZipFile(temp_backup_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            archive.writestr(
                BACKUP_MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            archive.writestr(
                BACKUP_INGESTED_FILES_NAME,
                json.dumps(list_ingested_files(), ensure_ascii=False, indent=2, default=str),
            )
            if os.path.isdir(source_qdrant_dir):
                state = get_qdrant_singleton_state()
                with state["lock"]:
                    for root, dirs, files in os.walk(source_qdrant_dir):
                        dirs[:] = [name for name in dirs if name != "__MACOSX"]
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            archive_name = os.path.join(QDRANT_DIR, os.path.relpath(file_path, source_qdrant_dir))
                            write_backup_file(archive, file_path, archive_name)
        os.replace(temp_backup_path, backup_path)
    except Exception:
        if os.path.exists(temp_backup_path):
            try:
                os.remove(temp_backup_path)
            except Exception:
                pass
        raise
    return backup_path, os.path.getsize(backup_path)


def create_vector_library_backup() -> bytes:
    """Create a backup and return bytes for backward compatibility.
    创建备份并以 bytes 返回，保留旧调用兼容性。
    """
    backup_path, _backup_size = create_vector_library_backup_file()
    with open(backup_path, "rb") as backup_file:
        return backup_file.read()


def safe_extract_backup(uploaded_backup) -> Tuple[str, bool, bool]:
    temp_dir = tempfile.mkdtemp(prefix="ocr_rag_restore_")
    has_qdrant = False
    has_ingested_records = False
    try:
        if not isinstance(uploaded_backup, (str, os.PathLike)):
            uploaded_backup.seek(0)
    except Exception:
        pass
    with zipfile.ZipFile(uploaded_backup) as archive:
        for member in archive.infolist():
            normalized = member.filename.replace("\\", "/")
            if normalized.endswith("/"):
                continue
            if normalized.startswith(f"{QDRANT_DIR}/"):
                has_qdrant = True
            elif normalized == BACKUP_INGESTED_FILES_NAME:
                has_ingested_records = True
            elif normalized == BACKUP_MANIFEST_NAME:
                pass
            else:
                continue
            target_path = os.path.abspath(os.path.join(temp_dir, normalized))
            if not target_path.startswith(os.path.abspath(temp_dir) + os.sep):
                raise ValueError(
                    localized_text(
                        "The backup contains an unsafe path and was rejected.",
                        "备份文件包含不安全路径，已拒绝导入。",
                        "備份文件包含不安全路徑，已拒絕導入。",
                    )
                )
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with archive.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)
    if not has_qdrant:
        raise ValueError(
            localized_text(
                "The backup does not contain qdrant_db contents.",
                "备份包中没有发现 qdrant_db 向量库内容。",
                "備份包中沒有發現 qdrant_db 向量庫內容。",
            )
        )
    return temp_dir, has_qdrant, has_ingested_records


def restore_vector_library_backup(uploaded_backup) -> str:
    target_qdrant_dir = ensure_local_qdrant_mode_for_backup(
        localized_text("restore", "导入", "導入")
    )
    restore_dir, has_qdrant, has_ingested_records = safe_extract_backup(uploaded_backup)
    try:
        try:
            close_qdrant_singleton()
            load_qdrant_client.clear()
        except Exception:
            pass
        restored_qdrant_dir = os.path.join(restore_dir, QDRANT_DIR)
        if has_qdrant and os.path.isdir(restored_qdrant_dir):
            if os.path.isdir(target_qdrant_dir):
                shutil.rmtree(target_qdrant_dir)
            os.makedirs(os.path.dirname(os.path.abspath(target_qdrant_dir)), exist_ok=True)
            shutil.copytree(restored_qdrant_dir, target_qdrant_dir)

        try:
            load_qdrant_client.clear()
        except Exception:
            pass
        load_qdrant_client()

        ingested_records_path = os.path.join(restore_dir, BACKUP_INGESTED_FILES_NAME)
        if has_ingested_records and os.path.isfile(ingested_records_path):
            with open(ingested_records_path, "r", encoding="utf-8") as records_file:
                records = json.load(records_file)
            restored_records = replace_ingested_file_records(records if isinstance(records, list) else [])
        else:
            restored_records = rebuild_ingested_file_records_from_qdrant()

        return localized_text(
            f"Backup imported. Restored {restored_records} file records. The library view has been reloaded.",
            f"备份已导入，已恢复 {restored_records} 条文件记录，文档库视图已重新加载。",
            f"備份已導入，已恢復 {restored_records} 條文件記錄，文件庫視圖已重新載入。",
        )
    finally:
        shutil.rmtree(restore_dir, ignore_errors=True)


def restore_vector_library_backup_from_path(backup_path: str) -> str:
    backup_path = normalize_local_path(backup_path)
    if not os.path.isfile(backup_path):
        raise FileNotFoundError(
            localized_text(
                f"Backup file was not found: {backup_path}",
                f"未找到备份文件：{backup_path}",
                f"未找到備份文件：{backup_path}",
            )
        )
    return restore_vector_library_backup(backup_path)
