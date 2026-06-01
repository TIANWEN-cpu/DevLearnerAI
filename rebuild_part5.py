# -*- coding: utf-8 -*-
"""Rebuild Algorithms and Integration tracks, then verify."""

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
for tid in ["algorithms", "integration"]:
    data["tracks"] = [t for t in data["tracks"] if t["id"] != tid]

# ============================================================
# ALGORITHMS TRACK
# ============================================================
data["tracks"].append(
    {
        "id": "algorithms",
        "title": "\u7b97\u6cd5 / \u6570\u636e\u7ed3\u6784\u8def\u7ebf",
        "icon": "\U0001f9e0",
        "summary": "\u4ece\u57fa\u7840\u6570\u636e\u7ed3\u6784\u5230\u7ecf\u5178\u7b97\u6cd5\uff0c\u7cfb\u7edf\u63d0\u5347\u7f16\u7a0b\u601d\u7ef4\u548c\u7ade\u8d5b\u80fd\u529b\u3002",
        "modules": [
            {
                "id": "algo-foundations",
                "title": "\u57fa\u7840\u6a21\u5757 \u00b7 \u6570\u636e\u7ed3\u6784\u57fa\u7840",
                "summary": "\u638c\u63e1\u6570\u7ec4\u3001\u94fe\u8868\u3001\u6808\u3001\u961f\u5217\u3001\u54c8\u5e0c\u8868\u7b49\u57fa\u7840\u6570\u636e\u7ed3\u6784\u3002",
                "lessons": [
                    {
                        "id": "algo-complexity",
                        "title": "\u65f6\u95f4\u590d\u6742\u5ea6\u4e0e\u7a7a\u95f4\u590d\u6742\u5ea6",
                        "summary": "\u7406\u89e3 Big-O \u8868\u793a\u6cd5\uff0c\u5b66\u4f1a\u5206\u6790\u7b97\u6cd5\u7684\u6027\u80fd\u3002",
                        "path": "algorithms/algo_complexity.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 30,
                        "tags": ["Big-O", "\u590d\u6742\u5ea6", "\u5206\u6790"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3 Big-O \u7684\u542b\u4e49",
                            "\u80fd\u5206\u6790\u7b80\u5355\u4ee3\u7801\u7684\u65f6\u95f4\u590d\u6742\u5ea6",
                            "\u77e5\u9053\u65f6\u95f4\u548c\u7a7a\u95f4\u7684\u6743\u8861",
                        ],
                    },
                    {
                        "id": "algo-arrays-strings",
                        "title": "\u6570\u7ec4\u4e0e\u5b57\u7b26\u4e32\u7b97\u6cd5",
                        "summary": "\u638c\u63e1\u6570\u7ec4\u548c\u5b57\u7b26\u4e32\u7684\u5e38\u89c1\u7b97\u6cd5\u6a21\u5f0f\u3002",
                        "path": "algorithms/algo_arrays_strings.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": [
                            "\u6570\u7ec4",
                            "\u5b57\u7b26\u4e32",
                            "\u53cc\u6307\u9488",
                        ],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u4f1a\u7528\u53cc\u6307\u9488\u89e3\u51b3\u6570\u7ec4\u95ee\u9898",
                            "\u638c\u63e1\u6ed1\u52a8\u7a97\u53e3\u6280\u5de7",
                            "\u7406\u89e3\u524d\u7f00\u548c\u7684\u5e94\u7528",
                        ],
                    },
                    {
                        "id": "algo-linked-lists",
                        "title": "\u94fe\u8868\u64cd\u4f5c\u4e0e\u5e38\u89c1\u9898\u578b",
                        "summary": "\u5b66\u4e60\u5355\u5411\u94fe\u8868\u3001\u53cc\u5411\u94fe\u8868\u548c\u73af\u5f62\u94fe\u8868\u7684\u64cd\u4f5c\u3002",
                        "path": "algorithms/algo_linked_lists.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u94fe\u8868", "\u6307\u9488", "\u73af"],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u4f1a\u5b9e\u73b0\u94fe\u8868\u7684\u589e\u5220\u6539\u67e5",
                            "\u638c\u63e1\u5feb\u6162\u6307\u9488\u6280\u5de7",
                            "\u80fd\u89e3\u51b3\u73af\u5f62\u94fe\u8868\u95ee\u9898",
                        ],
                    },
                    {
                        "id": "algo-stacks-queues",
                        "title": "\u6808\u3001\u961f\u5217\u4e0e\u53cc\u7aef\u961f\u5217",
                        "summary": "\u7406\u89e3\u6808\u3001\u961f\u5217\u7684\u7279\u6027\u548c\u5e94\u7528\u573a\u666f\u3002",
                        "path": "algorithms/algo_stacks_queues.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u6808", "\u961f\u5217", "\u53cc\u7aef\u961f\u5217"],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u7406\u89e3 LIFO \u548c FIFO \u7684\u533a\u522b",
                            "\u4f1a\u7528\u6808\u89e3\u51b3\u62ec\u53f7\u5339\u914d\u95ee\u9898",
                            "\u77e5\u9053\u53cc\u7aef\u961f\u5217\u7684\u5e94\u7528",
                        ],
                    },
                    {
                        "id": "algo-hash-tables",
                        "title": "\u54c8\u5e0c\u8868\u4e0e\u5b57\u5178",
                        "summary": "\u7406\u89e3\u54c8\u5e0c\u51fd\u6570\u3001\u51b2\u7a81\u89e3\u51b3\u548c\u54c8\u5e0c\u8868\u7684\u5e94\u7528\u3002",
                        "path": "algorithms/algo_hash_tables.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["\u54c8\u5e0c", "\u5b57\u5178", "\u51b2\u7a81"],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u7406\u89e3\u54c8\u5e0c\u8868\u7684\u5de5\u4f5c\u539f\u7406",
                            "\u4f1a\u7528\u54c8\u5e0c\u8868\u505a\u53bb\u91cd\u548c\u9891\u7387\u7edf\u8ba1",
                            "\u77e5\u9053\u54c8\u5e0c\u51b2\u7a81\u7684\u89e3\u51b3\u65b9\u6848",
                        ],
                    },
                ],
            },
            {
                "id": "algo-trees-graphs",
                "title": "\u6838\u5fc3\u6a21\u5757 \u00b7 \u6811\u4e0e\u56fe",
                "summary": "\u638c\u63e1\u4e8c\u53c9\u6811\u3001BST\u3001\u5806\u3001\u56fe\u7684\u904d\u5386\u548c\u6700\u77ed\u8def\u5f84\u7b97\u6cd5\u3002",
                "lessons": [
                    {
                        "id": "algo-binary-trees",
                        "title": "\u4e8c\u53c9\u6811\u904d\u5386\u4e0e\u64cd\u4f5c",
                        "summary": "\u5b66\u4e60\u524d\u5e8f\u3001\u4e2d\u5e8f\u3001\u540e\u5e8f\u548c\u5c42\u5e8f\u904d\u5386\u3002",
                        "path": "algorithms/algo_binary_trees.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u4e8c\u53c9\u6811", "\u904d\u5386", "\u9012\u5f52"],
                        "prerequisites": ["algo-linked-lists"],
                        "outcomes": [
                            "\u4f1a\u5199\u9012\u5f52\u548c\u8fed\u4ee3\u904d\u5386",
                            "\u7406\u89e3\u4e8c\u53c9\u6811\u7684\u6027\u8d28",
                            "\u80fd\u89e3\u51b3\u5e38\u89c1\u7684\u4e8c\u53c9\u6811\u9898",
                        ],
                    },
                    {
                        "id": "algo-bst",
                        "title": "\u4e8c\u53c9\u641c\u7d22\u6811",
                        "summary": "\u7406\u89e3 BST \u7684\u6027\u8d28\u3001\u63d2\u5165\u3001\u5220\u9664\u548c\u67e5\u627e\u3002",
                        "path": "algorithms/algo_bst.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["BST", "\u641c\u7d22", "\u5e73\u8861"],
                        "prerequisites": ["algo-binary-trees"],
                        "outcomes": [
                            "\u7406\u89e3 BST \u7684\u6709\u5e8f\u6027",
                            "\u4f1a\u5b9e\u73b0 BST \u7684\u63d2\u5165\u548c\u5220\u9664",
                            "\u77e5\u9053\u5e73\u8861\u6811\u7684\u5fc5\u8981\u6027",
                        ],
                    },
                    {
                        "id": "algo-heaps",
                        "title": "\u5806\u4e0e\u4f18\u5148\u961f\u5217",
                        "summary": "\u5b66\u4e60\u4e8c\u53c9\u5806\u7684\u5b9e\u73b0\u548c\u5e94\u7528\u3002",
                        "path": "algorithms/algo_heaps.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["\u5806", "\u4f18\u5148\u961f\u5217", "Top-K"],
                        "prerequisites": ["algo-binary-trees"],
                        "outcomes": [
                            "\u7406\u89e3\u5806\u7684\u6027\u8d28",
                            "\u4f1a\u7528\u5806\u89e3\u51b3 Top-K \u95ee\u9898",
                            "\u77e5\u9053\u5806\u6392\u5e8f\u7684\u539f\u7406",
                        ],
                    },
                    {
                        "id": "algo-graphs",
                        "title": "\u56fe\u7684\u8868\u793a\u4e0e\u904d\u5386",
                        "summary": "\u5b66\u4e60\u90bb\u63a5\u77e9\u9635\u3001\u90bb\u63a5\u8868\u3001BFS \u548c DFS\u3002",
                        "path": "algorithms/algo_graphs.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u56fe", "BFS", "DFS"],
                        "prerequisites": ["algo-stacks-queues"],
                        "outcomes": [
                            "\u4f1a\u7528\u90bb\u63a5\u8868\u8868\u793a\u56fe",
                            "\u4f1a\u5199 BFS \u548c DFS",
                            "\u80fd\u89e3\u51b3\u56fe\u7684\u8fde\u901a\u6027\u95ee\u9898",
                        ],
                    },
                ],
            },
            {
                "id": "algo-classic",
                "title": "\u9ad8\u7ea7\u6a21\u5757 \u00b7 \u7ecf\u5178\u7b97\u6cd5",
                "summary": "\u638c\u63e1\u6392\u5e8f\u3001\u67e5\u627e\u3001\u52a8\u6001\u89c4\u5212\u3001\u8d2a\u5fc3\u548c\u56de\u6eaf\u7b97\u6cd5\u3002",
                "lessons": [
                    {
                        "id": "algo-sorting",
                        "title": "\u6392\u5e8f\u7b97\u6cd5\u5168\u89e3\u6790",
                        "summary": "\u5b66\u4e60\u5feb\u901f\u6392\u5e8f\u3001\u5f52\u5e76\u6392\u5e8f\u3001\u5806\u6392\u5e8f\u548c\u57fa\u6570\u6392\u5e8f\u3002",
                        "path": "algorithms/algo_sorting.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u6392\u5e8f", "\u5feb\u6392", "\u5f52\u5e76"],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u7406\u89e3\u5404\u79cd\u6392\u5e8f\u7684\u590d\u6742\u5ea6",
                            "\u4f1a\u5b9e\u73b0\u5feb\u6392\u548c\u5f52\u5e76",
                            "\u77e5\u9053\u4ec0\u4e48\u573a\u666f\u7528\u4ec0\u4e48\u6392\u5e8f",
                        ],
                    },
                    {
                        "id": "algo-binary-search",
                        "title": "\u4e8c\u5206\u67e5\u627e\u4e0e\u53d8\u4f53",
                        "summary": "\u638c\u63e1\u4e8c\u5206\u67e5\u627e\u7684\u6a21\u677f\u548c\u5e38\u89c1\u53d8\u4f53\u3002",
                        "path": "algorithms/algo_binary_search.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["\u4e8c\u5206", "\u67e5\u627e", "\u8fb9\u754c"],
                        "prerequisites": ["algo-complexity"],
                        "outcomes": [
                            "\u4f1a\u5199\u6807\u51c6\u4e8c\u5206\u67e5\u627e",
                            "\u7406\u89e3\u5de6\u8fb9\u754c\u548c\u53f3\u8fb9\u754c",
                            "\u80fd\u8bc6\u522b\u4e8c\u5206\u7684\u9002\u7528\u573a\u666f",
                        ],
                    },
                    {
                        "id": "algo-dp",
                        "title": "\u52a8\u6001\u89c4\u5212\u5165\u95e8",
                        "summary": "\u7406\u89e3\u72b6\u6001\u8f6c\u79fb\u3001\u8bb0\u5fc6\u5316\u641c\u7d22\u548c\u81ea\u5e95\u5411\u4e0a DP\u3002",
                        "path": "algorithms/algo_dp.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 60,
                        "tags": [
                            "DP",
                            "\u72b6\u6001\u8f6c\u79fb",
                            "\u8bb0\u5fc6\u5316",
                        ],
                        "prerequisites": ["algo-binary-trees"],
                        "outcomes": [
                            "\u7406\u89e3\u91cd\u53e0\u5b50\u95ee\u9898\u548c\u6700\u4f18\u5b50\u7ed3\u6784",
                            "\u4f1a\u5199\u7ecf\u5178\u7684 DP \u9898",
                            "\u77e5\u9053\u7a7a\u95f4\u4f18\u5316\u7684\u65b9\u6cd5",
                        ],
                    },
                    {
                        "id": "algo-greedy-backtrack",
                        "title": "\u8d2a\u5fc3\u4e0e\u56de\u6eaf\u7b97\u6cd5",
                        "summary": "\u5b66\u4e60\u8d2a\u5fc3\u7b56\u7565\u7684\u9002\u7528\u6761\u4ef6\u548c\u56de\u6eaf\u641c\u7d22\u6a21\u677f\u3002",
                        "path": "algorithms/algo_greedy_backtrack.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 50,
                        "tags": ["\u8d2a\u5fc3", "\u56de\u6eaf", "\u641c\u7d22"],
                        "prerequisites": ["algo-binary-trees"],
                        "outcomes": [
                            "\u7406\u89e3\u8d2a\u5fc3\u7684\u9002\u7528\u6761\u4ef6",
                            "\u4f1a\u5199\u56de\u6eaf\u641c\u7d22\u6a21\u677f",
                            "\u80fd\u89e3\u51b3\u7ec4\u5408\u548c\u6392\u5217\u95ee\u9898",
                        ],
                    },
                ],
            },
        ],
    }
)

print(
    "Algorithms track added:",
    sum(len(m["lessons"]) for m in data["tracks"][-1]["modules"]),
    "lessons",
)

# ============================================================
# INTEGRATION TRACK
# ============================================================
data["tracks"].append(
    {
        "id": "integration",
        "title": "\u878d\u5408\u9879\u76ee\u8def\u7ebf",
        "icon": "\U0001f517",
        "summary": "\u8de8\u6280\u672f\u6808\u7efc\u5408\u5b9e\u6218\uff0c\u5c06\u6240\u5b66\u77e5\u8bc6\u878d\u4f1a\u8d2f\u901a\u3002",
        "modules": [
            {
                "id": "int-fullstack",
                "title": "\u5168\u6808\u5f00\u53d1\u6a21\u5757",
                "summary": "\u5b66\u4e60\u524d\u540e\u7aef\u5206\u79bb\u67b6\u6784\u3001API \u8bbe\u8ba1\u548c\u90e8\u7f72\u3002",
                "lessons": [
                    {
                        "id": "int-api-design",
                        "title": "RESTful API \u8bbe\u8ba1\u4e0e\u5b9e\u73b0",
                        "summary": "\u7406\u89e3 REST \u539f\u5219\uff0c\u5b66\u4f1a\u8bbe\u8ba1\u6e05\u6670\u7684 API \u63a5\u53e3\u3002",
                        "path": "integration/int_api_design.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["REST", "API", "\u8bbe\u8ba1"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3 REST \u7684\u516d\u4e2a\u7ea6\u675f",
                            "\u4f1a\u8bbe\u8ba1\u6e05\u6670\u7684 API \u63a5\u53e3",
                            "\u77e5\u9053\u7248\u672c\u63a7\u5236\u548c\u9519\u8bef\u5904\u7406",
                        ],
                    },
                    {
                        "id": "int-frontend-basics",
                        "title": "\u524d\u7aef\u57fa\u7840\u4e0e\u6570\u636e\u4ea4\u4e92",
                        "summary": "\u5b66\u4e60 HTML/CSS/JS \u57fa\u7840\uff0c\u7406\u89e3\u4e0e\u540e\u7aef\u7684\u6570\u636e\u4ea4\u4e92\u3002",
                        "path": "integration/int_frontend_basics.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["HTML", "CSS", "JavaScript"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3\u524d\u540e\u7aef\u5206\u79bb\u7684\u4ef7\u503c",
                            "\u4f1a\u5199\u7b80\u5355\u7684\u524d\u7aef\u9875\u9762",
                            "\u77e5\u9053\u5982\u4f55\u8c03\u7528 API \u5e76\u5904\u7406\u54cd\u5e94",
                        ],
                    },
                    {
                        "id": "int-docker",
                        "title": "Docker \u5bb9\u5668\u5316\u90e8\u7f72",
                        "summary": "\u5b66\u4e60 Docker \u57fa\u7840\u3001Dockerfile \u548c docker-compose\u3002",
                        "path": "integration/int_docker.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["Docker", "\u5bb9\u5668", "\u90e8\u7f72"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3\u5bb9\u5668\u5316\u7684\u4ef7\u503c",
                            "\u4f1a\u5199 Dockerfile",
                            "\u80fd\u7528 docker-compose \u90e8\u7f72\u591a\u670d\u52a1",
                        ],
                    },
                    {
                        "id": "int-ci-cd",
                        "title": "CI/CD \u4e0e\u81ea\u52a8\u5316",
                        "summary": "\u5b66\u4e60 GitHub Actions \u548c\u81ea\u52a8\u5316\u6d4b\u8bd5/\u90e8\u7f72\u6d41\u7a0b\u3002",
                        "path": "integration/int_ci_cd.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["CI/CD", "GitHub Actions", "\u81ea\u52a8\u5316"],
                        "prerequisites": ["int-docker"],
                        "outcomes": [
                            "\u7406\u89e3 CI/CD \u7684\u6982\u5ff5",
                            "\u4f1a\u914d\u7f6e GitHub Actions",
                            "\u77e5\u9053\u81ea\u52a8\u5316\u6d4b\u8bd5\u7684\u6d41\u7a0b",
                        ],
                    },
                ],
            },
            {
                "id": "int-embedded",
                "title": "\u5d4c\u5165\u5f0f\u4e0e\u63a7\u5236\u6a21\u5757",
                "summary": "\u4ece\u4eff\u771f\u5230\u5b9e\u7269\uff0c\u5b66\u4e60\u5d4c\u5165\u5f0f\u5f00\u53d1\u548c\u63a7\u5236\u7cfb\u7edf\u3002",
                "lessons": [
                    {
                        "id": "int-wokwi-sim",
                        "title": "Wokwi \u5728\u7ebf\u4eff\u771f\u5165\u95e8",
                        "summary": "\u7528 Wokwi \u5728\u7ebf\u4eff\u771f Arduino/ESP32/STM32 \u7535\u8def\u3002",
                        "path": "integration/int_wokwi_sim.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 35,
                        "tags": ["Wokwi", "\u4eff\u771f", "Arduino"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u4f1a\u7528 Wokwi \u642d\u5efa\u7535\u8def\u4eff\u771f",
                            "\u7406\u89e3 GPIO \u548c\u4e32\u53e3\u901a\u4fe1",
                            "\u80fd\u5b8c\u6210 LED \u548c\u6309\u952e\u5b9e\u9a8c",
                        ],
                    },
                    {
                        "id": "int-platformio",
                        "title": "PlatformIO \u5f00\u53d1\u73af\u5883",
                        "summary": "\u5b66\u4e60\u5728 VS Code \u4e2d\u7528 PlatformIO \u5f00\u53d1\u5d4c\u5165\u5f0f\u9879\u76ee\u3002",
                        "path": "integration/int_platformio.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["PlatformIO", "VS Code", "\u5d4c\u5165\u5f0f"],
                        "prerequisites": ["int-wokwi-sim"],
                        "outcomes": [
                            "\u4f1a\u914d\u7f6e PlatformIO \u9879\u76ee",
                            "\u7406\u89e3\u5e93\u7ba1\u7406\u548c\u4e0a\u4f20\u6d41\u7a0b",
                            "\u80fd\u5f00\u53d1\u591a\u677f\u5b50\u9879\u76ee",
                        ],
                    },
                    {
                        "id": "int-simulink",
                        "title": "Simulink \u63a7\u5236\u4eff\u771f",
                        "summary": "\u5b66\u4e60 Simulink \u5efa\u6a21\u548c PID \u63a7\u5236\u5668\u8bbe\u8ba1\u3002",
                        "path": "integration/int_simulink.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["Simulink", "PID", "\u63a7\u5236"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u4f1a\u7528 Simulink \u5efa\u7acb\u7cfb\u7edf\u6a21\u578b",
                            "\u7406\u89e3 PID \u63a7\u5236\u5668\u7684\u539f\u7406",
                            "\u80fd\u8bbe\u8ba1\u548c\u8c03\u53c2 PID \u63a7\u5236\u5668",
                        ],
                    },
                    {
                        "id": "int-robotics",
                        "title": "\u673a\u5668\u4eba\u4e0e\u667a\u80fd\u8f66\u5165\u95e8",
                        "summary": "\u4e86\u89e3\u673a\u5668\u4eba\u64cd\u4f5c\u7cfb\u7edf\u548c\u667a\u80fd\u8f66\u7ade\u8d5b\u7684\u57fa\u7840\u77e5\u8bc6\u3002",
                        "path": "integration/int_robotics.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 50,
                        "tags": ["\u673a\u5668\u4eba", "\u667a\u80fd\u8f66", "ROS"],
                        "prerequisites": ["int-platformio"],
                        "outcomes": [
                            "\u4e86\u89e3\u673a\u5668\u4eba\u7684\u57fa\u672c\u7ec4\u6210",
                            "\u77e5\u9053\u667a\u80fd\u8f66\u7ade\u8d5b\u7684\u8981\u6c42",
                            "\u80fd\u5b8c\u6210\u57fa\u7840\u7684\u4f20\u611f\u5668\u96c6\u6210",
                        ],
                    },
                ],
            },
            {
                "id": "int-competition",
                "title": "\u7ade\u8d5b\u4e0e\u9879\u76ee\u6a21\u5757",
                "summary": "\u9488\u5bf9\u84dd\u6865\u676f\u3001\u7535\u5b50\u8bbe\u8ba1\u7ade\u8d5b\u7b49\u5907\u8d5b\u6307\u5357\u3002",
                "lessons": [
                    {
                        "id": "int-lanqiao",
                        "title": "\u84dd\u6865\u676f\u5907\u8d5b\u6307\u5357",
                        "summary": "\u4e86\u89e3\u84dd\u6865\u676f\u7684\u8003\u70b9\u3001\u9898\u578b\u548c\u5907\u8d5b\u7b56\u7565\u3002",
                        "path": "integration/int_lanqiao.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 35,
                        "tags": ["\u84dd\u6865\u676f", "\u7ade\u8d5b", "\u5907\u8d5b"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u4e86\u89e3\u84dd\u6865\u676f\u7684\u8003\u70b9\u5206\u5e03",
                            "\u77e5\u9053\u5404\u8bed\u8a00\u7ec4\u7684\u9898\u578b\u7279\u70b9",
                            "\u6709\u660e\u786e\u7684\u5907\u8d5b\u8ba1\u5212",
                        ],
                    },
                    {
                        "id": "int-electronic-design",
                        "title": "\u7535\u5b50\u8bbe\u8ba1\u7ade\u8d5b\u5907\u8d5b",
                        "summary": "\u4e86\u89e3\u7535\u8d5b\u7684\u9898\u76ee\u7c7b\u578b\u3001\u5de5\u5177\u94fe\u548c\u56e2\u961f\u534f\u4f5c\u3002",
                        "path": "integration/int_electronic_design.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 40,
                        "tags": ["\u7535\u8d5b", "\u5d4c\u5165\u5f0f", "\u56e2\u961f"],
                        "prerequisites": ["int-platformio"],
                        "outcomes": [
                            "\u4e86\u89e3\u7535\u8d5b\u7684\u9898\u76ee\u7c7b\u578b",
                            "\u77e5\u9053\u5e38\u7528\u7684\u5f00\u53d1\u5de5\u5177",
                            "\u6709\u56e2\u961f\u534f\u4f5c\u7684\u610f\u8bc6",
                        ],
                    },
                    {
                        "id": "int-math-modeling",
                        "title": "\u6570\u5b66\u5efa\u6a21\u5165\u95e8",
                        "summary": "\u5b66\u4e60\u6570\u5b66\u5efa\u6a21\u7684\u57fa\u672c\u65b9\u6cd5\u548c Python/MATLAB \u5de5\u5177\u3002",
                        "path": "integration/int_math_modeling.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["\u6570\u5b66\u5efa\u6a21", "Python", "MATLAB"],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3\u6570\u5b66\u5efa\u6a21\u7684\u57fa\u672c\u6d41\u7a0b",
                            "\u4f1a\u7528 Python \u505a\u6570\u636e\u5206\u6790\u548c\u53ef\u89c6\u5316",
                            "\u77e5\u9053\u5e38\u89c1\u7684\u5efa\u6a21\u65b9\u6cd5",
                        ],
                    },
                    {
                        "id": "int-capstone",
                        "title": "\u7efc\u5408\u6bd5\u8bbe\u7ea7\u9879\u76ee",
                        "summary": "\u7efc\u5408\u8fd0\u7528\u6240\u5b66\u77e5\u8bc6\uff0c\u5b8c\u6210\u4e00\u4e2a\u8de8\u6280\u672f\u6808\u7684\u5b8c\u6574\u9879\u76ee\u3002",
                        "path": "integration/int_capstone.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 90,
                        "tags": ["\u9879\u76ee", "\u7efc\u5408", "\u6bd5\u8bbe"],
                        "prerequisites": ["int-ci-cd"],
                        "outcomes": [
                            "\u80fd\u72ec\u7acb\u5b8c\u6210\u8de8\u6280\u672f\u6808\u9879\u76ee",
                            "\u4f1a\u505a\u9700\u6c42\u5206\u6790\u548c\u6280\u672f\u9009\u578b",
                            "\u638c\u63e1\u5b8c\u6574\u7684\u9879\u76ee\u7ba1\u7406\u6d41\u7a0b",
                            "\u5177\u5907\u6c42\u804c\u7b80\u5386\u9879\u76ee\u7ecf\u9a8c",
                        ],
                    },
                ],
            },
        ],
    }
)

print(
    "Integration track added:",
    sum(len(m["lessons"]) for m in data["tracks"][-1]["modules"]),
    "lessons",
)
save(data)

# Verify all tracks
print("\n=== Final Track Summary ===")
for track in data["tracks"]:
    tid = track["id"]
    n_mod = len(track["modules"])
    n_lessons = sum(len(m["lessons"]) for m in track["modules"])
    print(f"{tid}: {n_mod} modules, {n_lessons} lessons")

total = sum(sum(len(m["lessons"]) for m in t["modules"]) for t in data["tracks"])
print(f"\nTotal lessons across all tracks: {total}")
