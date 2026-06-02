# AI 集成文档

本文档描述 DevLearnerAI 的 AI API 通信协议、消息格式和配置方式。

---

## API 兼容性

系统兼容 **OpenAI Chat Completions API** 格式，可对接任何实现该协议的服务端，包括：

- OpenAI 官方 API
- 兼容 OpenAI 格式的第三方 API（如 Azure OpenAI、本地模型服务）
- 自建的 API 中转服务

---

## 连接配置

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| API Host | API 端点地址（必须 HTTPS） | `https://api.openai.com/v1` |
| API Key | 认证密钥 | `sk-...` |
| Model | 模型名称 | `gpt-4o`, `claude-3-sonnet` |

### 密钥存储

API 密钥通过安全存储管理，不在数据库中明文保存：

1. **Windows**: Windows Credential Manager（加密存储）
2. **macOS/Linux + keyring**: 系统密钥环
3. **回退方案**: Base64 编码文件 `~/.devlearnerai/api_key.txt`

数据库 `mentor_api_config` 表仅保存 Host、Model 和 keyring 别名（`key_alias`）。

---

## 通信协议

### 安全要求

- **强制 HTTPS**: 所有 API 请求必须使用 HTTPS 协议
- **TLS 证书验证**: 启用标准 SSL 证书链验证
- **不支持 HTTP**: 明文 HTTP 请求会被拒绝并抛出 `ValueError`

### 端点构建

系统自动处理 `/v1` 路径：

| Host 输入 | Models 端点 | Chat 端点 |
|-----------|-------------|-----------|
| `https://api.example.com/v1` | `https://api.example.com/v1/models` | `https://api.example.com/v1/chat/completions` |
| `https://api.example.com` | `https://api.example.com/v1/models` | `https://api.example.com/v1/chat/completions` |

### 认证方式

使用 Bearer Token 认证：
```
Authorization: Bearer <api_key>
```

---

## 消息格式

### 请求格式

```json
{
  "model": "gpt-4o",
  "messages": [
    {"role": "system", "content": "系统提示词..."},
    {"role": "user", "content": "用户消息"},
    {"role": "assistant", "content": "助手回复"},
    {"role": "user", "content": "新的用户消息"}
  ]
}
```

### 流式请求格式

```json
{
  "model": "gpt-4o",
  "messages": [...],
  "stream": true
}
```

### 消息历史窗口

发送给 API 的消息历史限制为最近 **12 条**（不含 system 消息），避免超出模型上下文窗口。

### System Prompt 构建

系统提示词动态组装，包含以下部分：

1. **基础角色指令**: "你是 DevLearner 的学习型 AI 助手..."
2. **基础知识库**（可选）: 当前课程体系摘要
3. **个性知识库**（可选）: 用户学习进度、练习记录、连续学习天数
4. **扩展知识库**（可选）: 用户手动添加的文件摘录
5. **当前会话摘要**: 最后一条消息的预览

知识库的三个部分各自可通过开关独立启用/禁用。

---

## 响应处理

### 非流式响应

从标准 Chat Completions 响应中提取：
```
response["choices"][0]["message"]["content"]
```

### 流式响应（SSE）

通过 Server-Sent Events 接收分块数据：

```
data: {"choices":[{"delta":{"content":"你"}}]}
data: {"choices":[{"delta":{"content":"好"}}]}
data: [DONE]
```

处理流程：
1. 以 1024 字节为单位读取响应流
2. 按换行符分割，解析 `data:` 前缀的 SSE 行
3. 提取 `delta.content` 并调用 `on_chunk` 回调
4. 遇到 `[DONE]` 终止
5. 流式失败时自动回退到非流式请求

---

## 性能优化

### 连接状态缓存

- 连接测试结果缓存 **5 分钟**
- 缓存键基于 Host + API Key 后 8 位
- 避免重复网络请求

### 请求去重

对于非流式请求：
- 相同请求（Host + Model + Messages 完全一致）并发时只发送一次
- 其余等待者复用结果
- 使用 `threading.Event` 实现同步

### 超时设置

| 操作 | 默认超时 |
|------|----------|
| 连接测试 | 20 秒 |
| 获取模型列表 | 30 秒 |
| 聊天请求 | 90 秒 |

---

## 错误处理

| 错误类型 | 处理方式 |
|----------|----------|
| HTTPS 违规 | 抛出 `ValueError`，提示用户改用 HTTPS |
| HTTP 错误 | 解析响应体中的 error message，展示给用户 |
| 网络超时 | 提示检查网络连接 |
| API 响应无 choices | 提取 error.message 或显示通用提示 |
| 流式失败 | 自动回退到非流式模式 |
| 编码损坏消息 | 自动检测并替换为占位文本 |

---

## UI 交互模式

### AIMentorPanel

两种 UI 模式共享同一套逻辑：

- **page 模式**: 独立页面，左侧会话列表 + 右侧聊天区，通过 `QSplitter` 布局
- **dock 模式**: 侧边停靠，顶部会话选择器 + 下方聊天区

### 会话管理

- 支持多会话，按主题拆分对话
- 会话间自动同步（切换时保存活跃会话 ID）
- 至少保留一个会话
- 自动清理编码损坏的历史消息

### 快捷提问

预设三个快捷提问按钮：
1. "解释当前课程" -- 结合当前课程解释知识点
2. "分析当前代码" -- 分析代码或报错
3. "拆解当前项目" -- 将项目拆成最小可执行步骤
