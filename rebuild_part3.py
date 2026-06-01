# -*- coding: utf-8 -*-
"""Rebuild C#, Database, Algorithms, Integration tracks."""

import json, os

BASE = r"D:\codelearnhleper\content"


def load():
    with open(
        os.path.join(BASE, "metadata", "course_map.json"), "r", encoding="utf-8"
    ) as f:
        return json.load(f)


def save(data):
    with open(
        os.path.join(BASE, "metadata", "course_map.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load()

# Remove old tracks
for tid in ["csharp", "database", "algorithms", "integration"]:
    data["tracks"] = [t for t in data["tracks"] if t["id"] != tid]

# ============================================================
# C# TRACK
# ============================================================
data["tracks"].append(
    {
        "id": "csharp",
        "title": "C# \u8def\u7ebf",
        "icon": "\U0001f48e",
        "summary": "\u4ece .NET \u57fa\u7840\u5230\u4f01\u4e1a\u7ea7\u540e\u7aef\u5f00\u53d1\uff0c\u638c\u63e1\u73b0\u4ee3 C# \u7f16\u7a0b\u3002",
        "modules": [
            {
                "id": "csharp-foundations",
                "title": "\u57fa\u7840\u6a21\u5757 \u00b7 \u8bed\u6cd5\u4e0e .NET \u751f\u6001",
                "summary": "\u638c\u63e1 C# \u57fa\u7840\u8bed\u6cd5\u3001\u7c7b\u578b\u7cfb\u7edf\u548c .NET \u9879\u76ee\u7ed3\u6784\u3002",
                "lessons": [
                    {
                        "id": "cs-thinking-setup",
                        "title": "C# \u5b66\u4e60\u5730\u56fe\u4e0e .NET \u73af\u5883",
                        "summary": "\u7406\u89e3 .NET SDK\u3001\u8fd0\u884c\u65f6\u548c\u9879\u76ee\u7ed3\u6784\u3002",
                        "path": "csharp/cs_thinking_setup.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 25,
                        "tags": [".NET", "SDK", "\u5165\u95e8"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3 .NET \u751f\u6001\u7cfb\u7edf\u7684\u7ec4\u6210",
                            "\u4f1a\u521b\u5efa\u548c\u8fd0\u884c .NET \u9879\u76ee",
                            "\u77e5\u9053\u8bed\u8a00\u7248\u672c\u4e0e\u76ee\u6807\u6846\u67b6\u7684\u5173\u7cfb",
                        ],
                    },
                    {
                        "id": "cs-syntax-basics",
                        "title": "\u57fa\u7840\u8bed\u6cd5\u4e0e\u63a7\u5236\u6d41",
                        "summary": "\u638c\u63e1\u53d8\u91cf\u3001\u7c7b\u578b\u3001\u8fd0\u7b97\u7b26\u3001\u6761\u4ef6\u8bed\u53e5\u548c\u5faa\u73af\u3002",
                        "path": "csharp/cs_syntax_basics.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u8bed\u6cd5", "\u63a7\u5236\u6d41", "\u7c7b\u578b"],
                        "prerequisites": ["cs-thinking-setup"],
                        "outcomes": [
                            "\u4f1a\u5199\u5b8c\u6574\u7684 C# \u7a0b\u5e8f",
                            "\u638c\u63e1\u503c\u7c7b\u578b\u548c\u5f15\u7528\u7c7b\u578b\u7684\u533a\u522b",
                            "\u7406\u89e3 if/for/foreach/switch \u7684\u7528\u6cd5",
                        ],
                    },
                    {
                        "id": "cs-methods-params",
                        "title": "\u65b9\u6cd5\u4e0e\u53c2\u6570\u4f20\u9012",
                        "summary": "\u7406\u89e3\u65b9\u6cd5\u5b9a\u4e49\u3001\u53c2\u6570\u4f20\u9012\uff08\u503c/ref/out/in\uff09\u548c\u91cd\u8f7d\u3002",
                        "path": "csharp/cs_methods_params.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u65b9\u6cd5", "\u53c2\u6570", "\u91cd\u8f7d"],
                        "prerequisites": ["cs-syntax-basics"],
                        "outcomes": [
                            "\u4f1a\u5b9a\u4e49\u548c\u8c03\u7528\u65b9\u6cd5",
                            "\u7406\u89e3 ref/out/in \u53c2\u6570\u7684\u533a\u522b",
                            "\u77e5\u9053\u65b9\u6cd5\u91cd\u8f7d\u7684\u89c4\u5219",
                        ],
                    },
                    {
                        "id": "cs-collections",
                        "title": "\u96c6\u5408\u4e0e\u6cdb\u578b\u57fa\u7840",
                        "summary": "\u5b66\u4e60 List\u3001Dictionary \u7b49\u6cdb\u578b\u96c6\u5408\u3002",
                        "path": "csharp/cs_collections.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u96c6\u5408", "\u6cdb\u578b", "List"],
                        "prerequisites": ["cs-methods-params"],
                        "outcomes": [
                            "\u719f\u7ec3\u4f7f\u7528 List\u548c Dictionary",
                            "\u7406\u89e3\u6cdb\u578b\u7684\u597d\u5904",
                            "\u77e5\u9053\u96c6\u5408\u7684\u6027\u80fd\u7279\u70b9",
                        ],
                    },
                ],
            },
            {
                "id": "csharp-oop",
                "title": "\u6838\u5fc3\u6a21\u5757 \u00b7 \u9762\u5411\u5bf9\u8c61\u4e0e\u9ad8\u7ea7\u7279\u6027",
                "summary": "\u638c\u63e1\u7c7b\u3001\u63a5\u53e3\u3001\u6cdb\u578b\u3001\u59d4\u6258\u3001\u4e8b\u4ef6\u548c LINQ\u3002",
                "lessons": [
                    {
                        "id": "cs-oop-basics",
                        "title": "\u7c7b\u3001\u7ee7\u627f\u4e0e\u591a\u6001",
                        "summary": "\u5b66\u4e60\u7c7b\u5b9a\u4e49\u3001\u7ee7\u627f\u3001\u63a5\u53e3\u5b9e\u73b0\u548c\u591a\u6001\u3002",
                        "path": "csharp/cs_oop_basics.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["\u7c7b", "\u7ee7\u627f", "\u63a5\u53e3"],
                        "prerequisites": ["cs-collections"],
                        "outcomes": [
                            "\u4f1a\u5b9a\u4e49\u7c7b\u548c\u63a5\u53e3",
                            "\u7406\u89e3\u7ee7\u627f\u548c\u5b9e\u73b0\u7684\u533a\u522b",
                            "\u638c\u63e1\u591a\u6001\u7684\u5e94\u7528",
                        ],
                    },
                    {
                        "id": "cs-generics-delegates",
                        "title": "\u6cdb\u578b\u3001\u59d4\u6258\u4e0e\u4e8b\u4ef6",
                        "summary": "\u6df1\u5165\u7406\u89e3\u6cdb\u578b\u7ea6\u675f\u3001\u59d4\u6258\u7c7b\u578b\u548c\u4e8b\u4ef6\u6a21\u5f0f\u3002",
                        "path": "csharp/cs_generics_delegates.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["\u6cdb\u578b", "\u59d4\u6258", "\u4e8b\u4ef6"],
                        "prerequisites": ["cs-oop-basics"],
                        "outcomes": [
                            "\u4f1a\u5199\u6cdb\u578b\u7c7b\u548c\u65b9\u6cd5",
                            "\u7406\u89e3\u59d4\u6258\u548c\u4e8b\u4ef6\u7684\u533a\u522b",
                            "\u77e5\u9053 Action/Func/Predicate \u7684\u7528\u6cd5",
                        ],
                    },
                    {
                        "id": "cs-linq",
                        "title": "LINQ \u67e5\u8be2\u4e0e\u8868\u8fbe\u5f0f\u6811",
                        "summary": "\u638c\u63e1 LINQ \u67e5\u8be2\u8bed\u6cd5\u548c\u65b9\u6cd5\u8bed\u6cd5\uff0c\u7406\u89e3\u8868\u8fbe\u5f0f\u6811\u3002",
                        "path": "csharp/cs_linq.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["LINQ", "\u67e5\u8be2", "\u8868\u8fbe\u5f0f\u6811"],
                        "prerequisites": ["cs-generics-delegates"],
                        "outcomes": [
                            "\u719f\u7ec3\u4f7f\u7528 LINQ \u67e5\u8be2\u6570\u636e",
                            "\u7406\u89e3 IQueryable \u548c IEnumerable \u7684\u533a\u522b",
                            "\u77e5\u9053\u8868\u8fbe\u5f0f\u6811\u7684\u5e94\u7528\u573a\u666f",
                        ],
                    },
                    {
                        "id": "cs-async",
                        "title": "\u5f02\u6b65\u7f16\u7a0b\u4e0e TAP \u6a21\u5f0f",
                        "summary": "\u7406\u89e3 async/await\uff0c\u638c\u63e1 TAP \u5f02\u6b65\u8bbe\u8ba1\u6a21\u5f0f\u3002",
                        "path": "csharp/cs_async.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["async", "await", "TAP"],
                        "prerequisites": ["cs-generics-delegates"],
                        "outcomes": [
                            "\u7406\u89e3 async/await \u7684\u5de5\u4f5c\u539f\u7406",
                            "\u4f1a\u5199\u5f02\u6b65\u65b9\u6cd5",
                            "\u7406\u89e3\u53d6\u6d88\u4ee4\u724c\u548c\u8d85\u65f6\u5904\u7406",
                        ],
                    },
                ],
            },
            {
                "id": "csharp-backend",
                "title": "\u8fdb\u9636\u6a21\u5757 \u00b7 \u4f01\u4e1a\u7ea7\u540e\u7aef\u5f00\u53d1",
                "summary": "\u5b66\u4e60 Minimal API\u3001EF Core\u3001\u8ba4\u8bc1\u6388\u6743\u548c\u90e8\u7f72\u3002",
                "lessons": [
                    {
                        "id": "cs-minimal-api",
                        "title": "Minimal API \u5165\u95e8",
                        "summary": "\u7528 Minimal API \u5feb\u901f\u642d\u5efa Web \u670d\u52a1\uff0c\u7406\u89e3\u4e2d\u95f4\u4ef6\u548c\u8def\u7531\u3002",
                        "path": "csharp/cs_minimal_api.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["Minimal API", "\u4e2d\u95f4\u4ef6", "\u8def\u7531"],
                        "prerequisites": ["cs-async"],
                        "outcomes": [
                            "\u4f1a\u7528 Minimal API \u521b\u5efa Web \u670d\u52a1",
                            "\u7406\u89e3\u4e2d\u95f4\u4ef6\u7ba1\u9053",
                            "\u77e5\u9053\u8def\u7531\u548c\u53c2\u6570\u7ed1\u5b9a",
                        ],
                    },
                    {
                        "id": "cs-ef-core",
                        "title": "EF Core \u4e0e\u6570\u636e\u5e93\u8bbf\u95ee",
                        "summary": "\u5b66\u4e60 Entity Framework Core\uff0c\u638c\u63e1 Code First \u8fc1\u79fb\u548c LINQ \u67e5\u8be2\u3002",
                        "path": "csharp/cs_ef_core.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["EF Core", "ORM", "\u8fc1\u79fb"],
                        "prerequisites": ["cs-minimal-api"],
                        "outcomes": [
                            "\u4f1a\u7528 EF Core \u64cd\u4f5c\u6570\u636e\u5e93",
                            "\u7406\u89e3 Code First \u8fc1\u79fb",
                            "\u77e5\u9053 LINQ \u5230 SQL \u7684\u7ffb\u8bd1\u8fb9\u754c",
                        ],
                    },
                    {
                        "id": "cs-auth-security",
                        "title": "\u8ba4\u8bc1\u6388\u6743\u4e0e\u5b89\u5168",
                        "summary": "\u5b66\u4e60 JWT \u8ba4\u8bc1\u3001\u89d2\u8272\u6388\u6743\u548c OWASP \u5b89\u5168\u6700\u4f73\u5b9e\u8df5\u3002",
                        "path": "csharp/cs_auth_security.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["JWT", "\u8ba4\u8bc1", "\u5b89\u5168"],
                        "prerequisites": ["cs-ef-core"],
                        "outcomes": [
                            "\u4f1a\u5b9e\u73b0 JWT \u8ba4\u8bc1",
                            "\u7406\u89e3\u89d2\u8272\u548c\u7b56\u7565\u6388\u6743",
                            "\u77e5\u9053\u5e38\u89c1\u7684 Web \u5b89\u5168\u6f0f\u6d1e",
                        ],
                    },
                    {
                        "id": "cs-deployment",
                        "title": "\u6d4b\u8bd5\u3001\u76d1\u63a7\u4e0e\u90e8\u7f72",
                        "summary": "\u5b66\u4e60 xUnit \u5355\u5143\u6d4b\u8bd5\u3001\u65e5\u5fd7\u76d1\u63a7\u548c Docker \u90e8\u7f72\u3002",
                        "path": "csharp/cs_deployment.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["\u6d4b\u8bd5", "\u76d1\u63a7", "Docker"],
                        "prerequisites": ["cs-auth-security"],
                        "outcomes": [
                            "\u4f1a\u5199 xUnit \u5355\u5143\u6d4b\u8bd5",
                            "\u7406\u89e3\u7ed3\u6784\u5316\u65e5\u5fd7",
                            "\u77e5\u9053 Docker \u90e8\u7f72\u7684\u57fa\u672c\u6d41\u7a0b",
                        ],
                    },
                ],
            },
            {
                "id": "csharp-advanced",
                "title": "\u9ad8\u7ea7\u6a21\u5757 \u00b7 \u5e95\u5c42\u539f\u7406\u4e0e\u6027\u80fd",
                "summary": "\u7406\u89e3 CLR\u3001GC\u3001\u503c\u7c7b\u578b\u8bed\u4e49\u548c\u6027\u80fd\u4f18\u5316\u3002",
                "lessons": [
                    {
                        "id": "cs-clr-gc",
                        "title": "CLR \u4e0e\u5783\u573e\u56de\u6536",
                        "summary": "\u7406\u89e3 CLR \u8fd0\u884c\u65f6\u3001GC \u5de5\u4f5c\u539f\u7406\u548c\u6027\u80fd\u5f71\u54cd\u3002",
                        "path": "csharp/cs_clr_gc.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 50,
                        "tags": ["CLR", "GC", "\u8fd0\u884c\u65f6"],
                        "prerequisites": ["cs-deployment"],
                        "outcomes": [
                            "\u7406\u89e3 CLR \u7684\u57fa\u672c\u67b6\u6784",
                            "\u77e5\u9053 GC \u7684\u5de5\u4f5c\u539f\u7406",
                            "\u80fd\u8bc6\u522b GC \u6027\u80fd\u95ee\u9898",
                        ],
                    },
                    {
                        "id": "cs-value-types",
                        "title": "\u503c\u7c7b\u578b\u8bed\u4e49\u4e0e\u88c5\u7bb1\u62c6\u7bb1",
                        "summary": "\u6df1\u5165\u7406\u89e3 struct\u3001record struct \u548c\u88c5\u7bb1\u62c6\u7bb1\u7684\u6027\u80fd\u5f71\u54cd\u3002",
                        "path": "csharp/cs_value_types.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["struct", "\u88c5\u7bb1", "\u6027\u80fd"],
                        "prerequisites": ["cs-clr-gc"],
                        "outcomes": [
                            "\u7406\u89e3\u503c\u7c7b\u578b\u548c\u5f15\u7528\u7c7b\u578b\u7684\u5185\u5b58\u5dee\u5f02",
                            "\u77e5\u9053\u88c5\u7bb1\u62c6\u7bb1\u7684\u6027\u80fd\u4ee3\u4ef7",
                            "\u4f1a\u7528 record struct \u7b80\u5316\u4ee3\u7801",
                        ],
                    },
                    {
                        "id": "cs-reflection",
                        "title": "\u53cd\u5c04\u3001\u7279\u6027\u4e0e\u4f9d\u8d56\u6ce8\u5165",
                        "summary": "\u5b66\u4e60\u8fd0\u884c\u65f6\u7c7b\u578b\u53d1\u73b0\u3001\u81ea\u5b9a\u4e49\u7279\u6027\u548c DI \u5bb9\u5668\u3002",
                        "path": "csharp/cs_reflection.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["\u53cd\u5c04", "\u7279\u6027", "DI"],
                        "prerequisites": ["cs-clr-gc"],
                        "outcomes": [
                            "\u4f1a\u7528\u53cd\u5c04\u83b7\u53d6\u7c7b\u578b\u4fe1\u606f",
                            "\u7406\u89e3\u81ea\u5b9a\u4e49\u7279\u6027\u7684\u5e94\u7528",
                            "\u77e5\u9053 DI \u5bb9\u5668\u7684\u539f\u7406",
                        ],
                    },
                    {
                        "id": "cs-project-complete",
                        "title": "\u7efc\u5408\u5b9e\u6218\u9879\u76ee",
                        "summary": "\u4ece\u96f6\u5f00\u59cb\u6784\u5efa\u4e00\u4e2a\u5b8c\u6574\u7684 C# Web API \u9879\u76ee\u3002",
                        "path": "csharp/cs_project_complete.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 90,
                        "tags": ["\u9879\u76ee", "Web API", "\u7efc\u5408"],
                        "prerequisites": ["cs-deployment"],
                        "outcomes": [
                            "\u80fd\u72ec\u7acb\u8bbe\u8ba1\u5e76\u5b9e\u73b0\u4e00\u4e2a C# Web API",
                            "\u4f1a\u7ec4\u7ec7\u5206\u5c42\u67b6\u6784",
                            "\u638c\u63e1\u5b8c\u6574\u7684\u5f00\u53d1\u5230\u90e8\u7f72\u6d41\u7a0b",
                        ],
                    },
                ],
            },
        ],
    }
)

print(
    "C# track added:",
    sum(len(m["lessons"]) for m in data["tracks"][-1]["modules"]),
    "lessons",
)
save(data)
print("Saved C# track")
