# 常见问题

本文档汇总 DevLearnerAI 使用和开发过程中的常见问题及解决方案。

---

## 安装与启动

### Q: 启动时报 "No module named 'PyQt5'"?

**原因**: PyQt5 未安装或不在 Python 环境中。

**解决方案**:

```bash
pip install PyQt5>=5.15
```

如果使用虚拟环境，确保已激活：

```bash
# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

---

### Q: 启动时报 "No module named 'mistune'"?

```bash
pip install mistune>=3.0
```

或一次性安装所有依赖：

```bash
pip install -r requirements.txt
```

---

### Q: Python 版本不满足要求？

DevLearnerAI 需要 Python 3.9 或更高版本。检查当前版本：

```bash
python --version
```

如果版本过低，请从 [python.org](https://www.python.org/downloads/) 下载安装新版本。

---

### Q: 启动后白屏或窗口不显示？

可能原因：

1. **屏幕分辨率过低**: 窗口最小尺寸为 1360x900，确保屏幕分辨率足够
2. **显卡驱动问题**: 尝试更新显卡驱动
3. **PyQt5 版本冲突**: `pip install --force-reinstall PyQt5>=5.15`

---

### Q: 数据库路径在哪里？

数据库文件位于：

```text
Windows:  %APPDATA%/DevLearnerAI/data/app.db
Linux:    ~/.devlearnerai/data/app.db
macOS:    ~/Library/Application Support/DevLearnerAI/data/app.db
```

可通过环境变量 `%APPDATA%` 快速定位：

```bash
# Windows CMD
echo %APPDATA%

# Windows PowerShell
$env:APPDATA
```

---

## AI 导师

> AI 导师的详细功能和配置说明见 [AI 导师指南](../user-guide/ai-mentor-guide.md) 和 [API 集成参考](../reference/api-integration.md)。

### Q: AI 助手无法连接？

排查步骤：

1. **检查 API Host**: 必须以 `https://` 开头（不支持 HTTP）
   ```
   正确: https://api.openai.com
   错误: http://api.openai.com
   ```

2. **检查 API Key**: 确认密钥有效且未过期

3. **使用测试连接**: 在 AI 设置中点击 "测试连接" 按钮

4. **检查网络**: 确认可以访问 API 端点
   ```bash
   curl -I https://api.openai.com/v1/models
   ```

5. **查看日志**: 使用 `dev_main.py` 启动查看 DEBUG 日志

---

### Q: AI 响应速度很慢？

可能原因：

1. **网络延迟**: 使用国内 API 代理可减少延迟
2. **模型选择**: 较大的模型（如 GPT-4）响应较慢，可切换到较小模型
3. **消息过长**: 历史消息过多会增加处理时间，可创建新会话

---

### Q: AI 设置中 "获取模型" 失败？

确认：
- API Host 正确（以 `https://` 开头）
- API Key 有效
- API 端点支持 `/v1/models` 端点
- 网络连接正常

---

### Q: 如何切换 AI 模型？

1. 在 AI 工作台或侧边助手中点击 "AI 设置"
2. 填写 API Host 和 Key
3. 点击 "获取模型" 加载可用模型列表
4. 从下拉列表中选择模型

---

### Q: API 密钥存储在哪里？

API 密钥通过安全机制存储，不在配置文件中明文保存：

- **Windows**: Windows Credential Manager（加密存储）
- **Linux/macOS**: keyring 后端（如 GNOME Keychain、macOS Keychain）
- **回退**: `~/.devlearnerai/api_key.txt`（Base64 编码）

---

## 课程学习

> 课程体系的完整设计详见 [课程内容体系](../concepts/content-system.md)，内容加载策略见 [ADR-003](../adr/003-content-loading.md)。

### Q: 学习进度丢失了吗？

学习数据存储在 `%APPDATA%/DevLearnerAI/data/app.db` 中。

- 如果遇到数据库损坏，应用会自动迁移旧版数据库
- 手动备份可复制 `app.db` 文件
- 重置学习进度会清除课程进度、笔记和练习记录，但 AI 会话不受影响

---

### Q: 课程内容显示乱码？

系统内置了编码损坏检测机制，会自动修复大部分乱码。如果仍然有问题：

1. 检查 Markdown 文件的编码（应为 UTF-8 无 BOM）
2. 检查 `course_map.json` 中的文本字段
3. 在 `content/metadata/exercise_fallbacks.json` 中添加回退值

---

### Q: 如何添加新的课程内容？

1. 在 `content/` 目录对应技术栈下添加 `.md` 文件
2. 在 `content/metadata/course_map.json` 中注册课程元数据
3. （可选）在 `content/metadata/exercises.json` 中关联练习
4. 运行 `python scripts/rebuild/rebuild_courses.py` 更新索引

详见 [课程内容编写指南](../guides/content-authoring.md)。

---

### Q: Markdown 代码块语法高亮不生效？

系统使用 Pygments 进行语法高亮。确保代码块指定了正确的语言标识：

````markdown
```python   # 会高亮
print("hello")

```          # 不会高亮
print("hello")
```
````

---

## 练习评测

### Q: Python 练习提示 "安全限制: 不允许使用 import 语句"？

沙箱禁止使用 `import` 语句，但允许使用白名单中的标准库。白名单包括：

```text
argparse, collections, datetime, functools, itertools,
json, logging, math, pathlib, re, statistics
```

如需使用白名单外的模块，需要修改 `app/python_runner.py` 中的 `ALLOWED_IMPORTS` 集合。

---

### Q: 代码执行超时？

沙箱默认超时为 3 秒（评测为 4 秒）。超时可能的原因：

1. **死循环**: 检查 `while` 循环的退出条件
2. **大量计算**: 简化算法或减少数据量
3. **嵌套过深**: 减少递归深度

---

### Q: SQL 练习评测不通过？

检查以下项目：

1. SQL 语法是否正确
2. 是否包含所有 `required_keywords`
3. 是否使用了 `forbidden_keywords`
4. 结果集是否与参考答案一致（SQL 查询练习会在内存数据库中真实执行）

---

### Q: 练习草稿是否自动保存？

是的。系统会自动将你的代码保存到 `exercise_drafts` 表中，下次打开同一练习时自动恢复。

---

## 构建与打包

### Q: PyInstaller 打包后运行报错？

常见问题：

1. **缺少 hidden imports**: 在 `.spec` 文件中添加缺失的模块
2. **资源文件未包含**: 确认 `content/` 目录被正确打包
3. **路径问题**: 使用 `config.py` 中的 `RUNTIME_DIR` 而非硬编码路径

---

### Q: 打包后文件太大？

优化方法：

1. 使用 UPX 压缩
2. 排除不需要的 Qt 模块
3. 排除开发依赖（pytest、ruff 等）

---

## 开发相关

### Q: 测试运行报 "No module named 'app'"？

确保从项目根目录运行测试：

```bash
cd D:\codelearnhleper
pytest
```

或者安装为可编辑模式：

```bash
pip install -e .
```

---

### Q: 如何在无 GUI 的环境下运行测试？

核心逻辑测试（database、practice_service、content_service、python_runner、credentials）可在无 GUI 环境运行。`tests/conftest.py` 提供了 PyQt5 的 MagicMock 替代品。

Widget 测试需要真实的 PyQt5 环境。

---

### Q: Ruff 报错但不知道怎么修？

```bash
# 尝试自动修复
ruff check --fix .

# 格式化代码
ruff format .
```

对于无法自动修复的问题，参考 [Ruff 文档](https://docs.astral.sh/ruff/) 了解具体规则。

---

## 相关文档

- [沙箱问题排查](sandbox-issues.md) - 代码执行和评测问题
- [内容问题排查](content-issues.md) - 课程加载和显示问题
- [快速开始](../guides/getting-started.md) - 安装和首次运行
