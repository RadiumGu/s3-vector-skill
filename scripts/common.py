#!/usr/bin/env python3
"""
公共基础模块 — 所有 S3 向量桶脚本复用的客户端初始化、错误处理和 Skill 扫描逻辑。
"""

import argparse
import hashlib
import json
import os
import re
import sys


# ── 默认 Skill 扫描目录 ──────────────────────────────────────────────


def base_parser(description, bucket_required=True):
    """创建基础参数解析器，包含凭证和连接参数"""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"),
        help="AWS Region，如 ap-northeast-1（或设置环境变量 AWS_DEFAULT_REGION）",
    )
    parser.add_argument(
        "--bucket",
        required=bucket_required,
        default=None,
        help="S3 向量桶名称，如 my-vector-bucket",
    )
    parser.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE"),
        help="AWS CLI 配置文件名（可选，默认使用实例 IAM Role 或环境变量凭证）",
    )
    return parser


def create_client(args):
    """根据解析后的参数创建 boto3 s3vectors 客户端"""
    try:
        import boto3
    except ImportError:
        fail("boto3 未安装，请运行: pip3 install boto3 --upgrade")

    session_kwargs = {}
    if getattr(args, "profile", None):
        session_kwargs["profile_name"] = args.profile

    try:
        session = boto3.Session(**session_kwargs)
        client = session.client("s3vectors", region_name=args.region)
        return client
    except Exception as e:
        fail(f"创建 AWS 客户端失败: {e}")


def success_output(data):
    """输出成功结果的 JSON（自动处理 datetime 序列化）"""
    result = {"success": True}
    result.update(data)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))


def _json_default(obj):
    """JSON 序列化 fallback：处理 datetime 等非标准类型"""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def fail(message):
    """输出失败结果并退出"""
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False, indent=2))
    sys.exit(1)


def handle_error(e):
    """统一处理 AWS 异常（含 ThrottlingException 提示）"""
    try:
        from botocore.exceptions import ClientError, BotoCoreError
        if isinstance(e, ClientError):
            err = e.response.get("Error", {})
            error_code = err.get("Code", "Unknown")
            message = err.get("Message", str(e))

            # ThrottlingException 特殊提示 (#9)
            if error_code in ("ThrottlingException", "Throttling", "TooManyRequestsException"):
                message = f"请求被限流: {message}。建议：稍后重试或降低并发。"

            print(json.dumps({
                "success": False,
                "error": f"服务端错误: {message}",
                "error_code": error_code,
                "request_id": e.response.get("ResponseMetadata", {}).get("RequestId", "Unknown"),
            }, ensure_ascii=False, indent=2))
        elif isinstance(e, BotoCoreError):
            print(json.dumps({"success": False, "error": f"客户端错误: {e}"}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"success": False, "error": f"未知错误: {e}"}, ensure_ascii=False, indent=2))
    except ImportError:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2))
    sys.exit(1)


def run(func):
    """运行主函数并捕获异常"""
    try:
        func()
    except SystemExit:
        raise
    except Exception as e:
        handle_error(e)


# ══════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════

def _parse_skill_md_regex(fm: str, path: str) -> dict | None:
    """正则 fallback 解析 SKILL.md frontmatter"""
    name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
    if not name_match:
        return None
    name = name_match.group(1).strip().strip('"\'')

    desc_pos = re.search(r"^description:\s*", fm, re.MULTILINE)
    if not desc_pos:
        return None

    rest = fm[desc_pos.end():]

    if rest.startswith('"'):
        desc_m = re.match(r'"(.*?)"', rest, re.DOTALL)
        description = desc_m.group(1).strip() if desc_m else ""
    elif rest.startswith("'"):
        desc_m = re.match(r"'(.*?)'", rest, re.DOTALL)
        description = desc_m.group(1).strip() if desc_m else ""
    elif rest.startswith("|") or rest.startswith(">"):
        lines = rest.split("\n")[1:]
        block_lines = []
        for line in lines:
            if line and (line[0] == " " or line[0] == "\t"):
                block_lines.append(line.strip())
            elif line.strip() == "":
                continue
            else:
                break
        description = " ".join(block_lines)
    else:
        description = rest.split("\n")[0].strip().strip('"\'')

    if not description:
        return None

    return {"name": name, "description": description, "path": path}


