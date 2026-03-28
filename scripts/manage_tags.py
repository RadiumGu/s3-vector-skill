#!/usr/bin/env python3
"""
Tag 管理脚本 — 增删改查预定义 tag + 重新分类已有文档。

用法：
    # 查看所有 tag
    python3 manage_tags.py --list

    # 添加 tag
    python3 manage_tags.py --add finance --label "理财" --keywords "理财,投资,基金,股票"

    # 删除 tag
    python3 manage_tags.py --remove learning

    # 给 tag 追加关键词
    python3 manage_tags.py --update work --add-keywords "terraform,docker"

    # 重新分类文档
    python3 manage_tags.py --reclassify --doc-id "REVIEW-2026-03-28" --new-tag ops \
      --bucket openclaw-kb --index docs-v1
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import base_parser, create_client, fail, run, handle_error

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
TAGS_FILE = os.path.join(CONFIG_DIR, "tags.json")

TAG_NAME_RE = re.compile(r'^[\w\u4e00-\u9fff\u3400-\u4dbf][\w\u4e00-\u9fff\u3400-\u4dbf-]*$')


def load_tags() -> dict:
    if not os.path.exists(TAGS_FILE):
        return {"tags": {}, "default_tag": None, "allow_custom": False}
    with open(TAGS_FILE) as f:
        return json.load(f)


def save_tags(data: dict):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(TAGS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    parser = base_parser("Tag 管理 — 增删改查预定义 tag", bucket_required=False)
    parser.add_argument("--list", action="store_true", help="列出所有 tag")
    parser.add_argument("--add", metavar="TAG_NAME", help="添加新 tag")
    parser.add_argument("--remove", metavar="TAG_NAME", help="删除 tag")
    parser.add_argument("--update", metavar="TAG_NAME", help="更新 tag")
    parser.add_argument("--label", help="tag 显示名称（中文）")
    parser.add_argument("--keywords", help="逗号分隔关键词")
    parser.add_argument("--add-keywords", help="追加关键词（逗号分隔）")
    parser.add_argument("--description", help="tag 描述")
    parser.add_argument("--reclassify", action="store_true", help="重新分类文档")
    parser.add_argument("--doc-id", help="要重新分类的文档 ID")
    parser.add_argument("--new-tag", help="新 tag 名称")
    parser.add_argument("--index", default="docs-v1", help="索引名称")
    args = parser.parse_args()

    config = load_tags()

    # ── 列出 ──
    if args.list:
        if not config["tags"]:
            print(json.dumps({"success": True, "tags": {}, "message": "暂无 tag"}, ensure_ascii=False))
            return
        output = {"success": True, "tags": {}}
        for name, info in sorted(config["tags"].items()):
            output["tags"][name] = {
                "label": info.get("label", ""),
                "keywords": info.get("keywords", []),
                "description": info.get("description", ""),
            }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # ── 添加 ──
    if args.add:
        name = args.add.strip()
        if not TAG_NAME_RE.match(name):
            fail(f"Tag 名称 '{name}' 不合法，允许中文、英文、数字和连字符")
        if name in config["tags"]:
            fail(f"Tag '{name}' 已存在")
        if not args.keywords:
            fail("添加 tag 需要提供 --keywords（至少 2 个关键词）")
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        if len(keywords) < 2:
            fail("至少需要 2 个关键词")

        config["tags"][name] = {
            "label": args.label or name,
            "keywords": keywords,
            "description": args.description or "",
        }
        save_tags(config)
        print(json.dumps({
            "success": True,
            "action": "add_tag",
            "tag": name,
            "label": config["tags"][name]["label"],
            "keywords": keywords,
        }, ensure_ascii=False, indent=2))
        return

    # ── 删除 ──
    if args.remove:
        name = args.remove.strip()
        if name not in config["tags"]:
            fail(f"Tag '{name}' 不存在")
        del config["tags"][name]
        save_tags(config)
        print(json.dumps({
            "success": True,
            "action": "remove_tag",
            "tag": name,
            "message": f"已删除 tag '{name}'。已入库文档的 tag 不受影响。",
        }, ensure_ascii=False, indent=2))
        return

    # ── 更新 ──
    if args.update:
        name = args.update.strip()
        if name not in config["tags"]:
            fail(f"Tag '{name}' 不存在")
        tag = config["tags"][name]
        if args.label:
            tag["label"] = args.label
        if args.description:
            tag["description"] = args.description
        if args.add_keywords:
            new_kw = [k.strip() for k in args.add_keywords.split(",") if k.strip()]
            existing = tag.get("keywords", [])
            tag["keywords"] = list(dict.fromkeys(existing + new_kw))  # 去重保序
        if args.keywords:
            tag["keywords"] = [k.strip() for k in args.keywords.split(",") if k.strip()]
        save_tags(config)
        print(json.dumps({
            "success": True,
            "action": "update_tag",
            "tag": name,
            "updated": tag,
        }, ensure_ascii=False, indent=2))
        return

    # ── 重新分类文档 ──
    if args.reclassify:
        if not args.doc_id:
            fail("--reclassify 需要 --doc-id")
        if not args.new_tag:
            fail("--reclassify 需要 --new-tag")

        client = create_client(args)
        doc_id = args.doc_id
        new_tag = args.new_tag.strip()

        # 列出该文档的所有 chunk
        keys = []
        vectors_data = []
        next_token = None
        while True:
            kwargs = {"vectorBucketName": args.bucket, "indexName": args.index,
                      "returnMetadata": True}
            if next_token:
                kwargs["nextToken"] = next_token
            try:
                resp = client.list_vectors(**kwargs)
            except Exception as e:
                handle_error(e)
                return

            for v in resp.get("vectors", []):
                meta = v.get("metadata", {})
                if meta.get("doc_id") == doc_id:
                    keys.append(v["key"])
                    vectors_data.append(v)

            next_token = resp.get("nextToken")
            if not next_token:
                break

        if not keys:
            fail(f"未找到 doc_id='{doc_id}' 的向量")

        # 获取完整向量数据（含 data）
        try:
            full_resp = client.get_vectors(
                vectorBucketName=args.bucket,
                indexName=args.index,
                keys=keys,
                returnData=True,
                returnMetadata=True,
            )
        except Exception as e:
            handle_error(e)
            return

        # 更新 tag 并重新写入
        updated_vectors = []
        for v in full_resp.get("vectors", []):
            meta = v.get("metadata", {})
            meta["tags"] = new_tag
            updated_vectors.append({
                "key": v["key"],
                "data": v["data"],
                "metadata": meta,
            })

        # 批量写入（覆盖）
        batch_size = 100
        for start in range(0, len(updated_vectors), batch_size):
            batch = updated_vectors[start:start + batch_size]
            try:
                client.put_vectors(
                    vectorBucketName=args.bucket,
                    indexName=args.index,
                    vectors=batch,
                )
            except Exception as e:
                handle_error(e)
                return

        print(json.dumps({
            "success": True,
            "action": "reclassify",
            "doc_id": doc_id,
            "new_tag": new_tag,
            "chunks_updated": len(updated_vectors),
        }, ensure_ascii=False, indent=2))
        return

    # 没有指定操作
    parser.print_help()


if __name__ == "__main__":
    run(main)
