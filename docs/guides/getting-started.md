# 快速开始

本文档帮助你快速搭建开发环境并首次运行 DevLearnerAI。

---

## 系统要求

| 要求 | 最低版本 | 推荐版本 |
|------|---------|---------|
| Python | 3.9 | 3.12 |
| 操作系统 | Windows 10 | Windows 11 |
| 磁盘空间 | 500MB | 1GB |
| 内存 | 4GB | 8GB |

> 注意：部分功能（如 Windows Credential Manager 凭证存储）依赖 Windows 系统。Linux/macOS 用户可使用 keyring 后端。

---

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/TIANWEN-cpu/DevLearnerAI.git
cd DevLearnerAI
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv

# Windows 激活
.venv\Scripts\activate

# Linux / macOS 激活
source .venv/bin/activate
```

### 3. 安装依赖

**方式 A：以可编辑模式安装（推荐）**

```bash
pip install -e ".[dev]"
```

这将同时安装运行时依赖和开发依赖（pytest、ruff、coverage 等）。

**方式 B：仅安装运行时依赖**

```bash
pip install -r requirements.txt
```

运行时依赖仅包含三个包：

```text
PyQt5>=5.15       # GUI 框架
mistune>=3.0      # Markdown 解析
keyring>=24.0     # 凭证存储
```

### 4. 验证安装

```bash
# 检查 Python 版本
python --version
# Python 3.9.0 或更高

# 检查 PyQt5 是否安装成功
python -c "from PyQt5.QtWidgets import QApplication; print('PyQt5 OK')"

# 检查 keyring
python -c "import keyring; print('keyring OK')"
```

---

## 首次运行

### 启动生产环境

```bash
python main.py
```

### 启动开发环境（带 DEBUG 日志）

```bash
python dev_main.py
```

开发模式会输出更详细的日志信息，便于排查问题。

### 启动后的界面

```text
┌──────────────┬──────────────────────────────────────┐
│              │                                      │
│  LEARNING OS │  首页                                 │
│              │                                      │
│  DevLearner  │  ┌──────────────────────────────┐    │
│              │  │ 已完成课程: 0                  │    │
│  ──────────  │  │ 连续学习: 0 天                │    │
│              │  │ 练习平均分: 0                  │    │
│  [首页]      │  └──────────────────────────────┘    │
│  [学习路径]  │                                      │
│  [练习中心]  │  快速导航                             │
│  [融合项目]  │  ┌────┐ ┌────┐ ┌────┐ ┌────┐        │
│  [算法动画]  │  │Python│ │ C++ │ │ C#  │ │ DB  │    │
│              │  └────┘ └────┘ └────┘ └────┘        │
│  [深色模式]  │                                      │
│  [A-] [A] [A+]│                                     │
└──────────────┴──────────────────────────────────────┘
```

---

## 初始配置

### 配置 AI 导师

1. 点击顶部 "AI 工作台" 按钮
2. 在 AI 设置中填写：
   - **API Host**: `https://api.openai.com`（或其他兼容端点）
   - **API Key**: 你的 API 密钥
3. 点击 "测试连接" 验证配置
4. 点击 "获取模型" 加载可用模型列表
5. 选择一个模型

### 开始学习

1. 点击侧边栏 "学习路径"
2. 选择一个技术栈（如 Python）
3. 从第一个课程开始学习
4. 完成课程后，前往 "练习中心" 做相关练习

---

## 数据存储位置

应用运行时数据存储在 `%APPDATA%/DevLearnerAI/` 目录下：

```text
%APPDATA%/DevLearnerAI/
├── data/
│   └── app.db        # SQLite 数据库
├── logs/
│   └── app.log       # 应用日志（最大 5MB，保留 3 个备份）
├── cache/            # 缓存目录
├── exports/          # 导出目录
└── drafts/           # 草稿目录
```

---

## 快速验证清单

安装完成后，确认以下功能正常：

- [ ] 应用启动无报错
- [ ] 侧边栏导航正常切换
- [ ] 学习路径页面显示课程列表
- [ ] 练习中心显示练习列表
- [ ] 代码编辑器可以输入代码
- [ ] AI 工作台可以打开（无需配置 API 即可验证 UI）
- [ ] 深色模式切换正常
- [ ] 字号调整正常

---

## 下一步

- [开发工作流](development.md) - 了解日常开发流程
- [测试指南](testing.md) - 运行和编写测试
- [系统架构](../concepts/architecture.md) - 理解系统设计
