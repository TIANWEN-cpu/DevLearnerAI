"""Rebuild Database, Algorithms, Integration tracks."""

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
for tid in ["database", "algorithms", "integration"]:
    data["tracks"] = [t for t in data["tracks"] if t["id"] != tid]

# ============================================================
# DATABASE TRACK
# ============================================================
data["tracks"].append(
    {
        "id": "database",
        "title": "\u6570\u636e\u5e93\u8def\u7ebf",
        "icon": "\U0001f5c4\ufe0f",
        "summary": "\u4ece SQL \u57fa\u7840\u5230 DBMS \u5185\u6838\uff0c\u7cfb\u7edf\u638c\u63e1\u6570\u636e\u5e93\u7406\u8bba\u4e0e\u5de5\u7a0b\u5b9e\u8df5\u3002",
        "modules": [
            {
                "id": "db-foundations",
                "title": "\u57fa\u7840\u6a21\u5757 \u00b7 \u5173\u7cfb\u6a21\u578b\u4e0e SQL",
                "summary": "\u7406\u89e3\u5173\u7cfb\u6a21\u578b\u3001\u8303\u5f0f\u7406\u8bba\u548c\u57fa\u7840 SQL \u67e5\u8be2\u3002",
                "lessons": [
                    {
                        "id": "db-thinking",
                        "title": "\u6570\u636e\u5e93\u5b66\u4e60\u5730\u56fe\u4e0e\u6838\u5fc3\u6982\u5ff5",
                        "summary": "\u7406\u89e3\u6570\u636e\u5e93\u7684\u5b9a\u4f4d\u3001\u5173\u7cfb\u6a21\u578b\u548c ER \u56fe\u8bbe\u8ba1\u3002",
                        "path": "database/db_thinking.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 25,
                        "tags": [
                            "\u5173\u7cfb\u6a21\u578b",
                            "ER \u56fe",
                            "\u5165\u95e8",
                        ],
                        "prerequisites": [],
                        "outcomes": [
                            "\u7406\u89e3\u5173\u7cfb\u6a21\u578b\u7684\u57fa\u672c\u6982\u5ff5",
                            "\u4f1a\u753b ER \u56fe\u5e76\u8f6c\u6362\u4e3a\u8868\u7ed3\u6784",
                            "\u77e5\u9053\u6570\u636e\u5e93\u7684\u5e94\u7528\u573a\u666f",
                        ],
                    },
                    {
                        "id": "db-sql-basics",
                        "title": "SQL \u57fa\u7840\u67e5\u8be2\u4e0e DML",
                        "summary": "\u638c\u63e1 SELECT/INSERT/UPDATE/DELETE \u548c WHERE \u6761\u4ef6\u3002",
                        "path": "database/db_sql_basics.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["SELECT", "INSERT", "DML"],
                        "prerequisites": ["db-thinking"],
                        "outcomes": [
                            "\u4f1a\u5199\u57fa\u672c\u7684 SELECT \u67e5\u8be2",
                            "\u638c\u63e1 INSERT/UPDATE/DELETE",
                            "\u7406\u89e3 WHERE \u6761\u4ef6\u7684\u5199\u6cd5",
                        ],
                    },
                    {
                        "id": "db-joins",
                        "title": "\u591a\u8868\u8fde\u63a5\u4e0e\u5b50\u67e5\u8be2",
                        "summary": "\u7406\u89e3 INNER/LEFT/RIGHT/FULL JOIN \u548c\u5b50\u67e5\u8be2\u3002",
                        "path": "database/db_joins.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 45,
                        "tags": ["JOIN", "\u5b50\u67e5\u8be2", "\u591a\u8868"],
                        "prerequisites": ["db-sql-basics"],
                        "outcomes": [
                            "\u7406\u89e3\u5404\u79cd JOIN \u7684\u533a\u522b",
                            "\u4f1a\u5199\u5b50\u67e5\u8be2",
                            "\u77e5\u9053 EXISTS \u548c IN \u7684\u5e94\u7528\u573a\u666f",
                        ],
                    },
                    {
                        "id": "db-aggregation",
                        "title": "\u805a\u5408\u51fd\u6570\u4e0e GROUP BY",
                        "summary": "\u638c\u63e1 GROUP BY\u3001HAVING \u548c\u5e38\u7528\u805a\u5408\u51fd\u6570\u3002",
                        "path": "database/db_aggregation.md",
                        "difficulty": "\u57fa\u7840",
                        "estimated_minutes": 40,
                        "tags": ["GROUP BY", "\u805a\u5408", "HAVING"],
                        "prerequisites": ["db-joins"],
                        "outcomes": [
                            "\u4f1a\u7528 GROUP BY \u505a\u5206\u7ec4\u7edf\u8ba1",
                            "\u7406\u89e3 HAVING \u548c WHERE \u7684\u533a\u522b",
                            "\u638c\u63e1 COUNT/SUM/AVG/MAX/MIN",
                        ],
                    },
                    {
                        "id": "db-normalization",
                        "title": "\u8303\u5f0f\u7406\u8bba\u4e0e\u6570\u636e\u5e93\u8bbe\u8ba1",
                        "summary": "\u7406\u89e3 1NF/2NF/3NF/BCNF\uff0c\u5b66\u4f1a\u89c4\u8303\u5316\u6570\u636e\u5e93\u8bbe\u8ba1\u3002",
                        "path": "database/db_normalization.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["\u8303\u5f0f", "\u8bbe\u8ba1", "\u89c4\u8303\u5316"],
                        "prerequisites": ["db-thinking"],
                        "outcomes": [
                            "\u7406\u89e3\u5404\u8303\u5f0f\u7684\u5b9a\u4e49",
                            "\u4f1a\u505a\u6570\u636e\u5e93\u89c4\u8303\u5316\u8bbe\u8ba1",
                            "\u77e5\u9053\u4f55\u65f6\u53cd\u89c4\u8303\u5316",
                        ],
                    },
                ],
            },
            {
                "id": "db-advanced",
                "title": "\u6838\u5fc3\u6a21\u5757 \u00b7 \u9ad8\u7ea7 SQL \u4e0e\u7d22\u5f15",
                "summary": "\u638c\u63e1\u7a97\u53e3\u51fd\u6570\u3001CTE\u3001\u7d22\u5f15\u7ed3\u6784\u548c\u6267\u884c\u8ba1\u5212\u5206\u6790\u3002",
                "lessons": [
                    {
                        "id": "db-window-functions",
                        "title": "\u7a97\u53e3\u51fd\u6570\u4e0e CTE",
                        "summary": "\u5b66\u4e60 ROW_NUMBER/RANK/LEAD/LAG \u548c WITH \u5b50\u53e5\u3002",
                        "path": "database/db_window_functions.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["\u7a97\u53e3\u51fd\u6570", "CTE", "\u5206\u6790"],
                        "prerequisites": ["db-aggregation"],
                        "outcomes": [
                            "\u4f1a\u7528\u7a97\u53e3\u51fd\u6570\u505a\u6392\u540d\u548c\u79fb\u52a8\u5e73\u5747",
                            "\u7406\u89e3 CTE \u548c\u9012\u5f52 CTE",
                            "\u77e5\u9053\u7a97\u53e3\u51fd\u6570\u7684\u6027\u80fd\u7279\u70b9",
                        ],
                    },
                    {
                        "id": "db-indexes",
                        "title": "\u7d22\u5f15\u539f\u7406\u4e0e B+ \u6811",
                        "summary": "\u7406\u89e3 B+ \u6811\u7d22\u5f15\u7684\u7ed3\u6784\u3001\u8986\u76d6\u7d22\u5f15\u548c\u7ec4\u5408\u7d22\u5f15\u3002",
                        "path": "database/db_indexes.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["B+ \u6811", "\u7d22\u5f15", "\u6027\u80fd"],
                        "prerequisites": ["db-normalization"],
                        "outcomes": [
                            "\u7406\u89e3 B+ \u6811\u7684\u5de5\u4f5c\u539f\u7406",
                            "\u4f1a\u9009\u62e9\u5408\u9002\u7684\u7d22\u5f15",
                            "\u77e5\u9053\u8986\u76d6\u7d22\u5f15\u7684\u4f18\u52bf",
                        ],
                    },
                    {
                        "id": "db-explain",
                        "title": "\u6267\u884c\u8ba1\u5212\u4e0e\u67e5\u8be2\u4f18\u5316",
                        "summary": "\u5b66\u4f1a\u9605\u8bfb EXPLAIN \u8f93\u51fa\uff0c\u7406\u89e3\u67e5\u8be2\u4f18\u5316\u5668\u7684\u57fa\u672c\u7b56\u7565\u3002",
                        "path": "database/db_explain.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["EXPLAIN", "\u4f18\u5316", "\u6267\u884c\u8ba1\u5212"],
                        "prerequisites": ["db-indexes"],
                        "outcomes": [
                            "\u4f1a\u9605\u8bfb EXPLAIN \u8f93\u51fa",
                            "\u80fd\u8bc6\u522b\u5168\u8868\u626b\u63cf\u548c\u7d22\u5f15\u626b\u63cf",
                            "\u77e5\u9053\u57fa\u672c\u7684 SQL \u6539\u5199\u6280\u5de7",
                        ],
                    },
                    {
                        "id": "db-transactions",
                        "title": "\u4e8b\u52a1\u4e0e\u9694\u79bb\u7ea7\u522b",
                        "summary": "\u7406\u89e3 ACID \u7279\u6027\u3001\u56db\u79cd\u9694\u79bb\u7ea7\u522b\u548c MVCC \u539f\u7406\u3002",
                        "path": "database/db_transactions.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 50,
                        "tags": ["ACID", "\u9694\u79bb", "MVCC"],
                        "prerequisites": ["db-sql-basics"],
                        "outcomes": [
                            "\u7406\u89e3 ACID \u7684\u56db\u4e2a\u7279\u6027",
                            "\u77e5\u9053\u56db\u79cd\u9694\u79bb\u7ea7\u522b\u7684\u533a\u522b",
                            "\u7406\u89e3 MVCC \u7684\u57fa\u672c\u539f\u7406",
                        ],
                    },
                ],
            },
            {
                "id": "db-engines",
                "title": "\u8fdb\u9636\u6a21\u5757 \u00b7 \u5f15\u64ce\u4e0e NoSQL",
                "summary": "\u5bf9\u6bd4 PostgreSQL \u548c MySQL\uff0c\u7406\u89e3 NoSQL \u6570\u636e\u5e93\u3002",
                "lessons": [
                    {
                        "id": "db-postgresql",
                        "title": "PostgreSQL \u6df1\u5165",
                        "summary": "\u5b66\u4e60 PG \u7684\u9ad8\u7ea7\u7279\u6027\uff1aJSONB\u3001\u5168\u6587\u641c\u7d22\u3001\u6269\u5c55\u3002",
                        "path": "database/db_postgresql.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["PostgreSQL", "JSONB", "\u6269\u5c55"],
                        "prerequisites": ["db-transactions"],
                        "outcomes": [
                            "\u4f1a\u7528 PG \u7684 JSONB \u7c7b\u578b",
                            "\u77e5\u9053\u5168\u6587\u641c\u7d22\u7684\u57fa\u672c\u7528\u6cd5",
                            "\u4e86\u89e3 PG \u7684\u6269\u5c55\u751f\u6001",
                        ],
                    },
                    {
                        "id": "db-mysql",
                        "title": "MySQL InnoDB \u6df1\u5165",
                        "summary": "\u7406\u89e3 InnoDB \u7684\u5b58\u50a8\u7ed3\u6784\u3001\u9501\u673a\u5236\u548c\u9ed8\u8ba4\u9694\u79bb\u7ea7\u522b\u3002",
                        "path": "database/db_mysql.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 45,
                        "tags": ["MySQL", "InnoDB", "\u9501"],
                        "prerequisites": ["db-transactions"],
                        "outcomes": [
                            "\u7406\u89e3 InnoDB \u7684\u5b58\u50a8\u7ed3\u6784",
                            "\u77e5\u9053\u884c\u9501\u548c\u8868\u9501\u7684\u533a\u522b",
                            "\u7406\u89e3 MySQL \u9ed8\u8ba4\u7684 REPEATABLE READ",
                        ],
                    },
                    {
                        "id": "db-nosql",
                        "title": "NoSQL \u6570\u636e\u5e93\u6982\u89c8",
                        "summary": "\u4e86\u89e3\u6587\u6863\u6570\u636e\u5e93\u3001\u952e\u503c\u5b58\u50a8\u3001\u5217\u65cf\u6570\u636e\u5e93\u548c\u56fe\u6570\u636e\u5e93\u3002",
                        "path": "database/db_nosql.md",
                        "difficulty": "\u8fdb\u9636",
                        "estimated_minutes": 40,
                        "tags": ["NoSQL", "MongoDB", "Redis"],
                        "prerequisites": ["db-normalization"],
                        "outcomes": [
                            "\u7406\u89e3 NoSQL \u7684\u5206\u7c7b\u548c\u9002\u7528\u573a\u666f",
                            "\u77e5\u9053 MongoDB \u548c Redis \u7684\u57fa\u672c\u7528\u6cd5",
                            "\u80fd\u6839\u636e\u573a\u666f\u9009\u62e9\u5408\u9002\u7684\u6570\u636e\u5e93\u7c7b\u578b",
                        ],
                    },
                ],
            },
            {
                "id": "db-projects",
                "title": "\u5b9e\u6218\u6a21\u5757 \u00b7 \u8c03\u4f18\u4e0e\u9879\u76ee",
                "summary": "\u638c\u63e1\u6162\u67e5\u8be2\u8bca\u65ad\u3001\u5e76\u53d1\u63a7\u5236\u548c\u5b8c\u6574\u7684\u6570\u636e\u5e93\u9879\u76ee\u5b9e\u8df5\u3002",
                "lessons": [
                    {
                        "id": "db-tuning",
                        "title": "\u6162\u67e5\u8be2\u8bca\u65ad\u4e0e\u6027\u80fd\u8c03\u4f18",
                        "summary": "\u5b66\u4e60\u6162\u67e5\u8be2\u65e5\u5fd7\u3001\u7d22\u5f15\u4f18\u5316\u548c SQL \u6539\u5199\u7b56\u7565\u3002",
                        "path": "database/db_tuning.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 50,
                        "tags": ["\u6162\u67e5\u8be2", "\u8c03\u4f18", "\u6027\u80fd"],
                        "prerequisites": ["db-explain"],
                        "outcomes": [
                            "\u4f1a\u5f00\u542f\u548c\u5206\u6790\u6162\u67e5\u8be2\u65e5\u5fd7",
                            "\u80fd\u901a\u8fc7\u7d22\u5f15\u4f18\u5316\u67e5\u8be2",
                            "\u77e5\u9053\u5e38\u89c1\u7684 SQL \u6027\u80fd\u9677\u9631",
                        ],
                    },
                    {
                        "id": "db-connection-pool",
                        "title": "\u8fde\u63a5\u6c60\u4e0e\u9ad8\u5e76\u53d1\u5904\u7406",
                        "summary": "\u7406\u89e3\u8fde\u63a5\u6c60\u7684\u539f\u7406\u3001\u914d\u7f6e\u548c\u9ad8\u5e76\u53d1\u573a\u666f\u4e0b\u7684\u6570\u636e\u5e93\u4f18\u5316\u3002",
                        "path": "database/db_connection_pool.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": [
                            "\u8fde\u63a5\u6c60",
                            "\u9ad8\u5e76\u53d1",
                            "\u4f18\u5316",
                        ],
                        "prerequisites": ["db-transactions"],
                        "outcomes": [
                            "\u7406\u89e3\u8fde\u63a5\u6c60\u7684\u5de5\u4f5c\u539f\u7406",
                            "\u4f1a\u914d\u7f6e\u5408\u7406\u7684\u8fde\u63a5\u6c60\u53c2\u6570",
                            "\u77e5\u9053\u9ad8\u5e76\u53d1\u4e0b\u7684\u6570\u636e\u5e93\u4f18\u5316\u7b56\u7565",
                        ],
                    },
                    {
                        "id": "db-backup-recovery",
                        "title": "\u5907\u4efd\u3001\u6062\u590d\u4e0e\u9ad8\u53ef\u7528",
                        "summary": "\u5b66\u4e60\u6570\u636e\u5e93\u5907\u4efd\u7b56\u7565\u3001\u6062\u590d\u65b9\u6cd5\u548c\u4e3b\u4ece\u590d\u5236\u3002",
                        "path": "database/db_backup_recovery.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 45,
                        "tags": ["\u5907\u4efd", "\u6062\u590d", "\u4e3b\u4ece"],
                        "prerequisites": ["db-transactions"],
                        "outcomes": [
                            "\u4f1a\u5236\u5b9a\u5408\u7406\u7684\u5907\u4efd\u7b56\u7565",
                            "\u7406\u89e3 WAL \u548c\u65f6\u95f4\u70b9\u6062\u590d",
                            "\u77e5\u9053\u4e3b\u4ece\u590d\u5236\u7684\u57fa\u672c\u539f\u7406",
                        ],
                    },
                    {
                        "id": "db-project-complete",
                        "title": "\u7efc\u5408\u5b9e\u6218\u9879\u76ee",
                        "summary": "\u4ece\u96f6\u5f00\u59cb\u8bbe\u8ba1\u5e76\u5b9e\u73b0\u4e00\u4e2a\u5b8c\u6574\u7684\u6570\u636e\u5e93\u9879\u76ee\u3002",
                        "path": "database/db_project_complete.md",
                        "difficulty": "\u7efc\u5408",
                        "estimated_minutes": 90,
                        "tags": ["\u9879\u76ee", "\u5b9e\u6218", "\u7efc\u5408"],
                        "prerequisites": ["db-tuning"],
                        "outcomes": [
                            "\u80fd\u72ec\u7acb\u8bbe\u8ba1\u5e76\u5b9e\u73b0\u4e00\u4e2a\u6570\u636e\u5e93\u9879\u76ee",
                            "\u4f1a\u505a\u5b8c\u6574\u7684\u6027\u80fd\u8c03\u4f18",
                            "\u638c\u63e1\u5907\u4efd\u6062\u590d\u548c\u76d1\u63a7\u65b9\u6848",
                            "\u5177\u5907\u5b8c\u6574\u7684\u6570\u636e\u5e93\u8fd0\u7ef4\u80fd\u529b",
                        ],
                    },
                ],
            },
        ],
    }
)

print(
    "Database track added:",
    sum(len(m["lessons"]) for m in data["tracks"][-1]["modules"]),
    "lessons",
)
save(data)
print("Saved Database track")
