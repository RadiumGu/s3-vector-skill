#!/usr/bin/env python3
"""
文档摄入脚本 — 分块 + embedding + 写入 S3 Vectors。

用法：
    # 单文件
    python3 ingest.py --bucket my-kb --file doc.md

    # stdin（配合 web_fetch）
    echo "内容" | python3 ingest.py --bucket my-kb --doc-id "article-001"

    # 目录批量
    python3 ingest.py --bucket my-kb --dir /docs/ --glob "*.md"

    # 增量同步
    python3 ingest.py --bucket my-kb --dir /docs/ --sync

    # 删除
    python3 ingest.py --bucket my-kb --delete --doc-id "old-doc"

    # Contextual 模式（高召回率）
    python3 ingest.py --bucket my-kb --file doc.md --contextual
"""

import argparse
import glob as glob_mod
import hashlib
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import base_parser, create_client, success_output, fail, run, handle_error
from chunker import chunk_text, count_tokens
from embed import embed_text, EMBED_DIMENSION

# ── 索引维度校验 ──────────────────────────────────────────────────────
def _validate_index_dimension(client, bucket: str, index: str, expected_dim: int) -> None:
    """校验索引维度与当前 embedding 模型匹配"""
    try:
        resp = client.get_index(vectorBucketName=bucket, indexName=index)
        index_dim = resp.get("index", {}).get("dimension", 0)
        if index_dim and index_dim != expected_dim:
            fail(
                f"维度不匹配！索引 '{index}' 维度={index_dim}，"
                f"当前 embedding 模型维度={expected_dim}。\n"
                f"解决方案：\n"
                f"  1. 删除旧索引并重建: python3 delete_index.py --bucket {bucket} --index {index}\n"
                f"     然后: python3 create_index.py --bucket {bucket} --index {index} --dimension {expected_dim}\n"
                f"  2. 或切换回匹配的 embedding 模型"
            )
    except SystemExit:
        raise
    except Exception as e:
        import logging
        logging.warning(f"索引维度校验跳过: {e}")


# ── HTML 支持 ─────────────────────────────────────────────────────────
def extract_html_text(html: str) -> str:
    """从 HTML 提取纯文本"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        # fallback: 简单去标签
        text = re.sub(r'<[^>]+>', '', html)
        return re.sub(r'\n{3,}', '\n\n', text).strip()


# ── Contextual prefix ────────────────────────────────────────────────
def generate_context_prefix(full_doc: str, chunk_content: str,
                            region: str, model: str, profile=None) -> str:
    """用 LLM 为 chunk 生成上下文前缀"""
    import boto3
    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(**session_kwargs)
    client = session.client("bedrock-runtime", region_name=region)

    # 截断文档避免超 token 限制
    doc_truncated = full_doc[:12000]

    prompt = f"""<document>
{doc_truncated}
</document>

以下是文档中的一个片段：
<chunk>
{chunk_content[:2000]}
</chunk>

请用 2-3 句简短的话描述这个片段在文档中的位置和上下文，帮助读者理解它属于哪部分、讨论什么主题。只输出描述，不要解释。"""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    })

    try:
        resp = client.invoke_model(modelId=model, body=body,
                                   contentType="application/json", accept="application/json")
        result = json.loads(resp["body"].read())
        return result["content"][0]["text"].strip()
    except Exception as e:
        print(f"  ⚠️  Context prefix 生成失败: {e}", file=sys.stderr)
        return ""


# ── 文档 ID 生成 ─────────────────────────────────────────────────────
def make_doc_id(file_path: str = "", base_dir: str = "") -> str:
    """从文件路径生成 doc_id"""
    if base_dir and file_path.startswith(base_dir):
        rel = os.path.relpath(file_path, base_dir)
    else:
        rel = os.path.basename(file_path)
    # 去扩展名，特殊字符替换
    name = os.path.splitext(rel)[0]
    name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff_-]', '-', name)
    name = re.sub(r'-{2,}', '-', name).strip('-')
    return name[:128] or hashlib.md5(file_path.encode()).hexdigest()[:16]


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


# ── 写入 S3 Vectors ──────────────────────────────────────────────────
def put_chunks(client, bucket: str, index: str, doc_id: str, chunks,
               source: str, tags: str, file_type: str, full_text: str,
               contextual: bool, contextual_model: str, region: str,
               profile=None, author: str = ""):
    """将 chunks 生成 embedding 并写入 S3 Vectors"""
    vectors = []
    total = len(chunks)
    doc_hash = content_hash(full_text)

    for i, chunk in enumerate(chunks):
        # Contextual prefix
        ctx_prefix = ""
        if contextual:
            print(f"  [{i+1}/{total}] 生成上下文前缀...", file=sys.stderr)
            ctx_prefix = generate_context_prefix(
                full_text, chunk.content, region, contextual_model, profile)
            time.sleep(0.3)  # 限流

        # Embedding 输入：context_prefix + content（如有）
        embed_input = (ctx_prefix + "\n\n" + chunk.content).strip() if ctx_prefix else chunk.content
        print(f"  [{i+1}/{total}] Embedding ({chunk.tokens} tokens)...", file=sys.stderr)
        vec = embed_text(embed_input, region=region, profile=profile)

        # 构建 vector
        # S3 Vectors metadata 限制 2048 bytes filterable (UTF-8 encoded)
        # 先构建固定字段，然后用剩余空间给 content
        metadata = {
            "doc_id": doc_id,
            "chunk_index": str(chunk.index),
            "total_chunks": str(total),
            "content_hash": doc_hash,
            "file_type": file_type,
            "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if source:
            metadata["source"] = source[:200]
        if tags:
            metadata["tags"] = tags[:100]
        if author:
            metadata["author"] = author[:100]
        if chunk.heading_path:
            metadata["heading_path"] = chunk.heading_path[:150]
        if ctx_prefix:
            metadata["context_prefix"] = ctx_prefix[:200]

        # 计算已用 bytes，留给 content
        used_bytes = len(json.dumps(metadata, ensure_ascii=False).encode("utf-8"))
        content_byte_budget = max(100, 1900 - used_bytes)
        # 按 byte 截断 content
        content_preview = chunk.content
        while len(content_preview.encode("utf-8")) > content_byte_budget:
            content_preview = content_preview[:len(content_preview) * 3 // 4]
        metadata["content"] = content_preview

        vectors.append({
            "key": f"{doc_id}.chunk-{chunk.index:04d}",
            "data": {"float32": vec},
            "metadata": metadata,
        })

        time.sleep(0.1)  # embedding 限流

    # 批量写入（每批 100）
    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start:start + batch_size]
        try:
            client.put_vectors(
                vectorBucketName=bucket,
                indexName=index,
                vectors=batch,
            )
        except Exception as e:
            handle_error(e)

    return len(vectors)


# ── 删除文档 ─────────────────────────────────────────────────────────
def delete_doc(client, bucket: str, index: str, doc_id: str):
    """删除指定 doc_id 的所有 chunk"""
    # 列出所有 key
    keys = []
    next_token = None
    while True:
        kwargs = {"vectorBucketName": bucket, "indexName": index}
        if next_token:
            kwargs["nextToken"] = next_token
        try:
            resp = client.list_vectors(**kwargs)
        except Exception as e:
            handle_error(e)
            return 0

        for v in resp.get("vectors", []):
            if v["key"].startswith(f"{doc_id}.chunk-"):
                keys.append(v["key"])

        next_token = resp.get("nextToken")
        if not next_token:
            break

    if not keys:
        return 0

    # 批量删除
    batch_size = 100
    for start in range(0, len(keys), batch_size):
        batch = keys[start:start + batch_size]
        try:
            client.delete_vectors(
                vectorBucketName=bucket, indexName=index, keys=batch)
        except Exception as e:
            handle_error(e)

    return len(keys)


# ── 增量同步 ─────────────────────────────────────────────────────────
def get_existing_hashes(client, bucket: str, index: str) -> dict:
    """获取索引中所有 doc_id → content_hash 的映射"""
    doc_hashes = {}
    next_token = None
    while True:
        kwargs = {"vectorBucketName": bucket, "indexName": index,
                  "returnMetadata": True}
        if next_token:
            kwargs["nextToken"] = next_token
        try:
            resp = client.list_vectors(**kwargs)
        except Exception:
            break

        for v in resp.get("vectors", []):
            meta = v.get("metadata", {})
            doc_id = meta.get("doc_id", "")
            if doc_id and meta.get("chunk_index") == "0":
                doc_hashes[doc_id] = meta.get("content_hash", "")

        next_token = resp.get("nextToken")
        if not next_token:
            break

    return doc_hashes


# ── 主函数 ────────────────────────────────────────────────────────────
def main():
    parser = base_parser("文档摄入 — 分块 + embedding + 写入 S3 Vectors")
    parser.add_argument("--index", default="docs-v1", help="索引名称")
    parser.add_argument("--file", help="单文件路径")
    parser.add_argument("--dir", help="目录路径（批量摄入）")
    parser.add_argument("--glob", default="*.md,*.txt,*.html",
                        help="文件匹配模式，逗号分隔")
    parser.add_argument("--doc-id", help="文档标识符（默认自动生成）")
    parser.add_argument("--source", help="来源标识（URL 或描述）")
    parser.add_argument("--tags", help="逗号分隔标签")
    parser.add_argument("--chunk-size", type=int, default=512, help="目标 chunk 大小（tokens）")
    parser.add_argument("--chunk-overlap", type=int, default=64, help="chunk 重叠 tokens")
    parser.add_argument("--chunking", default="auto",
                        choices=["auto", "recursive", "heading"],
                        help="分块策略")
    parser.add_argument("--contextual", action="store_true",
                        help="启用 Contextual Chunking（LLM 生成上下文前缀）")
    parser.add_argument("--contextual-model",
                        default="anthropic.claude-3-haiku-20240307-v1:0",
                        help="Contextual prefix 使用的 LLM")
    parser.add_argument("--sync", action="store_true", help="增量同步模式")
    parser.add_argument("--delete", action="store_true", help="删除指定 doc-id 的所有 chunk")
    parser.add_argument("--author", default="", help="文档作者（写入 metadata，可用于过滤）")
    parser.add_argument("--dry-run", action="store_true", help="只输出计划，不执行")
    args = parser.parse_args()

    client = create_client(args)
    embed_region = getattr(args, "embed_region", None) or args.region

    # 启动校验：索引维度与 embedding 模型匹配
    if not args.delete:
        _validate_index_dimension(client, args.bucket, args.index, EMBED_DIMENSION)

    # 删除模式
    if args.delete:
        if not args.doc_id:
            fail("--delete 需要指定 --doc-id")
        if args.dry_run:
            print(json.dumps({"action": "delete", "doc_id": args.doc_id, "dry_run": True}))
            return
        count = delete_doc(client, args.bucket, args.index, args.doc_id)
        success_output("ingest_delete", doc_id=args.doc_id, deleted_chunks=count)
        return

    # 收集要处理的文件
    files = []
    if args.file:
        files.append(args.file)
    elif args.dir:
        patterns = args.glob.split(",")
        for pattern in patterns:
            files.extend(glob_mod.glob(os.path.join(args.dir, "**", pattern.strip()),
                                       recursive=True))
        files = sorted(set(files))
    elif not sys.stdin.isatty():
        # stdin 模式
        pass
    else:
        fail("请指定 --file、--dir 或通过 stdin 输入")

    # stdin 模式
    if not files and not sys.stdin.isatty():
        text = sys.stdin.read()
        if not text.strip():
            fail("stdin 为空")
        doc_id = args.doc_id or "stdin-" + content_hash(text)[:12]
        chunks = chunk_text(text, strategy=args.chunking,
                            chunk_size=args.chunk_size,
                            chunk_overlap=args.chunk_overlap, file_type="txt")
        if args.dry_run:
            print(json.dumps({"action": "ingest", "doc_id": doc_id,
                              "chunks": len(chunks), "dry_run": True}, ensure_ascii=False))
            return
        count = put_chunks(client, args.bucket, args.index, doc_id, chunks,
                           args.source or "stdin", args.tags or "", "txt", text,
                           args.contextual, args.contextual_model, embed_region,
                           getattr(args, "profile", None), author=args.author)
        success_output("ingest", doc_id=doc_id, chunks_written=count)
        return

    # 增量同步：获取已有 hash
    existing_hashes = {}
    if args.sync:
        print("获取索引中已有文档 hash...", file=sys.stderr)
        existing_hashes = get_existing_hashes(client, args.bucket, args.index)
        print(f"  已有 {len(existing_hashes)} 个文档", file=sys.stderr)

    # 处理文件
    results = {"ingested": 0, "skipped": 0, "deleted": 0, "chunks_written": 0, "files": []}
    processed_doc_ids = set()

    for fpath in files:
        with open(fpath) as f:
            text = f.read()

        if not text.strip():
            continue

        doc_id = args.doc_id if (args.doc_id and len(files) == 1) else make_doc_id(
            fpath, args.dir or "")
        processed_doc_ids.add(doc_id)

        # 检测文件类型
        ext = fpath.rsplit(".", 1)[-1].lower() if "." in fpath else "txt"
        if ext in ("html", "htm"):
            text = extract_html_text(text)
            ext = "html"

        # 增量同步：检查 hash
        doc_hash = content_hash(text)
        if args.sync and existing_hashes.get(doc_id) == doc_hash:
            results["skipped"] += 1
            continue

        # 分块
        chunks = chunk_text(text, strategy=args.chunking,
                            chunk_size=args.chunk_size,
                            chunk_overlap=args.chunk_overlap, file_type=ext)

        if args.dry_run:
            results["files"].append({
                "file": fpath, "doc_id": doc_id, "chunks": len(chunks),
                "tokens": sum(c.tokens for c in chunks),
            })
            results["ingested"] += 1
            results["chunks_written"] += len(chunks)
            continue

        # 如果是 sync 且 hash 不同，先删除旧的
        if args.sync and doc_id in existing_hashes:
            delete_doc(client, args.bucket, args.index, doc_id)

        print(f"摄入: {fpath} → {doc_id} ({len(chunks)} chunks)", file=sys.stderr)
        count = put_chunks(client, args.bucket, args.index, doc_id, chunks,
                           args.source or fpath, args.tags or "", ext, text,
                           args.contextual, args.contextual_model, embed_region,
                           getattr(args, "profile", None), author=args.author)
        results["ingested"] += 1
        results["chunks_written"] += count
        results["files"].append({"file": fpath, "doc_id": doc_id, "chunks": count})

    # 增量同步：删除已移除的文档
    if args.sync and not args.dry_run:
        for old_id in existing_hashes:
            if old_id not in processed_doc_ids:
                count = delete_doc(client, args.bucket, args.index, old_id)
                results["deleted"] += count
                print(f"删除过期: {old_id} ({count} chunks)", file=sys.stderr)

    if args.dry_run:
        results["dry_run"] = True

    print(json.dumps({"success": True, "action": "ingest", **results},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run(main)
