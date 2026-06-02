# ADR-001: 选择 PyQt5 作为 GUI 框架

## 状态

已采纳

## 背景

DevLearnerAI 是一款桌面编程学习平台，需要选择合适的 GUI 框架。候选方案包括：

1. **PyQt5** - Qt 的 Python 绑定
2. **Tkinter** - Python 标准库自带
3. **Electron + Web** - 基于浏览器的桌面方案
4. **Dear PyGui** - 即时模式 GUI
5. **wxPython** - 跨平台 GUI

## 决策

选择 **PyQt5** 作为 GUI 框架。

## 理由

### 选择 PyQt5 的原因

1. **成熟的组件体系**: PyQt5 提供了丰富的原生组件（QStackedWidget、QDockWidget、QScrollArea 等），可以直接构建复杂的多页面布局，无需从零开发。

2. **样式灵活性**: 通过 QSS（Qt Style Sheets）可以实现精细的样式控制，支持亮色/暗色主题切换、字号调整等需求。项目中的 `styles.py` 展示了完整的主题管理系统。

3. **信号与槽机制**: Qt 的信号与槽（Signal/Slot）机制提供了松耦合的组件通信方式，非常适合 Widget 间的事件传递（如 Dashboard 的 `navigate_requested` 信号）。

4. **文档和社区**: Qt 拥有超过 20 年的积累，文档完善，社区活跃，遇到问题容易找到解决方案。

5. **跨平台潜力**: 虽然当前主要面向 Windows，但 PyQt5 本身支持 macOS 和 Linux，为未来扩展保留了可能性。

6. **性能**: 原生渲染，启动速度快，内存占用合理。配合延迟初始化策略，可以在 1 秒内完成启动。

### 淘汰其他方案的原因

| 方案 | 淘汰原因 |
|------|---------|
| Tkinter | 组件不够丰富，样式控制能力弱，难以实现现代化 UI |
| Electron | 内存占用大（Chromium 运行时），启动慢，与 Python 后端集成需要额外 IPC |
| Dear PyGui | 即时模式不适合复杂的表单/文本编辑场景 |
| wxPython | 社区活跃度下降，新版本发布节奏慢 |

## 影响

### 正面影响

- 快速构建了多页面导航、代码编辑器、Markdown 渲染器等复杂 UI
- QSS 实现了完整的亮色/暗色主题和字号调整
- QDockWidget 实现了 AI 助手的侧边停靠面板
- QTextBrowser 支持富文本渲染，用于课程内容和 AI 响应展示

### 负面影响

- PyQt5 的安装包较大（约 70MB），增加了分发体积
- 测试环境需要 Mock PyQt5（见 `tests/conftest.py`），增加了测试复杂度
- 部分功能（如 Windows Credential Manager）需要平台特定代码

### 缓解措施

- 使用 PyInstaller 打包时，通过 `--exclude-module` 排除不需要的 Qt 模块减小体积
- `conftest.py` 提供了完整的 PyQt5 MagicMock，核心逻辑测试可在无 GUI 环境运行
- 凭证管理模块实现了三级回退（WCM → keyring → Base64 文件）

## 相关文档

- [Widget 系统](../concepts/widget-system.md) - PyQt5 组件层次详情
- [系统架构](../concepts/architecture.md) - 整体架构设计
