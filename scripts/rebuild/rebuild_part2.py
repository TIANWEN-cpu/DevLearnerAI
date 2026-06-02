"""Rebuild C, C#, Database, Algorithms, Integration tracks."""

import json
import os

BASE = r"D:\codelearnhleper\content"


def load():
    with open(os.path.join(BASE, "metadata", "course_map.json"), encoding="utf-8") as f:
        return json.load(f)


def save(data):
    with open(os.path.join(BASE, "metadata", "course_map.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load()

# Remove old tracks
for tid in ["c", "csharp", "database", "algorithms", "integration"]:
    data["tracks"] = [t for t in data["tracks"] if t["id"] != tid]

# ============================================================
# C TRACK
# ============================================================
data["tracks"].append(
    {
        "id": "c",
        "title": "C 语言路线",
        "icon": "\u2699\ufe0f",
        "summary": "从语法到系统编程，理解计算机底层运行机制。",
        "modules": [
            {
                "id": "c-foundations",
                "title": "基础模块 \u00b7 语法与编译",
                "summary": "掌握 C 语言基础语法、编译流程和指针基础。",
                "lessons": [
                    {
                        "id": "c-thinking-setup",
                        "title": "C 语言学习地图与环境准备",
                        "summary": "理解 C 语言的定位、编译流程和开发环境搭建。",
                        "path": "c/c_thinking_setup.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 25,
                        "tags": ["\u73af\u5883", "\u7f16\u8bd1", "\u5165\u95e8"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3 C \u8bed\u8a00\u7684\u5e94\u7528\u573a\u666f",
                            "\u4f1a\u642d\u5efa C \u5f00\u53d1\u73af\u5883",
                            "\u77e5\u9053\u7f16\u8bd1\u5230\u94fe\u63a5\u7684\u5b8c\u6574\u6d41\u7a0b",
                        ],
                    },
                    {
                        "id": "c-syntax-basics",
                        "title": "\u57fa\u7840\u8bed\u6cd5\u4e0e\u63a7\u5236\u6d41",
                        "summary": "\u638c\u63e1\u53d8\u91cf\u3001\u8fd0\u7b97\u7b26\u3001\u6761\u4ef6\u8bed\u53e5\u548c\u5faa\u73af\u3002",
                        "path": "c/c_syntax_basics.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u8bed\u6cd5", "\u63a7\u5236\u6d41", "\u5faa\u73af"],
                        "prerequisites": ["c-thinking-setup"],
                        "outcomes": [
                            "\u4f1a\u5199\u5b8c\u6574\u7684 C \u7a0b\u5e8f",
                            "\u638c\u63e1 if/for/while/switch",
                            "\u7406\u89e3\u51fd\u6570\u5b9a\u4e49\u548c\u8c03\u7528",
                        ],
                    },
                    {
                        "id": "c-arrays-strings",
                        "title": "\u6570\u7ec4\u4e0e\u5b57\u7b26\u4e32",
                        "summary": "\u7406\u89e3\u6570\u7ec4\u7684\u5185\u5b58\u5e03\u5c40\u548c C \u98ce\u683c\u5b57\u7b26\u4e32\u64cd\u4f5c\u3002",
                        "path": "c/c_arrays_strings.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u6570\u7ec4", "\u5b57\u7b26\u4e32", "\u5185\u5b58"],
                        "prerequisites": ["c-syntax-basics"],
                        "outcomes": [
                            "\u7406\u89e3\u6570\u7ec4\u5728\u5185\u5b58\u4e2d\u7684\u8fde\u7eed\u5b58\u50a8",
                            "\u4f1a\u64cd\u4f5c C \u98ce\u683c\u5b57\u7b26\u4e32",
                            "\u77e5\u9053\u5b57\u7b26\u4e32\u51fd\u6570\u7684\u7528\u6cd5",
                        ],
                    },
                    {
                        "id": "c-pointers",
                        "title": "\u6307\u9488\u57fa\u7840",
                        "summary": "\u7406\u89e3\u6307\u9488\u7684\u672c\u8d28\u3001\u6307\u9488\u7b97\u672f\u548c\u6307\u9488\u4e0e\u6570\u7ec4\u7684\u5173\u7cfb\u3002",
                        "path": "c/c_pointers.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u6307\u9488", "\u5730\u5740", "\u7b97\u672f"],
                        "prerequisites": ["c-arrays-strings"],
                        "outcomes": [
                            "\u7406\u89e3\u6307\u9488\u5c31\u662f\u5730\u5740",
                            "\u4f1a\u8fdb\u884c\u6307\u9488\u7b97\u672f\u8fd0\u7b97",
                            "\u7406\u89e3\u6307\u9488\u548c\u6570\u7ec4\u7684\u5173\u7cfb",
                        ],
                    },
                    {
                        "id": "c-functions-scope",
                        "title": "\u51fd\u6570\u3001\u4f5c\u7528\u57df\u4e0e\u5b58\u50a8\u7c7b",
                        "summary": "\u7406\u89e3\u51fd\u6570\u8c03\u7528\u6808\u3001\u4f5c\u7528\u57df\u89c4\u5219\u548c static/extern \u5173\u952e\u5b57\u3002",
                        "path": "c/c_functions_scope.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["\u51fd\u6570", "\u4f5c\u7528\u57df", "static"],
                        "prerequisites": ["c-pointers"],
                        "outcomes": [
                            "\u7406\u89e3\u51fd\u6570\u8c03\u7528\u6808\u5e27",
                            "\u77e5\u9053 static \u548c extern \u7684\u533a\u522b",
                            "\u7406\u89e3\u9012\u5f52\u7684\u5de5\u4f5c\u539f\u7406",
                        ],
                    },
                ],
            },
            {
                "id": "c-memory",
                "title": "\u6838\u5fc3\u6a21\u5757 \u00b7 \u5185\u5b58\u4e0e\u6570\u636e\u7ed3\u6784",
                "summary": "\u638c\u63e1\u52a8\u6001\u5185\u5b58\u7ba1\u7406\u3001\u7ed3\u6784\u4f53\u3001\u8054\u5408\u4f53\u548c\u5e38\u89c1\u6570\u636e\u7ed3\u6784\u3002",
                "lessons": [
                    {
                        "id": "c-dynamic-memory",
                        "title": "\u52a8\u6001\u5185\u5b58\u7ba1\u7406",
                        "summary": "\u5b66\u4e60 malloc/calloc/realloc/free\uff0c\u7406\u89e3\u5185\u5b58\u6cc4\u6f0f\u548c\u60ac\u5782\u6307\u9488\u3002",
                        "path": "c/c_dynamic_memory.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["malloc", "free", "\u5185\u5b58\u6cc4\u6f0f"],
                        "prerequisites": ["c-functions-scope"],
                        "outcomes": [
                            "\u4f1a\u6b63\u786e\u4f7f\u7528 malloc \u548c free",
                            "\u80fd\u8bc6\u522b\u548c\u907f\u514d\u5185\u5b58\u6cc4\u6f0f",
                            "\u7406\u89e3\u60ac\u5782\u6307\u9488\u7684\u5371\u5bb3",
                        ],
                    },
                    {
                        "id": "c-structs-unions",
                        "title": "\u7ed3\u6784\u4f53\u3001\u8054\u5408\u4f53\u4e0e\u4f4d\u6bb5",
                        "summary": "\u5b66\u4e60 struct/union/enum\uff0c\u7406\u89e3\u5185\u5b58\u5bf9\u9f50\u548c\u4f4d\u6bb5\u3002",
                        "path": "c/c_structs_unions.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["struct", "union", "\u5bf9\u9f50"],
                        "prerequisites": ["c-dynamic-memory"],
                        "outcomes": [
                            "\u4f1a\u5b9a\u4e49\u548c\u4f7f\u7528\u7ed3\u6784\u4f53",
                            "\u7406\u89e3\u8054\u5408\u4f53\u7684\u5185\u5b58\u5171\u4eab",
                            "\u77e5\u9053\u7ed3\u6784\u4f53\u5bf9\u9f50\u89c4\u5219",
                        ],
                    },
                    {
                        "id": "c-linked-lists",
                        "title": "\u94fe\u8868\u4e0e\u6811\u7ed3\u6784",
                        "summary": "\u7528 C \u5b9e\u73b0\u5355\u5411\u94fe\u8868\u3001\u53cc\u5411\u94fe\u8868\u548c\u4e8c\u53c9\u6811\u3002",
                        "path": "c/c_linked_lists.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u94fe\u8868", "\u6811", "\u6570\u636e\u7ed3\u6784"],
                        "prerequisites": ["c-structs-unions"],
                        "outcomes": [
                            "\u4f1a\u5b9e\u73b0\u5355\u5411\u94fe\u8868",
                            "\u4f1a\u5b9e\u73b0\u4e8c\u53c9\u6811",
                            "\u7406\u89e3\u6307\u9488\u5728\u6570\u636e\u7ed3\u6784\u4e2d\u7684\u5e94\u7528",
                        ],
                    },
                    {
                        "id": "c-file-io",
                        "title": "\u6587\u4ef6 I/O \u4e0e\u6807\u51c6\u5e93",
                        "summary": "\u5b66\u4e60 FILE \u6307\u9488\u3001fopen/fread/fwrite \u548c\u5e38\u7528\u6807\u51c6\u5e93\u51fd\u6570\u3002",
                        "path": "c/c_file_io.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["FILE", "fopen", "\u6807\u51c6\u5e93"],
                        "prerequisites": ["c-dynamic-memory"],
                        "outcomes": [
                            "\u4f1a\u7528 FILE \u6307\u9488\u8bfb\u5199\u6587\u4ef6",
                            "\u7406\u89e3\u6587\u672c\u548c\u4e8c\u8fdb\u5236\u6a21\u5f0f",
                            "\u77e5\u9053\u5e38\u7528\u6807\u51c6\u5e93\u51fd\u6570",
                        ],
                    },
                ],
            },
            {
                "id": "c-advanced",
                "title": "\u8fdb\u9636\u6a21\u5757 \u00b7 \u7cfb\u7edf\u7f16\u7a0b\u4e0e\u5e95\u5c42",
                "summary": "\u7406\u89e3 POSIX \u63a5\u53e3\u3001\u8fdb\u7a0b/\u7ebf\u7a0b\u3001\u4fe1\u53f7\u548c\u7cfb\u7edf\u8c03\u7528\u3002",
                "lessons": [
                    {
                        "id": "c-preprocessor",
                        "title": "\u9884\u5904\u7406\u5668\u4e0e\u5b8f",
                        "summary": "\u5b66\u4e60 #define\u3001\u6761\u4ef6\u7f16\u8bd1\u3001\u5b8f\u51fd\u6570\u548c #pragma\u3002",
                        "path": "c/c_preprocessor.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 35,
                        "tags": ["\u5b8f", "\u9884\u5904\u7406", "#define"],
                        "prerequisites": ["c-file-io"],
                        "outcomes": [
                            "\u4f1a\u5199\u5b8f\u5b9a\u4e49\u548c\u5b8f\u51fd\u6570",
                            "\u7406\u89e3\u6761\u4ef6\u7f16\u8bd1",
                            "\u77e5\u9053 #pragma \u7684\u7528\u6cd5",
                        ],
                    },
                    {
                        "id": "c-undefined-behavior",
                        "title": "\u672a\u5b9a\u4e49\u884c\u4e3a\u4e0e\u5b89\u5168\u7f16\u7a0b",
                        "summary": "\u7406\u89e3 UB\u3001\u6574\u6570\u6ea2\u51fa\u3001\u7f13\u51b2\u533a\u6ea2\u51fa\u548c\u9632\u5fa1\u6027\u7f16\u7a0b\u3002",
                        "path": "c/c_undefined_behavior.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["UB", "\u5b89\u5168", "\u9632\u5fa1"],
                        "prerequisites": ["c-dynamic-memory"],
                        "outcomes": [
                            "\u7406\u89e3\u4ec0\u4e48\u662f\u672a\u5b9a\u4e49\u884c\u4e3a",
                            "\u80fd\u8bc6\u522b\u5e38\u89c1\u7684 UB \u6a21\u5f0f",
                            "\u4f1a\u5199\u9632\u5fa1\u6027\u4ee3\u7801",
                        ],
                    },
                    {
                        "id": "c-posix-basics",
                        "title": "POSIX \u7cfb\u7edf\u63a5\u53e3\u5165\u95e8",
                        "summary": "\u5b66\u4e60\u6587\u4ef6\u63cf\u8ff0\u7b26\u3001\u8fdb\u7a0b\u3001\u4fe1\u53f7\u548c\u7ba1\u9053\u7b49 POSIX \u63a5\u53e3\u3002",
                        "path": "c/c_posix_basics.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 50,
                        "tags": ["POSIX", "\u8fdb\u7a0b", "\u4fe1\u53f7"],
                        "prerequisites": ["c-file-io"],
                        "outcomes": [
                            "\u7406\u89e3\u6587\u4ef6\u63cf\u8ff0\u7b26",
                            "\u4f1a\u7528 fork/exec \u521b\u5efa\u8fdb\u7a0b",
                            "\u77e5\u9053\u4fe1\u53f7\u5904\u7406\u7684\u57fa\u672c\u65b9\u6cd5",
                        ],
                    },
                    {
                        "id": "c-debugging-tools",
                        "title": "\u8c03\u8bd5\u5de5\u5177\u4e0e\u5185\u5b58\u68c0\u6d4b",
                        "summary": "\u5b66\u4e60 gdb \u8c03\u8bd5\u3001Valgrind \u5185\u5b58\u68c0\u6d4b\u548c AddressSanitizer\u3002",
                        "path": "c/c_debugging_tools.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["gdb", "Valgrind", "ASan"],
                        "prerequisites": ["c-dynamic-memory"],
                        "outcomes": [
                            "\u4f1a\u7528 gdb \u8c03\u8bd5 C \u7a0b\u5e8f",
                            "\u4f1a\u7528 Valgrind \u68c0\u6d4b\u5185\u5b58\u6cc4\u6f0f",
                            "\u77e5\u9053 AddressSanitizer \u7684\u7528\u6cd5",
                        ],
                    },
                ],
            },
            {
                "id": "c-projects",
                "title": "\u5b9e\u6218\u6a21\u5757 \u00b7 \u9879\u76ee\u4e0e\u5de5\u7a0b",
                "summary": "\u7efc\u5408\u8fd0\u7528 C \u8bed\u8a00\u77e5\u8bc6\uff0c\u5b9e\u73b0\u5b8c\u6574\u7684\u7cfb\u7edf\u7ea7\u9879\u76ee\u3002",
                "lessons": [
                    {
                        "id": "c-make-build",
                        "title": "Make \u4e0e\u6784\u5efa\u7cfb\u7edf",
                        "summary": "\u5b66\u4e60 Makefile \u7f16\u5199\u548c\u6784\u5efa\u7cfb\u7edf\u7ba1\u7406\u3002",
                        "path": "c/c_make_build.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["Make", "\u6784\u5efa", "\u5de5\u7a0b"],
                        "prerequisites": ["c-thinking-setup"],
                        "outcomes": [
                            "\u4f1a\u5199 Makefile",
                            "\u7406\u89e3\u4f9d\u8d56\u5173\u7cfb",
                            "\u77e5\u9053\u591a\u6587\u4ef6\u9879\u76ee\u7684\u6784\u5efa\u6d41\u7a0b",
                        ],
                    },
                    {
                        "id": "c-mini-libc",
                        "title": "\u8ff7\u4f60 libc \u5de5\u5177\u96c6",
                        "summary": "\u5b9e\u73b0\u4e00\u7ec4\u5e38\u7528\u7684\u5b57\u7b26\u4e32\u548c I/O \u5de5\u5177\u51fd\u6570\u3002",
                        "path": "c/c_mini_libc.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 60,
                        "tags": ["\u9879\u76ee", "\u5b57\u7b26\u4e32", "I/O"],
                        "prerequisites": ["c-make-build"],
                        "outcomes": [
                            "\u80fd\u5b9e\u73b0\u81ea\u5df1\u7684\u5b57\u7b26\u4e32\u51fd\u6570",
                            "\u7406\u89e3\u9519\u8bef\u7801\u5904\u7406",
                            "\u5efa\u7acb\u5b89\u5168\u7f16\u7a0b\u4e60\u60ef",
                        ],
                    },
                    {
                        "id": "c-memory-pool",
                        "title": "\u5185\u5b58\u6c60\u4e0e\u5206\u914d\u5668",
                        "summary": "\u5b9e\u73b0\u4e00\u4e2a\u7b80\u5355\u7684\u5185\u5b58\u6c60\u548c\u81ea\u5b9a\u4e49\u5206\u914d\u5668\u3002",
                        "path": "c/c_memory_pool.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 60,
                        "tags": [
                            "\u5206\u914d\u5668",
                            "\u5185\u5b58\u6c60",
                            "\u6027\u80fd",
                        ],
                        "prerequisites": ["c-dynamic-memory"],
                        "outcomes": [
                            "\u7406\u89e3\u5185\u5b58\u5206\u914d\u7684\u539f\u7406",
                            "\u4f1a\u5b9e\u73b0\u7b80\u5355\u7684\u5185\u5b58\u6c60",
                            "\u77e5\u9053\u5206\u914d\u5668\u6027\u80fd\u4f18\u5316\u7684\u65b9\u5411",
                        ],
                    },
                    {
                        "id": "c-project-complete",
                        "title": "\u7efc\u5408\u5b9e\u6218\u9879\u76ee",
                        "summary": "\u4ece\u96f6\u5f00\u59cb\u5b9e\u73b0\u4e00\u4e2a\u5b8c\u6574\u7684 C \u8bed\u8a00\u9879\u76ee\uff08\u5982\u8ff7\u4f60 Shell\uff09\u3002",
                        "path": "c/c_project_complete.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 90,
                        "tags": ["\u9879\u76ee", "Shell", "\u7efc\u5408"],
                        "prerequisites": ["c-posix-basics"],
                        "outcomes": [
                            "\u80fd\u72ec\u7acb\u8bbe\u8ba1\u5e76\u5b9e\u73b0\u4e00\u4e2a C \u9879\u76ee",
                            "\u4f1a\u7ec4\u7ec7\u591a\u6587\u4ef6\u9879\u76ee\u7ed3\u6784",
                            "\u638c\u63e1\u57fa\u672c\u7684\u8c03\u8bd5\u548c\u6d4b\u8bd5\u65b9\u6cd5",
                            "\u5177\u5907\u5b8c\u6574\u7684\u9879\u76ee\u4ea4\u4ed8\u80fd\u529b",
                        ],
                    },
                ],
            },
        ],
    }
)

print(
    "C track added:",
    sum(len(m["lessons"]) for m in data["tracks"][-1]["modules"]),
    "lessons",
)
save(data)
print("Saved C track")
