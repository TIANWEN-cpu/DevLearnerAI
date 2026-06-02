# DevLearnerAI 高投入产出比改进清单

**生成日期:** 2026-06-02
**基于:** MATURITY_SCORECARD.md (整体成熟度 L2.0) + PRODUCT_AUDIT.md
**目标:** 从 TOP 改进项中筛选 7 项，本冲刺 (Sprint) 内立即执行

---

## 评分框架

每项改进按四个维度打分 (1-10)，计算综合 ROI:

| 维度 | 权重 | 说明 |
|------|------|------|
| **影响力 (Impact)** | 35% | 对用户价值、成熟度提升、风险消除的贡献 |
| **紧迫度 (Urgency)** | 25% | 不做会怎样？是否阻塞发布/获客/用户留存 |
| **可复用性 (Leverage)** | 20% | 是否解锁后续功能、是否惠及多个模块 |
| **可执行性 (Feasibility)** | 20% | 当前代码基础是否支持，是否需要外部依赖 |

**ROI 公式:** `(Impact x 0.35 + Urgency x 0.25 + Leverage x 0.20 + Feasibility x 0.20) / Effort`

**Effort** 按人天估算: 1-2 天=1, 3-4 天=2, 5-7 天=3, 8-10 天=4, 10+ 天=5

---

## TOP 7 改进项 (按 ROI 降序)

---

### #1 -- C/C++/C# 评测诚实化

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 8 | 消除 "假装评测" 的信任风险 -- 用户发现关键字检查不代表代码正确会彻底失去对产品的信任 |
| 紧迫度 | 10 | 这是发布阻塞项 (P0) -- 公开发布后 60% 概率被用户发现并公开吐槽 |
| 可复用性 | 7 | 诚实化框架可复用到未来任何新增语言的评测上 |
| 可执行性 | 9 | 纯 UI + 文案变更，代码基础完全支持 |
| **Effort** | **1** | **2 天** |

**ROI = 8.75 / 1 = 8.75**

**具体措施:**

1. 在 `app/practice/evaluator.py` 的 `evaluate_keyword_code()` 返回的 `EvaluationResult` 中，将反馈文本从 "评测通过/未通过" 改为 "结构检查通过/未通过 (注意: 当前语言仅检查代码结构，不验证编译和运行结果)"
2. 在 `app/widgets/practice.py` 的练习详情面板中，当语言为 C/C++/C# 时，在代码编辑器上方显示一条黄色提示条: "此语言练习仅验证代码结构 (关键字、语法)，无法实际编译运行。推荐使用 Python 练习体验完整的运行评测。"
3. 将 `EvaluationResult` 新增 `evaluation_mode` 字段 (`"runtime"` / `"structural"`)，让 UI 可以区分真实评测和结构检查
4. 添加 3-5 个单元测试验证新模式的返回值和反馈文案

**涉及文件:**
- `app/practice/evaluator.py` -- 评测逻辑
- `app/practice/models.py` -- 新增 `evaluation_mode` 字段
- `app/widgets/practice.py` -- UI 提示条
- `tests/test_practice_service*.py` -- 新增测试

---

### #2 -- GitHub Release 安装包发布

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 9 | 消除安装门槛，从 "需要 Python 环境 + pip install" 变为 "下载双击安装" |
| 紧迫度 | 9 | 分发与增长维度从 L1 升 L2 的第一项必要条件 |
| 可复用性 | 8 | 构建流水线可复用于每次版本发布，CI 自动触发 |
| 可执行性 | 7 | 已有 PyInstaller 构建脚本和 GitHub Actions CI，只需串联 |
| **Effort** | **2** | **3 天** |

**ROI = 8.65 / 2 = 4.33**

**具体措施:**

1. 验证现有 `scripts/build/build.py --variant release` 能产出可运行的 `.exe`
2. 创建 `.github/workflows/release.yml` (如不存在)，在 tag push 时自动:
   - 运行完整测试套件
   - 执行 PyInstaller 打包
   - 创建 GitHub Release，附加 `.exe` 文件
3. 在 Release 正文中添加: 版本变更摘要 + 系统要求 (Windows 10+) + 安装说明 + 截图
4. 在 README.md 顶部添加醒目的 "Download Latest Release" 按钮和截图
5. 添加首次启动版本检查逻辑 (可选): 检查 GitHub API 提示用户更新

**涉及文件:**
- `.github/workflows/release.yml` -- 发布流水线
- `scripts/build/build.py` -- 构建脚本 (验证)
- `README.md` -- 添加下载按钮
- `app/config.py` -- 版本检查 (可选)

---

### #3 -- 空状态仪表盘改造

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 8 | 首次打开应用的第一印象 -- 空白仪表盘 = 用户 30 秒内关闭 |
| 紧迫度 | 9 | 首次体验是用户流失的最大单点 (85% 流失概率) |
| 可复用性 | 6 | 空状态模式可复用到练习中心、项目页面等其他空白区域 |
| 可执行性 | 9 | 纯前端 UI 工作，不依赖后端变更 |
| **Effort** | **2** | **3 天** |

**ROI = 8.05 / 2 = 4.03**

**具体措施:**

1. 在 `DashboardWidget._build_welcome()` 中检测首次使用状态 (数据库无进度记录)，显示:
   - 大标题: "欢迎来到 DevLearnerAI"
   - 副标题: "AI 驱动的桌面编程学习平台，从今天开始你的编程之旅"
   - 三个快速开始按钮: "开始 Python 学习" / "浏览所有路线" / "尝试练习题"
2. 统计卡片区域无数据时显示引导文案而非 0:
   - "还没有学习记录 -- 点击下方按钮开始第一课"
   - "还没有练习记录 -- 从 Python 基础练习开始"
3. 为学习路径、练习中心、融合项目页面的空列表添加引导卡片
4. 添加 "标记为已读" 或 "不再显示" 的交互，避免老用户每次都看到

**涉及文件:**
- `app/widgets/dashboard.py` -- 仪表盘空状态
- `app/widgets/learn.py` -- 学习路径空状态
- `app/widgets/practice.py` -- 练习中心空状态
- `app/widgets/projects.py` -- 融合项目空状态
- `app/database.py` -- 查询首次使用状态

---

### #4 -- GitHub 社区基础设施搭建

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 7 | 建立用户反馈渠道和社区归属感，是增长飞轮的起点 |
| 紧迫度 | 8 | 分发与增长维度 L1 升 L2 的必要条件，无社区 = 无反馈 = 产品闭门造车 |
| 可复用性 | 8 | Issue 模板和 Discussions 配置永久复用，成为项目的基础设施 |
| 可执行性 | 10 | 纯配置文件，零代码变更风险 |
| **Effort** | **1** | **1 天** |

**ROI = 8.15 / 1 = 8.15**

**具体措施:**

1. 创建 `.github/ISSUE_TEMPLATE/` 目录，添加:
   - `bug_report.yml` -- Bug 报告模板 (版本号、操作系统、复现步骤、预期行为)
   - `feature_request.yml` -- 功能请求模板 (问题描述、建议方案、使用场景)
   - `content_error.yml` -- 内容错误模板 (课程/练习位置、错误描述、正确答案)
   - `config.yml` -- 配置 "打开 Discussion" 链接
2. 创建 `.github/PULL_REQUEST_TEMPLATE.md` -- PR 模板 (变更说明、测试确认、关联 Issue)
3. 创建 `.github/SUPPORT.md` -- 支持文档 (FAQ 链接、Discussion 入口、安全漏洞报告方式)
4. 创建 `.github/SECURITY.md` -- 安全政策 (漏洞报告流程、响应时间承诺)
5. 在 README.md 添加 "社区" 板块: Discussion 链接 + Issue 模板说明 + 贡献者指南链接

**涉及文件:**
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/content_error.yml`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/SUPPORT.md`
- `.github/SECURITY.md`
- `README.md` -- 社区板块

---

### #5 -- 新用户入门引导流程

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 8 | 从 "打开就迷路" 到 "5 分钟走完核心路径" -- 首次体验决定留存 |
| 紧迫度 | 8 | 发布阻塞项 (P0)，无引导 = 用户流失率 90%+ |
| 可复用性 | 7 | 引导框架可扩展到新功能发布时的 Feature Tour |
| 可执行性 | 7 | 需要新建 Wizard 组件，但 PyQt5 的 QWizard 或自定义多步对话框是成熟模式 |
| **Effort** | **3** | **5 天** |

**ROI = 7.65 / 3 = 2.55**

**具体措施:**

1. 创建 `app/widgets/welcome_wizard.py`，实现 4 步引导:
   - **步骤 1 -- 欢迎:** "DevLearnerAI 是什么" + 30 秒产品介绍 + "开始体验" 按钮
   - **步骤 2 -- 选择目标:** "我想学什么？" -- Python / 数据库 / C/C++ / 不确定 (推荐 Python)
   - **步骤 3 -- 配置 AI (可选):** "是否现在配置 AI 导师？" + "跳过，稍后配置" 按钮 + "什么是 API Key?" 链接
   - **步骤 4 -- 开始学习:** 自动打开用户选择的第一课 + "完成入门" 按钮
2. 在 `app/window.py` 的 `__init__` 中检测是否首次使用 (数据库无进度记录)，首次使用时自动弹出 Wizard
3. 在数据库中记录 `onboarding_completed` 标记，防止重复弹出
4. 在侧边栏添加 "重新运行入门引导" 菜单项，允许用户随时重新体验
5. 添加测试: 验证首次使用弹出、已完成不弹出、重新运行正常

**涉及文件:**
- `app/widgets/welcome_wizard.py` -- 新建
- `app/window.py` -- 集成 Wizard 触发逻辑
- `app/database.py` -- 新增 `onboarding_completed` 标记
- `tests/test_welcome_wizard.py` -- 新建

---

### #6 -- Python 课程末尾知识检查点

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 8 | 将课程从 "可阅读" 升级为 "可交互" 的最小可行步骤 |
| 紧迫度 | 7 | 内容质量维度 L2 升 L3 的关键差距: 无测验 = 学了不知道会不会 |
| 可复用性 | 8 | 检查点框架可复用到所有 8 条技术栈路线的所有课程 |
| 可执行性 | 7 | 需要新增题库 JSON + UI 组件 + 数据追踪，但技术路径清晰 |
| **Effort** | **4** | **7 天** |

**ROI = 7.55 / 4 = 1.89**

**具体措施:**

1. 设计检查点数据结构，扩展 `content/metadata/course_map.json`，为每节课添加 `checkpoints` 字段:
   ```json
   {
     "checkpoints": [
       {
         "type": "choice",
         "question": "Python 中哪个关键字用于定义函数？",
         "options": ["def", "function", "func", "define"],
         "answer": 0,
         "explanation": "Python 使用 def 关键字定义函数。"
       }
     ]
   }
   ```
2. 为 Python 前 20 节课程 (覆盖基础到中级) 编写每课 3-5 道检查点题目 (选择题 + 填空题)
3. 创建 `app/widgets/checkpoint.py` 检查点组件:
   - 在课程阅读页面底部显示 "知识检查" 区域
   - 选择题: 4 选 1，即时反馈 + 解释
   - 填空题: 输入框 + 提交验证
   - 通过率统计: 显示 "3/5 道正确"
4. 在 `app/database.py` 中添加 `checkpoint_results` 表记录答题数据
5. 将检查点通过率与 SM-2 间隔复习联动: 错题自动加入复习队列

**涉及文件:**
- `content/metadata/course_map.json` -- 扩展结构
- `content/python/` -- 前 20 节课程的检查点题目
- `app/widgets/checkpoint.py` -- 新建
- `app/widgets/learn.py` -- 集成检查点
- `app/database.py` -- 新增 checkpoint_results 表
- `tests/test_checkpoint.py` -- 新建

---

### #7 -- 练习后 AI 自动分析反馈

| 维度 | 分数 | 理由 |
|------|------|------|
| 影响力 | 7 | 将 AI 从 "被动聊天框" 变为 "主动导师" 的最小可行步骤 |
| 紧迫度 | 7 | AI 维度 L2 升 L3 的核心差距: AI 必须主动提供建议而非等用户提问 |
| 可复用性 | 9 | 这个机制可扩展到: 错题分析、弱点诊断、自适应推荐、代码审查 -- 是整个 AI 导师架构的基础 |
| 可执行性 | 7 | 需要后端 prompt 设计 + 前端触发逻辑，但 AI 模块已完成架构拆分 |
| **Effort** | **3** | **5 天** |

**ROI = 7.45 / 3 = 2.48**

**具体措施:**

1. 在 `app/ai/` 下新建 `auto_feedback.py` 模块:
   - `build_analysis_prompt(exercise, user_code, result)` -- 根据练习题目、用户代码、评测结果构建分析 prompt
   - `request_auto_analysis(exercise, code, result, api_client)` -- 非阻塞调用 AI API 获取分析
2. Prompt 设计 (关键):
   - System: "你是一个编程导师。学生刚完成一道练习，请分析他们的代码并给出具体的改进建议。"
   - User: "题目: {exercise.question}\n学生代码:\n```\n{user_code}\n```\n评测结果: {result.feedback}\n分数: {result.score}"
   - 要求 AI 返回: 错误原因分析 + 改进方向 + 相关知识点链接
3. 在 `app/widgets/practice.py` 的评测结果展示区域:
   - 评测完成后，如果用户已配置 AI API，自动发起分析请求
   - 结果区域下方新增 "AI 分析" 折叠面板，显示加载动画 -> 分析结果 (Markdown 渲染)
   - 用户未配置 API Key 时，显示 "配置 AI 导师以获得代码分析" 提示 + 配置入口链接
4. 缓存策略: 对相同 (exercise_id, code_hash) 的分析结果缓存 24 小时，避免重复 API 调用
5. 超时控制: 分析请求 10 秒超时，超时后显示 "分析请求超时，可稍后重试"

**涉及文件:**
- `app/ai/auto_feedback.py` -- 新建
- `app/widgets/practice.py` -- 集成自动分析 UI
- `app/ai/api_client.py` -- 可能需要添加低优先级请求通道
- `tests/test_auto_feedback.py` -- 新建

---

## 总览

| 排名 | 改进项 | 影响力 | 紧迫度 | 可复用性 | 可执行性 | Effort (天) | ROI |
|------|--------|--------|--------|----------|----------|-------------|-----|
| 1 | C/C++/C# 评测诚实化 | 8 | 10 | 7 | 9 | 2 | **8.75** |
| 2 | GitHub 社区基础设施 | 7 | 8 | 8 | 10 | 1 | **8.15** |
| 3 | GitHub Release 安装包 | 9 | 9 | 8 | 7 | 3 | **4.33** |
| 4 | 空状态仪表盘改造 | 8 | 9 | 6 | 9 | 3 | **4.03** |
| 5 | 新用户入门引导 | 8 | 8 | 7 | 7 | 5 | **2.55** |
| 6 | 练习后 AI 自动分析 | 7 | 7 | 9 | 7 | 5 | **2.48** |
| 7 | Python 知识检查点 | 8 | 7 | 8 | 7 | 7 | **1.89** |

**总 Effort: 26 人天** (约 5 周单人全职，或 2 周双人并行)

---

## 执行顺序与依赖关系

```
Week 1 (Day 1-5):
  [并行] #4 GitHub 社区基础设施 (1 天)
  [并行] #1 C/C++/C# 评测诚实化 (2 天)
  [串行] #2 GitHub Release 安装包 (3 天) -- 依赖 #4 的 SECURITY.md

Week 2 (Day 6-10):
  [并行] #3 空状态仪表盘改造 (3 天)
  [并行] #5 新用户入门引导 (5 天)

Week 3 (Day 11-15):
  [并行] #7 练习后 AI 自动分析 (5 天)
  [串行] #6 Python 知识检查点 (7 天) -- 可与 #7 并行启动

Week 4 (Day 16-20):
  [收尾] #6 Python 知识检查点 (继续)
  [验证] 全量回归测试 + 发布 v1.2.0
```

---

## 预期成熟度提升

执行完 TOP 7 后，预计各维度的变化:

| 维度 | 执行前 | 执行后 | 涉及改进项 |
|------|--------|--------|-----------|
| 产品定义与定位 | L2 | L2+ | -- (需要用户验证) |
| 核心功能完成度 | L2 | L2+ | #1, #6 |
| 用户体验 | L2 | **L3** | #3, #5 |
| AI/智能化能力 | L2 | L2+ | #7 |
| 内容质量与深度 | L2 | L2+ | #6 |
| 工程质量与架构 | L3 | L3 | -- |
| 安全与数据完整性 | L3 | L3 | -- |
| 分发与增长 | L1 | **L2** | #2, #4 |
| 商业化能力 | L1 | L1 | -- (需要定价策略) |

**加权总分: L2.0 -> L2.3** (用户体验和分发增长各升一级)

---

## 与 CodeHelper 优先级框架的对齐

本清单与 CodeHelper 使用相同的优先级框架:

1. **消灭 L1 维度优先** -- 分发与增长从 L1 升 L2 (#2, #4)
2. **解决发布阻塞项** -- 评测诚实化 (#1)、安装包 (#2)、入门引导 (#5)
3. **高 ROI 快速胜利先行** -- #1 (2 天/ROI 8.75) 和 #4 (1 天/ROI 8.15) 应在第一周完成
4. **解锁后续功能的基础设施** -- #6 (检查点框架) 和 #7 (AI 自动分析) 是后续自适应学习、弱点诊断的基石
5. **投入产出比量化** -- 每项都经过 Impact/Urgency/Leverage/Feasibility 四维打分，非主观排序

---

## 风险与缓解

| 风险 | 概率 | 缓解措施 |
|------|------|----------|
| PyInstaller 打包产物无法在无 Python 环境运行 | 30% | 提前在干净虚拟机测试，CI 中添加 smoke test |
| AI 自动分析增加 API 成本 | 40% | 缓存分析结果 + 限制请求频率 + 仅对未通过的练习触发 |
| 知识检查点题库质量不高 | 30% | 先做 Python 前 10 节，收集用户反馈后再扩展 |
| 入门引导流程过长导致用户中途放弃 | 20% | 4 步精简设计 + "跳过" 按钮 + 总时长控制在 2 分钟内 |
| 安装包体积过大 (>100MB) | 50% | UPX 压缩 + 排除不必要依赖 + 条件加载 |

---

*本文档应与 MATURITY_SCORECARD.md 配合使用，每个 Sprint 结束时重新评估各项改进的完成状态和成熟度等级变化。*
