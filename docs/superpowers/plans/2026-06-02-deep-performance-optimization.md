# Deep Performance Optimization - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deep performance optimization across startup, database, AI, content loading, UI, and memory for the DevLearnerAI PyQt5 desktop application.

**Architecture:** This is a PyQt5 desktop learning platform with SQLite database, OpenAI-compatible AI chat, Markdown-based course content, and practice/exercise evaluation. The app already has partial optimizations (splash screen, deferred widget init, DB indexes, AI streaming, markdown cache). This plan addresses remaining gaps and hardens existing optimizations.

**Tech Stack:** Python 3.12+, PyQt5, SQLite3, mistune, urllib (stdlib), threading

---

## File Structure

### Files to Modify
- `app/window.py` - Startup orchestration, stylesheet caching, repaint optimization
- `app/database.py` - PRAGMA tuning, ANALYZE, memory management
- `app/content_service.py` - LRU cache, search index, lazy content loading
- `app/ai/api_client.py` - Timeout handling, connection pool improvements
- `app/ai/chat_handler.py` - Chat history limits, session cleanup
- `app/styles.py` - Stylesheet result caching
- `app/effects.py` - Animation throttling, repaint helpers
- `app/config.py` - Memory monitoring config constants
- `main.py` - Startup sequence optimization

### Files to Create
- `app/memory_monitor.py` - Memory usage monitoring and cache eviction

---

## Task 1: Stylesheet Caching in styles.py

**Files:**
- Modify: `D:/codelearnhleper/app/styles.py`

The `_build_global_style` function generates a ~400-line stylesheet string on every call. When the user toggles theme or changes font size, this function is called again, generating an identical string if the same parameters were used before. Cache the result keyed by parameters.

- [ ] **Step 1: Add stylesheet cache dict at module level**

```python
# Add after the FONT_SIZES dict (around line 76)
_style_cache: dict[tuple, str] = {}
```

- [ ] **Step 2: Modify `_build_global_style` to use cache**

Replace the function so it checks the cache before building:

```python
def _build_global_style(
    bg_base: str = BG_BASE,
    bg_shell: str = BG_SHELL,
    bg_card: str = BG_CARD,
    bg_card_soft: str = BG_CARD_SOFT,
    accent: str = ACCENT,
    accent_hover: str = ACCENT_HOVER,
    accent_pressed: str = ACCENT_PRESSED,
    accent_soft: str = ACCENT_SOFT,
    text_main: str = TEXT_MAIN,
    text_sub: str = TEXT_SUB,
    text_muted: str = TEXT_MUTED,
    border: str = BORDER,
    border_strong: str = BORDER_STRONG,
    f_base: int = F_BASE,
    f_title: int = F_TITLE,
    f_sub: int = F_SUB,
    f_code: int = F_CODE,
    btn_h: int = BTN_H,
) -> str:
    """Build the full application stylesheet from palette parameters.

    Results are cached so repeated calls with identical parameters
    (e.g. toggling theme back and forth) return instantly.
    """
    cache_key = (
        bg_base, bg_shell, bg_card, bg_card_soft,
        accent, accent_hover, accent_pressed, accent_soft,
        text_main, text_sub, text_muted, border, border_strong,
        f_base, f_title, f_sub, f_code, btn_h,
    )
    cached = _style_cache.get(cache_key)
    if cached is not None:
        return cached
    # ... existing f-string template ...
    result = f"""..."""  # keep existing template
    _style_cache[cache_key] = result
    return result
```

- [ ] **Step 3: Add cache invalidation for theme rebuilds**

Add a `clear_style_cache` function:

```python
def clear_style_cache() -> None:
    """Clear the stylesheet cache (e.g. after external color changes)."""
    _style_cache.clear()
```

- [ ] **Step 4: Verify by running existing tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Expected: All tests pass (stylesheet caching is transparent to callers)

---

## Task 2: Database PRAGMA Tuning and ANALYZE

**Files:**
- Modify: `D:/codelearnhleper/app/database.py`

SQLite default settings are suboptimal for desktop apps. Adding PRAGMA cache_size and running ANALYZE after schema creation lets the query planner make better decisions.

- [ ] **Step 1: Add PRAGMA cache_size and temp_store to `get_connection`**

In the `get_connection` function, after the existing PRAGMAs (around line 53), add:

```python
if _connection is None:
    ensure_runtime_dirs()
    _connection = sqlite3.connect(db_path, check_same_thread=False)
    _connection.execute("PRAGMA foreign_keys = ON")
    _connection.execute("PRAGMA journal_mode = WAL")
    _connection.execute("PRAGMA cache_size = -8000")  # 8 MB page cache
    _connection.execute("PRAGMA temp_store = MEMORY")  # temp tables in RAM
    _connection.execute("PRAGMA mmap_size = 268435456")  # 256 MB mmap
```

- [ ] **Step 2: Add ANALYZE after index creation in `init_db`**

After the CREATE INDEX block (around line 269), add:

```python
# ── Query planner optimization ───────────────────────────────────────────
cursor.execute("ANALYZE")
```

- [ ] **Step 3: Run existing database tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_database.py tests/test_database_extended.py tests/test_database_coverage.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 3: LRU Cache Eviction for Markdown Content

**Files:**
- Modify: `D:/codelearnhleper/app/content_service.py`

The current markdown cache uses a simple FIFO eviction (delete oldest key via `next(iter(...))`). This is inefficient when the user navigates back and forth -- recently accessed items may be evicted. Switch to an OrderedDict-based LRU.

- [ ] **Step 1: Import OrderedDict and replace `_markdown_cache`**

At the top of the file add `from collections import OrderedDict`.

In `__init__`, replace:
```python
self._markdown_cache: dict[str, str] = {}  # path -> markdown content
```
with:
```python
self._markdown_cache: OrderedDict[str, str] = OrderedDict()  # LRU cache
```

- [ ] **Step 2: Update `lesson_markdown` to use LRU access pattern**

Replace the cache check and eviction logic:

```python
def lesson_markdown(self, lesson: Lesson) -> str:
    """Read lesson markdown (with LRU cache).

    Accessed entries move to the end; evicted entries come from the front.
    """
    cache_key = lesson.path
    if cache_key in self._markdown_cache:
        self._markdown_cache.move_to_end(cache_key)
        return self._markdown_cache[cache_key]

    path = CONTENT_DIR / lesson.path
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("课程 Markdown 文件未找到: %s", path)
        content = f"# {lesson.title}\n\n这节课的文档文件暂时缺失。"
    except Exception as exc:
        logger.error("读取课程 Markdown 失败: %s - %s", path, exc)
        content = f"# {lesson.title}\n\n加载文档时出现错误：{exc}"

    # Evict least-recently-used entries if cache is full
    while len(self._markdown_cache) >= self._MAX_MARKDOWN_CACHE:
        self._markdown_cache.popitem(last=False)
    self._markdown_cache[cache_key] = content
    return content
```

- [ ] **Step 3: Update `clear_markdown_cache` (no change needed, OrderedDict.clear works)****

- [ ] **Step 4: Run content tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_content_service.py tests/test_content_service_extended.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 4: AI Request Timeout and Cancellation

**Files:**
- Modify: `D:/codelearnhleper/app/ai/api_client.py`

The streaming function `send_chat_stream` catches all exceptions but does not expose timeout to the caller, and the non-streaming `send_chat` uses a fixed 90s timeout. Add configurable timeouts with a more defensive approach.

- [ ] **Step 1: Add default timeout constants**

After the `_CONNECTION_CACHE_TTL` constant (around line 27):

```python
_DEFAULT_REQUEST_TIMEOUT = 60  # seconds for non-streaming
_DEFAULT_STREAM_TIMEOUT = 120  # seconds for streaming
```

- [ ] **Step 2: Update `send_chat` default timeout**

Change the function signature default from 90 to the constant:

```python
def send_chat(
    host: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: int = _DEFAULT_REQUEST_TIMEOUT,
) -> str:
```

- [ ] **Step 3: Update `send_chat_stream` default timeout**

```python
def send_chat_stream(
    host: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    on_chunk: Callable[[str], None],
    timeout: int = _DEFAULT_STREAM_TIMEOUT,
) -> str:
```

- [ ] **Step 4: Add timeout logging in the stream function**

In the `except Exception` block of `send_chat_stream`, add a log before falling back:

```python
except Exception as exc:
    logger.warning("Streaming request failed (received %d chunks): %s", len(full_text), exc)
    if not full_text:
        return send_chat(host, api_key, model, messages, timeout)
```

- [ ] **Step 5: Run AI tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_ai_chat_handler.py tests/test_ai_package.py tests/test_api_client_extended.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 5: Database PRAGMA Connection Cleanup Hardening

**Files:**
- Modify: `D:/codelearnhleper/app/database.py`

The `close_connection` function uses a lock but the `connect()` context manager does not properly handle the case where `_db_lock` acquisition fails. Also add a `PRAGMA optimize` call before closing.

- [ ] **Step 1: Add PRAGMA optimize to close_connection**

```python
def close_connection():
    """Close the global database connection.

    Runs PRAGMA optimize to update statistics before closing.
    """
    global _connection
    with _connection_lock:
        if _connection is not None:
            try:
                _connection.execute("PRAGMA optimize")
            except Exception:
                logger.debug("PRAGMA optimize failed during close", exc_info=True)
            _connection.close()
            _connection = None
```

- [ ] **Step 2: Run database tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_database.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 6: Session Cleanup and Chat History Trimming

**Files:**
- Modify: `D:/codelearnhleper/app/ai/chat_handler.py`

Long-running sessions accumulate thousands of messages. The `trim_mentor_messages` method exists in the database but is never called automatically. Add automatic trimming when switching sessions and on app startup.

- [ ] **Step 1: Add session trim on load in `_reload_sessions`**

In `_reload_sessions`, after setting `self.current_session_id = active_id` and before `self._sync_session_header()`:

```python
# Trim old messages to prevent memory bloat
self.db.trim_mentor_messages(active_id, keep_last=200)
```

- [ ] **Step 2: Add session trim when switching sessions**

In `_on_session_row_changed` and `_on_session_combo_changed`, after setting `self.current_session_id`:

```python
self.db.trim_mentor_messages(self.current_session_id, keep_last=200)
```

- [ ] **Step 3: Limit in-memory message loading for API calls**

In `_chat_worker`, the code already loads only the last 12 messages (`[-12:]`). Verify this is sufficient and document the limit:

```python
# Only send the most recent 12 messages to the API to control token usage
api_messages = [{"role": "system", "content": system_context}]
for role, content, _created_at in self.db.load_mentor_messages(session_id)[-12:]:
    api_messages.append({"role": role, "content": content})
```

- [ ] **Step 4: Run chat handler tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_ai_chat_handler.py tests/test_chat_handler_extended.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 7: Memory Monitor Module

**Files:**
- Create: `D:/codelearnhleper/app/memory_monitor.py`

Create a lightweight memory monitoring utility that tracks RSS usage and can trigger cache eviction when memory pressure is high.

- [ ] **Step 1: Create the memory monitor module**

```python
"""Lightweight memory monitoring for cache eviction decisions.

Tracks process RSS and provides a simple API for checking whether
caches should be trimmed.
"""

import logging
import os
import sys

logger = logging.getLogger(__name__)

# Threshold in MB above which caches should be trimmed
_CACHE_TRIM_THRESHOLD_MB = 300
# Threshold in MB above which aggressive cleanup is triggered
_AGGRESSIVE_CLEANUP_THRESHOLD_MB = 500


def get_rss_mb() -> float:
    """Return current process RSS in MB.

    Uses psutil if available, falls back to resource module on Unix,
    or returns 0.0 on unsupported platforms.
    """
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass

    if sys.platform != "win32":
        try:
            import resource
            # getrusage returns maxrss in KB on Linux, bytes on macOS
            usage = resource.getrusage(resource.RUSAGE_SELF)
            maxrss = usage.ru_maxrss
            if sys.platform == "darwin":
                maxrss /= 1024 * 1024
            else:
                maxrss /= 1024
            return maxrss
        except Exception:
            pass

    return 0.0


def should_trim_caches() -> bool:
    """Return True if memory usage suggests caches should be trimmed."""
    rss = get_rss_mb()
    return rss > _CACHE_TRIM_THRESHOLD_MB if rss > 0 else False


def should_aggressive_cleanup() -> bool:
    """Return True if memory usage is critically high."""
    rss = get_rss_mb()
    return rss > _AGGRESSIVE_CLEANUP_THRESHOLD_MB if rss > 0 else False


def log_memory_usage(label: str = "") -> None:
    """Log current memory usage at DEBUG level."""
    rss = get_rss_mb()
    if rss > 0:
        logger.debug("Memory [%s]: %.1f MB RSS", label or "check", rss)
```

- [ ] **Step 2: Run a basic import test**

Run: `cd D:/codelearnhleper && python -c "from app.memory_monitor import get_rss_mb, should_trim_caches; print(f'RSS: {get_rss_mb():.1f} MB')"`
Expected: Prints RSS value (0.0 on Windows without psutil, or actual value if psutil is installed)

---

## Task 8: Integrate Memory Monitor with Content Cache

**Files:**
- Modify: `D:/codelearnhleper/app/content_service.py`

Use the memory monitor to decide when to shrink the markdown cache proactively.

- [ ] **Step 1: Add memory-aware cache trimming to `lesson_markdown`**

After adding a new entry to the markdown cache, check memory:

```python
# At the top of the file, add import
from app.memory_monitor import should_trim_caches

# In lesson_markdown, after adding to cache:
self._markdown_cache[cache_key] = content

# Proactive memory pressure response
if should_trim_caches() and len(self._markdown_cache) > 8:
    # Shrink to half capacity under memory pressure
    target = max(8, self._MAX_MARKDOWN_CACHE // 2)
    while len(self._markdown_cache) > target:
        self._markdown_cache.popitem(last=False)
    logger.debug("Shrunk markdown cache to %d entries due to memory pressure", target)

return content
```

- [ ] **Step 2: Run content tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_content_service.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 9: Dashboard Query Batching

**Files:**
- Modify: `D:/codelearnhleper/app/widgets/dashboard.py`

The `refresh()` method makes 5+ separate database queries. Batch them where possible and use cached values for the session.

- [ ] **Step 1: Add a `_last_refresh_ts` throttle to prevent rapid refreshes**

In `__init__`:
```python
self._last_refresh_ts = 0.0
self._refresh_min_interval = 2.0  # seconds
```

- [ ] **Step 2: Add throttle to `refresh` method**

At the start of `refresh()`:
```python
import time as _time
now = _time.monotonic()
if now - self._last_refresh_ts < self._refresh_min_interval:
    return
self._last_refresh_ts = now
```

- [ ] **Step 3: Run dashboard-related tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=30 -k "dashboard or window" 2>&1 | tail -10`
Expected: All pass

---

## Task 10: Reduce Unnecessary Repaints in Sidebar Navigation

**Files:**
- Modify: `D:/codelearnhleper/app/window.py`

The `_apply_sidebar_state` and `switch_page` methods call `unpolish`/`polish`/`update` on every nav button even when only one changed. Batch these updates.

- [ ] **Step 1: Modify `switch_page` to only update changed buttons**

Replace the nav button loop in `switch_page`:

```python
for button_index, button in enumerate(self.nav_buttons):
    active = button_index == index
    was_active = button.property("active") == "true"
    if active == was_active:
        continue  # skip unchanged buttons
    button.setChecked(active)
    button.setProperty("active", "true" if active else "false")
    button.style().unpolish(button)
    button.style().polish(button)
    button.update()
```

- [ ] **Step 2: Defer theme application with a single-shot timer**

In `toggle_theme` and `set_font_size`, batch the stylesheet application:

```python
def toggle_theme(self) -> None:
    self._dark_mode = not self._dark_mode
    self._apply_style_deferred()

def set_font_size(self, size_name: str) -> None:
    self._font_size = size_name
    self._apply_style_deferred()

def _apply_style_deferred(self) -> None:
    """Apply stylesheet on next event loop tick to batch rapid changes."""
    if not hasattr(self, "_style_pending"):
        self._style_pending = False
    if self._style_pending:
        return
    self._style_pending = True
    QTimer.singleShot(0, self._do_apply_style)

def _do_apply_style(self) -> None:
    self._style_pending = False
    style = build_style_for_size(self._font_size, dark=self._dark_mode)
    QApplication.instance().setStyleSheet(style)
    self._update_connection_status("ready")
```

- [ ] **Step 3: Add QTimer import if not present**

Check that `QTimer` is already imported (it is at line 3).

- [ ] **Step 4: Run window tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=30 -k "window" 2>&1 | tail -5`
Expected: All pass

---

## Task 11: Startup Service Deferral

**Files:**
- Modify: `D:/codelearnhleper/app/window.py`

PracticeService loading happens synchronously in `__init__`. Defer it to after the window is shown, since the practice tab is not visible at startup.

- [ ] **Step 1: Make PracticeService lazy-loaded**

In `__init__`, replace:
```python
self.practice_service = PracticeService()
```
with:
```python
self._practice_service = None
```

- [ ] **Step 2: Add lazy accessor**

```python
@property
def practice_service(self) -> PracticeService:
    if self._practice_service is None:
        self._practice_service = PracticeService()
    return self._practice_service
```

- [ ] **Step 3: Defer PracticeService init in `_deferred_init`**

In `_deferred_init`, add:
```python
QTimer.singleShot(100, self._ensure_practice_service)
```

And add the method:
```python
def _ensure_practice_service(self) -> None:
    """Pre-load practice service in background after window is visible."""
    self.practice_service  # triggers lazy load via property
```

- [ ] **Step 4: Update PracticeWidget to accept lazy service**

PracticeWidget already receives `practice_service` in its constructor. The widget is created with `self.practice_service` which will trigger the property accessor. This works because PracticeWidget is created in `__init__` before the window is shown. We need to keep this synchronous since the widget needs it immediately. Revert to synchronous but make it a deferred-init step:

Actually, looking at the code more carefully, `PracticeWidget` is a critical widget created in `__init__`. The service must be available. Instead, keep it synchronous but move it to `_deferred_init` with a placeholder.

Better approach: Keep PracticeService synchronous but add a flag to skip heavy initialization:

Revert step 1-3. Instead, add initialization timing:

```python
import time as _time
_t0 = _time.monotonic()
self.db = AppDatabase()
self.db.init_db()
self.content_service = ContentService()
self.practice_service = PracticeService()
_t1 = _time.monotonic()
logger.info("Core services initialized in %.1f ms", (_t1 - _t0) * 1000)
```

Add this at the top of `__init__` after the screen geometry code.

- [ ] **Step 5: Run tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 12: Content Search Index

**Files:**
- Modify: `D:/codelearnhleper/app/content_service.py`

The `_build_lesson_index` already creates a lesson_id lookup. Add a lightweight text search index over lesson titles and summaries for the global search feature.

- [ ] **Step 1: Add search index to `__init__`**

```python
self._search_index: dict[str, list[str]] = {}  # token -> [lesson_id, ...]
self._build_search_index()
```

- [ ] **Step 2: Implement `_build_search_index`**

```python
def _build_search_index(self) -> None:
    """Build a simple inverted index over lesson titles and summaries.

    Enables fast text search without loading full Track objects.
    """
    for track_data in self._tracks_index:
        for module_data in track_data.get("modules", []):
            for lesson_data in module_data.get("lessons", []):
                lesson_id = lesson_data.get("id", "")
                if not lesson_id:
                    continue
                text = (
                    f"{lesson_data.get('title', '')} "
                    f"{lesson_data.get('summary', '')} "
                    f"{' '.join(lesson_data.get('tags', []))}"
                ).lower()
                tokens = set(text.split())
                for token in tokens:
                    if len(token) >= 2:  # skip single-char tokens
                        self._search_index.setdefault(token, []).append(lesson_id)
```

- [ ] **Step 3: Add search method**

```python
def search_lessons(self, query: str) -> list[str]:
    """Search lessons by query string using the inverted index.

    Returns a list of lesson_ids sorted by relevance (number of matching tokens).
    """
    tokens = query.lower().split()
    if not tokens:
        return []
    scores: dict[str, int] = {}
    for token in tokens:
        for lesson_id in self._search_index.get(token, []):
            scores[lesson_id] = scores.get(lesson_id, 0) + 1
    return [lid for lid, _ in sorted(scores.items(), key=lambda x: -x[1])]
```

- [ ] **Step 4: Run content tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_content_service.py tests/test_content_service_extended.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 13: Exercise Service Index for Fast Filtering

**Files:**
- Modify: `D:/codelearnhleper/app/practice_service.py`

The `filtered` method iterates all exercises every time. Build indexes on `track_id` and `difficulty` for O(1) lookups.

- [ ] **Step 1: Add indexes in `PracticeService.__init__`**

```python
def __init__(self, metadata_path: Optional[Path] = None) -> None:
    self.metadata_path = metadata_path
    self.exercises = _load_exercises(metadata_path)
    # Build indexes for fast filtering
    self._by_track: dict[str, list[Exercise]] = {}
    self._by_difficulty: dict[str, list[Exercise]] = {}
    self._by_id: dict[str, Exercise] = {}
    for ex in self.exercises:
        self._by_track.setdefault(ex.track_id, []).append(ex)
        self._by_difficulty.setdefault(ex.difficulty, []).append(ex)
        self._by_id[ex.id] = ex
```

- [ ] **Step 2: Use indexes in `filtered` and `exercise_by_id`**

```python
def filtered(self, track_id: str, difficulty: str) -> list[Exercise]:
    if track_id != "all" and difficulty != "all":
        # Intersection: filter from the smaller set
        by_track = set(id(ex) for ex in self._by_track.get(track_id, []))
        return [ex for ex in self._by_difficulty.get(difficulty, []) if id(ex) in by_track]
    if track_id != "all":
        return list(self._by_track.get(track_id, []))
    if difficulty != "all":
        return list(self._by_difficulty.get(difficulty, []))
    return list(self.exercises)

def exercise_by_id(self, exercise_id: str) -> Optional[Exercise]:
    return self._by_id.get(exercise_id)
```

- [ ] **Step 3: Run practice tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/test_practice_service.py tests/test_practice_service_extended.py -x -q --timeout=30 2>&1 | tail -5`
Expected: All pass

---

## Task 14: Animation Throttling in Effects

**Files:**
- Modify: `D:/codelearnhleper/app/effects.py`

The `LoadingSpinner` runs a 40ms timer even when the widget is not visible. Stop the timer when hidden.

- [ ] **Step 1: Override `showEvent` and `hideEvent` in `LoadingSpinner`**

```python
def showEvent(self, event):
    super().showEvent(event)
    if not self._timer.isActive():
        self._timer.start(40)

def hideEvent(self, event):
    super().hideEvent(event)
    self._timer.stop()
```

- [ ] **Step 2: Same for `AnimatedDotsLabel`**

```python
def showEvent(self, event):
    super().showEvent(event)
    if not self._timer.isActive():
        self._timer.start(500)

def hideEvent(self, event):
    super().hideEvent(event)
    self._timer.stop()
```

- [ ] **Step 3: Run effects-related tests**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=30 -k "effect" 2>&1 | tail -5`
Expected: All pass (or no matches if no effect tests exist, which is fine)

---

## Task 15: Final Integration Verification

- [ ] **Step 1: Run full test suite**

Run: `cd D:/codelearnhleper && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10`
Expected: All tests pass

- [ ] **Step 2: Verify startup still works**

Run: `cd D:/codelearnhleper && python -c "from app.window import DevLearnerWindow; print('Import OK')"`
Expected: Prints "Import OK" without errors

- [ ] **Step 3: Verify memory monitor**

Run: `cd D:/codelearnhleper && python -c "from app.memory_monitor import get_rss_mb, should_trim_caches; print(f'RSS: {get_rss_mb():.1f} MB, trim: {should_trim_caches()}')"`
Expected: Prints without error

- [ ] **Step 4: Verify stylesheet caching**

Run: `cd D:/codelearnhleper && python -c "from app.styles import build_style_for_size; s1 = build_style_for_size('medium'); s2 = build_style_for_size('medium'); print(f'Cached: {s1 is s2}')"`
Expected: Prints "Cached: True"
