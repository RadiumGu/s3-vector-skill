#!/usr/bin/env python3
"""
知识库状态查询 — 文档数、chunk 数、tag 分布、最近入库。

用法：
    python3 stats.py --bucket openclaw-kb --index docs-v1
    python3 stats.py --bucket openclaw-kb --index docs-v1 --tags
    python3 stats.py --bucket openclaw-kb --index docs-v1 --output markdown
"""

import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import base_parser, create_client, run, handle_error


def main():
    parser = base_parser("知识库状态查询")
    parser.add_argument("--index", default="docs-v1", help="索引名称")
    parser.add_argument("--tags", action="store_true", help="只输出 tag 分布")
    parser.add_argument("--output", choices=["json", "markdown"], default="json",
                        help="输出格式")
    args = parser.parse_args()

    client = create_client(args)

    # 遍历所有向量收集统计
    docs = {}  # doc_id → {chunks, tag, ingested_at, source}
    total_chunks = 0
    tag_stats = defaultdict(lambda: {"docs": set(), "chunks": 0})
    next_token = None

    while True:
        kwargs = {
            "vectorBucketName": args.bucket,
            "indexName": args.index,
            "returnMetadata": True,
        }
        if next_token:
            kwargs["nextToken"] = next_token

        try:
            resp = client.list_vectors(**kwargs)
        except Exception as e:
            handle_error(e)
            return

        for v in resp.get("vectors", []):
            total_chunks += 1
            meta = v.get("metadata", {})
            doc_id = meta.get("doc_id", "unknown")
            tag = meta.get("tags", "").split(",")[0].strip() if meta.get("tags") else ""
            ingested_at = meta.get("ingested_at", "")

            if doc_id not in docs:
                docs[doc_id] = {
                    "chunks": 0,
                    "tag": tag or "untagged",
                    "ingested_at": ingested_at[:10] if ingested_at else "",
                    "source": meta.get("source", ""),
                }
            docs[doc_id]["chunks"] += 1

            tag_key = tag or "untagged"
            tag_stats[tag_key]["docs"].add(doc_id)
            tag_stats[tag_key]["chunks"] += 1

        next_token = resp.get("nextToken")
        if not next_token:
            break

    # 整理 tag 统计
    tag_summary = {}
    for t, s in sorted(tag_stats.items()):
        tag_summary[t] = {"docs": len(s["docs"]), "chunks": s["chunks"]}

    # 最近入库（按时间倒序，取前 10）
    recent = sorted(docs.items(), key=lambda x: x[1]["ingested_at"], reverse=True)[:10]

    if args.tags:
        # 只输出 tag 分布
        if args.output == "markdown":
            print("📊 Tag 分布：\n")
            for t, s in tag_summary.items():
                label = t if t != "untagged" else "未分类"
                print(f"  {label}: {s['docs']} 篇 ({s['chunks']} chunks)")
        else:
            print(json.dumps({"success": True, "tags": tag_summary}, ensure_ascii=False, indent=2))
        return

    # 完整状态
    result = {
        "success": True,
        "action": "stats",
        "bucket": args.bucket,
        "index": args.index,
        "total_docs": len(docs),
        "total_chunks": total_chunks,
        "tags": tag_summary,
        "recent": [
            {
                "doc_id": doc_id,
                "tag": info["tag"],
                "chunks": info["chunks"],
                "ingested_at": info["ingested_at"],
                "source": info["source"][:100],
            }
            for doc_id, info in recent
        ],
    }

    if args.output == "markdown":
        _output_markdown(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _output_markdown(data: dict):
    lines = [
        f"📊 知识库状态：",
        "",
        f"文档数：{data['total_docs']}",
        f"Chunk 总数：{data['total_chunks']}",
        "",
        "按分类：",
    ]

    for t, s in data["tags"].items():
        label = t if t != "untagged" else "未分类"
        lines.append(f"  {label}: {s['docs']} 篇 ({s['chunks']} chunks)")

    if data["recent"]:
        lines.append("")
        lines.append("最近入库：")
        for r in data["recent"]:
            tag_str = f"[{r['tag']}]" if r["tag"] != "untagged" else "[未分类]"
            lines.append(f"  {tag_str} {r['doc_id']} — {r['chunks']} chunks ({r['ingested_at']})")

    print("\n".join(lines))


if __name__ == "__main__":
    run(main)
