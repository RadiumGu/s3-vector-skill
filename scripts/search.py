#!/usr/bin/env python3
"""
语义搜索脚本 — 查询 embedding + S3 Vectors 相似度搜索 + 格式化输出。

用法：
    # JSON 输出
    python3 search.py --bucket my-kb --query "EKS Pod 调度失败" --top-k 5

    # Markdown 输出（适合 Agent 回复）
    python3 search.py --bucket my-kb --query "EKS Pod 调度失败" --output markdown

    # 带过滤
    python3 search.py --bucket my-kb --query "..." --filter '{"file_type": {"$eq": "md"}}'
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import base_parser, create_client, fail, run, handle_error
from embed import embed_text


def main():
    parser = base_parser("语义搜索 — query embedding + S3 Vectors 相似度搜索")
    parser.add_argument("--index", default="docs-v1", help="索引名称")
    parser.add_argument("--query", required=True, help="搜索查询文本")
    parser.add_argument("--top-k", type=int, default=5, help="返回最相关的 K 个结果")
    parser.add_argument("--output", choices=["json", "markdown"], default="json",
                        help="输出格式")
    parser.add_argument("--filter", help="过滤条件 JSON")
    parser.add_argument("--threshold", type=float, default=0.6,
                        help="相似度分数阈值（0~1，默认 0.6）")
    parser.add_argument("--embed-region", help="Bedrock Embedding Region")
    args = parser.parse_args()

    # 1. 生成查询向量
    embed_region = args.embed_region or args.region
    try:
        query_vec = embed_text(args.query, region=embed_region,
                               profile=getattr(args, "profile", None))
    except Exception as e:
        fail(f"Query embedding 失败: {e}")

    # 2. S3 Vectors 查询
    client = create_client(args)
    query_kwargs = {
        "vectorBucketName": args.bucket,
        "indexName": args.index,
        "queryVector": {"float32": query_vec},
        "topK": args.top_k,
        "returnDistance": True,
        "returnMetadata": True,
    }
    if args.filter:
        try:
            query_kwargs["filter"] = json.loads(args.filter)
        except json.JSONDecodeError:
            fail(f"--filter JSON 解析失败: {args.filter}")

    try:
        resp = client.query_vectors(**query_kwargs)
    except Exception as e:
        handle_error(e)
        return

    results = resp.get("vectors", [])

    # 3. distance → score 转换 + 阈值过滤
    scored_results = []
    for r in results:
        distance = r.get("distance", 0)
        score = 1 - (distance / 2)  # cosine distance [0,2] → similarity [0,1]
        if score >= args.threshold:
            scored_results.append({**r, "score": score})

    # 4. 格式化输出
    if args.output == "markdown":
        _output_markdown(args.query, scored_results, args.top_k)
    else:
        _output_json(args.query, scored_results, args)


def _output_markdown(query: str, results: list, top_k: int):
    """Markdown 格式输出（适合 Agent 回复用户）"""
    if not results:
        print(f"🤖 知识库中未找到与 \"{query}\" 相关的内容。")
        return

    lines = [f"📚 知识库搜索结果（Top {min(top_k, len(results))} for \"{query}\"）：", ""]

    for i, r in enumerate(results):
        meta = r.get("metadata", {})
        score = r["score"]
        content = meta.get("content", "")
        source = meta.get("source", "unknown")
        chunk_idx = meta.get("chunk_index", "?")
        total = meta.get("total_chunks", "?")
        heading = meta.get("heading_path", "")
        ctx_prefix = meta.get("context_prefix", "")

        title = heading or meta.get("doc_id", r["key"])

        lines.append(f"**{i+1}. [{score:.2f}] {title}**")
        lines.append(f"来源：{source} (chunk {chunk_idx}/{total})")

        if ctx_prefix:
            lines.append(f"上下文：{ctx_prefix}")

        # 内容预览（前 200 字符）
        preview = content[:200].replace("\n", " ")
        if len(content) > 200:
            preview += "..."
        lines.append(f"> {preview}")
        lines.append("")

    print("\n".join(lines))


def _output_json(query: str, results: list, args):
    """JSON 格式输出"""
    output = {
        "success": True,
        "action": "search",
        "query": query,
        "bucket": args.bucket,
        "index": args.index,
        "top_k": args.top_k,
        "threshold": args.threshold,
        "results_count": len(results),
        "results": [],
    }

    for i, r in enumerate(results):
        meta = r.get("metadata", {})
        entry = {
            "rank": i + 1,
            "score": round(r["score"], 4),
            "doc_id": meta.get("doc_id", ""),
            "source": meta.get("source", ""),
            "chunk_index": meta.get("chunk_index", ""),
            "total_chunks": meta.get("total_chunks", ""),
            "heading_path": meta.get("heading_path", ""),
            "content_preview": meta.get("content", "")[:300],
            "tags": meta.get("tags", ""),
        }
        if meta.get("context_prefix"):
            entry["context_prefix"] = meta["context_prefix"]
        output["results"].append(entry)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run(main)
