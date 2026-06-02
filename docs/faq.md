# 常见问题 (FAQ)

---

## 安装与运行

### Q: pip install 报错 "No matching distribution found"?

确保 Python 版本 >= 3.9。推荐使用 Python 3.12：

```bash
python --version
```

如版本过低，请从 [python.org](https://www.python.org/downloads/) 下载最新版本。

### Q: 启动时报 "No module named 'PyQt5'"?

安装 PyQt5：

```bash
pip install PyQt5>=5.15
```

Windows 用户通常可直接安装。Linux 用户可能需要额外安装系统依赖：

```bash
sudo apt-get install python3-pyqt5
```

### Q: 启动后界面一片空白或崩溃?

1. 确认 PyQt5 版本 >= 5.15
2. 尝试删除缓存目录后重启：
   - Windows: `%APPDATA%\DevLearnerAI\`
3. 使用开发模式启动查看日志：`python dev_main.py`

### Q: 在 Linux / macOS 上可以运行吗?

可以运行，但部分功能依赖 Windows Credential Manager。Linux/macOS 用户需要安装 keyring：

```bash
pip install keyring>=24.0
```

凭证存储会自动回退到 keyring 后端。

---

## AI 导师

### Q: AI 导师连接失败?

1. 检查 AI 设置中的 Host 和 Key 是否正确
2. 确保使用 HTTPS 端点（HTTP 会被拒绝）
3. 点击"测试连接"按钮验证配置
4. 检查网络连接和防火墙设置
5. 使用 `python dev_main.py` 启动查看详细错误日志

### Q: AI 回复很慢?

- 检查网络延迟到 API 服务器
- 减少对话历史长度（长对话会增加 token 消耗）
- 尝试切换到更快的模型

### Q: 可以使用哪些 AI 服务?

支持所有 OpenAI 兼容 API，包括：
- OpenAI
- Azure OpenAI
- 本地部署的兼容服务（如 Ollama、vLLM、LocalAI）

在 AI 设置中配置自定义端点即可。

---

## 代码执行

### Q: Python 代码执行报错?

沙箱会拦截危险操作，以下操作会被阻止：
- `import os` / `import subprocess`
- `open()` 文件操作
- `eval()` / `exec()`
- `__import__`

这是设计行为，保障安全。如需运行受限代码，请使用本地 Python 环境。

### Q: C / C++ / C# 代码无法运行?

C / C++ / C# 代码当前使用结构检查评测，不实际编译运行。评测内容包括：
- 语法结构正确性
- 关键字检查
- 代码风格检查

### Q: SQL 练习评测不通过?

- 确认 SQL 语法正确（使用 SQLite 方言）
- 检查表名和列名拼写
- 注意大小写敏感性
- 查看评测反馈中的具体差异

---

## 课程与练习

### Q: 课程内容显示乱码?

确保系统安装了中文字体。课程使用 Markdown 格式，如果渲染异常：
1. 检查 Markdown 文件编码是否为 UTF-8
2. 尝试重启应用

### Q: 练习草稿丢失了吗?

不会。练习草稿自动保存到本地数据库，中途退出不会丢失。重新打开同一道题即可恢复。

### Q: 如何添加自定义课程?

1. 在 `content/` 目录对应子目录下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册课程元数据
3. 在 `content/metadata/exercises.json` 中注册关联练习（如适用）
4. 重启应用加载新内容

详见 [课程内容编写指南](guides/content-authoring.md)。

---

## 数据与隐私

### Q: 学习数据存储在哪里?

所有数据存储在本地 SQLite 数据库中，位于应用数据目录：
- Windows: `%APPDATA%\DevLearnerAI\`
- 数据不会上传到任何服务器

### Q: API Key 安全吗?

- Windows: 存储在 Windows Credential Manager 中（加密）
- 其他平台: 使用 keyring 库，回退到文件存储（base64 编码）
- API Key 不会明文存储在配置文件中

### Q: 如何备份学习数据?

复制应用数据目录下的数据库文件即可：
- Windows: `%APPDATA%\DevLearnerAI\*.db`

---

## 构建与打包

### Q: 打包后运行报 "ModuleNotFoundError"?

在 `scripts/build/build.py` 中对应变体的 `hidden_imports` 列表里添加缺失模块。

### Q: 打包体积过大?

1. 确保安装了 UPX 并在 PATH 中
2. 在构建脚本的 `excludes` 列表中排除不需要的包
3. 检查 `content/` 目录是否有非必要文件

更多打包问题请参阅 [构建与发布指南](distribution.md)。

---

## 其他问题

如以上内容未覆盖你的问题，请在 [GitHub Issues](https://github.com/TIANWEN-cpu/DevLearnerAI/issues) 中提问，或查阅 [故障排除指南](troubleshooting.md)。
