#!/usr/bin/env python3
"""
文档分块模块 — 支持 recursive splitting 和 heading-aware splitting。

策略选择（auto 模式）：
  - Markdown 且 ≥3 个 heading → heading-aware recursive
  - 其他 → 纯 recursive character splitting

Benchmark 依据：
  - Recursive 512-token: Vecta 2026 评测 69% 准确率（7 策略第一）
  - Heading-aware: 在 recursive 基础上保留文档结构
"""

import re
from typing import Optional


# ── Token 估算 ────────────────────────────────────────────────────────
try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
    def count_tokens(text: str) -> int:
        return len(_enc.encode(text))
except ImportError:
    def count_tokens(text: str) -> int:
        return max(1, len(text) // 4)  # 1 token ≈ 4 chars fallback


# ── 数据结构 ──────────────────────────────────────────────────────────
class Chunk:
    """一个文档分块"""
    def __init__(self, content: str, index: int, heading_path: str = "",
                 metadata: Optional[dict] = None):
        self.content = content
        self.index = index
        self.heading_path = heading_path
        self.tokens = count_tokens(content)
        self.metadata = metadata or {}

    def __repr__(self):
        return f"Chunk(idx={self.index}, tokens={self.tokens}, heading={self.heading_path!r})"


# ── Recursive Character Splitting ─────────────────────────────────────
SEPARATORS = ["\n\n", "\n", ". ", "。", " ", ""]

def recursive_split(text: str, chunk_size: int = 512, chunk_overlap: int = 64,
                    min_chunk: int = 100) -> list[str]:
    """
    递归字符分割：按分隔符优先级分割，合并到目标大小。
    """
    pieces = _split_by_separators(text, SEPARATORS, chunk_size)

    # 合并小片段到目标大小
    chunks = []
    current = ""
    for piece in pieces:
        piece_tokens = count_tokens(piece)
        current_tokens = count_tokens(current)

        if current and current_tokens + piece_tokens > chunk_size:
            if current_tokens >= min_chunk:
                chunks.append(current.strip())
            elif chunks:
                # 太小，合并到上一个 chunk
                chunks[-1] = chunks[-1] + "\n" + current.strip()
            current = ""

            # overlap: 从上一个 chunk 尾部取 overlap tokens
            if chunks and chunk_overlap > 0:
                overlap_text = _take_tail(chunks[-1], chunk_overlap)
                current = overlap_text + "\n"

        current += piece

    if current.strip():
        if count_tokens(current) >= min_chunk:
            chunks.append(current.strip())
        elif chunks:
            chunks[-1] = chunks[-1] + "\n" + current.strip()

    return chunks if chunks else [text.strip()]


def _split_by_separators(text: str, separators: list[str], chunk_size: int) -> list[str]:
    """用第一个能产生合理大小片段的分隔符分割"""
    if not text.strip():
        return []

    for sep in separators:
        if not sep:
            # 最后一个分隔符：按字符截断
            result = []
            for i in range(0, len(text), chunk_size * 4):
                result.append(text[i:i + chunk_size * 4])
            return result

        parts = text.split(sep)
        if len(parts) > 1:
            # 检查是否有片段超过 chunk_size，如果有则对该片段用更细的分隔符
            result = []
            remaining_seps = separators[separators.index(sep) + 1:]
            for part in parts:
                part_with_sep = part + sep if part != parts[-1] else part
                if count_tokens(part_with_sep) > chunk_size and remaining_seps:
                    result.extend(_split_by_separators(part_with_sep, remaining_seps, chunk_size))
                else:
                    result.append(part_with_sep)
            return result

    return [text]


def _take_tail(text: str, token_count: int) -> str:
    """从文本尾部取约 token_count 个 token"""
    words = text.split()
    result = []
    tokens = 0
    for w in reversed(words):
        tokens += count_tokens(w)
        if tokens > token_count:
            break
        result.insert(0, w)
    return " ".join(result)


# ── Heading-Aware Recursive Splitting ─────────────────────────────────
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)

def heading_aware_split(text: str, chunk_size: int = 512, chunk_overlap: int = 64,
                        min_chunk: int = 100) -> list[Chunk]:
    """
    Markdown heading 感知分块：
    1. 按 heading 切分 section
    2. 每个 section 内部用 recursive splitting
    3. 保留 heading_path 层级链
    """
    sections = _parse_sections(text)
    chunks = []
    idx = 0

    for section in sections:
        heading_path = section["heading_path"]
        content = section["content"]

        # heading 本身作为内容前缀（参与 embedding）
        prefix = f"{heading_path}\n\n" if heading_path else ""

        if count_tokens(prefix + content) <= chunk_size:
            # section 够小，整个作为一个 chunk
            if count_tokens(content) >= min_chunk or not chunks:
                chunks.append(Chunk(
                    content=(prefix + content).strip(),
                    index=idx,
                    heading_path=heading_path,
                ))
                idx += 1
            elif chunks:
                # 太小，合并到上一个
                chunks[-1].content += "\n\n" + content.strip()
                chunks[-1].tokens = count_tokens(chunks[-1].content)
        else:
            # section 太大，内部 recursive split
            sub_chunks = recursive_split(content, chunk_size - count_tokens(prefix),
                                         chunk_overlap, min_chunk)
            for sc in sub_chunks:
                chunks.append(Chunk(
                    content=(prefix + sc).strip(),
                    index=idx,
                    heading_path=heading_path,
                ))
                idx += 1

    # 重新编号
    for i, c in enumerate(chunks):
        c.index = i
        c.tokens = count_tokens(c.content)

    return chunks


def _parse_sections(text: str) -> list[dict]:
    """解析 Markdown 为 section 列表，保留 heading 层级链"""
    lines = text.split("\n")
    sections = []
    current_headings = {}  # level → heading text
    current_content = []
    current_path = ""

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            # 保存之前的 section
            if current_content:
                sections.append({
                    "heading_path": current_path,
                    "content": "\n".join(current_content).strip(),
                })
                current_content = []

            level = len(m.group(1))
            heading_text = m.group(2).strip()
            current_headings[level] = heading_text
            # 清除更深层级
            for l in list(current_headings.keys()):
                if l > level:
                    del current_headings[l]

            # 构建 heading path
            current_path = " > ".join(
                current_headings[l] for l in sorted(current_headings.keys())
            )
            current_content.append(line)
        else:
            current_content.append(line)

    # 最后一个 section
    if current_content:
        sections.append({
            "heading_path": current_path,
            "content": "\n".join(current_content).strip(),
        })

    return sections if sections else [{"heading_path": "", "content": text}]


# ── Auto 策略选择 ─────────────────────────────────────────────────────
def chunk_text(text: str, strategy: str = "auto", chunk_size: int = 512,
               chunk_overlap: int = 64, min_chunk: int = 100,
               file_type: str = "") -> list[Chunk]:
    """
    统一分块入口。

    strategy: auto / recursive / heading
    file_type: md / txt / html / 其他
    """
    if strategy == "auto":
        # Markdown 且有足够 heading 结构 → heading-aware
        heading_count = len(HEADING_RE.findall(text))
        if (file_type in ("md", "markdown") or heading_count >= 3):
            strategy = "heading"
        else:
            strategy = "recursive"

    if strategy == "heading":
        return heading_aware_split(text, chunk_size, chunk_overlap, min_chunk)
    else:
        raw_chunks = recursive_split(text, chunk_size, chunk_overlap, min_chunk)
        return [Chunk(content=c, index=i) for i, c in enumerate(raw_chunks)]


# ── CLI 测试入口 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python3 chunker.py <file> [--chunk-size 512] [--strategy auto]")
        sys.exit(1)

    file_path = sys.argv[1]
    chunk_size = 512
    strategy = "auto"

    for i, arg in enumerate(sys.argv):
        if arg == "--chunk-size" and i + 1 < len(sys.argv):
            chunk_size = int(sys.argv[i + 1])
        if arg == "--strategy" and i + 1 < len(sys.argv):
            strategy = sys.argv[i + 1]

    with open(file_path) as f:
        text = f.read()

    ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
    chunks = chunk_text(text, strategy=strategy, chunk_size=chunk_size, file_type=ext)

    print(json.dumps({
        "file": file_path,
        "strategy": strategy,
        "chunk_size": chunk_size,
        "total_chunks": len(chunks),
        "chunks": [
            {"index": c.index, "tokens": c.tokens, "heading": c.heading_path,
             "preview": c.content[:100] + "..." if len(c.content) > 100 else c.content}
            for c in chunks
        ]
    }, ensure_ascii=False, indent=2))
