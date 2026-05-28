"""Local LLM configuration and protocol adapters.
本地大模型配置和协议适配器。
"""

from .services import *


def load_llm_config_from_env() -> Dict[str, str]:
    env_values = dotenv_values(ENV_FILE) if os.path.exists(ENV_FILE) else {}
    model = (
        env_values.get("LLM_MODEL")
        or os.getenv("LLM_MODEL")
        or DEFAULT_LLM_MODEL
    )
    api_type = (
        env_values.get("LLM_API_TYPE")
        or os.getenv("LLM_API_TYPE")
        or DEFAULT_LLM_API_TYPE
    )
    if api_type not in set(LLM_API_TYPE_OPTIONS.values()):
        api_type = DEFAULT_LLM_API_TYPE
    return {
        "api_type": api_type,
        "base_url": (
            env_values.get("LLM_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or DEFAULT_LLM_BASE_URL
        ),
        "api_key": (
            env_values.get("LLM_API_KEY")
            or os.getenv("LLM_API_KEY")
            or DEFAULT_LLM_API_KEY
        ),
        "model": model,
        "fast_model": (
            env_values.get("LLM_FAST_MODEL")
            or os.getenv("LLM_FAST_MODEL")
            or model
        ),
        "thinking_model": (
            env_values.get("LLM_THINKING_MODEL")
            or os.getenv("LLM_THINKING_MODEL")
            or model
        ),
        "fast_extra_body": (
            env_values.get("LLM_FAST_EXTRA_BODY")
            or os.getenv("LLM_FAST_EXTRA_BODY")
            or DEFAULT_LLM_EXTRA_BODY
        ),
        "thinking_extra_body": (
            env_values.get("LLM_THINKING_EXTRA_BODY")
            or os.getenv("LLM_THINKING_EXTRA_BODY")
            or DEFAULT_LLM_EXTRA_BODY
        ),
        "request_timeout": str(
            env_values.get("LLM_REQUEST_TIMEOUT")
            or os.getenv("LLM_REQUEST_TIMEOUT")
            or DEFAULT_LLM_REQUEST_TIMEOUT
        ),
    }


def load_llm_config_from_db() -> Optional[Dict[str, str]]:
    base_url = get_config_value("LLM_BASE_URL", "")
    if not base_url:
        return None

    model = get_config_value("LLM_MODEL", DEFAULT_LLM_MODEL)
    api_type = get_config_value("LLM_API_TYPE", DEFAULT_LLM_API_TYPE)
    if api_type not in set(LLM_API_TYPE_OPTIONS.values()):
        api_type = DEFAULT_LLM_API_TYPE
    return {
        "api_type": api_type,
        "base_url": base_url,
        "api_key": get_config_value("LLM_API_KEY", DEFAULT_LLM_API_KEY),
        "model": model,
        "fast_model": get_config_value("LLM_FAST_MODEL", model),
        "thinking_model": get_config_value("LLM_THINKING_MODEL", model),
        "fast_extra_body": get_config_value("LLM_FAST_EXTRA_BODY", DEFAULT_LLM_EXTRA_BODY),
        "thinking_extra_body": get_config_value("LLM_THINKING_EXTRA_BODY", DEFAULT_LLM_EXTRA_BODY),
        "request_timeout": get_config_value("LLM_REQUEST_TIMEOUT", str(DEFAULT_LLM_REQUEST_TIMEOUT)),
    }


def persist_llm_config(config: Dict[str, str]) -> None:
    set_config_value("LLM_API_TYPE", config.get("api_type", DEFAULT_LLM_API_TYPE))
    set_config_value("LLM_BASE_URL", config["base_url"])
    set_config_value("LLM_API_KEY", config["api_key"])
    set_config_value("LLM_MODEL", config["model"])
    set_config_value("LLM_FAST_MODEL", config["fast_model"])
    set_config_value("LLM_THINKING_MODEL", config["thinking_model"])
    set_config_value("LLM_FAST_EXTRA_BODY", config["fast_extra_body"])
    set_config_value("LLM_THINKING_EXTRA_BODY", config["thinking_extra_body"])
    set_config_value("LLM_REQUEST_TIMEOUT", str(config.get("request_timeout", DEFAULT_LLM_REQUEST_TIMEOUT)))


def get_llm_config() -> Dict[str, str]:
    if "llm_config" not in st.session_state:
        config = load_llm_config_from_db()
        if config is None:
            config = load_llm_config_from_env()
            persist_llm_config(config)
        st.session_state["llm_config"] = config
    return st.session_state["llm_config"]


def save_llm_config(
    base_url: str,
    api_key: str,
    model: str,
    api_type: str = DEFAULT_LLM_API_TYPE,
    fast_model: str = "",
    thinking_model: str = "",
    fast_extra_body: str = DEFAULT_LLM_EXTRA_BODY,
    thinking_extra_body: str = DEFAULT_LLM_EXTRA_BODY,
    request_timeout: int = DEFAULT_LLM_REQUEST_TIMEOUT,
) -> None:
    api_type = api_type.strip() or DEFAULT_LLM_API_TYPE
    if api_type not in set(LLM_API_TYPE_OPTIONS.values()):
        api_type = DEFAULT_LLM_API_TYPE
    base_url = base_url.strip() or DEFAULT_LLM_BASE_URL
    api_key = api_key.strip() or DEFAULT_LLM_API_KEY
    model = model.strip() or DEFAULT_LLM_MODEL
    fast_model = fast_model.strip() or model
    thinking_model = thinking_model.strip() or model
    fast_extra_body = fast_extra_body.strip() or DEFAULT_LLM_EXTRA_BODY
    thinking_extra_body = thinking_extra_body.strip() or DEFAULT_LLM_EXTRA_BODY
    request_timeout = max(1, int(request_timeout or DEFAULT_LLM_REQUEST_TIMEOUT))

    parse_extra_body(fast_extra_body)
    parse_extra_body(thinking_extra_body)

    config = {
        "api_type": api_type,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "fast_model": fast_model,
        "thinking_model": thinking_model,
        "fast_extra_body": fast_extra_body,
        "thinking_extra_body": thinking_extra_body,
        "request_timeout": str(request_timeout),
    }
    persist_llm_config(config)

    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_API_TYPE"] = api_type
    os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_MODEL"] = model
    os.environ["LLM_FAST_MODEL"] = fast_model
    os.environ["LLM_THINKING_MODEL"] = thinking_model
    os.environ["LLM_FAST_EXTRA_BODY"] = fast_extra_body
    os.environ["LLM_THINKING_EXTRA_BODY"] = thinking_extra_body
    os.environ["LLM_REQUEST_TIMEOUT"] = str(request_timeout)
    st.session_state["llm_config"] = config


def get_llm_request_timeout(timeout_seconds: Optional[int] = None) -> int:
    if timeout_seconds is not None:
        return max(1, int(timeout_seconds or DEFAULT_LLM_REQUEST_TIMEOUT))
    config = get_llm_config()
    try:
        return max(1, int(config.get("request_timeout", DEFAULT_LLM_REQUEST_TIMEOUT)))
    except Exception:
        return DEFAULT_LLM_REQUEST_TIMEOUT


def get_llm_client(timeout_seconds: Optional[int] = None) -> OpenAI:
    config = get_llm_config()
    return load_llm_client(config["base_url"], config["api_key"], get_llm_request_timeout(timeout_seconds))


def parse_extra_body(raw_extra_body: str) -> Dict[str, Any]:
    raw_extra_body = (raw_extra_body or "").strip()
    if not raw_extra_body:
        return {}
    parsed = json.loads(raw_extra_body)
    if not isinstance(parsed, dict):
        raise ValueError(
            localized_text(
                'extra_body must be a JSON object, for example {} or {"enable_thinking": true}',
                'extra_body 必须是 JSON 对象，例如 {} 或 {"enable_thinking": true}',
                'extra_body 必須是 JSON 物件，例如 {} 或 {"enable_thinking": true}',
            )
        )
    return parsed


def get_llm_mode_config(mode: str) -> Tuple[str, Dict[str, Any]]:
    config = get_llm_config()
    if mode == "thinking":
        model = config.get("thinking_model") or config["model"]
        extra_body = parse_extra_body(config.get("thinking_extra_body", DEFAULT_LLM_EXTRA_BODY))
    else:
        model = config.get("fast_model") or config["model"]
        extra_body = parse_extra_body(config.get("fast_extra_body", DEFAULT_LLM_EXTRA_BODY))
    return model, extra_body


def is_empty_502_error(error: Exception) -> bool:
    status_code = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    response_text = getattr(response, "text", "") if response is not None else ""
    return status_code == 502 and not str(response_text).strip()


def create_simple_chat_completion_response(response_data: Dict[str, Any]) -> SimpleNamespace:
    choices = []
    for choice in response_data.get("choices", []):
        message = choice.get("message") or {}
        choices.append(
            SimpleNamespace(
                message=SimpleNamespace(
                    content=message.get("content") or "",
                    reasoning_content=message.get("reasoning_content"),
                ),
                finish_reason=choice.get("finish_reason"),
            )
        )
    if not choices:
        raise RuntimeError(
            localized_text(
                "The local LLM response did not contain choices.",
                "本地大模型响应中没有 choices。",
                "本地大模型響應中沒有 choices。",
            )
        )
    return SimpleNamespace(choices=choices, raw=response_data)


def create_llm_chat_completion_http_fallback(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    extra_body: Dict[str, Any],
    timeout_seconds: Optional[int] = None,
) -> SimpleNamespace:
    config = get_llm_config()
    base_url = config["base_url"].rstrip("/")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise RuntimeError(
            localized_text(
                f"Invalid local LLM Base URL: {base_url}",
                f"本地大模型 Base URL 无效：{base_url}",
                f"本地大模型 Base URL 無效：{base_url}",
            )
        )

    request_path = (parsed_url.path.rstrip("/") or "") + "/chat/completions"
    connection_cls = http.client.HTTPSConnection if parsed_url.scheme == "https" else http.client.HTTPConnection
    connection_host = parsed_url.hostname
    connection = connection_cls(connection_host, parsed_url.port, timeout=get_llm_request_timeout(timeout_seconds))
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    payload.update(extra_body or {})
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "User-Agent": "curl/8.7.1",
        "Accept": "*/*",
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    try:
        connection.request("POST", request_path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()

    if response.status >= 400:
        raise RuntimeError(
            localized_text(
                f"Local LLM HTTP fallback failed: HTTP {response.status} {response.reason}. {response_body}",
                f"本地大模型 HTTP 兼容调用失败：HTTP {response.status} {response.reason}。{response_body}",
                f"本地大模型 HTTP 相容調用失敗：HTTP {response.status} {response.reason}。{response_body}",
            )
        )
    try:
        response_data = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            localized_text(
                f"Local LLM returned non-JSON content: {response_body[:500]}",
                f"本地大模型返回的不是 JSON：{response_body[:500]}",
                f"本地大模型返回的不是 JSON：{response_body[:500]}",
            )
        ) from exc
    return create_simple_chat_completion_response(response_data)


def normalize_anthropic_base_url(base_url: str) -> Tuple[Any, str]:
    parsed_url = urlparse(base_url.rstrip("/"))
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.hostname:
        raise RuntimeError(
            localized_text(
                f"Invalid local LLM Base URL: {base_url}",
                f"本地大模型 Base URL 无效：{base_url}",
                f"本地大模型 Base URL 無效：{base_url}",
            )
        )
    base_path = parsed_url.path.rstrip("/")
    if base_path.endswith("/v1"):
        request_path = base_path + "/messages"
    elif base_path.endswith("/messages"):
        request_path = base_path
    else:
        request_path = base_path + "/v1/messages"
    return parsed_url, request_path


def convert_messages_to_anthropic(messages: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, str]]]:
    system_parts = []
    anthropic_messages = []
    for message in messages:
        role = message.get("role", "user")
        content = str(message.get("content", ""))
        if role == "system":
            if content.strip():
                system_parts.append(content.strip())
            continue
        if role not in {"user", "assistant"}:
            role = "user"
        if anthropic_messages and anthropic_messages[-1]["role"] == role:
            anthropic_messages[-1]["content"] += "\n\n" + content
        else:
            anthropic_messages.append({"role": role, "content": content})

    if not anthropic_messages:
        anthropic_messages.append({"role": "user", "content": localized_text("Hello", "你好", "你好")})
    if anthropic_messages[0]["role"] == "assistant":
        anthropic_messages.insert(0, {"role": "user", "content": localized_text("Continue.", "请继续。", "請繼續。")})
    return "\n\n".join(system_parts), anthropic_messages


def create_anthropic_messages_completion(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    extra_body: Dict[str, Any],
    timeout_seconds: Optional[int] = None,
) -> SimpleNamespace:
    config = get_llm_config()
    parsed_url, request_path = normalize_anthropic_base_url(config["base_url"])
    system_prompt, anthropic_messages = convert_messages_to_anthropic(messages)
    payload_extra = dict(extra_body or {})
    payload = {
        "model": model,
        "messages": anthropic_messages,
        "temperature": temperature,
        "max_tokens": int(payload_extra.pop("max_tokens", payload_extra.pop("max_output_tokens", 4096))),
    }
    if system_prompt:
        payload["system"] = system_prompt
    payload.update(payload_extra)

    connection_cls = http.client.HTTPSConnection if parsed_url.scheme == "https" else http.client.HTTPConnection
    connection = connection_cls(parsed_url.hostname, parsed_url.port, timeout=get_llm_request_timeout(timeout_seconds))
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
    }
    try:
        connection.request("POST", request_path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()

    if response.status >= 400:
        raise RuntimeError(
            localized_text(
                f"Anthropic-compatible call failed: HTTP {response.status} {response.reason}. {response_body}",
                f"Anthropic 兼容调用失败：HTTP {response.status} {response.reason}。{response_body}",
                f"Anthropic 相容調用失敗：HTTP {response.status} {response.reason}。{response_body}",
            )
        )

    try:
        response_data = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            localized_text(
                f"Anthropic-compatible endpoint returned non-JSON content: {response_body[:500]}",
                f"Anthropic 兼容接口返回的不是 JSON：{response_body[:500]}",
                f"Anthropic 相容接口返回的不是 JSON：{response_body[:500]}",
            )
        ) from exc

    content_parts = []
    for block in response_data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            content_parts.append(block.get("text", ""))
    content = "\n".join(part for part in content_parts if part).strip()
    return create_simple_chat_completion_response(
        {
            "choices": [
                {
                    "message": {"content": content},
                    "finish_reason": response_data.get("stop_reason"),
                }
            ],
            "raw": response_data,
        }
    )


def create_openai_compatible_chat_completion(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    extra_body: Dict[str, Any],
    timeout_seconds: Optional[int] = None,
):
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if extra_body:
        kwargs["extra_body"] = extra_body
    try:
        return get_llm_client(timeout_seconds).chat.completions.create(**kwargs)
    except Exception as error:
        if is_empty_502_error(error):
            return create_llm_chat_completion_http_fallback(
                model=model,
                messages=messages,
                temperature=temperature,
                extra_body=extra_body,
                timeout_seconds=timeout_seconds,
            )
        raise


def create_llm_chat_completion(
    messages: List[Dict[str, str]],
    temperature: float,
    mode: str = "fast",
    timeout_seconds: Optional[int] = None,
):
    model, extra_body = get_llm_mode_config(mode)
    api_type = get_llm_config().get("api_type", DEFAULT_LLM_API_TYPE)
    if api_type == "anthropic":
        return create_anthropic_messages_completion(model, messages, temperature, extra_body, timeout_seconds=timeout_seconds)
    if api_type == "openai":
        return create_openai_compatible_chat_completion(model, messages, temperature, extra_body, timeout_seconds=timeout_seconds)

    openai_error: Optional[Exception] = None
    try:
        return create_openai_compatible_chat_completion(model, messages, temperature, extra_body, timeout_seconds=timeout_seconds)
    except Exception as error:
        openai_error = error

    try:
        return create_anthropic_messages_completion(model, messages, temperature, extra_body, timeout_seconds=timeout_seconds)
    except Exception as anthropic_error:
        raise RuntimeError(
            localized_text(
                f"Auto-detect failed. OpenAI-compatible error: {openai_error}; Anthropic-compatible error: {anthropic_error}",
                f"接口自动识别失败。OpenAI 兼容错误：{openai_error}；Anthropic 兼容错误：{anthropic_error}",
                f"接口自動識別失敗。OpenAI 相容錯誤：{openai_error}；Anthropic 相容錯誤：{anthropic_error}",
            )
        ) from anthropic_error
