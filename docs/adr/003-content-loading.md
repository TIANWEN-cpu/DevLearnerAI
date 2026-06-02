# ADR-003: 课程内容加载机制

## 状态

已采纳

## 背景

DevLearnerAI 包含大量课程内容（多个技术栈、数十个模块、数百节课），每节课对应一个 Markdown 文件。需要设计合理的内容加载策略，平衡以下需求：

- **启动速度**: 应用启动不能因加载所有课程内容而变慢
- **内存占用**: 不能将所有内容常驻内存
- **响应速度**: 用户切换课程时需要即时渲染
- **数据完整性**: 需要处理编码损坏、文件缺失等异常情况

## 决策

采用 **索引预加载 + Track 懒加载 + Markdown LRU 缓存 + 相邻预加载** 的分层策略。

## 理由

### 备选方案对比

| 方案 | 说明 | 优缺点 |
|------|------|--------|
| **A: 索引 + 懒加载 + 缓存** (采纳) | 分层加载，按需缓存 | 启动快，内存可控，响应好 |
| B: 全量预加载 | 启动时加载所有内容到内存 | 响应最快，但启动慢、内存大 |
| C: 每次从磁盘读取 | 无缓存，每次都读文件 | 内存最小，但响应慢 |
| D: SQLite 存储内容 | 将 Markdown 存入数据库 | 增加数据库复杂度，不利于编辑 |

### 选择方案 A 的理由

1. **三级数据分离**: 将数据分为元数据索引、Track 对象、Markdown 内容三个层次，各层独立加载和缓存。

```text
第 1 层: 元数据索引 (启动时加载，约 50KB JSON)
  → 仅包含 Track/Module/Lesson 的 ID 和路径信息
  → 构建 lesson_id → (track_id, module_id) 的 O(1) 索引

第 2 层: Track 对象 (首次访问时按需构建，约 1-5KB/个)
  → 完整的 Track/Module/Lesson 数据模型
  → 使用字典缓存，避免重复构建

第 3 层: Markdown 内容 (首次读取时缓存，约 2-10KB/个)
  → 实际课程文本内容
  → LRU 缓存，上限 64 个文件，FIFO 淘汰
```

2. **O(1) 课程查找**: 通过预构建的 `_lesson_index` 字典，任何课程 ID 都能在 O(1) 时间定位到所属的 Track 和 Module，仅需加载目标 Track。

3. **Markdown 缓存**: 使用简单的 FIFO 淘汰策略（最多缓存 64 个文件），在内存占用和响应速度之间取得平衡。64 个文件约占用 300KB-600KB 内存。

4. **相邻课程预加载**: 打开某节课时，自动预加载前一课和后一课的 Markdown 到缓存，这样用户翻页时几乎无延迟。

5. **编码损坏自愈**: 对所有文本字段进行损坏检测，使用回退值替代损坏内容，确保应用不会因历史数据问题而崩溃。

## 实现细节

### 启动时的加载量

```python
class ContentService:
    def __init__(self):
        self._tracks_index = self._discover_tracks()   # 读取 course_map.json (~50KB)
        self._lesson_index = {}                         # 构建 ID 索引 (~5KB)
        self._cache = {}                                # Track 对象缓存 (空)
        self._markdown_cache = {}                       # Markdown 缓存 (空)
```

启动时仅加载 JSON 索引（~50KB），不构建任何 Track 对象，不读取任何 Markdown 文件。

### 按需加载

```python
def track_by_id(self, track_id: str) -> Optional[Track]:
    for td in self._tracks_index:
        if td.get("id") == track_id:
            return self._load_track(td)  # 首次访问时构建 Track 对象
    return None

def _load_track(self, track_data: dict) -> Track:
    track_id = track_data.get("id")
    if track_id not in self._cache:
        self._cache[track_id] = self._build_track(track_data)
    return self._cache[track_id]
```

### 缓存淘汰

```python
_MAX_MARKDOWN_CACHE = 64

def lesson_markdown(self, lesson: Lesson) -> str:
    if lesson.path in self._markdown_cache:
        return self._markdown_cache[lesson.path]

    content = (CONTENT_DIR / lesson.path).read_text(encoding="utf-8")

    # FIFO 淘汰
    if len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
        oldest_key = next(iter(self._markdown_cache))
        del self._markdown_cache[oldest_key]

    self._markdown_cache[lesson.path] = content
    return content
```

## 影响

### 正面影响

- 应用启动时间不受课程数量影响
- 内存占用可预测（最大约 600KB Markdown 缓存 + Track 对象）
- 课程切换延迟可控（缓存命中时即时响应）
- 前后课程预加载减少了翻页等待

### 负面影响

- 首次访问某个 Track 时有轻微延迟（~50ms，构建 Track 对象）
- FIFO 淘汰策略不如 LRU 精确（可能淘汰频繁使用的文件）
- 缓存大小硬编码为 64，未提供配置接口

### 可能的改进

- 使用 `collections.OrderedDict` 实现真正的 LRU 淘汰
- 将缓存大小暴露为配置项
- 添加异步预加载机制（在后台线程预加载热门课程）

## 相关文档

- [课程内容体系](../concepts/content-system.md) - 三级层次结构设计
- [内容文件格式](../reference/content-format.md) - course_map.json 格式
- [内容问题排查](../troubleshooting/content-issues.md) - 常见问题
