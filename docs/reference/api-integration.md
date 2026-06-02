# API 集成参考

本文档描述 DevLearnerAI 与 OpenAI 兼容 API 的通信协议和配置方式。

---

## 概述

DevLearnerAI 使用标准的 OpenAI Chat Completions API 协议进行 AI 通信。支持任何兼容 OpenAI API 格式的服务端点。

---

## API 端点

### 端点自动构建

系统根据用户配置的 `host` 自动构建完整端点：

```python
def build_chat_url(host: str) -> str:
    base = host.rstrip("/")
    return f"{base}/chat/completions" if base.endswith("/v1") else f"{base}/v1/chat/completions"

def build_models_url(host: str) -> str:
    base = host.rstrip("/")
    return f"{base}/models" if base.endswith("/v1") else f"{base}/v1/models"
```

**示例**:

| Host 配置 | 聊天端点 | 模型端点 |
|-----------|---------|---------|
| `https://api.openai.com` | `https://api.openai.com/v1/chat/completions` | `https://api.openai.com/v1/models` |
| `https://custom.api.com/v1` | `https://custom.api.com/v1/chat/completions` | `https://custom.api.com/v1/models` |

---

## 连接测试

### 测试端点

请求 `GET /v1/models` 验证 API 连接：

```python
def test_connection(host: str, api_key: str) -> str:
    require_https(host)
    ctx = create_ssl_context()
    request = urllib.request.Request(
        build_models_url(host),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=20, context=ctx) as response:
        return f"连接成功，状态码 {response.status}。"
```

**缓存**: 测试结果缓存 5 分钟，避免重复网络调用。

**返回值**:

| 场景 | 返回文本 |
|------|---------|
| 成功 | "连接成功，状态码 200。" |
| HTTP 错误 | "连接失败，请检查 Host 地址和网络连接。" |
| 非 HTTPS | "出于安全考虑，仅允许 HTTPS 连接。" |

---

## 模型列表

### 获取可用模型

```python
def fetch_models(host: str, api_key: str) -> list[str]:
    require_https(host)
    ctx = create_ssl_context()
    request = urllib.request.Request(
        build_models_url(host),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(request, timeout=30, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return sorted(item["id"] for item in payload.get("data", []) if "id" in item)
```

**API 请求**:

```http
GET /v1/models HTTP/1.1
Host: api.openai.com
Authorization: Bearer sk-xxx
```

**响应格式**:

```json
{
  "data": [
    {"id": "gpt-4", "object": "model"},
    {"id": "gpt-3.5-turbo", "object": "model"}
  ]
}
```

**返回**: 排序后的模型 ID 列表，如 `["gpt-3.5-turbo", "gpt-4"]`

---

## 聊天请求

### 非流式请求

```python
def send_chat(host, api_key, model, messages, timeout=90) -> str:
    require_https(host)
    ctx = create_ssl_context()
    body = json.dumps({"model": model, "messages": messages}).encode("utf-8")
    request = urllib.request.Request(
        build_chat_url(host),
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]
```

**API 请求**:

```http
POST /v1/chat/completions HTTP/1.1
Host: api.openai.com
Authorization: Bearer sk-xxx
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "你是一个编程导师..."},
    {"role": "user", "content": "什么是变量？"}
  ]
}
```

**响应格式**:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "变量是存储数据的容器..."
      }
    }
  ]
}
```

### 流式请求

```python
def send_chat_stream(host, api_key, model, messages, on_chunk, timeout=90) -> str:
    require_https(host)
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
    }).encode("utf-8")

    # ... 发送请求 ...

    with urllib.request.urlopen(request, timeout=timeout, context=ctx) as response:
        while True:
            chunk = response.read(1024)
            # 解析 SSE 格式
            # data: {"choices":[{"delta":{"content":"你"}}]}
            # data: {"choices":[{"delta":{"content":"好"}}]}
            # data: [DONE]
```

**请求差异**: 流式请求在 body 中添加 `"stream": true`

**SSE 响应格式**:

```text
data: {"choices":[{"delta":{"content":"你"},"index":0}]}

data: {"choices":[{"delta":{"content":"好"},"index":0}]}

data: {"choices":[{"delta":{},"finish_reason":"stop","index":0}]}

data: [DONE]
```

**回退机制**: 如果流式请求失败且未收到任何 chunk，自动回退到非流式模式。

---

## 请求去重

相同请求不会并发发送：

```python
def send_chat(host, api_key, model, messages, timeout=90) -> str:
    request_key = json.dumps({"host": host, "model": model, "messages": messages}, sort_keys=True)

    with _request_lock:
        if request_key in _pending_requests:
            # 等待已有请求完成，复用结果
            event = _pending_requests[request_key]
            event.wait(timeout=timeout)
            return _pending_results.pop(request_key)
```

---

## 安全要求

### HTTPS 强制

所有请求必须使用 HTTPS：

```python
def require_https(host: str) -> None:
    if not host.lower().startswith("https://"):
        raise ValueError("出于安全考虑，仅允许 HTTPS 连接。")
```

### SSL 证书验证

```python
def create_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()  # 完整证书链验证
```

### 认证方式

使用 Bearer Token 认证：

```http
Authorization: Bearer sk-xxxxxxxxxxxx
```

---

## 错误处理

### 常见错误

| 场景 | 处理方式 |
|------|---------|
| HTTP 401 | "连接失败" 提示检查 API Key |
| HTTP 429 | 返回 "请求失败"，用户可重试 |
| HTTP 500+ | 返回 "请求失败"，建议稍后重试 |
| 超时 | 返回 "请求失败"（默认 90 秒超时） |
| 网络不可达 | 返回 "连接失败" |
| 无 choices | 返回错误消息或 "API 返回了没有 choices 的响应" |

### 错误响应格式

```python
# API 返回的错误
if not payload.get("choices"):
    error_msg = payload.get("error", {}).get("message", "API 返回了没有 choices 的响应。")
    result = f"AI 响应异常：{error_msg}"
```

---

## 超时配置

| 操作 | 超时 | 可配置 |
|------|------|--------|
| 连接测试 | 20 秒 | 否 |
| 模型列表 | 30 秒 | 否 |
| 聊天请求 | 90 秒 | 是（timeout 参数） |
| 流式请求 | 90 秒 | 是（timeout 参数） |

---

## API 配置存储

API 配置存储在数据库中，密钥通过 keyring 安全存储：

```python
# 保存配置
db.save_api_config(
    host="https://api.openai.com",
    api_key="sk-xxx",  # 实际存储到 keyring
    model="gpt-4"
)

# 加载配置
host, api_key, model = db.load_api_config()
```

---

## 相关文档

- [安全模型](../concepts/security-model.md) - HTTPS 和凭证管理
- [AI 导师集成](../concepts/ai-integration.md) - AI 功能架构
- [常见问题](../troubleshooting/common-issues.md) - AI 连接问题排查
